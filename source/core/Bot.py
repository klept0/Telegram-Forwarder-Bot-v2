# source/core/Bot.py

import os

from source.core.Telegram import HeadlessStartupError, Telegram
from source.menu.AccountSelector import AccountSelector
from source.menu.MainMenu import MainMenu
from source.model.Credentials import Credentials
from source.model.ForwardConfig import ForwardConfig
from source.utils.Console import Terminal
from source.utils.Constants import FORWARD_CONFIG_FILE_PATH

console = Terminal.console


class Bot:
    def __init__(self):
        self.account_selector = AccountSelector()
        self.main_menu = None
        self.telegram = None
        self._status = "Idle"

    @property
    def status(self):
        """Get the current bot status."""
        return self._status

    async def start(self):
        self.telegram = await self.account_selector.select_account()
        self.main_menu = MainMenu(self.telegram)
        await self.main_menu.start()

    async def start_live(self, account: str | None = None) -> None:
        """Start Live Forward without any prompts (for `main.py --live`).

        Uses the saved session and the saved Live Forward settings. Raises
        HeadlessStartupError when a human has to fix something first.
        """
        credentials_list = Credentials.get_all()
        if not credentials_list:
            raise HeadlessStartupError(
                "No credentials found. Run `python main.py` once to add an account."
            )

        if account is not None:
            matches = [c for c in credentials_list if c.phone_number == account]
            if not matches:
                known = ", ".join(c.phone_number for c in credentials_list)
                raise HeadlessStartupError(
                    f"Account {account} was not found. Known accounts: {known}"
                )
            credentials = matches[0]
        elif len(credentials_list) > 1:
            raise HeadlessStartupError(
                "Multiple accounts found. Pass --account PHONE to choose one."
            )
        else:
            credentials = credentials_list[0]

        # Read the saved file directly: ForwardConfig.get_all() can prompt.
        if not os.path.exists(FORWARD_CONFIG_FILE_PATH):
            raise HeadlessStartupError(
                "No saved Live Forward settings. Run Live Forward once from "
                "`python main.py` and save the settings."
            )
        configs = ForwardConfig.read()
        if not configs:
            raise HeadlessStartupError(
                "No saved Live Forward settings. Run Live Forward once from "
                "`python main.py` and save the settings."
            )

        # Same defaults as the "No date filter" branch in ForwardDialog.
        for config in configs:
            config.timezone_name = "UTC"
            config.dry_run = False
        # Skip configs switched off from the web dashboard, as the menu does.
        config_map = {item.sourceID: item for item in configs if item.enabled}
        if not config_map:
            raise HeadlessStartupError(
                "All saved Live Forward settings are disabled. Enable one from "
                "the web dashboard or the menu."
            )

        self.telegram = Telegram(credentials)
        try:
            await self.telegram.connect(interactive=False)
            for config in config_map.values():
                console.print(str(config), markup=False)
            await self.telegram.start_forward_live(config_map)
            # start_forward_live only returns when the connection is lost.
            raise ConnectionError("Disconnected from Telegram")
        finally:
            await self.telegram.disconnect()
