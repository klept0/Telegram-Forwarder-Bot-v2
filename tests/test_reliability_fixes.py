import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from source.model.ForwardConfig import ForwardConfig
from source.service.Forward import Forward
from source.service.ForwardProgress import ForwardProgress
from source.service.MessageQueue import MessageQueue
from source.service.MessageService import MessageService
from source.utils.FileUtils import write_json_atomic


def _message(message_id: int, day: int):
    message = MagicMock()
    message.id = message_id
    message.date = datetime(2026, 3, day, 12, 0, tzinfo=timezone.utc)
    message.chat_id = -100111
    message.is_reply = False
    message.media = None
    message.text = ""
    return message


@pytest.mark.asyncio
async def test_history_progress_only_covers_messages_actually_sent(
    tmp_path, monkeypatch
):
    """Regression test: progress used to be saved as soon as a message was
    *enqueued*, so an interrupted run resumed past messages still waiting in
    the queue and they were never forwarded."""
    monkeypatch.setattr(
        "source.service.ForwardProgress.FORWARD_PROGRESS_FILE_PATH",
        str(tmp_path / "forward_progress.json"),
    )
    monkeypatch.setattr(
        "source.model.History.HISTORY_FILE_PATH", str(tmp_path / "history.json")
    )
    monkeypatch.setattr("source.service.Forward.DEFAULT_BATCH_SIZE", 2)

    sent_ids: list[int] = []

    async def slow_forward(_destination, message):
        await asyncio.sleep(0.01)
        sent_ids.append(message.id)
        return MagicMock(id=9000 + message.id, chat_id=-100222)

    client = AsyncMock()
    client.forward_messages = AsyncMock(side_effect=slow_forward)
    history = [_message(i, i) for i in range(1, 6)]

    async def get_messages(_source, min_id=0, **_kwargs):
        return [m for m in history if m.id > min_id]

    client.get_messages = AsyncMock(side_effect=get_messages)

    saves: list[tuple[int, list[int]]] = []
    real_save = ForwardProgress.save

    def recording_save(source, last_message_id, *args, **kwargs):
        saves.append((last_message_id, list(sent_ids)))
        return real_save(source, last_message_id, *args, **kwargs)

    monkeypatch.setattr(ForwardProgress, "save", staticmethod(recording_save))

    queue = MessageQueue(max_concurrent=1, delay=0)
    config = MagicMock(destinationID=-100222)
    forward = Forward(client, {-100111: config}, queue)
    try:
        await forward._forward_chat_history(-100111, 0)
    finally:
        await queue.stop()

    assert saves, "progress should have been saved"
    for last_saved_id, sent_at_save_time in saves:
        assert all(i in sent_at_save_time for i in range(1, last_saved_id + 1))
    assert saves[-1] == (5, [1, 2, 3, 4, 5])


@pytest.mark.asyncio
async def test_keyword_forward_waits_for_queue_before_marking_progress(
    tmp_path, monkeypatch
):
    progress_file = tmp_path / "forward_progress.json"
    monkeypatch.setattr(
        "source.service.ForwardProgress.FORWARD_PROGRESS_FILE_PATH",
        str(progress_file),
    )
    sent_ids: list[int] = []

    class Client:
        async def iter_messages(self, _source, search=None, limit=None, min_id=0):
            for message in (_message(2, 10), _message(1, 5)):
                if message.id > min_id:
                    yield message

        async def forward_messages(self, _destination, message):
            await asyncio.sleep(0.01)
            sent_ids.append(message.id)

    queue = MessageQueue(max_concurrent=1, delay=0)
    service = MessageService(Client(), MagicMock(), queue=queue)
    try:
        await service.forward_messages_by_keyword(
            source_id=-100111,
            destination_id=-100222,
            start_date="2026-03-01",
            end_date="2026-03-31",
        )
        # By the time progress is marked complete, both sends have happened.
        assert sent_ids == [1, 2]
    finally:
        await queue.stop()

    saved = json.loads(progress_file.read_text())
    entry = saved["-100111|2026-03-01|2026-03-31"]
    assert entry["last_message_id"] == 2
    assert entry["status"] == "completed"


def test_write_json_atomic_keeps_old_file_when_serialization_fails(tmp_path):
    """A failed write must leave the previous contents intact (and no temp
    file behind), instead of a truncated file that loads as empty progress."""
    path = tmp_path / "forward_progress.json"
    write_json_atomic(str(path), {"a": 1})

    with pytest.raises(TypeError):
        write_json_atomic(str(path), {"bad": object()})

    assert json.loads(path.read_text()) == {"a": 1}
    assert [p.name for p in tmp_path.iterdir()] == ["forward_progress.json"]


@pytest.mark.asyncio
async def test_delete_messages_filters_to_own_messages_and_batches():
    """Regression test: comparing `message.from_id` (a Peer object) to an int
    never matched, so "Delete My Messages" deleted nothing."""
    own_ids = list(range(1, 251))
    client = MagicMock()
    seen_kwargs = {}

    async def iter_messages(_chat_id, **kwargs):
        seen_kwargs.update(kwargs)
        for message_id in own_ids:
            yield MagicMock(id=message_id)

    client.iter_messages = iter_messages
    client.delete_messages = AsyncMock()
    service = MessageService(client, MagicMock())

    await service.delete_messages_from_dialog(MagicMock(id=-100111))

    assert seen_kwargs == {"from_user": "me"}
    batches = [call.args for call in client.delete_messages.await_args_list]
    assert [chat for chat, _ in batches] == [-100111] * 3
    assert [len(ids) for _, ids in batches] == [100, 100, 50]
    assert [i for _, ids in batches for i in ids] == own_ids


