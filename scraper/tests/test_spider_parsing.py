from __future__ import annotations

import json
from pathlib import Path

import scrapy
from scrapy.http import HtmlResponse, Request

from scraper.amazon_monitor.runner import build_parser, default_artifact_dir
from scraper.amazon_monitor.spiders.amazon_bearings import AmazonBearingsSpider, FailureArtifactStore

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def build_spider(**kwargs) -> AmazonBearingsSpider:
    return AmazonBearingsSpider(query="SKF bearing 6205", location_code="chennai-tn", **kwargs)


def test_extract_search_cards_from_fixture() -> None:
    spider = build_spider()
    selector = scrapy.Selector(text=load_fixture("search_results.html"))

    cards = spider.extract_search_cards(selector)

    assert cards == [
        {
            "asin": "B0SKF6205X",
            "title": "SKF 6205 Deep Groove Ball Bearing",
            "href": "/dp/B0SKF6205X",
            "image_url": "https://images.example.com/6205.jpg",
        },
        {
            "asin": "B0SKF6305Y",
            "title": "SKF 6305 Deep Groove Ball Bearing",
            "href": "/dp/B0SKF6305Y",
            "image_url": "https://images.example.com/6305.jpg",
        },
    ]


def test_extract_search_cards_from_current_amazon_layout() -> None:
    spider = build_spider()
    selector = scrapy.Selector(text="""
        <html>
          <body>
            <div
              role="listitem"
              data-asin="B07H1GJZMP"
              data-component-type="s-search-result"
              class="s-result-item s-asin"
            >
              <div data-cy="image-container">
                <a
                  class="a-link-normal s-no-outline"
                  href="/SKF-6205-2Z-Groove-Bearing-Silver/dp/B07H1GJZMP/ref=sr_1_1?dib=abc&sr=8-1"
                >
                  <img class="s-image" src="https://m.media-amazon.com/images/I/51sBl+RaGcL._AC_UL320_.jpg" />
                </a>
              </div>
              <div data-cy="title-recipe">
                <div class="a-row a-color-secondary">
                  <h2 class="a-size-mini s-line-clamp-1"><span class="a-size-base-plus a-color-base">SKF</span></h2>
                </div>
                <a
                  class="a-link-normal s-line-clamp-4 s-link-style a-text-normal"
                  href="/SKF-6205-2Z-Groove-Bearing-Silver/dp/B07H1GJZMP/ref=sr_1_1?dib=abc&sr=8-1"
                >
                  <h2
                    aria-label="6205-2Z Deep Groove Ball Bearing (Silver)"
                    class="a-size-base-plus a-spacing-none a-color-base a-text-normal"
                  >
                    <span>6205-2Z Deep Groove Ball Bearing (Silver)</span>
                  </h2>
                </a>
              </div>
            </div>
          </body>
        </html>
        """)

    cards = spider.extract_search_cards(selector)

    assert cards == [
        {
            "asin": "B07H1GJZMP",
            "title": "6205-2Z Deep Groove Ball Bearing (Silver)",
            "href": "/dp/B07H1GJZMP",
            "image_url": "https://m.media-amazon.com/images/I/51sBl+RaGcL._AC_UL320_.jpg",
        }
    ]


def test_extract_product_metadata_from_fixture() -> None:
    spider = build_spider()
    selector = scrapy.Selector(text=load_fixture("product_detail.html"))

    metadata = spider.extract_product_metadata(selector, title_hint="fallback title")

    assert metadata == {
        "title": "SKF 6205 Deep Groove Ball Bearing",
        "brand": "Visit the SKF Store",
        "buy_box_seller": "Bearing Hub Chennai",
        "buy_box_price": 995.0,
    }


def test_extract_offer_cards_from_fixture() -> None:
    spider = build_spider()
    selector = scrapy.Selector(text=load_fixture("offer_listing.html"))

    offers = spider.extract_offer_cards(selector, buy_box_seller="Bearing Hub Chennai")

    assert len(offers) == 2
    assert offers[0]["seller_id"] == "COMPETA1"
    assert offers[0]["seller_name"] == "Bearing Hub Chennai"
    assert offers[0]["price"] == 995.0
    assert offers[0]["buy_box_flag"] is True
    assert offers[0]["fba_status"] is True
    assert offers[0]["is_prime"] is True
    assert offers[0]["offer_url"] == "https://www.amazon.in/gp/offer-listing/B0SKF6205X?smid=COMPETA1"
    assert offers[1]["seller_id"] == "COMPETB2"
    assert offers[1]["buy_box_flag"] is False
    assert offers[1]["shipping_price"] == 40.0


