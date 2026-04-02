from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette import EventSourceResponse

from backend.app.config import settings
from backend.app.db import get_db
from backend.app.events import event_broker
from backend.app.location_profiles import resolve_locations
from backend.app.metrics import metrics_response
from backend.app.models import AlertEvent, Product
from backend.app.schemas import (
    AlertEventOut,
    CurrentAsinOut,
    DiscoverProductsIn,
    DiscoverProductsOut,
    HistoryOut,
    IngestResultOut,
    IngestSnapshotIn,
    LocationProfileOut,
    MarketInsightOut,
    ProductSummaryOut,
    TrackUrlIn,
    TrackUrlOut,
    WatchlistItemIn,
    WatchlistItemOut,
)
from backend.app.services.live_acquisition import (
    LiveAcquisitionError,
    discover_search_products,
    resolve_amazon_asin,
    run_asin_scrape,
    run_asin_scrape_all_locations,
)
from backend.app.services.market_data import (
    get_product_summary,
    get_current_snapshot,
    get_market_insights,
    get_price_history,
    ingest_snapshot,
    list_products,
)
from backend.app.services.product_filters import matches_tracking_filters
from backend.app.services.watchlist import add_watchlist_item, list_watchlist, remove_watchlist_item

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/metrics")
async def metrics():
    return metrics_response()


@router.get("/api/locations", response_model=list[LocationProfileOut])
async def locations() -> list[LocationProfileOut]:
    # Return all known location profiles, not just the configured defaults.
    from backend.app.location_profiles import LOCATION_PROFILES
    return [
        LocationProfileOut(
            code=profile.code,
            city=profile.city,
            state=profile.state,
            pin_code=profile.pin_code,
        )
        for profile in LOCATION_PROFILES.values()
    ]


@router.get("/api/products", response_model=list[ProductSummaryOut])
async def products(
    search: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    session: AsyncSession = Depends(get_db),
) -> list[ProductSummaryOut]:
    return [ProductSummaryOut(**row) for row in await list_products(session, limit=limit, search=search)]


