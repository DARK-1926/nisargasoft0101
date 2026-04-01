from __future__ import annotations

from dataclasses import dataclass


INVALID_TITLE_MARKERS = {
    "page not found",
    "amazon.in",
    "amazon.in: page not found",
    "amazon.in page not found",
}

BEARING_KEYWORDS = (
    "bearing",
    "deep groove",
    "ball bearing",
    "roller bearing",
    "taper bearing",
    "pillow block",
    "ucp",
    "ucf",
    "ucfl",
)

BEARING_BRANDS = (
    "skf",
    "nsk",
    "ntn",
    "fag",
    "koyo",
    "timken",
    "nachi",
    "ina",
    "nbc",
    "zkl",
)


@dataclass(frozen=True, slots=True)
class ProductValidation:
    is_valid: bool
    is_bearing: bool
    reason: str | None = None


def normalize_text(value: str | None) -> str:
    return " ".join((value or "").split()).strip().casefold()


def validate_product(title: str | None, brand: str | None = None, query: str | None = None) -> ProductValidation:
    normalized_title = normalize_text(title)
    normalized_brand = normalize_text(brand)
    normalized_query = normalize_text(query)

    if not normalized_title:
        return ProductValidation(is_valid=False, is_bearing=False, reason="missing_title")

    if normalized_title in INVALID_TITLE_MARKERS:
        return ProductValidation(is_valid=False, is_bearing=False, reason="invalid_title")

    if any(keyword in normalized_title for keyword in BEARING_KEYWORDS):
        return ProductValidation(is_valid=True, is_bearing=True)

    if any(brand_token in normalized_brand for brand_token in BEARING_BRANDS) and "bearing" in normalized_query:
        return ProductValidation(is_valid=True, is_bearing=True)

    bearing_series_tokens = (
        "620",
        "621",
        "622",
        "623",
        "624",
        "625",
        "626",
        "627",
        "628",
        "629",
        "630",
        "631",
        "632",
        "633",
        "634",
    )
    if "bearing" in normalized_query and any(token in normalized_title for token in bearing_series_tokens):
        return ProductValidation(is_valid=True, is_bearing=True)

    return ProductValidation(is_valid=True, is_bearing=False, reason="not_bearing")


def matches_tracking_filters(
    title: str | None,
    brand: str | None = None,
    *,
    brand_filter: str | None = None,
    model_filter: str | None = None,
) -> bool:
    normalized_title = normalize_text(title)
    normalized_brand = normalize_text(brand)
    normalized_brand_filter = normalize_text(brand_filter)
    normalized_model_filter = normalize_text(model_filter)

    brand_matches = (
        not normalized_brand_filter
        or normalized_brand_filter in normalized_brand
        or normalized_brand_filter in normalized_title
    )
    if not brand_matches:
        return False

    if normalized_model_filter and normalized_model_filter not in normalized_title:
        return False

    return True
