"""Run the stdio server, or configure a read-only account from a terminal."""

import argparse
import getpass
import os
import re
import stat
import sys
import tempfile
import warnings
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import tomlkit
from tomlkit.exceptions import TOMLKitError
from tomlkit.items import InlineTable

from .config import CONFIG_KEYS, ConfigError, configured_accounts, read_config


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


def section_name(account: str) -> str:
    if not re.fullmatch(r"[a-z][a-z0-9_-]*", account):
        raise ConfigError(
            "Use an account label starting with a lowercase letter, followed by lowercase letters, digits, underscores or hyphens."
        )
    return "trading" if account == "primary" else f"trading_accounts.{account}"


def existing_profile_message(path: Path, account: str) -> str | None:
    section = section_name(account)
    if not path.is_absolute():
        raise ConfigError("Set T212_CONFIG_FILE to an absolute path.")
    if path.is_symlink():
        raise ConfigError(
            "For setup, select the actual settings file instead of a symbolic link."
        )
    if not path.exists():
        return None
    config = read_config(str(path))
    profiles = config if account == "primary" else config.get("trading_accounts", {})
    if not isinstance(profiles, dict):
        raise ConfigError("Use named TOML sections such as [trading_accounts.isa].")
    label = "trading" if account == "primary" else account
    if label not in profiles:
        return None
    profile = profiles[label]
    fields = ("T212_API_KEY", "T212_API_SECRET")
    if isinstance(profile, dict):
        values = [profile[k] for k in fields if k in profile]
        if not values:
            return None
        if len(values) == 2 and all(isinstance(v, str) for v in values):
            if all(not v.strip() for v in values):
                return None
            if all(v.strip() for v in values):
                return f"Account {account} is already configured in [{section}]."
    return f"The section [{section}] already exists. Edit its T212_ENV, T212_API_KEY and T212_API_SECRET values in the private file."


@contextmanager
def setup_lock(path: Path) -> Iterator[None]:
    lock = path.with_name(path.name + ".setup.lock")
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ConfigError(
            f"Another setup may be saving accounts. Retry when it finishes. If setup was interrupted, remove {lock} after checking no setup is active."
        ) from None
    try:
        os.close(fd)
        yield
    finally:
        lock.unlink()


def save_account(
    path: Path, environment: str, key: str, secret: str, account: str = "primary"
) -> None:
    section_name(account)
    if not path.is_absolute():
        raise ConfigError("Set T212_CONFIG_FILE to an absolute path.")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with setup_lock(path):
        try:
            old = path.lstat()
        except FileNotFoundError:
            old = None
        message = existing_profile_message(path, account)
        if message:
            raise ConfigError(message)
        # Decode bytes directly so the text layer cannot normalise existing CRLFs.
        try:
            document = (
                tomlkit.parse(path.read_bytes().decode("utf-8"))
                if old
                else tomlkit.document()
            )
            if account == "primary":
                profile = document.setdefault("trading", tomlkit.table())
            else:
                profiles = document.setdefault("trading_accounts", tomlkit.table())
                blank = (
                    tomlkit.inline_table()
                    if isinstance(profiles, InlineTable)
                    else tomlkit.table()
                )
                profile = profiles.setdefault(account, blank)
            profile.update(
                {
                    "T212_ENV": environment,
                    "T212_API_KEY": key,
                    "T212_API_SECRET": secret,
                    "T212_ENABLE_WRITES": False,
                }
            )
            contents = tomlkit.dumps(document).encode("utf-8")
        except (TOMLKitError, TypeError, ValueError):
            raise ConfigError(
                "Could not safely update this TOML layout. Check the account section in the private file."
            ) from None
        fd, temp_name = tempfile.mkstemp(dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as target:
                target.write(contents)
                target.flush()
                os.fsync(target.fileno())
            configured_accounts({"T212_CONFIG_FILE": temp_name})
            if old:
                current = path.lstat()
                if (
                    not os.path.samestat(old, current)
                    or current.st_mtime_ns != old.st_mtime_ns
                    or current.st_ctime_ns != old.st_ctime_ns
                ):
                    raise ConfigError("Settings changed while saving. Run setup again.")
                if os.name == "posix":
                    os.chmod(temp_name, old.st_mode & stat.S_IRWXU)
                os.replace(temp_name, path)
            else:
                os.link(temp_name, path)
        finally:
            Path(temp_name).unlink(missing_ok=True)


def setup(account: str = "primary") -> None:
    filename = os.environ.get("T212_CONFIG_FILE")
    path = Path(filename) if filename is not None else default_config()
    message = existing_profile_message(path, account)
    if message:
        print(f"{message} Settings are in {path}.")
        return
    if not sys.stdin.isatty():
        raise SystemExit(
            "Run setup in an interactive terminal to enter your keys privately."
        )

    print(
        f"Switch to the Trading 212 account for {account} and use a key with Account data and Portfolio read permissions."
    )
    environment = input("Account environment [demo/live]: ").strip().lower()
    if environment not in {"demo", "live"}:
        raise SystemExit("Choose demo or live. Setup did not save an account.")
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        key = getpass.getpass("API key (hidden): ").strip()
        secret = getpass.getpass("API secret (hidden): ").strip()
    if not key or not secret:
        raise SystemExit("Both credentials are required.")
    save_account(path, environment, key, secret, account)
    print(f"Saved the read-only {account} account ({environment}) at {path}.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command")
    setup_parser = commands.add_parser(
        "setup", help="privately add a read-only account"
    )
    setup_parser.add_argument(
        "--account",
        default="primary",
        metavar="LABEL",
        help="a local label such as primary or isa",
    )
    args = parser.parse_args()
    if args.command == "setup":
        try:
            setup(args.account)
        except (EOFError, KeyboardInterrupt, getpass.GetPassWarning):
            raise SystemExit("Setup cancelled.") from None
        except ValueError as exc:
            raise SystemExit(str(exc)) from None
        except OSError as exc:
            raise SystemExit(f"Could not save settings: {exc.strerror}.") from None
        return

    from .server import main as serve

    serve(server_settings())
