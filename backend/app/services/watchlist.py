from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import Offer, Product, WatchlistItem
from backend.app.services.product_filters import matches_tracking_filters


async def list_watchlist(session: AsyncSession, location_code: str | None = None) -> list[dict]:
    last_seen_subquery = (
        select(
            Offer.asin,
            Offer.buyer_location_code,
            func.max(Offer.captured_at).label("last_seen_at"),
        )
        .group_by(Offer.asin, Offer.buyer_location_code)
        .subquery()
    )
    stmt = (
        select(WatchlistItem, Product.title, Product.brand, last_seen_subquery.c.last_seen_at)
        .join(Product, Product.asin == WatchlistItem.asin)
        .outerjoin(
            last_seen_subquery,
            (last_seen_subquery.c.asin == WatchlistItem.asin)
            & (last_seen_subquery.c.buyer_location_code == WatchlistItem.location_code),
        )
        .where(WatchlistItem.active.is_(True))
        .order_by(WatchlistItem.created_at.desc())
    )
    if location_code:
        stmt = stmt.where(WatchlistItem.location_code == location_code)

    rows = (await session.execute(stmt)).all()
    return [
        {
            "id": item.id,
            "asin": item.asin,
            "title": title,
            "brand": brand,
            "location_code": item.location_code,
            "source_query": item.source_query,
            "brand_filter": item.brand_filter,
            "model_filter": item.model_filter,
            "last_seen_at": last_seen_at,
            "created_at": item.created_at,
        }
        for item, title, brand, last_seen_at in rows
    ]


async def add_watchlist_item(
    session: AsyncSession,
    *,
    asin: str,
    location_code: str,
    source_query: str | None = None,
    brand_filter: str | None = None,
    model_filter: str | None = None,
) -> dict:
    product = await session.get(Product, asin)
    if product is None:
        raise RuntimeError(f"Product {asin} is not available in storage.")

    if (brand_filter or model_filter) and not matches_tracking_filters(
        product.title,
        product.brand,
        brand_filter=brand_filter,
        model_filter=model_filter,
    ):
        raise ValueError("Product does not satisfy the requested brand/model filters.")

    existing = (
        await session.execute(
            select(WatchlistItem).where(
                WatchlistItem.asin == asin,
                WatchlistItem.location_code == location_code,
            )
        )
    ).scalar_one_or_none()

    if existing is None:
        existing = WatchlistItem(
            asin=asin,
            location_code=location_code,
            source_query=source_query,
            brand_filter=brand_filter,
            model_filter=model_filter,
            active=True,
        )
        session.add(existing)
    else:
        existing.active = True
        existing.source_query = source_query or existing.source_query
        existing.brand_filter = brand_filter or existing.brand_filter
        existing.model_filter = model_filter or existing.model_filter

    await session.commit()
    rows = await list_watchlist(session, location_code=location_code)
    item = next((row for row in rows if row["asin"] == asin and row["location_code"] == location_code), None)
    if item is None:
        raise RuntimeError("Watchlist item was saved but could not be reloaded.")
    return item


async def remove_watchlist_item(session: AsyncSession, *, asin: str, location_code: str) -> bool:
    result = await session.execute(
        delete(WatchlistItem).where(
            WatchlistItem.asin == asin,
            WatchlistItem.location_code == location_code,
        )
    )
    await session.commit()
    return bool(result.rowcount)


async def get_active_watchlist_targets(session: AsyncSession) -> list[dict[str, str]]:
    rows = (
        await session.execute(
            select(WatchlistItem.asin, WatchlistItem.location_code)
            .where(WatchlistItem.active.is_(True))
            .order_by(WatchlistItem.created_at.asc())
        )
    ).all()
    return [{"asin": asin, "location_code": location_code} for asin, location_code in rows]
