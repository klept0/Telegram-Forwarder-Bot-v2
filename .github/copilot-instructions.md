# GitHub Copilot Instructions for Telegram Forwarder Bot v2

## Architecture Overview

This is a Python async Telegram message forwarding bot with a layered architecture:

- **Entry Point**: `main.py` → `source/core/Bot.py`
- **Account Management**: `source/menu/AccountSelector.py` handles multi-account Telegram credentials
- **Main Interface**: `source/menu/MainMenu.py` provides console-based menu system
- **Core Client**: `source/core/Telegram.py` wraps Telethon client with service layer
- **Services**: Message queuing, forwarding, chat management, and history tracking
- **Models**: Data persistence for credentials, chats, forward configs, and history
- **Dialogs**: Interactive user input flows for configuration and operations

## Modern Python Standards & Best Practices

### Python Version & Environment

- **Target Python**: 3.10+ (currently using 3.13.7)
- **Virtual Environment**: Always use `venv` or `conda` environments
- **Dependency Management**: Use `pyproject.toml` with modern tools like `uv` or `poetry`
- **Environment Variables**: Store sensitive data in `.env` files (never commit)

### Project Configuration

```toml
# pyproject.toml (recommended addition)
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "telegram-forwarder-bot-v2"
version = "2.0.0"
description = "Async Telegram message forwarding bot"
requires-python = ">=3.10"
dependencies = [
    "telethon>=1.39.0",
    "rich>=13.7.0",
    "inquirerpy>=0.3.4",
    "python-dotenv>=1.0.0",
    "pydantic>=2.0.0",
    "loguru>=0.7.0",
    "aiofiles>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.0.0",
    "black>=23.0.0",
    "isort>=5.12.0",
    "mypy>=1.0.0",
    "ruff>=0.1.0",
    "pre-commit>=3.0.0",
]
```

### Type Hints & Data Models

- **Use Pydantic**: Replace plain classes with Pydantic models for validation
- **Comprehensive Type Hints**: Add type hints to all functions and methods
- **Generic Types**: Use `typing.Generic` for reusable components

```python
# Modern model example with Pydantic
from pydantic import BaseModel, Field
from typing import Optional

class ForwardConfig(BaseModel):
    source_id: int = Field(..., description="Source chat ID")
    source_name: str = Field(..., description="Source chat name")
    destination_id: int = Field(..., description="Destination chat ID")
    destination_name: str = Field(..., description="Destination chat name")
    enabled: bool = Field(default=True, description="Whether forwarding is enabled")

    class Config:
        validate_assignment = True
```

### Async/Await Patterns

- **Modern Async**: Use `asyncio.TaskGroup` (Python 3.11+) for concurrent operations
- **Structured Concurrency**: Replace manual task management with modern patterns
- **Async Context Managers**: Use `async with` for resource management

```python
# Modern async pattern
async def process_messages(self) -> None:
    async with asyncio.TaskGroup() as tg:
        for message in messages:
            tg.create_task(self._process_single_message(message))
```

### Error Handling & Logging

- **Structured Logging**: Use `loguru` instead of print statements
- **Custom Exceptions**: Create specific exception types for different error scenarios
- **Context Managers**: Use context managers for resource cleanup

```python
# Modern logging setup
from loguru import logger

logger.add(
    "logs/bot_{time}.log",
    rotation="1 day",
    retention="7 days",
    level="INFO",
    format="{time} | {level} | {message}"
)

# Custom exceptions
class TelegramBotError(Exception):
    """Base exception for bot operations"""
    pass

class AuthenticationError(TelegramBotError):
    """Raised when authentication fails"""
    pass
```

### Security Best Practices

- **Environment Variables**: Store API keys and sensitive data securely
- **Input Validation**: Validate all user inputs and API responses
- **Rate Limiting**: Implement proper rate limiting for API calls
- **Session Security**: Secure session file handling

```python
# Environment variable usage
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", ""))
    TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")

    @classmethod
    def validate(cls) -> None:
        required = ["TELEGRAM_API_ID", "TELEGRAM_API_HASH"]
        missing = [key for key in required if not getattr(cls, key)]
        if missing:
            raise ValueError(f"Missing required environment variables: {missing}")
```

## Critical Patterns & Conventions

### Async/Await Pattern

- All main operations are async - use `await` for Telegram API calls, file I/O, and user input
- Event loop management in `main.py` with proper signal handling for graceful shutdown
- Background tasks for status updates and message queue processing
- **Modern**: Use `asyncio.TaskGroup` for structured concurrency (Python 3.11+)

### Console Output with Rich

- Import: `from source.utils.Console import Terminal` then use `Terminal.console`
- Formatting: `[bold red]Error:[/bold red]`, `[bold green]Status:[/]`, `[bold yellow]Warning:[/]`
- Always use `.clear()` before showing new dialogs/menus
- **Modern**: Consider migrating to `loguru` for structured logging

### Service Layer Organization

