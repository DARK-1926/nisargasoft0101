from decimal import Decimal

from backend.app.services.alert_rules import ComparableOffer, find_significant_price_drops


def test_detects_competitor_price_drop_against_own_offer() -> None:
    offers = [
        ComparableOffer(seller_id="ours", seller_name="Nisargasoft Industrial", price=Decimal("1000.00")),
        ComparableOffer(seller_id="competitor-a", seller_name="Competitor A", price=Decimal("850.00")),
        ComparableOffer(seller_id="competitor-b", seller_name="Competitor B", price=Decimal("970.00")),
    ]

    alerts = find_significant_price_drops(
        offers=offers,
        own_seller_names={"nisargasoft industrial"},
        threshold=0.10,
    )

    assert len(alerts) == 1
    assert alerts[0]["competitor_seller_id"] == "competitor-a"
    assert alerts[0]["delta_percent"] == Decimal("0.1500")


def test_returns_no_alert_when_own_offer_missing() -> None:
    offers = [
        ComparableOffer(seller_id="competitor-a", seller_name="Competitor A", price=Decimal("850.00")),
        ComparableOffer(seller_id="competitor-b", seller_name="Competitor B", price=Decimal("820.00")),
    ]

    alerts = find_significant_price_drops(
        offers=offers,
        own_seller_names={"nisargasoft industrial"},
        threshold=0.10,
    )

    assert alerts == []
