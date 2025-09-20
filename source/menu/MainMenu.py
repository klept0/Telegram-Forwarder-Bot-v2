from InquirerPy import inquirer
from source.utils.Console import Terminal
from source.model.Credentials import Credentials
from source.core.Telegram import Telegram
from source.dialog.ForwardDialog import ForwardDialog
from source.dialog.DeleteDialog import DeleteDialog
from source.dialog.FindUserDialog import FindUserDialog
from source.menu.AccountSelector import AccountSelector
import asyncio

class MainMenu:
    def __init__(self, telegram):
        self.console = Terminal.console
        self.telegram = telegram
        self.menu_options = self._init_menu_options()
        self.forward_dialog = ForwardDialog()
        self.delete_dialog = DeleteDialog()
        self.find_user_dialog = FindUserDialog()
        self._status_task = None
        self.status = "Idle"

    def _init_menu_options(self):
        return [
            {"name": "Add/Update Credentials", "value": "1", "handler": self.update_credentials},
            {"name": "List Chats", "value": "2", "handler": self.list_chats},
            {"name": "Delete My Messages", "value": "3", "handler": self.delete_messages},
            {"name": "Find User Messages", "value": "4", "handler": self.find_user},
            {"name": "Live Forward Messages", "value": "5", "handler": self.live_forward},
            {"name": "Past Forward Messages", "value": "6", "handler": self.past_forward},
            {"name": "Switch Account", "value": "7", "handler": self.switch_account},
            {"name": "Exit", "value": "0", "handler": None}
        ]

    async def _get_menu_choice(self):
        # Display queue status
        queue_status = self._get_queue_status()
        self.console.print(f"[bold green]Status:[/] {self.status} | Queue: {queue_status['queue_length']} | Current: {queue_status['current_task']}\n")
        choices = [{"name": opt["name"], "value": opt["value"]} for opt in self.menu_options]
        return await inquirer.select(message="Menu:", choices=choices).execute_async()

    def _get_queue_status(self):
        if hasattr(self.telegram, "queue") and self.telegram.queue:
            return {
                "queue_length": self.telegram.queue.qsize(),
                "current_task": str(self.telegram.queue.current_task) if self.telegram.queue.current_task else "None"
            }
        return {"queue_length": 0, "current_task": "None"}

    async def _status_updater(self):
        while True:
            await asyncio.sleep(1)
            # Optionally, you could refresh status in console here
            # For simplicity, we just update internal status variable
            if hasattr(self.telegram, "queue") and self.telegram.queue:
                self.status = "Processing" if self.telegram.queue.qsize() > 0 else "Idle"

    async def start(self):
        try:
            # Start background status updater
            self._status_task = asyncio.create_task(self._status_updater())
            while True:
                choice = await self._get_menu_choice()
                if choice == "0":
                    self.console.print("[bold red]Exiting...[/bold red]")
                    break

                handler = next(opt["handler"] for opt in self.menu_options if opt["value"] == choice)
                if handler:
                    await handler()
                else:
                    self.console.print("[bold red]Invalid choice[/bold red]")
        finally:
            if self._status_task:
                self._status_task.cancel()
            if self.telegram:
                await self._cleanup()

    async def _cleanup(self):
        if self.telegram:
            await self.telegram.disconnect()

    async def update_credentials(self):
        self.console.clear()
        await self.telegram.disconnect()
        credentials = await Credentials.get(False)
        self.telegram = await Telegram.create(credentials)

    async def list_chats(self):
        self.console.clear()
        await self.telegram.list_chats()

    async def live_forward(self):
        config = await self.forward_dialog.get_config()
        self.status = f"Live forwarding from {config}"
        await self.telegram.start_forward_live(config)
        self.status = "Idle"

    async def past_forward(self):
        config = await self.forward_dialog.get_config()
        self.status = f"Forwarding past messages from {config}"
        await self.telegram.past_forward(config)
        self.status = "Idle"

    async def delete_messages(self):
        ignore_chats = await self.delete_dialog.get_config()
        self.status = f"Deleting messages..."
        await self.telegram.delete(ignore_chats)
        self.status = "Idle"

    async def find_user(self):
        config = await self.find_user_dialog.get_config()
        self.status = f"Searching for user..."
        await self.telegram.find_user(config)
        self.status = "Idle"

    async def switch_account(self):
        await self._cleanup()
        selector = AccountSelector()
        self.telegram = await selector.select_account()
