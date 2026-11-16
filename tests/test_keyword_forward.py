from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from source.service.MessageService import MessageService


class _IterMessagesClient:
    def __init__(self, messages):
        self._messages = messages
        self.forward_messages = AsyncMock()

    async def iter_messages(
        self, source_id, search=None, limit=None, min_id=0, reverse=False
    ):
        # Telethon yields newest first unless reverse=True.
        ordered = sorted(self._messages, key=lambda m: m.id, reverse=not reverse)
        ordered = [m for m in ordered if m.id > min_id]
        for message in ordered[:limit]:
            yield message

    async def get_messages(self, source_id, limit=1, offset_date=None, reverse=False):
        ordered = sorted(self._messages, key=lambda m: m.id)
        return [m for m in ordered if m.date >= offset_date][:limit]


def _make_message(message_id, message_date):
    message = MagicMock()
    message.id = message_id
    message.date = message_date
    return message


@pytest.mark.asyncio
async def test_keyword_forward_dry_run_does_not_send_messages(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "source.service.ForwardProgress.FORWARD_PROGRESS_FILE_PATH",
        str(tmp_path / "forward_progress.json"),
    )
    messages = [
        _make_message(5, datetime(2026, 3, 15, tzinfo=timezone.utc)),
        _make_message(4, datetime(2026, 3, 12, tzinfo=timezone.utc)),
    ]
    client = _IterMessagesClient(messages)
    console = MagicMock()
    service = MessageService(client, console)

    sent_count = await service.forward_messages_by_keyword(
        source_id=-100111,
        destination_id=-100222,
        keyword="elden",
        limit=100,
        start_date="2026-03-01",
        end_date="2026-03-31",
        timezone_name="UTC",
        dry_run=True,
    )

    # Dry-run reports how many messages still need forwarding, not zero.
    assert sent_count == 2
    client.forward_messages.assert_not_awaited()


@pytest.mark.asyncio
async def test_keyword_forward_sends_only_in_date_range(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "source.service.ForwardProgress.FORWARD_PROGRESS_FILE_PATH",
        str(tmp_path / "forward_progress.json"),
    )
    messages = [
        _make_message(10, datetime(2026, 4, 1, tzinfo=timezone.utc)),
        _make_message(9, datetime(2026, 3, 20, tzinfo=timezone.utc)),
        _make_message(8, datetime(2026, 3, 5, tzinfo=timezone.utc)),
        _make_message(7, datetime(2026, 2, 28, tzinfo=timezone.utc)),
    ]
    client = _IterMessagesClient(messages)
    console = MagicMock()
    service = MessageService(client, console)

    sent_count = await service.forward_messages_by_keyword(
        source_id=-100111,
        destination_id=-100222,
        keyword="guts",
        limit=100,
        start_date="2026-03-01",
        end_date="2026-03-31",
        timezone_name="UTC",
        dry_run=False,
    )

    assert sent_count == 2
    forwarded_ids = [
        call.args[1].id for call in client.forward_messages.await_args_list
    ]
    assert forwarded_ids == [8, 9]


@pytest.mark.asyncio
async def test_keyword_forward_keyword_is_optional(tmp_path, monkeypatch):
    """Regression test: keyword must not be required — omitting it should
    forward every message in range instead of raising."""
    monkeypatch.setattr(
        "source.service.ForwardProgress.FORWARD_PROGRESS_FILE_PATH",
        str(tmp_path / "forward_progress.json"),
    )
    messages = [
        _make_message(2, datetime(2026, 3, 10, tzinfo=timezone.utc)),
        _make_message(1, datetime(2026, 3, 5, tzinfo=timezone.utc)),
    ]
    client = _IterMessagesClient(messages)
    console = MagicMock()
    service = MessageService(client, console)

    sent_count = await service.forward_messages_by_keyword(
        source_id=-100111,
        destination_id=-100222,
        start_date="2026-03-01",
        end_date="2026-03-31",
        timezone_name="UTC",
        dry_run=False,
    )

    assert sent_count == 2
    forwarded_ids = [
        call.args[1].id for call in client.forward_messages.await_args_list
    ]
    assert forwarded_ids == [1, 2]


@pytest.mark.asyncio
async def test_keyword_forward_resumes_and_skips_already_forwarded(
    tmp_path, monkeypatch
):
    """Re-running the exact same source/date-range/keyword combination must
    skip messages already forwarded instead of sending duplicates."""
    monkeypatch.setattr(
        "source.service.ForwardProgress.FORWARD_PROGRESS_FILE_PATH",
        str(tmp_path / "forward_progress.json"),
    )
    messages = [
        _make_message(8, datetime(2026, 3, 5, tzinfo=timezone.utc)),
        _make_message(9, datetime(2026, 3, 20, tzinfo=timezone.utc)),
    ]
    client = _IterMessagesClient(messages)
    console = MagicMock()
    service = MessageService(client, console)

    kwargs = dict(
        source_id=-100111,
        destination_id=-100222,
        keyword="guts",
        start_date="2026-03-01",
        end_date="2026-03-31",
        timezone_name="UTC",
        dry_run=False,
    )

    first_count = await service.forward_messages_by_keyword(**kwargs)
    assert first_count == 2

    client.forward_messages.reset_mock()
    second_count = await service.forward_messages_by_keyword(**kwargs)

    assert second_count == 0
    client.forward_messages.assert_not_awaited()


@pytest.mark.asyncio
async def test_keyword_forward_limit_resumes_without_skipping(tmp_path, monkeypatch):
    """Regression test: with more matches than `limit`, the run used to take
    the newest ones and save the highest ID, so the older matches were
    skipped by every later run."""
    monkeypatch.setattr(
        "source.service.ForwardProgress.FORWARD_PROGRESS_FILE_PATH",
        str(tmp_path / "forward_progress.json"),
    )
    messages = [
        _make_message(i, datetime(2026, 3, i, tzinfo=timezone.utc)) for i in range(1, 6)
    ]
    messages.append(_make_message(6, datetime(2026, 4, 2, tzinfo=timezone.utc)))
    client = _IterMessagesClient(messages)
    service = MessageService(client, MagicMock())
    kwargs = dict(
        source_id=-100111,
        destination_id=-100222,
        limit=2,
        start_date="2026-03-01",
        end_date="2026-03-31",
    )

    counts = [await service.forward_messages_by_keyword(**kwargs) for _ in range(4)]

    assert counts == [2, 2, 1, 0]
    forwarded_ids = [
        call.args[1].id for call in client.forward_messages.await_args_list
    ]
    assert forwarded_ids == [1, 2, 3, 4, 5]
