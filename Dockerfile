FROM python:3.11-slim-bookworm AS python-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY scrapy.cfg ./
COPY backend ./backend
COPY scraper ./scraper

FROM python-base AS api-base
RUN python -m pip install --no-cache-dir \
    "aiosqlite>=0.20.0" \
    "asyncpg>=0.29.0" \
    "celery[redis]>=5.4.0" \
    "fastapi>=0.115.0" \
    "httpx>=0.27.0" \
    "motor>=3.5.0" \
    "orjson>=3.10.0" \
    "prometheus-client>=0.20.0" \
    "psycopg[binary]>=3.2.0" \
    "pydantic-settings>=2.3.0" \
    "sqlalchemy[asyncio]>=2.0.31" \
    "sse-starlette>=2.1.2" \
    "structlog>=24.2.0" \
    "tenacity>=8.4.2" \
    "uvicorn[standard]>=0.30.1" \
    "python-slugify>=8.0.4"

FROM api-base AS crawler-base
RUN python -m pip install --no-cache-dir \
    "Scrapy>=2.11.0" \
    "scrapy-playwright>=0.0.35" \
    "playwright>=1.45.0"

# Install playwright browsers for API container (needed for live scraping)
RUN playwright install --with-deps chromium

FROM crawler-base AS backend
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM crawler-base AS worker
ENV ENABLE_WORKER_METRICS=1
CMD ["celery", "-A", "backend.app.celery_app.celery_app", "worker", "--loglevel=info"]

FROM crawler-base AS beat
CMD ["celery", "-A", "backend.app.celery_app.celery_app", "beat", "--loglevel=info"]

FROM crawler-base AS scraper
CMD ["python", "-m", "scraper.amazon_monitor.runner", "monitor"]
