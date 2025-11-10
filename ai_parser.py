"""
AI-powered search query parser using Google Gemini.
Parses natural language product search queries into structured parameters.
"""

import json
import logging
import re
from typing import Dict, Any, Optional
import google.generativeai as genai
from config import config

# Configure logging
logger = logging.getLogger(__name__)

# Try to import REST API fallback
try:
    from ai_parser_rest import parse_search_query_rest
    HAS_REST_FALLBACK = True
    logger.info("REST API fallback available")
except ImportError:
    HAS_REST_FALLBACK = False
    logger.warning("REST API fallback not available")

# Configure Gemini API
genai.configure(api_key=config.GEMINI_API_KEY)

# Initialize the Gemini model (using gemini-1.5-flash for faster responses)
model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')


def create_prompt(user_text: str) -> str:
    """
    Create an optimized prompt for Gemini to parse search queries.

    Args:
        user_text: The user's search query

    Returns:
        The complete prompt for Gemini
    """
    prompt = f"""You are a JSON-only parser. You MUST return ONLY valid JSON with NO explanations, NO markdown, NO code blocks.

Parse this product search query into JSON with EXACTLY these fields:
- keyword: main product name/type (string, never null)
- color: color mentioned or null (string or null)
- min_price: minimum price in CNY or null (number or null)
- max_price: maximum price in CNY or null (number or null)
- min_rating: minimum rating 0-5 or null (number or null)
- min_sales: minimum sales count or null (number or null)

CRITICAL RULES:
1. ALWAYS extract the main product as "keyword" - never leave it as the full query
2. For prices in rupiah (rb/ribu/rupiah): DIVIDE by 2300 to get CNY
3. For "dibawah X" or "under X" = max_price only
4. For "diatas X" or "over X" = min_price only
5. For "X-Y" range = both min and max
6. Translate Indonesian colors to English (coklat=brown, hitam=black, putih=white, merah=red, biru=blue, hijau=green, kuning=yellow, pink=pink, ungu=purple)
7. Remove search words like "cari", "search", "find" from keyword
8. For ratings like "4.5+" or "4.5 keatas" = min_rating: 4.5
9. For sales like "1000+ terjual" or "sold 1000+" = min_sales: 1000

EXAMPLES (learn from these):

Input: "cari washi tape aesthetic coklat harga dibawah 50rb rating 4.5+"
Output: {{"keyword":"washi tape aesthetic","color":"brown","min_price":null,"max_price":22,"min_rating":4.5,"min_sales":null}}

Input: "notebook minimalis harga 20rb-100rb"
Output: {{"keyword":"notebook minimalis","color":null,"min_price":9,"max_price":43,"min_rating":null,"min_sales":null}}

Input: "blue backpack under 200 CNY rating 4+"
Output: {{"keyword":"backpack","color":"blue","min_price":null,"max_price":200,"min_rating":4.0,"min_sales":null}}

Input: "sepatu olahraga hitam 100-300rb terjual 1000+"
Output: {{"keyword":"sepatu olahraga","color":"black","min_price":43,"max_price":130,"min_rating":null,"min_sales":1000}}

Input: "cute stickers pink"
Output: {{"keyword":"cute stickers","color":"pink","min_price":null,"max_price":null,"min_rating":null,"min_sales":null}}

NOW PARSE THIS QUERY:
"{user_text}"

RETURN ONLY THE JSON OBJECT - NO OTHER TEXT BEFORE OR AFTER:"""

    return prompt


