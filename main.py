import asyncio
import os
import signal
import sys

from source.core.Bot import Bot
from source.utils.Console import Terminal
from source.utils.Constants import (
    SESSION_FOLDER_PATH,
    RESOURCE_FILE_PATH,
    MEDIA_FOLDER_PATH,
)

console = Terminal.console


async def run() -> None:
    # SIGINT already cancels this task under asyncio.run(); make SIGTERM
    # (e.g. `docker stop`) do the same so the menu's cleanup (disconnecting
    # the Telegram client) still runs instead of the process being killed.
    task = asyncio.current_task()
    if sys.platform != "win32" and task is not None:
        asyncio.get_running_loop().add_signal_handler(signal.SIGTERM, task.cancel)
    await Bot().start()


def main() -> None:
    os.makedirs(RESOURCE_FILE_PATH, exist_ok=True)
    os.makedirs(MEDIA_FOLDER_PATH, exist_ok=True)
    os.makedirs(SESSION_FOLDER_PATH, exist_ok=True)

    try:
        asyncio.run(run())
    except (KeyboardInterrupt, asyncio.CancelledError):
        console.print("[bold yellow]Exiting...[/bold yellow]")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")


if __name__ == "__main__":
    main()
