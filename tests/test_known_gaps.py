"""Regression tests for the gaps listed in the runbook: reply threading,
albums in history forwarding, live start/stop, and Find User output."""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from telethon.tl.functions.messages import ForwardMessagesRequest

from source.service.Forward import Forward
from source.service.MessageForwardService import MessageForwardService
from source.service.MessageQueue import MessageQueue

SOURCE, DEST = -100111, -100222


def _message(message_id, grouped_id=None, reply_to_msg_id=None):
    message = MagicMock()
    message.id = message_id
    message.chat_id = SOURCE
    message.peer_id = f"peer:{SOURCE}"
    message.date = datetime(2026, 3, 10, tzinfo=timezone.utc)
    message.media = MagicMock() if grouped_id else None
    message.text = ""
    message.grouped_id = grouped_id
    message.is_reply = reply_to_msg_id is not None
    message.reply_to_msg_id = reply_to_msg_id
    return message


class _Client:
    """Fake Telethon client. Plain forwards go through forward_messages;
    replies are sent by awaiting the client with a raw ForwardMessagesRequest
    (recorded in `requests`). Destination copies get ID 9000 + source ID."""

    def __init__(self):
        self.requests = []
        self.forward_messages = AsyncMock(side_effect=self._forward)
        self.get_input_entity = AsyncMock(side_effect=lambda peer: f"input:{peer}")

    @staticmethod
    async def _forward(_dest, msgs):
        if isinstance(msgs, list):
            return [MagicMock(id=9000 + m.id, chat_id=DEST) for m in msgs]
        return MagicMock(id=9000 + msgs.id, chat_id=DEST)

    async def __call__(self, request):
        self.requests.append(request)
        return request

    @staticmethod
    def _get_response_message(request, _result, _peer):
        return [MagicMock(id=9000 + i, chat_id=DEST) for i in request.id]


@pytest.mark.asyncio
async def test_reply_forwarded_with_reply_to_parent_in_destination(
    tmp_path, monkeypatch
):
    """A reply whose parent was forwarded earlier is forwarded as a reply to
    the parent's copy, keeping the "Forwarded from" header, even when the
    parent was still queued when the reply was enqueued."""
    monkeypatch.setattr(
        "source.model.History.HISTORY_FILE_PATH", str(tmp_path / "history.json")
    )
    client = _Client()
    queue = MessageQueue(max_concurrent=1, delay=0)
    forward = Forward(client, {SOURCE: MagicMock(destinationID=DEST)}, queue)

    # Both enqueued back to back, before the queue sends the parent.
    await forward._forward_message(DEST, _message(1))
    await forward._forward_message(DEST, _message(2, reply_to_msg_id=1))
    await asyncio.wait_for(queue.join(), timeout=1)
    await queue.stop()

    client.forward_messages.assert_awaited_once()  # the parent, as a plain forward
    (request,) = client.requests
    assert isinstance(request, ForwardMessagesRequest)
    assert request.id == [2]
    assert request.reply_to.reply_to_msg_id == 9001  # the parent's copy
    assert request.to_peer == f"input:{DEST}"
    assert forward.history.get_mapping(SOURCE, 2, DEST) == 9002


@pytest.mark.asyncio
async def test_reply_to_unforwarded_parent_is_a_plain_forward(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "source.model.History.HISTORY_FILE_PATH", str(tmp_path / "history.json")
    )
    client = _Client()
    forward = Forward(client, {SOURCE: MagicMock(destinationID=DEST)}, None)

    await forward._forward_message(DEST, _message(5, reply_to_msg_id=4))

    client.forward_messages.assert_awaited_once()
    assert client.requests == []


@pytest.mark.asyncio
async def test_album_reply_uses_first_reply_in_album():
    resolver = AsyncMock(side_effect=[None, 777])
    client = _Client()
    service = MessageForwardService(client, reply_resolver=resolver)

    await service.forward_album(DEST, [_message(1, 5), _message(2, 5)])

    (request,) = client.requests
    assert request.id == [1, 2]
    assert request.reply_to.reply_to_msg_id == 777


