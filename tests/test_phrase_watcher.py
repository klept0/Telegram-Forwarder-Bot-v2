from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from telethon.tl.types import PeerChannel, PeerUser

from source.service.PhraseWatcher import PhraseWatcher


def _event(message_id, text, peer, sender_name=None):
    message = MagicMock()
    message.id = message_id
    message.message = text
    message.date = datetime(2026, 10, 13, 14, 5, 9, tzinfo=timezone.utc)
    message.peer_id = peer
    event = MagicMock(message=message)
    sender = MagicMock(first_name=sender_name, last_name=None) if sender_name else None
    event.get_sender = AsyncMock(return_value=sender)
    return event


def _watcher(tmp_path, **kwargs):
    defaults = dict(
        client=MagicMock(),
        chat_id=-1001234,
        phrase="Server Down",
        output_path=str(tmp_path / "out" / "matches.md"),
        chat_title="Ops Alerts",
    )
    return PhraseWatcher(**{**defaults, **kwargs})


@pytest.mark.asyncio
async def test_only_matching_messages_are_appended_case_insensitively(tmp_path):
    watcher = _watcher(tmp_path)
    channel = PeerChannel(channel_id=1234)

    await watcher.message_handler(_event(1, "all good here", channel))
    await watcher.message_handler(_event(2, "ALERT: server down in eu-1", channel))
    await watcher.message_handler(_event(3, None, channel))  # media, no caption
    await watcher.message_handler(_event(4, "Server down again\nsecond line", channel))

    content = (tmp_path / "out" / "matches.md").read_text(encoding="utf-8")
    assert content == (
        '# Messages containing "Server Down" in Ops Alerts\n\n'
        "## 2026-10-13 14:05:09 UTC\n\n"
        "[Open in Telegram](https://t.me/c/1234/2)\n\n"
        "> ALERT: server down in eu-1\n\n"
        "## 2026-10-13 14:05:09 UTC\n\n"
        "[Open in Telegram](https://t.me/c/1234/4)\n\n"
        "> Server down again  \n"
        "> second line\n\n"
    )


@pytest.mark.asyncio
async def test_header_written_once_across_watch_sessions(tmp_path):
    channel = PeerChannel(channel_id=1234)
    await _watcher(tmp_path).message_handler(_event(1, "server down", channel))
    await _watcher(tmp_path).message_handler(_event(2, "server down", channel))

    content = (tmp_path / "out" / "matches.md").read_text(encoding="utf-8")
    assert content.count("# Messages containing") == 1
    assert content.count("## 2026-10-13") == 2


def test_multi_line_posts_keep_one_line_per_entry_when_rendered(tmp_path):
    """Regression test: Markdown merges consecutive `>` lines into one
    paragraph, so schedule-style posts rendered as a single run-on line."""
    from markdown_it import MarkdownIt

    text = (
        "MLB 01: 8PM Cleveland Guardians vs. Tampa Bay Rays\n"
        "MLB 02: 8PM Cleveland Guardians vs. Tampa Bay Rays\n"
        "\n"
        "MLB 03: 8PM Cleveland Guardians vs. Tampa Bay Rays"
    )
    message = _event(5, text, PeerChannel(channel_id=1)).message

    entry = _watcher(tmp_path).format_entry(message, None)
    html = MarkdownIt("commonmark").render(entry)

    assert html.count("<br />") == 1  # between MLB 01 and MLB 02
    assert html.count("<p>MLB") == 2  # the blank line still splits paragraphs
    # Read as plain text, the lines are unchanged apart from the quote marker.
    plain = [line.rstrip() for line in entry.splitlines() if line.startswith(">")]
    assert plain == [
        "> MLB 01: 8PM Cleveland Guardians vs. Tampa Bay Rays",
        "> MLB 02: 8PM Cleveland Guardians vs. Tampa Bay Rays",
        ">",
        "> MLB 03: 8PM Cleveland Guardians vs. Tampa Bay Rays",
    ]


def test_group_entry_names_sender_and_public_chat_uses_username_link(tmp_path):
    watcher = _watcher(tmp_path, chat_title="Team Chat", chat_username="teamchat")
    message = _event(7, "server down?", PeerUser(user_id=42)).message

    entry = watcher.format_entry(message, "Alice")

    assert "**From:** Alice · [Open in Telegram](https://t.me/teamchat/7)" in entry


def test_channel_posts_do_not_repeat_channel_name_as_sender(tmp_path):
    watcher = _watcher(tmp_path)
    message = _event(2, "server down", PeerChannel(channel_id=1234)).message

    assert "**From:**" not in watcher.format_entry(message, "Ops Alerts")


@pytest.mark.asyncio
async def test_handler_errors_are_logged_not_raised(tmp_path):
    watcher = _watcher(tmp_path)
    event = _event(1, "server down", PeerChannel(channel_id=1))
    event.get_sender = AsyncMock(side_effect=RuntimeError("network"))

    await watcher.message_handler(event)  # must not raise

    assert not (tmp_path / "out" / "matches.md").exists()


def test_default_output_path_is_a_safe_filename():
    assert PhraseWatcher.default_output_path("Ops / Alerts!", -100) == (
        "logs/phrase_ops_alerts.md"
    )
    assert PhraseWatcher.default_output_path("🔥🔥", -100) == "logs/phrase_-100.md"


def test_add_events_listens_only_to_the_watched_chat(tmp_path):
    watcher = _watcher(tmp_path)

    watcher.add_events()

    handler, event_builder = watcher.client.add_event_handler.call_args.args
    assert handler == watcher.message_handler
    assert event_builder.chats == [-1001234]


@pytest.mark.asyncio
async def test_telegram_watch_phrase_wires_dialog_config_to_file(tmp_path):
    """End to end: the dict PhraseWatchDialog returns drives a live watch
    that writes matches to the chosen file."""
    from source.core.Telegram import Telegram

    output = tmp_path / "watch.md"
    handlers = []
    client = MagicMock()
    client.add_event_handler = lambda handler, _builder: handlers.append(handler)

    async def run_until_disconnected():
        await handlers[0](_event(9, "server down!", PeerChannel(channel_id=55)))

    client.run_until_disconnected = run_until_disconnected
    telegram = Telegram.__new__(Telegram)
    telegram.client = client
    telegram.console = MagicMock()

    await telegram.watch_phrase(
        {
            "chat_id": -10055,
            "chat_title": "Ops Alerts",
            "chat_username": None,
            "phrase": "server down",
            "output_path": str(output),
        }
    )

    assert "> server down!" in output.read_text(encoding="utf-8")
