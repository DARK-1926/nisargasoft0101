from __future__ import annotations

from backend.app.services.product_filters import validate_product


def test_validate_product_rejects_invalid_title() -> None:
    result = validate_product("Page Not Found", None, "SKF bearing 6205")
    assert result.is_valid is False
    assert result.is_bearing is False


def test_validate_product_accepts_bearing_title() -> None:
    result = validate_product(
        "6201 ZZ Deep Groove Ball Bearing, Double Metal Shielded, 12x32x10mm, Pack of 10",
        "Brand: Generic",
        "SKF bearing 6201",
    )
    assert result.is_valid is True
    assert result.is_bearing is True


def test_validate_product_rejects_non_bearing_product() -> None:
    result = validate_product(
        "Samsung Galaxy S26 Ultra 5G",
        "Visit the Samsung Store",
        "SKF bearing 6205",
    )
    assert result.is_valid is True
    assert result.is_bearing is False
