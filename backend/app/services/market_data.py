from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from statistics import mean

from slugify import slugify
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.metrics import OFFERS_INGESTED
from backend.app.models import Offer, Product, Seller
from backend.app.mongo import MongoArchive
from backend.app.notifications import Notifier
from backend.app.schemas import IngestSnapshotIn
from backend.app.services.alert_rules import ComparableOffer
from backend.app.services.alerts import create_alert_records
from backend.app.services.product_filters import validate_product


def seller_identity(raw_seller_id: str | None, seller_name: str) -> str:
    if raw_seller_id:
        return raw_seller_id.strip()
    return slugify(seller_name)[:120] or "unknown-seller"


async def ingest_snapshot(
    session: AsyncSession,
    payload: IngestSnapshotIn,
    archive: MongoArchive,
    notifier: Notifier,
    own_seller_names: set[str],
    price_drop_threshold: float,
) -> dict[str, int | str]:
    product = await session.get(Product, payload.asin)
    if product is None:
        product = Product(
            asin=payload.asin,
            title=payload.title,
            brand=payload.brand,
            query=payload.query,
            image_url=payload.image_url,
            product_url=payload.product_url,
        )
        session.add(product)
    else:
        product.title = payload.title
        product.brand = payload.brand
        product.query = payload.query
        product.image_url = payload.image_url
        product.product_url = payload.product_url

    captured_at = payload.captured_at or datetime.now(timezone.utc)

    for incoming_offer in payload.offers:
        seller_id = seller_identity(incoming_offer.seller_id, incoming_offer.seller_name)
        seller = await session.get(Seller, seller_id)
        if seller is None:
            seller = Seller(seller_id=seller_id, name=incoming_offer.seller_name)
            session.add(seller)
        else:
            seller.name = incoming_offer.seller_name

        session.add(
            Offer(
                asin=payload.asin,
                seller_id=seller_id,
                price=incoming_offer.price,
                list_price=incoming_offer.list_price,
                shipping_price=incoming_offer.shipping_price,
                availability=incoming_offer.availability,
                fba_status=incoming_offer.fba_status,
                buy_box_flag=incoming_offer.buy_box_flag,
                is_prime=incoming_offer.is_prime,
                buyer_location_code=payload.location_code,
                buyer_pin_code=payload.buyer_pin_code,
                offer_url=incoming_offer.offer_url,
                raw_payload=incoming_offer.raw_payload,
                captured_at=captured_at,
            )
        )

    await session.commit()
    OFFERS_INGESTED.inc(len(payload.offers))
    await archive.store_snapshot(payload.model_dump(mode="json"))

    current = await get_current_snapshot(session, payload.asin, payload.location_code)
    current_offers = [
        ComparableOffer(
            seller_id=offer["seller_id"],
            seller_name=offer["seller_name"],
            price=Decimal(str(offer["price"])),
            buy_box_flag=offer["buy_box_flag"],
            fba_status=offer["fba_status"],
        )
        for offer in current["offers"]
    ]

    alerts = await create_alert_records(
        session=session,
        asin=payload.asin,
        product_title=payload.title,
        location_code=payload.location_code,
        offers=current_offers,
        own_seller_names=own_seller_names,
        threshold=price_drop_threshold,
        notifier=notifier,
    )
    return {
        "asin": payload.asin,
        "offers_ingested": len(payload.offers),
        "alerts_created": len(alerts),
    }


