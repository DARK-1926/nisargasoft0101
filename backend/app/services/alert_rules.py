from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(slots=True)
class ComparableOffer:
    seller_id: str
    seller_name: str
    price: Decimal
    buy_box_flag: bool = False
    fba_status: bool = False


def find_significant_price_drops(
    offers: list[ComparableOffer], own_seller_names: set[str], threshold: float
) -> list[dict[str, Decimal | str]]:
    if not own_seller_names:
        return []

    own_offers = [
        offer
        for offer in offers
        if offer.seller_name.casefold() in own_seller_names or offer.seller_id.casefold() in own_seller_names
    ]
    if not own_offers:
        return []

    reference_offer = min(own_offers, key=lambda offer: offer.price)
    alerts: list[dict[str, Decimal | str]] = []
    threshold_decimal = Decimal(str(threshold))

    for offer in offers:
        if offer.seller_id == reference_offer.seller_id:
            continue
        if offer.price >= reference_offer.price:
            continue

        delta = (reference_offer.price - offer.price) / reference_offer.price
        if delta < threshold_decimal:
            continue

        alerts.append(
            {
                "competitor_seller_id": offer.seller_id,
                "competitor_seller_name": offer.seller_name,
                "own_seller_id": reference_offer.seller_id,
                "own_seller_name": reference_offer.seller_name,
                "competitor_price": offer.price,
                "own_price": reference_offer.price,
                "delta_percent": delta.quantize(Decimal("0.0001")),
            }
        )

    alerts.sort(key=lambda row: row["delta_percent"], reverse=True)
    return alerts
