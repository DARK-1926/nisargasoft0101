# Amazon India Bearing Price Monitor

This repository contains a deployable MVP for monitoring bearing prices on Amazon India. It is designed for distributors tracking identical ASINs across multiple sellers, watching Buy Box ownership by buyer location, and reacting to significant price drops.

## 🚀 Quick Start

**One command to start everything:**

```bash
LAUNCH.bat
```

That's it! The system will automatically:
- Install all dependencies
- Start Redis (via Docker if available)
- Start API, scheduler, and frontend
- Open your browser to the dashboard

**See [QUICKSTART.md](QUICKSTART.md) for detailed instructions.**

## ✨ What's New

Recent fixes include:
- ✅ **Automatic scheduler** - Scrapes watchlist every 10 minutes
- ✅ **Complete seller capture** - Scrolls to load all sellers from Amazon
- ✅ **All 5 locations available** - Chennai, Mumbai, Bengaluru, Delhi, Hyderabad
- ✅ **Automatic Redis setup** - Starts in Docker if available

## What is included

- `backend`: FastAPI API, PostgreSQL/TimescaleDB models, alert evaluation, SSE stream, Prometheus metrics, Slack/email notifications.
- `scraper`: Scrapy + Playwright crawler scaffold with rotating proxies, user-agent rotation, location simulation hooks, and ingestion into the API.
- `frontend`: React + TypeScript dashboard for current offers, Buy Box state, price history, and active alerts.
- `infra`: Prometheus, Grafana, and Alertmanager configuration.
- `.github/workflows/ci.yml`: CI pipeline for Python checks, tests, frontend build, and Docker image builds.
- `docs`: submission-oriented notes for architecture, anti-blocking strategy, and checklist coverage.

## Architecture

1. Scraper searches Amazon.in for queries like `SKF bearing 6205`.
2. Search result pages yield ASINs and product metadata.
3. Product detail and offer listing pages are rendered with Playwright to capture seller offers and Buy Box context for a simulated buyer location.
4. Scraped snapshots are posted to the API ingestion endpoint.
5. The API persists product, seller, and offer history in PostgreSQL/TimescaleDB and optionally archives raw payloads to MongoDB.
6. Alert logic compares competitor prices against configured in-house sellers and emits Slack/email notifications for large drops.
7. The dashboard consumes `/api/current/{asin}`, `/api/history/{asin}`, `/api/insights/{asin}`, `/api/alerts`, and an SSE stream for live refreshes.

## Repository layout

```text
backend/                FastAPI service and scheduled jobs
scraper/                Scrapy project with Playwright support
frontend/               React dashboard
infra/                  Prometheus, Alertmanager, Grafana config
docs/                   Architecture and submission notes
docker-compose.yml      Local orchestration
```

## Quick start

1. Copy `.env.example` to `.env` and fill in real values for proxies, seller names, and notification channels.
2. Start the stack:

```bash
docker compose up --build
```

3. Open:
   - Dashboard: `http://localhost:3000`
   - API docs: `http://localhost:8000/docs`
   - Prometheus: `http://localhost:9090`
   - Grafana: `http://localhost:3001`
   - Alertmanager: `http://localhost:9093`

## Local development

### Python services

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .[dev]
playwright install chromium
uvicorn backend.app.main:app --reload
```

### Local MVP without Docker

If Docker is unavailable, you can still run the MVP end to end with a local SQLite database.

```bash
pip install -e .[dev]
playwright install chromium
export DATABASE_URL=sqlite+aiosqlite:///./artifacts/mvp.db
export MONGODB_URL=
export OWN_SELLER_NAMES=HEERA SPRING & MILL STORE
uvicorn backend.app.main:app --reload
```

Then run a real scrape into the local API:

```bash
python -m scraper.amazon_monitor.runner asin --asin B07H1GJZMP --location-code chennai-tn
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Environment variables

Important variables are documented in `.env.example`.

- `SEARCH_QUERIES`: comma-separated seed search terms.
- `DEFAULT_LOCATIONS`: comma-separated location profile codes such as `chennai-tn`.
- `OWN_SELLER_NAMES`: comma-separated internal seller names used for alert comparisons.
- `ROTATING_PROXIES`: proxy pool used by the scraper middleware.
- `SLACK_WEBHOOK_URL` and SMTP settings: optional outbound notifications.

## Notes on Amazon scraping

- The scraper is structured for Amazon pages, but selectors and anti-bot behavior should be treated as operational code that will need maintenance.
- Real production usage should rely on legally reviewed scraping policies, proxy governance, and careful rate limiting.
- Location simulation is implemented as a best-effort browser workflow that updates delivery PIN code and pairs requests with location-specific proxies.

## Core API endpoints

- `GET /api/products`
- `GET /api/current/{asin}?location_code=chennai-tn`
- `GET /api/history/{asin}?location_code=chennai-tn&hours=168`
- `GET /api/insights/{asin}?location_code=chennai-tn&hours=168`
- `GET /api/alerts`
- `POST /api/ingest`
- `GET /api/stream`

## Verification

Python syntax can be checked quickly with:

```bash
python -m compileall backend scraper
```

The frontend build is validated in CI and can be checked locally with:

```bash
cd frontend
npm install
npm run build
```

## Demo data

If you want to test the API and dashboard without running the live Amazon scraper, start the API and database stack and then seed sample snapshots:

```bash
python scripts/seed_demo_data.py --base-url http://localhost:8000
```

This inserts synthetic offer history for multiple sellers and locations, including alert-triggering price drops relative to `Nisargasoft Industrial`.

## Analytics report

Generate a markdown report from the running API:

```bash
python scripts/generate_analytics_report.py --base-url http://127.0.0.1:8000
```

The default output path is `artifacts/analytics_report.md`.

## Submission documents

- `docs/architecture.md`
- `docs/anti_blocking.md`
- `docs/submission_checklist.md`
