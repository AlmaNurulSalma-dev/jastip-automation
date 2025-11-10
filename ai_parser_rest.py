"""
REST API fallback for Gemini AI parsing.
Uses direct HTTP requests instead of the SDK.
"""

import requests
import json
import logging
import re
from typing import Dict, Any, Optional
from config import config

# Configure logging
logger = logging.getLogger(__name__)


def create_prompt(user_text: str) -> str:
    """
    Create the parsing prompt for Gemini.

    Args:
        user_text: The user's search query

    Returns:
        The complete prompt for Gemini
    """
    prompt = f"""You are a JSON-only parser. Return ONLY valid JSON, no markdown, no explanations, no code blocks.

Parse this product search query into JSON with EXACTLY these fields:
- keyword (string): main product type only, NOT the full query
- color (string or null): color if mentioned, translate to English (e.g., "coklat" → "brown")
- min_price (number or null): minimum price in CNY
- max_price (number or null): maximum price in CNY (convert IDR to CNY by dividing by 2300)
- min_rating (number or null): minimum rating 0-5
- min_sales (number or null): minimum sales count

CRITICAL: Extract the product name as "keyword", NOT the entire query.

Examples:
Input: "cari washi tape coklat harga dibawah 50rb"
Output: {{"keyword":"washi tape","color":"brown","min_price":null,"max_price":22,"min_rating":null,"min_sales":null}}

Input: "notebook aesthetic rating 4.5+"
Output: {{"keyword":"notebook aesthetic","color":null,"min_price":null,"max_price":null,"min_rating":4.5,"min_sales":null}}

Input: "sepatu olahraga hitam 100-300rb terjual 1000+"
Output: {{"keyword":"sepatu olahraga","color":"black","min_price":43,"max_price":130,"min_rating":null,"min_sales":1000}}

Now parse: "{user_text}"

Return ONLY the JSON object, nothing else."""

    return prompt


async def parse_search_query_rest(user_text: str) -> Dict[str, Any]:
    """
    Parse search query using Gemini REST API.

    This is a fallback method that uses direct HTTP requests instead of the SDK.
    It tries multiple model endpoints to find one that works.

    Args:
        user_text: The natural language search query from the user.

    Returns:
        A dictionary containing parsed search parameters.
    """
    logger.info("=" * 70)
    logger.info("USING REST API FALLBACK")
    logger.info(f"PARSING QUERY: {user_text}")
    logger.info("=" * 70)

    # Default result
    default_result = {
        "keyword": user_text,
        "color": None,
        "min_price": None,
        "max_price": None,
        "min_rating": None,
        "min_sales": None
    }

    try:
        api_key = config.GEMINI_API_KEY

        # Try multiple model endpoints in order of preference
        model_endpoints = [
            "gemini-2.5-flash-preview-05-20",
            "gemini-1.5-flash-latest",
            "gemini-1.5-flash",
            "gemini-1.5-pro-latest",
            "gemini-1.5-pro",
            "gemini-pro"
        ]

        for model in model_endpoints:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

                payload = {
                    "contents": [{
                        "parts": [{
                            "text": create_prompt(user_text)
                        }]
                    }],
                    "generationConfig": {
                        "temperature": 0.1,
                        "topK": 1,
                        "topP": 1,
                        "maxOutputTokens": 1024,
                    }
                }

                logger.info(f"Trying model: {model}")
                logger.debug(f"Request URL: {url.split('?')[0]}")

                response = requests.post(url, json=payload, timeout=30)

                logger.info(f"Response status: {response.status_code}")

                if response.status_code == 200:
                    result = response.json()
                    text = result['candidates'][0]['content']['parts'][0]['text']

                    logger.info(f"✅ SUCCESS with model: {model}")
                    logger.info(f"RAW RESPONSE:\n{text}\n")

                    # Extract and parse JSON
                    parsed_data = _extract_and_parse_json(text)

                    if parsed_data:
                        # Validate and normalize
                        validated = _validate_and_normalize(parsed_data, user_text)
                        logger.info(f"FINAL RESULT: {json.dumps(validated, ensure_ascii=False)}")
                        logger.info("=" * 70)
                        return validated
                    else:
                        logger.warning("Failed to extract JSON from response")
                        continue

                elif response.status_code == 404:
                    logger.warning(f"Model {model} not found (404)")
                    continue
                else:
                    logger.warning(f"Model {model} returned status {response.status_code}")
                    logger.debug(f"Response: {response.text[:200]}")
                    continue

            except requests.exceptions.Timeout:
                logger.warning(f"Model {model} timed out")
                continue
            except requests.exceptions.RequestException as e:
                logger.warning(f"Model {model} request failed: {e}")
                continue
            except Exception as e:
                logger.warning(f"Model {model} error: {e}")
                continue

        # All models failed
        logger.error("All Gemini models failed")
        logger.info(f"RETURNING DEFAULT RESULT: {json.dumps(default_result, ensure_ascii=False)}")
        logger.info("=" * 70)
        return default_result

    except Exception as e:
        logger.error(f"REST API Error: {e}", exc_info=True)
        logger.info("=" * 70)
        return default_result


def _extract_and_parse_json(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract and parse JSON from Gemini response.

    Tries multiple strategies to extract valid JSON.

    Args:
        text: Raw text response from Gemini

    Returns:
        Parsed JSON dict or None
    """
    # Strategy 1: Direct parsing
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Strategy 2: Strip markdown code blocks
    cleaned = text.strip()
    if '```json' in cleaned:
        cleaned = cleaned.split('```json')[1].split('```')[0].strip()
    elif '```' in cleaned:
        cleaned = cleaned.split('```')[1].split('```')[0].strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Strategy 3: Extract between { and }
    start = text.find('{')
    end = text.rfind('}') + 1
    if start != -1 and end > start:
        json_text = text[start:end]
        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            pass

    return None


def _validate_and_normalize(parsed_data: Dict[str, Any], original_query: str) -> Dict[str, Any]:
    """
    Validate and normalize the parsed data.

    Args:
        parsed_data: The parsed JSON data from Gemini.
        original_query: The original user query.

    Returns:
        Normalized dictionary with all required fields.
    """
    # Define required fields
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
    if not result["keyword"]:
        result["keyword"] = original_query

    # Type conversions
    try:
        if result["min_price"] is not None:
            result["min_price"] = int(float(result["min_price"]))
        if result["max_price"] is not None:
            result["max_price"] = int(float(result["max_price"]))
        if result["min_rating"] is not None:
            result["min_rating"] = float(result["min_rating"])
            result["min_rating"] = max(0.0, min(5.0, result["min_rating"]))
        if result["min_sales"] is not None:
            result["min_sales"] = int(float(result["min_sales"]))
    except (ValueError, TypeError) as e:
        logger.warning(f"Type conversion error: {e}")

    return result


def test_parser_sync(query: str):
    """
    Synchronous test function for manual testing.

    Usage:
        python -c "from ai_parser_rest import test_parser_sync; test_parser_sync('cari washi tape coklat')"

    Args:
        query: The search query to test
    """
    import asyncio

    print("\n" + "=" * 70)
    print(f"TESTING REST API PARSER WITH QUERY: {query}")
    print("=" * 70)

    result = asyncio.run(parse_search_query_rest(query))

    print("\n" + "=" * 70)
    print("FINAL RESULT:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("=" * 70)

    return result


if __name__ == "__main__":
    # Test when run directly
    import asyncio

    test_query = "cari washi tape aesthetic coklat harga dibawah 50rb rating 4.5+"
    asyncio.run(parse_search_query_rest(test_query))
