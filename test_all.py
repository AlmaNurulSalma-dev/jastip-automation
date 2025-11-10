"""
Automated testing script for Gemini API compatibility.
Runs all diagnostics and tests in sequence.
"""

import subprocess
import sys
import os

def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def run_command(description, command):
    """Run a command and handle errors."""
    print_section(description)
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=False,
            capture_output=False,
            text=True
        )
        if result.returncode != 0:
            print(f"\n⚠️ Warning: Command exited with code {result.returncode}")
        return result.returncode == 0
    except Exception as e:
        print(f"\n❌ Error running command: {e}")
        return False


def main():
    """Main testing function."""
    print("\n" + "=" * 70)
    print("  GEMINI API COMPATIBILITY TEST SUITE")
    print("=" * 70)

    # Check if we're in the right directory
    if not os.path.exists('config.py'):
        print("\n❌ Error: Must run from jastip-automation directory")
        sys.exit(1)

    results = {}

    # Step 1: Upgrade library
    print_section("STEP 1: Upgrading google-generativeai library")
    print("This may take a moment...")
    results['upgrade'] = run_command(
        "Upgrading Library",
        f"{sys.executable} -m pip install --upgrade google-generativeai requests"
    )

    # Step 2: Check models
    results['models'] = run_command(
        "STEP 2: Checking Available Models",
        f"{sys.executable} check_models.py"
    )

    # Step 3: Test SDK parser
    print_section("STEP 3: Testing SDK Parser")
    test_query = "cari washi tape coklat harga dibawah 50rb"
    print(f"Test query: \"{test_query}\"\n")
    results['sdk'] = run_command(
        "SDK Parser Test",
        f"{sys.executable} -c \"from ai_parser import test_parser_sync; test_parser_sync('{test_query}')\""
    )

    # Step 4: Test REST API parser
    print_section("STEP 4: Testing REST API Parser")
    print(f"Test query: \"{test_query}\"\n")
    results['rest'] = run_command(
        "REST API Parser Test",
        f"{sys.executable} -c \"from ai_parser_rest import test_parser_sync; test_parser_sync('{test_query}')\""
    )

    # Summary
    print_section("TEST SUMMARY")

    print("Results:")
    print(f"  Library Upgrade: {'✅ Success' if results.get('upgrade') else '❌ Failed'}")
    print(f"  Model Check:     {'✅ Success' if results.get('models') else '❌ Failed'}")
    print(f"  SDK Parser:      {'✅ Success' if results.get('sdk') else '❌ Failed'}")
    print(f"  REST Parser:     {'✅ Success' if results.get('rest') else '❌ Failed'}")

    print("\n" + "-" * 70)

    if results.get('sdk') or results.get('rest'):
        print("\n✅ At least one parser is working!")
        print("\nYou can now run the bot with:")
        print("  python main.py")
    else:
        print("\n❌ Both parsers failed!")
        print("\nTroubleshooting steps:")
        print("1. Check your GEMINI_API_KEY in .env file")
        print("2. Verify API key at: https://makersuite.google.com/app/apikey")
        print("3. Check bot.log for detailed error messages")
        print("4. Ensure you have internet connectivity")

    print("\n" + "=" * 70)
    print("  TESTING COMPLETE")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Testing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        sys.exit(1)
