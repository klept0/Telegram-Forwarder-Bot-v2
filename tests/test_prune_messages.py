from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from source.core.Telegram import Telegram
from source.service.MessageService import MessageService


class _PruneClient:
    def __init__(self, messages):
        self._messages = messages
        self.delete_messages = AsyncMock()

    async def iter_messages(self, chat_id, offset_date=None):
        # Telethon yields newest first; offset_date means "older than this".
        ordered = sorted(self._messages, key=lambda m: m.date, reverse=True)
        for message in ordered:
            if offset_date is None or message.date < offset_date:
                yield message


def _make_message(message_id, message_date, photo=None, document=None):
    message = MagicMock()
    message.id = message_id
    message.date = message_date
    message.photo = photo
    message.document = document
    return message


def test_build_prune_cutoff_from_days():
    now = datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc)

    cutoff = MessageService.build_prune_cutoff(days=30, now=now)

    assert cutoff == now - timedelta(days=30)


def test_build_prune_cutoff_from_before_date_utc():
    cutoff = MessageService.build_prune_cutoff(
        before_date="2026-03-01", timezone_name="UTC"
    )

    assert cutoff == datetime(2026, 3, 1, tzinfo=timezone.utc)


def test_build_prune_cutoff_requires_days_or_date():
    with pytest.raises(ValueError):
        MessageService.build_prune_cutoff()


@pytest.mark.asyncio
async def test_collect_old_message_ids_returns_only_older_messages():
    cutoff = datetime(2026, 3, 1, tzinfo=timezone.utc)
    messages = [
        _make_message(1, datetime(2026, 2, 1, tzinfo=timezone.utc)),
        _make_message(2, datetime(2026, 2, 20, tzinfo=timezone.utc)),
        _make_message(3, datetime(2026, 3, 5, tzinfo=timezone.utc)),
    ]
    service = MessageService(_PruneClient(messages), MagicMock())

    ids = await service.collect_old_message_ids(-100111, cutoff)

    assert ids == [2, 1]


@pytest.mark.asyncio
async def test_collect_old_message_ids_media_only_keeps_photos_and_documents():
    cutoff = datetime(2026, 3, 1, tzinfo=timezone.utc)
    old = datetime(2026, 2, 1, tzinfo=timezone.utc)
    messages = [
        _make_message(1, old, photo=None, document=None),  # text only
        _make_message(
            2, datetime(2026, 2, 1, 1, tzinfo=timezone.utc), photo=MagicMock()
        ),
        _make_message(
            3, datetime(2026, 2, 1, 2, tzinfo=timezone.utc), document=MagicMock()
        ),
        _make_message(4, datetime(2026, 3, 5, tzinfo=timezone.utc), photo=MagicMock()),
    ]
    service = MessageService(_PruneClient(messages), MagicMock())

    ids = await service.collect_old_message_ids(-100111, cutoff, media_only=True)

    assert ids == [3, 2]


@pytest.mark.asyncio
async def test_delete_message_ids_batches_by_delete_batch_size():
    client = _PruneClient([])
    service = MessageService(client, MagicMock())
    ids = list(range(1, 251))

    await service.delete_message_ids(-100111, ids)

    assert client.delete_messages.await_count == 3
    batch_sizes = [len(c.args[1]) for c in client.delete_messages.await_args_list]
    assert batch_sizes == [100, 100, 50]


def _make_telegram(messages):
    telegram = Telegram.__new__(Telegram)
    telegram.console = MagicMock()
    client = _PruneClient(messages)
    telegram.message_service = MessageService(client, telegram.console)
    return telegram, client


def _old_messages(count):
    old = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return [_make_message(i, old) for i in range(1, count + 1)]


_PRUNE_CONFIG = {
    "chat_id": -100111,
    "chat_name": "Test chat",
    "media_only": False,
    "days": None,
    "before_date": "2026-03-01",
    "timezone_name": "UTC",
    "dry_run": False,
}


