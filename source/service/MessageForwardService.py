class MessageForwardService:
    def __init__(self, client, queue=None):
        self.client = client
        self.queue = queue

    async def forward_message(self, destination_id, message, reply_to=None):
        if self.queue:
            await self.queue.put((self._send_message, (destination_id, message, reply_to)))
            return message
        return await self._send_message(destination_id, message, reply_to)

    async def forward_album(self, destination_id, messages, text=None, reply_to=None):
        if self.queue:
            await self.queue.put((self._send_album, (destination_id, messages, text, reply_to)))
            return messages
        return await self._send_album(destination_id, messages, text, reply_to)

    async def _send_message(self, destination_id, message, reply_to=None):
        return await self.client.send_message(destination_id, message.text, reply_to=reply_to)

    async def _send_album(self, destination_id, messages, text=None, reply_to=None):
        return await self.client.send_messages(destination_id, messages, reply_to=reply_to)
