from InquirerPy import inquirer

from source.dialog.BaseDialog import BaseDialog
from source.model.Chat import Chat
from source.service.PhraseWatcher import PhraseWatcher


class PhraseWatchDialog(BaseDialog):
    """Gathers settings for logging a chat's phrase matches to a file."""

    async def get_config(self):
        """Returns a dict of PhraseWatcher arguments, or None if cancelled."""
        self.clear()
        chats = Chat.read()

        chat_idx = await self.list_chats_terminal(chats, "watch")
        if chat_idx == -1:
            return None
        chat = chats[chat_idx]

        phrase = await inquirer.text(
            message="Phrase to watch for (case-insensitive):",
            validate=lambda x: bool(x.strip()),
            invalid_message="Phrase cannot be empty",
        ).execute_async()

        output_path = await inquirer.text(
            message="Append matches to file:",
            default=PhraseWatcher.default_output_path(chat.title, chat.id),
            validate=lambda x: bool(x.strip()),
            invalid_message="File path cannot be empty",
        ).execute_async()

        return {
            "chat_id": chat.id,
            "chat_title": chat.title,
            "chat_username": chat.username,
            "phrase": phrase.strip(),
            "output_path": output_path.strip(),
        }
