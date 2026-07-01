# Changelog

All notable changes to this project will be documented in this file.

Maintenance policy: keep this as a running changelog. Every project update must append a new versioned entry that includes what changed and, when relevant, a before/after behavior delta.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- New `Forward Media Files (Files/Images)` menu option (`source/dialog/MediaForwardDialog.py`, `Telegram.forward_media_files`) to forward only messages that carry a file/photo/video from a source chat's history, optionally filtered by keyword, in the order they were originally posted. Shares the same resumable progress tracking, date-range selection, and dry-run flow as `Past Forward Messages`.
- Dry-run preview for both `Past Forward Messages` and the new media forward now reports the **exact total count** of matching messages/files (not an estimate), and labels the count as "files" vs "messages" depending on mode.
- Extracted the shared month/date-range/timezone/dry-run prompts out of `ForwardDialog` and `KeywordForwardDialog` into a new `source/dialog/DateRangeDialog.py` mixin, reused by the new `MediaForwardDialog` — removes ~150 lines of duplicated dialog code across the three forwarding flows.
- Web dashboard now supports **dark mode**: a toggle button in the header switches between light/dark, defaults to the browser's `prefers-color-scheme`, and remembers the choice in `localStorage`. Colors were moved to CSS custom properties (`web/static/style.css`) so both themes share one set of component styles.
- The "Forwarding Configurations" and "Available Chats" sections on the web dashboard are now collapsible (`<details>`/`<summary>`), so a long chat list no longer forces you to scroll past it to reach other controls.

### Fixed

- The web dashboard's `GET /api/forwards` returned a 500 error on a fresh install (before any forward configs had been saved) because it called `ForwardConfig.read()` unconditionally instead of checking the file exists first, unlike the sibling `/api/status` endpoint. Now returns an empty list in that case.
- **Historical forwarding did not actually forward messages in the order they were posted.** `Forward._forward_chat_history` paged backward from the newest message in `DEFAULT_CHUNK_SIZE`-sized chunks and only reversed the order *within* each chunk — so across chunk boundaries, the global forward order looked like `[newest-chunk oldest→newest], [next-older-chunk oldest→newest], ...` rather than a single ascending sequence. Fixed by fetching chunks directly in ascending order via Telethon's `reverse=True`, which also lets the scan stop as soon as it passes the configured end date instead of always paging until a short chunk is returned.
- Re-running a forward (`Past Forward Messages` or the new media forward) over a source/date-range/mode that had already **completed** silently restarted from the beginning and could re-forward everything — `_load_progress` only resumed for a prior run marked `"in_progress"`, not `"completed"`. Since Telegram message IDs are never reused, it now resumes from the last processed message ID for both statuses, so re-running the same range (e.g. re-running "all of June") picks up after what's already been sent instead of duplicating it. Use `Clear Forward Progress Cache` to force a full re-scan.

