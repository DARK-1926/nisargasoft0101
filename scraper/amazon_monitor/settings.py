from __future__ import annotations

import os


def split_csv(value: str) -> list[str]:
    return [chunk.strip() for chunk in value.split(",") if chunk.strip()]


BOT_NAME = "amazon_price_monitor"
SPIDER_MODULES = ["scraper.amazon_monitor.spiders"]
NEWSPIDER_MODULE = "scraper.amazon_monitor.spiders"

ROBOTSTXT_OBEY = False
LOG_LEVEL = os.getenv("SCRAPY_LOG_LEVEL", "INFO")
CONCURRENT_REQUESTS = int(os.getenv("SCRAPER_CONCURRENT_REQUESTS", "2"))
DOWNLOAD_DELAY = float(os.getenv("SCRAPER_DOWNLOAD_DELAY", "2.0"))
DOWNLOAD_TIMEOUT = int(os.getenv("SCRAPER_DOWNLOAD_TIMEOUT", "90"))
RETRY_TIMES = int(os.getenv("SCRAPER_RETRY_TIMES", "4"))
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = float(os.getenv("SCRAPER_AUTOTHROTTLE_START_DELAY", "1.5"))
AUTOTHROTTLE_MAX_DELAY = float(os.getenv("SCRAPER_AUTOTHROTTLE_MAX_DELAY", "15.0"))
AUTOTHROTTLE_TARGET_CONCURRENCY = float(os.getenv("SCRAPER_TARGET_CONCURRENCY", "1.0"))
COOKIES_ENABLED = True

INGEST_API_URL = os.getenv("INGEST_API_URL", "http://localhost:8000")
AMAZON_BASE_URL = os.getenv("AMAZON_BASE_URL", "https://www.amazon.in")
DEFAULT_LOCATION_CODES = split_csv(os.getenv("DEFAULT_LOCATIONS", "chennai-tn"))
SEARCH_QUERIES = split_csv(os.getenv("SEARCH_QUERIES", "SKF bearing 6205"))
ROTATING_PROXY_LIST = split_csv(os.getenv("ROTATING_PROXIES", ""))
PLAYWRIGHT_HEADLESS = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() == "true"
SCRAPER_DRY_RUN = os.getenv("SCRAPER_DRY_RUN", "false").lower() == "true"

USER_AGENT_POOL = [
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    ),
    ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 " "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"),
]

DOWNLOADER_MIDDLEWARES = {
    "scraper.amazon_monitor.middlewares.RandomizedProxyMiddleware": 350,
}
ITEM_PIPELINES = {
    "scraper.amazon_monitor.pipelines.ApiIngestionPipeline": 300,
}

TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}
PLAYWRIGHT_BROWSER_TYPE = "chromium"
PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = int(os.getenv("PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT_MS", "45000"))
PLAYWRIGHT_MAX_PAGES_PER_CONTEXT = int(os.getenv("PLAYWRIGHT_MAX_PAGES_PER_CONTEXT", "4"))
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": PLAYWRIGHT_HEADLESS,
}
