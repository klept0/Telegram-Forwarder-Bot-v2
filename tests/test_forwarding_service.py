import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from source.service.Forward import Forward
from source.service.MessageForwardService import MessageForwardService
from source.service.MessageQueue import MessageQueue


def _mock_message(
    message_id: int,
    message_date: datetime,
    chat_id: int = -100111,
    media=None,
    text: str = "",
):
    message = MagicMock()
    message.id = message_id
    message.date = message_date
    message.chat_id = chat_id
    message.is_reply = False
    message.media = media
    message.text = text
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
    )
    called_methods = [call_item[0] for call_item in client.method_calls]
    assert "send_messages" not in called_methods


@pytest.mark.asyncio
async def test_forward_message_notifies_actual_sent_message_when_queued():
    """A queued send must report the real destination message to on_sent,
    not the source message that was originally passed in."""
    client = AsyncMock()
    dest_message = MagicMock(id=9001, chat_id=-100222)
    client.forward_messages.return_value = dest_message

    queue = MessageQueue(max_concurrent=1, delay=0)
    service = MessageForwardService(client, queue=queue)
    source_message = MagicMock(id=1001, chat_id=-100111)

    seen = []
    result = await service.forward_message(
        -100222, source_message, on_sent=lambda src, sent: seen.append((src, sent))
    )

    # Queued sends can't know the result yet, so they must not fake one.
    assert result is None

    await asyncio.wait_for(queue.queue.join(), timeout=1)
    await queue.stop()

    assert seen == [(source_message, dest_message)]


@pytest.mark.asyncio
async def test_forward_updates_history_with_destination_message_when_queued(
    tmp_path, monkeypatch
):
    """Regression test: Forward._forward_message must map history using the
    real destination message id, not the source message id."""
    monkeypatch.setattr(
        "source.model.History.HISTORY_FILE_PATH", str(tmp_path / "history.json")
    )

    client = AsyncMock()
    dest_message = MagicMock(id=9001, chat_id=-100222)
    client.forward_messages.return_value = dest_message

    queue = MessageQueue(max_concurrent=1, delay=0)
    config = MagicMock(destinationID=-100222)
    forward = Forward(client, {-100111: config}, queue)

    source_message = MagicMock(id=1001, chat_id=-100111, is_reply=False)
    await forward._forward_message(-100222, source_message)

    await asyncio.wait_for(queue.queue.join(), timeout=1)
    await queue.stop()

    mapping = forward.history.get_mapping(-100111, 1001, -100222)
    assert mapping == 9001


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


def test_progress_key_keeps_media_and_keyword_runs_separate():
    """A media-only or keyword-filtered run over the same date range must not
    collide with (or resume from) a plain full-history run's progress, but the
    plain-run key format must stay unchanged for backward compatibility with
    existing forward_progress.json files."""
    forward = Forward.__new__(Forward)

    plain_key = forward.progress_key(-100123, "2026-06-01", "2026-06-30")
    media_key = forward.progress_key(
        -100123, "2026-06-01", "2026-06-30", media_only=True
    )
    keyword_key = forward.progress_key(
        -100123, "2026-06-01", "2026-06-30", keyword="invoice"
    )

    assert plain_key == "-100123|2026-06-01|2026-06-30"
    assert media_key == "-100123|2026-06-01|2026-06-30|media"
    assert keyword_key == "-100123|2026-06-01|2026-06-30|kw:invoice"
    assert len({plain_key, media_key, keyword_key}) == 3


def test_matches_criteria_filters_by_media_presence():
    forward = Forward.__new__(Forward)
    dt = datetime(2026, 3, 15, 12, 0, 0, tzinfo=timezone.utc)

    file_message = MagicMock(date=dt, media=MagicMock(), text="a photo")
    text_message = MagicMock(date=dt, media=None, text="just words")

    assert forward.matches_criteria(file_message, None, None, media_only=True) is True
    assert forward.matches_criteria(text_message, None, None, media_only=True) is False
    assert forward.matches_criteria(text_message, None, None, media_only=False) is True


def test_matches_criteria_filters_by_keyword():
    forward = Forward.__new__(Forward)
    dt = datetime(2026, 3, 15, 12, 0, 0, tzinfo=timezone.utc)

    matching = MagicMock(date=dt, media=None, text="please forward the Invoice")
    other = MagicMock(date=dt, media=None, text="unrelated message")

    assert forward.matches_criteria(matching, None, None, keyword="invoice") is True
    assert forward.matches_criteria(other, None, None, keyword="invoice") is False


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
async def test_forward_chat_history_forwards_in_ascending_order_and_stops_at_end(
    monkeypatch,
):
    """Regression test: messages must be forwarded oldest-first (the order
    they were originally posted), and the scan must stop once it reaches
    messages past the configured end date rather than continuing to page."""
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

    march_ascending = [
        _mock_message(149, datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc)),
        _mock_message(150, datetime(2026, 3, 20, 12, 0, tzinfo=timezone.utc)),
    ]
    april_ascending = [
        _mock_message(199, datetime(2026, 4, 4, 12, 0, tzinfo=timezone.utc)),
        _mock_message(200, datetime(2026, 4, 5, 12, 0, tzinfo=timezone.utc)),
    ]

    async def fake_get_messages(_source, **kwargs):
        assert kwargs.get("reverse") is True
        if kwargs.get("offset_date") is not None:
            # First fetch: no resume cursor yet, jump straight to start_date.
            return march_ascending
        if kwargs.get("min_id") == 150:
            return april_ascending
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


