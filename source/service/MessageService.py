from datetime import datetime, timedelta, timezone

from telethon.errors import FloodWaitError

from rich.markup import escape

from source.service.ForwardProgress import ForwardProgress
from source.utils.Constants import DEFAULT_BATCH_SIZE, DELETE_BATCH_SIZE
from source.utils.DateUtils import DateUtils


class MessageService:
    def __init__(self, client, console, queue=None):
        self.client = client
        self.console = console
        self.queue = queue

    async def delete_messages_from_dialog(self, dialog):
        """Delete every message the current user sent in `dialog`.

        Filters server-side with `from_user="me"`; comparing `message.from_id`
        to an int never matches because Telethon returns a Peer object there.
        """
        message_ids = [
            message.id
            async for message in self.client.iter_messages(dialog.id, from_user="me")
        ]
        for start in range(0, len(message_ids), DELETE_BATCH_SIZE):
            batch = message_ids[start : start + DELETE_BATCH_SIZE]
            if self.queue:
                await self.queue.put((self._delete_messages, (dialog.id, batch)))
            else:
                await self._delete_messages(dialog.id, batch)

    async def _delete_messages(self, chat_id, message_ids):
        try:
            await self.client.delete_messages(chat_id, message_ids)
        except FloodWaitError:
            raise  # let the queue wait it out and retry
        except Exception as e:
            self.console.print(
                f"[bold red]Error deleting messages:[/bold red] {escape(str(e))}"
            )

    @staticmethod
    def build_prune_cutoff(days=None, before_date=None, timezone_name="UTC", now=None):
        """Aware datetime; messages strictly older than it get deleted.

        `days`: older than that many days from `now` (UTC).
        `before_date` (YYYY-MM-DD): before the start of that day in `timezone_name`.
        """
        if days is not None:
            now = now or datetime.now(timezone.utc)
            return now - timedelta(days=int(days))
        parsed = DateUtils.parse_date(before_date) if before_date else None
        if not parsed:
            raise ValueError("Give either days or a valid before_date")
        return datetime.combine(parsed, datetime.min.time()).replace(
            tzinfo=DateUtils.get_timezone(timezone_name)
        )

    async def collect_old_message_ids(self, chat_id, cutoff, media_only=False):
        """IDs of messages in `chat_id` posted before `cutoff`, newest first.

        `media_only` keeps photos, videos and files only; link previews
        don't count as media.
        """
        ids = []
        async for message in self.client.iter_messages(chat_id, offset_date=cutoff):
            if media_only and not (message.photo or message.document):
                continue
            ids.append(message.id)
        return ids

    async def delete_message_ids(self, chat_id, message_ids):
        """Delete `message_ids` in batches; waits until all are done."""
        for start in range(0, len(message_ids), DELETE_BATCH_SIZE):
            batch = message_ids[start : start + DELETE_BATCH_SIZE]
            if self.queue:
                await self.queue.put((self._delete_messages, (chat_id, batch)))
            else:
                await self._delete_messages(chat_id, batch)
        await self._drain_queue()

    async def find_user_messages(self, chat, user, limit=None):
        """Messages sent by `user` among the latest `limit` in `chat`."""
        return [
            message
            async for message in self.client.iter_messages(chat.id, limit=limit)
            if message.sender_id == user.id
        ]

    async def forward_messages_by_keyword(
        self,
        source_id,
        destination_id,
        keyword=None,
        limit=None,
        start_date=None,
        end_date=None,
        timezone_name="UTC",
        dry_run=False,
    ):
        """Search a chat's history and forward matches. `keyword` is
        optional — leave it unset to forward every message in the range.

        When both `start_date` and `end_date` are given, this is resumable:
        re-running the same source/date-range/keyword combination skips
        whatever was already forwarded (whether the prior run finished or
        was interrupted) instead of sending duplicates.
        """
        start_datetime, end_datetime = self._build_date_bounds(
            start_date, end_date, timezone_name
        )
        keyword = (
            keyword.strip() if isinstance(keyword, str) and keyword.strip() else None
        )
        keyword_label = f" matching keyword '{keyword}'" if keyword else ""

        has_date_range = bool(start_date and end_date)
        last_message_id = 0
        if has_date_range:
            last_message_id = ForwardProgress.load(
                source_id, start_date, end_date, keyword=keyword
            )
            if last_message_id > 0:
                self.console.print(
                    f"[bold yellow]Resuming: skipping messages already forwarded "
                    f"up through {last_message_id}[/bold yellow]"
                )

        limit_reached = False
        if has_date_range:
            # Oldest first from the resume point, so when `limit` cuts the
            # run short the saved progress has nothing unforwarded before it
            # and the next run carries on from there.
            matches, limit_reached = await self._collect_ascending(
                source_id, keyword, limit, last_message_id, start_datetime, end_datetime
            )
        else:
            # No date range means no saved progress: take the newest `limit`
            # matches and send them oldest first.
            matches = []
            async for message in self.client.iter_messages(
                source_id,
                search=keyword,
                limit=limit,
                min_id=last_message_id,
            ):
                if self._in_date_range(message.date, start_datetime, end_datetime):
                    matches.append(message)
            matches.reverse()

        if dry_run:
            self.console.print(
                f"[bold cyan]Dry-run:[/bold cyan] {len(matches)} messages"
                f"{keyword_label} remain to forward"
            )
            return len(matches)

        sent_count = 0
        last_forwarded_id = last_message_id
        for i, message in enumerate(matches, 1):
            if self.queue:
                await self.queue.put(
                    (self._forward_message, (destination_id, message, None))
                )
            else:
                await self._forward_message(destination_id, message)
            sent_count += 1
            last_forwarded_id = max(last_forwarded_id, message.id)

            if has_date_range and i % DEFAULT_BATCH_SIZE == 0:
                # Only record progress for sends that have actually happened.
                await self._drain_queue()
                ForwardProgress.save(
                    source_id, last_forwarded_id, start_date, end_date, keyword=keyword
                )

        await self._drain_queue()
        if has_date_range:
            if matches:
                ForwardProgress.save(
                    source_id, last_forwarded_id, start_date, end_date, keyword=keyword
                )
            if not limit_reached:
                ForwardProgress.mark_completed(
                    source_id, start_date, end_date, keyword=keyword
                )

        self.console.print(
            f"[bold green]Forwarded {sent_count} messages{keyword_label}[/bold green]"
        )
        if limit_reached:
            self.console.print(
                f"[bold yellow]Stopped at the {limit}-message limit; run it "
                "again to continue from here.[/bold yellow]"
            )
        return sent_count

    async def _collect_ascending(
        self, source_id, keyword, limit, last_message_id, start_datetime, end_datetime
    ):
        """Matches in the date range after `last_message_id`, oldest first.

        Returns (matches, limit_reached). `limit_reached` means the scan
        stopped at `limit` and later messages in the range may remain.
        """
        min_id = last_message_id
        if not min_id and start_datetime:
            # Search can't start from a date when going oldest-first, so
            # find the first message of the range and start from its ID.
            first = await self.client.get_messages(
                source_id, limit=1, offset_date=start_datetime, reverse=True
            )
            if not first:
                return [], False
            min_id = first[0].id - 1

        matches = []
        scanned = 0
        async for message in self.client.iter_messages(
            source_id, search=keyword, limit=limit, min_id=min_id, reverse=True
        ):
            scanned += 1
            if end_datetime and not self._in_date_range(
                message.date, None, end_datetime
            ):
                # Past the end of the range; everything later is too.
                return matches, False
            if self._in_date_range(message.date, start_datetime, end_datetime):
                matches.append(message)
        return matches, bool(limit) and scanned >= limit

    async def _drain_queue(self):
        if self.queue:
            await self.queue.join()

    async def _forward_message(self, destination_id, message, reply_to=None):
        _ = reply_to
        await self.client.forward_messages(destination_id, message)

    @staticmethod
    def _build_date_bounds(start_date, end_date, timezone_name):
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

    @staticmethod
    def _in_date_range(message_date, start_datetime, end_datetime):
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
