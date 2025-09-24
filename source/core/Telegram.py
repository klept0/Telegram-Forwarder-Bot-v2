import os

from telethon import TelegramClient

from source.model.Chat import Chat
from source.service.ChatService import ChatService
from source.service.Forward import Forward
from source.service.MessageQueue import MessageQueue
from source.service.MessageService import MessageService
from source.utils.Console import Terminal
from source.utils.Constants import MEDIA_FOLDER_PATH, SESSION_PREFIX_PATH


class Telegram:
    def __init__(self, credentials):
        self.credentials = credentials
        self.client = TelegramClient(
            SESSION_PREFIX_PATH + credentials.phone_number,
            credentials.api_id,
            credentials.api_hash
        )
        self._is_connected = False
        self.console = Terminal.console

        # Initialize services
        self.queue = MessageQueue()
        self.chat_service = ChatService(self.console)
        self.message_service = MessageService(self.client, self.console, queue=self.queue)

        self.status = "Idle"

    @classmethod
    async def create(cls, credentials):
        instance = cls(credentials)
        await instance.connect()
        return instance

    async def connect(self):
        if not self._is_connected:
            if not self.client.is_connected():
                await self.client.connect()
            if not await self.client.is_user_authorized():
                await self.client.start(self.credentials.phone_number)
            self._is_connected = True

    async def disconnect(self):
        if self._is_connected:
            await self.client.disconnect()
            self._is_connected = False

    async def list_chats(self):
        chats = await self.client.get_dialogs()
        chat_list = Chat.write(chats)
        self.console.print("\n[bold blue]Available Chats:[/]")
        for chat_dict in chat_list:
            chat = Chat(**chat_dict)
            self.console.print(chat.get_display_name())

    async def delete(self, ignore_chats):
        me = await self.client.get_me()
        ignored_ids = [chat.id for chat in ignore_chats]
        async for dialog in self.client.iter_dialogs():
            if dialog.id == me.id or dialog.id in ignored_ids or not dialog.is_group:
                continue
            await self.message_service.delete_messages_from_dialog(dialog, me.id)

    async def find_user(self, config):
        wanted_user, message_limit = config
        if not wanted_user:
            return
        me = await self.client.get_me()
        async for dialog in self.client.iter_dialogs():
            chat = dialog.entity
            try:
                if chat.id == me.id or isinstance(chat, type(me)):
                    continue
                await self.message_service.process_user_messages(chat, wanted_user, message_limit)
            except Exception as e:
                self.console.print(f"[bold red]Error processing dialog:[/bold red] {e}")

    async def start_forward_live(self, forward_config):
        forward = Forward(self.client, forward_config, self.queue)
        forward.add_events()
        await self.client.run_until_disconnected()

    async def past_forward(self, forward_config):
        forward = Forward(self.client, forward_config, self.queue)
        await forward.history_handler()

    async def download_media(self, message):
        os.makedirs(MEDIA_FOLDER_PATH, exist_ok=True)
        return await self.client.download_media(message, file=MEDIA_FOLDER_PATH)

    def get_queue_status(self):
        return {
            "queue_length": self.queue.qsize(),
            "active_task": getattr(self.queue, "current_task", "None")
        }
