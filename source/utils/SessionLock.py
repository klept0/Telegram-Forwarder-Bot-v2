"""Cross-process lock so only one process uses a Telegram session at a time.

Telethon keeps the session in an SQLite file. Two processes on the same
session (e.g. `main.py --live` and the web dashboard, or the two Docker
Compose services sharing ./sessions) fail with "database is locked" and
compete for the same updates, so the second one is refused up front.
"""

import os


class SessionInUseError(RuntimeError):
    """Another process already holds this Telegram session."""


class SessionLock:
    def __init__(self, path: str):
        self.path = path
        self._file = None

    def acquire(self) -> None:
        if self._file is not None:
            return
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        lock_file = open(self.path, "a+")
        try:
            lock_file.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            lock_file.close()
            raise SessionInUseError(
                "This Telegram session is already in use by another process "
                "(the live forwarder, the menu or the web dashboard). Stop it "
                "first; only one can use an account at a time."
            ) from None
        self._file = lock_file

    def release(self) -> None:
        # The OS also drops the lock if the process dies without calling this.
        if self._file is None:
            return
        try:
            if os.name == "nt":
                import msvcrt

                self._file.seek(0)
                msvcrt.locking(self._file.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
        finally:
            self._file.close()
            self._file = None
