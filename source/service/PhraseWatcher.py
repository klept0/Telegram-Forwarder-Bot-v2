"""Watch a chat live and append every message containing a phrase to a
Markdown file."""

import os
import re
from datetime import timezone

from telethon import TelegramClient, events
from telethon.tl.custom import Message
from telethon.utils import get_display_name

from source.utils.Console import Terminal
from source.utils.Constants import PHRASE_LOG_FOLDER_PATH

console = Terminal.console


class PhraseWatcher:
    def __init__(
        self,
        client: TelegramClient,
        chat_id: int,
        phrase: str,
        output_path: str,
        chat_title: str | None = None,
        chat_username: str | None = None,
    ):
        self.client = client
        self.chat_id = chat_id
        self.phrase = phrase
        self.output_path = output_path
        self.chat_title = chat_title or str(chat_id)
        self.chat_username = chat_username

    @staticmethod
    def default_output_path(chat_title: str | None, chat_id: int) -> str:
        slug = re.sub(r"[^A-Za-z0-9]+", "_", chat_title or "").strip("_").lower()
        return os.path.join(PHRASE_LOG_FOLDER_PATH, f"phrase_{slug or chat_id}.md")

    def matches(self, text: str | None) -> bool:
        """Case-insensitive substring match, like the keyword filters."""
        return self.phrase.lower() in (text or "").lower()

    def add_events(self) -> None:
        self.client.add_event_handler(
            self.message_handler, events.NewMessage(chats=[self.chat_id])
        )

    async def message_handler(self, event: events.NewMessage.Event) -> None:
        try:
            message = event.message
            if not self.matches(message.message):
                return
            sender = await event.get_sender()
            self.append_entry(message, get_display_name(sender) if sender else None)
            console.print(
                f"[bold green]Logged message {message.id} to {self.output_path}[/bold green]"
            )
        except Exception as e:
            console.print(f"[bold red]Error logging message:[/bold red] {e}")

    def append_entry(self, message: Message, sender_name: str | None) -> None:
        directory = os.path.dirname(self.output_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        is_new = (
            not os.path.exists(self.output_path)
            or os.path.getsize(self.output_path) == 0
        )
        with open(self.output_path, "a", encoding="utf-8") as f:
            if is_new:
                f.write(
                    f'# Messages containing "{self.phrase}" in {self.chat_title}\n\n'
                )
            f.write(self.format_entry(message, sender_name))

    def format_entry(self, message: Message, sender_name: str | None) -> str:
        date = message.date
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        stamp = date.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        meta = []
        # In channels the sender is the channel itself; only name real people.
        if sender_name and sender_name != self.chat_title:
            meta.append(f"**From:** {sender_name}")
        link = self.message_link(message)
        if link:
            meta.append(f"[Open in Telegram]({link})")

        lines = [f"## {stamp}", ""]
        if meta:
            lines += [" · ".join(meta), ""]
        lines.append(self._quote(message.message or ""))
        return "\n".join(lines) + "\n\n"

    @staticmethod
    def _quote(text: str) -> str:
        """Blockquote the message, keeping its line breaks.

        Markdown joins consecutive `>` lines into one paragraph, so a
        multi-line post (e.g. one schedule entry per line) would render as a
        single run-on line. Two trailing spaces are Markdown's hard line
        break and stay invisible when the file is read as plain text.
        """
        quoted = [f"> {line}".rstrip() for line in text.splitlines()]
        return "\n".join(
            line + "  " if line != ">" and nxt != ">" else line
            for line, nxt in zip(quoted, quoted[1:] + [">"])
        )

    def message_link(self, message: Message) -> str | None:
        if self.chat_username:
            return f"https://t.me/{self.chat_username}/{message.id}"
        channel_id = getattr(message.peer_id, "channel_id", None)
        if isinstance(channel_id, int):
            return f"https://t.me/c/{channel_id}/{message.id}"
        return None
