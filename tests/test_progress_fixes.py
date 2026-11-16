"""Regression tests: legacy progress keys must not hijack filtered runs, and
a failed send must be retried on the next run instead of being skipped."""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from source.model import History as history_module
from source.service import ForwardProgress as progress_module
from source.service.Forward import Forward
from source.service.ForwardProgress import ForwardProgress
from source.service.MessageQueue import MessageQueue

SOURCE, DEST = -100111, -100222


def _message(message_id, grouped_id=None):
    message = MagicMock()
    message.id = message_id
    message.chat_id = SOURCE
    message.date = datetime(2026, 3, 10, tzinfo=timezone.utc)
    message.media = None
    message.text = ""
    message.grouped_id = grouped_id
    message.is_reply = False
    return message


def test_data_files_are_isolated_from_real_resources(tmp_path):
    assert history_module.HISTORY_FILE_PATH.startswith(str(tmp_path))
    assert progress_module.FORWARD_PROGRESS_FILE_PATH.startswith(str(tmp_path))


def test_legacy_progress_key_only_applies_to_unfiltered_run():
    legacy = {str(SOURCE): {"status": "completed", "last_message_id": 900}}
    with open(progress_module.FORWARD_PROGRESS_FILE_PATH, "w") as f:
        json.dump(legacy, f)

    assert ForwardProgress.load(SOURCE) == 900
    assert ForwardProgress.load(SOURCE, "2026-03-01", "2026-03-31") == 0
    assert ForwardProgress.load(SOURCE, media_only=True) == 0
    assert ForwardProgress.load(SOURCE, keyword="stl") == 0


@pytest.mark.asyncio
async def test_failed_send_is_recorded_then_retried_on_next_run():
    history = [_message(i) for i in range(1, 4)]
    fail_ids = {2}
    sent: list[int] = []

    async def forward_messages(_destination, message):
        if message.id in fail_ids:
            raise RuntimeError("connection lost")
        sent.append(message.id)
        return MagicMock(id=message.id * 10, chat_id=DEST)

    async def get_messages(_source, min_id=0, ids=None, **_kwargs):
        if ids is not None:
            return [m for m in history if m.id in ids]
        return [m for m in history if m.id > min_id]

    client = AsyncMock()
    client.forward_messages = AsyncMock(side_effect=forward_messages)
    client.get_messages = AsyncMock(side_effect=get_messages)

    queue = MessageQueue(max_concurrent=1, delay=0)
    config = MagicMock(destinationID=DEST)
    try:
        await Forward(client, {SOURCE: config}, queue)._forward_chat_history(SOURCE, 0)
        assert sent == [1, 3]
        assert ForwardProgress.load(SOURCE) == 3
        assert ForwardProgress.load_failed(SOURCE) == [2]

        # Next run: the send works now, so only message 2 goes out.
        fail_ids.clear()
        await Forward(client, {SOURCE: config}, queue)._forward_chat_history(SOURCE, 3)
        assert sent == [1, 3, 2]
        assert ForwardProgress.load_failed(SOURCE) == []
    finally:
        await queue.stop()


def test_session_lock_refuses_second_holder(tmp_path):
    from source.utils.SessionLock import SessionInUseError, SessionLock

    path = str(tmp_path / "session_+111.lock")
    first, second = SessionLock(path), SessionLock(path)
    first.acquire()
    with pytest.raises(SessionInUseError):
        second.acquire()
    first.release()
    second.acquire()  # free again once the first holder lets go
    second.release()


def test_saving_credentials_replaces_same_phone(tmp_path, monkeypatch):
    from source.model.Credentials import Credentials

    monkeypatch.setattr(Credentials, "CREDENTIALS_FILE", str(tmp_path / "c.json"))
    Credentials("1", "old", "+111").save()
    Credentials("2", "other", "+222").save()
    Credentials("1", "new", "+111").save()

    saved = {c.phone_number: c.api_hash for c in Credentials.get_all()}
    assert saved == {"+111": "new", "+222": "other"}


