class MessageService:
    def __init__(self, client, console, queue=None):
        self.client = client
        self.console = console
        self.queue = queue

    async def delete_messages_from_dialog(self, dialog, my_id):
        async for message in self.client.iter_messages(dialog.id):
            if message.from_id == my_id:
                if self.queue:
                    await self.queue.put((self._delete_message, (message,)))
                else:
                    await self._delete_message(message)

    async def _delete_message(self, message):
        try:
            await self.client.delete_messages(message.chat_id, message.id)
        except Exception as e:
            self.console.print(f"[bold red]Error deleting message:[/bold red] {e}")

    async def process_user_messages(self, chat, user, limit=None):
        async for message in self.client.iter_messages(chat.id, limit=limit):
            if message.sender_id == user.id:
                if self.queue:
                    await self.queue.put((self._process_message, (message,)))
                else:
                    await self._process_message(message)

    async def _process_message(self, message):
        pass  # implement any processing/download logic
