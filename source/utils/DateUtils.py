"""
Date utility functions for Telegram Forwarder Bot.
Provides utilities for date range calculations and month filtering.
"""

from calendar import monthrange
from datetime import date, datetime


class DateUtils:
    """Utility class for date operations and month filtering."""

    @staticmethod
    def get_month_date_range(year: int, month: int) -> tuple[date, date]:
        """Get the start and end dates for a specific month.

        Args:
            year: The year (e.g., 2024)
            month: The month (1-12)

        Returns:
            Tuple of (start_date, end_date) for the month
        """
        start_date = date(year, month, 1)
        _, last_day = monthrange(year, month)
        end_date = date(year, month, last_day)
        return start_date, end_date

    @staticmethod
    def parse_date(date_str: str) -> date | None:
        """Parse a date string in YYYY-MM-DD format.

        Args:
            date_str: Date string in YYYY-MM-DD format

        Returns:
            date object or None if parsing fails
        """
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return None

    @staticmethod
    def format_date(date_obj: date) -> str:
        """Format a date object to YYYY-MM-DD string.

        Args:
            date_obj: Date object to format

        Returns:
            Formatted date string
        """
        return date_obj.strftime("%Y-%m-%d")

    @staticmethod
    def get_current_month_range() -> tuple[date, date]:
        """Get the date range for the current month.

        Returns:
            Tuple of (start_date, end_date) for current month
        """
        today = date.today()
        return DateUtils.get_month_date_range(today.year, today.month)

    @staticmethod
    def get_previous_month_range() -> tuple[date, date]:
        """Get the date range for the previous month.

        Returns:
            Tuple of (start_date, end_date) for previous month
        """
        today = date.today()
        year = today.year
        month = today.month - 1
        if month == 0:
            month = 12
            year -= 1
        return DateUtils.get_month_date_range(year, month)

    @staticmethod
    def validate_date_range(start_date: str | None,
                            end_date: str | None) -> bool:
        """Validate that start_date is before or equal to end_date.

        Args:
            start_date: Start date string (YYYY-MM-DD) or None
            end_date: End date string (YYYY-MM-DD) or None

        Returns:
            True if dates are valid, False otherwise
        """
        if not start_date or not end_date:
            return True  # None dates are considered valid

        start = DateUtils.parse_date(start_date)
        end = DateUtils.parse_date(end_date)

        if not start or not end:
            return False

        return start <= end