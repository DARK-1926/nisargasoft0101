from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from backend.app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    import backend.app.models  # noqa: F401

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        if "postgresql" in settings.database_url:
            await connection.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb"))
            await connection.execute(text("""
                    SELECT create_hypertable(
                        'offers',
                        'captured_at',
                        if_not_exists => TRUE,
                        migrate_data => TRUE
                    )
                    """))


async def close_db() -> None:
    await engine.dispose()
