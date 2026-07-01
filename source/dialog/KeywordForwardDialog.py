from InquirerPy import inquirer

from source.dialog.DateRangeDialog import DateRangeDialog
from source.model.Chat import Chat
from source.utils.DateUtils import DateUtils


class KeywordForwardDialog(DateRangeDialog):
    async def get_config(self):
        """Get keyword-forward settings from user input."""
        self.clear()
        chats = Chat.read()

        source_idx = await self.list_chats_terminal(chats, "source")
        if source_idx == -1:
            return None

        destination_idx = await self.list_chats_terminal(chats, "destination")
        if destination_idx == -1:
            return None

        keyword_value = await inquirer.text(
            message="Enter keyword to search for:",
            validate=lambda x: bool(x and x.strip()),
            invalid_message="Keyword cannot be empty",
        ).execute_async()
        keyword = keyword_value.strip() if isinstance(keyword_value, str) else ""

        limit_value = await inquirer.text(
            message="Max messages to scan (1-5000, default 500):",
            default="500",
            validate=lambda x: x.isdigit() and 1 <= int(x) <= 5000,
            invalid_message="Please enter a number between 1 and 5000",
        ).execute_async()
        limit = int(limit_value)

        date_filter = await self.show_options(
            "Apply date filter?",
            [
                {"name": "No", "value": "none"},
                {"name": "Yes", "value": "range"},
            ],
        )

        start_date = None
        end_date = None
        timezone_name = "UTC"
        if date_filter == "range":
            start_date = await self._get_date_input("Enter start date (YYYY-MM-DD):")
            end_date = await self._get_date_input("Enter end date (YYYY-MM-DD):")

            if not DateUtils.validate_date_range(start_date, end_date):
                self.console.print(
                    "[bold red]Error:[/bold red] Start date must be before or equal to end date."
                )
                return await self.get_config()

            timezone_name = await self._get_timezone_selection()

        dry_run = (
            await self.show_options(
                "Dry-run only?",
                [
                    {"name": "No, forward matches", "value": "no"},
                    {"name": "Yes, count only", "value": "yes"},
                ],
            )
            == "yes"
        )

        return {
            "source_id": chats[source_idx].id,
            "destination_id": chats[destination_idx].id,
            "keyword": keyword,
            "limit": limit,
            "start_date": start_date,
            "end_date": end_date,
            "timezone_name": timezone_name,
            "dry_run": dry_run,
        }
