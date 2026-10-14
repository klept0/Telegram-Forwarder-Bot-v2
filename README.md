# Telegram Forwarder Bot v2

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Release](https://img.shields.io/github/v/release/klept0/Telegram-Forwarder-Bot-v2?color=0A66C2)](https://github.com/klept0/Telegram-Forwarder-Bot-v2/releases/latest)
[![CI](https://github.com/klept0/Telegram-Forwarder-Bot-v2/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/klept0/Telegram-Forwarder-Bot-v2/actions/workflows/ci.yml)
[![Docker](https://img.shields.io/badge/docker-supported-2496ED.svg?logo=docker&logoColor=white)](docker-compose.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688.svg?logo=fastapi&logoColor=white)](web/app.py)
[![Telethon](https://img.shields.io/badge/Telethon-1.40+-2CA5E0.svg)](https://github.com/LonamiWebs/Telethon)

An asynchronous Telegram message forwarding bot with a modern Python architecture, built with Telethon and Rich.

This project is based on the [original Telegram Forwarder Bot](https://github.com/MohammadShabib/Telegram-Forwarder-Bot) by Mohammad Shabib.

## Features

- 🚀 **Async/Await**: Fully asynchronous architecture for high performance
- 🔄 **Live Forwarding**: Real-time message forwarding with event handlers
- 🧵 **Threads & Albums Preserved**: Replies stay replies to the forwarded parent, and albums are forwarded as albums
- 📚 **History Forwarding**: Bulk message forwarding from chat history with date filtering
- 📅 **Month Filtering**: Forward messages from specific months or date ranges
- 🌍 **Timezone-Aware Date Filters**: Apply date windows in UTC, local, or custom IANA timezone
- 🔎 **Dry-Run Preview**: Count matching historical messages before forwarding
- 📊 **Progress Tracking**: Real-time progress indicators showing completion percentage
- 📝 **Phrase Watch → File**: Watch a chat live and append every message containing a phrase to a Markdown file
- 🔍 **Keyword Search Forwarding**: Search source chat history by an optional keyword and forward matching (or all) messages, resumable over a date range
- 👥 **Multi-Account Support**: Switch between multiple Telegram accounts
- 🎯 **Rate Limiting**: Sends are queued and paced, and Telegram flood waits are waited out and retried instead of dropping messages
- 🎨 **Rich Console UI**: Beautiful terminal interface with Rich
- 🌐 **Web Dashboard**: FastAPI-based web interface for remote management
- 🔒 **Secure**: Credentials and sessions stay local (credentials file is owner-only), and the web API requires an API key
- ✅ **Tested**: pytest suite, ruff, and mypy run in CI on Python 3.10–3.13
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

4. **Run the bot:**

   ```bash
   python main.py
   ```

   You'll be prompted for your Telegram API credentials on first run; they're
   saved to `resources/credentials.json` for reuse (no `.env` file needed for
   the CLI — that's only required if you also run the web dashboard, see
   [Configuration](#configuration)).

#### Option 2: Docker Installation (Recommended for Production)

1. **Clone the repository:**

   ```bash
   git clone https://github.com/klept0/Telegram-Forwarder-Bot-v2.git
   cd Telegram-Forwarder-Bot-v2
   ```

2. **Set up environment variables:**

   ```bash
   cp .env.example .env
   # Edit .env and set API_KEY (required by the web service, see Configuration below)
   ```

3. **Authenticate once, interactively, before running detached:**

   The `telegram-forwarder` container runs `python main.py`, which prompts
   for your Telegram API credentials and login code on first use. Run it
   attached the first time so you can answer the prompts:

   ```bash
   docker compose run --rm telegram-forwarder
   ```

   This saves a session under `./sessions` and credentials under
   `./resources`, which are mounted as volumes — subsequent runs (including
   the `web` service) reuse that session without prompting again.

4. **Start in the background:**

   ```bash
   docker compose up -d --build
   ```

5. **Use the menu:** the bot is an interactive menu, so attach to it:

   ```bash
   docker attach telegram-forwarder-bot
   ```

   Press Enter if the menu doesn't redraw. Detach **without stopping it** with
   `Ctrl+P` then `Ctrl+Q`. `Ctrl+C` while attached stops the container.

6. **View logs:**

   ```bash
   docker compose logs -f telegram-forwarder
   ```

7. **Stop everything:**

   ```bash
   docker compose down
   ```

**Docker Notes:**

- `resources/`, `sessions/`, `media/` and `logs/` are bind-mounted from the project folder, so settings, the login session, and phrase-watch files survive rebuilds
- The web service's `API_KEY` is loaded from the `.env` file; `docker compose up` fails fast with a clear error if it isn't set
- The bot and the web dashboard share one Telegram session. Don't run live forwarding from both at the same time
- The bot runs as a non-root user for security
- Older Docker installs use `docker-compose` (with a hyphen) instead of `docker compose`

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

4. **Authenticate an account first, via the CLI:**

   The web dashboard never prompts for a Telegram login itself — it reuses
   the session created by the CLI. Run `python main.py` once, answer the
   credential/login prompts, then exit; this saves a session under
   `./sessions` and credentials under `./resources`.

5. **Set up environment variables:**

   ```bash
   cp .env.example .env
   # Edit .env and set API_KEY (the dashboard refuses to serve API
   # requests without it — see Configuration below)
   ```

6. **Run the web dashboard:**

   ```bash
   python web/app.py
   ```

   Or, equivalently:

   ```bash
   python -m web.app
   ```

   Always start it from the project root: data paths like `resources/` are
   relative to the current directory.

7. **Open your browser:**

   Navigate to `http://localhost:8000` to access the web interface. The
   page will prompt you once for the `API_KEY` value and remember it in
   the browser's local storage for subsequent requests.

**Web Interface Features:**

- Real-time bot status monitoring
- Forward configuration management
- Chat browser and selection
- REST API for programmatic access
- Remote control of forwarding operations
- Dark mode (follows system preference, toggle in the header)
- Collapsible sections for long lists (Forwarding Configurations, Available Chats)

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
3. **Delete My Messages** - Delete every message you sent in your groups, except chats on the ignore list (⚠️ irreversible)
4. **Find User Messages** - Print a user's recent messages from every group/channel (chat, date, text, link) and the total found
5. **Live Forward Messages** - Start real-time message forwarding
6. **Past Forward Messages** - Forward historical messages
7. **Keyword Search + Forward** - Search by keyword and forward matching messages
8. **Forward Media Files (Files/Images)** - Forward all files/images (optionally keyword-filtered) from a date range, in the order they were posted
9. **Switch Account** - Change between configured accounts
10. **Clear Forward Progress Cache** - Reset saved resume state for historical forwarding
11. **Watch Chat for Phrase → File** - Watch a chat live and append messages containing a phrase to a Markdown file
12. **Exit** - Close the application

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

Replies and albums are preserved in live, past, and media forwarding:

- **Replies**: if the message being replied to was forwarded earlier, the
  reply is forwarded as a reply to that copy, still showing "Forwarded from".
  If the original wasn't forwarded (e.g. it's outside the date range), the
  reply is forwarded normally.
- **Albums**: photos/videos sent together are forwarded together as one album.

When forwarding historical messages, the bot displays real-time progress indicators showing:

- An approximate number of messages to forward
- Current progress (X/Y messages)
- Percentage completion (against the estimate; use a dry run for an exact count)

### Keyword Search + Forward

Use the `Keyword Search + Forward` menu option to:

- Select source and destination chats
- Optionally enter a keyword to search in source chat history — leave it
  blank to forward every message in range instead of filtering by keyword
- Optionally set date range + timezone filtering
- Run dry-run preview (count matches only) or forward matches

Matching messages are forwarded in chronological order. When a date range is
selected, this is resumable: re-running the exact same source, date range,
and keyword — whether the previous run finished or was interrupted — checks
what's already been forwarded and only sends what hasn't been, instead of
duplicating messages. Use `Clear Forward Progress Cache` to force a full
re-scan of a range you've already run.

### Forward Media Files (Files/Images)

Use the `Forward Media Files` menu option to forward only messages that
carry a file, photo, or video from a source chat's history — in the order
they were originally posted:

- Select source and destination chats
- Optionally filter to files whose caption/text matches a keyword
- Pick a date range (no filter, a specific month, multiple months, or a
  custom range — e.g. "all of June")
- Timezone selection and dry-run preview, same as the other forward flows

Dry-run preview reports the **total number of matching files**, not an
estimate. Real runs are resumable: if you re-run the exact same source,
date range, and keyword/media combination — whether the previous run
finished or was interrupted — it picks up right after the last file it
already forwarded instead of sending duplicates. To force a full re-scan
of a range you've already run, use `Clear Forward Progress Cache` first.

### Watch Chat for Phrase → File

Use the `Watch Chat for Phrase → File` menu option to keep a running log of
every new message in one chat that contains a phrase:

- Select the chat to watch (run `List Chats` first so it appears)
- Enter the phrase — matching is case-insensitive and finds the phrase
  anywhere in the message text or caption
- Choose the output file (defaults to `logs/phrase_<chat_name>.md`)

The bot then listens live, like `Live Forward Messages`, until you press
Ctrl+C. Each match is appended as a Markdown entry with its UTC timestamp,
the sender (in groups), a link back to the message, and the message text as a
quote. Re-running with the same file keeps appending to it. Markdown is plain
text, so you can name the file `.txt` if you prefer. Only messages that arrive
while the watch is running are logged; earlier history isn't scanned.

Example entry:

```markdown
## 2026-10-13 14:05:09 UTC

[Open in Telegram](https://t.me/c/1234/2)

> ALERT: server down in eu-1
```

In Docker, `logs/` is already mounted as a volume, so the file is kept on the
host.

### Web API

The web interface provides a REST API for programmatic access. Every
`/api/*` route requires an `X-API-Key` header matching the server's
`API_KEY` environment variable (see [Configuration](#configuration)):

```bash
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/status
```

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

- `POST /api/start-forwarding` - Start live forwarding for every enabled configuration (`400` if none are enabled, `409` if already running). Configs are read at start; stop and start again after changing them.
- `POST /api/stop-forwarding` - Stop live forwarding (`409` if not running)

#### Keyword Forwarding

- `POST /api/keyword-forward` - Forward messages in a source chat, optionally filtered by keyword (omit `keyword` to forward everything in range) — supports dry-run and, with a date range, resumes without re-forwarding what was already sent

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
│       ├── Constants.py
│       ├── DateUtils.py
│       └── FileUtils.py
├── web/
│   ├── app.py
│   ├── static/
│   ├── templates/
│   └── README.md
├── docs/
│   ├── conf.py
│   ├── index.rst
│   └── Makefile
├── tests/
├── .github/
│   ├── scripts/changelog_section.py
│   └── workflows/ci.yml
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── CHANGELOG.md
├── Dockerfile
├── docker-compose.yml
├── LICENSE
├── main.py
├── pyproject.toml
├── requirements.txt
└── README.md

# Created at runtime (gitignored): resources/, sessions/, media/, logs/
```

### Running Tests and Checks

Install the dev tools, then run the same checks CI runs:

```bash
pip install -e ".[dev]"
ruff check source/ tests/
ruff format --check source/ tests/
mypy source/
pytest tests/ --cov=source
```

### Building Documentation

```bash
pip install -e ".[docs]"
cd docs
make html  # output in docs/_build/html/
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

### Changelog Policy

`CHANGELOG.md` is maintained as a running log for every update. Each release entry should include:

- `Added`/`Changed`/`Fixed` details
- Explicit behavior delta when relevant (before vs after)
- Release date and semantic version

### Releasing

Releases are published automatically. To cut one:

1. Bump `version` in `pyproject.toml` (and keep `web/app.py` and
   `docs/conf.py` in step).
2. Move the `[Unreleased]` entries in `CHANGELOG.md` under a new
   `## [X.Y.Z] - YYYY-MM-DD` heading.
3. Merge to `main`.

When CI passes on `main` and no `vX.Y.Z` tag exists yet, the `release` job
tags that commit, publishes a GitHub release whose notes are the matching
CHANGELOG section, and attaches the built package (`dist/`). If the
CHANGELOG has no section for the version, GitHub's generated notes are used
instead. Pushes that don't change the version publish nothing.

## Security

- Never commit API credentials or sensitive data (`resources/credentials.json` and `sessions/` are gitignored)
- The web dashboard requires an `API_KEY` and refuses to serve `/api/*` requests without one; it binds to `127.0.0.1` by default
- Regularly update dependencies for security patches
- Follow principle of least privilege

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Telethon](https://github.com/LonamiWebs/Telethon) - Telegram client library
- [Rich](https://github.com/Textualize/rich) - Beautiful terminal output
- [InquirerPy](https://github.com/kazhala/InquirerPy) - Interactive terminal menus
- [FastAPI](https://github.com/tiangolo/fastapi) - Modern web framework
- [Pydantic](https://github.com/pydantic/pydantic) - Data validation
- [Uvicorn](https://github.com/encode/uvicorn) - ASGI server

## Support

If you find this project helpful, please give it a ⭐️!

For questions or issues:

- Open an [issue](https://github.com/klept0/Telegram-Forwarder-Bot-v2/issues)
- Check the [documentation](https://github.com/klept0/Telegram-Forwarder-Bot-v2/wiki)
