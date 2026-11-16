import asyncio
from datetime import datetime, timezone

from telethon import TelegramClient, events
from telethon.tl.custom import Message
from telethon.tl.types import MessageService as ServiceMessage

from rich.markup import escape

from source.service.ForwardProgress import ForwardProgress
from source.service.HistoryService import HistoryService
from source.service.MessageForwardService import MessageForwardService
from source.service.MessageQueue import MessageQueue
from source.utils.Console import Terminal
from source.utils.Constants import DEFAULT_CHUNK_SIZE, DEFAULT_BATCH_SIZE
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
        self.message_forward = MessageForwardService(
            client, queue=self.queue, reply_resolver=self._handle_reply
        )
        # Source message IDs whose send failed during the current history run.
        self._failed_ids: set[int] = set()
        # (source chat, message ID) of messages the live handlers took while
        # catch_up was running, so catch_up doesn't queue them a second time.
        self._catching_up = False
        self._live_seen: set[tuple[int, int]] = set()
        # Live mode prints a line per forward; a bulk history run would
        # print thousands, and has its own progress output.
        self._log_forwards = False

    def add_events(self) -> None:
        self._log_forwards = True
        source_chats = list(self.forward_config_map.keys())
        self.client.add_event_handler(
            self.message_handler, events.NewMessage(chats=source_chats)
        )
        self.client.add_event_handler(
            self.album_handler, events.Album(chats=source_chats)
        )

    def remove_events(self) -> None:
        """Stop live forwarding by unregistering the handlers from add_events."""
        self._log_forwards = False
        self.client.remove_event_handler(self.message_handler)
        self.client.remove_event_handler(self.album_handler)

    async def message_handler(self, event: events.NewMessage.Event) -> None:
        try:
            if event.grouped_id:
                return
            destination_id = self._get_destination_id(event.chat_id)
            if not destination_id:
                return
            if self._catching_up:
                self._live_seen.add((event.chat_id, event.message.id))
            await self._forward_message(destination_id, event.message)
        except Exception as e:
            console.print(
                f"[bold red]Error handling message:[/bold red] {escape(str(e))}"
            )

    async def album_handler(self, event: events.Album.Event) -> None:
        try:
            destination_id = self._get_destination_id(event.chat_id)
            if not destination_id:
                return
            if self._catching_up:
                self._live_seen.update(
                    (event.chat_id, message.id) for message in event.messages
                )
            await self._forward_album(destination_id, event.messages)
        except Exception as e:
            console.print(
                f"[bold red]Error handling album:[/bold red] {escape(str(e))}"
            )

    async def catch_up(self) -> int:
        """Forward messages posted while live forwarding was not running.

        For each source, resumes after the newest source message already
        recorded in history for its destination, up to the newest message at
        call time. Call it after add_events(): anything newer is left to the
        live handlers. Messages that already have a history mapping are
        skipped, so one the live handler sent during catch-up isn't sent
        twice. A source with no history is skipped, so a new config never
        forwards a whole chat. Returns the number of messages forwarded.
        """
        # Read every resume point before the first await: once handlers run,
        # a live send would move a later source's newest mapping past its gap.
        resume_points = {
            source: self._last_forwarded_id(source, config.destinationID)
            for source, config in self.forward_config_map.items()
        }
        self._catching_up = True
        try:
            total = await self._catch_up_sources(resume_points)
        finally:
            self._catching_up = False
            self._live_seen.clear()
        if total:
            console.print(
                f"[bold green]Catch-up queued {total} message(s)[/bold green]"
            )
        return total

    async def _catch_up_sources(self, resume_points: dict) -> int:
        total = 0
        for source, config in self.forward_config_map.items():
            destination_id = config.destinationID
            try:
                last_id = resume_points[source]
                if not last_id:
                    console.print(
                        f"[dim]No forward history for {source}; skipping catch-up[/dim]"
                    )
                    continue
                latest = await self.client.get_messages(source, limit=1)
                if not latest or latest[0].id <= last_id:
                    continue
                upper_id = latest[0].id
                console.print(
                    f"[bold blue]Catching up {source}: messages after "
                    f"{last_id} up to {upper_id}[/bold blue]"
                )
                total += await self._catch_up_source(
                    source, destination_id, last_id, upper_id
                )
            except Exception as e:
                console.print(
                    f"[bold red]Catch-up failed for {source}:[/bold red] {escape(str(e))}"
                )
        return total

    def _last_forwarded_id(self, source: int, destination_id: int) -> int:
        """Newest source message ID with a history mapping to destination_id."""
        return max(
            (
                source_msg_id
                for (src, source_msg_id, dest) in self.history.get_all_mappings()
                if src == source and dest == destination_id
            ),
            default=0,
        )

    async def _catch_up_source(
        self, source: int, destination_id: int, last_id: int, upper_id: int
    ) -> int:
        cursor_id = last_id
        album: list[Message] = []
        sent = 0
        done = False
        while not done:
            chunk = await self._fetch_ascending_chunk(
                source, cursor_id, None, DEFAULT_CHUNK_SIZE
            )
            if not chunk:
                break
            cursor_id = chunk[-1].id
            for message in chunk:
                if message.id > upper_id:
                    done = True
                    break
                if isinstance(message, ServiceMessage):
                    continue  # joins, pins etc. can't be forwarded
                if self.history.get_mapping(source, message.id, destination_id):
                    continue
                # Taken by a live handler since catch-up began; it is queued
                # but has no history mapping until it is actually sent.
                if (source, message.id) in self._live_seen:
                    continue
                grouped_id = message.grouped_id
                if album and album[-1].grouped_id != grouped_id:
                    await self._send_history_unit(destination_id, album, 0)
                    sent += len(album)
                    album = []
                if grouped_id:
                    album.append(message)
                else:
                    await self._send_history_unit(destination_id, [message], 0)
                    sent += 1
            if len(chunk) < DEFAULT_CHUNK_SIZE:
                break
        if album:
            await self._send_history_unit(destination_id, album, 0)
            sent += len(album)
        return sent

    async def history_handler(self) -> None:
        for source in self.forward_config_map:
            config = self.forward_config_map[source]
            start_date = getattr(config, "start_date", None)
            end_date = getattr(config, "end_date", None)
            timezone_name = getattr(config, "timezone_name", "UTC")
            dry_run = bool(getattr(config, "dry_run", False))
            media_only = bool(getattr(config, "media_only", False))
            keyword = getattr(config, "keyword", None) or None

            # Check if there's existing progress to resume
            last_message_id = await self._load_progress(
                source, start_date, end_date, media_only, keyword
            )
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
                media_only,
                keyword,
            )

            # Mark progress as completed
            if not dry_run:
                await self._mark_progress_completed(
                    source, start_date, end_date, media_only, keyword
                )

    async def _forward_chat_history(
        self,
        source: int,
        last_message_id: int,
        start_date: str | None = None,
        end_date: str | None = None,
        timezone_name: str = "UTC",
        dry_run: bool = False,
        media_only: bool = False,
        keyword: str | None = None,
    ) -> None:
        """Forward chat history with optional date/media/keyword filtering and
        chunked processing.

        Args:
            source: Source chat ID
            last_message_id: Last processed message ID
            start_date: Start date filter (YYYY-MM-DD) or None
            end_date: End date filter (YYYY-MM-DD) or None
            media_only: Only forward messages carrying a file/photo/video
            keyword: Only forward messages whose text/caption contains this
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
                source,
                last_message_id,
                start_datetime,
                end_datetime,
                media_only,
                keyword,
            )
            item_label = "files" if media_only else "messages"
            keyword_label = f" matching keyword '{keyword}'" if keyword else ""
            console.print(
                "[bold cyan]Dry-run complete:[/bold cyan] "
                f"{match_count} {item_label}{keyword_label} match range "
                f"{start_date or 'beginning'} to {end_date or 'latest'} "
                f"in timezone {timezone_name}"
            )
            return

        console.print("[bold blue]Retrieving messages from chat...[/bold blue]")

        # Get total message count first (for progress tracking)
        total_messages = await self._get_total_message_count(
            source, start_datetime, end_datetime, last_message_id
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

        # Sends that failed in an earlier run sit at or before the resume
        # point, so the loop below would never reach them again.
        self._failed_ids = set()
        retry_ids = ForwardProgress.load_failed(
            source, start_date, end_date, media_only, keyword
        )
        if retry_ids:
            await self._retry_failed(source, destination_id, retry_ids)
            await self._drain_queue()
            await self._save_progress(
                source, last_message_id, start_date, end_date, media_only, keyword
            )

        # Process messages in chunks, oldest-to-newest, so files/messages are
        # forwarded in the order they were originally posted.
        processed_count = 0
        cursor_id = last_message_id
        reached_end = False
        # An album may straddle a chunk boundary, so this carries across chunks.
        album: list[Message] = []

        # Start background status updater for queue monitoring
        status_task = asyncio.create_task(self._periodic_status_update())

        try:
            while not reached_end:
                chunk_messages = await self._fetch_ascending_chunk(
                    source, cursor_id, start_datetime, CHUNK_SIZE
                )

                if not chunk_messages:
                    break  # No more messages

                cursor_id = chunk_messages[-1].id  # Highest ID fetched so far

                # Messages already come back oldest-first when reverse=True.
                messages = []
                for msg in chunk_messages:
                    if end_datetime and self._is_after(msg, end_datetime):
                        reached_end = True
                        break
                    if self.matches_criteria(
                        msg, start_datetime, end_datetime, media_only, keyword
                    ):
                        messages.append(msg)

                for i, message in enumerate(messages, 1):
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

                    # Album items share a grouped_id and arrive consecutively;
                    # collect them so the album is forwarded as one unit
                    # instead of as separate messages.
                    grouped_id = message.grouped_id
                    if album and album[-1].grouped_id != grouped_id:
                        last_message_id = await self._send_history_unit(
                            destination_id, album, last_message_id
                        )
                        album = []
                    if grouped_id:
                        album.append(message)
                    else:
                        last_message_id = await self._send_history_unit(
                            destination_id, [message], last_message_id
                        )

                    # Save progress every BATCH_SIZE messages
                    if current_total % BATCH_SIZE == 0:
                        await self._drain_queue()
                        await self._save_progress(
                            source,
                            last_message_id,
                            start_date,
                            end_date,
                            media_only,
                            keyword,
                        )

                processed_count += len(messages)

                if len(chunk_messages) < CHUNK_SIZE:
                    break

            if album:
                last_message_id = await self._send_history_unit(
                    destination_id, album, last_message_id
                )

            # Final progress save
            await self._drain_queue()
            await self._save_progress(
                source, last_message_id, start_date, end_date, media_only, keyword
            )

            # Clear the progress line and show completion
            item_label = "files" if media_only else "messages"
            console.print(
                f"[bold green]✓ Completed forwarding {processed_count} {item_label}[/bold green]"
            )

        finally:
            # Stop the status updater
            status_task.cancel()
            try:
                await status_task
            except asyncio.CancelledError:
                pass

    async def _retry_failed(
        self, source: int, destination_id: int, message_ids: list[int]
    ) -> None:
        """Re-send messages whose send failed in an earlier run."""
        console.print(
            f"[bold yellow]Retrying {len(message_ids)} message(s) that failed "
            f"earlier for chat {source}[/bold yellow]"
        )
        try:
            fetched = await self.client.get_messages(source, ids=message_ids)
        except Exception as e:
            console.print(
                f"[bold red]Could not fetch failed messages:[/bold red] {escape(str(e))}"
            )
            self._failed_ids.update(message_ids)  # keep them for the next run
            return
        # Deleted messages come back as None; there is nothing left to retry.
        messages = [m for m in fetched or [] if m is not None]
        unit: list[Message] = []
        for message in messages:
            same_album = (
                unit
                and message.grouped_id
                and unit[-1].grouped_id == message.grouped_id
            )
            if unit and not same_album:
                await self._send_history_unit(destination_id, unit, 0)
                unit = []
            unit.append(message)
        if unit:
            await self._send_history_unit(destination_id, unit, 0)

    async def _send_history_unit(
        self, destination_id: int, messages: list[Message], last_message_id: int
    ) -> int:
        """Forward one message or one album; return the new resume point.

        The send is usually only queued here, so a failure shows up later:
        it is recorded in `_failed_ids`, which `_save_progress` persists so
        the next run retries the message instead of resuming past it.
        """
        ids = [message.id for message in messages]

        def on_error(_error: Exception) -> None:
            self._failed_ids.update(ids)

        if len(messages) == 1:
            await self._forward_message(destination_id, messages[0], on_error=on_error)
        else:
            await self._forward_album(destination_id, messages, on_error=on_error)
        return max(last_message_id, messages[-1].id)

    async def _drain_queue(self) -> None:
        """Wait for queued sends to finish before persisting progress.

        `_forward_message` only enqueues, so saving right after it would
        record messages as forwarded while they're still waiting in the
        queue — an interrupted run would then resume past them and they'd
        never be sent.
        """
        if self.queue:
            await self.queue.join()

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
        last_message_id: int = 0,
    ) -> int:
        """Get approximate total message count for progress tracking.

        Args:
            source: Source chat ID
            start_datetime: Start date filter
            end_datetime: End date filter
            last_message_id: Resume point; earlier messages are not counted

        Returns:
            Approximate number of messages to process
        """
        try:
            if not start_datetime and not end_datetime and not last_message_id:
                # limit=0 fetches no messages, only the chat's message count.
                result = await self.client.get_messages(source, limit=0)
                return int(getattr(result, "total", 0) or 0)

            # For part of a chat, use the span of message IDs it covers: IDs
            # in a channel or supergroup are sequential, so this is close
            # (deleted messages make it a little high).
            first_id = last_message_id + 1
            if not last_message_id and start_datetime:
                first = await self.client.get_messages(
                    source, limit=1, offset_date=start_datetime, reverse=True
                )
                if not first:
                    return 0
                first_id = first[0].id
            if end_datetime:
                last = await self.client.get_messages(
                    source, limit=1, offset_date=end_datetime
                )
            else:
                last = await self.client.get_messages(source, limit=1)
            if not last:
                return 0
            return max(last[0].id - first_id + 1, 0)

        except Exception:
            return 0  # If estimation fails, just show 0

    async def count_messages_in_range(
        self,
        source: int,
        last_message_id: int,
        start_datetime: datetime | None,
        end_datetime: datetime | None,
        media_only: bool = False,
        keyword: str | None = None,
    ) -> int:
        """Count source messages in range without forwarding any message."""
        cursor_id = last_message_id
        total = 0

        while True:
            chunk_messages = await self._fetch_ascending_chunk(
                source, cursor_id, start_datetime, DEFAULT_CHUNK_SIZE
            )

            if not chunk_messages:
                break

            cursor_id = chunk_messages[-1].id

            reached_end = False
            for msg in chunk_messages:
                if end_datetime and self._is_after(msg, end_datetime):
                    reached_end = True
                    break
                if self.matches_criteria(
                    msg, start_datetime, end_datetime, media_only, keyword
                ):
                    total += 1

            if reached_end or len(chunk_messages) < DEFAULT_CHUNK_SIZE:
                break

        return total

    async def _save_progress(
        self,
        source: int,
        last_message_id: int,
        start_date: str | None = None,
        end_date: str | None = None,
        media_only: bool = False,
        keyword: str | None = None,
    ) -> None:
        """Save forwarding progress for this chat to resume later."""
        # Only pass failed_ids when there are some, so a clean run's call and
        # saved entry stay unchanged.
        extra = {"failed_ids": sorted(self._failed_ids)} if self._failed_ids else {}
        saved = ForwardProgress.save(
            source, last_message_id, start_date, end_date, media_only, keyword, **extra
        )
        if saved:
            console.print(
                f"[dim]Progress saved: chat {source}, message {last_message_id}[/dim]"
            )
        else:
            console.print(
                f"[bold red]Failed to save progress for chat {source}[/bold red]"
            )

    async def _load_progress(
        self,
        source: int,
        start_date: str | None = None,
        end_date: str | None = None,
        media_only: bool = False,
        keyword: str | None = None,
    ) -> int:
        """Load saved progress for this chat (see ForwardProgress.load)."""
        return ForwardProgress.load(source, start_date, end_date, media_only, keyword)

    async def _mark_progress_completed(
        self,
        source: int,
        start_date: str | None = None,
        end_date: str | None = None,
        media_only: bool = False,
        keyword: str | None = None,
    ) -> None:
        """Mark progress as completed for this chat."""
        ForwardProgress.mark_completed(
            source, start_date, end_date, media_only, keyword
        )

    def progress_key(
        self,
        source: int,
        start_date: str | None = None,
        end_date: str | None = None,
        media_only: bool = False,
        keyword: str | None = None,
    ) -> str:
        return ForwardProgress.key(source, start_date, end_date, media_only, keyword)

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

    def _normalized_message_date(
        self,
        message: Message,
        start_datetime: datetime | None,
        end_datetime: datetime | None,
    ) -> datetime:
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
        return message_date.astimezone(target_tz)

    def in_date_range(
        self,
        message: Message,
        start_datetime: datetime | None,
        end_datetime: datetime | None,
    ) -> bool:
        message_date = self._normalized_message_date(
            message, start_datetime, end_datetime
        )

        if start_datetime and message_date < start_datetime:
            return False
        if end_datetime and message_date > end_datetime:
            return False
        return True

    def _is_after(self, message: Message, end_datetime: datetime) -> bool:
        """True once a message (fetched in ascending order) has passed the
        configured end of the range, meaning every later message will too."""
        message_date = self._normalized_message_date(message, None, end_datetime)
        return message_date > end_datetime

    def matches_criteria(
        self,
        message: Message,
        start_datetime: datetime | None,
        end_datetime: datetime | None,
        media_only: bool = False,
        keyword: str | None = None,
    ) -> bool:
        """Combined date range / media-presence / keyword filter for a message."""
        # Service messages (joins, pins, title changes) can't be forwarded;
        # trying only produces an error and uses a rate-limited send slot.
        if isinstance(message, ServiceMessage):
            return False
        if not self.in_date_range(message, start_datetime, end_datetime):
            return False
        if media_only and not message.media:
            return False
        if keyword:
            text = (message.text or getattr(message, "message", "") or "").lower()
            if keyword.lower() not in text:
                return False
        return True

    async def _fetch_ascending_chunk(
        self,
        source: int,
        cursor_id: int,
        start_datetime: datetime | None,
        limit: int,
    ) -> list[Message]:
        """Fetch the next chunk of messages in ascending (oldest-first) order.

        On the very first fetch (no resume cursor yet) and a start date is
        configured, jump directly to that date instead of scanning the whole
        chat history from message 1 forward.
        """
        if cursor_id == 0 and start_datetime:
            return await self.client.get_messages(
                source, limit=limit, offset_date=start_datetime, reverse=True
            )
        return await self.client.get_messages(
            source, limit=limit, min_id=cursor_id, reverse=True
        )

    async def clear_progress(self) -> bool:
        """Delete the persisted forward progress file."""
        return ForwardProgress.clear()

    def _get_destination_id(self, source_id: int) -> int | None:
        config = self.forward_config_map.get(source_id)
        return config.destinationID if config else None

    async def _handle_reply(self, message: Message, destination_id: int) -> int | None:
        if not message.is_reply:
            return None
        return self.history.get_mapping(
            message.chat_id, message.reply_to_msg_id, destination_id
        )

    async def _forward_message(
        self,
        destination_id: int,
        message: Message,
        reply_to: int | None = None,
        on_error=None,
    ) -> None:
        try:
            await self.message_forward.forward_message(
                destination_id,
                message,
                reply_to,
                on_sent=self._on_message_sent,
                on_error=on_error,
            )
        except Exception as e:
            console.print(
                f"[bold red]Error forwarding message:[/bold red] {escape(str(e))}"
            )

    async def _forward_album(
        self,
        destination_id: int,
        messages: list[Message],
        reply_to: int | None = None,
        on_error=None,
    ) -> None:
        try:
            await self.message_forward.forward_album(
                destination_id,
                messages,
                None,
                reply_to,
                on_sent=lambda source_messages, sent_messages: self._on_album_sent(
                    source_messages, sent_messages, destination_id
                ),
                on_error=on_error,
            )
        except Exception as e:
            console.print(
                f"[bold red]Error forwarding album:[/bold red] {escape(str(e))}"
            )

    def _on_message_sent(self, source_message: Message, sent_message) -> None:
        if not sent_message:
            return
        if isinstance(sent_message, list):
            if sent_message:
                self._update_history(source_message, sent_message[0])
        else:
            self._update_history(source_message, sent_message)

    def _on_album_sent(
        self, source_messages: list[Message], sent_messages, destination_id: int
    ) -> None:
        if not sent_messages:
            return
        if not isinstance(sent_messages, list):
            sent_messages = [sent_messages]
        self._update_album_history(source_messages, sent_messages, destination_id)

    def _update_history(self, source_message: Message, sent_message: Message) -> None:
        self.history.add_mapping(
            source_message.chat_id,
            source_message.id,
            sent_message.chat_id,
            sent_message.id,
        )
        self._log_forward(
            source_message.chat_id,
            [source_message.id],
            sent_message.chat_id,
            [sent_message.id],
        )

    def _update_album_history(
        self,
        source_messages: list[Message],
        sent_messages: list[Message],
        destination_id: int,
    ) -> None:
        pairs = list(zip(source_messages, sent_messages))
        for source_message, dest_message in pairs:
            self.history.add_mapping(
                source_message.chat_id,
                source_message.id,
                destination_id,
                dest_message.id,
            )
        if pairs:
            self._log_forward(
                pairs[0][0].chat_id,
                [source_message.id for source_message, _ in pairs],
                destination_id,
                [dest_message.id for _, dest_message in pairs],
            )

    def _log_forward(
        self, source_id: int, source_ids: list[int], dest_id: int, dest_ids: list[int]
    ) -> None:
        """Print one timestamped line for a forwarded message or album."""
        if not self._log_forwards:
            return

        def span(ids: list[int]) -> str:
            return str(ids[0]) if len(ids) == 1 else f"{ids[0]}-{ids[-1]}"

        kind = "message" if len(source_ids) == 1 else f"album of {len(source_ids)}"
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        console.print(
            f"{stamp} Forwarded {kind} {span(source_ids)} from {source_id} "
            f"as {span(dest_ids)} in {dest_id}",
            markup=False,
            highlight=False,
            soft_wrap=True,  # keep it on one line in the redirected log
        )
