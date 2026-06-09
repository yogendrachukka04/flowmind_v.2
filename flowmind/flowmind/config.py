"""FlowMind config — load ~/.flowmind.json."""

import json
from pathlib import Path
from typing import Optional

CONFIG_PATH = Path.home() / ".flowmind.json"


def load() -> dict:
    """Return config dict, or empty dict if not yet configured."""
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def get_key(provider: str) -> Optional[str]:
    """Return the API key for *provider*, or None."""
    return load().get(provider) or None
