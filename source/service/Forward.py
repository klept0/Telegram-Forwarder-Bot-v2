
from datetime import datetime

from telethon import TelegramClient, events
from telethon.tl.custom import Message

from source.service.HistoryService import HistoryService
from source.service.MessageForwardService import MessageForwardService
from source.service.MessageQueue import MessageQueue
from source.utils.Console import Terminal
from source.utils.DateUtils import DateUtils

console = Terminal.console


class Forward:
    def __init__(self, client: TelegramClient, forward_config_map: dict, queue: MessageQueue):
        self.client = client
        self.forward_config_map = forward_config_map
        self.queue = queue
        self.history = HistoryService()
        self.message_forward = MessageForwardService(client, queue=self.queue)

    def add_events(self) -> None:
        source_chats = list(self.forward_config_map.keys())
        self.client.add_event_handler(self.message_handler, events.NewMessage(chats=source_chats))
        self.client.add_event_handler(self.album_handler, events.Album(chats=source_chats))

    async def message_handler(self, event: events.NewMessage.Event) -> None:
        try:
            if event.grouped_id:
                return
            destination_id = self._get_destination_id(event.chat_id)
            if not destination_id:
                return
            reply_message = await self._handle_reply(event.message, destination_id)
            await self._forward_message(destination_id, event.message, reply_message)
        except Exception as e:
            print(f"Error handling message: {e}")

    async def album_handler(self, event: events.Album.Event) -> None:
        try:
            destination_id = self._get_destination_id(event.chat_id)
            if not destination_id:
                return
            reply_message = await self._get_album_reply(event.messages, destination_id)
            await self._forward_album(destination_id, event, reply_message)
        except Exception as e:
            print(f"Error handling album: {e}")

    async def history_handler(self) -> None:
        last_message_id = 0
        for source in self.forward_config_map:
            config = self.forward_config_map[source]
            await self._forward_chat_history(
                source, last_message_id,
                config.start_date, config.end_date
            )

    async def _forward_chat_history(self, source: int, last_message_id: int,
                                    start_date: str | None = None,
                                    end_date: str | None = None) -> None:
        """Forward chat history with optional date filtering.

        Args:
            source: Source chat ID
            last_message_id: Last processed message ID
            start_date: Start date filter (YYYY-MM-DD) or None
            end_date: End date filter (YYYY-MM-DD) or None
        """
        # Prepare date filters for Telethon
        offset_date = None
        end_datetime = None

        if start_date:
            start_dt = DateUtils.parse_date(start_date)
            if start_dt:
                # Convert to datetime at start of day
                offset_date = datetime.combine(start_dt, datetime.min.time())

        if end_date:
            end_dt = DateUtils.parse_date(end_date)
            if end_dt:
                # Convert to datetime at end of day for filtering
                end_datetime = datetime.combine(end_dt, datetime.max.time())

        # Get messages with date filtering (Telethon doesn't support max_date)
        console.print("[bold blue]Retrieving messages from chat...[/bold blue]")
        messages = await self.client.get_messages(
            source,
            min_id=last_message_id,
            offset_date=offset_date,
            limit=None
        )

        # Filter messages to only include those before end_datetime
        if end_datetime:
            messages = [msg for msg in messages if msg.date <= end_datetime]

        total_messages = len(messages)
        console.print(f"[bold green]Found {total_messages} messages to forward[/bold green]")

        destination_id = self._get_destination_id(source)
        for i, message in enumerate(reversed(messages), 1):
            percentage = (i / total_messages) * 100 if total_messages > 0 else 100
            console.print(f"[bold yellow]Progress: {i}/{total_messages} ({percentage:.1f}%)[/bold yellow]", end="\r")
            
            try:
                reply_message = await self._handle_reply(message, destination_id)
                await self._forward_message(destination_id, message, reply_message)
                last_message_id = max(last_message_id, message.id)
            except Exception as e:
                print(f"Error forwarding message: {e}")

        # Clear the progress line and show completion
        console.print(f"[bold green]✓ Completed forwarding {total_messages} messages[/bold green]")

    def _get_destination_id(self, source_id: int) -> int | None:
        config = self.forward_config_map.get(source_id)
        return config.destinationID if config else None

    async def _handle_reply(self, message: Message, destination_id: int) -> int | None:
        if not message.is_reply:
            return None
        return self.history.get_mapping(message.chat_id, message.reply_to_msg_id, destination_id)

    async def _get_album_reply(self, messages: list[Message], destination_id: int) -> int | None:
        for message in messages:
            reply = await self._handle_reply(message, destination_id)
            if reply is not None:
                return reply
        return None

    async def _forward_message(self, destination_id: int, message: Message, reply_to: int | None = None) -> None:
        try:
            sent_message = await self.message_forward.forward_message(destination_id, message, reply_to)
            if sent_message:
                self._update_history(message, sent_message)
        except Exception as e:
            print(f"Error forwarding message: {e}")

    async def _forward_album(self, destination_id: int, event: events.Album.Event, reply_to: int | None = None) -> None:
        try:
            sent_messages = await self.message_forward.forward_album(destination_id, event.messages, event.text, reply_to)
            if sent_messages:
                self._update_album_history(event, sent_messages, destination_id)
        except Exception as e:
            print(f"Error forwarding album: {e}")

    def _update_history(self, source_message: Message, sent_message: Message) -> None:
        self.history.add_mapping(source_message.chat_id, source_message.id, sent_message.chat_id, sent_message.id)

    def _update_album_history(self, event: events.Album.Event, sent_messages: list[Message], destination_id: int) -> None:
        for i, message in enumerate(event.messages):
            self.history.add_mapping(event.chat_id, message.id, destination_id, sent_messages[i].id)