def test_extract_offer_cards_from_current_amazon_layout() -> None:
    spider = build_spider()
    selector = scrapy.Selector(text="""
        <html>
          <body>
            <div id="aod-pinned-offer">
              <div id="pinned-de-id" class="pinned-offer-block">
                <div id="aod-offer-heading"><span class="a-text-bold">New</span></div>
                <span class="apex-pricetopay-value">
                  <span class="a-offscreen">₹639.00</span>
                </span>
                <span class="apex-basisprice-value">
                  <span class="a-offscreen">₹680.00</span>
                </span>
                <div class="aod-delivery-promise">
                  <span data-csa-c-delivery-price="₹76">
                    ₹76 delivery <span class="a-text-bold">Sunday, 5 April</span>
                  </span>
                </div>
                <div id="aod-offer-shipsFrom"><span class="a-size-small a-color-base">Amazon</span></div>
                <div id="aod-offer-soldBy">
                  <a href="/gp/help/seller/at-a-glance.html?seller=A2MPD1EA7SJGR6">
                    HEERA SPRING &amp; MILL STORE
                  </a>
                </div>
              </div>
            </div>
            <div id="aod-offer">
              <div id="aod-offer-heading"><span class="a-text-bold">New</span></div>
              <span class="a-price"><span class="a-offscreen">₹639.00</span></span>
              <div class="aod-delivery-promise">
                <span data-csa-c-delivery-price="₹200">₹200 delivery Tuesday, 7 April</span>
              </div>
              <div id="aod-offer-shipsFrom"><span class="a-size-small a-color-base">Shivneri Auto Parts</span></div>
              <div id="aod-offer-soldBy">
                <a href="/gp/aag/main?ie=UTF8&amp;seller=A1ZSO9HD215305">Shivneri Auto Parts</a>
              </div>
            </div>
          </body>
        </html>
        """)

    offers = spider.extract_offer_cards(selector, buy_box_seller="HEERA SPRING & MILL STORE")

    assert len(offers) == 2
    assert offers[0]["seller_id"] == "A2MPD1EA7SJGR6"
    assert offers[0]["seller_name"] == "HEERA SPRING & MILL STORE"
    assert offers[0]["buy_box_flag"] is True
    assert offers[0]["fba_status"] is True
    assert offers[0]["shipping_price"] == 76.0
    assert offers[0]["availability"] == "New | ₹76 delivery Sunday, 5 April | Ships from Amazon"
    assert offers[1]["seller_id"] == "A1ZSO9HD215305"
    assert offers[1]["buy_box_flag"] is False
    assert offers[1]["shipping_price"] == 200.0


def test_extract_offer_cards_when_seller_name_is_plain_text() -> None:
    spider = build_spider()
    selector = scrapy.Selector(text="""
        <html>
          <body>
            <div id="aod-pinned-offer">
              <div id="aod-offer-heading"><span class="a-text-bold">New</span></div>
              <span class="a-price"><span class="a-offscreen">₹799.00</span></span>
              <div id="aod-offer-soldBy">
                <span class="a-size-small a-color-base">Industrial Seller Direct</span>
              </div>
            </div>
          </body>
        </html>
        """)

    offers = spider.extract_offer_cards(selector, buy_box_seller="Industrial Seller Direct")

    assert len(offers) == 1
    assert offers[0]["seller_name"] == "Industrial Seller Direct"
    assert offers[0]["price"] == 799.0
    assert offers[0]["buy_box_flag"] is True


def test_failure_artifact_store_writes_metadata_and_html(tmp_path: Path) -> None:
    body = load_fixture("search_results.html")
    response = HtmlResponse(
        url="https://www.amazon.in/s?k=SKF+bearing+6205&page=1",
        body=body.encode("utf-8"),
        encoding="utf-8",
        request=Request(url="https://www.amazon.in/s?k=SKF+bearing+6205&page=1"),
    )
    store = FailureArtifactStore(str(tmp_path))

    artifact_path = store.capture_response_artifact(
        "search-empty-results",
        response,
        extra={"query": "SKF bearing 6205", "location_code": "chennai-tn"},
    )

    assert artifact_path is not None
    metadata = json.loads(artifact_path.with_suffix(".json").read_text(encoding="utf-8"))
    assert metadata["label"] == "search-empty-results"
    assert metadata["location_code"] == "chennai-tn"
    assert artifact_path.with_suffix(".html").exists()


def test_runner_supports_asin_command() -> None:
    args = build_parser().parse_args(["asin", "--asin", "B0SKF6205X", "--location-code", "chennai-tn", "--dry-run"])

    assert args.command == "asin"
    assert args.asin == "B0SKF6205X"
    assert args.location_code == "chennai-tn"
    assert args.artifact_dir == default_artifact_dir()
    assert args.dry_run is True
