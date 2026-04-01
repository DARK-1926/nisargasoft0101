from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SellerOfferIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    seller_id: str | None = None
    seller_name: str
    price: Decimal
    list_price: Decimal | None = None
    shipping_price: Decimal | None = None
    availability: str | None = None
    fba_status: bool = False
    buy_box_flag: bool = False
    is_prime: bool = False
    offer_url: str | None = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class IngestSnapshotIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    asin: str
    title: str
    brand: str | None = None
    query: str | None = None
    image_url: str | None = None
    product_url: str | None = None
    location_code: str
    buyer_pin_code: str | None = None
    captured_at: datetime | None = None
    offers: list[SellerOfferIn]


class ProductSummaryOut(BaseModel):
    asin: str
    title: str
    brand: str | None
    last_seen_at: datetime | None
    available_locations: list[str]


class TrackUrlIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    url: str
    location_code: str
    title_hint: str | None = None


class DiscoverProductsIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    query: str
    location_code: str
    max_pages: int = Field(default=1, ge=1, le=5)
    brand_filter: str | None = None
    model_filter: str | None = None


class TrackUrlOut(BaseModel):
    asin: str
    location_code: str
    product: ProductSummaryOut
    snapshot: "CurrentAsinOut"


class DiscoverProductsOut(BaseModel):
    query: str
    location_code: str
    brand_filter: str | None = None
    model_filter: str | None = None
    tracked_count: int
    products: list[ProductSummaryOut]


class WatchlistItemIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    asin: str
    title: str | None = None
    brand: str | None = None
    location_code: str
    source_query: str | None = None
    brand_filter: str | None = None
    model_filter: str | None = None


class WatchlistItemOut(BaseModel):
    id: str
    asin: str
    title: str
    brand: str | None
    location_code: str
    source_query: str | None
    brand_filter: str | None
    model_filter: str | None
    last_seen_at: datetime | None
    created_at: datetime


class LocationProfileOut(BaseModel):
    code: str
    city: str
    state: str
    pin_code: str


class CurrentOfferOut(BaseModel):
    seller_id: str
    seller_name: str
    price: float
    list_price: float | None
    shipping_price: float | None
    availability: str | None
    fba_status: bool
    buy_box_flag: bool
    is_prime: bool
    offer_url: str | None
    captured_at: datetime


class CurrentAsinOut(BaseModel):
    asin: str
    title: str
    location_code: str
    captured_at: datetime | None
    buy_box_offer: CurrentOfferOut | None
    offers: list[CurrentOfferOut]


class HistoryPointOut(BaseModel):
    captured_at: datetime
    price: float
    buy_box_flag: bool


class HistorySeriesOut(BaseModel):
    seller_id: str
    seller_name: str
    points: list[HistoryPointOut]


class HistoryOut(BaseModel):
    asin: str
    location_code: str
    hours: int
    series: list[HistorySeriesOut]


class SellerInsightOut(BaseModel):
    seller_id: str
    seller_name: str
    min_price: float
    max_price: float
    avg_price: float
    latest_price: float
    price_change_count: int
    buy_box_wins: int
    leadership_wins: int


class MarketInsightOut(BaseModel):
    asin: str
    title: str
    location_code: str
    hours: int
    snapshot_count: int
    seller_count: int
    captured_from: datetime | None
    captured_to: datetime | None
    current_lowest_price: float | None
    current_lowest_seller: str | None
    buy_box_seller: str | None
    highest_price_seen: float | None
    lowest_price_seen: float | None
    seller_insights: list[SellerInsightOut]


class AlertEventOut(BaseModel):
    id: str
    asin: str
    product_title: str
    location_code: str
    competitor_seller_name: str
    own_seller_name: str
    competitor_price: float
    own_price: float
    delta_percent: float
    message: str
    slack_sent: bool
    email_sent: bool
    created_at: datetime


class IngestResultOut(BaseModel):
    asin: str
    offers_ingested: int
    alerts_created: int


TrackUrlOut.model_rebuild()