- Services in `source/service/` handle business logic (Forward, MessageQueue, ChatService, etc.)
- Models in `source/model/` handle data persistence with JSON files in `resources/` folder
- All services take console parameter for consistent output formatting
- **Modern**: Use dependency injection with protocols/interfaces

### Dialog System Pattern

- Base class: `source/dialog/BaseDialog.py` with `show_options()` and `clear()` methods
- Use `InquirerPy` for async user input: `await inquirer.select(message="...", choices=[]).execute_async()`
- Dialog choices have `{"name": "Display Text", "value": "return_value"}` format
- **Modern**: Consider using `questionary` or `prompt_toolkit` for richer interactions

### File Persistence Pattern

- All data stored as JSON in `resources/` folder (created on startup)
- Models have static `read()`, `write()`, and class methods for data operations
- Sessions stored in `sessions/` folder with `session_` prefix + phone number
- **Modern**: Consider SQLite with SQLAlchemy or async database solutions

### Rate Limiting & Queue Management

- `MessageQueue` class handles Telegram rate limits with configurable delay (default 1 second)
- Queue workers process forwarding tasks in background
- Always check queue status for UI updates
- **Modern**: Use `asyncio.Queue` with proper typing and error handling

## Development Workflow & Quality Assurance

### Code Quality Tools

```bash
# Install development dependencies
pip install -e ".[dev]"

# Code formatting
black source/
isort source/

# Linting
ruff check source/
mypy source/

# Testing
pytest tests/ -v --cov=source --cov-report=html
```

### Testing Strategy

- **Unit Tests**: Test individual functions and methods
- **Integration Tests**: Test service interactions
- **Async Tests**: Use `pytest-asyncio` for async test functions
- **Mocking**: Use `pytest-mock` for external dependencies

```python
# Example async test
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_message_forwarding():
    # Arrange
    mock_client = AsyncMock()
    service = MessageForwardService(mock_client)

    # Act
    result = await service.forward_message(chat_id=123, message="test")

    # Assert
    mock_client.send_message.assert_called_once()
    assert result is not None
```

### CI/CD Pipeline

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12", "3.13"]

    steps:
      - uses: actions/checkout@v4
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"
      - name: Run tests
        run: pytest tests/ --cov=source --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Key Development Workflows

### Running the Bot

```bash
# Modern development setup
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Set up environment variables
cp .env.example .env
# Edit .env with your credentials

# Run with hot reload (if using tools like `watch`)
python main.py

# Or run tests
pytest tests/ -v
```

### Folder Structure Created on Startup

- `resources/` - JSON config files (credentials, chats, forward config, history)
- `media/` - Downloaded media files
- `sessions/` - Telegram session files (format: `session_+1234567890`)
- `logs/` - Application logs (new recommendation)
- `.env` - Environment variables (add to .gitignore)

### Adding New Features

1. **Services**: Add to `source/service/` for business logic
2. **Models**: Add to `source/model/` for data persistence
3. **Dialogs**: Add to `source/dialog/` for user interaction flows
4. **Menu Options**: Update `source/menu/MainMenu.py` menu_options list
5. **Tests**: Add corresponding tests in `tests/` directory

### Debugging & Error Handling

- Use structured logging with `loguru` instead of print statements
- Implement proper exception handling with custom exception types
- Add comprehensive logging for debugging and monitoring
- Use `rich` for console output and `loguru` for file logging

## Integration Points

### Telethon Client Integration

- Wrapped in `source/core/Telegram.py` class with credential management
- Event handlers for live message forwarding (NewMessage, Album events)
- Session management with automatic reconnection
- **Modern**: Use latest Telethon features and proper async context management

### Multiple Account Support

- Credentials stored as JSON array in `resources/credentials.json`
- AccountSelector allows switching between configured accounts
- Each account has separate session file
- **Modern**: Consider using Pydantic settings for configuration management

### Message Forwarding Pipeline

1. **Live Mode**: Event handlers capture new messages → Queue → Rate-limited forwarding
2. **History Mode**: Bulk message retrieval → Process in batches → Forward with rate limits
3. **Configuration**: Source/destination chat mapping via ForwardConfig model
4. **Modern**: Add message deduplication, retry logic, and circuit breaker patterns

### File Organization Constants

- All paths defined in `source/utils/Constants.py`
- Use constants instead of hardcoded paths
- Ensure proper async file operations for JSON persistence
- **Modern**: Use `pathlib.Path` for path operations and `aiofiles` for async I/O

## Quick Reference

- **Add new menu option**: Update `MainMenu._init_menu_options()`
- **New user dialog**: Inherit from `BaseDialog`, use `show_options()` and `InquirerPy`
- **Service integration**: Inject console and queue dependencies
- **Model persistence**: Follow JSON read/write pattern in existing models
- **Error handling**: Use rich formatting with Terminal.console
- **Async operations**: Always await Telegram API calls and file operations
- **Modern logging**: Use `loguru` for structured logging
- **Type hints**: Add comprehensive type annotations
- **Testing**: Write async tests with `pytest-asyncio`
- **Security**: Store secrets in environment variables
- **Code quality**: Use `black`, `isort`, `ruff`, and `mypy`
