import json
import os

from source.utils.Constants import HISTORY_FILE_PATH
from source.utils.FileUtils import write_json_atomic


class History:
    """Source message → destination message mappings.

    The full map lives in history.json. Rewriting that whole file for every
    forwarded message gets slower as it grows, so new mappings are appended
    to a small log next to it (history.jsonl) and folded into history.json
    the next time the history is loaded.
    """

    def __init__(self):
        self.message_map = self.load_data()

    @staticmethod
    def _log_path():
        # Derived at call time so it follows HISTORY_FILE_PATH.
        return os.path.splitext(HISTORY_FILE_PATH)[0] + ".jsonl"

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
        main_file_ok = True
        try:
            with open(HISTORY_FILE_PATH) as file:
                data = self.convert_from_json_format(json.load(file))
        except FileNotFoundError:
            data = {}
        except Exception:
            data = {}
            main_file_ok = False

        logged = self._read_log()
        data.update(logged)
        # Fold the log into the main file. Skipped when the main file exists
        # but can't be read, so it isn't overwritten with only the log.
        if logged and main_file_ok:
            try:
                self.save_data(data)
                os.remove(self._log_path())
            except OSError:
                pass  # the log is still there; it is folded in next time
        return data

    def _read_log(self):
        entries = {}
        try:
            with open(self._log_path(), encoding="utf-8") as file:
                for line in file:
                    try:
                        source_id, source_msg_id, dest_id, dest_msg_id = json.loads(
                            line
                        )
                    except (ValueError, TypeError):
                        continue  # e.g. a line cut short by a crash mid-write
                    entries[(source_id, source_msg_id, dest_id)] = dest_msg_id
        except OSError:
            pass
        return entries

    def add_mapping(self, source_id, source_msg_id, dest_id, dest_msg_id):
        self.message_map[(source_id, source_msg_id, dest_id)] = dest_msg_id
        log_path = self._log_path()
        directory = os.path.dirname(log_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as file:
            file.write(
                json.dumps([source_id, source_msg_id, dest_id, dest_msg_id]) + "\n"
            )

    def get_mapping(self, source_id, source_msg_id, dest_id):
        return self.message_map.get((source_id, source_msg_id, dest_id))
