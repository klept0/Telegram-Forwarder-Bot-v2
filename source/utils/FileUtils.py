import json
import os
import tempfile


def write_json_atomic(path: str, data, indent: int = 2) -> None:
    """Write JSON so readers only ever see the old or the new file, never a
    half-written one (e.g. if the process is killed mid-write)."""
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent)
        os.replace(tmp_path, path)
    except BaseException:
        os.unlink(tmp_path)
        raise
