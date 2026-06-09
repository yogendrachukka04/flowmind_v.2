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


def get_keys(provider: str) -> list[str]:
    """Return list of API keys for *provider* (supports multi-key)."""
    config = load()
    val = config.get(provider, [])
    if isinstance(val, str):
        return [val] if val else []
    return [k for k in val if k]


def get_key(provider: str) -> Optional[str]:
    """Return the first API key for *provider*, or None."""
    keys = get_keys(provider)
    return keys[0] if keys else None


def get_provider_priority() -> list[str]:
    """Return ordered list of providers to try."""
    config = load()
    priority = config.get("provider_priority", [])
    if not priority:
        # legacy fallback: use active_provider
        active = config.get("active_provider", "gemini")
        return [active]
    return priority
