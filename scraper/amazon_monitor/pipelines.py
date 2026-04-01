from __future__ import annotations

import logging

import httpx


class ApiIngestionPipeline:
    def __init__(self, api_url: str, dry_run: bool = False) -> None:
        self.api_url = api_url.rstrip("/")
        self.dry_run = dry_run
        self.client: httpx.Client | None = None
        self.logger = logging.getLogger(__name__)

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            api_url=crawler.settings.get("INGEST_API_URL"),
            dry_run=crawler.settings.getbool("SCRAPER_DRY_RUN"),
        )

    def open_spider(self):
        if self.dry_run:
            self.logger.info("api_ingestion_disabled dry_run=true")
            return
        self.client = httpx.Client(base_url=self.api_url, timeout=30.0)

    def close_spider(self):
        if self.client is not None:
            self.client.close()

    def process_item(self, item):
        if self.client is None:
            return item
        response = self.client.post("/api/ingest", json=dict(item))
        response.raise_for_status()
        return item
