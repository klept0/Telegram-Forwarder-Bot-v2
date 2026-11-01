import argparse
import asyncio
import os
import signal
import sys

from source.core.Bot import Bot
from source.core.Telegram import HeadlessStartupError
from source.utils.Console import Terminal
from source.utils.Constants import (
    SESSION_FOLDER_PATH,
    RESOURCE_FILE_PATH,
    MEDIA_FOLDER_PATH,
)

console = Terminal.console


async def run(live: bool = False, account: str | None = None) -> None:
    # SIGINT already cancels this task under asyncio.run(); make SIGTERM
    # (e.g. `docker stop`) do the same so the menu's cleanup (disconnecting
    # the Telegram client) still runs instead of the process being killed.
    task = asyncio.current_task()
    if sys.platform != "win32" and task is not None:
        asyncio.get_running_loop().add_signal_handler(signal.SIGTERM, task.cancel)
    if live:
        await Bot().start_live(account)
    else:
        await Bot().start()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Telegram Forwarder Bot")
    parser.add_argument(
        "--live",
        action="store_true",
        help="start Live Forward without prompts (for startup tasks)",
    )
    parser.add_argument(
        "--account",
        metavar="PHONE",
        help="account phone number to use with --live",
    )
    args = parser.parse_args(argv)
    if args.account and not args.live:
        parser.error("--account requires --live")
    return args


def main() -> None:
    args = parse_args()
    os.makedirs(RESOURCE_FILE_PATH, exist_ok=True)
    os.makedirs(MEDIA_FOLDER_PATH, exist_ok=True)
    os.makedirs(SESSION_FOLDER_PATH, exist_ok=True)

    try:
        asyncio.run(run(args.live, args.account))
    except (KeyboardInterrupt, asyncio.CancelledError):
        console.print("[bold yellow]Exiting...[/bold yellow]")
    except HeadlessStartupError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        # 2: permanent, a restart will not fix it. The launcher must not retry.
        if args.live:
            sys.exit(2)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        # 1: possibly transient (e.g. no network at boot), so the launcher retries.
        if args.live:
            sys.exit(1)


if __name__ == "__main__":
    main()
