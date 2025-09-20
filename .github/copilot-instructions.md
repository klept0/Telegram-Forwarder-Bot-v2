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

## Critical Patterns & Conventions

### Async/Await Pattern

- All main operations are async - use `await` for Telegram API calls, file I/O, and user input
- Event loop management in `main.py` with proper signal handling for graceful shutdown
- Background tasks for status updates and message queue processing

### Console Output with Rich

- Import: `from source.utils.Console import Terminal` then use `Terminal.console`
- Formatting: `[bold red]Error:[/bold red]`, `[bold green]Status:[/]`, `[bold yellow]Warning:[/]`
- Always use `.clear()` before showing new dialogs/menus

### Service Layer Organization

- Services in `source/service/` handle business logic (Forward, MessageQueue, ChatService, etc.)
- Models in `source/model/` handle data persistence with JSON files in `resources/` folder
- All services take console parameter for consistent output formatting

### Dialog System Pattern

- Base class: `source/dialog/BaseDialog.py` with `show_options()` and `clear()` methods
- Use `InquirerPy` for async user input: `await inquirer.select(message="...", choices=[]).execute_async()`
- Dialog choices have `{"name": "Display Text", "value": "return_value"}` format

### File Persistence Pattern

- All data stored as JSON in `resources/` folder (created on startup)
- Models have static `read()`, `write()`, and class methods for data operations
- Sessions stored in `sessions/` folder with `session_` prefix + phone number

### Rate Limiting & Queue Management

- `MessageQueue` class handles Telegram rate limits with configurable delay (default 1 second)
- Queue workers process forwarding tasks in background
- Always check queue status for UI updates

## Key Development Workflows

### Running the Bot

```bash
# Install dependencies
pip install -r requirements.txt

# Run the bot
python main.py
```

### Folder Structure Created on Startup

- `resources/` - JSON config files (credentials, chats, forward config, history)
- `media/` - Downloaded media files
- `sessions/` - Telegram session files (format: `session_+1234567890`)

### Adding New Features

1. **Services**: Add to `source/service/` for business logic
2. **Models**: Add to `source/model/` for data persistence
3. **Dialogs**: Add to `source/dialog/` for user interaction flows
4. **Menu Options**: Update `source/menu/MainMenu.py` menu_options list

### Debugging & Error Handling

- Use `Terminal.console.print()` for consistent error formatting
- Wrap async operations in try/catch with graceful error messages
- Check queue status via `telegram.queue.qsize()` and `telegram.queue.current_task`

## Integration Points

### Telethon Client Integration

- Wrapped in `source/core/Telegram.py` class with credential management
- Event handlers for live message forwarding (NewMessage, Album events)
- Session management with automatic reconnection

### Multiple Account Support

- Credentials stored as JSON array in `resources/credentials.json`
- AccountSelector allows switching between configured accounts
- Each account has separate session file

### Message Forwarding Pipeline

1. **Live Mode**: Event handlers capture new messages → Queue → Rate-limited forwarding
2. **History Mode**: Bulk message retrieval → Process in batches → Forward with rate limits
3. **Configuration**: Source/destination chat mapping via ForwardConfig model

### File Organization Constants

- All paths defined in `source/utils/Constants.py`
- Use constants instead of hardcoded paths
- Ensure proper async file operations for JSON persistence

## Quick Reference

- **Add new menu option**: Update `MainMenu._init_menu_options()`
- **New user dialog**: Inherit from `BaseDialog`, use `show_options()` and `InquirerPy`
- **Service integration**: Inject console and queue dependencies
- **Model persistence**: Follow JSON read/write pattern in existing models
- **Error handling**: Use rich formatting with Terminal.console
- **Async operations**: Always await Telegram API calls and file operations
