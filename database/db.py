"""
Database module for Jastip Automation Bot.
Handles product storage, search history, and price tracking.
"""

import sqlite3
import logging
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import uuid4
from contextlib import contextmanager

# Configure logging
logger = logging.getLogger(__name__)

# Database file path
DB_PATH = "jastip.db"


@contextmanager
def get_connection():
    """
    Context manager for database connections.

    Ensures connections are properly closed and provides better error handling.

    Yields:
        sqlite3.Connection: Database connection
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # Enable column access by name

        # Enable foreign keys and set WAL mode for better concurrency
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")

        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database connection error: {e}", exc_info=True)
        raise
    finally:
        if conn:
            conn.close()


def init_database() -> None:
    """
    Initialize database and create tables if they don't exist.

    Creates three tables:
    - products: Store product information
    - search_history: Log user searches
    - price_history: Track price changes over time

    Also creates indexes for better query performance.
    """
    try:
        logger.info("Initializing database...")

        with get_connection() as conn:
            cursor = conn.cursor()

            # Create products table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id TEXT PRIMARY KEY,
                    platform TEXT NOT NULL,
                    product_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    price REAL NOT NULL,
                    original_price REAL,
                    currency TEXT DEFAULT 'CNY',
                    rating REAL,
                    sales_count INTEGER,
                    image_url TEXT,
                    product_url TEXT,
                    color TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create search_history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS search_history (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    username TEXT,
                    search_query TEXT NOT NULL,
                    parsed_params TEXT NOT NULL,
                    results_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create price_history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_history (
                    id TEXT PRIMARY KEY,
                    product_id TEXT NOT NULL,
                    price REAL NOT NULL,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
                )
            """)

            # Create indexes for better performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_products_platform_id
                ON products(platform, product_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_search_history_user_date
                ON search_history(user_id, created_at DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_price_history_product_date
                ON price_history(product_id, recorded_at DESC)
            """)

            logger.info("Database initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        raise


def save_product(product: Dict[str, Any]) -> str:
    """
    Save or update a product in the database.

    Uses INSERT OR REPLACE to handle both new products and updates.
    Automatically generates an ID if not provided.

    Args:
        product: Dictionary containing product information with keys:
                - platform (str): Platform name (e.g., 'taobao', 'pinduoduo')
                - product_id (str): Platform-specific product ID
                - title (str): Product title
                - price (float): Current price
                - original_price (float, optional): Original price before discount
                - currency (str, optional): Currency code (default 'CNY')
                - rating (float, optional): Product rating (0-5)
                - sales_count (int, optional): Number of sales
                - image_url (str, optional): Product image URL
                - product_url (str, optional): Product page URL
                - color (str, optional): Product color

    Returns:
        str: The product ID

    Example:
        >>> product_id = save_product({
        ...     'platform': 'taobao',
        ...     'product_id': '12345',
        ...     'title': 'Washi Tape',
        ...     'price': 15.50,
        ...     'rating': 4.8,
        ...     'sales_count': 1000
        ... })
    """
    try:
        # Generate ID if not provided
        product_id = product.get('id') or f"{product['platform']}_{product['product_id']}"

        with get_connection() as conn:
            cursor = conn.cursor()

            # Use INSERT OR REPLACE for upsert logic
            cursor.execute("""
                INSERT OR REPLACE INTO products (
                    id, platform, product_id, title, price, original_price,
                    currency, rating, sales_count, image_url, product_url,
                    color, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                         COALESCE((SELECT created_at FROM products WHERE id = ?), CURRENT_TIMESTAMP),
                         CURRENT_TIMESTAMP)
            """, (
                product_id,
                product['platform'],
                product['product_id'],
                product['title'],
                product['price'],
                product.get('original_price'),
                product.get('currency', 'CNY'),
                product.get('rating'),
                product.get('sales_count'),
                product.get('image_url'),
                product.get('product_url'),
                product.get('color'),
                product_id  # For COALESCE to preserve original created_at
            ))

            logger.info(f"Saved product: {product_id} - {product['title'][:50]}")
            return product_id

    except Exception as e:
        logger.error(f"Failed to save product: {e}", exc_info=True)
        raise


def save_search(
    user_id: str,
    username: Optional[str],
    query: str,
    parsed_params: Dict[str, Any],
    results_count: int = 0
) -> str:
    """
    Log a search to the database.

    Stores the original query, parsed parameters, and metadata
    for analytics and user history tracking.

    Args:
        user_id: Telegram user ID
        username: Telegram username (can be None)
        query: Original search query text
        parsed_params: Dictionary of parsed search parameters
        results_count: Number of results found (default 0)

    Returns:
        str: The search record ID

    Example:
        >>> search_id = save_search(
        ...     user_id='123456789',
        ...     username='john_doe',
        ...     query='cari washi tape coklat',
        ...     parsed_params={'keyword': 'washi tape', 'color': 'brown'},
        ...     results_count=15
        ... )
    """
    try:
        search_id = str(uuid4())

        # Convert parsed_params to JSON string
        params_json = json.dumps(parsed_params, ensure_ascii=False)

        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO search_history (
                    id, user_id, username, search_query,
                    parsed_params, results_count
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (search_id, user_id, username, query, params_json, results_count))

            logger.info(f"Saved search for user {user_id}: {query[:50]}")
            return search_id

    except Exception as e:
        logger.error(f"Failed to save search: {e}", exc_info=True)
        # Don't raise - logging searches shouldn't break the bot
        return ""


def get_product_by_id(product_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a product by its ID.

    Args:
        product_id: The product ID to look up

    Returns:
        Dictionary containing product data, or None if not found

    Example:
        >>> product = get_product_by_id('taobao_12345')
        >>> if product:
        ...     print(f"Title: {product['title']}, Price: {product['price']}")
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
            row = cursor.fetchone()

            if row:
                # Convert sqlite3.Row to dictionary
                return dict(row)
            else:
                logger.debug(f"Product not found: {product_id}")
                return None

    except Exception as e:
        logger.error(f"Failed to get product {product_id}: {e}", exc_info=True)
        return None


def save_price_history(product_id: str, price: float) -> None:
    """
    Save a price snapshot for a product.

    Used to track price changes over time for price alerts
    and historical analysis.

    Args:
        product_id: The product ID
        price: Current price to record

    Example:
        >>> save_price_history('taobao_12345', 15.50)
    """
    try:
        price_id = str(uuid4())

        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO price_history (id, product_id, price)
                VALUES (?, ?, ?)
            """, (price_id, product_id, price))

            logger.debug(f"Saved price history for {product_id}: {price}")

    except Exception as e:
        logger.error(f"Failed to save price history: {e}", exc_info=True)
        # Don't raise - price tracking shouldn't break the bot


def get_price_history(product_id: str, days: int = 7) -> List[Dict[str, Any]]:
    """
    Get price history for a product.

    Retrieves price snapshots from the last N days to show
    price trends and identify good deals.

    Args:
        product_id: The product ID
        days: Number of days to look back (default 7)

    Returns:
        List of dictionaries with 'price' and 'recorded_at' keys,
        ordered from newest to oldest

    Example:
        >>> history = get_price_history('taobao_12345', days=7)
        >>> for record in history:
        ...     print(f"{record['recorded_at']}: ¥{record['price']}")
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(days=days)

            cursor.execute("""
                SELECT price, recorded_at
                FROM price_history
                WHERE product_id = ? AND recorded_at >= ?
                ORDER BY recorded_at DESC
            """, (product_id, cutoff_date.isoformat()))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    except Exception as e:
        logger.error(f"Failed to get price history for {product_id}: {e}", exc_info=True)
        return []


def get_user_search_history(user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get recent searches for a user.

    Useful for showing user their search history and
    quick repeat searches.

    Args:
        user_id: Telegram user ID
        limit: Maximum number of records to return (default 10)

    Returns:
        List of search records, ordered from newest to oldest

    Example:
        >>> history = get_user_search_history('123456789', limit=5)
        >>> for search in history:
        ...     print(f"{search['created_at']}: {search['search_query']}")
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, user_id, username, search_query,
                       parsed_params, results_count, created_at
                FROM search_history
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, limit))

            rows = cursor.fetchall()

            # Convert rows to dictionaries and parse JSON params
            results = []
            for row in rows:
                record = dict(row)
                # Parse the JSON params back to dict
                record['parsed_params'] = json.loads(record['parsed_params'])
                results.append(record)

            return results

    except Exception as e:
        logger.error(f"Failed to get search history for user {user_id}: {e}", exc_info=True)
        return []


def save_scraped_products(
    products: List[Dict[str, Any]],
    platform: str = 'taobao',
    search_id: Optional[str] = None
) -> List[str]:
    """
    Save multiple scraped products to the database.

    Converts scraped product format to database format and saves each product.
    Automatically extracts product_id from URL if not provided.

    Args:
        products: List of scraped product dictionaries from scraper
        platform: Platform name (default 'taobao')
        search_id: Optional search ID to associate products with a search

    Returns:
        List of saved product IDs

    Example:
        >>> scraped = [
        ...     {'title': 'Washi Tape', 'price_cny': 15.5, 'link': '...', ...}
        ... ]
        >>> product_ids = save_scraped_products(scraped, platform='taobao')
        >>> print(f"Saved {len(product_ids)} products")
    """
    saved_ids = []

    try:
        for product in products:
            # Extract product ID from URL or generate from title hash
            product_id = _extract_product_id(product.get('link', '')) or str(hash(product.get('title', '')))[:10]

            # Convert scraped format to database format
            db_product = {
                'platform': platform,
                'product_id': product_id,
                'title': product.get('title', 'Unknown Product'),
                'price': product.get('price_cny', 0.0),
                'currency': 'CNY',
                'sales_count': product.get('sales_count', 0),
                'image_url': product.get('image_url'),
                'product_url': product.get('link'),
            }

            # Save product and add to saved_ids
            saved_id = save_product(db_product)
            saved_ids.append(saved_id)

            # Save price history for tracking
            save_price_history(saved_id, db_product['price'])

        logger.info(f"Saved {len(saved_ids)} scraped products from {platform}")
        return saved_ids

    except Exception as e:
        logger.error(f"Failed to save scraped products: {e}", exc_info=True)
        return saved_ids  # Return partial results


def _extract_product_id(url: str) -> Optional[str]:
    """
    Extract product ID from Taobao/1688 URL.

    Args:
        url: Product URL

    Returns:
        Product ID if found, None otherwise
    """
    import re

    if not url:
        return None

    # Taobao: id=123456
    match = re.search(r'[?&]id=(\d+)', url)
    if match:
        return match.group(1)

    # 1688: offer/123456.html
    match = re.search(r'offer/(\d+)\.html', url)
    if match:
        return match.group(1)

    return None


def get_database_stats() -> Dict[str, int]:
    """
    Get database statistics.

    Returns counts of records in each table for monitoring
    and debugging purposes.

    Returns:
        Dictionary with counts for each table

    Example:
        >>> stats = get_database_stats()
        >>> print(f"Total products: {stats['products']}")
        >>> print(f"Total searches: {stats['searches']}")
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            stats = {}

            # Count products
            cursor.execute("SELECT COUNT(*) as count FROM products")
            stats['products'] = cursor.fetchone()['count']

            # Count searches
            cursor.execute("SELECT COUNT(*) as count FROM search_history")
            stats['searches'] = cursor.fetchone()['count']

            # Count price records
            cursor.execute("SELECT COUNT(*) as count FROM price_history")
            stats['price_records'] = cursor.fetchone()['count']

            return stats

    except Exception as e:
        logger.error(f"Failed to get database stats: {e}", exc_info=True)
        return {'products': 0, 'searches': 0, 'price_records': 0}


def test_database():
    """
    Test database functionality.

    Creates sample data and retrieves it to verify all operations work.
    Run with: python -c "from database.db import test_database; test_database()"
    """
    print("\n" + "=" * 70)
    print("TESTING DATABASE FUNCTIONALITY")
    print("=" * 70)

    try:
        # Initialize database
        print("\n1. Initializing database...")
        init_database()
        print("✅ Database initialized")

        # Test save_product
        print("\n2. Testing save_product...")
        product_id = save_product({
            'platform': 'taobao',
            'product_id': 'TEST123',
            'title': 'Test Washi Tape - Aesthetic Brown',
            'price': 15.50,
            'original_price': 20.00,
            'rating': 4.8,
            'sales_count': 1500,
            'image_url': 'https://example.com/image.jpg',
            'product_url': 'https://example.com/product',
            'color': 'brown'
        })
        print(f"✅ Product saved with ID: {product_id}")

        # Test get_product_by_id
        print("\n3. Testing get_product_by_id...")
        product = get_product_by_id(product_id)
        if product:
            print(f"✅ Product retrieved:")
            print(f"   Title: {product['title']}")
            print(f"   Price: ¥{product['price']}")
            print(f"   Rating: {product['rating']}")

        # Test save_search
        print("\n4. Testing save_search...")
        search_id = save_search(
            user_id='123456789',
            username='test_user',
            query='cari washi tape coklat harga dibawah 50rb',
            parsed_params={
                'keyword': 'washi tape',
                'color': 'brown',
                'max_price': 22,
                'min_rating': None
            },
            results_count=15
        )
        print(f"✅ Search saved with ID: {search_id}")

        # Test get_user_search_history
        print("\n5. Testing get_user_search_history...")
        history = get_user_search_history('123456789', limit=5)
        print(f"✅ Found {len(history)} search(es):")
        for search in history:
            print(f"   - {search['search_query']}")
            print(f"     Params: {search['parsed_params']}")

        # Test save_price_history
        print("\n6. Testing save_price_history...")
        save_price_history(product_id, 15.50)
        save_price_history(product_id, 14.80)
        save_price_history(product_id, 16.20)
        print("✅ Price history saved")

        # Test get_price_history
        print("\n7. Testing get_price_history...")
        price_history = get_price_history(product_id, days=7)
        print(f"✅ Found {len(price_history)} price record(s):")
        for record in price_history:
            print(f"   - {record['recorded_at']}: ¥{record['price']}")

        # Test database stats
        print("\n8. Testing get_database_stats...")
        stats = get_database_stats()
        print("✅ Database statistics:")
        print(f"   Products: {stats['products']}")
        print(f"   Searches: {stats['searches']}")
        print(f"   Price records: {stats['price_records']}")

        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED!")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run tests when executed directly
    test_database()
