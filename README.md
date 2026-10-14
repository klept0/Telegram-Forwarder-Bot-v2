# Telegram Forwarder Bot v2

[![Python Version](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Fklept0%2FTelegram-Forwarder-Bot-v2%2Fmain%2Fpyproject.toml&label=python&color=blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Release](https://img.shields.io/github/v/release/klept0/Telegram-Forwarder-Bot-v2?color=0A66C2)](https://github.com/klept0/Telegram-Forwarder-Bot-v2/releases/latest)
[![CI](https://github.com/klept0/Telegram-Forwarder-Bot-v2/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/klept0/Telegram-Forwarder-Bot-v2/actions/workflows/ci.yml)
[![Docker](https://img.shields.io/badge/docker-supported-2496ED.svg?logo=docker&logoColor=white)](docker-compose.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688.svg?logo=fastapi&logoColor=white)](web/app.py)
[![Telethon](https://img.shields.io/badge/Telethon-1.40+-2CA5E0.svg)](https://github.com/LonamiWebs/Telethon)

Forward Telegram messages between chats from your own account, either live as
they arrive or from a chat's history. Use it from an interactive terminal menu
or a small web dashboard. Built with Telethon and Rich.

This project is based on the [original Telegram Forwarder Bot](https://github.com/MohammadShabib/Telegram-Forwarder-Bot) by Mohammad Shabib.

## Features

- 🔄 **Live forwarding**: new messages are forwarded as they arrive, from any number of source chats
- 📚 **History forwarding**: forward a chat's past messages oldest-first, filtered by month, several months, or a date range in any timezone
- 🔍 **Keyword and media filters**: forward only messages matching a keyword, or only files, photos and videos
- 🧵 **Threads and albums kept**: replies stay replies to the forwarded original, and albums arrive as albums
- ⏯️ **Resumable, with dry runs**: interrupted runs pick up where they stopped without duplicates, and a dry run counts matches before anything is sent
- 📝 **Phrase watch → file**: log every new message containing a phrase to a Markdown file
- 🌐 **Web dashboard**: manage forwarding configurations and start or stop live forwarding from a browser, behind an API key
- 👥 **Multiple accounts**, **Docker support**, and paced sending that waits out Telegram flood limits instead of dropping messages

## Before you start

> [!WARNING]
> This bot logs in as **your personal Telegram account** (not a bot account)
> and acts on its behalf.
>
> - **Account limits:** Telegram may temporarily restrict accounts that
>   forward large volumes quickly. The bot paces sends and waits out flood
>   limits, but very large history runs are still at your own risk.
> - **Protected chats:** messages from chats with *Restrict saving content*
>   enabled can't be forwarded. Those sends fail and are skipped with an error.
> - **One live job at a time:** Live Forward and Phrase Watch both run until
>   you press Ctrl+C, so only one can run per bot instance. The bot and the web
>   dashboard share one login session, so don't run live forwarding in both at
>   once.
> - **Your session file is your account:** anyone with `sessions/` can act as
>   you. It's gitignored; keep it that way.

You'll need:

- Python 3.10 or newer, or Docker
- A Telegram **API ID** and **API hash**:
  1. Sign in at [my.telegram.org](https://my.telegram.org) with your phone number
  2. Open **API development tools** and create an application
  3. Copy the `api_id` and `api_hash`

## Install

```bash
git clone https://github.com/klept0/Telegram-Forwarder-Bot-v2.git
cd Telegram-Forwarder-Bot-v2
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
```

Always run the bot and the dashboard **from the project root**. Data paths
like `resources/` are relative to the current directory.

## First run

```bash
python main.py
```

1. Enter your **API ID**, **API hash**, and **phone number** (international
   format, e.g. `+15551234567`). They're saved to `resources/credentials.json`
   with owner-only permissions.
2. Enter the **login code** Telegram sends you and, if you use two-step
   verification, your **password**. This creates a session under `sessions/`,
   so you won't be asked again.
3. Choose **List Chats** from the menu. **Do this before anything else:**
   every chat picker reads the list it saves (`resources/chats.json`). Run it
   again whenever you join new chats.
4. Pick what you want to do (see [Which option do I use?](#which-option-do-i-use)).
   For history forwards, try a **dry run** first.

## Which option do I use?

| Option | Works on | Filters | Resumable | Dry run | Replies & albums kept |
| :-- | :-- | :-- | :-- | :-- | :-- |
| **Live Forward Messages** | New messages, until Ctrl+C | — | — | — | ✅ |
| **Past Forward Messages** | History, oldest-first | Date range | ✅ | ✅ | ✅ |
| **Forward Media Files** | History, files/photos/videos only | Date range, keyword | ✅ | ✅ | ✅ |
| **Keyword Search + Forward** | History (Telegram search when a keyword is given) | Keyword (optional), date range, max messages to scan | ✅ with a start **and** end date | ✅ | ❌ sent as individual messages |
| **Watch Chat for Phrase → File** | New messages, until Ctrl+C | Phrase | — | — | Writes to a file, doesn't forward |

**Resumable** means re-running the same source, date range, and filters picks
up after the last message already forwarded, whether the previous run finished
or was interrupted, so nothing is sent twice. To deliberately start a range
over, use **Clear Forward Progress Cache** first. That clears progress for
*every* chat and range.

### Main menu

1. **Add/Update Credentials**: add another account's API credentials
2. **List Chats**: refresh the saved chat list
3. **Delete My Messages**: delete every message you sent in your groups, except chats on the ignore list (⚠️ irreversible)
4. **Find User Messages**: print a user's recent messages from every group/channel (chat, date, text, link) and the total found
5. **Live Forward Messages**
6. **Past Forward Messages**
7. **Keyword Search + Forward**
8. **Forward Media Files (Files/Images)**
9. **Switch Account**
10. **Clear Forward Progress Cache**
11. **Watch Chat for Phrase → File**
12. **Exit**

### Forwarding configurations

Live and Past forwarding use saved **source → destination** pairs. Choose
**New settings** to pick pairs (select **Stop** when done), or reuse the saved
ones. You're then asked for a date filter (none, one month, several months,
or a custom range) and, if you choose one, a timezone (UTC, your local zone,
or any IANA name like `America/New_York`) and whether to dry-run. These only
affect Past forwarding; Live forwarding ignores them.

Pairs can be enabled or disabled from the web dashboard. Disabled pairs show
as `[disabled]` and are skipped.

How replies and albums are handled:

- **Replies:** if the message being replied to was forwarded earlier, the
  reply is forwarded as a reply to that copy, still showing "Forwarded from".
  If the original wasn't forwarded (e.g. it's outside the date range), the
  reply is forwarded normally.
- **Albums:** photos and videos sent together are forwarded together.

History runs show progress against an **estimated** total; a dry run gives
the exact count.

### Watch Chat for Phrase → File

Pick a chat, type a phrase, and choose an output file (default
`logs/phrase_<chat_name>.md`). Every new message containing the phrase
(case-insensitive, anywhere in the text or caption) is appended until you
press Ctrl+C. Each entry has its UTC time, the sender (in groups), a link to
the message, and the text:

```markdown
## 2026-10-13 14:05:09 UTC

[Open in Telegram](https://t.me/c/1234/2)

> ALERT: server down in eu-1
```

Multi-line posts keep one line per entry. Re-running with the same file keeps
appending to it, and you can name it `.txt` if you prefer. Only messages that
arrive while the watch runs are logged.

## Web dashboard

The dashboard reuses the session from [First run](#first-run); it never asks
for a Telegram login itself.

1. Create `.env` in the project root and set an API key:

   ```bash
   cp .env.example .env
   # then set API_KEY to a long random value
   ```

   ```env
   API_KEY=change_me_to_a_long_random_value  # required
   WEB_HOST=127.0.0.1                         # optional (default)
   WEB_PORT=8000                              # optional (default)
   ```

2. Start it from the project root: `python web/app.py`, or
   `python -m web.app`.
3. Open <http://localhost:8000>. The page asks for the `API_KEY` once and
   remembers it in that browser.

The dashboard shows bot status and the send queue, browses chats, adds,
enables, disables and deletes forwarding configurations, and starts or stops
live forwarding for all enabled configurations. It binds to `127.0.0.1` by
default. Only set `WEB_HOST=0.0.0.0` behind a reverse proxy.

### Web API

Every `/api/*` route requires an `X-API-Key` header matching `API_KEY`.
Interactive API docs are at <http://localhost:8000/docs>; enter your key in
the `x-api-key` field to try requests.

| Method & path | What it does |
| :-- | :-- |
| `GET /api/status` | Status, queue size, current task, uptime, enabled configurations |
| `GET /api/chats` | List the account's chats |
| `GET /api/forwards` | List forwarding configurations |
| `POST /api/forwards` | Create one: `source_id`, `source_name`, `destination_id`, `destination_name`, `enabled` |
| `DELETE /api/forwards/{source_id}` | Delete one |
| `POST /api/forwards/{source_id}/toggle` | Enable/disable one |
| `POST /api/start-forwarding` | Start live forwarding for all enabled configurations (`400` if none, `409` if already running) |
| `POST /api/stop-forwarding` | Stop live forwarding (`409` if not running) |
| `POST /api/keyword-forward` | Run a Keyword Search + Forward (below) |

Configurations are read when live forwarding starts. After changing them,
stop and start again.

Example keyword forward (only `source_id` and `destination_id` are required):

```bash
curl -X POST http://localhost:8000/api/keyword-forward \
  -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{
        "source_id": -1001234567890,
        "destination_id": -1009876543210,
        "keyword": "invoice",
        "limit": 500,
        "start_date": "2026-06-01",
        "end_date": "2026-06-30",
        "timezone_name": "UTC",
        "dry_run": true
      }'
# {"message": "Keyword run completed: 12 messages previewed for keyword 'invoice'."}
```

Omit `keyword` to forward everything in the range; `limit` (default 500) caps
how many messages are scanned. Chat IDs come from `GET /api/chats`.

## Docker

1. `cp .env.example .env` and set `API_KEY` (required by the `web` service).
2. Log in once, interactively:

   ```bash
   docker compose run --rm telegram-forwarder
   ```

   Complete the [First run](#first-run) steps, then exit. The session and
   credentials are saved to the mounted `sessions/` and `resources/` folders.
3. Start the bot and the dashboard in the background:

   ```bash
   docker compose up -d --build
   ```

4. Use the bot's menu by attaching to it:

   ```bash
   docker attach telegram-forwarder-bot
   ```

   Press Enter if the menu doesn't redraw. Detach **without stopping it** with
   `Ctrl+P` then `Ctrl+Q`; `Ctrl+C` while attached stops the container.

Logs: `docker compose logs -f telegram-forwarder` · Stop: `docker compose down`

`resources/`, `sessions/`, `media/` and `logs/` are bind-mounted from the
project folder, so they survive rebuilds. The dashboard is published on
`127.0.0.1:8000` only. Older Docker installs use `docker-compose` instead of
`docker compose`.

## Where your data lives

| Path | Contents | If deleted |
| :-- | :-- | :-- |
| `resources/credentials.json` | API ID, API hash, phone number (owner-only permissions) | You re-enter credentials |
| `sessions/` | Logged-in Telegram session | You log in again with a code |
| `resources/chats.json` | Chat list from **List Chats** | Run **List Chats** again |
| `resources/forwardConfig.json` | Saved source → destination pairs | Saved forwarding settings are lost |
| `resources/forward_progress.json` | Resume points for history forwards | The next run starts from the beginning |
| `resources/history.json` | Source → destination message IDs, used to thread replies | Replies to earlier forwards aren't threaded |
| `logs/phrase_*.md` | Phrase-watch output | Recreated on the next match |
| `.env` | Web dashboard settings | The dashboard refuses API requests |

All of these are gitignored.

## Troubleshooting

| Symptom | What to do |
| :-- | :-- |
| A chat is missing from the picker, or the picker is empty | Run **List Chats** to refresh the saved list. |
| `Rate limited by Telegram; waiting Ns before retrying…` | Normal. The bot waits as long as Telegram asks and retries (up to 3 times). Leave it running. |
| `Queue Worker Error (message(chat=…, id=…))` | That one message failed and was skipped, often because the source chat restricts saving content. |
| Re-running a range forwards nothing | That range already completed. Use **Clear Forward Progress Cache** to redo it. |
| A forwarded reply isn't shown as a reply | Its original wasn't forwarded (e.g. outside the date range), so it was forwarded normally. |
| Asked for a login code again | The session was deleted or revoked (Telegram → Settings → Devices). Log in again. |
| Dashboard shows "Not Initialized" | No logged-in session yet. Complete [First run](#first-run), then restart the dashboard. |
| API returns `503` "missing API_KEY" | Set `API_KEY` in `.env` and restart the dashboard. |
| API returns `401` | Wrong key. The page asks for it again. |
| Start Forwarding says "No enabled forwarding configurations" | Add a configuration, or enable one. |
| Docker bot container keeps restarting | Make sure `docker-compose.yml` has `stdin_open: true` and `tty: true` for `telegram-forwarder`, then `docker compose up -d --build`. |
| Files appear in an unexpected `resources/` or `logs/` folder | You started it outside the project root. `cd` there first. |

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for the
development setup, the checks CI runs, the project layout, and how releases
are made. Changes are recorded in [CHANGELOG.md](CHANGELOG.md).

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

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
