# Telegram Forwarder Bot - Web Interface

This directory contains the FastAPI web interface for the Telegram Forwarder Bot.

## Features

- **Dashboard**: Real-time bot status monitoring
- **Forward Management**: Create, enable/disable, and delete forwarding configurations
- **Chat Browser**: View and select available Telegram chats
- **Control Panel**: Start/stop forwarding operations
- **REST API**: Full REST API for programmatic access

## Quick Start

1. Install dependencies:

   ```bash
   pip install -e ".[web]"
   ```

2. Run the web interface:

   ```bash
   python web/app.py
   ```

3. Open your browser to `http://localhost:8000`

## API Endpoints

### Status

- `GET /api/status` - Get bot status information

### Chats

- `GET /api/chats` - List available chats

### Forwarding

- `GET /api/forwards` - List all forwarding configurations
- `POST /api/forwards` - Create new forwarding configuration
- `DELETE /api/forwards/{source_id}` - Delete forwarding configuration
- `POST /api/forwards/{source_id}/toggle` - Enable/disable forwarding

### Control

- `POST /api/start-forwarding` - Start live message forwarding
- `POST /api/stop-forwarding` - Stop live message forwarding

## Development

The web interface uses:

- **FastAPI**: Modern async web framework
- **Jinja2**: Template engine for HTML rendering
- **Vanilla JavaScript**: Frontend interactions
- **CSS**: Custom styling for modern UI

## File Structure

```text
web/
├── app.py              # FastAPI application
├── templates/
│   └── index.html      # Main dashboard template
└── static/             # Static files (CSS, JS, images)
```

## Docker Support

The web interface is included in the Docker setup. To run with Docker:

```bash
docker-compose up web
```

This will start the web interface on port 8000 with the bot backend.