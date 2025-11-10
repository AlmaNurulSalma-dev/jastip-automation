"""
1688.com (Alibaba Wholesale) web scraper using Playwright
Searches for products based on parsed AI parameters

Note: Using 1688.com instead of Taobao due to less strict anti-bot protection
"""

import asyncio
import logging
import re
import sys
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, Page, Browser
from urllib.parse import quote

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TaobaoScraper:
    """Scrapes product listings from 1688.com (Alibaba wholesale platform)"""

    def __init__(self, headless: bool = True, platform: str = '1688'):
        """
        Initialize scraper

        Args:
            headless: Run browser in headless mode (no GUI)
            platform: Platform to scrape ('1688' or 'taobao')
        """
        self.headless = headless
        self.platform = platform

        # Platform-specific configurations
        if platform == '1688':
            self.base_url = "https://s.1688.com/selloffer/offer_search.htm"
            self.mobile_url = "https://m.1688.com/offer_search/-{keyword}.html"
            logger.info("Using 1688.com (Alibaba wholesale platform)")
        else:
            self.base_url = "https://s.taobao.com/search"
            logger.info("Using Taobao platform")

    async def search_products(
        self,
        keyword: str,
        max_price_cny: Optional[float] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        Search Taobao for products

        Args:
            keyword: Search keyword
            max_price_cny: Maximum price in CNY
            limit: Maximum number of products to return

        Returns:
            List of product dictionaries
        """
        logger.info(f"Searching Taobao for: {keyword}, max_price: {max_price_cny}")

        products = []

        async with async_playwright() as p:
            # Launch with stealth options
            browser = await p.chromium.launch(
                headless=self.headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-web-security',
                ]
            )
            try:
                # Create context with realistic browser fingerprint
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    locale='zh-CN',
                    timezone_id='Asia/Shanghai',
                    geolocation={'longitude': 121.4737, 'latitude': 31.2304},  # Shanghai
                    permissions=['geolocation'],
                )

                # Add additional stealth
                await context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['zh-CN', 'zh', 'en-US', 'en']
                    });
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });
                """)

                page = await context.new_page()

                # Set additional headers
                await page.set_extra_http_headers({
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Cache-Control': 'max-age=0',
                })

                # Build search URL
                search_url = self._build_search_url(keyword, max_price_cny)
                logger.info(f"Navigating to: {search_url}")

                # Navigate to search page with more lenient waiting
                try:
                    # Add random delay to seem more human
                    import random
                    await page.wait_for_timeout(random.randint(500, 1500))

                    await page.goto(search_url, wait_until='domcontentloaded', timeout=20000)
                except Exception as nav_error:
                    logger.warning(f"Navigation warning: {nav_error}")
                    # Try alternate approach
                    await page.goto(search_url, timeout=15000)

                # Wait for dynamic content and simulate human behavior
                await page.wait_for_timeout(random.randint(2000, 4000))

                # Simulate mouse movement
                try:
                    await page.mouse.move(random.randint(100, 500), random.randint(100, 500))
                    await page.wait_for_timeout(random.randint(500, 1000))
                except:
                    pass

                # Platform-specific selectors
                if self.platform == '1688':
                    selectors_to_try = [
                        '.sm-offer-item',  # 1688 main item class
                        '.offer-item',
                        '.sm-floorhead-title',
                        '[class*="offer"]',
                        '.list-item',
                        '.gallery-offer-item',
                    ]
                else:
                    selectors_to_try = [
                        '.item',
                        '.Card--mainPicAndDesc--wvcDXVq',
                        '[class*="item"]',
                        '[data-item]',
                    ]

                selector_found = None
                for selector in selectors_to_try:
                    try:
                        await page.wait_for_selector(selector, timeout=5000)
                        selector_found = selector
                        logger.info(f"Found products with selector: {selector}")
                        break
                    except:
                        continue

                if not selector_found:
                    logger.warning(f"Could not find product listings - {self.platform} may have blocked the request or changed structure")
                    # Save screenshot for debugging
                    try:
                        await page.screenshot(path='debug_screenshot.png')
                        logger.info("Saved debug screenshot to debug_screenshot.png")
                    except:
                        pass
                    return []

                # Extract products
                products = await self._extract_products(page, limit, selector_found)

                logger.info(f"Successfully scraped {len(products)} products from {self.platform}")

            except Exception as e:
                logger.error(f"Error during scraping from {self.platform}: {str(e)}")
                raise
            finally:
                try:
                    await context.close()
                except:
                    pass
                await browser.close()

        return products

    def _build_search_url(self, keyword: str, max_price_cny: Optional[float] = None) -> str:
        """Build search URL with parameters based on platform"""
        encoded_keyword = quote(keyword)

        if self.platform == '1688':
            # 1688 URL format
            url = f"{self.base_url}?keywords={encoded_keyword}"

            # Add price filter if specified
            if max_price_cny:
                # 1688 price filter format
                url += f"&priceStart=0&priceEnd={int(max_price_cny)}"

            # Sort by relevance
            url += "&sortType=default"

        else:
            # Taobao URL format
            url = f"{self.base_url}?q={encoded_keyword}"

            # Add price filter if specified
            if max_price_cny:
                # Taobao price filter format: &filter=reserve_price[,max_price]
                url += f"&filter=reserve_price%5B%2C{int(max_price_cny)}%5D"

            # Sort by relevance (default)
            url += "&sort=default"

        return url

    async def _extract_products(self, page: Page, limit: int, selector: str) -> List[Dict]:
        """Extract product information from the page"""
        products = []

        # Get all product items using the found selector
        items = await page.query_selector_all(selector)
        logger.info(f"Found {len(items)} product items on page")

        # Debug: Save HTML of first item for analysis
        if items and len(items) > 0:
            try:
                first_item_html = await items[0].inner_html()
                with open('debug_item.html', 'w', encoding='utf-8') as f:
                    f.write(first_item_html)
                logger.info("Saved first item HTML to debug_item.html for analysis")
            except:
                pass

        for i, item in enumerate(items[:limit]):
            try:
                product = await self._extract_product_info(item)
                if product:
                    products.append(product)
            except Exception as e:
                logger.warning(f"Failed to extract product {i}: {str(e)}")
                continue

        return products

    async def _extract_product_info(self, item) -> Optional[Dict]:
        """Extract information from a single product item (platform-agnostic)"""
        try:
            if self.platform == '1688':
                return await self._extract_1688_product_info(item)
            else:
                return await self._extract_taobao_product_info(item)
        except Exception as e:
            logger.warning(f"Error extracting product info: {str(e)}")
            return None

    async def _extract_1688_product_info(self, item) -> Optional[Dict]:
        """Extract information from a 1688 product item"""
        try:
            # Extract title from title-text div
            title = "N/A"
            title_selectors = [
                '.offer-title-row .title-text div',
                '.title-text div',
                '.offer-title-row',
                'a[title]'
            ]
            for selector in title_selectors:
                title_elem = await item.query_selector(selector)
                if title_elem:
                    if selector == 'a[title]':
                        title = await title_elem.get_attribute('title')
                    else:
                        title = await title_elem.inner_text()
                    if title and title.strip() and len(title.strip()) > 3:
                        title = title.strip()
                        break

            # Extract price from offer-price-row
            price = 0.0
            # Look for text-main class which contains the main price number
            price_elem = await item.query_selector('.offer-price-row .text-main')
            if price_elem:
                price_main = await price_elem.inner_text()
                # Look for decimal part
                decimal_elem = await item.query_selector('.offer-price-row .text-main + div')
                decimal_part = ""
                if decimal_elem:
                    decimal_text = await decimal_elem.inner_text()
                    if decimal_text:
                        decimal_part = decimal_text.replace('.', '')

                price_text = f"{price_main}.{decimal_part}" if decimal_part else price_main
                price = self._parse_price(price_text)

            # Extract product link from the main <a> tag
            link = await item.get_attribute('href')
            if link and not link.startswith('http'):
                link = f"https:{link}" if link.startswith('//') else f"https:{link}"

            # Extract image URL
            image_url = None
            img_elem = await item.query_selector('.offer-img-wrapper img, .main-img')
            if img_elem:
                image_url = await img_elem.get_attribute('src') or await img_elem.get_attribute('data-src')
                if image_url and not image_url.startswith('http'):
                    image_url = f"https:{image_url}"

            # Extract shop/seller name from offer-shop-row
            shop_name = "Unknown"
            shop_elem = await item.query_selector('.offer-shop-row .desc-text')
            if shop_elem:
                shop_name = await shop_elem.inner_text()
                shop_name = shop_name.strip() if shop_name else "Unknown"

            # Extract sales count from col-desc_after in offer-price-row
            sales = 0
            sales_elem = await item.query_selector('.offer-price-row .col-desc_after .desc-text')
            if sales_elem:
                sales_text = await sales_elem.inner_text()
                if sales_text:
                    sales = self._parse_sales(sales_text)

            product = {
                'title': title,
                'price_cny': price,
                'link': link,
                'image_url': image_url,
                'shop_name': shop_name,
                'location': '',
                'sales_count': sales
            }

            return product

        except Exception as e:
            logger.warning(f"Error extracting 1688 product info: {str(e)}")
            return None

    async def _extract_taobao_product_info(self, item) -> Optional[Dict]:
        """Extract information from a Taobao product item"""
        try:
            # Extract title
            title_elem = await item.query_selector('.title')
            title = await title_elem.inner_text() if title_elem else "N/A"
            title = title.strip()

            # Extract price
            price_elem = await item.query_selector('.price')
            price_text = await price_elem.inner_text() if price_elem else "0"
            price = self._parse_price(price_text)

            # Extract product link
            link_elem = await item.query_selector('a')
            link = await link_elem.get_attribute('href') if link_elem else None
            if link and not link.startswith('http'):
                link = f"https:{link}"

            # Extract image URL
            img_elem = await item.query_selector('img')
            image_url = await img_elem.get_attribute('src') if img_elem else None
            if image_url and not image_url.startswith('http'):
                image_url = f"https:{image_url}"

            # Extract shop/seller name
            shop_elem = await item.query_selector('.shop')
            shop_name = await shop_elem.inner_text() if shop_elem else "Unknown"
            shop_name = shop_name.strip()

            # Extract location
            location_elem = await item.query_selector('.location')
            location = await location_elem.inner_text() if location_elem else ""

            # Extract sales count
            deal_elem = await item.query_selector('.deal-cnt')
            sales_text = await deal_elem.inner_text() if deal_elem else "0"
            sales = self._parse_sales(sales_text)

            product = {
                'title': title,
                'price_cny': price,
                'link': link,
                'image_url': image_url,
                'shop_name': shop_name,
                'location': location,
                'sales_count': sales
            }

            return product

        except Exception as e:
            logger.warning(f"Error extracting Taobao product info: {str(e)}")
            return None

    def _parse_price(self, price_text: str) -> float:
        """Parse price from text"""
        try:
            # Remove currency symbols and extract numbers
            price_str = re.sub(r'[^\d.]', '', price_text)
            return float(price_str) if price_str else 0.0
        except:
            return 0.0

    def _parse_sales(self, sales_text: str) -> int:
        """Parse sales count from text (handles Chinese formats like '9.6万+件')"""
        try:
            # Remove common suffixes
            sales_text = sales_text.replace('件', '').replace('人付款', '').replace('+', '').strip()

            # Handle "万" (10,000) - like "9.6万" or "1.2万"
            if '万' in sales_text:
                num_str = re.search(r'([\d.]+)万', sales_text)
                if num_str:
                    return int(float(num_str.group(1)) * 10000)

            # Handle regular numbers
            num_str = re.search(r'[\d.]+', sales_text)
            if num_str:
                return int(float(num_str.group(0)))

            return 0
        except Exception as e:
            logger.debug(f"Failed to parse sales: {sales_text} - {e}")
            return 0


