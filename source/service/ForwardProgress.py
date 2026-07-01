"""Shared resumable-progress tracking used by historical, media, and
keyword forwards, so re-running the same source/date-range/mode picks up
after whatever was already forwarded instead of duplicating it."""

import json
import os
from datetime import datetime

from source.utils.Constants import FORWARD_PROGRESS_FILE_PATH


class ForwardProgress:
    @staticmethod
    def key(
        source: int,
        start_date: str | None = None,
        end_date: str | None = None,
        media_only: bool = False,
        keyword: str | None = None,
    ) -> str:
        start_value = start_date or "none"
        end_value = end_date or "none"
        progress_key = f"{source}|{start_value}|{end_value}"
        # Keep the plain "forward everything" key format unchanged so
        # existing forward_progress.json entries keep resolving; media
        # and/or keyword-scoped runs get a distinct suffix so they track
        # separately from a plain history run over the same date range.
        if media_only:
            progress_key += "|media"
        if keyword:
            progress_key += f"|kw:{keyword.lower()}"
        return progress_key

    @staticmethod
    def load(
        source: int,
        start_date: str | None = None,
        end_date: str | None = None,
        media_only: bool = False,
        keyword: str | None = None,
    ) -> int:
        """Resumes from the last processed message ID regardless of whether
        the prior run finished ("completed") or was interrupted
        ("in_progress"): re-running the same source/date-range/mode should
        pick up after whatever was already forwarded, not re-forward it,
        since Telegram message IDs are never reused.

        Returns:
            Last processed message ID, or 0 if no progress saved.
        """
        progress_file = FORWARD_PROGRESS_FILE_PATH
        progress_key = ForwardProgress.key(
            source, start_date, end_date, media_only, keyword
        )

        if not os.path.exists(progress_file):
            return 0

        try:
            with open(progress_file, encoding="utf-8") as f:
                progress_data = json.load(f)

            chat_progress = progress_data.get(progress_key)
            if chat_progress and chat_progress.get("status") in (
                "in_progress",
                "completed",
            ):
                return chat_progress.get("last_message_id", 0)

            # Backward compatibility: older progress files keyed only by source id.
            legacy_progress = progress_data.get(str(source))
            if legacy_progress and legacy_progress.get("status") in (
                "in_progress",
                "completed",
            ):
                return legacy_progress.get("last_message_id", 0)

        except (json.JSONDecodeError, OSError, KeyError):
            pass

        return 0

    @staticmethod
    def save(
        source: int,
        last_message_id: int,
        start_date: str | None = None,
        end_date: str | None = None,
        media_only: bool = False,
        keyword: str | None = None,
    ) -> bool:
        """Persist progress for this chat/range/mode. Returns True on success."""
        progress_file = FORWARD_PROGRESS_FILE_PATH
        progress_key = ForwardProgress.key(
            source, start_date, end_date, media_only, keyword
        )

        progress_data = {}
        if os.path.exists(progress_file):
            try:
                with open(progress_file, encoding="utf-8") as f:
                    progress_data = json.load(f)
            except (json.JSONDecodeError, OSError):
                progress_data = {}

        progress_data[progress_key] = {
            "source": source,
            "start_date": start_date,
            "end_date": end_date,
            "last_message_id": last_message_id,
            "timestamp": datetime.now().isoformat(),
            "status": "in_progress",
        }

        try:
            with open(progress_file, "w", encoding="utf-8") as f:
                json.dump(progress_data, f, indent=2)
            return True
        except OSError:
            return False

    @staticmethod
    def mark_completed(
        source: int,
        start_date: str | None = None,
        end_date: str | None = None,
        media_only: bool = False,
        keyword: str | None = None,
    ) -> None:
        progress_file = FORWARD_PROGRESS_FILE_PATH
        progress_key = ForwardProgress.key(
            source, start_date, end_date, media_only, keyword
        )

        progress_data = {}
        if os.path.exists(progress_file):
            try:
                with open(progress_file, encoding="utf-8") as f:
                    progress_data = json.load(f)
            except (json.JSONDecodeError, OSError):
                progress_data = {}

        if progress_key in progress_data:
            progress_data[progress_key]["status"] = "completed"
            progress_data[progress_key]["completed_at"] = datetime.now().isoformat()

            try:
                with open(progress_file, "w", encoding="utf-8") as f:
                    json.dump(progress_data, f, indent=2)
            except OSError:
                pass  # Ignore save errors for completion marking

    @staticmethod
    def clear() -> bool:
        """Delete the persisted forward progress file. Returns True if a file existed."""
        progress_file = FORWARD_PROGRESS_FILE_PATH
        if not os.path.exists(progress_file):
            return False

        os.remove(progress_file)
        return True
