from __future__ import annotations

from celery import Celery

from backend.app.config import settings
from backend.app.metrics import maybe_start_worker_metrics_server

celery_app = Celery(
    "bearing_monitor",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["backend.app.tasks"],
)
celery_app.conf.timezone = "Asia/Kolkata"
celery_app.conf.beat_schedule = {
    "scrape-watchlist": {
        "task": "bearing_monitor.run_watchlist",
        "schedule": settings.scrape_interval_minutes * 60,
    }
}

maybe_start_worker_metrics_server()
