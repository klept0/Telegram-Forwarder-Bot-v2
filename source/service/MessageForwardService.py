class MessageForwardService:
    def __init__(self, client, queue=None):
        self.client = client
        self.queue = queue

    async def forward_message(self, destination_id, message, reply_to=None):
        if self.queue:
            await self.queue.put(
                (self._send_message, (destination_id, message, reply_to))
            )
            return message
        return await self._send_message(destination_id, message, reply_to)

    async def forward_album(self, destination_id, messages, text=None, reply_to=None):
        if self.queue:
            await self.queue.put(
                (self._send_album, (destination_id, messages, text, reply_to))
            )
            return messages
        return await self._send_album(destination_id, messages, text, reply_to)

    async def _send_message(self, destination_id, message, reply_to=None):
        # Telethon forward_messages does not support reply_to across versions.
        _ = reply_to
        return await self.client.forward_messages(destination_id, message)

    async def _send_album(self, destination_id, messages, _text=None, reply_to=None):
        _ = reply_to
        return await self.client.forward_messages(destination_id, messages)
