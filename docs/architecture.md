# Architecture Overview

## Pipeline

1. The scraper searches Amazon.in using product queries such as `SKF bearing 6205`.
2. Search result pages yield ASINs and basic product metadata.
3. Product detail and offer-listing pages are rendered with Playwright to capture seller offers, availability, and Buy Box context.
4. Scraped snapshots are posted into the FastAPI ingestion endpoint.
5. The API stores products, sellers, and time-series offers in PostgreSQL or local SQLite for MVP mode.
6. Alert evaluation compares configured in-house sellers against competitor offers and emits Slack or email notifications.
7. The dashboard consumes current offers, historical series, alerts, and market insights from the API.

## Main Components

- `scraper/amazon_monitor/spiders/amazon_bearings.py`: Amazon search, detail-page, and offer extraction.
- `scraper/amazon_monitor/middlewares.py`: proxy rotation, user-agent rotation, and location-aware request headers.
- `backend/app/routes.py`: API endpoints for ingestion, products, offers, history, alerts, and insights.
- `backend/app/services/market_data.py`: persistence and analytical summaries for current snapshots, history, and seller insights.
- `backend/app/tasks.py`: scheduled scrape execution through Celery.
- `frontend/src/App.tsx`: operator dashboard for competitor comparison and trend review.

## Data Model

- `products`: ASIN-level metadata such as title, brand, query, and product URL.
- `sellers`: normalized seller identities and display names.
- `offers`: price, availability, Buy Box flag, FBA status, and capture timestamp by ASIN and location.
- `alert_events`: generated undercut alerts with delivery status.

## Deployment Shape

- `api`: FastAPI service.
- `worker` and `beat`: Celery execution and scheduling.
- `scraper`: Playwright-capable crawler image.
- `postgres`, `mongo`, `redis`: backing services.
- `prometheus`, `grafana`, `alertmanager`: observability stack.
