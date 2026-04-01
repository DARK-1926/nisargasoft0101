from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone

import httpx


def build_snapshots() -> list[dict]:
    start = datetime.now(timezone.utc) - timedelta(hours=12)
    snapshots: list[dict] = []

    price_points = [
        (1120.0, 1095.0, 1110.0),
        (1115.0, 1080.0, 1105.0),
        (1110.0, 1040.0, 1100.0),
        (1100.0, 1035.0, 1098.0),
        (1090.0, 1010.0, 1088.0),
        (1085.0, 995.0, 1080.0),
    ]

    for index, (ours, competitor_a, competitor_b) in enumerate(price_points):
        captured_at = (start + timedelta(hours=index * 2)).isoformat()
        snapshots.append(
            {
                "asin": "B0SKF6205X",
                "title": "SKF 6205 Deep Groove Ball Bearing",
                "brand": "SKF",
                "query": "SKF bearing 6205",
                "image_url": "https://example.com/skf-6205.jpg",
                "product_url": "https://www.amazon.in/dp/B0SKF6205X",
                "location_code": "chennai-tn",
                "buyer_pin_code": "600001",
                "captured_at": captured_at,
                "offers": [
                    {
                        "seller_id": "OURS01",
                        "seller_name": "Nisargasoft Industrial",
                        "price": ours,
                        "availability": "In stock",
                        "fba_status": True,
                        "buy_box_flag": competitor_a > ours,
                        "is_prime": True,
                        "offer_url": "https://www.amazon.in/gp/offer-listing/B0SKF6205X?smid=OURS01",
                    },
                    {
                        "seller_id": "COMPETA1",
                        "seller_name": "Bearing Hub Chennai",
                        "price": competitor_a,
                        "availability": "In stock",
                        "fba_status": True,
                        "buy_box_flag": competitor_a <= ours and competitor_a <= competitor_b,
                        "is_prime": True,
                        "offer_url": "https://www.amazon.in/gp/offer-listing/B0SKF6205X?smid=COMPETA1",
                    },
                    {
                        "seller_id": "COMPETB2",
                        "seller_name": "Motion Parts India",
                        "price": competitor_b,
                        "availability": "In stock",
                        "fba_status": False,
                        "buy_box_flag": competitor_b < ours and competitor_b < competitor_a,
                        "is_prime": False,
                        "offer_url": "https://www.amazon.in/gp/offer-listing/B0SKF6205X?smid=COMPETB2",
                    },
                ],
            }
        )

    snapshots.append(
        {
            "asin": "B0SKF6305Y",
            "title": "SKF 6305 Deep Groove Ball Bearing",
            "brand": "SKF",
            "query": "SKF bearing 6305",
            "image_url": "https://example.com/skf-6305.jpg",
            "product_url": "https://www.amazon.in/dp/B0SKF6305Y",
            "location_code": "mumbai-mh",
            "buyer_pin_code": "400001",
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "offers": [
                {
                    "seller_id": "OURS01",
                    "seller_name": "Nisargasoft Industrial",
                    "price": 840.0,
                    "availability": "In stock",
                    "fba_status": True,
                    "buy_box_flag": False,
                    "is_prime": True,
                    "offer_url": "https://www.amazon.in/gp/offer-listing/B0SKF6305Y?smid=OURS01",
                },
                {
                    "seller_id": "COMPETC3",
                    "seller_name": "SKF Trade Link",
                    "price": 735.0,
                    "availability": "Only 2 left",
                    "fba_status": True,
                    "buy_box_flag": True,
                    "is_prime": True,
                    "offer_url": "https://www.amazon.in/gp/offer-listing/B0SKF6305Y?smid=COMPETC3",
                },
            ],
        }
    )
    snapshots.append(
        {
            "asin": "B0SKF6305Y",
            "title": "SKF 6305 Deep Groove Ball Bearing",
            "brand": "SKF",
            "query": "SKF bearing 6305",
            "image_url": "https://example.com/skf-6305.jpg",
            "product_url": "https://www.amazon.in/dp/B0SKF6305Y",
            "location_code": "chennai-tn",
            "buyer_pin_code": "600001",
            "captured_at": (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat(),
            "offers": [
                {
                    "seller_id": "OURS01",
                    "seller_name": "Nisargasoft Industrial",
                    "price": 845.0,
                    "availability": "In stock",
                    "fba_status": True,
                    "buy_box_flag": False,
                    "is_prime": True,
                    "offer_url": "https://www.amazon.in/gp/offer-listing/B0SKF6305Y?smid=OURS01",
                },
                {
                    "seller_id": "COMPETC3",
                    "seller_name": "SKF Trade Link",
                    "price": 742.0,
                    "availability": "Only 2 left",
                    "fba_status": True,
                    "buy_box_flag": True,
                    "is_prime": True,
                    "offer_url": "https://www.amazon.in/gp/offer-listing/B0SKF6305Y?smid=COMPETC3",
                },
            ],
        }
    )
    return snapshots


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo offer history into the API")
    parser.add_argument("--base-url", default="http://localhost:8000")
    args = parser.parse_args()

    snapshots = build_snapshots()
    with httpx.Client(base_url=args.base_url, timeout=30.0) as client:
        for snapshot in snapshots:
            response = client.post("/api/ingest", json=snapshot)
            response.raise_for_status()
            print(f"ingested {snapshot['asin']} at {snapshot['captured_at']}")


if __name__ == "__main__":
    main()
