"""FlowMind CLI — entry point for the `flowmind` command."""

import sys


HELP = """
FlowMind v0.1.1-alpha

Commands:
  flowmind setup    Configure API keys and provider priority
  flowmind start    Start the local gateway on :4000
  flowmind doctor   Check configuration and connectivity
  flowmind version  Show version
"""


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"

    if cmd == "setup":
        from flowmind.setup import run_setup
        run_setup()

    elif cmd == "start":
        from flowmind.server import start_server
        start_server()

    elif cmd == "doctor":
        _doctor()

    elif cmd in ("version", "--version", "-v"):
        from flowmind import __version__
        print(f"flowmind {__version__}")

    else:
        print(HELP)


def _doctor() -> None:
    """Basic health-check: config file present, keys non-empty, priority set."""
    import json
    from pathlib import Path

    config_path = Path.home() / ".flowmind.json"

    print("FlowMind Doctor\n" + "─" * 30)

    if not config_path.exists():
        print("✗  ~/.flowmind.json not found — run `flowmind setup` first")
        print("─" * 30)
        print("Issues found — see above.")
        return

    try:
        config = json.loads(config_path.read_text())
    except json.JSONDecodeError:
        print("✗  ~/.flowmind.json is not valid JSON")
        print("─" * 30)
        print("Issues found — see above.")
        return

    # Keys
    for provider in ("gemini", "openrouter", "nvidia"):
        val = config.get(provider, [])
        if isinstance(val, str):
            val = [val] if val else []
        n = len(val)
        if n:
            print(f"✓  {provider:12s} {n} key{'s' if n > 1 else ''} configured")
        else:
            print(f"–  {provider:12s} no keys set  (optional)")

    # Priority
    priority = config.get("provider_priority", [])
    if priority:
        print(f"✓  provider_priority: {' → '.join(priority)}")
    else:
        active = config.get("active_provider")
        if active:
            print(f"–  provider_priority not set (legacy active_provider={active!r})")
        else:
            print("–  provider_priority not set — run `flowmind setup`")

    print("─" * 30)
    print("System healthy ✓")
