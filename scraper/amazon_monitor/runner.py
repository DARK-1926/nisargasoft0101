from __future__ import annotations

import argparse
import os

import httpx
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from scraper.amazon_monitor.spiders.amazon_bearings import AmazonBearingsSpider


def split_csv(value: str) -> list[str]:
    return [chunk.strip() for chunk in value.split(",") if chunk.strip()]


def default_artifact_dir() -> str:
    return os.getenv("SCRAPER_ARTIFACT_DIR", "artifacts/scraper_failures")


def add_artifact_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--artifact-dir", default=default_artifact_dir())


def add_dry_run_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--dry-run", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Amazon India bearing monitor runner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    search_parser = subparsers.add_parser("search")
    search_parser.add_argument("--query", required=True)
    search_parser.add_argument("--location-code", required=True)
    search_parser.add_argument("--max-pages", type=int, default=2)
    add_artifact_arg(search_parser)
    add_dry_run_arg(search_parser)

    asin_parser = subparsers.add_parser("asin")
    asin_parser.add_argument("--asin", required=True)
    asin_parser.add_argument("--location-code", required=True)
    asin_parser.add_argument("--title-hint")
    add_artifact_arg(asin_parser)
    add_dry_run_arg(asin_parser)

    monitor_parser = subparsers.add_parser("monitor")
    monitor_parser.add_argument("--max-pages", type=int, default=2)
    add_artifact_arg(monitor_parser)
    add_dry_run_arg(monitor_parser)

    return parser


def watchlist_api_url() -> str:
    return f"{os.getenv('INGEST_API_URL', 'http://localhost:8000').rstrip('/')}/api/watchlist"


def load_watchlist_targets() -> list[dict[str, str]]:
    response = httpx.get(watchlist_api_url(), timeout=30.0)
    response.raise_for_status()
    rows = response.json()
    return [
        {
            "asin": row["asin"],
            "location_code": row["location_code"],
        }
        for row in rows
    ]


def main() -> None:
    args = build_parser().parse_args()
    if args.dry_run:
        os.environ["SCRAPER_DRY_RUN"] = "true"
    process = CrawlerProcess(get_project_settings())

    if args.command == "search":
        process.crawl(
            AmazonBearingsSpider,
            query=args.query,
            location_code=args.location_code,
            max_pages=args.max_pages,
            artifact_dir=args.artifact_dir,
        )
    elif args.command == "asin":
        process.crawl(
            AmazonBearingsSpider,
            query=args.title_hint,
            asin=args.asin,
            location_code=args.location_code,
            artifact_dir=args.artifact_dir,
        )
    else:
        targets = load_watchlist_targets()
        for target in targets:
            process.crawl(
                AmazonBearingsSpider,
                asin=target["asin"],
                location_code=target["location_code"],
                artifact_dir=args.artifact_dir,
            )

    process.start()


if __name__ == "__main__":
    main()
