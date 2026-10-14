# Contributing

Thanks for helping improve Telegram Forwarder Bot v2. This page covers the
development setup, the checks every change must pass, how the code is laid
out, and how releases are made.

## Development setup

```bash
git clone https://github.com/klept0/Telegram-Forwarder-Bot-v2.git
cd Telegram-Forwarder-Bot-v2
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Checks

CI runs these on Python 3.10, 3.11, 3.12 and 3.13, and all of them must pass
before a pull request can be merged:

```bash
ruff check source/ tests/
ruff format --check source/ tests/
mypy source/
pytest tests/ --cov=source
```

Ruff's lint rules are pinned in `pyproject.toml` (`[tool.ruff.lint] select`)
so a new ruff release can't change what CI enforces. Change that list
deliberately, in its own commit.

To build the Sphinx docs (CI does this too):

```bash
pip install -e ".[docs]"
cd docs
make html  # output in docs/_build/html/
```

## Pull requests

`main` is protected: changes go through a pull request, the CI checks above
must pass, and a review is required.

1. Branch from `main` (e.g. `feature/…`, `fix/…`, `docs/…`).
2. Add or update tests for any behavior change. Regression tests should fail
   without the fix.
3. Add an entry under `## [Unreleased]` in `CHANGELOG.md` (see below).
4. Update `README.md` when user-facing behavior, menu options, or API routes
   change.
5. Open the pull request with a summary and a test plan.

Conventions:

- Match the surrounding code: naming, comment density, and the existing
  layering (dialogs gather input, `Telegram` orchestrates, services do the
  work).
- Add type hints to new functions.
- `main.py`, `requirements.txt` and `source/service/MessageQueue.py` use
  **CRLF** line endings. Keep them that way when editing.
- Never commit anything from `resources/`, `sessions/`, `media/`, `logs/` or
  `.env`.

## Changelog policy

`CHANGELOG.md` follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and is updated with every change. Each entry should say what changed and,
when behavior changes, what it did before and after. Group entries under
`Added`, `Changed`, `Fixed`, `Removed` or `Security`.

## Releasing

Releases are published automatically:

1. Bump `version` in `pyproject.toml`, and keep `web/app.py` (`version=`) and
   `docs/conf.py` (`release =`) in step.
2. Add a `## [X.Y.Z] - YYYY-MM-DD` heading directly under `## [Unreleased]`
   in `CHANGELOG.md`, so the unreleased entries now belong to that version.
3. Merge to `main`.

When CI passes on `main` and no `vX.Y.Z` tag exists yet, the `release` job
tags that commit and publishes a GitHub release. Its notes are the matching
CHANGELOG section, and the built package (`dist/`) is attached. If the
CHANGELOG has no section for the version, GitHub's generated notes are used
instead. Pushes that don't change the version publish nothing.

Versions follow [Semantic Versioning](https://semver.org/): patch for fixes,
minor for new features, major for breaking changes.

## Project layout

```text
telegram-forwarder-bot-v2/
├── main.py                 # CLI entry point
├── source/
│   ├── core/               # Bot (startup) and Telegram (client + orchestration)
│   ├── dialog/             # Interactive prompts that gather settings
│   ├── menu/               # Main menu and account selector
│   ├── model/              # Persisted data: chats, credentials, forward configs, history
│   ├── service/            # Forwarding, queue, progress, phrase watch, messages
│   └── utils/              # Constants, dates, atomic file writes, console
├── web/
│   ├── app.py              # FastAPI dashboard and REST API
│   ├── static/
│   ├── templates/
│   └── README.md
├── tests/
├── docs/                   # Sphinx scaffold
├── .github/
│   ├── scripts/changelog_section.py   # Extracts release notes
│   └── workflows/ci.yml
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── requirements.txt        # Used by the Docker image

# Created at runtime (gitignored): resources/, sessions/, media/, logs/
```

## Architecture

- **Live mode:** Telethon event handlers receive new messages → the send
  queue → paced forwarding, with Telegram flood waits waited out and retried.
- **History mode:** messages are fetched oldest-first in chunks, filtered by
  date, media and keyword, grouped into albums, and queued for sending.
  Progress is saved only after queued sends have completed, and files are
  written atomically, so an interrupted run resumes without gaps or
  duplicates.
- **Replies:** `history.json` maps source messages to their forwarded copies.
  When a reply is sent, its parent's copy is looked up so it's forwarded as a
  reply.
- **Configuration:** source → destination pairs are stored by the
  `ForwardConfig` model and shared by the CLI and the web dashboard.
