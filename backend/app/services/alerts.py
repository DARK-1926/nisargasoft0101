from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.metrics import ALERTS_TRIGGERED
from backend.app.models import AlertEvent
from backend.app.notifications import Notifier
from backend.app.services.alert_rules import ComparableOffer, find_significant_price_drops


async def create_alert_records(
    session: AsyncSession,
    asin: str,
    product_title: str,
    location_code: str,
    offers: list[ComparableOffer],
    own_seller_names: set[str],
    threshold: float,
    notifier: Notifier,
) -> list[AlertEvent]:
    created: list[AlertEvent] = []
    dedupe_cutoff = datetime.now(timezone.utc) - timedelta(hours=4)

    for candidate in find_significant_price_drops(offers, own_seller_names, threshold):
        existing = await session.scalar(
            select(AlertEvent).where(
                AlertEvent.asin == asin,
                AlertEvent.location_code == location_code,
                AlertEvent.competitor_seller_id == candidate["competitor_seller_id"],
                AlertEvent.own_seller_id == candidate["own_seller_id"],
                AlertEvent.created_at >= dedupe_cutoff,
            )
        )
        if existing:
            continue

        message = (
            f"{candidate['competitor_seller_name']} is pricing {asin} at INR "
            f"{candidate['competitor_price']:.2f}, which is {candidate['delta_percent']:.2%} "
            f"below {candidate['own_seller_name']} in {location_code}."
        )
        payload = {
            "asin": asin,
            "product_title": product_title,
            "location_code": location_code,
            "message": message,
            **candidate,
        }
        slack_sent, email_sent = await notifier.notify(payload)

        alert = AlertEvent(
            asin=asin,
            product_title=product_title,
            location_code=location_code,
            competitor_seller_id=str(candidate["competitor_seller_id"]),
            competitor_seller_name=str(candidate["competitor_seller_name"]),
            own_seller_id=str(candidate["own_seller_id"]),
            own_seller_name=str(candidate["own_seller_name"]),
            competitor_price=Decimal(candidate["competitor_price"]),
            own_price=Decimal(candidate["own_price"]),
            delta_percent=Decimal(candidate["delta_percent"]),
            message=message,
            slack_sent=slack_sent,
            email_sent=email_sent,
        )
        session.add(alert)
        created.append(alert)
        ALERTS_TRIGGERED.inc()

    if created:
        await session.commit()

    return created
