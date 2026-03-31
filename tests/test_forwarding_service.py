import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from source.service.Forward import Forward
from source.service.MessageForwardService import MessageForwardService
from source.service.MessageQueue import MessageQueue


def _mock_message(message_id: int, message_date: datetime, chat_id: int = -100111):
    message = MagicMock()
    message.id = message_id
    message.date = message_date
    message.chat_id = chat_id
    message.is_reply = False
    return message


@pytest.mark.asyncio
async def test_forward_message_uses_forward_messages():
    client = AsyncMock()
    service = MessageForwardService(client)
    message = MagicMock(id=1001, chat_id=-100111)

    await service.forward_message(-100222, message, reply_to=55)

    client.forward_messages.assert_awaited_once_with(
        -100222,
        message,
        reply_to=55,
    )


@pytest.mark.asyncio
async def test_forward_album_uses_forward_messages_and_not_send_messages():
    client = AsyncMock()
    service = MessageForwardService(client)
    messages = [MagicMock(id=1), MagicMock(id=2)]

    await service.forward_album(-100222, messages, text="caption", reply_to=99)

    client.forward_messages.assert_awaited_once_with(
        -100222,
        messages,
        reply_to=99,
    )
    called_methods = [call_item[0] for call_item in client.method_calls]
    assert "send_messages" not in called_methods


@pytest.mark.asyncio
async def test_message_queue_keeps_processing_after_task_failure():
    queue = MessageQueue(max_concurrent=1, delay=0)
    events = []

    async def failing_task(*_args):
        raise RuntimeError("boom")

    async def successful_task(*_args):
        events.append("success")

    await queue.put((failing_task, ("dest", MagicMock(id=1))))
    await queue.put((successful_task, ("dest", MagicMock(id=2))))

    await asyncio.wait_for(queue.queue.join(), timeout=1)
    await queue.stop()

    assert events == ["success"]


def test_progress_key_is_date_aware():
    forward = Forward.__new__(Forward)

    key_a = forward.progress_key(-100123, "2026-03-01", "2026-03-31")
    key_b = forward.progress_key(-100123, "2026-02-01", "2026-02-28")

    assert key_a != key_b
    assert key_a == "-100123|2026-03-01|2026-03-31"


def test_in_date_range_respects_start_and_end_bounds():
    forward = Forward.__new__(Forward)
    start = datetime(2026, 3, 1, 0, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 3, 31, 23, 59, 59, tzinfo=timezone.utc)

    before = MagicMock(date=datetime(2026, 2, 28, 23, 59, 59, tzinfo=timezone.utc))
    inside = MagicMock(date=datetime(2026, 3, 15, 12, 0, 0, tzinfo=timezone.utc))
    after = MagicMock(date=datetime(2026, 4, 1, 0, 0, 0, tzinfo=timezone.utc))

    assert forward.in_date_range(before, start, end) is False
    assert forward.in_date_range(inside, start, end) is True
    assert forward.in_date_range(after, start, end) is False


def test_build_date_bounds_for_single_day():
    forward = Forward.__new__(Forward)

    start, end = forward.build_date_bounds("2026-03-31", "2026-03-31")

    assert start == datetime(2026, 3, 31, 0, 0, 0, tzinfo=timezone.utc)
    assert end == datetime(2026, 3, 31, 23, 59, 59, 999999, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_forward_chat_history_pages_until_in_range_messages(monkeypatch):
    client = AsyncMock()
    queue = MagicMock()
    config = MagicMock(
        destinationID=-100222,
        start_date="2026-03-01",
        end_date="2026-03-31",
        timezone_name="UTC",
        dry_run=False,
    )
    forward = Forward(client, {-100111: config}, queue)

    monkeypatch.setattr("source.service.Forward.DEFAULT_CHUNK_SIZE", 2)

    april = [
        _mock_message(200, datetime(2026, 4, 5, 12, 0, tzinfo=timezone.utc)),
        _mock_message(199, datetime(2026, 4, 4, 12, 0, tzinfo=timezone.utc)),
    ]
    march = [
        _mock_message(150, datetime(2026, 3, 20, 12, 0, tzinfo=timezone.utc)),
        _mock_message(149, datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc)),
    ]
    feb = [_mock_message(120, datetime(2026, 2, 10, 12, 0, tzinfo=timezone.utc))]

    async def fake_get_messages(_source, **kwargs):
        offset_id = kwargs.get("offset_id", 0)
        if offset_id == 0:
            return april
        if offset_id == 199:
            return march
        if offset_id == 149:
            return feb
        return []

    client.get_messages = AsyncMock(side_effect=fake_get_messages)

    async def idle_status_task():
        while True:
            await asyncio.sleep(60)

    forward._periodic_status_update = idle_status_task
    forward._get_total_message_count = AsyncMock(return_value=2)
    forward._handle_reply = AsyncMock(return_value=None)
    forward._save_progress = AsyncMock()
    forward._forward_message = AsyncMock()

    await forward._forward_chat_history(
        -100111,
        0,
        "2026-03-01",
        "2026-03-31",
        "UTC",
        False,
    )

    forwarded_ids = [
        call.args[1].id for call in forward._forward_message.await_args_list
    ]
    assert forwarded_ids == [149, 150]


@pytest.mark.asyncio
async def test_forward_chat_history_dry_run_does_not_forward():
    client = AsyncMock()
    queue = MagicMock()
    config = MagicMock(
        destinationID=-100222,
        start_date="2026-03-01",
        end_date="2026-03-31",
        timezone_name="UTC",
        dry_run=True,
    )
    forward = Forward(client, {-100111: config}, queue)

    forward.count_messages_in_range = AsyncMock(return_value=42)
    forward._forward_message = AsyncMock()
    forward._save_progress = AsyncMock()

    await forward._forward_chat_history(
        -100111,
        0,
        "2026-03-01",
        "2026-03-31",
        "UTC",
        True,
    )

    forward.count_messages_in_range.assert_awaited_once()
    forward._forward_message.assert_not_awaited()
    forward._save_progress.assert_not_awaited()
