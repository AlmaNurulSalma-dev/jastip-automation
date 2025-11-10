"""
Test if the Gemini API key is valid and what models are available.
This will help diagnose 404 errors.
"""
import os
from dotenv import load_dotenv
import requests
import json

def print_header(text):
    print("\n" + "=" * 70)
    print(text)
    print("=" * 70)

def test_api_key():
    load_dotenv()
    api_key = os.getenv('GEMINI_API_KEY')

    if not api_key:
        print("❌ ERROR: GEMINI_API_KEY not found in .env file")
        return False

    print(f"Testing API Key: {api_key[:15]}...{api_key[-5:]}")

    # Test 1: List all models
    print_header("TEST 1: Listing Available Models")
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            models = data.get('models', [])

            print(f"\n✅ API KEY IS VALID!")
            print(f"Found {len(models)} total models")

            # Filter models that support generateContent
            valid_models = []
            print("\n📋 Models that support generateContent:")
            for model in models:
                methods = model.get('supportedGenerationMethods', [])
                if 'generateContent' in methods:
                    valid_models.append(model['name'])
                    print(f"  ✅ {model['name']}")
                    print(f"     Display: {model.get('displayName', 'N/A')}")

            if valid_models:
                print(f"\n🎯 RECOMMENDED MODEL TO USE:")
                # Prefer flash models
                for model in valid_models:
                    if 'flash' in model.lower():
                        print(f"   {model}")
                        return model
                # Otherwise use first available
                print(f"   {valid_models[0]}")
                return valid_models[0]
            else:
                print("\n⚠️ WARNING: No models support generateContent")
                return None

        elif response.status_code == 400:
            print(f"\n❌ API KEY IS INVALID")
            error_data = response.json()
            print(f"Error: {json.dumps(error_data, indent=2)}")
            print("\n🔧 FIX: Generate a new API key at:")
            print("   https://aistudio.google.com/app/apikey")
            return False

        elif response.status_code == 403:
            print(f"\n❌ API ACCESS DENIED")
            error_data = response.json()
            print(f"Error: {json.dumps(error_data, indent=2)}")
            print("\n🔧 FIX: Enable the Generative Language API:")
            print("   1. Go to: https://console.cloud.google.com/")
            print("   2. Select your project")
            print("   3. Enable 'Generative Language API'")
            return False

        else:
            print(f"\n❌ UNEXPECTED ERROR: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except requests.exceptions.Timeout:
        print("\n❌ REQUEST TIMEOUT")
        print("Check your internet connection")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False

def test_model_generation(model_name):
    """Test if a specific model can generate content"""
    load_dotenv()
    api_key = os.getenv('GEMINI_API_KEY')

    print_header(f"TEST 2: Testing Content Generation with {model_name}")

    url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={api_key}"

    payload = {
        "contents": [{
            "parts": [{
                "text": "Say 'Hello, API is working!'"
            }]
        }]
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            text = data['candidates'][0]['content']['parts'][0]['text']
            print(f"\n✅ GENERATION WORKS!")
            print(f"Response: {text}")
            return True
        else:
            print(f"\n❌ GENERATION FAILED")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    print_header("GEMINI API KEY DIAGNOSTIC TOOL")

    result = test_api_key()

    if result and isinstance(result, str):
        # Test content generation
        test_model_generation(result)

        print_header("SUMMARY & NEXT STEPS")
        print(f"✅ Your API key is valid")
        print(f"✅ Recommended model: {result}")
        print(f"\n📝 Update ai_parser.py to use this model:")
        model_id = result.replace('models/', '')
        print(f"   model = genai.GenerativeModel('{model_id}')")
        print(f"\n🚀 Or run auto-fix:")
        print(f"   python fix_api_config.py")
        print(f"\n🚀 Then run the bot:")
        print(f"   python main.py")
    else:
        print_header("SUMMARY")
        print("❌ API key validation failed")
        print("\n🔧 ACTION REQUIRED:")
        print("1. Go to: https://aistudio.google.com/app/apikey")
        print("2. Create a NEW API key")
        print("3. Update .env file with new key:")
        print("   GEMINI_API_KEY=your_new_key_here")
        print("4. Run this script again: python test_api_key.py")
