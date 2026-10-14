import os
from types import SimpleNamespace

from telethon import TelegramClient

from source.model.Chat import Chat
from source.service.ChatService import ChatService
from source.service.Forward import Forward
from source.service.MessageQueue import MessageQueue
from source.service.MessageService import MessageService
from source.service.PhraseWatcher import PhraseWatcher
from source.utils.Console import Terminal
from source.utils.Constants import MEDIA_FOLDER_PATH, SESSION_PREFIX_PATH


class Telegram:
    def __init__(self, credentials):
        self.credentials = credentials
        self.client = TelegramClient(
            SESSION_PREFIX_PATH + credentials.phone_number,
            credentials.api_id,
            credentials.api_hash,
        )
        self._is_connected = False
        self.console = Terminal.console

        # Initialize services
        self.queue = MessageQueue()
        self.chat_service = ChatService(self.console)
        self.message_service = MessageService(
            self.client, self.console, queue=self.queue
        )

        self.status = "Idle"
        self._live_forward: Forward | None = None

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
        result = []
        for chat_dict in chat_list:
            chat = Chat(**chat_dict)
            self.console.print(chat.get_display_name())
            result.append(chat)
        return result

    async def delete(self, ignore_chats):
        me = await self.client.get_me()
        ignored_ids = [chat.id for chat in ignore_chats]
        async for dialog in self.client.iter_dialogs():
            if dialog.id == me.id or dialog.id in ignored_ids or not dialog.is_group:
                continue
            await self.message_service.delete_messages_from_dialog(dialog)

    async def find_user(self, config):
        """Print the wanted user's recent messages from every group/channel,
        scanning the latest `message_limit` messages of each."""
        wanted_user, message_limit = config
        if not wanted_user:
            return 0
        me = await self.client.get_me()
        found = 0
        async for dialog in self.client.iter_dialogs():
            chat = dialog.entity
            try:
                if chat.id == me.id or isinstance(chat, type(me)):
                    continue
                messages = await self.message_service.find_user_messages(
                    chat, wanted_user, message_limit
                )
                for message in messages:
                    self.chat_service.print_chat_info(chat, message)
                found += len(messages)
            except Exception as e:
                self.console.print(f"[bold red]Error processing dialog:[/bold red] {e}")
        self.console.print(
            f"[bold green]Found {found} message(s) from {wanted_user.title}[/bold green]"
        )
        return found

    def start_live_forwarding(self, forward_config) -> bool:
        """Begin forwarding new messages for `forward_config` (source ID →
        config). Returns False if live forwarding is already running."""
        if self._live_forward:
            return False
        self._live_forward = Forward(self.client, forward_config, self.queue)
        self._live_forward.add_events()
        self.status = "Live forwarding"
        return True

    def stop_live_forwarding(self) -> bool:
        """Returns False if live forwarding wasn't running."""
        if not self._live_forward:
            return False
        self._live_forward.remove_events()
        self._live_forward = None
        self.status = "Idle"
        return True

    @property
    def is_live_forwarding(self) -> bool:
        return self._live_forward is not None

    async def start_forward_live(self, forward_config):
        """CLI entry point: forward live until disconnected (Ctrl+C)."""
        self.start_live_forwarding(forward_config)
        try:
            await self.client.run_until_disconnected()
        finally:
            self.stop_live_forwarding()

    async def watch_phrase(self, config):
        """Append new messages in a chat that contain a phrase to a file,
        until disconnected (Ctrl+C)."""
        watcher = PhraseWatcher(self.client, **config)
        watcher.add_events()
        self.console.print(
            f"[bold blue]Watching {watcher.chat_title} for "
            f'"{watcher.phrase}" → {watcher.output_path} '
            "(Ctrl+C to stop)[/bold blue]"
        )
        await self.client.run_until_disconnected()

    async def past_forward(self, forward_config):
        forward = Forward(self.client, forward_config, self.queue)
        await forward.history_handler()

    async def clear_forward_progress(self) -> bool:
        forward = Forward(self.client, {}, self.queue)
        return await forward.clear_progress()

    async def forward_by_keyword(self, config):
        return await self.message_service.forward_messages_by_keyword(
            source_id=config["source_id"],
            destination_id=config["destination_id"],
            keyword=config["keyword"],
            limit=config.get("limit"),
            start_date=config.get("start_date"),
            end_date=config.get("end_date"),
            timezone_name=config.get("timezone_name", "UTC"),
            dry_run=config.get("dry_run", False),
        )

    async def forward_media_files(self, config):
        """Forward all files/images (optionally keyword-filtered) from a
        source chat's history, in the order they were originally posted.

        Resumable and dry-run-aware via the same progress-tracking
        machinery as `past_forward`, but scoped to media messages only.
        """
        forward_config_map = {
            config["source_id"]: SimpleNamespace(
                destinationID=config["destination_id"],
                start_date=config.get("start_date"),
                end_date=config.get("end_date"),
                timezone_name=config.get("timezone_name", "UTC"),
                dry_run=config.get("dry_run", False),
                media_only=True,
                keyword=config.get("keyword") or None,
            )
        }
        forward = Forward(self.client, forward_config_map, self.queue)
        await forward.history_handler()

    async def download_media(self, message):
        os.makedirs(MEDIA_FOLDER_PATH, exist_ok=True)
        return await self.client.download_media(message, file=MEDIA_FOLDER_PATH)

    def get_queue_status(self):
        return {
            "queue_length": self.queue.qsize(),
            "active_task": getattr(self.queue, "current_task", "None"),
        }