- **CI was completely non-functional.** `pyproject.toml` had no `dev` or `docs` extras, so `pip install -e ".[dev]"` silently installed none of `ruff`/`mypy`/`pytest-asyncio`/`pytest-cov`, and every job in the `test` matrix failed at the linting step with `ruff: command not found`. Added `dev` and `docs` extras with the tools each CI step actually needs.
- `.github/workflows/ci.yml`'s `security` and `docs` jobs failed immediately (before running any of their steps) because `actions/upload-artifact@v3` is a hard-blocked deprecated action. Bumped to `v4`, along with `actions/setup-python@v4→v5`, `actions/cache@v3→v4`, and `codecov/codecov-action@v3→v4` in the same file to clear the accompanying deprecation warnings.
- The `docs` job's `cd docs && make html` had no `docs/` directory to build — added a minimal Sphinx scaffold (`docs/conf.py`, `docs/index.rst`, `docs/Makefile`) so the job builds real output instead of failing on a missing path.
- `mypy source/` (run with no config) failed with 16 pre-existing type errors across `DateUtils.py`, `Chat.py`, `KeywordForwardDialog.py`, and `ForwardDialog.py` — untyped-import noise from `telethon`, implicit-`Optional` parameter defaults, a `tzinfo | None` attribute access, a return-type mismatch on `Chat.scan_wanted_user`, and false positives from InquirerPy's `execute_async()` stubs being (incorrectly) typed as returning `None`. Fixed the real type issues and added `[tool.mypy]` config (`ignore_missing_imports`, and `follow_imports = "skip"` for `InquirerPy.*`) so the check reflects actual bugs instead of stub noise.
- `ruff format --check source/ tests/` (enforced by CI) failed on 13 files that had never been run through `ruff format` (only `black`, via pre-commit, had touched them, and the two formatters disagree on some edge cases). Reformatted the whole tree so the CI check and the pre-commit hook agree.
- `web/app.py`'s home page crashed with a 500 error (`TypeError: cannot use 'tuple' as a dict key`) on the pinned Starlette version — `templates.TemplateResponse("index.html", {"request": request})` uses the old, removed calling convention. Fixed to the current signature (`TemplateResponse(request, "index.html")`).
- `python-dotenv` was a declared dependency that nothing ever called — `cp .env.example .env` had no effect on a plain `python web/app.py` run, only under `docker-compose` (which substitutes `.env` itself). `web/app.py` now calls `load_dotenv()` on startup so the documented `.env` workflow actually works locally; real environment variables still take precedence.
- The web dashboard's own frontend (`web/templates/index.html`) called every `/api/*` endpoint with a bare `fetch()`, so the `X-API-Key` requirement added below broke the built-in UI (every button and the initial status load returned 401). Added an `apiFetch()` wrapper that prompts for the key once, sends it on every request, and re-prompts if the server rejects it.
- README instructions in all three install paths said to "edit `.env` with your Telegram API credentials," but `.env` only ever held web-dashboard settings (`API_KEY`, `WEB_HOST`, `WEB_PORT`) — Telegram credentials are entered interactively and stored in `resources/credentials.json`. Corrected each install path, and added a note that the web dashboard/Docker `web` service needs a session created by running `python main.py` once first.
- README had a `## Changelog Policy` section sitting between two subsections of `## Usage`, which made the `### Web API` heading that followed it read as a child of the changelog policy. Moved the changelog policy under `## Contributing` and restored `### Web API` as a subsection of `## Usage`, plus added a note there (and a `curl` example) that every `/api/*` route now requires the `X-API-Key` header.
- **History/reply mapping was broken for every queued forward.** `MessageForwardService.forward_message`/`forward_album` returned the *source* message immediately when queuing a send (since the real send happens later, asynchronously), and `Forward._forward_message`/`_forward_album` used that placeholder to record history mappings — meaning `(source_chat, source_id) -> (source_chat, source_id)` was stored instead of `(source_chat, source_id) -> (dest_chat, dest_id)`. Since `Telegram` always constructs a real queue, this hit every forward, silently breaking reply-threading. Fixed by passing an `on_sent` callback into the queue job that fires with the real destination message once it's actually sent, and updating history from that callback instead of the return value. Added regression tests covering the queued path.
- `requirements.txt` was missing `fastapi`, `uvicorn`, `jinja2`, `pydantic`, `python-dotenv`, `loguru`, and `aiofiles` (present in `pyproject.toml` but not `requirements.txt`), so `pip install -r requirements.txt` could not run `web/app.py`. Also dropped the obsolete `typing` PyPI backport, which can break stdlib `typing` on Python 3.10+.
- `web/app.py`'s startup handler checked for `TELEGRAM_API_ID`/`TELEGRAM_API_HASH`/`TELEGRAM_PHONE` env vars that the app never reads or sets (credentials come from `resources/credentials.json`) and then did nothing (`pass`), so `telegram_client` was never initialized and every `/api/*` route reported "not initialized". It now reuses the session created by the CLI (`python main.py`) via `Credentials.get_all()` + `Telegram.create()`.
- `source/model/Credentials.py` hardcoded `resources/credentials.json` separately from `Constants.CREDENTIALS_FILE_PATH`; now reuses the constant so the two can't diverge. The credentials file is also now written with `0600` permissions since it contains a plaintext `api_hash`.
- Resolved queue worker runtime error when forwarding messages on Telethon versions where `forward_messages` does not accept `reply_to`
- Updated forwarding paths (history and keyword) to use `forward_messages` without unsupported kwargs for cross-version compatibility

### Security

- All `/api/*` routes in `web/app.py` now require an `X-API-Key` header matching the `API_KEY` environment variable; the server refuses to serve API requests if `API_KEY` isn't set, rather than defaulting to an open API. Previously any network client that could reach the port could list chats, create/delete forward configs, and trigger keyword-forward against the user's real Telegram account.
- The web dashboard now binds to `127.0.0.1` by default instead of `0.0.0.0` (override with `WEB_HOST`/`WEB_PORT`). `docker-compose.yml`'s `web` service now publishes port 8000 on `127.0.0.1` only and requires `API_KEY` to be set (`docker compose up` fails fast with a clear error if it isn't).

### Removed

- Removed `source/utils/RateLimiter.py` (`RateLimitedQueue`) — dead code with zero references anywhere in the codebase; rate limiting is already handled by `MessageQueue`.
- Removed the `postgres`, `redis`, and `prometheus` services from `docker-compose.yml`. None of them were used by any application code, and the `postgres`/`prometheus` services referenced `./docker/postgres/init.sql` and `./docker/prometheus.yml`, which don't exist in the repo — enabling either profile would fail immediately.
- Removed the `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_PHONE`, `BOT_TOKEN`, `LOG_LEVEL`, `LOG_FILE`, `MAX_CONCURRENT_TASKS`, `MESSAGE_QUEUE_DELAY`, and `SECRET_KEY` entries from `.env.example`/`docker-compose.yml` — none of these were ever read anywhere in the application; only `API_KEY`, `WEB_HOST`, and `WEB_PORT` are real, load-bearing settings.

