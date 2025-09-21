import asyncio
import os
import signal
import sys
from typing import Optional

from source.core.Bot import Bot
from source.utils.Console import Terminal
from source.utils.Constants import (
    SESSION_FOLDER_PATH,
    RESOURCE_FILE_PATH,
    MEDIA_FOLDER_PATH,
)

console = Terminal.console


async def shutdown(
    loop: asyncio.AbstractEventLoop, signal: Optional[signal.Signals] = None
) -> None:
    if signal:
        console.print(f"[bold red]Received exit signal {signal.name}...[/bold red]")
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    console.print(f"[bold yellow]Cancelling {len(tasks)} tasks...[/bold yellow]")
    [task.cancel() for task in tasks]
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()


def main() -> None:
    os.makedirs(RESOURCE_FILE_PATH, exist_ok=True)
    os.makedirs(MEDIA_FOLDER_PATH, exist_ok=True)
    os.makedirs(SESSION_FOLDER_PATH, exist_ok=True)

    bot = Bot()
    loop = None
    try:
        # Modern 3.10+ event loop creation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        if sys.platform != "win32":
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(
                    sig, lambda s=sig: asyncio.create_task(shutdown(loop, signal=s))
                )

        loop.run_until_complete(bot.start())
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
    finally:
        if loop is not None:
            loop.close()


if __name__ == "__main__":
    main()
