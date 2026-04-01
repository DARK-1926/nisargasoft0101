from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, urljoin, urlparse

import scrapy
from scrapy import Request
from slugify import slugify

from backend.app.config import settings as app_settings
from backend.app.location_profiles import resolve_location

PRICE_RE = re.compile(r"([\d,]+(?:\.\d{2})?)")


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = " ".join(value.split()).strip()
    return text or None


def parse_price(raw_text: str | None) -> float | None:
    text = clean_text(raw_text)
    if not text:
        return None
    match = PRICE_RE.search(text.replace("â‚¹", "").replace("₹", "").replace("INR", ""))
    if not match:
        return None
    return float(match.group(1).replace(",", ""))


def extract_first(selector: scrapy.Selector, css_queries: list[str]) -> str | None:
    for query in css_queries:
        value = clean_text(selector.css(query).get())
        if value:
            return value
    return None


def extract_joined(selector: scrapy.Selector, css_queries: list[str]) -> str | None:
    for query in css_queries:
        value = join_clean_text(selector.css(query).getall())
        if value:
            return value
    return None


def join_clean_text(values: list[str]) -> str | None:
    cleaned = [clean_text(value) for value in values]
    collapsed = [value for value in cleaned if value]
    if not collapsed:
        return None
    return clean_text(" ".join(collapsed))


def safe_response_text(response: scrapy.http.Response) -> str:
    try:
        return response.text
    except AttributeError:
        return response.body.decode("utf-8", errors="replace")


def looks_invalid_product_title(title: str | None) -> bool:
    normalized = clean_text(title)
    if not normalized:
        return True
    lowered = normalized.casefold()
    return lowered in {
        "page not found",
        "amazon.in",
        "amazon.in: page not found",
        "amazon.in page not found",
    }


