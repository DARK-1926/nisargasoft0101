"""Selenium-based Amazon scraper with anti-detection."""
from __future__ import annotations

import time
from dataclasses import dataclass

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


class SeleniumAmazonScraper:
    """Scraper using undetected-chromedriver to bypass bot detection."""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None
    
    def _init_driver(self):
        """Initialize undetected Chrome driver."""
        options = uc.ChromeOptions()
        if self.headless:
            options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        self.driver = uc.Chrome(options=options, version_main=120)
        self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
    
    def scrape_offers(self, asin: str, location_code: str = "BLR") -> list[OfferData]:
        """Scrape offers for an ASIN."""
        if not self.driver:
            self._init_driver()
        
        url = f"https://www.amazon.in/dp/{asin}"
        self.driver.get(url)
        
        # Wait for page load
        time.sleep(3)
        
        # Check for bot detection
        if "robot" in self.driver.page_source.lower() or "captcha" in self.driver.page_source.lower():
            raise Exception("Bot detection triggered")
        
        offers = []
        
        try:
            # Click "See All Buying Options" button
            wait = WebDriverWait(self.driver, 10)
            see_all_btn = wait.until(
                EC.element_to_be_clickable((By.ID, "buybox-see-all-buying-choices"))
            )
            see_all_btn.click()
            time.sleep(2)
            
            # Scroll to load all offers
            self._scroll_offers_page()
            
            # Extract offers
            offer_elements = self.driver.find_elements(By.CSS_SELECTOR, "#aod-offer, .aod-offer")
            
            for elem in offer_elements:
                try:
                    # Extract seller name
                    try:
                        seller = elem.find_element(By.CSS_SELECTOR, "#aod-offer-soldBy a, .a-size-small.a-link-normal").text
                    except NoSuchElementException:
                        seller = "Unknown"
                    
                    # Extract price
                    try:
                        price_elem = elem.find_element(By.CSS_SELECTOR, ".a-price .a-offscreen")
                        price_text = price_elem.get_attribute("textContent").replace("₹", "").replace(",", "").strip()
                        price = float(price_text)
                    except (NoSuchElementException, ValueError):
                        continue
                    
                    # Extract condition
                    try:
                        condition = elem.find_element(By.CSS_SELECTOR, "#aod-offer-heading").text
                    except NoSuchElementException:
                        condition = "New"
                    
                    # Extract availability
                    try:
                        availability = elem.find_element(By.CSS_SELECTOR, "#availability, .a-color-success").text
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
            
        except TimeoutException:
            # No "See All Buying Options" button - try to get main offer
            try:
                seller = self.driver.find_element(By.CSS_SELECTOR, "#sellerProfileTriggerId").text
                price_text = self.driver.find_element(By.CSS_SELECTOR, ".a-price .a-offscreen").get_attribute("textContent")
                price = float(price_text.replace("₹", "").replace(",", "").strip())
                
                offers.append(OfferData(
                    seller_name=seller,
                    price=price,
                    condition="New",
                    availability="In Stock"
                ))
            except Exception:
                pass
        
        return offers
    
    def _scroll_offers_page(self):
        """Scroll the offers page to load all sellers."""
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        max_scrolls = 30
        
        while scroll_attempts < max_scrolls:
            # Scroll down
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)
            
            # Try clicking "Show more" buttons
            try:
                show_more = self.driver.find_element(By.CSS_SELECTOR, "#aod-show-more-offers, a[data-action='show-more']")
                show_more.click()
                time.sleep(1.5)
            except NoSuchElementException:
                pass
            
            # Check if we've reached the bottom
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            
            last_height = new_height
            scroll_attempts += 1
    
    def close(self):
        """Close the browser."""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
