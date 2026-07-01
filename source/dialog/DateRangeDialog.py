from InquirerPy import inquirer

from source.dialog.BaseDialog import BaseDialog
from source.utils.DateUtils import DateUtils


class DateRangeDialog(BaseDialog):
    """Shared date-range/timezone/dry-run prompts used by forwarding dialogs."""

    async def _get_month_selection(self):
        """Get month and year selection from user.

        Returns:
            Tuple of (start_date_str, end_date_str)
        """
        current_year = DateUtils.get_current_month_range()[0].year
        years = [str(y) for y in range(current_year - 5, current_year + 2)]
        year_choice = await self.show_options(
            "Select Year:", [{"name": year, "value": year} for year in years]
        )

        months = [
            {"name": f"{i:02d} - {m}", "value": str(i)}
            for i, m in enumerate(
                [
                    "January",
                    "February",
                    "March",
                    "April",
                    "May",
                    "June",
                    "July",
                    "August",
                    "September",
                    "October",
                    "November",
                    "December",
                ],
                1,
            )
        ]
        month_choice = await self.show_options("Select Month:", months)

        start_date, end_date = DateUtils.get_month_date_range(
            int(year_choice), int(month_choice)
        )

        return (DateUtils.format_date(start_date), DateUtils.format_date(end_date))

    async def _get_multi_month_selection(self):
        """Get multiple month selection from user by selecting start and end months.

        Returns:
            Tuple of (start_date_str, end_date_str) spanning selected month range
        """
        current_year = DateUtils.get_current_month_range()[0].year
        years = [str(y) for y in range(current_year - 5, current_year + 2)]
        year_choice = await self.show_options(
            "Select Year:", [{"name": year, "value": year} for year in years]
        )

        months = [
            {"name": f"{i:02d} - {m}", "value": str(i)}
            for i, m in enumerate(
                [
                    "January",
                    "February",
                    "March",
                    "April",
                    "May",
                    "June",
                    "July",
                    "August",
                    "September",
                    "October",
                    "November",
                    "December",
                ],
                1,
            )
        ]

        start_month_choice = await self.show_options("Select Start Month:", months)
        end_month_choice = await self.show_options("Select End Month:", months)

        start_month = int(start_month_choice)
        end_month = int(end_month_choice)

        if start_month > end_month:
            self.console.print(
                "[bold yellow]Start month is after end month, swapping them[/bold yellow]"
            )
            start_month, end_month = end_month, start_month

        start_date, _ = DateUtils.get_month_date_range(int(year_choice), start_month)
        _, end_date = DateUtils.get_month_date_range(int(year_choice), end_month)

        return (DateUtils.format_date(start_date), DateUtils.format_date(end_date))

    async def _get_date_range_selection(self):
        """Get custom date range from user.

        Returns:
            Tuple of (start_date_str, end_date_str)
        """
        start_date_str = await self._get_date_input("Enter start date (YYYY-MM-DD):")
        if not start_date_str:
            return None, None

        end_date_str = await self._get_date_input("Enter end date (YYYY-MM-DD):")
        if not end_date_str:
            return None, None

        if not DateUtils.validate_date_range(start_date_str, end_date_str):
            self.console.print(
                "[bold red]Error:[/bold red] Start date must be before "
                "or equal to end date."
            )
            return await self._get_date_range_selection()

        return start_date_str, end_date_str

    async def _get_date_input(self, prompt: str) -> str | None:
        """Get date input from user with validation.

        Args:
            prompt: Input prompt message

        Returns:
            Valid date string or None if cancelled
        """
        try:
            date_input = await inquirer.text(message=prompt).execute_async()
            if isinstance(date_input, str) and DateUtils.parse_date(date_input):
                return date_input
            else:
                self.console.print(
                    "[bold red]Error:[/bold red] Invalid date format. Use YYYY-MM-DD."
                )
                return await self._get_date_input(prompt)
        except KeyboardInterrupt:
            return None

    async def _get_text_input(self, prompt: str) -> str | None:
        """Get text input from user.

        Args:
            prompt: Input prompt message

        Returns:
            User input string or None if cancelled
        """
        try:
            text_value = await inquirer.text(message=prompt).execute_async()
            return text_value if isinstance(text_value, str) else None
        except KeyboardInterrupt:
            return None

    async def _get_timezone_selection(self) -> str:
        """Get timezone selection from user.

        Returns:
            IANA timezone name (e.g. UTC, America/New_York)
        """
        timezone_choice = await self.show_options(
            "Timezone for date boundaries:",
            [
                {"name": "UTC (recommended)", "value": "UTC"},
                {"name": "System local timezone", "value": "LOCAL"},
                {"name": "Custom IANA timezone", "value": "CUSTOM"},
            ],
        )

        if timezone_choice == "UTC":
            return "UTC"

        if timezone_choice == "LOCAL":
            return DateUtils.get_local_timezone_name()

        timezone_input = await self._get_text_input(
            "Enter timezone (example: America/New_York):"
        )
        if timezone_input and DateUtils.is_valid_timezone(timezone_input):
            return timezone_input

        self.console.print(
            "[bold red]Error:[/bold red] Invalid timezone. Falling back to UTC."
        )
        return "UTC"

    async def _get_dry_run_selection(self) -> bool:
        """Ask whether to run in count-only preview mode."""
        choice = await self.show_options(
            "Run as dry-run preview?",
            [
                {
                    "name": "No - forward matching messages",
                    "value": "no",
                },
                {
                    "name": "Yes - count matches only (no forwarding)",
                    "value": "yes",
                },
            ],
        )
        return choice == "yes"

    async def _get_date_filter_selection(self):
        """Ask the user to pick a date filtering strategy and return the
        resulting (start_date, end_date) strings, or (None, None) for no filter.
        """
        date_options = [
            {"name": "No date filter (forward all messages)", "value": "none"},
            {"name": "Filter by specific month", "value": "month"},
            {"name": "Filter by multiple months", "value": "multi_month"},
            {"name": "Filter by date range", "value": "range"},
        ]
        date_choice = await self.show_options("Date Filtering:", date_options)

        if date_choice == "month":
            return await self._get_month_selection()
        if date_choice == "multi_month":
            return await self._get_multi_month_selection()
        if date_choice == "range":
            return await self._get_date_range_selection()
        return None, None