def test_wanted_users_is_empty_before_first_save(tmp_path, monkeypatch):
    from source.model.Chat import Chat

    monkeypatch.setattr(
        "source.model.Chat.WANTED_USER_FILE_PATH", str(tmp_path / "wantedUser.json")
    )
    assert Chat.read_wanted_users() == []


def test_history_appends_to_log_and_folds_it_on_load():
    from source.model.History import History

    first = History()
    first.add_mapping(SOURCE, 1, DEST, 10)
    first.add_mapping(SOURCE, 2, DEST, 20)
    log_path = History._log_path()
    with open(log_path, "a", encoding="utf-8") as f:
        f.write("[1, 2")  # a line cut short by a crash is ignored

    reloaded = History()
    assert reloaded.get_mapping(SOURCE, 1, DEST) == 10
    assert reloaded.get_mapping(SOURCE, 2, DEST) == 20
    # Folded into history.json, so the log is gone and a third load agrees.
    import os

    assert not os.path.exists(log_path)
    assert History().message_map == reloaded.message_map


@pytest.mark.asyncio
async def test_reply_falls_back_to_plain_forward_when_parent_is_gone():
    from telethon.errors import BadRequestError

    from source.service.MessageForwardService import MessageForwardService

    client = AsyncMock()
    client.forward_messages = AsyncMock(return_value="plain")
    service = MessageForwardService(client)
    service._forward_as_reply = AsyncMock(
        side_effect=BadRequestError(request=None, message="REPLY_MESSAGE_ID_INVALID")
    )

    message = _message(5)
    assert await service._send_message(DEST, message, reply_to=99) == "plain"
    client.forward_messages.assert_awaited_once_with(DEST, message)


def test_service_messages_are_never_forwarded():
    from telethon.tl.types import MessageActionPinMessage, MessageService, PeerChannel

    forward = Forward(AsyncMock(), {SOURCE: MagicMock(destinationID=DEST)}, None)
    pin = MessageService(
        id=7,
        peer_id=PeerChannel(1),
        date=datetime(2026, 3, 10, tzinfo=timezone.utc),
        action=MessageActionPinMessage(),
    )
    assert forward.matches_criteria(pin, None, None) is False
    assert forward.matches_criteria(_message(8), None, None) is True


@pytest.mark.asyncio
async def test_catch_up_skips_message_a_live_handler_already_queued():
    history = [_message(i) for i in range(1, 5)]
    client = AsyncMock()
    forward = Forward(client, {SOURCE: MagicMock(destinationID=DEST)}, None)
    forward.history.add_mapping(SOURCE, 1, DEST, 10)
    forward._send_history_unit = AsyncMock(return_value=0)

    async def get_messages(_source, limit=None, min_id=0, **_kwargs):
        if limit == 1:
            # A live message arrives while catch-up is working out its range.
            event = MagicMock(chat_id=SOURCE, grouped_id=None, message=history[2])
            forward._forward_message = AsyncMock()
            await forward.message_handler(event)
            return [history[-1]]
        return [m for m in history if m.id > min_id]

    client.get_messages = AsyncMock(side_effect=get_messages)

    await forward.catch_up()

    queued = [call.args[1][0].id for call in forward._send_history_unit.await_args_list]
    assert queued == [2, 4]  # 3 was taken by the live handler
    assert forward._live_seen == set() and forward._catching_up is False


@pytest.mark.asyncio
async def test_total_count_uses_real_chat_total_and_id_span():
    client = AsyncMock()
    forward = Forward(client, {SOURCE: MagicMock(destinationID=DEST)}, None)

    client.get_messages = AsyncMock(return_value=MagicMock(total=4321))
    assert await forward._get_total_message_count(SOURCE, None, None) == 4321

    client.get_messages = AsyncMock(return_value=[_message(150)])
    assert await forward._get_total_message_count(SOURCE, None, None, 100) == 50
