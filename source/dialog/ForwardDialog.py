from InquirerPy import inquirer

from source.dialog.BaseDialog import BaseDialog
from source.model.ForwardConfig import ForwardConfig
from source.utils.DateUtils import DateUtils


class ForwardDialog(BaseDialog):
    async def get_config(self):
        """Get forward configuration from user.
        
        Returns:
            Dict mapping source chat IDs to their forward configurations
        """
        self.clear()
        return await self._get_forward_config()

    async def _get_forward_config(self):
        """Get forward configuration settings.
        
        Returns:
            Dict mapping source chat IDs to their forward configurations
        """
        forward_config_list = await ForwardConfig.get_all(True)
        config_string = '\n   '.join(
            str(config) for config in forward_config_list
        )

        options = [
            {"name": "Use saved settings.\n   " + config_string, "value": "1"},
            {"name": "New settings", "value": "2"}
        ]

        choice = await self.show_options("Forward Settings:", options)
        if choice == "2":
            forward_config_list = await ForwardConfig.get_all(False)

        # Ask if user wants to filter by date
        date_options = [
            {"name": "No date filter (forward all messages)", "value": "none"},
            {"name": "Filter by specific month", "value": "month"},
            {"name": "Filter by date range", "value": "range"}
        ]

        date_choice = await self.show_options("Date Filtering:", date_options)

        if date_choice != "none":
            for config in forward_config_list:
                if date_choice == "month":
                    start_date, end_date = await self._get_month_selection()
                elif date_choice == "range":
                    start_date, end_date = await self._get_date_range_selection()
                else:
                    start_date, end_date = None, None

                config.start_date = start_date
                config.end_date = end_date

        return {item.sourceID: item for item in forward_config_list}

    async def _get_month_selection(self):
        """Get month and year selection from user.

        Returns:
            Tuple of (start_date_str, end_date_str)
        """
        # Get year
        current_year = DateUtils.get_current_month_range()[0].year
        years = [str(y) for y in range(current_year - 5, current_year + 2)]
        year_choice = await self.show_options(
            "Select Year:",
            [{"name": year, "value": year} for year in years]
        )

        # Get month
        months = [
            {"name": f"{i:02d} - {m}", "value": str(i)}
            for i, m in enumerate([
                "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October",
                "November", "December"
            ], 1)
        ]
        month_choice = await self.show_options("Select Month:", months)

        # Calculate date range
        start_date, end_date = DateUtils.get_month_date_range(
            int(year_choice), int(month_choice)
        )

        return (DateUtils.format_date(start_date),
                DateUtils.format_date(end_date))

    async def _get_date_range_selection(self):
        """Get custom date range from user.

        Returns:
            Tuple of (start_date_str, end_date_str)
        """
        # Get start date
        start_date_str = await self._get_date_input(
            "Enter start date (YYYY-MM-DD):"
        )
        if not start_date_str:
            return None, None

        # Get end date
        end_date_str = await self._get_date_input(
            "Enter end date (YYYY-MM-DD):"
        )
        if not end_date_str:
            return None, None

        # Validate date range
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
            if DateUtils.parse_date(date_input):
                return date_input
            else:
                self.console.print(
                    "[bold red]Error:[/bold red] Invalid date format. "
                    "Use YYYY-MM-DD."
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
            return await inquirer.text(message=prompt).execute_async()
        except KeyboardInterrupt:
            return None
