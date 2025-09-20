"""Unit tests for the Bot class."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from source.core.Bot import Bot


class TestBot:
    """Test cases for the Bot class."""

    @pytest.mark.asyncio
    async def test_bot_initialization(self):
        """Test that Bot initializes correctly."""
        bot = Bot()

        assert bot.account_selector is not None
        assert bot.main_menu is None
        assert bot.telegram is None
        assert bot.status == "Idle"

    @pytest.mark.asyncio
    async def test_bot_start_success(self, mock_telegram_client):
        """Test successful bot startup."""
        bot = Bot()

        with patch("source.core.Bot.AccountSelector") as mock_selector_cls, \
             patch("source.core.Bot.MainMenu") as mock_menu_cls:

            # Setup mocks
            mock_selector = MagicMock()
            mock_selector.select_account = AsyncMock(
                return_value=mock_telegram_client
            )
            mock_selector_cls.return_value = mock_selector

            mock_menu = MagicMock()
            mock_menu.start = AsyncMock()
            mock_menu_cls.return_value = mock_menu

            # Execute
            await bot.start()

            # Verify
            mock_selector.select_account.assert_called_once()
            mock_menu_cls.assert_called_once_with(mock_telegram_client)
            mock_menu.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_bot_start_with_exception(self):
        """Test bot startup with exception handling."""
        bot = Bot()

        with patch("source.core.Bot.AccountSelector") as mock_selector_cls:
            mock_selector = MagicMock()
            mock_selector.select_account = AsyncMock(
                side_effect=Exception("Test error")
            )
            mock_selector_cls.return_value = mock_selector

            # Should raise the exception
            with pytest.raises(Exception, match="Test error"):
                await bot.start()

    def test_bot_status_property(self):
        """Test bot status property."""
        bot = Bot()
        assert bot.status == "Idle"

        # Status should be read-only
        with pytest.raises(AttributeError):
            bot.status = "Running"
