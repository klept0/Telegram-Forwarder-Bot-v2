from source.dialog.DateRangeDialog import DateRangeDialog
from source.model.ForwardConfig import ForwardConfig


class ForwardDialog(DateRangeDialog):
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
        config_string = "\n   ".join(str(config) for config in forward_config_list)

        options = [
            {"name": "Use saved settings.\n   " + config_string, "value": "1"},
            {"name": "New settings", "value": "2"},
        ]

        choice = await self.show_options("Forward Settings:", options)
        if choice == "2":
            forward_config_list = await ForwardConfig.get_all(False)

        date_options = [
            {"name": "No date filter (forward all messages)", "value": "none"},
            {"name": "Filter by specific month", "value": "month"},
            {"name": "Filter by multiple months", "value": "multi_month"},
            {"name": "Filter by date range", "value": "range"},
        ]

        date_choice = await self.show_options("Date Filtering:", date_options)

        if date_choice != "none":
            timezone_name = await self._get_timezone_selection()
            dry_run = await self._get_dry_run_selection()
            for config in forward_config_list:
                if date_choice == "month":
                    start_date, end_date = await self._get_month_selection()
                elif date_choice == "multi_month":
                    start_date, end_date = await self._get_multi_month_selection()
                elif date_choice == "range":
                    start_date, end_date = await self._get_date_range_selection()
                else:
                    start_date, end_date = None, None

                config.start_date = start_date
                config.end_date = end_date
                config.timezone_name = timezone_name
                config.dry_run = dry_run
        else:
            for config in forward_config_list:
                config.timezone_name = "UTC"
                config.dry_run = False

        return {item.sourceID: item for item in forward_config_list}
