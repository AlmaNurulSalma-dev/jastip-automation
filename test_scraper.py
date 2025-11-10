"""
Quick test script to verify the scraper integration
"""

import asyncio
import logging
import sys
from taobao_scraper import search_taobao
from database import init_database, save_scraped_products

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_scraper():
    """Test the Taobao scraper"""

    print("\n" + "="*60)
    print("TESTING 1688 SCRAPER INTEGRATION")
    print("="*60)

    # Initialize database
    print("\n1. Initializing database...")
    init_database()
    print("✅ Database initialized")

    # Test scraping (with a simple query)
    print("\n2. Testing 1688.com scraper...")
    print("   Query: 'notebook'")
    print("   Max Price: ¥30 CNY")
    print("   Limit: 3 products")
    print("\n   ⚠️  This may take 10-30 seconds...")
    print("   ⚠️  Using 1688.com (less strict than Taobao)")

    try:
        products = await search_taobao(
            keyword="notebook",
            max_price_cny=30,
            limit=3,
            platform='1688'
        )

        if products:
            print(f"\n✅ Successfully scraped {len(products)} products!")
            print("\n" + "-"*60)
            for i, product in enumerate(products, 1):
                print(f"\nProduct {i}:")
                print(f"  Title: {product.get('title', 'N/A')[:50]}")
                print(f"  Price: ¥{product.get('price_cny', 0):.2f}")
                print(f"  Shop: {product.get('shop_name', 'Unknown')}")
                print(f"  Sales: {product.get('sales_count', 0):,}")
                if product.get('link'):
                    print(f"  Link: {product.get('link')[:60]}...")

            # Test saving to database
            print("\n3. Testing database save...")
            saved_ids = save_scraped_products(products, platform='taobao')
            print(f"✅ Saved {len(saved_ids)} products to database")

            print("\n" + "="*60)
            print("✅ ALL TESTS PASSED!")
            print("="*60)

        else:
            print("\n⚠️  No products found (this may be due to 1688's anti-bot measures)")
            print("\n💡 This is expected behavior in some cases.")
            print("   The bot will still work - it will just return 0 products.")
            print("\n" + "="*60)
            print("⚠️  SCRAPER RETURNED NO RESULTS (but no errors)")
            print("="*60)

    except Exception as e:
        print(f"\n❌ Error during scraping: {e}")
        print("\n💡 Common issues:")
        print("   1. 1688's anti-bot protection (though less strict than Taobao)")
        print("   2. Network connectivity")
        print("   3. Region restrictions")
        print("   4. Need to try different selectors")
        print("\nThe bot will handle these errors gracefully.")
        print("\n" + "="*60)
        print("⚠️  TEST FAILED (see error above)")
        print("="*60)


if __name__ == "__main__":
    asyncio.run(test_scraper())
