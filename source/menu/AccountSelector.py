from InquirerPy import inquirer

from source.core.Telegram import Telegram
from source.model.Credentials import Credentials
from source.utils.Console import Terminal


class AccountSelector:
    def __init__(self):
        self.console = Terminal.console

    async def select_account(self):
        credentials_list = Credentials.get_all()

        if not credentials_list:
            self.console.print(
                "[bold red]No credentials found. Please add credentials first.[/bold red]"
            )
            return await self._add_account()

        choices = [
            {"name": f"Account: {cred.phone_number}", "value": cred}
            for cred in credentials_list
        ]

        choices.append({"name": "➕ Add New Account", "value": "new"})

        selected = await inquirer.select(
            message="Select account to use:", choices=choices
        ).execute_async()

        if selected == "new":
            return await self._add_account()

        return await Telegram.create(selected)

    @staticmethod
    async def _add_account():
        credentials = await Credentials.prompt()
        telegram = await Telegram.create(credentials)
        # Saved only after the login worked.
        credentials.save()
        return telegram
