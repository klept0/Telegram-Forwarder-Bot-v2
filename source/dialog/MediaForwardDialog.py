from source.dialog.DateRangeDialog import DateRangeDialog
from source.model.Chat import Chat


class MediaForwardDialog(DateRangeDialog):
    """Gathers settings for forwarding files/images (optionally keyword-filtered)
    from a source chat's history, in the order they were originally posted."""

    async def get_config(self):
        """Get media-forward settings from user input.

        Returns:
            dict with source_id, destination_id, keyword, start_date, end_date,
            timezone_name, dry_run — or None if cancelled.
        """
        self.clear()
        chats = Chat.read()

        source_idx = await self.list_chats_terminal(chats, "source")
        if source_idx == -1:
            return None

        destination_idx = await self.list_chats_terminal(chats, "destination")
        if destination_idx == -1:
            return None

        keyword_choice = await self.show_options(
            "Filter files by keyword (caption/filename text)?",
            [
                {"name": "No - forward all files/images", "value": "none"},
                {"name": "Yes - only files matching a keyword", "value": "keyword"},
            ],
        )
        keyword = None
        if keyword_choice == "keyword":
            keyword_value = await self._get_text_input("Enter keyword to search for:")
            keyword = keyword_value.strip() if keyword_value else None

        start_date, end_date = await self._get_date_filter_selection()
        timezone_name = await self._get_timezone_selection()
        dry_run = await self._get_dry_run_selection()

        return {
            "source_id": chats[source_idx].id,
            "destination_id": chats[destination_idx].id,
            "keyword": keyword,
            "start_date": start_date,
            "end_date": end_date,
            "timezone_name": timezone_name,
            "dry_run": dry_run,
        }
