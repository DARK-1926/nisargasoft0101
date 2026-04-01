from __future__ import annotations

from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient
import structlog

from backend.app.config import settings

logger = structlog.get_logger(__name__)


class MongoArchive:
    def __init__(self) -> None:
        self.client: AsyncIOMotorClient | None = None
        self.collection = None

    async def connect(self) -> None:
        if not settings.mongodb_url:
            return
        try:
            self.client = AsyncIOMotorClient(settings.mongodb_url, serverSelectionTimeoutMS=2_000)
            await self.client.admin.command("ping")
            self.collection = self.client[settings.mongodb_database]["raw_offer_snapshots"]
        except Exception:  # noqa: BLE001
            logger.warning("mongo_archive_unavailable")
            await self.close()

    async def store_snapshot(self, document: dict[str, Any]) -> None:
        if self.collection is None:
            return
        try:
            await self.collection.insert_one(document)
        except Exception:  # noqa: BLE001
            logger.warning("mongo_archive_store_failed")
            await self.close()

    async def close(self) -> None:
        self.collection = None
        if self.client is not None:
            self.client.close()
            self.client = None


mongo_archive = MongoArchive()
