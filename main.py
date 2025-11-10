"""
Telegram Bot for Jastip Automation.
A production-ready bot with proper error handling and logging.
"""

import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from config import config
from ai_parser import parse_search_query
from database import init_database, save_search, save_scraped_products
from taobao_scraper import search_taobao
from urllib.parse import quote

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

# Set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /start command.
    Sends a welcome message to the user.

    Args:
        update: The incoming update.
        context: The context object for the handler.
    """
    user = update.effective_user
    welcome_message = (
        f"Hello {user.mention_html()}! 👋\n\n"
        "Welcome to Jastip Automation Bot! 🤖\n\n"
        "I can help you search for products on 1688.com (Alibaba wholesale)!\n\n"
        "📋 Available commands:\n"
        "/start - Show this welcome message\n"
        "/help - Get help information\n"
        "/manual_search - Manual search instructions\n\n"
        "💡 How to use:\n"
        "1. Send a search query (e.g., \"washi tape coklat under 50rb\")\n"
        "2. I'll search 1688.com and show results\n"
        "3. If CAPTCHA appears, I'll give you manual search instructions\n\n"
        "🔍 I can extract:\n"
        "• Product keyword\n"
        "• Color preferences\n"
        "• Price range (converts IDR to CNY)\n"
        "• Minimum rating & sales\n\n"
        "Try it now! Example: \"cari notebook aesthetic 20-50rb\""
    )

    try:
        await update.message.reply_html(welcome_message)
        logger.info(f"User {user.id} ({user.username}) started the bot")
    except Exception as e:
        logger.error(f"Error in start_command: {e}")
        await update.message.reply_text("Sorry, an error occurred. Please try again.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /help command.
    Provides help information to the user.

    Args:
        update: The incoming update.
        context: The context object for the handler.
    """
    help_text = (
        "🤖 Jastip Automation Bot - Help\n\n"
        "This bot uses Google Gemini AI to parse your product search queries!\n\n"
        "📝 How to use:\n"
        "Simply send a product search query in Indonesian or English.\n\n"
        "🔍 What I can extract:\n"
        "• Product name/keyword\n"
        "• Color preferences\n"
        "• Price range (automatically converts IDR to CNY)\n"
        "• Minimum rating (0-5 scale)\n"
        "• Minimum sales quantity\n\n"
        "💡 Example queries:\n"
        "• \"cari washi tape aesthetic coklat harga dibawah 50rb rating 4.5+\"\n"
        "• \"notebook minimalis harga 20rb-100rb\"\n"
        "• \"blue backpack under 200 CNY rating 4+\"\n"
        "• \"sepatu olahraga hitam 100-300rb terjual 1000+\"\n\n"
        "💰 Price conversion:\n"
        "• Prices in Rupiah (rb/ribu) are automatically converted to CNY\n"
        "• Conversion rate: 1 CNY ≈ 2300 IDR\n\n"
        "📋 Available Commands:\n"
        "/start - Show welcome message\n"
        "/help - Show this help message\n"
        "/manual_search - Get manual search instructions for 1688\n\n"
        "⚠️ Note: 1688 sometimes requires verification (CAPTCHA). "
        "When this happens, I'll provide manual search instructions.\n\n"
        "Try sending a search query now!"
    )

    try:
        await update.message.reply_text(help_text)
        logger.info(f"Help command used by user {update.effective_user.id}")
    except Exception as e:
        logger.error(f"Error in help_command: {e}")