async def list_products(session: AsyncSession, limit: int = 50, search: str | None = None) -> list[dict]:
    last_seen_subquery = (
        select(Offer.asin, func.max(Offer.captured_at).label("last_seen_at")).group_by(Offer.asin).subquery()
    )
    stmt = (
        select(Product, last_seen_subquery.c.last_seen_at)
        .join(last_seen_subquery, Product.asin == last_seen_subquery.c.asin)
        .order_by(last_seen_subquery.c.last_seen_at.desc())
        .limit(limit)
    )
    if search:
        stmt = stmt.where(
            or_(
                Product.asin.ilike(f"%{search}%"),
                Product.title.ilike(f"%{search}%"),
                Product.query.ilike(f"%{search}%"),
            )
        )

    rows = (await session.execute(stmt)).all()
    asins = [product.asin for product, _ in rows]
    location_map: dict[str, list[str]] = defaultdict(list)

    if asins:
        location_rows = (
            await session.execute(
                select(Offer.asin, Offer.buyer_location_code)
                .where(Offer.asin.in_(asins))
                .distinct()
                .order_by(Offer.asin.asc(), Offer.buyer_location_code.asc())
            )
        ).all()
        for asin, location_code in location_rows:
            if location_code not in location_map[asin]:
                location_map[asin].append(location_code)

    products = [
        {
            "asin": product.asin,
            "title": product.title,
            "brand": product.brand,
            "last_seen_at": last_seen_at,
            "available_locations": location_map.get(product.asin, []),
            "query": product.query,
        }
        for product, last_seen_at in rows
    ]
    filtered_products = [
        {
            "asin": row["asin"],
            "title": row["title"],
            "brand": row["brand"],
            "last_seen_at": row["last_seen_at"],
            "available_locations": row["available_locations"],
        }
        for row in products
        if validate_product(row["title"], row["brand"], row["query"]).is_valid
    ]
    return filtered_products[:limit]


async def get_product_summary(session: AsyncSession, asin: str) -> dict | None:
    rows = await list_products(session, limit=500)
    return next((row for row in rows if row["asin"] == asin), None)


