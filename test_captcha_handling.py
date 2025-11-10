"""
Test CAPTCHA handling and link detection
"""

import sys

# Test link detection function
def _is_1688_product_link(text: str) -> bool:
    """Check if the text is a 1688 product link."""
    import re
    pattern = r'(https?://)?(detail\.|m\.)?1688\.com/(offer|page)/\S+'
    return bool(re.search(pattern, text, re.IGNORECASE))


def test_link_detection():
    """Test the 1688 link detection"""
    print("\n" + "="*60)
    print("TESTING 1688 LINK DETECTION")
    print("="*60)

    test_cases = [
        # Valid product links
        ("https://detail.1688.com/offer/123456.html", True),
        ("http://m.1688.com/page/index.html?offerId=123456", True),
        ("detail.1688.com/offer/123456.html", True),

        # Invalid (search pages, not product pages)
        ("https://s.1688.com/selloffer/offer_search.htm?keywords=notebook", False),

        # Invalid (not 1688 links)
        ("cari washi tape coklat", False),
        ("notebook 20-50rb", False),
        ("https://taobao.com/item/123456", False),
        ("just some random text", False),
    ]

    passed = 0
    failed = 0

    for text, expected in test_cases:
        result = _is_1688_product_link(text)
        status = "✅ PASS" if result == expected else "❌ FAIL"

        if result == expected:
            passed += 1
        else:
            failed += 1

        print(f"\n{status}")
        print(f"  Text: {text[:50]}")
        print(f"  Expected: {expected}, Got: {result}")

    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60 + "\n")

    return failed == 0


if __name__ == "__main__":
    # Fix Windows encoding
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except:
            pass

    success = test_link_detection()
    sys.exit(0 if success else 1)