async def manual_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /manual_search command.
    Provides manual search instructions when automated scraping fails.

    Args:
        update: The incoming update.
        context: The context object for the handler.
    """
    manual_search_text = (
        "🔍 Manual Search Instructions\n\n"
        "When automated scraping is blocked by 1688's CAPTCHA:\n\n"
        "**Method 1: Direct Search**\n"
        "1. Go to https://s.1688.com\n"
        "2. Enter your search keyword\n"
        "3. Solve the CAPTCHA if prompted\n"
        "4. Copy any product link\n"
        "5. Send the link to me\n\n"
        "**Method 2: Send Product Link**\n"
        "Just send me any 1688 product URL like:\n"
        "• https://detail.1688.com/offer/123456.html\n"
        "• http://m.1688.com/offer/123456.html\n\n"
        "I'll extract the product details for you!\n\n"
        "💡 Tip: After solving one CAPTCHA, automated scraping "
        "usually works again for a while."
    )

    try:
        await update.message.reply_text(manual_search_text)
        logger.info(f"Manual search command used by user {update.effective_user.id}")
    except Exception as e:
        logger.error(f"Error in manual_search_command: {e}")


async def echo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Parse user search query using AI and return structured parameters.
    Also handles 1688 product links sent by users.
    This handler processes any text message that is not a command.

    Args:
        update: The incoming update.
        context: The context object for the handler.
    """
    status_message = None
    try:
        user_message = update.message.text
        user_id = update.effective_user.id

        # Check if message is a 1688 product link
        if _is_1688_product_link(user_message):
            await handle_product_link(update, context)
            return

        # Send "typing" action and status message to show bot is processing
        await update.message.chat.send_action(action="typing")

        # Send a status message
        status_message = await update.message.reply_text(
            "🔄 Parsing your search query with AI...",
            reply_to_message_id=update.message.message_id
        )

        logger.info(f"Processing search query from user {user_id}: {user_message[:100]}")

        # Parse the search query using Gemini AI
        parsed_params = await parse_search_query(user_message)

        # Check if parsing was successful (i.e., keyword is not the full query)
        parsing_successful = (
            parsed_params['keyword'] != user_message or
            any(parsed_params.get(key) is not None for key in ['color', 'min_price', 'max_price', 'min_rating', 'min_sales'])
        )

        # Update status: Scraping 1688
        await status_message.edit_text(
            "✅ Query parsed!\n🔄 Searching 1688.com for products..."
        )

        # Scrape 1688 for products
        products = []
        scraping_failed = False
        try:
            logger.info(f"Scraping 1688 for: {parsed_params['keyword']}, max_price: {parsed_params.get('max_price')}")
            products = await search_taobao(
                keyword=parsed_params['keyword'],
                max_price_cny=parsed_params.get('max_price'),
                limit=10,  # Limit to 10 products
                platform='1688'  # Use 1688 instead of Taobao
            )
            logger.info(f"Scraped {len(products)} products from 1688")

            # Check if scraping returned no results (likely CAPTCHA)
            if not products:
                scraping_failed = True

        except Exception as scrape_error:
            logger.error(f"Failed to scrape 1688: {scrape_error}", exc_info=True)
            scraping_failed = True

        # Save products to database
        saved_product_ids = []
        if products:
            try:
                await status_message.edit_text(
                    "✅ Query parsed!\n✅ Products found!\n🔄 Saving to database..."
                )
                saved_product_ids = save_scraped_products(products, platform='1688')
                logger.info(f"Saved {len(saved_product_ids)} products to database")
            except Exception as save_error:
                logger.error(f"Failed to save products: {save_error}", exc_info=True)

        # Save search to database
        try:
            save_search(
                user_id=str(user_id),
                username=update.effective_user.username,
                query=user_message,
                parsed_params=parsed_params,
                results_count=len(products)
            )
            logger.debug(f"Search saved to database for user {user_id}")
        except Exception as db_error:
            # Log but don't fail if database save fails
            logger.warning(f"Failed to save search to database: {db_error}")

        # Format the response with parsed parameters and products
        response = _format_parsed_response(
            user_message,
            parsed_params,
            parsing_successful,
            products,
            scraping_failed=scraping_failed
        )

        # Update the status message with the result
        await status_message.edit_text(response)

        logger.info(f"Successfully parsed and responded to user {user_id}")

    except Exception as e:
        logger.error(f"Error in echo_handler: {e}", exc_info=True)

        error_message = (
            "❌ Sorry, I encountered an error while parsing your query.\n"
            "Please try again or rephrase your search.\n\n"
            f"Error: {str(e)[:100]}"
        )

        if status_message:
            await status_message.edit_text(error_message)
        else:
            await update.message.reply_text(error_message)


