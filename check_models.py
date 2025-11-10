"""
Diagnostic script to check available Gemini models.
Run this to see which models work with your API key.
"""

import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 70)
print("CHECKING AVAILABLE GEMINI MODELS")
print("=" * 70)

try:
    # Configure API
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ ERROR: GEMINI_API_KEY not found in .env file")
        exit(1)

    genai.configure(api_key=api_key)
    print(f"\n✓ API Key configured (length: {len(api_key)})")

    # List all models
    print("\nFetching available models...")
    models = list(genai.list_models())
    supported_models = []

    print(f"\nTotal models found: {len(models)}")
    print("\n" + "-" * 70)

    for model in models:
        if 'generateContent' in model.supported_generation_methods:
            supported_models.append(model.name)
            print(f"\n✅ {model.name}")
            print(f"   Display Name: {model.display_name}")
            print(f"   Description: {model.description[:100] if model.description else 'N/A'}")

    print("\n" + "=" * 70)
    print(f"FOUND {len(supported_models)} MODELS THAT SUPPORT generateContent")
    print("=" * 70)

    if supported_models:
        print("\nRECOMMENDED MODEL TO USE:")
        # Prefer flash models for speed
        recommended = None
        for model in supported_models:
            if 'flash' in model.lower():
                recommended = model
                break

        if recommended:
            print(f"  → {recommended}")
        else:
            # Fallback to first available
            recommended = supported_models[0]
            print(f"  → {recommended}")

        print("\nTo use this model, update ai_parser.py line 20:")
        model_id = recommended.split('/')[-1]  # Extract just the model name
        print(f"  model = genai.GenerativeModel('{model_id}')")

    else:
        print("\n⚠️ WARNING: No models found that support generateContent")
        print("This might indicate an API key or permissions issue.")

    # Try to test the recommended model
    if supported_models:
        print("\n" + "=" * 70)
        print("TESTING RECOMMENDED MODEL")
        print("=" * 70)

        model_id = recommended.split('/')[-1]
        print(f"\nTesting model: {model_id}")

        try:
            test_model = genai.GenerativeModel(model_id)
            response = test_model.generate_content("Say 'test successful' if you can read this.")
            print(f"✅ Model works! Response: {response.text[:100]}")
        except Exception as e:
            print(f"❌ Model test failed: {e}")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    print("\nTROUBLESHOOTING:")
    print("1. Check your GEMINI_API_KEY in .env file")
    print("2. Upgrade library: pip install --upgrade google-generativeai")
    print("3. Try generating a new API key at https://makersuite.google.com/app/apikey")
    print("4. Ensure your API key has the necessary permissions")

print("\n" + "=" * 70)
