from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    log_json: bool = False
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/bearing_monitor"
    mongodb_url: str | None = None
    mongodb_database: str = "bearing_monitor"
    redis_url: str = "redis://localhost:6379/0"
    api_port: int = 8000
    worker_metrics_port: int = 9102
    prometheus_namespace: str = "bearing_monitor"
    amazon_base_url: str = "https://www.amazon.in"
    ingest_api_url: str = "http://localhost:8000"
    frontend_origin: str = "http://localhost:3000"
    search_queries_raw: str = Field(default="SKF bearing 6205", alias="SEARCH_QUERIES")
    default_locations_raw: str = Field(default="chennai-tn", alias="DEFAULT_LOCATIONS")
    own_seller_names_raw: str = Field(default="", alias="OWN_SELLER_NAMES")
    rotating_proxies_raw: str = Field(default="", alias="ROTATING_PROXIES")
    price_drop_threshold: float = 0.10
    scrape_interval_minutes: int = 20
    slack_webhook_url: str | None = None
    alert_email_from: str | None = None
    alert_email_to: str | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    playwright_headless: bool = True

    @staticmethod
    def _split_csv(value: str) -> list[str]:
        return [chunk.strip() for chunk in value.split(",") if chunk.strip()]

    @property
    def search_queries(self) -> list[str]:
        return self._split_csv(self.search_queries_raw)

    @property
    def default_locations(self) -> list[str]:
        return self._split_csv(self.default_locations_raw)

    @property
    def own_seller_names(self) -> list[str]:
        return self._split_csv(self.own_seller_names_raw)

    @property
    def rotating_proxies(self) -> list[str]:
        return self._split_csv(self.rotating_proxies_raw)

    @property
    def own_seller_lookup(self) -> set[str]:
        return {seller.casefold() for seller in self.own_seller_names}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
