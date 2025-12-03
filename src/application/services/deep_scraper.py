"""
Deep Content Scraper - Handles JavaScript-rendered sites and dynamic content
Uses Playwright for sites that require JavaScript execution
"""
import asyncio
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, Browser, Page
from datetime import datetime
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
from src.utilities.logger import get_logger

logger = get_logger(__name__)


class DeepContentScraper:
    """Advanced scraper for JavaScript-heavy and dynamic websites"""
    
    def __init__(self, headless: bool = True, timeout: int = 30000):
        self.headless = headless
        self.timeout = timeout
        self.browser: Optional[Browser] = None
        self.playwright = None
        
    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=['--disable-blink-features=AutomationControlled']
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def _create_stealth_page(self) -> Page:
        """Create a page that mimics real browser behavior"""
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        page = await context.new_page()
        
        # Add stealth scripts
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            window.chrome = {
                runtime: {}
            };
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
        """)
        
        return page
    
    async def scrape_dynamic_site(self, url: str, wait_selector: Optional[str] = None,
                                  scroll_to_bottom: bool = True) -> Dict[str, Any]:
        """
        Scrape sites with JavaScript rendering
        
        Args:
            url: Target URL
            wait_selector: CSS selector to wait for before extracting
            scroll_to_bottom: Whether to scroll to load lazy content
        """
        try:
            page = await self._create_stealth_page()
            logger.info(f"Navigating to {url}")
            
            # Navigate and wait for network to be idle
            await page.goto(url, wait_until='networkidle', timeout=self.timeout)
            
            # Wait for specific selector if provided
            if wait_selector:
                await page.wait_for_selector(wait_selector, timeout=self.timeout)
            
            # Scroll to load lazy content
            if scroll_to_bottom:
                await self._scroll_page(page)
            
            # Extract content
            content = await page.content()
            title = await page.title()
            
            # Get all links
            links = await page.evaluate("""
                () => {
                    return Array.from(document.querySelectorAll('a[href]'))
                        .map(a => a.href)
                        .filter(href => href.startsWith('http'));
                }
            """)
            
            # Get all text content
            text_content = await page.evaluate("""
                () => {
                    return document.body.innerText;
                }
            """)
            
            await page.close()
            
            return {
                "success": True,
                "url": url,
                "title": title,
                "html": content,
                "text": text_content,
                "links": list(set(links)),
                "scraped_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            return {
                "success": False,
                "url": url,
                "error": str(e)
            }
    
    async def _scroll_page(self, page: Page, scroll_pause: float = 0.5):
        """Scroll page to trigger lazy loading"""
        try:
            # Get scroll height
            scroll_height = await page.evaluate("document.body.scrollHeight")
            current_position = 0
            
            while current_position < scroll_height:
                # Scroll down
                await page.evaluate(f"window.scrollTo(0, {current_position})")
                await asyncio.sleep(scroll_pause)
                
                # Update position
                current_position += 500
                
                # Check if new content loaded
                new_height = await page.evaluate("document.body.scrollHeight")
                if new_height > scroll_height:
                    scroll_height = new_height
                    
        except Exception as e:
            logger.warning(f"Error scrolling page: {str(e)}")
    
    async def scrape_bloomberg_fx_center(self) -> List[Dict[str, Any]]:
        """Specialized scraper for Bloomberg FX Center"""
        url = "https://www.bloomberg.com/fx-center"
        result = await self.scrape_dynamic_site(
            url,
            wait_selector='.currency-table, [class*="currency"]',
            scroll_to_bottom=True
        )
        
        if not result["success"]:
            return []
        
        soup = BeautifulSoup(result["html"], 'html.parser')
        articles = []
        
        # Extract currency data
        currency_elements = soup.select('.currency-row, [class*="currency-pair"]')
        
        for elem in currency_elements:
            try:
                # Extract relevant data
                text = elem.get_text(strip=True)
                articles.append({
                    "text": text,
                    "metadata": {
                        "source": "Bloomberg FX Center",
                        "category": "forex",
                        "scraped_at": datetime.now().isoformat(),
                        "type": "fx_data"
                    }
                })
            except Exception as e:
                logger.error(f"Error parsing currency element: {str(e)}")
                
        return articles
    
    async def scrape_coindesk_prices(self) -> List[Dict[str, Any]]:
        """Specialized scraper for CoinDesk price data"""
        url = "https://www.coindesk.com/price"
        result = await self.scrape_dynamic_site(
            url,
            wait_selector='[class*="price"], .price-table',
            scroll_to_bottom=True
        )
        
        if not result["success"]:
            return []
        
        soup = BeautifulSoup(result["html"], 'html.parser')
        articles = []
        
        # Extract price elements
        price_elements = soup.select('[class*="price-row"], tr, .coin-row')
        
        for elem in price_elements:
            try:
                text = elem.get_text(strip=True)
                if text and len(text) > 10:  # Filter out empty rows
                    articles.append({
                        "text": f"Crypto Price Update: {text}",
                        "metadata": {
                            "source": "CoinDesk Prices",
                            "category": "crypto",
                            "scraped_at": datetime.now().isoformat(),
                            "type": "price_data"
                        }
                    })
            except Exception as e:
                logger.error(f"Error parsing price element: {str(e)}")
        
        return articles
    
    async def extract_structured_data(self, url: str) -> Dict[str, Any]:
        """Extract JSON-LD and structured data from pages"""
        try:
            page = await self._create_stealth_page()
            await page.goto(url, wait_until='networkidle')
            
            # Extract JSON-LD data
            json_ld = await page.evaluate("""
                () => {
                    const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                    return Array.from(scripts).map(s => {
                        try {
                            return JSON.parse(s.textContent);
                        } catch(e) {
                            return null;
                        }
                    }).filter(d => d !== null);
                }
            """)
            
            # Extract meta tags
            meta_data = await page.evaluate("""
                () => {
                    const metas = document.querySelectorAll('meta[property], meta[name]');
                    const data = {};
                    metas.forEach(meta => {
                        const key = meta.getAttribute('property') || meta.getAttribute('name');
                        const value = meta.getAttribute('content');
                        if (key && value) {
                            data[key] = value;
                        }
                    });
                    return data;
                }
            """)
            
            await page.close()
            
            return {
                "success": True,
                "json_ld": json_ld,
                "meta_data": meta_data,
                "url": url
            }
            
        except Exception as e:
            logger.error(f"Error extracting structured data from {url}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def scrape_with_api_interception(self, url: str, 
                                           api_patterns: List[str]) -> Dict[str, Any]:
        """
        Intercept API calls made by the page
        Useful for getting raw JSON data
        """
        api_responses = []
        
        try:
            page = await self._create_stealth_page()
            
            # Setup request interception
            async def handle_response(response):
                for pattern in api_patterns:
                    if pattern in response.url:
                        try:
                            if response.status == 200:
                                data = await response.json()
                                api_responses.append({
                                    "url": response.url,
                                    "data": data,
                                    "headers": response.headers
                                })
                        except:
                            pass
            
            page.on("response", handle_response)
            
            # Navigate and wait
            await page.goto(url, wait_until='networkidle')
            await asyncio.sleep(3)  # Wait for API calls
            
            await page.close()
            
            return {
                "success": True,
                "api_responses": api_responses,
                "count": len(api_responses)
            }
            
        except Exception as e:
            logger.error(f"Error intercepting APIs: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def deep_crawl(self, start_url: str, max_depth: int = 2,
                        same_domain_only: bool = True) -> List[Dict[str, Any]]:
        """
        Deep crawl starting from a URL
        Follows links up to max_depth
        """
        from urllib.parse import urlparse
        
        visited = set()
        to_visit = [(start_url, 0)]
        all_data = []
        
        base_domain = urlparse(start_url).netloc
        
        while to_visit:
            url, depth = to_visit.pop(0)
            
            if url in visited or depth > max_depth:
                continue
            
            visited.add(url)
            
            # Check domain restriction
            if same_domain_only and urlparse(url).netloc != base_domain:
                continue
            
            logger.info(f"Crawling: {url} (depth: {depth})")
            
            result = await self.scrape_dynamic_site(url)
            
            if result["success"]:
                all_data.append(result)
                
                # Add child links
                if depth < max_depth:
                    for link in result.get("links", [])[:50]:  # Limit links per page
                        if link not in visited:
                            to_visit.append((link, depth + 1))
            
            # Rate limiting
            await asyncio.sleep(2)
        
        logger.info(f"Deep crawl complete: {len(all_data)} pages scraped")
        return all_data


class SpecializedScrapers:
    """Collection of specialized scrapers for specific sites"""
    
    @staticmethod
    async def scrape_reuters_api(session) -> List[Dict[str, Any]]:
        """Try to access Reuters API endpoints directly"""
        articles = []
        
        # Reuters often exposes APIs
        api_urls = [
            "https://www.reuters.com/pf/api/v3/content/fetch/articles-by-section-alias-or-id-v1",
            "https://www.reuters.com/assets/jsonWireNews"
        ]
        
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json"
        }
        
        for api_url in api_urls:
            try:
                params = {"uri": "/markets/currencies", "size": 20}
                async with session.get(api_url, params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Process API response
                        logger.info(f"Successfully fetched Reuters API: {api_url}")
                        # Convert to article format
            except Exception as e:
                logger.debug(f"Reuters API endpoint failed: {str(e)}")
        
        return articles
    
    @staticmethod
    async def scrape_bloomberg_api() -> List[Dict[str, Any]]:
        """Bloomberg market data extraction"""
        # Bloomberg uses various APIs for market data
        # This would require reverse engineering their API
        pass