def _format_parsed_response(
    original_query: str,
    params: dict,
    parsing_successful: bool = True,
    products: list = None,
    scraping_failed: bool = False
) -> str:
    """
    Format the parsed search parameters and products into a user-friendly message.

    Args:
        original_query: The original search query from the user.
        params: Dictionary containing parsed search parameters.
        parsing_successful: Whether the parsing was successful (extracted parameters beyond just keyword).
        products: List of scraped products to display.
        scraping_failed: Whether scraping failed (CAPTCHA or error).

    Returns:
        Formatted string with parsed parameters, active filters, and products.
    """
    # Build the response message
    if parsing_successful:
        response = "✅ Search Query Parsed Successfully!\n\n"
    else:
        response = "⚠️ Partial Parse - Using Keyword Search\n\n"

    response += f"📝 Original Query:\n\"{original_query}\"\n\n"
    response += "🔍 Extracted Parameters:\n"
    response += "─" * 30 + "\n\n"

    # Keyword (always present)
    response += f"📦 Keyword: {params['keyword']}\n"

    # Color (optional)
    if params['color']:
        response += f"🎨 Color: {params['color']}\n"

    # Price range (optional)
    if params['min_price'] is not None or params['max_price'] is not None:
        if params['min_price'] is not None and params['max_price'] is not None:
            response += f"💰 Price Range: ¥{params['min_price']} - ¥{params['max_price']} CNY\n"
        elif params['min_price'] is not None:
            response += f"💰 Min Price: ¥{params['min_price']} CNY\n"
        elif params['max_price'] is not None:
            response += f"💰 Max Price: ¥{params['max_price']} CNY\n"

    # Rating (optional)
    if params['min_rating'] is not None:
        stars = "⭐" * int(params['min_rating'])
        response += f"⭐ Min Rating: {params['min_rating']}/5 {stars}\n"

    # Sales (optional)
    if params['min_sales'] is not None:
        response += f"📊 Min Sales: {params['min_sales']:,} units\n"

    # Add summary of active filters
    response += "\n" + "─" * 30 + "\n"
    active_filters = []
    if params['color']:
        active_filters.append("Color")
    if params['min_price'] is not None or params['max_price'] is not None:
        active_filters.append("Price")
    if params['min_rating'] is not None:
        active_filters.append("Rating")
    if params['min_sales'] is not None:
        active_filters.append("Sales")

    if active_filters:
        response += f"\n✓ Active Filters: {', '.join(active_filters)}"
    else:
        response += "\n💡 No filters specified - showing all results for keyword"

    # Add products section if available
    if products:
        response += f"\n\n🛒 Found {len(products)} Products:\n"
        response += "═" * 30 + "\n\n"

        for i, product in enumerate(products[:5], 1):  # Show top 5 products
            response += f"{i}. {product.get('title', 'N/A')[:60]}\n"
            response += f"   💰 Price: ¥{product.get('price_cny', 0):.2f}\n"
            response += f"   🏪 Shop: {product.get('shop_name', 'Unknown')}\n"
            if product.get('sales_count'):
                response += f"   📊 Sales: {product.get('sales_count'):,}\n"
            if product.get('link'):
                response += f"   🔗 Link: {product.get('link')}\n"
            response += "\n"

        if len(products) > 5:
            response += f"... and {len(products) - 5} more products saved to database!\n"

    elif products is not None and scraping_failed:
        # Scraping failed - likely CAPTCHA
        response += "\n\n🤖 1688 requires verification to continue.\n\n"
        response += "📋 **Manual Search Option:**\n"
        response += f"1. Open: https://s.1688.com/selloffer/offer_search.htm?keywords={quote(params['keyword'])}\n"
        response += "2. Solve the slider CAPTCHA\n"
        response += "3. Copy any product link from results\n"
        response += "4. Send the link back to me\n\n"
        response += "Or use /manual_search to search manually\n"
        response += "Or try again in a few minutes!\n\n"
        response += "⚠️ Note: 1688 sometimes requires verification. This is normal for wholesale sites."

    elif products is not None:
        # Scraping was attempted but no products found (not CAPTCHA, just no results)
        response += "\n\n⚠️ No products found matching your criteria.\n"
        response += "Try adjusting your search filters or keywords.\n\n"
        response += "⚠️ Note: 1688 sometimes requires verification for automated searches."

    # Add tip if parsing failed
    if not parsing_successful:
        response += "\n\n💡 Tip: Try being more specific with filters like:\n"
        response += "• Price: 'harga 20rb-50rb' or 'under 100 CNY'\n"
        response += "• Color: 'hitam', 'pink', 'blue'\n"
        response += "• Rating: 'rating 4+' or 'rating 4.5 keatas'\n"
        response += "• Sales: 'terjual 1000+'"

    return response


