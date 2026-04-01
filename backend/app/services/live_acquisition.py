from __future__ import annotations

import asyncio
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import httpx
import scrapy

from backend.app.location_profiles import resolve_location
from backend.app.services.product_filters import validate_product
from scraper.amazon_monitor.spiders.amazon_bearings import AmazonBearingsSpider


ASIN_RE = re.compile(r"\b([A-Z0-9]{10})\b", re.IGNORECASE)
PRODUCT_PATH_RE = re.compile(r"/(?:dp|gp/product|gp/aw/d|gp/offer-listing)/([A-Z0-9]{10})", re.IGNORECASE)
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class LiveAcquisitionError(RuntimeError):
    pass


@dataclass(slots=True)
class ScrapeExecutionResult:
    command: list[str]
    stdout: str
    stderr: str


@dataclass(slots=True)
class DiscoveryCandidate:
    asin: str
    title: str
    brand: str | None
    last_seen_at: None = None
    available_locations: list[str] | None = None


def extract_amazon_asin(url_or_asin: str) -> str | None:
    candidate = (url_or_asin or "").strip()
    if not candidate:
        return None

    candidate = unquote(candidate)

    direct_match = ASIN_RE.fullmatch(candidate)
    if direct_match:
        return direct_match.group(1).upper()

    parsed = urlparse(candidate)
    if parsed.scheme and parsed.netloc:
        path_match = PRODUCT_PATH_RE.search(parsed.path)
        if path_match:
            return path_match.group(1).upper()

        for key in ("asin", "ASIN", "pd_rd_i"):
            values = parse_qs(parsed.query).get(key)
            if values:
                match = ASIN_RE.search(values[0])
                if match:
                    return match.group(1).upper()
        fallback_match = PRODUCT_PATH_RE.search(candidate) or ASIN_RE.search(candidate)
        if fallback_match:
            return fallback_match.group(1).upper()
        return None

    loose_match = PRODUCT_PATH_RE.search(candidate) or ASIN_RE.search(candidate)
    if loose_match:
        return loose_match.group(1).upper()
    return None


async def resolve_amazon_asin(url_or_asin: str) -> str | None:
    extracted = extract_amazon_asin(url_or_asin)
    if extracted:
        return extracted

    candidate = (url_or_asin or "").strip()
    parsed = urlparse(candidate)
    if not parsed.scheme or not parsed.netloc:
        return None

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=20.0,
            headers={"User-Agent": "Mozilla/5.0"},
        ) as client:
            response = await client.get(candidate)
    except httpx.HTTPError:
        return None

    return extract_amazon_asin(str(response.url))


async def run_asin_scrape(
    *,
    asin: str,
    location_code: str,
    api_base_url: str,
    title_hint: str | None = None,
    artifact_dir: str = "artifacts/scraper_failures",
    timeout_seconds: int = 240,
) -> ScrapeExecutionResult:
    command = [
        sys.executable,
        "-m",
        "scraper.amazon_monitor.runner",
        "asin",
        "--asin",
        asin,
        "--location-code",
        location_code,
        "--artifact-dir",
        artifact_dir,
    ]
    if title_hint:
        command.extend(["--title-hint", title_hint])
    return await _run_scraper_command(command, api_base_url=api_base_url, timeout_seconds=timeout_seconds)


async def run_search_scrape(
    *,
    query: str,
    location_code: str,
    api_base_url: str,
    max_pages: int = 1,
    artifact_dir: str = "artifacts/scraper_failures",
    timeout_seconds: int = 420,
) -> ScrapeExecutionResult:
    command = [
        sys.executable,
        "-m",
        "scraper.amazon_monitor.runner",
        "search",
        "--query",
        query,
        "--location-code",
        location_code,
        "--max-pages",
        str(max_pages),
        "--artifact-dir",
        artifact_dir,
    ]
    return await _run_scraper_command(command, api_base_url=api_base_url, timeout_seconds=timeout_seconds)


async def discover_search_products(
    *,
    query: str,
    location_code: str,
    max_pages: int = 1,
) -> list[DiscoveryCandidate]:
    location = resolve_location(location_code)
    spider = AmazonBearingsSpider(query=query, location_code=location_code, max_pages=max_pages)
    seen: dict[str, DiscoveryCandidate] = {}
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-IN,en;q=0.9",
        "X-Forwarded-For": location.x_forwarded_for,
    }

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=30.0,
        headers=headers,
    ) as client:
        for page_number in range(1, max_pages + 1):
            search_url = f"https://www.amazon.in/s?k={quote_plus(query)}&page={page_number}"
            try:
                response = await client.get(search_url)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise LiveAcquisitionError(f"Amazon search discovery failed for page {page_number}.") from exc
            cards = spider.extract_search_cards(scrapy.Selector(text=response.text))
            for card in cards:
                asin = card["asin"]
                title = card["title"] or asin or ""
                if not asin or asin in seen:
                    continue
                if not validate_product(title, None, query).is_bearing:
                    continue
                seen[asin] = DiscoveryCandidate(
                    asin=asin,
                    title=title,
                    brand=None,
                    available_locations=[location_code],
                )

    return list(seen.values())


async def _run_scraper_command(
    command: list[str],
    *,
    api_base_url: str,
    timeout_seconds: int,
) -> ScrapeExecutionResult:
    env = os.environ.copy()
    env["INGEST_API_URL"] = api_base_url.rstrip("/")
    env.setdefault("SCRAPER_ARTIFACT_DIR", "artifacts/scraper_failures")
    env.setdefault("PYTHONIOENCODING", "utf-8")

    process = await asyncio.create_subprocess_exec(
        *command,
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=timeout_seconds)
    except TimeoutError as exc:
        process.kill()
        await process.communicate()
        raise LiveAcquisitionError("Live scrape timed out before completing.") from exc

    stdout = stdout_bytes.decode("utf-8", errors="replace")
    stderr = stderr_bytes.decode("utf-8", errors="replace")
    result = ScrapeExecutionResult(command=command, stdout=stdout, stderr=stderr)
    if process.returncode != 0:
        diagnostic = stderr.strip() or stdout.strip() or f"Scraper exited with code {process.returncode}."
        raise LiveAcquisitionError(diagnostic[-1200:])
    return result
