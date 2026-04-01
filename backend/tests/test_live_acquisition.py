from __future__ import annotations

import pytest

from backend.app.services.live_acquisition import extract_amazon_asin


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("B07H1GJZMP", "B07H1GJZMP"),
        ("https://www.amazon.in/dp/B07H1GJZMP", "B07H1GJZMP"),
        ("https://www.amazon.in/SKF-Bearing/dp/B07H1GJZMP/ref=sr_1_1", "B07H1GJZMP"),
        ("https://www.amazon.in/gp/product/B07H1GJZMP?psc=1", "B07H1GJZMP"),
        ("https://www.amazon.in/gp/offer-listing/B07H1GJZMP/ref=dp_olp_NEW_mbc", "B07H1GJZMP"),
        ("https://www.amazon.in/s?k=skf&pd_rd_i=B07H1GJZMP", "B07H1GJZMP"),
        ("Check this bearing https://www.amazon.in/dp/B07H1GJZMP/?tag=test", "B07H1GJZMP"),
        ("https%3A%2F%2Fwww.amazon.in%2Fdp%2FB07H1GJZMP%3Fpsc%3D1", "B07H1GJZMP"),
        ("not-an-amazon-link", None),
    ],
)
def test_extract_amazon_asin(value: str, expected: str | None) -> None:
    assert extract_amazon_asin(value) == expected
