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

   Or using module syntax:

   ```bash
   python -m web.app
   ```

   Run it from the project root, not from `web/`: data paths like
   `resources/` are relative to the current directory, so starting it inside
   `web/` would look for credentials in `web/resources/` and find none.

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

- `POST /api/start-forwarding` - Start live forwarding for every enabled configuration (`400` if none are enabled, `409` if already running). Configs are read at start; stop and start again after changing them.
- `POST /api/stop-forwarding` - Stop live forwarding (`409` if not running)

### Keyword Forwarding

- `POST /api/keyword-forward` - Forward messages, optionally filtered by keyword (omit it to forward everything in range) — supports date range, timezone, dry-run, and (with a date range) resumes without re-forwarding what was already sent

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
docker compose up -d --build web
```

The `web` service depends on `telegram-forwarder`, so this starts both. The
dashboard is published on `127.0.0.1:8000` and shares `resources/` and
`sessions/` with the bot. Don't run live forwarding from the bot menu and the
dashboard at the same time, because they share one Telegram session.
