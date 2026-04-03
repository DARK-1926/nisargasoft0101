import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('https://www.amazon.in/dp/B07845BYSZ')
        print('Title:', await page.title())
        await browser.close()

asyncio.run(test())
