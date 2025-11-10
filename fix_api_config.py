"""
Automatically detect working model and update ai_parser.py and ai_parser_rest.py
"""
import os
import re
from test_api_key import test_api_key

def update_model_in_file(model_name):
    """Update the model name in ai_parser.py"""

    file_path = 'ai_parser.py'

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract just the model ID without 'models/' prefix
        model_id = model_name.replace('models/', '')

        # Find and replace model initialization
        # Pattern: model = genai.GenerativeModel('...')
        pattern = r"model = genai\.GenerativeModel\(['\"]([^'\"]+)['\"]\)"

        def replace_model(match):
            old_model = match.group(1)
            print(f"  Changing SDK model: {old_model} → {model_id}")
            return f"model = genai.GenerativeModel('{model_id}')"

        new_content = re.sub(pattern, replace_model, content)

        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"✅ Updated {file_path}")
            return True
        else:
            print(f"⚠️ No model initialization found in {file_path}")
            return False

    except Exception as e:
        print(f"❌ Error updating file: {e}")
        return False

def update_rest_api_models(working_model):
    """Update model list in ai_parser_rest.py"""

    file_path = 'ai_parser_rest.py'

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract just the model name without 'models/' prefix
        model_name = working_model.replace('models/', '')

        # Find the model_endpoints list
        pattern = r'model_endpoints = \[(.*?)\]'

        # Create new list with working model first
        new_endpoints = f"""model_endpoints = [
            "{model_name}",
            "gemini-1.5-flash-latest",
            "gemini-1.5-flash",
            "gemini-1.5-pro-latest",
            "gemini-1.5-pro",
            "gemini-pro"
        ]"""

        print(f"  Updating REST API models list (prioritizing {model_name})")

        new_content = re.sub(pattern, new_endpoints, content, flags=re.DOTALL)

        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"✅ Updated {file_path}")
            return True
        else:
            print(f"⚠️ Could not update model list in {file_path}")
            return False

    except Exception as e:
        print(f"❌ Error updating REST API file: {e}")
        return False

if __name__ == "__main__":
    print("=" * 70)
    print("AUTO-FIX: Detecting working Gemini model...")
    print("=" * 70)

    working_model = test_api_key()

    if working_model and isinstance(working_model, str):
        print(f"\n✅ Found working model: {working_model}")
        print("\nUpdating configuration files...")
        print("-" * 70)

        success_count = 0

        # Update SDK version
        if update_model_in_file(working_model):
            success_count += 1

        # Update REST API version
        if update_rest_api_models(working_model):
            success_count += 1

        print("-" * 70)

        if success_count > 0:
            print("\n" + "=" * 70)
            print("✅ AUTO-FIX COMPLETE!")
            print("=" * 70)
            print(f"\nUpdated {success_count} configuration file(s)")
            print(f"Using model: {working_model}")
            print("\n🚀 Next steps:")
            print("1. Run the bot: python main.py")
            print("2. Test in Telegram with: 'cari washi tape coklat'")
        else:
            print("\n" + "=" * 70)
            print("⚠️ AUTO-FIX PARTIAL")
            print("=" * 70)
            print("\nModel detected but files could not be updated")
            print(f"\nManually update ai_parser.py line ~28:")
            model_id = working_model.replace('models/', '')
            print(f"  model = genai.GenerativeModel('{model_id}')")

    else:
        print("\n" + "=" * 70)
        print("❌ AUTO-FIX FAILED")
        print("=" * 70)
        print("\n🔧 Manual action required:")
        print("1. Generate new API key: https://aistudio.google.com/app/apikey")
        print("2. Update .env file:")
        print("   GEMINI_API_KEY=your_new_key_here")
        print("3. Run: python fix_api_config.py")
        print("\nOR:")
        print("   Check if you have internet connection")
        print("   Verify API key is correct in .env file")
