# Changelog

All notable changes to this project will be documented in this file.

Maintenance policy: keep this as a running changelog. Every project update must append a new versioned entry that includes what changed and, when relevant, a before/after behavior delta.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
