"""
Database package for Jastip Automation Bot.

Provides database functionality for storing products, search history,
and price tracking.
"""

from .db import (
    init_database,
    save_product,
    save_search,
    save_scraped_products,
    get_product_by_id,
    save_price_history,
    get_price_history,
    get_user_search_history,
    get_database_stats,
)

__all__ = [
    'init_database',
    'save_product',
    'save_search',
    'save_scraped_products',
    'get_product_by_id',
    'save_price_history',
    'get_price_history',
    'get_user_search_history',
    'get_database_stats',
]