async def parse_search_query(user_text: str) -> Dict[str, Any]:
    """
    Parse a natural language search query using Gemini AI.

    This function sends the user's search query to Google Gemini API
    and extracts structured search parameters from it.

    Args:
        user_text: The natural language search query from the user.
                  Can be in Indonesian or English.

    Returns:
        A dictionary containing parsed search parameters:
        {
            "keyword": str,           # Product name/type
            "color": str or None,     # Color if specified
            "min_price": int or None, # Minimum price in CNY
            "max_price": int or None, # Maximum price in CNY
            "min_rating": float or None,  # Minimum rating (0-5)
            "min_sales": int or None  # Minimum sold quantity
        }

    Example:
        >>> await parse_search_query("cari washi tape aesthetic coklat harga dibawah 50rb rating 4.5+")
        {
            "keyword": "washi tape aesthetic",
            "color": "brown",
            "min_price": None,
            "max_price": 22,
            "min_rating": 4.5,
            "min_sales": None
        }
    """
    logger.info(f"=" * 70)
    logger.info(f"PARSING QUERY: {user_text}")
    logger.info(f"=" * 70)

    # Default structure to return if parsing fails
    default_result = {
        "keyword": user_text,
        "color": None,
        "min_price": None,
        "max_price": None,
        "min_rating": None,
        "min_sales": None
    }

    try:
        # Create the prompt
        full_prompt = create_prompt(user_text)
        logger.info(f"PROMPT SENT TO GEMINI:\n{full_prompt}\n")

        # Call Gemini API
        logger.info("Sending request to Gemini API...")
        response = model.generate_content(full_prompt)

        # Get the response text
        response_text = response.text.strip()
        logger.info(f"RAW GEMINI RESPONSE:\n{response_text}\n")

        # Try multiple strategies to extract JSON
        parsed_data = _extract_json_robust(response_text)

        if parsed_data is None:
            logger.error("FAILED to extract JSON from response")
            return default_result

        logger.info(f"EXTRACTED JSON: {json.dumps(parsed_data, ensure_ascii=False)}")

        # Validate and normalize the parsed data
        result = _validate_and_normalize(parsed_data, user_text)

        logger.info(f"FINAL PARSED RESULT: {json.dumps(result, ensure_ascii=False, indent=2)}")
        logger.info(f"=" * 70)
        return result

    except Exception as e:
        logger.error(f"SDK ERROR in parse_search_query: {type(e).__name__}: {e}", exc_info=True)

        # Try REST API fallback if available
        if HAS_REST_FALLBACK:
            logger.warning("SDK failed, trying REST API fallback...")
            try:
                return await parse_search_query_rest(user_text)
            except Exception as fallback_error:
                logger.error(f"REST API fallback also failed: {fallback_error}")

        # Final fallback - return default result
        logger.info(f"RETURNING DEFAULT RESULT: {json.dumps(default_result, ensure_ascii=False)}")
        logger.info(f"=" * 70)
        return default_result


