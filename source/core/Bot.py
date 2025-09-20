# source/core/Bot.py

import asyncio
import os
import signal
import sys

from source.core.Telegram import Telegram
from source.menu.AccountSelector import AccountSelector
from source.menu.MainMenu import MainMenu
from source.utils.Console import Terminal
from source.utils.Constants import SESSION_FOLDER_PATH, RESOURCE_FILE_PATH, MEDIA_FOLDER_PATH

console = Terminal.console

async def shutdown(loop, signal=None):
    if signal:
        console.print(f"[bold yellow]Received exit signal {signal.name}...[/bold yellow]")
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    console.print(f"[bold yellow]Cancelling {len(tasks)} tasks...[/bold yellow]")
    [task.cancel() for task in tasks]
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()

def main():
    os.makedirs(RESOURCE_FILE_PATH, exist_ok=True)
    os.makedirs(MEDIA_FOLDER_PATH, exist_ok=True)
    os.makedirs(SESSION_FOLDER_PATH, exist_ok=True)
    
    bot = Bot()
    try:
        loop = asyncio.get_event_loop()
        if sys.platform != 'win32':
            signals = (signal.SIGINT, signal.SIGTERM)
            for s in signals:
                loop.add_signal_handler(s, lambda a=s: asyncio.create_task(shutdown(loop, signal=s)))
        loop.run_until_complete(bot.start())
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
    finally:
        loop.close()

class Bot:
    def __init__(self):
        self.account_selector = AccountSelector()
        self.main_menu = None
        self.telegram = None

    async def start(self):
        try:
            self.telegram = await self.account_selector.select_account()
            self.main_menu = MainMenu(self.telegram)
            await self.main_menu.start()
        except Exception as err:
            raise err

if __name__ == "__main__":
    main()
