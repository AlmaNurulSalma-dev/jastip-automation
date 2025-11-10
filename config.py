"""
Configuration module for Telegram Bot.
Handles environment variables and application settings.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """
    Configuration class for managing bot settings.
    All sensitive data should be stored in environment variables.
    """

    def __init__(self):
        """Initialize configuration and validate required settings."""
        self._telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self._gemini_api_key = os.getenv('GEMINI_API_KEY')
        self._validate_config()

    def _validate_config(self):
        """
        Validate that all required configuration values are present.
        Raises SystemExit if validation fails.
        """
        errors = []

        if not self._telegram_bot_token:
            errors.append("TELEGRAM_BOT_TOKEN is not set!")

        if not self._gemini_api_key:
            errors.append("GEMINI_API_KEY is not set!")

        if errors:
            print("ERROR: Missing required environment variables:")
            for error in errors:
                print(f"  - {error}")
            print("\nPlease create a .env file with the required variables:")
            print("TELEGRAM_BOT_TOKEN=your_telegram_token_here")
            print("GEMINI_API_KEY=your_gemini_api_key_here")
            sys.exit(1)

    @property
    def TELEGRAM_BOT_TOKEN(self) -> str:
        """
        Get the Telegram bot token.

        Returns:
            str: The bot token from environment variables.
        """
        return self._telegram_bot_token

    @property
    def GEMINI_API_KEY(self) -> str:
        """
        Get the Google Gemini API key.

        Returns:
            str: The Gemini API key from environment variables.
        """
        return self._gemini_api_key


# Create a global config instance
config = Config()
