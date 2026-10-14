from telethon.tl.functions.messages import ForwardMessagesRequest
from telethon.tl.types import InputReplyToMessage


class MessageForwardService:
    def __init__(self, client, queue=None, reply_resolver=None):
        """
        Args:
            reply_resolver: Optional async callable (message, destination_id)
                -> destination message ID to reply to, or None. It runs when
                the message is actually sent rather than when it's queued, so
                a parent forwarded just before it (and possibly still queued
                at that point) is already mapped by the time it's needed.
        """
        self.client = client
        self.queue = queue
        self.reply_resolver = reply_resolver

    async def forward_message(
        self, destination_id, message, reply_to=None, on_sent=None
    ):
        if self.queue:
            await self.queue.put(
                (
                    self._send_message_and_notify,
                    (destination_id, message, reply_to, on_sent),
                )
            )
            return None
        return await self._send_message_and_notify(
            destination_id, message, reply_to, on_sent
        )

    async def forward_album(
        self, destination_id, messages, text=None, reply_to=None, on_sent=None
    ):
        if self.queue:
            await self.queue.put(
                (
                    self._send_album_and_notify,
                    (destination_id, messages, text, reply_to, on_sent),
                )
            )
            return None
        return await self._send_album_and_notify(
            destination_id, messages, text, reply_to, on_sent
        )

    async def _send_message_and_notify(
        self, destination_id, message, reply_to, on_sent
    ):
        if reply_to is None:
            reply_to = await self._resolve_reply([message], destination_id)
        sent = await self._send_message(destination_id, message, reply_to)
        if on_sent:
            on_sent(message, sent)
        return sent

    async def _send_album_and_notify(
        self, destination_id, messages, text, reply_to, on_sent
    ):
        if reply_to is None:
            reply_to = await self._resolve_reply(messages, destination_id)
        sent = await self._send_album(destination_id, messages, text, reply_to)
        if on_sent:
            on_sent(messages, sent)
        return sent

    async def _resolve_reply(self, messages, destination_id):
        if not self.reply_resolver:
            return None
        for message in messages:
            reply_to = await self.reply_resolver(message, destination_id)
            if reply_to is not None:
                return reply_to
        return None

    async def _send_message(self, destination_id, message, reply_to=None):
        if reply_to is None:
            return await self.client.forward_messages(destination_id, message)
        sent = await self._forward_as_reply(destination_id, [message], reply_to)
        return sent[0] if sent else None

    async def _send_album(self, destination_id, messages, _text=None, reply_to=None):
        if reply_to is None:
            return await self.client.forward_messages(destination_id, messages)
        return await self._forward_as_reply(destination_id, messages, reply_to)

    async def _forward_as_reply(self, destination_id, messages, reply_to):
        """Forward `messages` (keeping the "Forwarded from" header) as a reply
        to `reply_to` in the destination.

        `client.forward_messages` doesn't expose Telegram's `reply_to` option,
        so this sends the same request it builds, plus `reply_to`, and parses
        the result the same way.
        """
        to_peer = await self.client.get_input_entity(destination_id)
        request = ForwardMessagesRequest(
            from_peer=await self.client.get_input_entity(messages[0].peer_id),
            id=[message.id for message in messages],
            to_peer=to_peer,
            reply_to=InputReplyToMessage(reply_to_msg_id=reply_to),
        )
        result = await self.client(request)
        return self.client._get_response_message(request, result, to_peer)
