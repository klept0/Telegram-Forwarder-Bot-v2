import json
import os.path

from source.dialog.BaseDialog import BaseDialog
from source.model.Chat import Chat
from source.utils.Constants import FORWARD_CONFIG_FILE_PATH


class ForwardConfig:

    def __init__(self, sourceID=None, sourceName=None, destinationID=None,
                 destinationName=None, start_date=None, end_date=None, **kwargs):
        self.sourceID = sourceID
        self.sourceName = sourceName
        self.destinationID = destinationID
        self.destinationName = destinationName
        self.start_date = start_date  # ISO format date string (YYYY-MM-DD)
        self.end_date = end_date      # ISO format date string (YYYY-MM-DD)

    @staticmethod
    def write(forward_config_list):
        forwardList = []
        for _ in forward_config_list:
            forwardList.append(_.__dict__)
        with open(FORWARD_CONFIG_FILE_PATH, "w") as file:
            json.dump(forwardList, file, indent=4)

    @staticmethod
    def read():
        with open(FORWARD_CONFIG_FILE_PATH) as file:
            data = json.load(file)
            return [ForwardConfig(**forwardConfig) for forwardConfig in data]

    @staticmethod
    async def scan():
        chat = Chat()
        chats = chat.read()
        forwardConfigList = []
        dialog = BaseDialog()

        while True:
            forwardConfig = ForwardConfig()
            sourceChoice = await dialog.list_chats_terminal(chats, "source")
            if sourceChoice == -1:
                break
            source = chats[sourceChoice]
            forwardConfig.sourceID = source.id
            forwardConfig.sourceName = source.title

            destinationChoice = await dialog.list_chats_terminal(chats, "destination")
            destination = chats[destinationChoice]
            forwardConfig.destinationID = destination.id
            forwardConfig.destinationName = destination.title

            forwardConfigList.append(forwardConfig)
        ForwardConfig.write(forwardConfigList)
        return forwardConfigList

    @staticmethod
    async def get_all(is_saved=True):
        if is_saved and os.path.exists(FORWARD_CONFIG_FILE_PATH):
            return ForwardConfig.read()
        else:
            return await ForwardConfig.scan()

    def __repr__(self):
        date_info = ""
        if self.start_date or self.end_date:
            date_parts = []
            if self.start_date:
                date_parts.append(f"from {self.start_date}")
            if self.end_date:
                date_parts.append(f"to {self.end_date}")
            date_info = f" ({' '.join(date_parts)})"
        return f'"{self.sourceName}" → "{self.destinationName}"{date_info}'
