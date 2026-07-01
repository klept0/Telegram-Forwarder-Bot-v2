from datetime import datetime, timezone

from source.service.ForwardProgress import ForwardProgress
from source.utils.Constants import DEFAULT_BATCH_SIZE
from source.utils.DateUtils import DateUtils


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

        matches = []
        async for message in self.client.iter_messages(
            source_id,
            search=keyword,
            limit=limit,
            min_id=last_message_id,
        ):
            if self._in_date_range(message.date, start_datetime, end_datetime):
                matches.append(message)

        if dry_run:
            self.console.print(
                f"[bold cyan]Dry-run:[/bold cyan] {len(matches)} messages"
                f"{keyword_label} remain to forward"
            )
            return len(matches)

        sent_count = 0
        last_forwarded_id = last_message_id
        for i, message in enumerate(reversed(matches), 1):
            if self.queue:
                await self.queue.put(
                    (self._forward_message, (destination_id, message, None))
                )
            else:
                await self._forward_message(destination_id, message)
            sent_count += 1
            last_forwarded_id = max(last_forwarded_id, message.id)

            if has_date_range and i % DEFAULT_BATCH_SIZE == 0:
                ForwardProgress.save(
                    source_id, last_forwarded_id, start_date, end_date, keyword=keyword
                )

        if has_date_range:
            if matches:
                ForwardProgress.save(
                    source_id, last_forwarded_id, start_date, end_date, keyword=keyword
                )
            ForwardProgress.mark_completed(
                source_id, start_date, end_date, keyword=keyword
            )

        self.console.print(
            f"[bold green]Forwarded {sent_count} messages{keyword_label}[/bold green]"
        )
        return sent_count

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
