#!/bin/bash
export TWISTED_REACTOR=twisted.internet.asyncioreactor.AsyncioSelectorReactor
python -m scraper.amazon_monitor.runner asin --asin B07845BYSZ --location-code chennai-tn --artifact-dir /tmp 2>&1 | tail -30
