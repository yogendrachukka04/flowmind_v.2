"""FlowMind CLI — entry point for the `flowmind` command."""

import sys


HELP = """
FlowMind v0.1.0-alpha

Commands:
  flowmind setup    Configure API keys
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
    """Basic health-check: config file present, keys non-empty."""
    import json
    from pathlib import Path

    config_path = Path.home() / ".flowmind.json"
    ok = True

    print("FlowMind Doctor\n" + "─" * 30)

    if not config_path.exists():
        print("✗  ~/.flowmind.json not found — run `flowmind setup` first")
        ok = False
    else:
        try:
            cfg = json.loads(config_path.read_text())
        except json.JSONDecodeError:
            print("✗  ~/.flowmind.json is not valid JSON")
            ok = False
        else:
            for key in ("gemini", "openrouter", "nvidia"):
                val = cfg.get(key, "")
                if val and val != "":
                    print(f"✓  {key:12s} key present")
                else:
                    print(f"–  {key:12s} key not set  (optional)")

    print("─" * 30)
    if ok:
        print("System healthy ✓")
    else:
        print("Issues found — see above.")
