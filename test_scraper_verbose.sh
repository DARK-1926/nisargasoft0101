#!/bin/bash
export TWISTED_REACTOR=twisted.internet.asyncioreactor.AsyncioSelectorReactor
export SCRAPY_LOG_LEVEL=DEBUG
python -m scraper.amazon_monitor.runner asin --asin B07845BYSZ --location-code chennai-tn --artifact-dir /tmp 2>&1 | grep -i "download\|handler\|playwright" | head -50
