#!/usr/bin/env python3
"""Test if Playwright can access Amazon and extract offers."""
import asyncio
from playwright.async_api import async_playwright


async def test_amazon_access():
    """Test basic Amazon access and offer extraction."""
    # Test with a popular, available product (iPhone 15)
    asin = "B0CHX1W1XY"
    url = f"https://www.amazon.in/dp/{asin}"
    
    async with async_playwright() as p:
        print("Launching browser...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            locale="en-IN",
        )
        page = await context.new_page()
        
        print(f"Navigating to {url}...")
        try:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            print(f"Response status: {response.status}")
        except Exception as e:
            print(f"Navigation failed: {e}")
            await browser.close()
            return
        
        # Wait a bit for page to load
        await page.wait_for_timeout(3000)
        
        # Check page title
        title = await page.title()
        print(f"Page title: {title}")
        
        # Check if we got blocked
        content = await page.content()
        if "robot" in content.lower() or "captcha" in content.lower():
            print("⚠️  BLOCKED: Page contains robot/captcha check")
            print(content[:500])
        else:
            print("✓ Page loaded successfully")
        
        # Try to find "See All Buying Options" button
        see_all_button = page.locator("#buybox-see-all-buying-choices")
        button_count = await see_all_button.count()
        print(f"'See All Buying Options' buttons found: {button_count}")
        
        if button_count > 0:
            print("Clicking 'See All Buying Options'...")
            await see_all_button.first.click()
            await page.wait_for_timeout(2000)
            
            # Check for offers
            offers = page.locator("#aod-pinned-offer, #aod-offer, div.aod-offer")
            offer_count = await offers.count()
            print(f"Offers found: {offer_count}")
            
            if offer_count > 0:
                print("✓ SUCCESS: Offers are visible")
                # Get first offer details
                first_offer = offers.first
                seller_elem = first_offer.locator("#aod-offer-soldBy a, .a-size-small.a-link-normal")
                seller_count = await seller_elem.count()
                if seller_count > 0:
                    seller = await seller_elem.first.inner_text()
                    print(f"First seller: {seller}")
            else:
                print("⚠️  No offers found after clicking button")
        else:
            print("⚠️  'See All Buying Options' button not found")
            
            # Check if product is available
            availability = page.locator("#availability")
            avail_count = await availability.count()
            if avail_count > 0:
                avail_text = await availability.inner_text()
                print(f"Availability: {avail_text}")
        
        await browser.close()
        print("\nTest complete!")


if __name__ == "__main__":
    asyncio.run(test_amazon_access())
