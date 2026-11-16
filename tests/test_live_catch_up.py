"""Live Forward catch-up: messages posted while the bot was down are forwarded
on the next start, resuming after the newest message recorded in history."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from source.model.ForwardConfig import ForwardConfig
from source.service.Forward import Forward

SOURCE = -100111
DEST = -100222


def _message(message_id: int, grouped_id=None):
    message = MagicMock()
    message.id = message_id
    message.chat_id = SOURCE
    message.is_reply = False
    message.grouped_id = grouped_id
    return message


def _forward(tmp_path, monkeypatch, chat, mapped_ids):
    monkeypatch.setattr(
        "source.model.History.HISTORY_FILE_PATH", str(tmp_path / "history.json")
    )
    client = AsyncMock()

    async def get_messages(_source, limit=None, min_id=0, reverse=False, **_kw):
        if not reverse:  # newest first, as Telethon returns by default
            return sorted(chat, key=lambda m: -m.id)[:limit]
        return [m for m in chat if m.id > min_id][:limit]

    client.get_messages = AsyncMock(side_effect=get_messages)
    config = ForwardConfig(sourceID=SOURCE, destinationID=DEST)
    forward = Forward(client, {SOURCE: config}, queue=None)
    for message_id in mapped_ids:
        forward.history.add_mapping(SOURCE, message_id, DEST, 5000 + message_id)
    forward._forward_message = AsyncMock()
    forward._forward_album = AsyncMock()
    return forward


@pytest.mark.asyncio
async def test_catch_up_forwards_only_messages_after_last_mapped(tmp_path, monkeypatch):
    chat = [_message(i) for i in range(1, 7)]
    forward = _forward(tmp_path, monkeypatch, chat, mapped_ids=[1, 2, 3])

    count = await forward.catch_up()

    sent = [c.args[1].id for c in forward._forward_message.await_args_list]
    assert sent == [4, 5, 6]
    assert count == 3


@pytest.mark.asyncio
async def test_catch_up_skips_messages_already_sent_live(tmp_path, monkeypatch):
    chat = [_message(i) for i in range(1, 6)]
    forward = _forward(tmp_path, monkeypatch, chat, mapped_ids=[1, 2])
    original = forward.client.get_messages.side_effect

    async def live_send_during_catch_up(source, **kwargs):
        if kwargs.get("limit") == 1:
            # The live handler sends 5 after handlers are registered but
            # before catch-up reaches it.
            forward.history.add_mapping(SOURCE, 5, DEST, 9005)
        return await original(source, **kwargs)

    forward.client.get_messages.side_effect = live_send_during_catch_up

    await forward.catch_up()

    sent = [c.args[1].id for c in forward._forward_message.await_args_list]
    assert sent == [3, 4]


@pytest.mark.asyncio
async def test_catch_up_without_history_forwards_nothing(tmp_path, monkeypatch):
    chat = [_message(i) for i in range(1, 4)]
    forward = _forward(tmp_path, monkeypatch, chat, mapped_ids=[])

    assert await forward.catch_up() == 0
    forward._forward_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_catch_up_sends_albums_as_one_unit(tmp_path, monkeypatch):
    chat = [_message(1), _message(2, 77), _message(3, 77), _message(4)]
    forward = _forward(tmp_path, monkeypatch, chat, mapped_ids=[1])

    await forward.catch_up()

    album = forward._forward_album.await_args.args[1]
    assert [m.id for m in album] == [2, 3]
    sent = [c.args[1].id for c in forward._forward_message.await_args_list]
    assert sent == [4]


@pytest.mark.asyncio
async def test_catch_up_ignores_messages_newer_than_start(tmp_path, monkeypatch):
    chat = [_message(i) for i in range(1, 4)]
    forward = _forward(tmp_path, monkeypatch, chat, mapped_ids=[1])
    original = forward.client.get_messages.side_effect

    async def grows(source, **kwargs):
        result = await original(source, **kwargs)
        if kwargs.get("limit") == 1:
            chat.append(_message(4))  # arrives after the upper bound is read
        return result

    forward.client.get_messages.side_effect = grows

    await forward.catch_up()

    sent = [c.args[1].id for c in forward._forward_message.await_args_list]
    assert sent == [2, 3]