def _extract_json_robust(response_text: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON from Gemini response using multiple strategies.

    Tries different methods to handle various response formats:
    1. Direct JSON parsing
    2. Strip markdown code blocks
    3. Extract JSON between curly braces
    4. Remove text before/after JSON

    Args:
        response_text: Raw response from Gemini

    Returns:
        Parsed JSON dict or None if extraction fails
    """
    strategies = [
        ("Direct parsing", lambda t: t),
        ("Strip markdown blocks", _strip_markdown),
        ("Extract JSON braces", _extract_json_braces),
        ("Remove surrounding text", _remove_surrounding_text),
    ]

    for strategy_name, strategy_func in strategies:
        try:
            cleaned = strategy_func(response_text)
            logger.info(f"Trying strategy: {strategy_name}")
            logger.debug(f"Cleaned text: {cleaned[:200]}")

            parsed = json.loads(cleaned)
            logger.info(f"SUCCESS with strategy: {strategy_name}")
            return parsed

        except json.JSONDecodeError as e:
            logger.debug(f"Strategy '{strategy_name}' failed: {e}")
            continue
        except Exception as e:
            logger.debug(f"Strategy '{strategy_name}' error: {e}")
            continue

    logger.error("ALL parsing strategies failed")
    return None


def _strip_markdown(text: str) -> str:
    """Remove markdown code block markers."""
    # Remove ```json and ``` markers
    cleaned = re.sub(r'^```json\s*', '', text, flags=re.MULTILINE | re.IGNORECASE)
    cleaned = re.sub(r'^```\s*', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'\s*```$', '', cleaned, flags=re.MULTILINE)
    return cleaned.strip()


def _extract_json_braces(text: str) -> str:
    """Extract content between first { and last }."""
    # Find the first { and last }
    first_brace = text.find('{')
    last_brace = text.rfind('}')

    if first_brace == -1 or last_brace == -1 or first_brace >= last_brace:
        return text

    return text[first_brace:last_brace + 1]


def _remove_surrounding_text(text: str) -> str:
    """Remove any text before { and after }."""
    # First strip markdown
    cleaned = _strip_markdown(text)
    # Then extract JSON
    return _extract_json_braces(cleaned)


def _validate_and_normalize(parsed_data: Dict[str, Any], original_query: str) -> Dict[str, Any]:
    """
    Validate and normalize the parsed data from Gemini.

    Ensures all required fields exist and have the correct types.
    Converts null/None values appropriately.

    Args:
        parsed_data: The parsed JSON data from Gemini.
        original_query: The original user query (used as fallback for keyword).

    Returns:
        Normalized dictionary with all required fields.
    """
    logger.info(f"Validating parsed data: {parsed_data}")

    # Define required fields and their types
    result = {
        "keyword": parsed_data.get("keyword", original_query),
        "color": parsed_data.get("color"),
        "min_price": parsed_data.get("min_price"),
        "max_price": parsed_data.get("max_price"),
        "min_rating": parsed_data.get("min_rating"),
        "min_sales": parsed_data.get("min_sales")
    }

    # Convert "null" strings to None
    for key in result:
        if result[key] == "null" or result[key] == "":
            result[key] = None

    # Ensure keyword is not None or empty
    if not result["keyword"] or result["keyword"] == original_query:
        logger.warning(f"Keyword was not properly extracted, using original query")
        result["keyword"] = original_query

    # Type conversions and validations
    try:
        # Convert prices to integers if present
        if result["min_price"] is not None:
            result["min_price"] = int(float(result["min_price"]))
            logger.debug(f"Converted min_price to: {result['min_price']}")

        if result["max_price"] is not None:
            result["max_price"] = int(float(result["max_price"]))
            logger.debug(f"Converted max_price to: {result['max_price']}")

        # Convert rating to float if present and validate range
        if result["min_rating"] is not None:
            result["min_rating"] = float(result["min_rating"])
            # Clamp rating between 0 and 5
            result["min_rating"] = max(0.0, min(5.0, result["min_rating"]))
            logger.debug(f"Converted min_rating to: {result['min_rating']}")

        # Convert sales to integer if present
        if result["min_sales"] is not None:
            result["min_sales"] = int(float(result["min_sales"]))
            logger.debug(f"Converted min_sales to: {result['min_sales']}")

    except (ValueError, TypeError) as e:
        logger.warning(f"Type conversion error in parsed data: {e}")
        # Continue with partial data - some fields may remain None

    return result


def test_parser_sync(query: str):
    """
    Synchronous test function for manual testing.

    Usage:
        python -c "from ai_parser import test_parser_sync; test_parser_sync('cari washi tape coklat')"

    Args:
        query: The search query to test
    """
    import asyncio

    print("\n" + "=" * 70)
    print(f"TESTING PARSER WITH QUERY: {query}")
    print("=" * 70)

    result = asyncio.run(parse_search_query(query))

    print("\n" + "=" * 70)
    print("FINAL RESULT:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("=" * 70)

    return result


async def test_parser():
    """
    Test function to validate the parser with example queries.
    Run this to test the AI parser functionality.
    """
    test_queries = [
        "cari washi tape aesthetic coklat harga dibawah 50rb rating 4.5+",
        "notebook minimalis harga 20rb-100rb",
        "blue backpack under 200 CNY rating 4+",
        "sepatu olahraga hitam 100-300rb terjual 1000+",
        "cute stickers pink"
    ]

    print("\n" + "=" * 70)
    print("TESTING AI PARSER WITH MULTIPLE QUERIES")
    print("=" * 70)

    for i, query in enumerate(test_queries, 1):
        print(f"\n[TEST {i}/{len(test_queries)}]")
        result = await parse_search_query(query)
        print(f"\nFormatted Result:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print("\n" + "-" * 70)


if __name__ == "__main__":
    # Run tests when executed directly
    import asyncio
    asyncio.run(test_parser())
