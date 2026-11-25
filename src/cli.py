"""Run the stdio server, or configure a read-only account from a terminal."""

import argparse
import getpass
import json
import os
import sys
import tempfile
import warnings
from pathlib import Path

from .config import CONFIG_KEYS


def default_config() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "trading212-mcp" / "accounts.toml"


def server_settings() -> dict[str, str]:
    settings = {name: os.environ[name] for name in CONFIG_KEYS if name in os.environ}
    if not settings:
        path = default_config()
        if path.is_file():
            settings["T212_CONFIG_FILE"] = str(path)
    return settings


def save_account(path: Path, environment: str, key: str, secret: str) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    # Link the completed owner-only file into place. Concurrent setup runs cannot
    # overwrite an account or leave half-written credentials at the final path.
    fd, temp_name = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as target:
            target.write(
                f"[trading]\nT212_ENV = {json.dumps(environment)}\n"
                f"T212_API_KEY = {json.dumps(key, ensure_ascii=False)}\n"
                f"T212_API_SECRET = {json.dumps(secret, ensure_ascii=False)}\n"
                "T212_ENABLE_WRITES = false\n"
            )
        os.link(temp_name, path)
    finally:
        Path(temp_name).unlink(missing_ok=True)


def setup() -> None:
    path = default_config()
    if path.exists():
        print(
            f"Your existing settings are at {path}. Edit that file to change accounts."
        )
        return
    if not sys.stdin.isatty():
        raise SystemExit(
            "Run setup in an interactive terminal to enter your keys privately."
        )

    print("Use a Trading 212 key with Account data and Portfolio read permissions.")
    environment = input("Account environment [demo/live]: ").strip().lower()
    if environment not in {"demo", "live"}:
        raise SystemExit("Choose demo or live. Setup did not save an account.")
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        key = getpass.getpass("API key (hidden): ").strip()
        secret = getpass.getpass("API secret (hidden): ").strip()
    if not key or not secret:
        raise SystemExit("Both credentials are required.")
    save_account(path, environment, key, secret)
    print(f"Saved your read-only {environment} configuration at {path}.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", nargs="?", choices=["setup"], help="set up your account"
    )
    if parser.parse_args().command == "setup":
        try:
            setup()
        except (EOFError, KeyboardInterrupt, getpass.GetPassWarning):
            raise SystemExit("Setup cancelled.") from None
        except OSError as exc:
            raise SystemExit(f"Could not create settings: {exc.strerror}.") from None
        return

    from .server import main as serve

    serve(server_settings())
