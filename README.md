# Telegram Forwarder Bot v2

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-2.3.0-0A66C2.svg)](CHANGELOG.md)
[![Docker](https://img.shields.io/badge/docker-supported-2496ED.svg?logo=docker&logoColor=white)](docker-compose.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688.svg?logo=fastapi&logoColor=white)](web/app.py)
[![Telethon](https://img.shields.io/badge/Telethon-1.39+-2CA5E0.svg)](https://github.com/LonamiWebs/Telethon)

An asynchronous Telegram message forwarding bot with a modern Python architecture, built with Telethon and Rich.

This project is based on the [original Telegram Forwarder Bot](https://github.com/MohammadShabib/Telegram-Forwarder-Bot) by Mohammad Shabib.

## Features

- 🚀 **Async/Await**: Fully asynchronous architecture for high performance
- 🔄 **Live Forwarding**: Real-time message forwarding with event handlers
- 📚 **History Forwarding**: Bulk message forwarding from chat history with date filtering
- 📅 **Month Filtering**: Forward messages from specific months or date ranges
- 🌍 **Timezone-Aware Date Filters**: Apply date windows in UTC, local, or custom IANA timezone
- 🔎 **Dry-Run Preview**: Count matching historical messages before forwarding
- 📊 **Progress Tracking**: Real-time progress indicators showing completion percentage
- 🔍 **Keyword Search Forwarding**: Search source chat history by keyword and forward only matching messages
- 👥 **Multi-Account Support**: Switch between multiple Telegram accounts
- 🎯 **Rate Limiting**: Built-in rate limiting to respect Telegram's API limits
- 🎨 **Rich Console UI**: Beautiful terminal interface with Rich
- 🌐 **Web Dashboard**: FastAPI-based web interface for remote management
- 🔒 **Secure**: Environment variable management for sensitive data
- 📝 **Type-Safe**: Full type hints throughout the codebase
- 🐳 **Docker Support**: Containerized deployment with Docker Compose

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

#### Option 3: Web Interface (FastAPI Dashboard)

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

3. **Install dependencies with web extras:**

   ```bash
   pip install -e ".[web]"
   ```

4. **Set up environment variables:**

   ```bash
   cp .env.example .env
   # Edit .env with your Telegram API credentials
   ```

5. **Run the web dashboard:**

   ```bash
   python web/app.py
   ```

   Or run from the project root:

   ```bash
   python -m web.app
   ```

6. **Open your browser:**

   Navigate to `http://localhost:8000` to access the web interface.

**Web Interface Features:**

- Real-time bot status monitoring
- Forward configuration management
- Chat browser and selection
- REST API for programmatic access
- Remote control of forwarding operations

## Configuration

### Environment Variables

Telegram account credentials are entered interactively on first run
(`python main.py`) and stored in `resources/credentials.json` — they are
not read from environment variables.

The web dashboard (`web/app.py`) does use environment variables. Create a
`.env` file in the project root (see `.env.example`):

```env
# Required: shared secret clients must send as the X-API-Key header on
# every /api/* request. The dashboard refuses to serve requests without it.
API_KEY=change_me_to_a_long_random_value

# Optional: bind address/port for the web dashboard (defaults shown below)
WEB_HOST=127.0.0.1
WEB_PORT=8000
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
7. **Keyword Search + Forward** - Search by keyword and forward matching messages
8. **Switch Account** - Change between configured accounts
9. **Clear Forward Progress Cache** - Reset saved resume state for historical forwarding
10. **Exit** - Close the application

### Forward Configuration

Configure message forwarding by specifying:

- **Source Chat**: The chat to forward messages from
- **Destination Chat**: The chat to forward messages to
- **Date Filtering**: Choose from:
  - No date filter (forward all messages)
  - Filter by specific month
  - Filter by multiple months
  - Filter by custom date range
- **Timezone**: Choose UTC, local system timezone, or custom IANA timezone
- **Dry-Run Preview**: Optional count-only run without sending messages
- **Enabled**: Whether forwarding is active

When forwarding historical messages, the bot displays real-time progress indicators showing:

- Number of messages found
- Current progress (X/Y messages)
- Percentage completion

### Keyword Search + Forward

Use the `Keyword Search + Forward` menu option to:

- Select source and destination chats
- Enter a keyword to search in source chat history
- Optionally set date range + timezone filtering
- Run dry-run preview (count matches only) or forward matches

Matching messages are forwarded in chronological order.

## Changelog Policy

`CHANGELOG.md` is maintained as a running log for every update. Each release entry should include:

- `Added`/`Changed`/`Fixed` details
- Explicit behavior delta when relevant (before vs after)
- Release date and semantic version

### Web API

The web interface provides a REST API for programmatic access:

#### Status & Monitoring

- `GET /api/status` - Get real-time bot status

#### Chat Management

- `GET /api/chats` - List available Telegram chats

#### Forwarding Configuration

- `GET /api/forwards` - List all forwarding configurations
- `POST /api/forwards` - Create new forwarding configuration
- `DELETE /api/forwards/{source_id}` - Delete forwarding configuration
- `POST /api/forwards/{source_id}/toggle` - Enable/disable forwarding

#### Control Operations

- `POST /api/start-forwarding` - Start live message forwarding
- `POST /api/stop-forwarding` - Stop live message forwarding

#### Keyword Forwarding

- `POST /api/keyword-forward` - Search source chat by keyword and forward matches (supports dry-run)

## Development

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
│       └── Constants.py
├── web/
│   ├── __init__.py
│   ├── app.py
│   ├── static/
│   ├── templates/
│   └── README.md
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
- [FastAPI](https://github.com/tiangolo/fastapi) - Modern web framework
- [Pydantic](https://github.com/pydantic/pydantic) - Data validation
- [Loguru](https://github.com/Delgan/loguru) - Structured logging
- [Uvicorn](https://github.com/encode/uvicorn) - ASGI server

## Support

If you find this project helpful, please give it a ⭐️!

For questions or issues:

- Open an [issue](https://github.com/klept0/Telegram-Forwarder-Bot-v2/issues)
- Check the [documentation](https://github.com/klept0/Telegram-Forwarder-Bot-v2/wiki)
