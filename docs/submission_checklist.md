# PDF Submission Checklist

## Required Deliverables

- Working scraping pipeline
- Historical data storage
- Competitor pricing dashboard
- Analytics report
- Documentation for architecture and anti-blocking strategy
- Deployment and execution instructions

## Repository Mapping

- Scraping pipeline: `scraper/`
- Historical storage and API: `backend/`
- Dashboard: `frontend/`
- Analytics report generator: `scripts/generate_analytics_report.py`
- Architecture notes: `docs/architecture.md`
- Anti-blocking notes: `docs/anti_blocking.md`
- Run instructions: `README.md`

## Demo Path

1. Start the API and frontend.
2. Load demo data or run a live scrape.
3. Open the dashboard and confirm offers, Buy Box, history, and alerts.
4. Run `python scripts/generate_analytics_report.py` to produce a markdown report artifact.