def _is_1688_product_link(text: str) -> bool:
    """
    Check if the text is a 1688 product link.

    Args:
        text: Message text to check

    Returns:
        True if it's a 1688 product link, False otherwise
    """
    import re
    # Pattern for 1688 product URLs
    pattern = r'(https?://)?(detail\.|m\.)?1688\.com/(offer|page)/\S+'
    return bool(re.search(pattern, text, re.IGNORECASE))


async def handle_product_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle when user sends a 1688 product link.

    Args:
        update: The incoming update.
        context: The context object for the handler.
    """
    try:
        user_message = update.message.text
        user_id = update.effective_user.id

        await update.message.chat.send_action(action="typing")

        status_message = await update.message.reply_text(
            "🔗 Detected 1688 product link!\n🔄 Extracting product details...",
            reply_to_message_id=update.message.message_id
        )

        logger.info(f"Processing 1688 product link from user {user_id}")

        # For now, provide the link info and acknowledge
        # TODO: In future, could scrape individual product page
        response = (
            "🔗 **1688 Product Link Received**\n\n"
            f"Link: {user_message}\n\n"
            "📋 To view product details:\n"
            "1. Click the link above\n"
            "2. If you see CAPTCHA, solve it\n"
            "3. You'll see full product details\n\n"
            "💡 **Future Feature:**\n"
            "I'll soon be able to extract product details "
            "directly from individual product links!\n\n"
            "For now, you can:\n"
            "• View the product on 1688\n"
            "• Send me a search query instead (e.g., \"washi tape 20-50rb\")\n"
            "• Use /manual_search for instructions"
        )

        await status_message.edit_text(response)
        logger.info(f"Product link acknowledged for user {user_id}")

    except Exception as e:
        logger.error(f"Error handling product link: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Sorry, I encountered an error processing your product link.\n"
            "Please try sending a search query instead!"
        )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle errors that occur during update processing.

    Args:
        update: The update that caused the error.
        context: The context object containing error information.
    """
    logger.error(f"Exception while handling an update: {context.error}", exc_info=True)

    # Try to send error message to user if update is available
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "An error occurred while processing your request. "
                "The error has been logged and will be investigated."
            )
        except Exception as e:
            logger.error(f"Could not send error message to user: {e}")


def main() -> None:
    """
    Main function to start the bot.
    Initializes the application, registers handlers, and starts polling.
    """
    try:
        logger.info("Starting Jastip Automation Bot...")

        # Initialize database
        logger.info("Initializing database...")
        init_database()
        logger.info("Database ready")

        # Create the Application instance
        application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

        # Register command handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("manual_search", manual_search_command))

        # Register message handler for text messages (excluding commands)
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, echo_handler)
        )

        # Register error handler
        application.add_error_handler(error_handler)

        # Start the bot
        logger.info("Bot is now running. Press Ctrl+C to stop.")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C)")
    except Exception as e:
        logger.critical(f"Critical error in main: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
