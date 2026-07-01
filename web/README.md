# Telegram Forwarder Bot - Web Interface

This directory contains the FastAPI web interface for the Telegram Forwarder Bot.

## Features

- **Dashboard**: Real-time bot status monitoring
- **Forward Management**: Create, enable/disable, and delete forwarding configurations
- **Chat Browser**: View and select available Telegram chats
- **Control Panel**: Start/stop forwarding operations
- **REST API**: Full REST API for programmatic access
- **Dark mode**: Toggle in the header, follows your browser's `prefers-color-scheme` by default, remembered per-browser
- **Collapsible sections**: Long lists (Forwarding Configurations, Available Chats) collapse so they don't push other controls off-screen

## Authentication

Every `/api/*` route requires an `X-API-Key` header matching the server's
`API_KEY` environment variable — the server refuses to serve requests if
`API_KEY` isn't set. The dashboard page itself prompts for the key once and
remembers it in the browser's `localStorage`. For `curl`/scripts:

```bash
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/status
```

The dashboard also never logs into Telegram itself — run `python main.py`
once from the project root to authenticate an account; the web interface
reuses that session.

## Quick Start

1. Install dependencies:

   ```bash
   pip install -e ".[web]"
   ```

2. Run the web interface:

   From the project root:

   ```bash
   python web/app.py
   ```

   Or from the web directory:

   ```bash
   cd web
   python app.py
   ```

   Or using module syntax:

   ```bash
   python -m web.app
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

### Keyword Forwarding

- `POST /api/keyword-forward` - Search by keyword and forward matching messages (supports date range, timezone, and dry-run)

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
docker-compose up --build web
```

To run both bot + web together:

```bash
docker-compose up --build telegram-forwarder web
```

This starts the web interface on port 8000 with shared project resources.
