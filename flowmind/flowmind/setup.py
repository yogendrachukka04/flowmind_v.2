"""FlowMind setup wizard — interactively collect and save API keys."""

import json
from pathlib import Path

CONFIG_PATH = Path.home() / ".flowmind.json"


def run_setup() -> None:
    print("\nFlowMind Setup\n" + "─" * 30)
    print("Press Enter to skip any key you don't have yet.\n")

    existing: dict = {}
    if CONFIG_PATH.exists():
        try:
            existing = json.loads(CONFIG_PATH.read_text())
            print("Existing config found — press Enter to keep current values.\n")
        except json.JSONDecodeError:
            pass

    def _prompt(label: str, key: str) -> str:
        current = existing.get(key, "")
        hint = f" [{'set' if current else 'not set'}]"
        val = input(f"{label}{hint}: ").strip()
        return val if val else current

    config = {
        "gemini":      _prompt("Gemini API Key    ", "gemini"),
        "openrouter":  _prompt("OpenRouter API Key", "openrouter"),
        "nvidia":      _prompt("NVIDIA API Key    ", "nvidia"),
    }

    # Determine active provider (first one with a key set)
    providers_in_order = ["gemini", "openrouter", "nvidia"]
    active = next((p for p in providers_in_order if config.get(p)), None)
    config["active_provider"] = active or "gemini"

    CONFIG_PATH.write_text(json.dumps(config, indent=2))
    CONFIG_PATH.chmod(0o600)  # owner read/write only

    print(f"\n✓  Configuration saved to {CONFIG_PATH}")
    print(f"✓  Active provider: {config['active_provider']}")
    print("\nRun `flowmind start` to launch the gateway.\n")
