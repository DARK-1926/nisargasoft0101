from __future__ import annotations

import subprocess
import sys
import time

import structlog

from backend.app.celery_app import celery_app
from backend.app.metrics import SCRAPER_PROXY_FAILURES, SCRAPER_RUN_DURATION, SCRAPER_RUNS

logger = structlog.get_logger(__name__)


@celery_app.task(name="bearing_monitor.run_watchlist")
def run_watchlist() -> dict[str, int | str]:
    started_at = time.perf_counter()
    result = subprocess.run(
        [sys.executable, "-m", "scraper.amazon_monitor.runner", "monitor"],
        capture_output=True,
        text=True,
        check=False,
    )
    duration = time.perf_counter() - started_at
    proxy_failures = result.stdout.count("proxy_failure") + result.stderr.count("proxy_failure")

    SCRAPER_PROXY_FAILURES.inc(proxy_failures)
    SCRAPER_RUN_DURATION.observe(duration)

    if result.returncode != 0:
        SCRAPER_RUNS.labels(status="failure").inc()
        logger.error(
            "scraper_run_failed",
            return_code=result.returncode,
            stdout=result.stdout[-2000:],
            stderr=result.stderr[-2000:],
        )
        return {"status": "failure", "proxy_failures": proxy_failures}

    SCRAPER_RUNS.labels(status="success").inc()
    logger.info("scraper_run_completed", proxy_failures=proxy_failures, duration=duration)
    return {"status": "success", "proxy_failures": proxy_failures}