@pytest.mark.asyncio
async def test_media_forward_dry_run_counts_only_files(monkeypatch, tmp_path):
    """Dry-run for a media-only forward must count files, not the plain text
    message mixed into the same range."""
    monkeypatch.setattr(
        "source.service.Forward.FORWARD_PROGRESS_FILE_PATH",
        str(tmp_path / "forward_progress.json"),
    )

    june_messages = [
        _mock_message(
            101, datetime(2026, 6, 2, 9, 0, tzinfo=timezone.utc), media=MagicMock()
        ),
        _mock_message(
            102, datetime(2026, 6, 10, 9, 0, tzinfo=timezone.utc), media=None
        ),
        _mock_message(
            103, datetime(2026, 6, 20, 9, 0, tzinfo=timezone.utc), media=MagicMock()
        ),
    ]

    client = AsyncMock()

    async def fake_get_messages(_source, **kwargs):
        if kwargs.get("offset_date") is not None:
            return june_messages
        return []

    client.get_messages = AsyncMock(side_effect=fake_get_messages)

    forward = Forward(client, {-100111: MagicMock()}, MagicMock())
    start_dt, end_dt = forward.build_date_bounds("2026-06-01", "2026-06-30")

    count = await forward.count_messages_in_range(
        -100111, 0, start_dt, end_dt, media_only=True
    )

    assert count == 2


@pytest.mark.asyncio
async def test_media_forward_end_to_end_forwards_in_order_and_resumes(
    monkeypatch, tmp_path
):
    """Exercises the full media-forward feature: only files are forwarded (in
    posting order), and a second run resumes from where the first left off
    instead of re-forwarding already-sent files."""
    monkeypatch.setattr(
        "source.service.Forward.FORWARD_PROGRESS_FILE_PATH",
        str(tmp_path / "forward_progress.json"),
    )

    # June 2026 chat history: two files and one plain text message, oldest first.
    june_messages = [
        _mock_message(
            101, datetime(2026, 6, 2, 9, 0, tzinfo=timezone.utc), media=MagicMock()
        ),
        _mock_message(
            102, datetime(2026, 6, 10, 9, 0, tzinfo=timezone.utc), media=None
        ),
        _mock_message(
            103, datetime(2026, 6, 20, 9, 0, tzinfo=timezone.utc), media=MagicMock()
        ),
    ]

    client = AsyncMock()

    async def fake_get_messages(_source, **kwargs):
        if kwargs.get("offset_date") is not None or kwargs.get("min_id", 0) == 0:
            return june_messages
        return []  # nothing newer than the last message we've already seen

    client.get_messages = AsyncMock(side_effect=fake_get_messages)
    client.forward_messages = AsyncMock(
        side_effect=lambda _dest, msg: MagicMock(id=msg.id * 10, chat_id=-100222)
    )

    async def idle_status_task():
        while True:
            await asyncio.sleep(60)

    config = MagicMock(
        destinationID=-100222,
        start_date="2026-06-01",
        end_date="2026-06-30",
        timezone_name="UTC",
        dry_run=False,
        media_only=True,
        keyword=None,
    )

    queue = MessageQueue(delay=0)
    forward = Forward(client, {-100111: config}, queue)
    forward._periodic_status_update = idle_status_task
    forward._get_total_message_count = AsyncMock(return_value=2)
    await forward.history_handler()
    await asyncio.wait_for(queue.queue.join(), timeout=1)
    await queue.stop()

    forwarded_ids = [
        call.args[1].id for call in client.forward_messages.await_args_list
    ]
    assert forwarded_ids == [101, 103]  # files only, oldest first, no text message

    # --- Re-running the same range must not re-forward already-sent files ---
    client.forward_messages.reset_mock()
    queue_again = MessageQueue(delay=0)
    forward_again = Forward(client, {-100111: config}, queue_again)
    forward_again._periodic_status_update = idle_status_task
    forward_again._get_total_message_count = AsyncMock(return_value=2)
    await forward_again.history_handler()
    await queue_again.stop()

    client.forward_messages.assert_not_awaited()
