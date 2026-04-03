from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

from backend.app.services.market_data import build_market_insights


def make_offer(
    seller_id: str,
    price: str,
    captured_at: datetime,
    *,
    buy_box_flag: bool = False,
):
    return SimpleNamespace(
        seller_id=seller_id,
        price=Decimal(price),
        captured_at=captured_at,
        buy_box_flag=buy_box_flag,
    )


def test_build_market_insights_summarizes_leaders_and_price_changes() -> None:
    start = datetime(2026, 3, 30, 8, 0, tzinfo=timezone.utc)
    rows = [
        (make_offer("ours", "1000.00", start, buy_box_flag=True), "Nisargasoft Industrial"),
        (make_offer("comp-a", "980.00", start), "Bearing Hub Chennai"),
        (make_offer("ours", "995.00", start + timedelta(hours=2)), "Nisargasoft Industrial"),
        (make_offer("comp-a", "970.00", start + timedelta(hours=2), buy_box_flag=True), "Bearing Hub Chennai"),
        (make_offer("ours", "990.00", start + timedelta(hours=4)), "Nisargasoft Industrial"),
        (make_offer("comp-a", "990.00", start + timedelta(hours=4)), "Bearing Hub Chennai"),
    ]

    result = build_market_insights(
        asin="B0SKF6205X",
        title="SKF 6205 Deep Groove Ball Bearing",
        location_code="chennai-tn",
        hours=168,
        rows=rows,
    )

    assert result["snapshot_count"] == 3
    assert result["seller_count"] == 2
    assert result["current_lowest_price"] == 990.0
    # At the final snapshot both sellers are tied at 990.0 — lowest seller is whichever
    # sorts first; just assert the price is correct rather than a specific seller name.
    assert result["buy_box_seller"] == "Nisargasoft Industrial"
    assert result["highest_price_seen"] == 1000.0
    assert result["lowest_price_seen"] == 970.0
    assert result["seller_insights"][0]["seller_name"] == "Bearing Hub Chennai"
    assert result["seller_insights"][0]["leadership_wins"] == 3
    assert result["seller_insights"][0]["price_change_count"] == 2
    assert result["seller_insights"][1]["buy_box_wins"] == 1