async def search_taobao(
    keyword: str,
    max_price_cny: Optional[float] = None,
    limit: int = 20,
    platform: str = '1688'
) -> List[Dict]:
    """
    Convenience function to search for products

    Args:
        keyword: Search keyword
        max_price_cny: Maximum price in CNY
        limit: Maximum number of products to return
        platform: Platform to search ('1688' or 'taobao', default: '1688')

    Returns:
        List of product dictionaries
    """
    scraper = TaobaoScraper(headless=True, platform=platform)
    return await scraper.search_products(keyword, max_price_cny, limit)


# For testing
async def test_search(keyword: str = "notebook", max_price: float = 30, limit: int = 5):
    """
    Test function for scraper

    Args:
        keyword: Search keyword
        max_price: Maximum price in CNY
        limit: Number of products to fetch
    """
    print(f"\n{'='*60}")
    print(f"Testing 1688.com Scraper")
    print(f"{'='*60}")
    print(f"Keyword: {keyword}")
    print(f"Max Price: ¥{max_price} CNY")
    print(f"Limit: {limit} products")
    print(f"{'='*60}\n")

    products = await search_taobao(keyword, max_price_cny=max_price, limit=limit, platform='1688')

    if products:
        print(f"\n✅ Found {len(products)} products:\n")
        for i, product in enumerate(products, 1):
            print(f"{i}. {product['title'][:60]}")
            print(f"   💰 Price: ¥{product['price_cny']:.2f}")
            print(f"   🏪 Shop: {product['shop_name']}")
            print(f"   📊 Sales: {product['sales_count']:,}")
            if product['link']:
                print(f"   🔗 Link: {product['link'][:60]}...")
            print()
    else:
        print("\n⚠️  No products found")

    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(test_search())
