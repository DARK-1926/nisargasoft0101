"""Hybrid scraper combining multiple methods for speed and accuracy."""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Optional

import httpx
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import undetected_chromedriver as uc


@dataclass
class OfferData:
    seller_name: str
    price: float
    condition: str
    availability: str
    shipping_price: float = 0.0


class HybridAmazonScraper:
    """Fast hybrid scraper using multiple methods."""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver: Optional[uc.Chrome] = None
    
    async def scrape_offers(self, asin: str, location_code: str = "BLR") -> list[OfferData]:
        """
        Scrape offers using hybrid approach:
        1. Try fast HTTP request first
        2. Fall back to Selenium if needed
        3. Use parallel extraction for speed
        """
        # Try fast method first
        try:
            offers = await self._fast_scrape(asin)
            if offers:
                return offers
        except Exception:
            pass
        
        # Fall back to Selenium with anti-detection
        return await self._selenium_scrape(asin, location_code)
    
    async def _fast_scrape(self, asin: str) -> list[OfferData]:
        """Fast HTTP-based scraping (works if not blocked)."""
        url = f"https://www.amazon.in/gp/aod/ajax?asin={asin}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-IN,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': f'https://www.amazon.in/dp/{asin}',
        }
        
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code != 200:
                return []
            
            # Check for bot detection
            if 'robot' in response.text.lower() or 'captcha' in response.text.lower():
                return []
            
            return self._parse_offers_html(response.text)
    
    def _parse_offers_html(self, html: str) -> list[OfferData]:
        """Parse offers from HTML using BeautifulSoup."""
        soup = BeautifulSoup(html, 'html.parser')
        offers = []
        
        # Find all offer divs
        offer_divs = soup.select('#aod-offer, .aod-offer, div[id^="aod-offer"]')
        
        for div in offer_divs:
            try:
                # Extract seller
                seller_elem = div.select_one('#aod-offer-soldBy a, .a-size-small.a-link-normal')
                seller = seller_elem.get_text(strip=True) if seller_elem else "Unknown"
                
                # Extract price
                price_elem = div.select_one('.a-price .a-offscreen, span.a-price-whole')
                if not price_elem:
                    continue
                
                price_text = price_elem.get_text(strip=True).replace('₹', '').replace(',', '').replace('.00', '')
                try:
                    price = float(price_text)
                except ValueError:
                    continue
                
                # Extract condition
                condition_elem = div.select_one('#aod-offer-heading, .a-color-base')
                condition = condition_elem.get_text(strip=True) if condition_elem else "New"
                
                # Extract availability
                avail_elem = div.select_one('#availability, .a-color-success, .a-color-state')
                availability = avail_elem.get_text(strip=True) if avail_elem else "In Stock"
                
                # Extract shipping
                shipping = 0.0
                shipping_elem = div.select_one('.a-color-secondary')
                if shipping_elem and 'FREE' not in shipping_elem.get_text(strip=True).upper():
                    try:
                        shipping_text = shipping_elem.get_text(strip=True).replace('₹', '').replace(',', '')
                        shipping = float(shipping_text)
                    except ValueError:
                        pass
                
                offers.append(OfferData(
                    seller_name=seller,
                    price=price,
                    condition=condition,
                    availability=availability,
                    shipping_price=shipping
                ))
            except Exception:
                continue
        
        return offers
    
    async def _selenium_scrape(self, asin: str, location_code: str) -> list[OfferData]:
        """Selenium-based scraping with anti-detection."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._selenium_scrape_sync, asin, location_code)
    
    def _selenium_scrape_sync(self, asin: str, location_code: str) -> list[OfferData]:
        """Synchronous Selenium scraping."""
        if not self.driver:
            self._init_driver()
        
        url = f"https://www.amazon.in/dp/{asin}"
        self.driver.get(url)
        
        # Random human-like delay
        time.sleep(2 + (time.time() % 2))
        
        # Check for bot detection
        if "robot" in self.driver.page_source.lower() or "captcha" in self.driver.page_source.lower():
            raise Exception("Bot detection triggered")
        
        offers = []
        
        try:
            # Click "See All Buying Options"
            wait = WebDriverWait(self.driver, 10)
            see_all_btn = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "#buybox-see-all-buying-choices, a[href*='offer-listing']"))
            )
            see_all_btn.click()
            time.sleep(2)
            
            # Scroll to load all offers (optimized)
            self._smart_scroll()
            
            # Extract offers using parallel parsing
            html = self.driver.page_source
            offers = self._parse_offers_html(html)
            
            # If parsing failed, try direct element extraction
            if not offers:
                offers = self._extract_offers_direct()
            
        except TimeoutException:
            # Try to get main offer
            try:
                offers = self._extract_main_offer()
            except Exception:
                pass
        
        return offers
    
    def _init_driver(self):
        """Initialize undetected Chrome with optimizations."""
        options = uc.ChromeOptions()
        if self.headless:
            options.add_argument('--headless=new')
        
        # Performance optimizations
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-images')  # Faster loading
        options.add_argument('--disable-javascript')  # Not needed for static content
        options.add_argument('--window-size=1920,1080')
        
        # Anti-detection
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        prefs = {
            'profile.managed_default_content_settings.images': 2,  # Disable images
            'profile.default_content_setting_values.notifications': 2,
        }
        options.add_experimental_option('prefs', prefs)
        
        self.driver = uc.Chrome(options=options, version_main=120)
    
    def _smart_scroll(self):
        """Optimized scrolling - only scroll until no new content."""
        last_height = 0
        no_change_count = 0
        scroll_attempts = 0
        max_scrolls = 20  # Reduced for speed
        
        while scroll_attempts < max_scrolls and no_change_count < 3:
            # Get current offer count
            current_height = self.driver.execute_script("return document.body.scrollHeight")
            
            # Scroll
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.8)  # Faster than before
            
            # Try clicking "Show more"
            try:
                show_more = self.driver.find_element(By.CSS_SELECTOR, "#aod-show-more-offers")
                show_more.click()
                time.sleep(1)
            except NoSuchElementException:
                pass
            
            # Check if height changed
            if current_height == last_height:
                no_change_count += 1
            else:
                no_change_count = 0
            
            last_height = current_height
            scroll_attempts += 1
    
    def _extract_offers_direct(self) -> list[OfferData]:
        """Direct element extraction as fallback."""
        offers = []
        offer_elements = self.driver.find_elements(By.CSS_SELECTOR, "#aod-offer, .aod-offer")
        
        for elem in offer_elements:
            try:
                seller = elem.find_element(By.CSS_SELECTOR, "#aod-offer-soldBy a").text
                price_text = elem.find_element(By.CSS_SELECTOR, ".a-price .a-offscreen").get_attribute("textContent")
                price = float(price_text.replace("₹", "").replace(",", "").strip())
                
                try:
                    condition = elem.find_element(By.CSS_SELECTOR, "#aod-offer-heading").text
                except NoSuchElementException:
                    condition = "New"
                
                try:
                    availability = elem.find_element(By.CSS_SELECTOR, "#availability").text
                except NoSuchElementException:
                    availability = "In Stock"
                
                offers.append(OfferData(
                    seller_name=seller,
                    price=price,
                    condition=condition,
                    availability=availability
                ))
            except Exception:
                continue
        
        return offers
    
    def _extract_main_offer(self) -> list[OfferData]:
        """Extract main buybox offer."""
        seller = self.driver.find_element(By.CSS_SELECTOR, "#sellerProfileTriggerId").text
        price_text = self.driver.find_element(By.CSS_SELECTOR, ".a-price .a-offscreen").get_attribute("textContent")
        price = float(price_text.replace("₹", "").replace(",", "").strip())
        
        return [OfferData(
            seller_name=seller,
            price=price,
            condition="New",
            availability="In Stock"
        )]
    
    def close(self):
        """Close browser."""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
