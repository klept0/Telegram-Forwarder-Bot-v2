import asyncio
import os
from datetime import datetime, timezone

from telethon import TelegramClient, events
from telethon.tl.custom import Message

from source.service.HistoryService import HistoryService
from source.service.MessageForwardService import MessageForwardService
from source.service.MessageQueue import MessageQueue
from source.utils.Console import Terminal
from source.utils.Constants import (
    DEFAULT_CHUNK_SIZE,
    DEFAULT_BATCH_SIZE,
    FORWARD_PROGRESS_FILE_PATH,
)
from source.utils.DateUtils import DateUtils

console = Terminal.console


class Forward:
    def __init__(
        self, client: TelegramClient, forward_config_map: dict, queue: MessageQueue
    ):
        self.client = client
        self.forward_config_map = forward_config_map
        self.queue = queue
        self.history = HistoryService()
        self.message_forward = MessageForwardService(client, queue=self.queue)

    def add_events(self) -> None:
        source_chats = list(self.forward_config_map.keys())
        self.client.add_event_handler(
            self.message_handler, events.NewMessage(chats=source_chats)
        )
        self.client.add_event_handler(
            self.album_handler, events.Album(chats=source_chats)
        )

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
            start_date = getattr(config, "start_date", None)
            end_date = getattr(config, "end_date", None)
            timezone_name = getattr(config, "timezone_name", "UTC")
            dry_run = bool(getattr(config, "dry_run", False))

            # Check if there's existing progress to resume
            last_message_id = await self._load_progress(source, start_date, end_date)
            if last_message_id > 0:
                console.print(
                    f"[bold yellow]Resuming from message {last_message_id} for chat {source}[/bold yellow]"
                )

            await self._forward_chat_history(
                source,
                last_message_id,
                start_date,
                end_date,
                timezone_name,
                dry_run,
            )

            # Mark progress as completed
            if not dry_run:
                await self._mark_progress_completed(source, start_date, end_date)

    async def _forward_chat_history(
        self,
        source: int,
        last_message_id: int,
        start_date: str | None = None,
        end_date: str | None = None,
        timezone_name: str = "UTC",
        dry_run: bool = False,
    ) -> None:
        """Forward chat history with optional date filtering and chunked processing.

        Args:
            source: Source chat ID
            last_message_id: Last processed message ID
            start_date: Start date filter (YYYY-MM-DD) or None
            end_date: End date filter (YYYY-MM-DD) or None
        """
        # Configuration for chunked processing
        CHUNK_SIZE = DEFAULT_CHUNK_SIZE  # Number of messages to retrieve per chunk
        BATCH_SIZE = (
            DEFAULT_BATCH_SIZE  # Number of messages to process before saving progress
        )

        # Prepare strict date bounds in selected timezone
        start_datetime, end_datetime = self.build_date_bounds(
            start_date, end_date, timezone_name
        )

        if dry_run:
            match_count = await self.count_messages_in_range(
                source, last_message_id, start_datetime, end_datetime
            )
            console.print(
                "[bold cyan]Dry-run complete:[/bold cyan] "
                f"{match_count} messages match range "
                f"{start_date or 'beginning'} to {end_date or 'latest'} "
                f"in timezone {timezone_name}"
            )
            return

        console.print("[bold blue]Retrieving messages from chat...[/bold blue]")

        # Get total message count first (for progress tracking)
        total_messages = await self._get_total_message_count(
            source, start_datetime, end_datetime
        )
        console.print(
            f"[bold green]Found approximately {total_messages} messages to forward[/bold green]"
        )

        destination_id = self._get_destination_id(source)
        if not destination_id:
            console.print(
                "[bold red]No destination configured for this chat[/bold red]"
            )
            return

        # Process messages in chunks
        processed_count = 0
        chunk_offset_id = 0  # Start from the most recent message

        # Start background status updater for queue monitoring
        status_task = asyncio.create_task(self._periodic_status_update())

        try:
            while True:
                # Get next chunk of messages
                chunk_messages = await self.client.get_messages(
                    source,
                    limit=CHUNK_SIZE,
                    offset_id=chunk_offset_id,
                    min_id=last_message_id,
                )

                if not chunk_messages:
                    break  # No more messages

                chunk_offset_id = chunk_messages[
                    -1
                ].id  # Use last message ID for next chunk

                # Strictly enforce configured date range boundaries.
                messages = [
                    msg
                    for msg in chunk_messages
                    if self.in_date_range(msg, start_datetime, end_datetime)
                ]

                if not messages:
                    # Continue scanning older chunks to find in-range messages.
                    if len(chunk_messages) < CHUNK_SIZE:
                        break
                    continue

                # Process messages in batches
                for i, message in enumerate(reversed(messages), 1):
                    current_total = processed_count + i
                    percentage = (
                        (current_total / total_messages) * 100
                        if total_messages > 0
                        else 0
                    )

                    console.print(
                        f"[bold yellow]Progress: {current_total}/{total_messages} ({percentage:.1f}%)[/bold yellow]",
                        end="\r",
                    )

                    try:
                        reply_message = await self._handle_reply(
                            message, destination_id
                        )
                        await self._forward_message(
                            destination_id, message, reply_message
                        )
                        last_message_id = max(last_message_id, message.id)
                    except Exception as e:
                        console.print(
                            f"[bold red]Error forwarding message {message.id}: {e}[/bold red]"
                        )

                    # Save progress every BATCH_SIZE messages
                    if current_total % BATCH_SIZE == 0:
                        await self._save_progress(
                            source, last_message_id, start_date, end_date
                        )

                processed_count += len(messages)

                # Break if we've processed all messages in the date range
                if len(chunk_messages) < CHUNK_SIZE:
                    break

            # Final progress save
            await self._save_progress(source, last_message_id, start_date, end_date)

            # Clear the progress line and show completion
            console.print(
                f"[bold green]✓ Completed forwarding {processed_count} messages[/bold green]"
            )

        finally:
            # Stop the status updater
            status_task.cancel()
            try:
                await status_task
            except asyncio.CancelledError:
                pass

    async def _periodic_status_update(self) -> None:
        """Periodically display queue status during forwarding operations."""
        while True:
            await asyncio.sleep(2)  # Update every 2 seconds
            if hasattr(self, "queue") and self.queue:
                queue_size = self.queue.qsize()
                current_task = (
                    str(self.queue.current_task) if self.queue.current_task else "None"
                )
                console.print(
                    f"[dim]Queue Status: {queue_size} pending | Current: {current_task}[/dim]",
                    end="\r",
                )

    async def _get_total_message_count(
        self,
        source: int,
        start_datetime: datetime | None,
        end_datetime: datetime | None,
    ) -> int:
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
            sample_messages = await self.client.get_messages(source, limit=10)

            if not sample_messages:
                return 0

            # If we have date filters, estimate based on date range
            if start_datetime and end_datetime:
                date_range_days = (end_datetime.date() - start_datetime.date()).days
                if date_range_days > 0:
                    # Rough estimate: assume 100 messages per day on average
                    return min(date_range_days * 100, 10000)  # Cap at 10k for safety

            # Default estimate based on sample
            return 1000  # Conservative estimate

        except Exception:
            return 0  # If estimation fails, just show 0

    async def count_messages_in_range(
        self,
        source: int,
        last_message_id: int,
        start_datetime: datetime | None,
        end_datetime: datetime | None,
    ) -> int:
        """Count source messages in range without forwarding any message."""
        chunk_offset_id = 0
        total = 0

        while True:
            chunk_messages = await self.client.get_messages(
                source,
                limit=DEFAULT_CHUNK_SIZE,
                offset_id=chunk_offset_id,
                min_id=last_message_id,
            )

            if not chunk_messages:
                break

            chunk_offset_id = chunk_messages[-1].id
            total += sum(
                1
                for msg in chunk_messages
                if self.in_date_range(msg, start_datetime, end_datetime)
            )

            if len(chunk_messages) < DEFAULT_CHUNK_SIZE:
                break

        return total

    async def _save_progress(
        self,
        source: int,
        last_message_id: int,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> None:
        """Save forwarding progress for this chat to resume later.

        Args:
            source: Source chat ID
            last_message_id: Last processed message ID
        """
        import json

        progress_file = FORWARD_PROGRESS_FILE_PATH
        progress_key = self.progress_key(source, start_date, end_date)

        # Load existing progress
        progress_data = {}
        if os.path.exists(progress_file):
            try:
                with open(progress_file, encoding="utf-8") as f:
                    progress_data = json.load(f)
            except (json.JSONDecodeError, OSError):
                progress_data = {}

        # Update progress for this chat
        progress_data[progress_key] = {
            "source": source,
            "start_date": start_date,
            "end_date": end_date,
            "last_message_id": last_message_id,
            "timestamp": datetime.now().isoformat(),
            "status": "in_progress",
        }

        # Save progress
        try:
            with open(progress_file, "w", encoding="utf-8") as f:
                json.dump(progress_data, f, indent=2)
            console.print(
                f"[dim]Progress saved: chat {source}, message {last_message_id}[/dim]"
            )
        except OSError as e:
            console.print(f"[bold red]Failed to save progress: {e}[/bold red]")

    async def _load_progress(
        self,
        source: int,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> int:
        """Load saved progress for this chat.

        Args:
            source: Source chat ID

        Returns:
            Last processed message ID, or 0 if no progress saved
        """
        import json

        progress_file = FORWARD_PROGRESS_FILE_PATH
        progress_key = self.progress_key(source, start_date, end_date)

        if not os.path.exists(progress_file):
            return 0

        try:
            with open(progress_file, encoding="utf-8") as f:
                progress_data = json.load(f)

            chat_progress = progress_data.get(progress_key)
            if chat_progress and chat_progress.get("status") == "in_progress":
                return chat_progress.get("last_message_id", 0)

            # Backward compatibility: older progress files keyed only by source id.
            legacy_progress = progress_data.get(str(source))
            if legacy_progress and legacy_progress.get("status") == "in_progress":
                return legacy_progress.get("last_message_id", 0)

        except (json.JSONDecodeError, OSError, KeyError):
            pass

        return 0

    async def _mark_progress_completed(
        self,
        source: int,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> None:
        """Mark progress as completed for this chat.

        Args:
            source: Source chat ID
        """
        import json

        progress_file = FORWARD_PROGRESS_FILE_PATH
        progress_key = self.progress_key(source, start_date, end_date)

        # Load existing progress
        progress_data = {}
        if os.path.exists(progress_file):
            try:
                with open(progress_file, encoding="utf-8") as f:
                    progress_data = json.load(f)
            except (json.JSONDecodeError, OSError):
                progress_data = {}

        # Mark as completed
        if progress_key in progress_data:
            progress_data[progress_key]["status"] = "completed"
            progress_data[progress_key]["completed_at"] = datetime.now().isoformat()

            try:
                with open(progress_file, "w", encoding="utf-8") as f:
                    json.dump(progress_data, f, indent=2)
            except OSError:
                pass  # Ignore save errors for completion marking

    def progress_key(
        self, source: int, start_date: str | None = None, end_date: str | None = None
    ) -> str:
        start_value = start_date or "none"
        end_value = end_date or "none"
        return f"{source}|{start_value}|{end_value}"

    def build_date_bounds(
        self,
        start_date: str | None,
        end_date: str | None,
        timezone_name: str = "UTC",
    ) -> tuple[datetime | None, datetime | None]:
        tzinfo = DateUtils.get_timezone(timezone_name)
        start_datetime = None
        end_datetime = None

        if start_date:
            start_dt = DateUtils.parse_date(start_date)
            if start_dt:
                start_datetime = datetime.combine(
                    start_dt, datetime.min.time()
                ).replace(tzinfo=tzinfo)

        if end_date:
            end_dt = DateUtils.parse_date(end_date)
            if end_dt:
                end_datetime = datetime.combine(end_dt, datetime.max.time()).replace(
                    tzinfo=tzinfo
                )

        return start_datetime, end_datetime

    def in_date_range(
        self,
        message: Message,
        start_datetime: datetime | None,
        end_datetime: datetime | None,
    ) -> bool:
        message_date = message.date

        # Ensure comparisons are timezone-aware and comparable.
        if message_date.tzinfo is None:
            message_date = message_date.replace(tzinfo=timezone.utc)

        target_tz = (
            start_datetime.tzinfo
            if start_datetime and start_datetime.tzinfo
            else (
                end_datetime.tzinfo
                if end_datetime and end_datetime.tzinfo
                else timezone.utc
            )
        )
        message_date = message_date.astimezone(target_tz)

        if start_datetime and message_date < start_datetime:
            return False
        if end_datetime and message_date > end_datetime:
            return False
        return True

    async def clear_progress(self) -> bool:
        """Delete the persisted forward progress file."""
        progress_file = FORWARD_PROGRESS_FILE_PATH
        if not os.path.exists(progress_file):
            return False

        os.remove(progress_file)
        return True

    def _get_destination_id(self, source_id: int) -> int | None:
        config = self.forward_config_map.get(source_id)
        return config.destinationID if config else None

    async def _handle_reply(self, message: Message, destination_id: int) -> int | None:
        if not message.is_reply:
            return None
        return self.history.get_mapping(
            message.chat_id, message.reply_to_msg_id, destination_id
        )

    async def _get_album_reply(
        self, messages: list[Message], destination_id: int
    ) -> int | None:
        for message in messages:
            reply = await self._handle_reply(message, destination_id)
            if reply is not None:
                return reply
        return None

    async def _forward_message(
        self, destination_id: int, message: Message, reply_to: int | None = None
    ) -> None:
        try:
            await self.message_forward.forward_message(
                destination_id, message, reply_to, on_sent=self._on_message_sent
            )
        except Exception as e:
            console.print(f"[bold red]Error forwarding message:[/bold red] {e}")

    async def _forward_album(
        self,
        destination_id: int,
        event: events.Album.Event,
        reply_to: int | None = None,
    ) -> None:
        try:
            await self.message_forward.forward_album(
                destination_id,
                event.messages,
                event.text,
                reply_to,
                on_sent=lambda _source_messages, sent_messages: self._on_album_sent(
                    event, sent_messages, destination_id
                ),
            )
        except Exception as e:
            console.print(f"[bold red]Error forwarding album:[/bold red] {e}")

    def _on_message_sent(self, source_message: Message, sent_message) -> None:
        if not sent_message:
            return
        if isinstance(sent_message, list):
            if sent_message:
                self._update_history(source_message, sent_message[0])
        else:
            self._update_history(source_message, sent_message)

    def _on_album_sent(self, event, sent_messages, destination_id: int) -> None:
        if not sent_messages:
            return
        if not isinstance(sent_messages, list):
            sent_messages = [sent_messages]
        self._update_album_history(event, sent_messages, destination_id)

    def _update_history(self, source_message: Message, sent_message: Message) -> None:
        self.history.add_mapping(
            source_message.chat_id,
            source_message.id,
            sent_message.chat_id,
            sent_message.id,
        )

    def _update_album_history(
        self,
        event: events.Album.Event,
        sent_messages: list[Message],
        destination_id: int,
    ) -> None:
        for source_message, dest_message in zip(event.messages, sent_messages):
            self.history.add_mapping(
                event.chat_id, source_message.id, destination_id, dest_message.id
            )
