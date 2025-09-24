
from datetime import datetime

import pytz
from telethon import TelegramClient, events
from telethon.tl.custom import Message

from source.service.HistoryService import HistoryService
from source.service.MessageForwardService import MessageForwardService
from source.service.MessageQueue import MessageQueue
from source.utils.Console import Terminal
from source.utils.Constants import (
    DEFAULT_CHUNK_SIZE,
    DEFAULT_BATCH_SIZE,
    FORWARD_PROGRESS_FILE_PATH
)
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
            console.print(f"[bold red]Error handling message:[/bold red] {e}")

    async def album_handler(self, event: events.Album.Event) -> None:
        try:
            destination_id = self._get_destination_id(event.chat_id)
            if not destination_id:
                return
            reply_message = await self._get_album_reply(event.messages, destination_id)
            await self._forward_album(destination_id, event, reply_message)
        except Exception as e:
            console.print(f"[bold red]Error handling album:[/bold red] {e}")

    async def history_handler(self) -> None:
        for source in self.forward_config_map:
            config = self.forward_config_map[source]

            # Check if there's existing progress to resume
            last_message_id = await self._load_progress(source)
            if last_message_id > 0:
                console.print(f"[bold yellow]Resuming from message {last_message_id} for chat {source}[/bold yellow]")

            await self._forward_chat_history(
                source, last_message_id,
                config.start_date, config.end_date
            )

            # Mark progress as completed
            await self._mark_progress_completed(source)

    async def _forward_chat_history(self, source: int, last_message_id: int,
                                    start_date: str | None = None,
                                    end_date: str | None = None) -> None:
        """Forward chat history with optional date filtering and chunked processing.

        Args:
            source: Source chat ID
            last_message_id: Last processed message ID
            start_date: Start date filter (YYYY-MM-DD) or None
            end_date: End date filter (YYYY-MM-DD) or None
        """
        # Configuration for chunked processing
        CHUNK_SIZE = DEFAULT_CHUNK_SIZE  # Number of messages to retrieve per chunk
        BATCH_SIZE = DEFAULT_BATCH_SIZE   # Number of messages to process before saving progress

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
                end_datetime = datetime.combine(end_dt, datetime.max.time()) \
                    .replace(tzinfo=pytz.UTC)

        console.print("[bold blue]Retrieving messages from chat...[/bold blue]")

        # Get total message count first (for progress tracking)
        total_messages = await self._get_total_message_count(source, offset_date, end_datetime)
        console.print(f"[bold green]Found approximately {total_messages} messages to forward[/bold green]")

        destination_id = self._get_destination_id(source)
        if not destination_id:
            console.print("[bold red]No destination configured for this chat[/bold red]")
            return

        # Process messages in chunks
        processed_count = 0
        chunk_offset_id = 0  # Start from the most recent message

        while True:
            # Get next chunk of messages
            messages = await self.client.get_messages(
                source,
                limit=CHUNK_SIZE,
                offset_id=chunk_offset_id,
                offset_date=offset_date,
                min_id=last_message_id
            )

            if not messages:
                break  # No more messages

            # Filter messages by end date if specified
            if end_datetime:
                messages = [msg for msg in messages if msg.date <= end_datetime]

            if not messages:
                break  # No messages in this date range

            # Process messages in batches
            for i, message in enumerate(reversed(messages), 1):
                current_total = processed_count + i
                percentage = (current_total / total_messages) * 100 if total_messages > 0 else 0

                console.print(f"[bold yellow]Progress: {current_total}/{total_messages} ({percentage:.1f}%)[/bold yellow]", end="\r")

                try:
                    reply_message = await self._handle_reply(message, destination_id)
                    await self._forward_message(destination_id, message, reply_message)
                    last_message_id = max(last_message_id, message.id)
                except Exception as e:
                    console.print(f"[bold red]Error forwarding message {message.id}: {e}[/bold red]")

                # Save progress every BATCH_SIZE messages
                if current_total % BATCH_SIZE == 0:
                    await self._save_progress(source, last_message_id)

            processed_count += len(messages)
            chunk_offset_id = messages[-1].id  # Use last message ID for next chunk

            # Break if we've processed all messages in the date range
            if len(messages) < CHUNK_SIZE:
                break

        # Final progress save
        await self._save_progress(source, last_message_id)

        # Clear the progress line and show completion
        console.print(f"[bold green]✓ Completed forwarding {processed_count} messages[/bold green]")

    async def _get_total_message_count(self, source: int, offset_date: datetime | None,
                                     end_datetime: datetime | None) -> int:
        """Get approximate total message count for progress tracking.

        Args:
            source: Source chat ID
            offset_date: Start date filter
            end_datetime: End date filter

        Returns:
            Approximate number of messages to process
        """
        try:
            # Get a small sample to estimate total
            sample_messages = await self.client.get_messages(
                source,
                limit=10,
                offset_date=offset_date
            )

            if not sample_messages:
                return 0

            # If we have date filters, estimate based on date range
            if offset_date and end_datetime:
                date_range_days = (end_datetime.date() - offset_date.date()).days
                if date_range_days > 0:
                    # Rough estimate: assume 100 messages per day on average
                    return min(date_range_days * 100, 10000)  # Cap at 10k for safety

            # Default estimate based on sample
            return 1000  # Conservative estimate

        except Exception:
            return 0  # If estimation fails, just show 0

    async def _save_progress(self, source: int, last_message_id: int) -> None:
        """Save forwarding progress for this chat to resume later.

        Args:
            source: Source chat ID
            last_message_id: Last processed message ID
        """
        import json
        import os

        progress_file = FORWARD_PROGRESS_FILE_PATH

        # Load existing progress
        progress_data = {}
        if os.path.exists(progress_file):
            try:
                with open(progress_file) as f:
                    progress_data = json.load(f)
            except (json.JSONDecodeError, OSError):
                progress_data = {}

        # Update progress for this chat
        progress_data[str(source)] = {
            "last_message_id": last_message_id,
            "timestamp": datetime.now().isoformat(),
            "status": "in_progress"
        }

        # Save progress
        try:
            with open(progress_file, 'w') as f:
                json.dump(progress_data, f, indent=2)
            console.print(f"[dim]Progress saved: chat {source}, message {last_message_id}[/dim]")
        except OSError as e:
            console.print(f"[bold red]Failed to save progress: {e}[/bold red]")

    async def _load_progress(self, source: int) -> int:
        """Load saved progress for this chat.

        Args:
            source: Source chat ID

        Returns:
            Last processed message ID, or 0 if no progress saved
        """
        import json
        import os

        progress_file = FORWARD_PROGRESS_FILE_PATH

        if not os.path.exists(progress_file):
            return 0

        try:
            with open(progress_file) as f:
                progress_data = json.load(f)

            chat_progress = progress_data.get(str(source))
            if chat_progress and chat_progress.get("status") == "in_progress":
                return chat_progress.get("last_message_id", 0)

        except (json.JSONDecodeError, OSError, KeyError):
            pass

        return 0

    async def _mark_progress_completed(self, source: int) -> None:
        """Mark progress as completed for this chat.

        Args:
            source: Source chat ID
        """
        import json
        import os

        progress_file = FORWARD_PROGRESS_FILE_PATH

        # Load existing progress
        progress_data = {}
        if os.path.exists(progress_file):
            try:
                with open(progress_file) as f:
                    progress_data = json.load(f)
            except (json.JSONDecodeError, OSError):
                progress_data = {}

        # Mark as completed
        if str(source) in progress_data:
            progress_data[str(source)]["status"] = "completed"
            progress_data[str(source)]["completed_at"] = datetime.now().isoformat()

            try:
                with open(progress_file, 'w') as f:
                    json.dump(progress_data, f, indent=2)
            except OSError:
                pass  # Ignore save errors for completion marking

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
            console.print(f"[bold red]Error forwarding message:[/bold red] {e}")

    async def _forward_album(self, destination_id: int, event: events.Album.Event, reply_to: int | None = None) -> None:
        try:
            sent_messages = await self.message_forward.forward_album(destination_id, event.messages, event.text, reply_to)
            if sent_messages:
                self._update_album_history(event, sent_messages, destination_id)
        except Exception as e:
            console.print(f"[bold red]Error forwarding album:[/bold red] {e}")

    def _update_history(self, source_message: Message, sent_message: Message) -> None:
        self.history.add_mapping(source_message.chat_id, source_message.id, sent_message.chat_id, sent_message.id)

    def _update_album_history(self, event: events.Album.Event, sent_messages: list[Message], destination_id: int) -> None:
        for i, message in enumerate(event.messages):
            self.history.add_mapping(event.chat_id, message.id, destination_id, sent_messages[i].id)