@pytest.mark.asyncio
async def test_prune_dry_run_deletes_nothing():
    telegram, client = _make_telegram(_old_messages(3))
    confirm = AsyncMock(return_value=True)

    result = await telegram.prune_messages(
        {**_PRUNE_CONFIG, "dry_run": True}, confirm=confirm
    )

    assert result["matched"] == 3
    assert result["deleted"] == 0
    client.delete_messages.assert_not_awaited()
    confirm.assert_not_awaited()


@pytest.mark.asyncio
async def test_prune_declined_confirmation_deletes_nothing():
    telegram, client = _make_telegram(_old_messages(3))
    confirm = AsyncMock(return_value=False)

    result = await telegram.prune_messages(_PRUNE_CONFIG, confirm=confirm)

    assert result["matched"] == 3
    assert result["deleted"] == 0
    confirm.assert_awaited_once_with(3)
    client.delete_messages.assert_not_awaited()


@pytest.mark.asyncio
async def test_prune_confirmed_deletes_and_returns_count():
    telegram, client = _make_telegram(_old_messages(3))
    confirm = AsyncMock(return_value=True)

    result = await telegram.prune_messages(_PRUNE_CONFIG, confirm=confirm)

    assert result["matched"] == 3
    assert result["deleted"] == 3
    client.delete_messages.assert_awaited_once()
    assert sorted(client.delete_messages.await_args.args[1]) == [1, 2, 3]


@pytest.mark.asyncio
async def test_prune_without_confirm_callable_deletes_nothing():
    telegram, client = _make_telegram(_old_messages(3))

    result = await telegram.prune_messages(_PRUNE_CONFIG, confirm=None)

    assert result["matched"] == 3
    assert result["deleted"] == 0
    client.delete_messages.assert_not_awaited()


def _web_prune_request(**overrides):
    from web.app import PruneRequest

    fields = {"chat_id": -100111, "before_date": "2026-03-01", "dry_run": False}
    fields.update(overrides)
    return PruneRequest(**fields)


@pytest.mark.asyncio
async def test_web_prune_dry_run_counts_and_deletes_nothing(monkeypatch):
    import web.app as web_app

    telegram, client = _make_telegram(_old_messages(3))
    monkeypatch.setattr(web_app, "telegram_client", telegram)

    result = await web_app.prune_messages(_web_prune_request(dry_run=True))

    assert result["matched"] == 3
    assert result["deleted"] == 0
    assert result["message"] == "3 messages would be deleted."
    client.delete_messages.assert_not_awaited()


@pytest.mark.asyncio
async def test_web_prune_confirmed_run_deletes_matched_count(monkeypatch):
    import web.app as web_app

    old = datetime(2025, 1, 1, tzinfo=timezone.utc)
    photos = [_make_message(i, old, photo=MagicMock()) for i in range(1, 4)]
    telegram, client = _make_telegram(photos)
    monkeypatch.setattr(web_app, "telegram_client", telegram)

    result = await web_app.prune_messages(
        _web_prune_request(media_only=True, max_delete=3)
    )

    assert result["matched"] == 3
    assert result["deleted"] == 3
    assert result["message"] == "Deleted 3 media messages."
    client.delete_messages.assert_awaited_once()


@pytest.mark.asyncio
async def test_web_prune_more_matches_than_confirmed_is_409(monkeypatch):
    import web.app as web_app
    from fastapi import HTTPException

    telegram, client = _make_telegram(_old_messages(3))
    monkeypatch.setattr(web_app, "telegram_client", telegram)

    with pytest.raises(HTTPException) as error:
        await web_app.prune_messages(_web_prune_request(max_delete=2))

    assert error.value.status_code == 409
    client.delete_messages.assert_not_awaited()


def test_prune_request_requires_exactly_one_cutoff():
    from pydantic import ValidationError

    from web.app import PruneRequest

    with pytest.raises(ValidationError):
        PruneRequest(chat_id=1, days=30, before_date="2026-03-01")
    with pytest.raises(ValidationError):
        PruneRequest(chat_id=1)


def test_prune_request_delete_needs_max_delete_and_defaults_to_dry_run():
    from pydantic import ValidationError

    from web.app import PruneRequest

    with pytest.raises(ValidationError):
        PruneRequest(chat_id=1, days=30, dry_run=False)
    assert PruneRequest(chat_id=1, days=30).dry_run is True
