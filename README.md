# Telegram Forwarder Bot v2

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![Linting: Ruff](https://img.shields.io/badge/linting-ruff-4b8bbe.svg)](https://github.com/charliermarsh/ruff)

An asynchronous Telegram message forwarding bot with a modern Python architecture, built with Telethon and Rich.

This project is based on the [original Telegram Forwarder Bot](https://github.com/MohammadShabib/Telegram-Forwarder-Bot) by Mohammad Shabib.

## Features

- 🚀 **Async/Await**: Fully asynchronous architecture for high performance
- 🔄 **Live Forwarding**: Real-time message forwarding with event handlers
- 📚 **History Forwarding**: Bulk message forwarding from chat history with date filtering
- 📅 **Month Filtering**: Forward messages from specific months or date ranges
- 📊 **Progress Tracking**: Real-time progress indicators showing completion percentage
- 👥 **Multi-Account Support**: Switch between multiple Telegram accounts
- 🎯 **Rate Limiting**: Built-in rate limiting to respect Telegram's API limits
- 🎨 **Rich Console UI**: Beautiful terminal interface with Rich
- 🔒 **Secure**: Environment variable management for sensitive data
- 📝 **Type-Safe**: Full type hints with mypy support
- 🐳 **Docker Support**: Containerized deployment with Docker Compose
- 🔧 **Modern Tooling**: Black, isort, ruff, mypy, and pre-commit hooks

## Quick Start

### Prerequisites

- Python 3.10 or higher (for local installation)
- A Telegram account with API credentials
- Docker & Docker Compose (for containerized deployment)

### Installation Methods

Choose one of the following installation methods:

#### Option 1: Local Installation (Recommended for Development)

1. **Clone the repository:**

   ```bash
   git clone https://github.com/klept0/Telegram-Forwarder-Bot-v2.git
   cd Telegram-Forwarder-Bot-v2
   ```

2. **Create virtual environment:**

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -e ".[dev]"
   ```

4. **Set up environment variables:**

   ```bash
   cp .env.example .env
   # Edit .env with your Telegram API credentials
   ```

5. **Run the bot:**

   ```bash
   python main.py
   ```

#### Option 2: Docker Installation (Recommended for Production)

1. **Clone the repository:**

   ```bash
   git clone https://github.com/klept0/Telegram-Forwarder-Bot-v2.git
   cd Telegram-Forwarder-Bot-v2
   ```

2. **Set up environment variables:**

   ```bash
   cp .env.example .env
   # Edit .env with your Telegram API credentials
   ```

3. **Run with Docker Compose:**

   ```bash
   docker-compose up --build
   ```

   Or run in background:

   ```bash
   docker-compose up -d --build
   ```

4. **View logs:**

   ```bash
   docker-compose logs -f telegram-forwarder
   ```

5. **Stop the bot:**

   ```bash
   docker-compose down
   ```

**Docker Notes:**

- Configuration files are stored in Docker volumes for persistence
- Environment variables are loaded from the `.env` file
- The bot runs as a non-root user for security

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Telegram API Credentials
TELEGRAM_API_ID=your_api_id_here
TELEGRAM_API_HASH=your_api_hash_here

# Optional: Bot Token (if using bot account)
BOT_TOKEN=your_bot_token_here

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=logs/bot.log

# Application Settings
MAX_CONCURRENT_TASKS=3
MESSAGE_QUEUE_DELAY=1.0
```

### Getting Telegram API Credentials

1. Go to [my.telegram.org](https://my.telegram.org)
2. Log in with your phone number
3. Go to "API development tools"
4. Create a new application
5. Copy the `api_id` and `api_hash`

## Usage

### Main Menu Options

1. **Add/Update Credentials** - Configure Telegram API credentials
2. **List Chats** - Display all available chats
3. **Delete My Messages** - Remove your messages from chats
4. **Find User Messages** - Search for messages from specific users
5. **Live Forward Messages** - Start real-time message forwarding
6. **Past Forward Messages** - Forward historical messages
7. **Switch Account** - Change between configured accounts
8. **Exit** - Close the application

### Forward Configuration

Configure message forwarding by specifying:

- **Source Chat**: The chat to forward messages from
- **Destination Chat**: The chat to forward messages to
- **Date Filtering**: Choose from:
  - No date filter (forward all messages)
  - Filter by specific month
  - Filter by custom date range
- **Enabled**: Whether forwarding is active

When forwarding historical messages, the bot displays real-time progress indicators showing:

- Number of messages found
- Current progress (X/Y messages)
- Percentage completion

## Development

### Code Quality

This project uses modern Python tooling for code quality:

```bash
# Format code
black source/
isort source/

# Lint code
ruff check source/

# Type check
mypy source/
```

### Pre-commit Hooks

Install pre-commit hooks for automatic code quality checks:

```bash
pre-commit install
pre-commit run --all-files
```

### Project Structure

```text
telegram-forwarder-bot-v2/
├── source/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── Bot.py
│   │   └── Telegram.py
│   ├── dialog/
│   │   ├── __init__.py
│   │   ├── BaseDialog.py
│   │   ├── ForwardDialog.py
│   │   └── ...
│   ├── menu/
│   │   ├── __init__.py
│   │   ├── AccountSelector.py
│   │   └── MainMenu.py
│   ├── model/
│   │   ├── __init__.py
│   │   ├── Chat.py
│   │   ├── Credentials.py
│   │   └── ...
│   ├── service/
│   │   ├── __init__.py
│   │   ├── MessageQueue.py
│   │   ├── MessageForwardService.py
│   │   └── ...
│   └── utils/
│       ├── __init__.py
│       ├── Console.py
│       ├── Constants.py
│       └── RateLimiter.py
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── Dockerfile
├── docker-compose.yml
├── main.py
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Architecture

### Core Components

- **Bot**: Main application orchestrator
- **Telegram**: Telethon client wrapper with service integration
- **Services**: Business logic layer (Forwarding, Queue, Chat management)
- **Models**: Data persistence and validation
- **Dialogs**: User interaction flows
- **Utils**: Shared utilities and constants

### Data Flow

1. **Live Mode**: Event handlers capture new messages → Queue → Rate-limited forwarding
2. **History Mode**: Bulk message retrieval → Process in batches → Forward with rate limits
3. **Configuration**: Source/destination chat mapping via ForwardConfig model

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Add type hints to all functions and methods
- Update documentation for API changes
- Use conventional commit messages

## Security

- Never commit API credentials or sensitive data
- Use environment variables for configuration
- Regularly update dependencies for security patches
- Follow principle of least privilege

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Telethon](https://github.com/LonamiWebs/Telethon) - Telegram client library
- [Rich](https://github.com/Textualize/rich) - Beautiful terminal output
- [Pydantic](https://github.com/pydantic/pydantic) - Data validation
- [Loguru](https://github.com/Delgan/loguru) - Structured logging

## Support

If you find this project helpful, please give it a ⭐️!

For questions or issues:

- Open an [issue](https://github.com/klept0/Telegram-Forwarder-Bot-v2/issues)
- Check the [documentation](https://github.com/klept0/Telegram-Forwarder-Bot-v2/wiki)

