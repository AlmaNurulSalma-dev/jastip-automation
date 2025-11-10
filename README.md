# Jastip Automation Bot

A production-ready Telegram bot built with Python that demonstrates modern async/await patterns, robust error handling, and proper logging practices.

## Features

- Asynchronous bot implementation using `python-telegram-bot` v20+
- Command handlers (`/start`, `/help`)
- Echo functionality for text messages
- Comprehensive error handling and logging
- Environment-based configuration
- Production-ready code structure

## Project Structure

```
jastip-automation/
├── main.py              # Main bot application with handlers
├── config.py            # Configuration management
├── requirements.txt     # Python dependencies
├── .gitignore          # Git ignore rules
├── .env                # Environment variables (create this)
└── README.md           # This file
```

## Prerequisites

- Python 3.8 or higher
- A Telegram account
- Basic knowledge of Python and command line

## Getting a Telegram Bot Token

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Start a chat and send `/newbot`
3. Follow the prompts to:
   - Choose a name for your bot (e.g., "Jastip Automation Bot")
   - Choose a username for your bot (must end in 'bot', e.g., "jastip_automation_bot")
4. BotFather will provide you with a token that looks like:
   ```
   123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   ```
5. Save this token - you'll need it for setup

## Installation

1. **Clone or download this project:**
   ```bash
   cd jastip-automation
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   # On Windows
   python -m venv venv
   venv\Scripts\activate

   # On macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create a `.env` file in the project root:**
   ```bash
   # On Windows
   type nul > .env

   # On macOS/Linux
   touch .env
   ```

5. **Add your bot token to `.env`:**
   ```env
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   ```

   Replace `your_bot_token_here` with the token from BotFather.

## Running the Bot

1. **Make sure your virtual environment is activated**

2. **Run the bot:**
   ```bash
   python main.py
   ```

3. **You should see:**
   ```
   Starting Jastip Automation Bot...
   Bot is now running. Press Ctrl+C to stop.
   ```

4. **Test your bot:**
   - Open Telegram
   - Search for your bot by username
   - Send `/start` to begin
   - Send any message and the bot will echo it back

## Available Commands

- `/start` - Display welcome message and bot information
- `/help` - Show help information

## Configuration

All configuration is managed through environment variables in the `.env` file:

- `TELEGRAM_BOT_TOKEN` - Your Telegram bot token (required)
- `GEMINI_API_KEY` - Your Google Gemini API key (required for AI parsing)

## Logging

The bot logs to both:
- **Console**: Real-time logs visible in terminal
- **File**: `bot.log` file for persistent logs

Log levels:
- INFO: General information about bot operations
- WARNING: Warning messages
- ERROR: Error messages
- CRITICAL: Critical errors

## Error Handling

The bot includes comprehensive error handling:
- All handlers wrapped in try-except blocks
- Global error handler for uncaught exceptions
- User-friendly error messages
- Detailed error logging for debugging

## Development

### Adding New Commands

1. Create an async handler function in `main.py`:
   ```python
   async def my_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
       await update.message.reply_text("Response")
   ```

2. Register the handler in `main()`:
   ```python
   application.add_handler(CommandHandler("mycommand", my_command))
   ```

### Adding New Message Handlers

```python
# Example: Handler for photos
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Nice photo!")

application.add_handler(MessageHandler(filters.PHOTO, photo_handler))
```

## Security Best Practices

- Never commit `.env` file to version control
- Keep your bot token secret
- Regularly update dependencies
- Review and audit bot permissions

## Troubleshooting

### Bot doesn't respond
- Check if the bot is running (`python main.py`)
- Verify the token in `.env` is correct
- Check `bot.log` for errors

### Import errors
- Ensure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`

### Token validation error
- Verify your `.env` file exists and contains the token
- Check for extra spaces or quotes in the token

### Gemini API 404 Errors

If you see "404 models/gemini-xxx is not found" errors:

1. **Test your API key:**
   ```bash
   python test_api_key.py
   ```
   This will verify your API key and list available models.

2. **Auto-fix configuration:**
   ```bash
   python fix_api_config.py
   ```
   This automatically detects the working model and updates configuration files.

3. **If still failing:**
   - Generate a new API key at: https://aistudio.google.com/app/apikey
   - Update `.env` file with the new key:
     ```
     GEMINI_API_KEY=your_new_key_here
     ```
   - Run `python fix_api_config.py` again

### Common Gemini API Issues

- **API key invalid (400)**: Generate a new API key at the link above
- **Access denied (403)**: Enable Generative Language API in Google Cloud Console
- **All models return 404**: Your API key might be for a different region/project
  - Try creating a new API key
  - Ensure you're using Google AI Studio (not Vertex AI)
- **Request timeout**: Check your internet connection

### Running Full Diagnostic

To run all tests and diagnostics:
```bash
python test_all.py
```

This will:
- Upgrade the google-generativeai library
- Check available models
- Test both SDK and REST API parsers
- Show a summary of what works

## Dependencies

- `python-telegram-bot>=20.0` - Telegram Bot API wrapper with async support
- `python-dotenv>=1.0.0` - Environment variable management
- `google-generativeai>=0.3.0` - Google Gemini AI for query parsing
- `requests>=2.31.0` - HTTP requests for REST API fallback

## License

This project is open source and available for educational purposes.

## Contributing

Feel free to fork this project and submit pull requests for improvements.

## Support

For issues related to:
- This bot: Check the logs in `bot.log`
- Telegram Bot API: Visit [python-telegram-bot documentation](https://docs.python-telegram-bot.org/)
- Telegram bots in general: Contact [@BotSupport](https://t.me/botsupport) on Telegram

## Roadmap

Potential future enhancements:
- Database integration
- User state management
- Inline keyboard buttons
- Webhook deployment option
- Admin panel
- Multi-language support

---

**Note**: This bot is designed as a template for building more complex Telegram bots. Customize it according to your needs!
