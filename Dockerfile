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
    "beautifulsoup4>=4.12.0" \
    "celery[redis]>=5.4.0" \
    "fastapi>=0.115.0" \
    "httpx>=0.27.0" \
    "motor>=3.5.0" \
    "orjson>=3.10.0" \
    "prometheus-client>=0.20.0" \
    "psycopg[binary]>=3.2.0" \
    "pydantic-settings>=2.3.0" \
    "selenium>=4.15.0" \
    "sqlalchemy[asyncio]>=2.0.31" \
    "sse-starlette>=2.1.2" \
    "structlog>=24.2.0" \
    "tenacity>=8.4.2" \
    "undetected-chromedriver>=3.5.0" \
    "uvicorn[standard]>=0.30.1" \
    "python-slugify>=8.0.4"

# Install Chrome for Selenium
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

FROM api-base AS backend
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM api-base AS worker
ENV ENABLE_WORKER_METRICS=1
CMD ["celery", "-A", "backend.app.celery_app.celery_app", "worker", "--loglevel=info"]

FROM api-base AS beat
CMD ["celery", "-A", "backend.app.celery_app.celery_app", "beat", "--loglevel=info"]