def test_forward_config_enabled_flag_survives_round_trip(tmp_path, monkeypatch):
    """Regression test: `enabled` was swallowed by **kwargs on read, so the
    web dashboard's toggle never persisted."""
    monkeypatch.setattr(
        "source.model.ForwardConfig.FORWARD_CONFIG_FILE_PATH",
        str(tmp_path / "forwardConfig.json"),
    )
    config = ForwardConfig(sourceID=1, destinationID=2)
    config.enabled = False
    ForwardConfig.write([config])

    (loaded,) = ForwardConfig.read()
    assert loaded.enabled is False
    assert ForwardConfig(sourceID=1).enabled is True


@pytest.mark.asyncio
async def test_forward_dialog_skips_disabled_configs(monkeypatch):
    from source.dialog.ForwardDialog import ForwardDialog

    enabled = ForwardConfig(sourceID=1, destinationID=2)
    disabled = ForwardConfig(sourceID=3, destinationID=4, enabled=False)
    monkeypatch.setattr(
        ForwardConfig, "get_all", AsyncMock(return_value=[enabled, disabled])
    )
    dialog = ForwardDialog()
    dialog.clear = MagicMock()
    dialog.show_options = AsyncMock(side_effect=["1", "none"])

    config_map = await dialog.get_config()

    assert list(config_map) == [1]


@pytest.mark.asyncio
async def test_scan_stop_at_destination_does_not_pick_last_chat(tmp_path, monkeypatch):
    """Regression test: choosing "Stop" (-1) at the destination prompt used
    to index chats[-1] and silently save the last chat as the destination."""
    monkeypatch.setattr(
        "source.model.ForwardConfig.FORWARD_CONFIG_FILE_PATH",
        str(tmp_path / "forwardConfig.json"),
    )
    chats = [MagicMock(id=10, title="A"), MagicMock(id=20, title="B")]
    monkeypatch.setattr("source.model.Chat.Chat.read", lambda self=None: chats)
    monkeypatch.setattr(
        "source.dialog.BaseDialog.BaseDialog.list_chats_terminal",
        AsyncMock(side_effect=[0, -1]),
    )

    configs = await ForwardConfig.scan()

    assert configs == []
    assert json.loads((tmp_path / "forwardConfig.json").read_text()) == []


def _flood_wait(seconds: int):
    from telethon.errors import FloodWaitError

    return FloodWaitError(request=None, capture=seconds)


@pytest.fixture
def recorded_sleeps(monkeypatch):
    """Make the queue's sleeps instant, recording how long each would be."""
    sleeps: list[float] = []
    real_sleep = asyncio.sleep

    async def fake_sleep(seconds):
        sleeps.append(seconds)
        await real_sleep(0)

    monkeypatch.setattr("source.service.MessageQueue.asyncio.sleep", fake_sleep)
    return sleeps


@pytest.mark.asyncio
async def test_queue_waits_out_flood_wait_and_retries(recorded_sleeps):
    """Regression test: a FloodWaitError longer than Telethon's auto-sleep
    threshold used to be logged and the message silently dropped."""
    calls = []

    async def send(*_args):
        calls.append("attempt")
        if len(calls) == 1:
            raise _flood_wait(120)
        return "sent"

    queue = MessageQueue(max_concurrent=1, delay=0)
    await queue.put((send, ("dest", MagicMock(id=1))))
    await asyncio.wait_for(queue.join(), timeout=1)
    await queue.stop()

    assert calls == ["attempt", "attempt"]
    assert 121 in recorded_sleeps


@pytest.mark.asyncio
async def test_queue_gives_up_after_max_flood_retries_and_keeps_going(
    recorded_sleeps, monkeypatch
):
    monkeypatch.setattr("source.service.MessageQueue.MAX_FLOOD_WAIT_RETRIES", 2)
    attempts = []
    done = []

    async def always_flooded(*_args):
        attempts.append(1)
        raise _flood_wait(5)

    async def next_task(*_args):
        done.append(True)

    queue = MessageQueue(max_concurrent=1, delay=0)
    await queue.put((always_flooded, ("dest", MagicMock(id=1))))
    await queue.put((next_task, ("dest", MagicMock(id=2))))
    await asyncio.wait_for(queue.join(), timeout=1)
    await queue.stop()

    assert len(attempts) == 3  # first try + 2 retries
    assert done == [True]


@pytest.mark.asyncio
async def test_delete_lets_flood_wait_reach_the_queue(recorded_sleeps):
    client = MagicMock()
    client.delete_messages = AsyncMock(side_effect=[_flood_wait(90), None])

    async def iter_messages(_chat_id, **_kwargs):
        yield MagicMock(id=1)

    client.iter_messages = iter_messages
    queue = MessageQueue(max_concurrent=1, delay=0)
    service = MessageService(client, MagicMock(), queue=queue)

    await service.delete_messages_from_dialog(MagicMock(id=-100111))
    await asyncio.wait_for(queue.join(), timeout=1)
    await queue.stop()

    assert client.delete_messages.await_count == 2
    assert 91 in recorded_sleeps
