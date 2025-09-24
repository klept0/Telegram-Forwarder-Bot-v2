# source/core/Bot.py

from source.menu.AccountSelector import AccountSelector
from source.menu.MainMenu import MainMenu
from source.utils.Console import Terminal

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
        try:
            self.telegram = await self.account_selector.select_account()
            self.main_menu = MainMenu(self.telegram)
            await self.main_menu.start()
        except Exception as err:
            raise err
