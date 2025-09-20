# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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

### Changed

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

### Added

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
