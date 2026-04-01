from __future__ import annotations

import argparse
from pathlib import Path

import httpx


def build_report(base_url: str, hours: int) -> str:
    with httpx.Client(base_url=base_url, timeout=30.0) as client:
        products = client.get("/api/products").json()
        alerts = client.get("/api/alerts").json()

        lines = [
            "# Amazon India Bearing Monitor Analytics Report",
            "",
            "## Executive Summary",
            "",
            f"- Products tracked: {len(products)}",
            f"- Active alerts captured: {len(alerts)}",
            f"- Analysis window: last {hours} hours",
            "",
            "## Product Intelligence",
            "",
        ]

        for product in products:
            locations = product.get("available_locations") or []
            if not locations:
                continue

            lines.append(f"### {product['asin']} - {product['title']}")
            lines.append("")

            for location_code in locations:
                insight = client.get(
                    f"/api/insights/{product['asin']}",
                    params={"location_code": location_code, "hours": hours},
                ).json()
                current = client.get(
                    f"/api/current/{product['asin']}",
                    params={"location_code": location_code},
                ).json()

                lines.extend(
                    [
                        f"#### Location: {location_code}",
                        "",
                        f"- Buy Box seller: {insight['buy_box_seller'] or 'Unknown'}",
                        f"- Current lowest seller: {insight['current_lowest_seller'] or 'Unknown'}",
                        f"- Current lowest price: INR {insight['current_lowest_price'] or 0:.2f}",
                        (
                            f"- Historical range: INR {insight['lowest_price_seen'] or 0:.2f} "
                            f"to INR {insight['highest_price_seen'] or 0:.2f}"
                        ),
                        f"- Snapshots analyzed: {insight['snapshot_count']}",
                        f"- Live offers in latest snapshot: {len(current.get('offers', []))}",
                        "",
                        "| Seller | Latest Price | Avg Price | Price Changes | Buy Box Wins | Leadership Wins |",
                        "| --- | ---: | ---: | ---: | ---: | ---: |",
                    ]
                )

                for seller in insight["seller_insights"]:
                    lines.append(
                        "| "
                        f"{seller['seller_name']} | "
                        f"INR {seller['latest_price']:.2f} | "
                        f"INR {seller['avg_price']:.2f} | "
                        f"{seller['price_change_count']} | "
                        f"{seller['buy_box_wins']} | "
                        f"{seller['leadership_wins']} |"
                    )

                product_alerts = [
                    alert
                    for alert in alerts
                    if alert["asin"] == product["asin"] and alert["location_code"] == location_code
                ]
                lines.extend(["", "Recent alerts:"])
                if product_alerts:
                    for alert in product_alerts[:5]:
                        lines.append(f"- {alert['message']}")
                else:
                    lines.append("- None in the current report window.")
                lines.append("")

        lines.extend(
            [
                "## Notes",
                "",
                "- Buy Box detection is derived from the latest captured offer stack for each product and location.",
                (
                    "- Price leadership counts how often a seller matched the cheapest visible price "
                    "in captured snapshots."
                ),
                "- Price change count measures visible seller price moves inside the report window.",
                "",
            ]
        )
        return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a markdown analytics report from the running API"
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--hours", type=int, default=168)
    parser.add_argument("--output", default="artifacts/analytics_report.md")
    args = parser.parse_args()

    report = build_report(args.base_url, args.hours)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"report written to {output_path}")


if __name__ == "__main__":
    main()
