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
        # Check if message has any content to send
        if not message.text and not message.media:
            # Skip empty messages that have no text and no media
            return None

        # Handle different message types
        if message.media and message.text:
            # Message has both media and text - use send_file with caption
            return await self.client.send_file(
                destination_id,
                message.media,
                caption=message.text,
                reply_to=reply_to
            )
        elif message.media:
            # Media-only message
            return await self.client.send_file(
                destination_id,
                message.media,
                reply_to=reply_to
            )
        elif message.text:
            # Text-only message
            return await self.client.send_message(
                destination_id,
                message.text,
                reply_to=reply_to
            )
        else:
            # Fallback: skip message if we can't determine content
            return None

    async def _send_album(self, destination_id, messages, text=None, reply_to=None):
        return await self.client.send_messages(destination_id, messages, reply_to=reply_to)
