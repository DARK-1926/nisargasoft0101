from __future__ import annotations

import os
import time

from fastapi import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest, start_http_server
from starlette.middleware.base import BaseHTTPMiddleware

from backend.app.config import settings

HTTP_REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests handled by the API",
    ["method", "path", "status_code"],
    namespace=settings.prometheus_namespace,
)
HTTP_LATENCY = Histogram(
    "http_request_latency_seconds",
    "Latency of API requests",
    ["method", "path"],
    namespace=settings.prometheus_namespace,
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)
OFFERS_INGESTED = Counter(
    "offers_ingested_total",
    "Number of offer snapshots ingested",
    namespace=settings.prometheus_namespace,
)
ALERTS_TRIGGERED = Counter(
    "alerts_triggered_total",
    "Number of pricing alerts created",
    namespace=settings.prometheus_namespace,
)
SCRAPER_RUNS = Counter(
    "scraper_runs_total",
    "Scheduled scraper runs",
    ["status"],
    namespace=settings.prometheus_namespace,
)
SCRAPER_PROXY_FAILURES = Counter(
    "scraper_proxy_failures_total",
    "Proxy failures observed during scraping",
    namespace=settings.prometheus_namespace,
)
SCRAPER_RUN_DURATION = Histogram(
    "scraper_run_duration_seconds",
    "Duration of scraper task execution",
    namespace=settings.prometheus_namespace,
    buckets=(5, 15, 30, 60, 120, 300, 600),
)

_worker_metrics_started = False


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        started_at = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - started_at
        path = request.url.path
        HTTP_REQUESTS.labels(method=request.method, path=path, status_code=str(response.status_code)).inc()
        HTTP_LATENCY.labels(method=request.method, path=path).observe(elapsed)
        return response


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def maybe_start_worker_metrics_server() -> None:
    global _worker_metrics_started
    if _worker_metrics_started or not os.getenv("ENABLE_WORKER_METRICS"):
        return
    start_http_server(settings.worker_metrics_port)
    _worker_metrics_started = True