@router.get("/api/watchlist", response_model=list[WatchlistItemOut])
async def watchlist(
    location_code: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> list[WatchlistItemOut]:
    rows = await list_watchlist(session, location_code=location_code)
    return [WatchlistItemOut(**row) for row in rows]


@router.post("/api/watchlist", response_model=WatchlistItemOut)
async def create_watchlist_item(
    payload: WatchlistItemIn,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> WatchlistItemOut:
    if await session.get(Product, payload.asin) is None:
        api_base_url = str(request.base_url).rstrip("/")
        try:
            await run_asin_scrape_all_locations(
                asin=payload.asin,
                api_base_url=api_base_url,
                title_hint=payload.source_query,
            )
        except LiveAcquisitionError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        await session.rollback()
        if await session.get(Product, payload.asin) is None:
            session.add(
                Product(
                    asin=payload.asin,
                    title=payload.title or payload.asin,
                    brand=payload.brand,
                    query=payload.source_query,
                    product_url=f"https://www.amazon.in/dp/{payload.asin}",
                )
            )
            await session.commit()

    try:
        item = await add_watchlist_item(
            session,
            asin=payload.asin,
            location_code=payload.location_code,
            source_query=payload.source_query,
            brand_filter=payload.brand_filter,
            model_filter=payload.model_filter,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return WatchlistItemOut(**item)


@router.delete("/api/watchlist/{asin}")
async def delete_watchlist_item(
    asin: str,
    location_code: str = Query(...),
    session: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    deleted = await remove_watchlist_item(session, asin=asin, location_code=location_code)
    if not deleted:
        raise HTTPException(status_code=404, detail="Watchlist item not found.")
    return {"deleted": True}


@router.get("/api/current/{asin}", response_model=CurrentAsinOut)
async def current_offer_snapshot(
    asin: str,
    location_code: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> CurrentAsinOut:
    resolved_location = location_code or settings.default_locations[0]
    snapshot = await get_current_snapshot(session, asin=asin, location_code=resolved_location)
    if not snapshot["offers"]:
        raise HTTPException(status_code=404, detail="No offers found for ASIN")
    return CurrentAsinOut(**snapshot)


@router.get("/api/history/{asin}", response_model=HistoryOut)
async def history(
    asin: str,
    location_code: str | None = Query(default=None),
    hours: int = Query(default=168, ge=1, le=2160),
    session: AsyncSession = Depends(get_db),
) -> HistoryOut:
    resolved_location = location_code or settings.default_locations[0]
    snapshot = await get_price_history(session, asin=asin, location_code=resolved_location, hours=hours)
    return HistoryOut(**snapshot)


@router.get("/api/insights/{asin}", response_model=MarketInsightOut)
async def insights(
    asin: str,
    location_code: str | None = Query(default=None),
    hours: int = Query(default=168, ge=1, le=2160),
    session: AsyncSession = Depends(get_db),
) -> MarketInsightOut:
    resolved_location = location_code or settings.default_locations[0]
    snapshot = await get_market_insights(session, asin=asin, location_code=resolved_location, hours=hours)
    return MarketInsightOut(**snapshot)


@router.get("/api/alerts", response_model=list[AlertEventOut])
async def alerts(
    limit: int = Query(default=50, le=250),
    session: AsyncSession = Depends(get_db),
) -> list[AlertEventOut]:
    stmt = select(AlertEvent).order_by(desc(AlertEvent.created_at)).limit(limit)
    rows = (await session.execute(stmt)).scalars().all()
    return [
        AlertEventOut(
            id=row.id,
            asin=row.asin,
            product_title=row.product_title,
            location_code=row.location_code,
            competitor_seller_name=row.competitor_seller_name,
            own_seller_name=row.own_seller_name,
            competitor_price=float(row.competitor_price),
            own_price=float(row.own_price),
            delta_percent=float(row.delta_percent),
            message=row.message,
            slack_sent=row.slack_sent,
            email_sent=row.email_sent,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.post("/api/ingest", response_model=IngestResultOut)
async def ingest(
    payload: IngestSnapshotIn,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> IngestResultOut:
    result = await ingest_snapshot(
        session=session,
        payload=payload,
        archive=request.app.state.mongo_archive,
        notifier=request.app.state.notifier,
        own_seller_names=settings.own_seller_lookup,
        price_drop_threshold=settings.price_drop_threshold,
    )
    await event_broker.publish(
        "snapshot.updated",
        {
            "asin": payload.asin,
            "location_code": payload.location_code,
            "offers_ingested": result["offers_ingested"],
        },
    )
    if result["alerts_created"]:
        await event_broker.publish(
            "alert.created",
            {
                "asin": payload.asin,
                "location_code": payload.location_code,
                "alerts_created": result["alerts_created"],
            },
        )
    return IngestResultOut(**result)


@router.post("/api/track-url", response_model=TrackUrlOut)
async def track_url(
    payload: TrackUrlIn,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> TrackUrlOut:
    asin = await resolve_amazon_asin(payload.url)
    if asin is None:
        raise HTTPException(status_code=400, detail="Could not extract a valid ASIN from the provided Amazon URL.")

    api_base_url = str(request.base_url).rstrip("/")
    try:
        await run_asin_scrape_all_locations(
            asin=asin,
            api_base_url=api_base_url,
            title_hint=payload.title_hint,
        )
    except LiveAcquisitionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    snapshot = await get_current_snapshot(session, asin=asin, location_code=payload.location_code)
    if not snapshot["offers"]:
        raise HTTPException(status_code=502, detail="Scrape completed but no offers were captured for this ASIN.")

    product = await get_product_summary(session, asin)
    if product is None:
        raise HTTPException(status_code=404, detail="Product was scraped but could not be loaded from storage.")

    return TrackUrlOut(
        asin=asin,
        location_code=payload.location_code,
        product=ProductSummaryOut(**product),
        snapshot=CurrentAsinOut(**snapshot),
    )


@router.post("/api/discover", response_model=DiscoverProductsOut)
async def discover_products(
    payload: DiscoverProductsIn,
    request: Request,
) -> DiscoverProductsOut:
    api_base_url = str(request.base_url).rstrip("/")
    try:
        products = await discover_search_products(
            query=payload.query,
            location_code=payload.location_code,
            max_pages=payload.max_pages,
            api_base_url=api_base_url,
        )
    except LiveAcquisitionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if payload.brand_filter or payload.model_filter:
        products = [
            row
            for row in products
            if matches_tracking_filters(
                row.title,
                row.brand,
                brand_filter=payload.brand_filter,
                model_filter=payload.model_filter,
            )
        ]
    return DiscoverProductsOut(
        query=payload.query,
        location_code=payload.location_code,
        brand_filter=payload.brand_filter,
        model_filter=payload.model_filter,
        tracked_count=len(products),
        products=[
            ProductSummaryOut(
                asin=row.asin,
                title=row.title,
                brand=row.brand,
                last_seen_at=row.last_seen_at,
                available_locations=row.available_locations or [],
            )
            for row in products
        ],
    )


@router.get("/api/stream")
async def stream(request: Request) -> EventSourceResponse:
    async def generator():
        async with event_broker.subscribe() as queue:
            yield {"event": "connected", "data": json.dumps({"status": "connected"})}
            while True:
                if await request.is_disconnected():
                    break
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield {"event": message["event"], "data": json.dumps(message["data"])}
                except TimeoutError:
                    yield {
                        "event": "heartbeat",
                        "data": json.dumps({"timestamp": datetime.now(timezone.utc).isoformat(), "status": "alive"}),
                    }

    return EventSourceResponse(generator())
