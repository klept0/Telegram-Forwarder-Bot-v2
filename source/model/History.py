import json

from source.utils.Constants import HISTORY_FILE_PATH
from source.utils.FileUtils import write_json_atomic


class History:
    def __init__(self):
        self.message_map = self.load_data()

    def convert_to_json_format(self, data):
        return [
            {
                "source": {"id": source_id, "message_id": source_msg_id},
                "destination": {"id": dest_id, "message_id": dest_msg_id},
            }
            for (source_id, source_msg_id, dest_id), dest_msg_id in data.items()
        ]

    def convert_from_json_format(self, json_data):
        return {
            (
                item["source"]["id"],
                item["source"]["message_id"],
                item["destination"]["id"],
            ): item["destination"]["message_id"]
            for item in json_data
        }

    def save_data(self, data):
        json_data = self.convert_to_json_format(data)
        write_json_atomic(HISTORY_FILE_PATH, json_data, indent=4)

    def load_data(self):
        try:
            with open(HISTORY_FILE_PATH) as file:
                json_data = json.load(file)
                return self.convert_from_json_format(json_data)
        except Exception:
            return {}

    def add_mapping(self, source_id, source_msg_id, dest_id, dest_msg_id):
        self.message_map[(source_id, source_msg_id, dest_id)] = dest_msg_id
        self.save_data(self.message_map)

    def get_mapping(self, source_id, source_msg_id, dest_id):
        return self.message_map.get((source_id, source_msg_id, dest_id))
