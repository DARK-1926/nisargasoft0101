from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from backend.app.db import Base

json_type = JSON().with_variant(JSONB, "postgresql")


class Product(Base):
    __tablename__ = "products"

    asin: Mapped[str] = mapped_column(String(20), primary_key=True)
    title: Mapped[str] = mapped_column(String(512))
    brand: Mapped[str | None] = mapped_column(String(128))
    query: Mapped[str | None] = mapped_column(String(256))
    image_url: Mapped[str | None] = mapped_column(String(1024))
    product_url: Mapped[str | None] = mapped_column(String(1024))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    offers: Mapped[list["Offer"]] = relationship(back_populates="product")
    watchlist_items: Mapped[list["WatchlistItem"]] = relationship(back_populates="product")


class Seller(Base):
    __tablename__ = "sellers"

    seller_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(256))
    marketplace: Mapped[str] = mapped_column(String(32), default="amazon.in")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    offers: Mapped[list["Offer"]] = relationship(back_populates="seller")


class Offer(Base):
    __tablename__ = "offers"
    __table_args__ = (
        Index("ix_offers_asin_location_ts", "asin", "buyer_location_code", "captured_at"),
        Index("ix_offers_seller_ts", "seller_id", "captured_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    asin: Mapped[str] = mapped_column(ForeignKey("products.asin"), nullable=False)
    seller_id: Mapped[str] = mapped_column(ForeignKey("sellers.seller_id"), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    list_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    shipping_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    availability: Mapped[str | None] = mapped_column(Text)
    fba_status: Mapped[bool] = mapped_column(Boolean, default=False)
    buy_box_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    is_prime: Mapped[bool] = mapped_column(Boolean, default=False)
    buyer_location_code: Mapped[str] = mapped_column(String(64), nullable=False)
    buyer_pin_code: Mapped[str | None] = mapped_column(String(16))
    offer_url: Mapped[str | None] = mapped_column(String(1024))
    raw_payload: Mapped[dict] = mapped_column(json_type, default=dict)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, server_default=func.now(), nullable=False
    )

    product: Mapped[Product] = relationship(back_populates="offers")
    seller: Mapped[Seller] = relationship(back_populates="offers")


class AlertEvent(Base):
    __tablename__ = "alert_events"
    __table_args__ = (Index("ix_alert_events_asin_location_created", "asin", "location_code", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    asin: Mapped[str] = mapped_column(String(20), nullable=False)
    product_title: Mapped[str] = mapped_column(String(512))
    location_code: Mapped[str] = mapped_column(String(64), nullable=False)
    competitor_seller_id: Mapped[str] = mapped_column(String(128), nullable=False)
    competitor_seller_name: Mapped[str] = mapped_column(String(256), nullable=False)
    own_seller_id: Mapped[str] = mapped_column(String(128), nullable=False)
    own_seller_name: Mapped[str] = mapped_column(String(256), nullable=False)
    competitor_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    own_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    delta_percent: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    slack_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    email_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"
    __table_args__ = (
        Index("ix_watchlist_location_active", "location_code", "active"),
        Index("ix_watchlist_asin_location", "asin", "location_code", unique=True),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    asin: Mapped[str] = mapped_column(ForeignKey("products.asin"), nullable=False)
    location_code: Mapped[str] = mapped_column(String(64), nullable=False)
    source_query: Mapped[str | None] = mapped_column(String(256))
    brand_filter: Mapped[str | None] = mapped_column(String(64))
    model_filter: Mapped[str | None] = mapped_column(String(64))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    product: Mapped[Product] = relationship(back_populates="watchlist_items")