class FailureArtifactStore:
    def __init__(self, artifact_dir: str | None) -> None:
        self.root = Path(artifact_dir).expanduser() if artifact_dir else None

    @property
    def enabled(self) -> bool:
        return self.root is not None

    def capture_response_artifact(
        self,
        label: str,
        response: scrapy.http.Response,
        extra: dict[str, Any] | None = None,
        body_text: str | None = None,
    ) -> Path | None:
        metadata = {
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "label": label,
            "url": response.url,
            "status": response.status,
            "headers": dict(response.headers.to_unicode_dict()),
            **(extra or {}),
        }
        return self._write_bundle(
            label=label,
            body_text=body_text if body_text is not None else safe_response_text(response),
            metadata=metadata,
        )

    def capture_page_artifact(
        self,
        label: str,
        url: str,
        body_text: str | None,
        extra: dict[str, Any] | None = None,
        screenshot_bytes: bytes | None = None,
    ) -> Path | None:
        metadata = {
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "label": label,
            "url": url,
            **(extra or {}),
        }
        return self._write_bundle(
            label=label,
            body_text=body_text,
            metadata=metadata,
            screenshot_bytes=screenshot_bytes,
        )

    def _write_bundle(
        self,
        label: str,
        body_text: str | None,
        metadata: dict[str, Any],
        screenshot_bytes: bytes | None = None,
    ) -> Path | None:
        if self.root is None:
            return None

        day_dir = self.root / datetime.now(timezone.utc).strftime("%Y-%m-%d")
        day_dir.mkdir(parents=True, exist_ok=True)
        base_path = day_dir / self._build_stem(label, metadata)

        base_path.with_suffix(".json").write_text(
            json.dumps(metadata, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        if body_text is not None:
            base_path.with_suffix(".html").write_text(body_text, encoding="utf-8")
        if screenshot_bytes is not None:
            base_path.with_suffix(".png").write_bytes(screenshot_bytes)
        return base_path

    @staticmethod
    def _build_stem(label: str, metadata: dict[str, Any]) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        subject_bits = [
            metadata.get("asin"),
            metadata.get("query"),
            metadata.get("location_code"),
            metadata.get("page_number"),
            metadata.get("status"),
        ]
        subject = slugify("-".join(str(bit) for bit in subject_bits if bit is not None))[:80] or "artifact"
        return f"{timestamp}-{slugify(label)[:40]}-{subject}"


class AmazonBearingsSpider(scrapy.Spider):
    name = "amazon_bearings"
    OFFER_PAGE_TIMEOUT_MS = 45_000
    OFFER_PAGE_READY_TIMEOUT_MS = 15_000
    CONTENT_RETRY_COUNT = 3

    def __init__(
        self,
        query: str | None = None,
        location_code: str = "chennai-tn",
        max_pages: int = 2,
        asin: str | None = None,
        artifact_dir: str | None = None,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        if not clean_text(query) and not clean_text(asin):
            raise ValueError("Either query or asin must be provided")

        self.query = clean_text(query)
        self.target_asin = clean_text(asin)
        self.location_profile = resolve_location(location_code)
        self.max_pages = max_pages
        self.base_url = app_settings.amazon_base_url
        self.artifacts = FailureArtifactStore(artifact_dir)

    @property
    def crawl_label(self) -> str:
        return self.query or f"asin:{self.target_asin}"

    async def start(self):
        if self.target_asin:
            yield Request(
                f"{self.base_url}/dp/{self.target_asin}",
                callback=self.parse_product_detail,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "location_profile": self.location_profile,
                    "handle_httpstatus_all": True,
                },
                cb_kwargs={
                    "asin": self.target_asin,
                    "title_hint": self.query or self.target_asin,
                    "image_url": None,
                },
                dont_filter=True,
            )
            return

        for page in range(1, self.max_pages + 1):
            search_url = f"{self.base_url}/s?k={quote_plus(self.query or '')}&page={page}"
            yield Request(
                search_url,
                callback=self.parse_search_results,
                meta={
                    "playwright": True,
                    "location_profile": self.location_profile,
                    "handle_httpstatus_all": True,
                },
                cb_kwargs={"page_number": page},
                dont_filter=True,
            )

    def parse_search_results(self, response: scrapy.http.Response, page_number: int):
        if response.status >= 400:
            self.capture_response_failure(
                "search-http-error",
                response,
                page_number=page_number,
                query=self.crawl_label,
                location_code=self.location_profile.code,
            )
            return

        cards = self.extract_search_cards(response.selector)
        self.logger.info(
            "parsed_search_results query=%s page=%s cards=%s location=%s",
            self.crawl_label,
            page_number,
            len(cards),
            self.location_profile.code,
        )

        if not cards:
            self.capture_response_failure(
                "search-empty-results",
                response,
                page_number=page_number,
                query=self.crawl_label,
                location_code=self.location_profile.code,
            )
            return

        for card in cards:
            yield response.follow(
                card["href"],
                callback=self.parse_product_detail,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "location_profile": self.location_profile,
                    "handle_httpstatus_all": True,
                },
                cb_kwargs={
                    "asin": card["asin"],
                    "title_hint": card["title"] or card["asin"],
                    "image_url": card["image_url"],
                },
                dont_filter=True,
            )

    async def parse_product_detail(
        self,
        response: scrapy.http.Response,
        asin: str,
        title_hint: str,
        image_url: str | None,
    ):
        page = response.meta.get("playwright_page")
        offers_page = None
        try:
            if response.status >= 400:
                self.capture_response_failure(
                    "detail-http-error",
                    response,
                    asin=asin,
                    query=self.crawl_label,
                    location_code=self.location_profile.code,
                )
                return

            if page is None:
                self.logger.warning("detail-page-missing-playwright-page asin=%s url=%s", asin, response.url)
                return

            await page.wait_for_load_state("domcontentloaded")
            await self.ensure_location(page)

            detail_html = await self.safe_page_content(page)
            detail_selector = scrapy.Selector(text=detail_html)
            metadata = self.extract_product_metadata(detail_selector, title_hint)
            product_url = page.url

            offers_url = f"{self.base_url}/gp/offer-listing/{asin}/ref=dp_olp_NEW_mbc?ie=UTF8&condition=NEW"
            offers_page = await page.context.new_page()
            offers_response = await self.goto_with_retries(offers_page, offers_url)
            await self.ensure_location(offers_page)
            await self.wait_for_offer_page_ready(offers_page)
            offers_html = await self.safe_page_content(offers_page)
            offers_selector = scrapy.Selector(text=offers_html)
            offers_status = offers_response.status if offers_response is not None else None
            metadata = self.merge_offer_page_metadata(metadata, offers_selector, title_hint)

            if offers_status is not None and offers_status >= 400:
                await self.capture_page_failure(
                    "offers-http-error",
                    offers_page,
                    body_text=offers_html,
                    asin=asin,
                    query=self.crawl_label,
                    location_code=self.location_profile.code,
                    status=offers_status,
                    offers_url=offers_url,
                )
                return

            offers = self.extract_offer_cards(offers_selector, metadata["buy_box_seller"])

            if not offers and metadata["buy_box_seller"] and metadata["buy_box_price"] is not None:
                offers = [
                    {
                        "seller_name": metadata["buy_box_seller"],
                        "price": metadata["buy_box_price"],
                        "list_price": None,
                        "shipping_price": None,
                        "availability": "Unknown",
                        "fba_status": False,
                        "buy_box_flag": True,
                        "is_prime": False,
                        "offer_url": product_url,
                        "raw_payload": {"source": "detail-page-fallback"},
                    }
                ]

            if not offers:
                await self.capture_page_failure(
                    "offers-empty-results",
                    offers_page,
                    body_text=offers_html,
                    asin=asin,
                    query=self.crawl_label,
                    location_code=self.location_profile.code,
                    offers_url=offers_url,
                    buy_box_seller=metadata["buy_box_seller"],
                )
                return

            yield {
                "asin": asin,
                "title": metadata["title"],
                "brand": metadata["brand"],
                "query": self.crawl_label,
                "image_url": image_url,
                "product_url": product_url,
                "location_code": self.location_profile.code,
                "buyer_pin_code": self.location_profile.pin_code,
                "offers": offers,
            }
        except Exception as exc:  # noqa: BLE001
            target_page = offers_page or page
            if target_page is not None:
                await self.capture_page_failure(
                    "detail-exception",
                    target_page,
                    asin=asin,
                    query=self.crawl_label,
                    location_code=self.location_profile.code,
                    error=repr(exc),
                )
            self.logger.exception("detail-page-error asin=%s url=%s error=%s", asin, response.url, repr(exc))
        finally:
            if offers_page is not None:
                await offers_page.close()
            if page is not None:
                await page.close()

    async def ensure_location(self, page) -> None:
        if await self.location_is_applied(page):
            return
        await self.apply_location(page)

    async def apply_location(self, page) -> None:
        try:
            trigger = page.locator("#contextualIngressPtLabel")
            if await trigger.count() == 0:
                return
            await trigger.first.click(timeout=4_000, force=True)
            zip_input = page.locator("#GLUXZipUpdateInput")
            if await zip_input.count() == 0:
                return
            await zip_input.fill(self.location_profile.pin_code)
            await page.locator("#GLUXZipUpdate").click(force=True)
            await page.wait_for_timeout(1_500)
            done_button = page.locator("input.a-button-input, button[name='glowDoneButton']")
            if await done_button.count():
                await done_button.first.click(timeout=2_000, force=True)
            await page.wait_for_timeout(1_000)
        except Exception as exc:  # noqa: BLE001
            self.logger.info(
                "location_simulation_best_effort code=%s error=%s",
                self.location_profile.code,
                repr(exc),
            )

    async def location_is_applied(self, page) -> bool:
        try:
            trigger = page.locator("#contextualIngressPtLabel")
            if await trigger.count() == 0:
                return False
            label = clean_text(await trigger.first.text_content())
            if not label:
                return False
            return self.location_label_matches(label)
        except Exception:  # noqa: BLE001
            return False

    def location_label_matches(self, label: str) -> bool:
        normalized = clean_text(label)
        if not normalized:
            return False
        lowered = normalized.casefold()
        return any(
            token.casefold() in lowered
            for token in [
                self.location_profile.pin_code,
                self.location_profile.city,
                self.location_profile.state,
            ]
        )

    async def goto_with_retries(self, page, url: str):
        last_error: Exception | None = None
        for attempt in range(1, self.CONTENT_RETRY_COUNT + 1):
            try:
                response = await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=self.OFFER_PAGE_TIMEOUT_MS,
                )
                await page.wait_for_timeout(1_200)
                return response
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                self.logger.info(
                    "offer_page_navigation_retry asin=%s attempt=%s url=%s error=%s",
                    self.target_asin,
                    attempt,
                    url,
                    repr(exc),
                )
                await page.wait_for_timeout(1_000 * attempt)
        if last_error is not None:
            raise last_error
        raise RuntimeError(f"Unable to navigate to {url}")

    async def wait_for_offer_page_ready(self, page) -> None:
        selectors = [
            "#aod-pinned-offer",
            "#aod-offer-list",
            "#all-offers-display-scroller",
            "#exports_desktop_qualifiedBuybox_atf_feature_div",
            "#availability",
            "#outOfStock",
        ]
        for selector in selectors:
            try:
                await page.wait_for_selector(selector, timeout=self.OFFER_PAGE_READY_TIMEOUT_MS)
                return
            except Exception:  # noqa: BLE001
                continue

    async def safe_page_content(self, page) -> str:
        last_error: Exception | None = None
        for attempt in range(1, self.CONTENT_RETRY_COUNT + 1):
            try:
                if attempt > 1:
                    await page.wait_for_timeout(500 * attempt)
                return await page.content()
            except Exception as exc:  # noqa: BLE001
                last_error = exc
        if last_error is not None:
            raise last_error
        raise RuntimeError("Unable to read page content")

    def extract_search_cards(self, selector: scrapy.Selector) -> list[dict[str, str | None]]:
        cards: list[dict[str, str | None]] = []
        for card in selector.css(
            "[data-component-type='s-search-result'][data-asin], " "div.s-result-item.s-asin[data-asin]"
        ):
            asin = clean_text(card.attrib.get("data-asin"))
            href = self.extract_search_card_href(card, asin)
            if not asin or not href:
                continue
            cards.append(
                {
                    "asin": asin,
                    "title": self.extract_search_card_title(card, asin),
                    "href": href,
                    "image_url": extract_first(card, ["img.s-image::attr(src)", "img::attr(src)"]),
                }
            )
        return cards

    def extract_search_card_href(self, card: scrapy.Selector, asin: str | None) -> str | None:
        href_candidates = card.css(
            "h2 a::attr(href), "
            "a.s-link-style::attr(href), "
            "a[href*='/dp/']::attr(href), "
            "a[href*='/gp/product/']::attr(href)"
        ).getall()
        href_candidates = [href for href in href_candidates if href and "#customerReviews" not in href]

        if asin:
            for href in href_candidates:
                if asin.casefold() in href.casefold():
                    return self.normalize_product_href(href, asin)

        for href in href_candidates:
            normalized = self.normalize_product_href(href, asin)
            if normalized:
                return normalized
        return None

    def extract_search_card_title(self, card: scrapy.Selector, asin: str) -> str:
        title_candidates = [
            clean_text(value)
            for value in card.css(
                "h2 a span::text, "
                "a h2 span::text, "
                "h2::attr(aria-label), "
                "h2 span::text, "
                "[data-cy='title-recipe'] span::text"
            ).getall()
        ]
        title_candidates = [value for value in title_candidates if value and value.casefold() != asin.casefold()]
        if title_candidates:
            return max(title_candidates, key=len)
        return asin

    @staticmethod
    def normalize_product_href(href: str | None, asin: str | None = None) -> str | None:
        if not href:
            return None

        match = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", href, re.IGNORECASE)
        if match:
            return f"/dp/{match.group(1).upper()}"

        if asin:
            return f"/dp/{asin}"
        return href

    def extract_product_metadata(self, selector: scrapy.Selector, title_hint: str) -> dict[str, Any]:
        return {
            "title": extract_first(selector, ["#productTitle::text", "title::text"]) or title_hint,
            "brand": extract_first(selector, ["#bylineInfo::text"]),
            "buy_box_seller": extract_first(
                selector,
                [
                    "#merchant-info a::text",
                    "#desktop_qualifiedBuyBox #merchantInfoFeature_feature_div a::text",
                    "#tabular-buybox .tabular-buybox-text a::text",
                ],
            ),
            "buy_box_price": parse_price(
                extract_first(
                    selector,
                    [
                        ".a-price .a-offscreen::text",
                        "#corePrice_feature_div .a-price-whole::text",
                    ],
                )
            ),
        }

    def merge_offer_page_metadata(
        self,
        metadata: dict[str, Any],
        offers_selector: scrapy.Selector,
        title_hint: str,
    ) -> dict[str, Any]:
        merged = dict(metadata)
        offer_page_title = extract_first(
            offers_selector,
            [
                "input#productTitle::attr(value)",
                "input[name='productTitle']::attr(value)",
                "#aod-asin-title-text::text",
                "meta[property='og:title']::attr(content)",
                "title::text",
            ],
        )
        if looks_invalid_product_title(merged.get("title")):
            merged["title"] = offer_page_title or title_hint
        if not merged.get("brand"):
            merged["brand"] = extract_first(
                offers_selector,
                [
                    "#brand::text",
                    "a#bylineInfo::text",
                    "input[name='brand']::attr(value)",
                ],
            )
        if not merged.get("buy_box_seller"):
            merged["buy_box_seller"] = extract_first(
                offers_selector,
                [
                    "#aod-pinned-offer #aod-offer-soldBy a::text",
                    "#aod-pinned-offer #sellerProfileTriggerId::text",
                ],
            )
        if merged.get("buy_box_price") is None:
            merged["buy_box_price"] = parse_price(
                extract_first(
                    offers_selector,
                    [
                        "#aod-pinned-offer .apex-pricetopay-value .a-offscreen::text",
                        "#aod-pinned-offer .a-price .a-offscreen::text",
                    ],
                )
            )
        return merged

    def extract_offer_cards(self, selector: scrapy.Selector, buy_box_seller: str | None) -> list[dict[str, Any]]:
        cards = selector.css("#aod-pinned-offer, #aod-offer, div.aod-offer")
        offers: list[dict[str, Any]] = []
        seen_offer_keys: set[tuple[str, float]] = set()

        for card in cards:
            seller_name = extract_first(
                card,
                [
                    "#aod-offer-soldBy a::text",
                    ".aod-offer-soldBy a::text",
                    "#sellerProfileTriggerId::text",
                    "[id*='aod-offer-soldBy'] a::text",
                    ".a-fixed-left-grid-col.a-col-right .a-size-small.a-link-normal::text",
                ],
            ) or extract_joined(
                card,
                [
                    "#aod-offer-soldBy ::text",
                    "[id*='aod-offer-soldBy'] ::text",
                ],
            )
            price = parse_price(
                extract_first(
                    card,
                    [
                        ".apex-pricetopay-value .a-offscreen::text",
                        ".a-price .a-offscreen::text",
                        ".a-price-whole::text",
                    ],
                )
            )
            if not seller_name or price is None:
                continue

            offer_url = card.css(
                "a[href*='/gp/offer-listing/']::attr(href), a[href*='/offer-listing/']::attr(href)"
            ).get()
            if offer_url:
                offer_url = response_urljoin(self.base_url, offer_url)

            sold_by_link = card.css(
                "#aod-offer-soldBy a::attr(href), "
                ".aod-offer-soldBy a::attr(href), "
                "#sellerProfileTriggerId::attr(href)"
            ).get()
            seller_id = self.extract_seller_id(sold_by_link)
            condition_text = extract_first(
                card,
                ["#aod-offer-heading .a-text-bold::text", "#aod-offer-heading span::text"],
            )
            delivery_text = join_clean_text(card.css(".aod-delivery-promise ::text").getall())
            ship_from_text = join_clean_text(card.css("#aod-offer-shipsFrom .a-color-base::text").getall())
            secondary_text = join_clean_text(card.css(".a-color-secondary .a-size-base::text").getall())
            availability_bits = [bit for bit in [condition_text, delivery_text or secondary_text] if bit]
            if ship_from_text and not any(ship_from_text.casefold() in bit.casefold() for bit in availability_bits):
                availability_bits.append(f"Ships from {ship_from_text}")
            availability_text = " | ".join(availability_bits) or None
            shipping_price = parse_price(
                extract_first(
                    card,
                    [
                        ".aod-delivery-promise [data-csa-c-delivery-price]::attr(data-csa-c-delivery-price)",
                        ".aod-ship-charge .a-price .a-offscreen::text",
                        ".a-color-secondary .a-size-base::text",
                    ],
                )
            )
            is_pinned_offer = bool(card.css("#pinned-de-id, #aod-pinned-offer, .pinned-offer-block"))
            offer_key = ((seller_id or seller_name.casefold()), price)
            if offer_key in seen_offer_keys:
                continue
            seen_offer_keys.add(offer_key)

            offers.append(
                {
                    "seller_id": seller_id,
                    "seller_name": seller_name,
                    "price": price,
                    "list_price": parse_price(
                        extract_first(
                            card,
                            [
                                ".apex-basisprice-value .a-offscreen::text",
                                ".basisPrice .a-offscreen::text",
                                ".a-price.a-text-price .a-offscreen::text",
                            ],
                        )
                    ),
                    "shipping_price": shipping_price,
                    "availability": availability_text,
                    "fba_status": bool(
                        (availability_text or sold_by_link or "")
                        and any(
                            token in (availability_text or sold_by_link or "").casefold()
                            for token in [
                                "fulfilled by amazon",
                                "ships from amazon",
                                "delivered by amazon",
                                "isamazonfulfilled=1",
                            ]
                        )
                    ),
                    "buy_box_flag": bool(
                        is_pinned_offer or (buy_box_seller and seller_name.casefold() == buy_box_seller.casefold())
                    ),
                    "is_prime": bool(card.css(".a-icon-prime, .a-icon-prime-mini"))
                    or bool(availability_text and "prime" in availability_text.casefold()),
                    "offer_url": offer_url,
                    "raw_payload": {
                        "condition": condition_text,
                        "delivery": delivery_text,
                        "secondary_text": secondary_text,
                        "ship_from": ship_from_text,
                        "excerpt": availability_text,
                    },
                }
            )

        return offers

    def capture_response_failure(self, label: str, response: scrapy.http.Response, **extra: Any) -> Path | None:
        artifact = self.artifacts.capture_response_artifact(label, response, extra=extra)
        self.logger.warning(
            "%s url=%s status=%s location=%s artifact=%s",
            label,
            response.url,
            response.status,
            self.location_profile.code,
            artifact,
        )
        return artifact

    async def capture_page_failure(self, label: str, page, body_text: str | None = None, **extra: Any) -> Path | None:
        screenshot_bytes = None
        if body_text is None:
            try:
                body_text = await page.content()
            except Exception:  # noqa: BLE001
                body_text = None
        try:
            screenshot_bytes = await page.screenshot(type="png", full_page=True)
        except Exception:  # noqa: BLE001
            screenshot_bytes = None

        artifact = self.artifacts.capture_page_artifact(
            label=label,
            url=page.url,
            body_text=body_text,
            extra=extra,
            screenshot_bytes=screenshot_bytes,
        )
        self.logger.warning(
            "%s url=%s location=%s artifact=%s",
            label,
            page.url,
            self.location_profile.code,
            artifact,
        )
        return artifact

    @staticmethod
    def extract_seller_id(href: str | None) -> str | None:
        if not href:
            return None
        match = re.search(r"(?:seller=|smid=)([A-Z0-9]+)", href, re.IGNORECASE)
        if match:
            return match.group(1)
        parsed = urlparse(href)
        return parsed.path.rsplit("/", 1)[-1] or None


def response_urljoin(base_url: str, href: str) -> str:
    return urljoin(f"{base_url.rstrip('/')}/", href)