async def list_products_for_query(
    session: AsyncSession,
    query: str,
    location_code: str,
    lookback_hours: int = 1,
    limit: int = 100,
) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    last_seen_subquery = (
        select(Offer.asin, func.max(Offer.captured_at).label("last_seen_at"))
        .where(
            Offer.buyer_location_code == location_code,
            Offer.captured_at >= cutoff,
        )
        .group_by(Offer.asin)
        .subquery()
    )
    stmt = (
        select(Product, last_seen_subquery.c.last_seen_at)
        .join(last_seen_subquery, Product.asin == last_seen_subquery.c.asin)
        .where(Product.query == query)
        .order_by(last_seen_subquery.c.last_seen_at.desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    asins = [product.asin for product, _ in rows]
    location_map: dict[str, list[str]] = defaultdict(list)

    if asins:
        location_rows = (
            await session.execute(
                select(Offer.asin, Offer.buyer_location_code)
                .where(
                    Offer.asin.in_(asins),
                    Offer.captured_at >= cutoff,
                )
                .distinct()
                .order_by(Offer.asin.asc(), Offer.buyer_location_code.asc())
            )
        ).all()
        for asin_value, product_location_code in location_rows:
            if product_location_code not in location_map[asin_value]:
                location_map[asin_value].append(product_location_code)

    products = [
        {
            "asin": product.asin,
            "title": product.title,
            "brand": product.brand,
            "last_seen_at": last_seen_at,
            "available_locations": location_map.get(product.asin, []),
            "query": product.query,
        }
        for product, last_seen_at in rows
    ]
    filtered_products = [
        {
            "asin": row["asin"],
            "title": row["title"],
            "brand": row["brand"],
            "last_seen_at": row["last_seen_at"],
            "available_locations": row["available_locations"],
        }
        for row in products
        if validate_product(row["title"], row["brand"], row["query"]).is_valid
    ]
    return filtered_products[:limit]


async def get_current_snapshot(session: AsyncSession, asin: str, location_code: str) -> dict:
    # Find the single most recent captured_at across all sellers for this
    # ASIN+location. All offers from that scrape run share the same timestamp
    # because the spider sets captured_at once per ingest call.
    latest_ts_row = await session.execute(
        select(func.max(Offer.captured_at))
        .where(Offer.asin == asin, Offer.buyer_location_code == location_code)
    )
    latest_ts = latest_ts_row.scalar_one_or_none()

    if latest_ts is None:
        return {
            "asin": asin,
            "title": asin,
            "location_code": location_code,
            "captured_at": None,
            "buy_box_offer": None,
            "offers": [],
        }

    # Allow a 5-second window around the latest timestamp to catch any offers
    # that were written in the same scrape run but committed a moment later.
    window_start = latest_ts - timedelta(seconds=5)

    stmt = (
        select(Offer, Seller.name, Product.title)
        .join(Seller, Seller.seller_id == Offer.seller_id)
        .join(Product, Product.asin == Offer.asin)
        .where(
            Offer.asin == asin,
            Offer.buyer_location_code == location_code,
            Offer.captured_at >= window_start,
        )
        .order_by(Offer.price.asc())
    )
    rows = (await session.execute(stmt)).all()

    offers = []
    title = rows[0][2] if rows else asin
    latest_captured_at = None

    # Deduplicate: keep only the most recent offer per seller within the window.
    seen_sellers: set[str] = set()
    for offer, seller_name, _ in sorted(rows, key=lambda r: r[0].captured_at, reverse=True):
        if offer.seller_id in seen_sellers:
            continue
        seen_sellers.add(offer.seller_id)
        latest_captured_at = max(latest_captured_at, offer.captured_at) if latest_captured_at else offer.captured_at
        offers.append(
            {
                "seller_id": offer.seller_id,
                "seller_name": seller_name,
                "price": float(offer.price),
                "list_price": float(offer.list_price) if offer.list_price is not None else None,
                "shipping_price": float(offer.shipping_price) if offer.shipping_price is not None else None,
                "availability": offer.availability,
                "fba_status": offer.fba_status,
                "buy_box_flag": offer.buy_box_flag,
                "is_prime": offer.is_prime,
                "offer_url": offer.offer_url,
                "captured_at": offer.captured_at,
            }
        )

    # Re-sort by price ascending after dedup.
    offers.sort(key=lambda o: o["price"])
    buy_box_offer = next((o for o in offers if o["buy_box_flag"]), offers[0] if offers else None)
    return {
        "asin": asin,
        "title": title,
        "location_code": location_code,
        "captured_at": latest_captured_at,
        "buy_box_offer": buy_box_offer,
        "offers": offers,
    }


async def get_price_history(session: AsyncSession, asin: str, location_code: str, hours: int = 168) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    stmt = (
        select(Offer, Seller.name)
        .join(Seller, Seller.seller_id == Offer.seller_id)
        .where(
            Offer.asin == asin,
            Offer.buyer_location_code == location_code,
            Offer.captured_at >= cutoff,
        )
        .order_by(Offer.captured_at.asc())
    )
    rows = (await session.execute(stmt)).all()

    series_map: dict[str, dict] = defaultdict(lambda: {"seller_name": "", "points": []})
    for offer, seller_name in rows:
        series_map[offer.seller_id]["seller_name"] = seller_name
        series_map[offer.seller_id]["points"].append(
            {
                "captured_at": offer.captured_at,
                "price": float(offer.price),
                "buy_box_flag": offer.buy_box_flag,
            }
        )

    series = [
        {
            "seller_id": seller_id,
            "seller_name": payload["seller_name"],
            "points": payload["points"],
        }
        for seller_id, payload in series_map.items()
    ]
    series.sort(key=lambda row: row["seller_name"].casefold())
    return {
        "asin": asin,
        "location_code": location_code,
        "hours": hours,
        "series": series,
    }


def build_market_insights(
    asin: str,
    title: str,
    location_code: str,
    hours: int,
    rows: list[tuple[Offer, str]],
) -> dict:
    if not rows:
        return {
            "asin": asin,
            "title": title,
            "location_code": location_code,
            "hours": hours,
            "snapshot_count": 0,
            "seller_count": 0,
            "captured_from": None,
            "captured_to": None,
            "current_lowest_price": None,
            "current_lowest_seller": None,
            "buy_box_seller": None,
            "highest_price_seen": None,
            "lowest_price_seen": None,
            "seller_insights": [],
        }

    seller_points: dict[str, dict] = {}
    snapshot_map: dict[datetime, list[dict]] = defaultdict(list)
    all_prices: list[float] = []
    captured_from = rows[0][0].captured_at
    captured_to = rows[-1][0].captured_at

    for offer, seller_name in rows:
        price = float(offer.price)
        all_prices.append(price)
        if offer.seller_id not in seller_points:
            seller_points[offer.seller_id] = {
                "seller_name": seller_name,
                "points": [],
                "buy_box_wins": 0,
                "leadership_wins": 0,
            }
        seller_points[offer.seller_id]["points"].append(
            {
                "captured_at": offer.captured_at,
                "price": price,
                "buy_box_flag": offer.buy_box_flag,
            }
        )
        if offer.buy_box_flag:
            seller_points[offer.seller_id]["buy_box_wins"] += 1
        snapshot_map[offer.captured_at].append(
            {
                "seller_id": offer.seller_id,
                "seller_name": seller_name,
                "price": price,
                "buy_box_flag": offer.buy_box_flag,
            }
        )

    latest_snapshot_at = max(snapshot_map)
    latest_snapshot = sorted(snapshot_map[latest_snapshot_at], key=lambda row: row["price"])
    current_lowest = latest_snapshot[0]
    buy_box_offer = next((row for row in latest_snapshot if row["buy_box_flag"]), current_lowest)

    for snapshot_rows in snapshot_map.values():
        leader_price = min(row["price"] for row in snapshot_rows)
        leaders = [row["seller_id"] for row in snapshot_rows if row["price"] == leader_price]
        for seller_id in leaders:
            seller_points[seller_id]["leadership_wins"] += 1

    seller_insights = []
    for seller_id, payload in seller_points.items():
        points = sorted(payload["points"], key=lambda row: row["captured_at"])
        price_change_count = 0
        previous_price = None
        for point in points:
            if previous_price is not None and point["price"] != previous_price:
                price_change_count += 1
            previous_price = point["price"]

        prices = [point["price"] for point in points]
        seller_insights.append(
            {
                "seller_id": seller_id,
                "seller_name": payload["seller_name"],
                "min_price": min(prices),
                "max_price": max(prices),
                "avg_price": round(mean(prices), 2),
                "latest_price": points[-1]["price"],
                "price_change_count": price_change_count,
                "buy_box_wins": payload["buy_box_wins"],
                "leadership_wins": payload["leadership_wins"],
            }
        )

    seller_insights.sort(
        key=lambda row: (
            -row["leadership_wins"],
            -row["buy_box_wins"],
            row["latest_price"],
            row["seller_name"].casefold(),
        )
    )

    return {
        "asin": asin,
        "title": title,
        "location_code": location_code,
        "hours": hours,
        "snapshot_count": len(snapshot_map),
        "seller_count": len(seller_insights),
        "captured_from": captured_from,
        "captured_to": captured_to,
        "current_lowest_price": current_lowest["price"],
        "current_lowest_seller": current_lowest["seller_name"],
        "buy_box_seller": buy_box_offer["seller_name"],
        "highest_price_seen": max(all_prices),
        "lowest_price_seen": min(all_prices),
        "seller_insights": seller_insights,
    }


async def get_market_insights(session: AsyncSession, asin: str, location_code: str, hours: int = 168) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    stmt = (
        select(Offer, Seller.name, Product.title)
        .join(Seller, Seller.seller_id == Offer.seller_id)
        .join(Product, Product.asin == Offer.asin)
        .where(
            Offer.asin == asin,
            Offer.buyer_location_code == location_code,
            Offer.captured_at >= cutoff,
        )
        .order_by(Offer.captured_at.asc(), Offer.price.asc())
    )
    results = (await session.execute(stmt)).all()
    title = results[0][2] if results else asin
    rows = [(offer, seller_name) for offer, seller_name, _ in results]
    return build_market_insights(
        asin=asin,
        title=title,
        location_code=location_code,
        hours=hours,
        rows=rows,
    )
