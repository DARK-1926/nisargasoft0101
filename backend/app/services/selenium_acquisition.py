"""Integration layer for hybrid scraper."""
from __future__ import annotations

import httpx
from backend.app.services.hybrid_scraper import HybridAmazonScraper


async def hybrid_scrape_and_ingest(
    asin: str,
    location_code: str,
    api_base_url: str,
) -> dict:
    """Scrape using hybrid method and ingest to API."""
    
    scraper = HybridAmazonScraper(headless=True)
    try:
        offers = await scraper.scrape_offers(asin, location_code)
    finally:
        scraper.close()
    
    if not offers:
        raise Exception(f"No offers found for ASIN {asin}")
    
    # Prepare payload for ingestion
    payload = {
        "asin": asin,
        "location_code": location_code,
        "scraped_at": None,  # Will be set by API
        "offers": [
            {
                "seller_name": offer.seller_name,
                "price": offer.price,
                "condition": offer.condition,
                "availability": offer.availability,
                "shipping_price": offer.shipping_price,
            }
            for offer in offers
        ]
    }
    
    # Ingest to API
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{api_base_url}/api/ingest",
            json=payload,
        )
        response.raise_for_status()
        result = response.json()
    
    return {
        "offers_scraped": len(offers),
        "offers_ingested": result.get("offers_ingested", 0),
    }
