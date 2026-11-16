"""Load optional API keys from a project .env file."""
import os
from pathlib import Path


def load_env(path):
    """Set missing environment variables from KEY=VALUE lines.

    Existing process environment values win, so a shell export is left as-is.
    """
    file_path = Path(path)
    if not file_path.is_file():
        return
    for raw in file_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
