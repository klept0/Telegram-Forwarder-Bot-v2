# Telegram Forwarder Bot v2 - GitHub Wiki Content

This file contains the complete wiki content for the Telegram Forwarder Bot v2 GitHub repository. You can copy and paste these sections into your GitHub wiki pages.

---

## Home

# Welcome to Telegram Forwarder Bot v2

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An asynchronous Telegram message forwarding bot with a modern Python architecture, built with Telethon and Rich.

This project is based on the [original Telegram Forwarder Bot](https://github.com/MohammadShabib/Telegram-Forwarder-Bot) by Mohammad Shabib.

## 🚀 Key Features

- **Async/Await Architecture**: Fully asynchronous for high performance
- **Live Forwarding**: Real-time message forwarding with event handlers
- **History Forwarding**: Bulk message forwarding with date filtering
- **Progress Tracking**: Real-time progress indicators
- **Multi-Account Support**: Switch between multiple Telegram accounts
- **Rate Limiting**: Built-in rate limiting to respect API limits
- **Rich Console UI**: Beautiful terminal interface
- **Type-Safe**: Full type hints with mypy support

## 📖 Quick Links

- [Installation Guide](wiki/Installation)
- [Configuration](wiki/Configuration)
- [Usage Guide](wiki/Usage)
- [Troubleshooting](wiki/Troubleshooting)
- [API Reference](wiki/API-Reference)
- [FAQ](wiki/FAQ)
- [Development](wiki/Development)

## 🏁 Quick Start

```bash
# Clone and setup
git clone https://github.com/klept0/Telegram-Forwarder-Bot-v2.git
cd Telegram-Forwarder-Bot-v2

# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Run the bot
python main.py
```

---

## Installation

# Installation Guide

## Prerequisites

- Python 3.10 or higher
- A Telegram account with API credentials from [my.telegram.org](https://my.telegram.org)
- Docker & Docker Compose (optional, for containerized deployment)

## Installation Methods

### Option 1: Local Installation (Recommended for Development)

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

### Option 2: Docker Installation (Recommended for Production)

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
   docker-compose logs -f
   ```

## Getting Telegram API Credentials

1. Go to [my.telegram.org](https://my.telegram.org) and log in
2. Click on "API development tools"
3. Create a new application
4. Copy the `api_id` and `api_hash` values
5. Add them to your `.env` file

## Verification

After installation, you should see the main menu with options for account management and forwarding configuration.

---

## Configuration

# Configuration Guide

## Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# Telegram API Credentials
TELEGRAM_API_ID=your_api_id_here
TELEGRAM_API_HASH=your_api_hash_here

# Optional: Bot Token (for bot functionality)
BOT_TOKEN=your_bot_token_here

# Optional: Web Interface
WEB_HOST=0.0.0.0
WEB_PORT=8000
```

## Getting API Credentials

1. Visit [my.telegram.org](https://my.telegram.org)
2. Log in with your Telegram account
3. Navigate to "API development tools"
4. Create a new application
5. Copy the `api_id` and `api_hash`

## Account Management

The bot supports multiple Telegram accounts. Credentials are stored securely in `resources/credentials.json`.

### Adding Accounts

1. Run the bot: `python main.py`
2. Select "Manage Accounts" from the main menu
3. Choose "Add Account"
4. Enter your phone number and API credentials
5. Complete the Telegram authentication flow

### Switching Accounts

1. Select "Switch Account" from the main menu
2. Choose the account you want to use
3. The bot will reconnect with the selected account

## Forward Configuration

Forwarding rules are stored in `resources/forward_config.json`. Each rule maps a source chat to one or more destination chats.

### Creating Forward Rules

1. Select "Configure Forwarding" from the main menu
2. Choose "Add Forward Rule"
3. Select source chat
4. Select destination chat(s)
5. Configure filtering options (optional)

### Configuration File Structure

```json
[
  {
    "source_id": 123456789,
    "source_name": "Source Chat",
    "destination_id": 987654321,
    "destination_name": "Destination Chat",
    "enabled": true,
    "filters": {
      "date_from": "2024-01-01",
      "date_to": "2024-12-31",
      "keywords": ["important", "urgent"]
    }
  }
]
```

## Rate Limiting

The bot includes built-in rate limiting to respect Telegram's API limits:

- **Messages**: 30 messages per second
- **Media**: 10 media uploads per second
- **Other operations**: Appropriate limits per operation type

Rate limits are configurable in `source/utils/RateLimiter.py`.

---

## Usage

# Usage Guide

## Main Menu Options

After starting the bot, you'll see the main menu with the following options:

1. **Manage Accounts**: Add, remove, or switch between Telegram accounts
2. **Configure Forwarding**: Set up forwarding rules between chats
3. **Start Live Forwarding**: Begin real-time message forwarding
4. **Forward History**: Bulk forward messages from chat history
5. **View History**: Check forwarding history and statistics
6. **Settings**: Configure bot settings and preferences

## Live Forwarding

Live forwarding monitors chats in real-time and forwards new messages according to your rules.

### Starting Live Forwarding

1. Select "Start Live Forwarding" from the main menu
2. Choose which forwarding rules to activate
3. The bot will begin monitoring and forwarding messages
4. Progress indicators show forwarding status

### Stopping Live Forwarding

- Press `Ctrl+C` to stop gracefully
- The bot will save current state and statistics

## History Forwarding

Forward messages from chat history with date filtering and progress tracking.

### Forwarding History

1. Select "Forward History" from the main menu
2. Choose source chat
3. Select date range or specific months
4. Choose destination chat
5. Monitor progress as messages are forwarded

### Filtering Options

- **Date Range**: Specify start and end dates
- **Months**: Select specific months to forward
- **Keywords**: Filter messages containing specific words
- **Media Only**: Forward only messages with media attachments

## Chat Management

### Finding Chats

1. Select "Find Chats" from the main menu
2. Search by name or browse your chat list
3. View chat details and message counts

### Chat Statistics

The bot provides statistics for each chat:
- Total messages
- Media count
- Last activity
- Chat type (private, group, channel)

## Monitoring and Logs

### Viewing Logs

- Console output shows real-time progress
- Logs are saved to `logs/bot_YYYY-MM-DD.log`
- Use `rich` formatting for better readability

### Progress Indicators

During forwarding operations, you'll see:
```
Forwarding messages: 150/500 (30%)
Processing media: 45/100 (45%)
Rate limiting active: 2.1 seconds remaining
```

---

## Troubleshooting

# Troubleshooting Guide

## Common Issues

### Authentication Errors

**Problem**: "Invalid API credentials" or "Phone number not registered"

**Solutions**:
1. Verify your `api_id` and `api_hash` from [my.telegram.org](https://my.telegram.org)
2. Check that your phone number is correctly formatted (+country code)
3. Ensure your Telegram account is not banned or restricted

### Connection Issues

**Problem**: "Connection failed" or "Network timeout"

**Solutions**:
1. Check your internet connection
2. Try switching networks (mobile data vs WiFi)
3. Wait a few minutes and retry
4. Check if Telegram is blocked in your region

### Rate Limiting

**Problem**: "Too many requests" or slow forwarding

**Solutions**:
1. The bot has built-in rate limiting - wait for it to complete
2. Reduce the number of active forwarding rules
3. Increase delays between operations in settings

### Permission Errors

**Problem**: "Access denied" or "Not authorized"

**Solutions**:
1. Ensure you have access to the source chat
2. Check that you can send messages to destination chats
3. For channels, ensure you have admin/editor permissions

## Docker Issues

### Container Won't Start

**Problem**: Docker container fails to start

**Solutions**:
1. Check Docker and Docker Compose installation
2. Verify `.env` file exists and has correct credentials
3. Check container logs: `docker-compose logs`
4. Ensure ports 8000 (web) are not in use

### Permission Issues in Docker

**Problem**: File permission errors in container

**Solutions**:
1. Check host file permissions
2. Ensure Docker has access to project directory
3. Try running with `--user $(id -u):$(id -g)`

## Performance Issues

### Slow Forwarding

**Causes**:
- Large message volumes
- Media-heavy chats
- Network latency
- Rate limiting

**Solutions**:
1. Reduce batch sizes
2. Filter messages to reduce volume
3. Use faster network connection
4. Run during off-peak hours

### High Memory Usage

**Causes**:
- Large chat histories
- Media downloads
- Multiple concurrent operations

**Solutions**:
1. Process chats in smaller batches
2. Disable media forwarding temporarily
3. Restart the bot periodically
4. Monitor with `docker stats`

## Logs and Debugging

### Enabling Debug Mode

Set environment variable: `LOG_LEVEL=DEBUG`

### Log Locations

- Console output: Real-time logs
- File logs: `logs/bot_YYYY-MM-DD.log`
- Docker logs: `docker-compose logs -f`

### Getting Help

If you can't resolve an issue:

1. Check the [FAQ](wiki/FAQ) page
2. Review [GitHub Issues](https://github.com/klept0/Telegram-Forwarder-Bot-v2/issues)
3. Create a new issue with:
   - Error messages
   - Log excerpts
   - Steps to reproduce
   - Your environment details

---

## API Reference

# API Reference

## Core Classes

### TelegramClient

Main Telegram client wrapper.

```python
from source.core.Telegram import TelegramClient

client = TelegramClient(api_id, api_hash, phone)
await client.connect()
```

**Methods**:
- `connect()`: Establish connection
- `disconnect()`: Close connection
- `get_chats()`: Retrieve user's chats
- `send_message(chat_id, text)`: Send text message

### ForwardService

Handles message forwarding operations.

```python
from source.service.Forward import ForwardService

service = ForwardService(client, console)
await service.forward_history(source_id, dest_id, date_from, date_to)
```

**Methods**:
- `forward_history()`: Bulk forward from history
- `start_live_forwarding()`: Begin real-time forwarding
- `stop_live_forwarding()`: Stop real-time forwarding

### MessageQueue

Manages message queuing and rate limiting.

```python
from source.service.MessageQueue import MessageQueue

queue = MessageQueue(rate_limiter)
await queue.add_message(message)
await queue.process_queue()
```

## Data Models

### ForwardConfig

```python
from source.model.ForwardConfig import ForwardConfig

config = ForwardConfig(
    source_id=123,
    source_name="Source",
    destination_id=456,
    destination_name="Destination",
    enabled=True
)
```

### Credentials

```python
from source.model.Credentials import Credentials

creds = Credentials(
    phone="+1234567890",
    api_id=12345,
    api_hash="abcdef123456"
)
```

## Utility Classes

### RateLimiter

Handles API rate limiting.

```python
from source.utils.RateLimiter import RateLimiter

limiter = RateLimiter()
await limiter.wait_if_needed()  # Respects rate limits
```

### Console

Rich console output wrapper.

```python
from source.utils.Console import Terminal

Terminal.console.print("[green]Success![/]")
Terminal.console.print("[red]Error![/]")
```

## Configuration Constants

Located in `source/utils/Constants.py`:

```python
RESOURCES_DIR = "resources"
SESSIONS_DIR = "sessions"
MEDIA_DIR = "media"
LOGS_DIR = "logs"
```

## Error Handling

Custom exceptions:

```python
from source.core.Telegram import TelegramError
from source.service.Forward import ForwardError

try:
    await client.connect()
except TelegramError as e:
    console.print(f"[red]Connection failed: {e}[/]")
```

---

## FAQ

# Frequently Asked Questions

## General Questions

**Q: What is Telegram Forwarder Bot v2?**

A: It's an asynchronous Python application that forwards messages between Telegram chats automatically, with support for live forwarding, history forwarding, and multi-account management.

**Q: How is this different from the original version?**

A: This version features modern Python async architecture, better error handling, progress indicators, Docker support, and improved user interface.

**Q: Is it safe to use?**

A: Yes, it only requires standard Telegram API access and doesn't store your messages. All credentials are stored locally and encrypted.

## Installation & Setup

**Q: Do I need programming knowledge to use this?**

A: Basic command-line knowledge is helpful, but the installation guides are step-by-step. Docker installation requires even less technical knowledge.

**Q: Can I run multiple instances?**

A: Yes, each instance can run with different accounts or configurations. Use separate directories or Docker containers.

**Q: What are the system requirements?**

A: Python 3.10+ for local installation, or Docker for containerized deployment. Minimal RAM (512MB) and storage requirements.

## Usage Questions

**Q: Can I forward from channels I'm not admin of?**

A: No, you need to be a member of the source chat and have permission to read messages.

**Q: How fast does forwarding work?**

A: Speed depends on message volume and media content. Typically 30-50 messages per minute with rate limiting.

**Q: Can I filter messages during forwarding?**

A: Yes, you can filter by date range, keywords, and media type.

**Q: What happens if the bot loses connection?**

A: It will automatically attempt to reconnect. Live forwarding will resume when connection is restored.

## Technical Questions

**Q: How does rate limiting work?**

A: The bot respects Telegram's API limits (30 messages/second, 10 media uploads/second) and includes additional safety buffers.

**Q: Where are my credentials stored?**

A: Credentials are stored encrypted in `resources/credentials.json`. Never commit this file to version control.

**Q: Can I use this with a bot token instead of user account?**

A: Yes, set the `BOT_TOKEN` environment variable. Note that bots have different API limitations.

**Q: How do I backup my configuration?**

A: Backup the `resources/` directory. It contains all your settings, credentials, and forwarding rules.

## Troubleshooting

**Q: The bot says "phone not registered"?**

A: Ensure your phone number includes the country code (+1 for US, +44 for UK, etc.) and that you've completed Telegram verification.

**Q: Forwarding is very slow?**

A: This is normal due to rate limiting. The bot prioritizes reliability over speed to avoid being blocked.

**Q: Can I run this on a server?**

A: Yes, use Docker deployment for server environments. Ensure proper firewall and security configurations.

**Q: How do I update the bot?**

A: Pull the latest changes from Git (`git pull`) and reinstall dependencies (`pip install -e ".[dev]"`).

---

## Development

# Development Guide

## Project Structure

```
Telegram-Forwarder-Bot-v2/
├── main.py                 # Entry point
├── source/
│   ├── core/              # Core functionality
│   │   ├── Bot.py         # Main bot class
│   │   └── Telegram.py    # Telegram client wrapper
│   ├── service/           # Business logic services
│   │   ├── Forward.py     # Forwarding logic
│   │   ├── MessageQueue.py # Queue management
│   │   └── ...
│   ├── model/             # Data models
│   │   ├── ForwardConfig.py
│   │   ├── Credentials.py
│   │   └── ...
│   ├── dialog/            # User interaction dialogs
│   ├── menu/              # Menu systems
│   └── utils/             # Utilities
├── resources/             # Runtime data
├── sessions/              # Telegram sessions
├── media/                 # Downloaded media
├── logs/                  # Application logs
└── requirements.txt       # Dependencies
```

## Development Setup

1. **Clone and setup:**
   ```bash
   git clone https://github.com/klept0/Telegram-Forwarder-Bot-v2.git
   cd Telegram-Forwarder-Bot-v2
   python -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```

2. **Install development tools:**
   ```bash
   pip install -e ".[dev]"  # Includes pytest, black, ruff, mypy
   ```

3. **Set up pre-commit hooks:**
   ```bash
   pre-commit install
   ```

## Code Quality

### Linting and Formatting

```bash
# Format code
black source/
isort source/

# Lint code
ruff check source/
mypy source/

# Fix auto-fixable issues
ruff check --fix source/
```

### Testing

```bash
# Run all tests
pytest tests/ -v --cov=source --cov-report=html

# Run specific test
pytest tests/test_forward.py -v

# Run with coverage
pytest tests/ --cov=source --cov-report=term-missing
```

### Type Checking

```bash
# Run mypy
mypy source/

# Strict mode
mypy source/ --strict
```

## Contributing

### Development Workflow

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes and run tests:**
   ```bash
   # Make your changes
   pytest tests/  # Ensure tests pass
   black source/ && isort source/  # Format code
   ruff check source/  # Lint code
   ```

3. **Commit changes:**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

4. **Create pull request**

### Commit Message Format

Use conventional commits:

```
feat: add new forwarding filter options
fix: resolve rate limiting issue
docs: update installation guide
refactor: simplify message queue logic
test: add unit tests for forward service
```

### Code Style Guidelines

- **Type Hints**: Use comprehensive type hints for all functions
- **Docstrings**: Add docstrings to classes and public methods
- **Async/Await**: Use async patterns consistently
- **Error Handling**: Use custom exceptions and proper error propagation
- **Logging**: Use structured logging with `loguru`

### Testing Guidelines

- **Unit Tests**: Test individual functions and methods
- **Integration Tests**: Test service interactions
- **Async Tests**: Use `pytest-asyncio` for async functions
- **Mocking**: Use `pytest-mock` for external dependencies
- **Coverage**: Aim for >80% code coverage

## Architecture Principles

### Async/Await Pattern

All I/O operations use async/await:

```python
async def forward_message(self, message: Message) -> None:
    await self.rate_limiter.wait_if_needed()
    await self.client.send_message(self.dest_id, message)
```

### Service Layer Pattern

Business logic separated into services:

```python
class ForwardService:
    def __init__(self, client: TelegramClient, console: Console):
        self.client = client
        self.console = console

    async def forward_history(self, config: ForwardConfig) -> None:
        # Implementation
```

### Dependency Injection

Services receive dependencies through constructor:

```python
# Good
service = ForwardService(client, console, queue)

# Avoid
service = ForwardService()
service.client = client  # Tight coupling
```

## API Design

### RESTful Endpoints (Future)

```
GET  /api/chats           # List chats
POST /api/forward         # Start forwarding
GET  /api/status          # Get bot status
POST /api/accounts        # Add account
```

### WebSocket Events (Future)

```javascript
// Real-time progress updates
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'progress') {
    updateProgress(data.current, data.total);
  }
};
```

## Deployment

### Docker Development

```bash
# Build and run
docker-compose up --build

# Run tests in container
docker-compose exec app pytest tests/
```

### Production Deployment

```bash
# Use production compose file
docker-compose -f docker-compose.prod.yml up -d

# Monitor logs
docker-compose logs -f app
```

## Performance Optimization

### Profiling

```python
import cProfile
cProfile.run('main()', 'profile.prof')
```

### Memory Monitoring

```python
import tracemalloc
tracemalloc.start()
# ... code ...
current, peak = tracemalloc.get_traced_memory()
print(f"Current memory usage: {current / 1024 / 1024:.1f} MB")
```

### Async Optimization

- Use `asyncio.gather()` for concurrent operations
- Implement connection pooling for database operations
- Use streaming for large file transfers

## Security Considerations

### Credential Management

- Never commit `.env` files
- Use environment variables for sensitive data
- Encrypt stored credentials

### API Security

- Implement proper rate limiting
- Validate all user inputs
- Use HTTPS for web interface

### Docker Security

- Run as non-root user
- Use minimal base images
- Regularly update dependencies

## Future Enhancements

### Planned Features

- Web-based management interface
- Message filtering and transformation
- Scheduled forwarding
- Multi-language support
- Plugin system for custom functionality

### Architecture Improvements

- GraphQL API
- Message queuing with Redis
- Distributed deployment support
- Real-time notifications
- Advanced analytics dashboard

---

*End of Wiki Content*