from source.dialog.DateRangeDialog import DateRangeDialog
from source.model.Chat import Chat


class PruneDialog(DateRangeDialog):
    """Settings for deleting old messages from one chat."""

    async def get_config(self):
        """Returns dict with chat_id, chat_name, media_only, days,
        before_date, timezone_name, dry_run — or None if cancelled."""
        self.clear()
        chats = Chat.read()

        idx = await self.list_chats_terminal(chats, "chat to clean up")
        if idx == -1:
            return None

        content = await self.show_options(
            "What to delete?",
            [
                {"name": "All messages (text and media)", "value": "all"},
                {"name": "Media only (photos, videos, files)", "value": "media"},
            ],
        )

        mode = await self.show_options(
            "Delete messages older than:",
            [
                {"name": "A number of days", "value": "days"},
                {"name": "A date (everything before it)", "value": "date"},
            ],
        )

        days = None
        before_date = None
        timezone_name = "UTC"
        if mode == "days":
            while True:
                value = await self._get_text_input(
                    "Delete messages older than how many days?"
                )
                if value is None:
                    return None
                if value.strip().isdigit() and int(value) > 0:
                    days = int(value)
                    break
                self.console.print(
                    "[bold red]Error:[/bold red] Enter a whole number of days greater than 0."
                )
        else:
            before_date = await self._get_date_input(
                "Delete everything before (YYYY-MM-DD):"
            )
            if before_date is None:
                return None
            timezone_name = await self._get_timezone_selection()

        choice = await self.show_options(
            "Run as dry-run preview?",
            [
                {
                    "name": "No - delete matching messages (asks to confirm first)",
                    "value": "no",
                },
                {
                    "name": "Yes - count matches only (nothing deleted)",
                    "value": "yes",
                },
            ],
        )

        return {
            "chat_id": chats[idx].id,
            "chat_name": chats[idx].get_plain_display_name(),
            "media_only": content == "media",
            "days": days,
            "before_date": before_date,
            "timezone_name": timezone_name,
            "dry_run": choice == "yes",
        }
