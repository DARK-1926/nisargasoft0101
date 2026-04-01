import pytest

from backend.app.mongo import MongoArchive


class FailingCollection:
    async def insert_one(self, document):  # noqa: ANN001
        raise RuntimeError("mongo unavailable")


class ClosableClient:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_store_snapshot_is_best_effort_when_archive_fails() -> None:
    archive = MongoArchive()
    archive.client = ClosableClient()
    archive.collection = FailingCollection()

    await archive.store_snapshot({"asin": "B07H1GJZMP"})

    assert archive.collection is None
    assert archive.client is None