@pytest.mark.asyncio
async def test_history_forwards_albums_as_one_unit_across_chunks(monkeypatch):
    """Regression test: history/media forwarding sent album items one by one,
    splitting albums. Consecutive items sharing a grouped_id now go together,
    even when the album straddles a fetch-chunk boundary."""
    monkeypatch.setattr("source.service.Forward.DEFAULT_CHUNK_SIZE", 3)
    history = [
        _message(1),
        _message(2, grouped_id=50),
        _message(3, grouped_id=50),
        _message(4, grouped_id=50),  # next chunk, same album
        _message(5, grouped_id=60),
        _message(6),
    ]

    async def get_messages(_source, min_id=0, limit=3, **_kwargs):
        return [m for m in history if m.id > min_id][:limit]

    client = MagicMock()
    client.get_messages = AsyncMock(side_effect=get_messages)
    forward = Forward(client, {SOURCE: MagicMock(destinationID=DEST)}, None)
    forward._get_total_message_count = AsyncMock(return_value=6)
    forward._save_progress = AsyncMock()
    sent = []
    forward._forward_message = AsyncMock(
        side_effect=lambda _dest, m: sent.append([m.id])
    )
    forward._forward_album = AsyncMock(
        side_effect=lambda _dest, ms: sent.append([m.id for m in ms])
    )

    await forward._forward_chat_history(SOURCE, 0)

    assert sent == [[1], [2, 3, 4], [5], [6]]
    assert forward._save_progress.await_args.args[1] == 6


@pytest.mark.asyncio
async def test_live_forwarding_can_be_started_and_stopped():
    from source.core.Telegram import Telegram

    telegram = Telegram.__new__(Telegram)
    telegram.client = MagicMock()
    telegram.queue = None
    telegram.status = "Idle"
    telegram._live_forward = None
    config = {SOURCE: MagicMock(destinationID=DEST)}

    assert telegram.start_live_forwarding(config) is True
    assert telegram.start_live_forwarding(config) is False  # already running
    assert telegram.status == "Live forwarding"
    handlers = [c.args[0] for c in telegram.client.add_event_handler.call_args_list]

    assert telegram.stop_live_forwarding() is True
    assert telegram.stop_live_forwarding() is False  # not running
    removed = [c.args[0] for c in telegram.client.remove_event_handler.call_args_list]
    assert removed == handlers
    assert telegram.status == "Idle"


@pytest.mark.asyncio
async def test_web_start_stop_forwarding_uses_enabled_configs(tmp_path, monkeypatch):
    import web.app as web_app
    from source.model.ForwardConfig import ForwardConfig

    monkeypatch.chdir(tmp_path)
    (tmp_path / "resources").mkdir()
    monkeypatch.setattr(
        "source.model.ForwardConfig.FORWARD_CONFIG_FILE_PATH",
        "resources/forwardConfig.json",
    )
    ForwardConfig.write(
        [
            ForwardConfig(sourceID=1, destinationID=2),
            ForwardConfig(sourceID=3, destinationID=4, enabled=False),
        ]
    )
    client = MagicMock()
    client.start_live_forwarding = MagicMock(side_effect=[True, False])
    client.stop_live_forwarding = MagicMock(side_effect=[True, False])
    monkeypatch.setattr(web_app, "telegram_client", client)

    started = await web_app.start_forwarding()
    assert started["message"] == "Live forwarding started for 1 configuration(s)"
    (config_map,) = client.start_live_forwarding.call_args.args
    assert list(config_map) == [1]

    with pytest.raises(HTTPException) as already:
        await web_app.start_forwarding()
    assert already.value.status_code == 409

    assert (await web_app.stop_forwarding())["message"] == "Live forwarding stopped"
    with pytest.raises(HTTPException) as not_running:
        await web_app.stop_forwarding()
    assert not_running.value.status_code == 409


@pytest.mark.asyncio
async def test_web_start_forwarding_with_nothing_enabled_is_400(tmp_path, monkeypatch):
    import web.app as web_app

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(web_app, "telegram_client", MagicMock())

    with pytest.raises(HTTPException) as error:
        await web_app.start_forwarding()
    assert error.value.status_code == 400


@pytest.mark.asyncio
async def test_find_user_prints_each_message_and_total():
    """Regression test: Find User used to discard what it found."""
    from source.core.Telegram import Telegram

    wanted = MagicMock(id=42, title="Alice")
    group = MagicMock(id=-100555)
    me = MagicMock(id=1)
    their_message = MagicMock(sender_id=42)
    other_message = MagicMock(sender_id=7)

    async def iter_dialogs():
        yield MagicMock(entity=group)

    async def iter_messages(_chat_id, limit=None):
        for message in (their_message, other_message):
            yield message

    telegram = Telegram.__new__(Telegram)
    telegram.client = MagicMock(
        get_me=AsyncMock(return_value=me),
        iter_dialogs=iter_dialogs,
        iter_messages=iter_messages,
    )
    telegram.console = MagicMock()
    telegram.chat_service = MagicMock()
    from source.service.MessageService import MessageService

    telegram.message_service = MessageService(telegram.client, telegram.console)

    found = await telegram.find_user((wanted, 10))

    assert found == 1
    telegram.chat_service.print_chat_info.assert_called_once_with(group, their_message)
    assert "Found 1 message(s) from Alice" in str(telegram.console.print.call_args)