### Changed

- `Bot.start()` no longer wraps its body in a `try/except Exception as err: raise err`, which was a no-op that just added noise.
- `main.py`'s `shutdown()` now logs any non-cancellation exception raised by a task during shutdown instead of silently discarding it via `return_exceptions=True`.

## [2.3.0] - 2026-03-31

### Added in 2.3.0

- Web API endpoint `POST /api/keyword-forward` for keyword-based forwarding from dashboard
- Web API endpoint `GET /api/status` for dashboard status/queue telemetry
- Dashboard keyword-forward form with optional date range, timezone, scan limit, and dry-run toggle

### Changed in 2.3.0

- Web dashboard template was rebuilt to valid HTML and aligned with current API behavior
- `Telegram.list_chats()` now returns chat objects in addition to console output, enabling web API chat responses
- README badge section expanded with project-relevant Shields.io badges

### Before vs After in 2.3.0

- Before: dashboard could not run keyword-forward workflows and status endpoint used by UI was missing.
- After: dashboard can run keyword-forward requests and poll a status endpoint for queue and uptime metrics.
- Before: README had minimal badges.
- After: README includes version, Docker, FastAPI, and Telethon shields in addition to Python and license.

## [2.2.0] - 2026-03-31

### Added in 2.2.0

- Keyword-based search and forwarding workflow from the main menu
- Date + timezone filtering and dry-run preview for keyword-forward operations
- Dedicated Docker Compose `web` service for dashboard startup
- New keyword-forward unit tests

### Changed in 2.2.0

- Main menu now includes `Keyword Search + Forward` and shifts option ordering
- Docker build now includes `web/` assets for containerized web startup

### Before vs After in 2.2.0

- Before: only live/past forward workflows were available.
- After: users can search source history by keyword and forward only matching messages.
- Before: `web/README.md` referenced a compose service that was not defined.
- After: compose includes a `web` service and docs match real startup commands.

## [2.1.0] - 2026-03-31

### Added in 2.1.0

- Timezone-aware date filtering for historical forwarding windows
- Dry-run preview mode to count matching messages without forwarding
- Forward progress cache cleanup command in the main menu
- Regression and integration tests for forwarding service paging and date boundaries

### Changed in 2.1.0

- Historical forwarding now uses strict date boundaries (`start <= message.date <= end`)
- Progress tracking keys now include source + date-range to prevent resume collisions across different date windows

### Fixed

- Album forwarding crash from invalid `send_messages` call
- Queue worker stability for long-running workloads by always acknowledging completed/failed tasks

### Added in modernization cycle

- Modern Python project structure with `pyproject.toml`
- Comprehensive type hints throughout the codebase
- Async/await patterns with structured concurrency
- Rich console output with modern formatting
- Environment variable management with `.env` support
- Comprehensive test suite with pytest
- CI/CD pipeline with GitHub Actions
- Code quality tools (black, isort, ruff, mypy)
- Pre-commit hooks for automated code quality
- Security scanning with bandit and safety
- Professional documentation with README and API docs
- Logging system with loguru
- Pydantic models for data validation
- Dependency injection patterns

### Changed in modernization cycle

- Migrated from `requirements.txt` to `pyproject.toml`
- Updated to Python 3.10+ features and syntax
- Improved error handling with custom exceptions
- Enhanced async patterns with modern Python features

### Technical Improvements

- Added comprehensive type annotations
- Implemented modern async/await patterns
- Added structured logging with loguru
- Integrated Pydantic for data validation
- Added comprehensive test coverage
- Implemented CI/CD with multiple quality checks
- Added security scanning and vulnerability checks

## [2.0.0] - 2025-01-19

### Added in 2.0.0

- Initial release of Telegram Forwarder Bot v2
- Async architecture with Telethon integration
- Multi-account support
- Live and historical message forwarding
- Rate limiting and queue management
- Console-based user interface
- JSON-based data persistence

### Key Features

- Real-time message forwarding with event handlers
- Bulk message forwarding from chat history
- Multiple Telegram account management
- Built-in rate limiting to respect API limits
- Beautiful terminal interface with Rich
- Secure credential management

---

## Types of changes

- `Added` for new features
- `Changed` for changes in existing functionality
- `Deprecated` for soon-to-be removed features
- `Removed` for now removed features
- `Fixed` for any bug fixes
- `Security` in case of vulnerabilities

## Versioning

This project uses [Semantic Versioning](https://semver.org/). For the versions available, see the [tags on this repository](https://github.com/klept0/Telegram-Forwarder-Bot-v2/tags).
