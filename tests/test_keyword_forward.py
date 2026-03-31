from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from source.service.MessageService import MessageService


class _IterMessagesClient:
    def __init__(self, messages):
        self._messages = messages
        self.forward_messages = AsyncMock()

    async def iter_messages(self, source_id, search=None, limit=None):
        for message in self._messages:
            yield message


def _make_message(message_id, message_date):
    message = MagicMock()
    message.id = message_id
    message.date = message_date
    return message


@pytest.mark.asyncio
async def test_keyword_forward_dry_run_does_not_send_messages():
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

    assert sent_count == 0
    client.forward_messages.assert_not_awaited()


@pytest.mark.asyncio
async def test_keyword_forward_sends_only_in_date_range():
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
