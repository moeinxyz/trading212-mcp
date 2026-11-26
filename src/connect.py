"""Connect the local stdio launcher and private account settings to Codex."""

import json
import os
import shutil
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from importlib.metadata import Distribution
from pathlib import Path

from . import cli
from .config import CONFIG_KEYS, ConfigError, configured_accounts

SERVER = "trading212"
LAUNCHER = "trading212-mcp.exe" if os.name == "nt" else "trading212-mcp"
LAUNCHERS = {"trading212-mcp", "moein-trading212-mcp", LAUNCHER, "moein-" + LAUNCHER}


def usable(path: Path) -> bool:
    return path.is_absolute() and path.is_file() and os.access(path, os.X_OK)


def stable_launcher(path: Path) -> bool:
    if os.path.normcase(path.name) not in LAUNCHERS or not usable(path):
        return False
    resolved = path.resolve()
    cache = os.environ.get("UV_CACHE_DIR")
    if cache and (path.is_relative_to(cache) or resolved.is_relative_to(cache)):
        return False
    return not any(
        part.startswith(("archive-v", ".tmp"))
        for part in (*path.parts, *resolved.parts)
    )


def installed_launcher() -> Path:
    override = os.environ.get("T212_MCP_EXECUTABLE")
    if override is not None:
        if stable_launcher(path := Path(override)):
            return path
    else:
        # Prefer the user-facing launcher over its version-specific environment.
        candidates = [
            shutil.which(LAUNCHER),
            Path.home() / ".local" / "bin" / LAUNCHER,
            sys.argv[0],
        ]
        for candidate in filter(None, candidates):
            if stable_launcher(path := Path(candidate)):
                return path
    raise ConfigError(
        "Install trading212-mcp as a persistent tool, then run trading212-mcp connect."
    )


def codex_executable() -> str:
    found = shutil.which("codex")
    if found:
        return found
    if sys.platform == "darwin":
        for directory in [Path("/Applications"), Path.home() / "Applications"]:
            bundled = directory / "Codex.app/Contents/Resources/codex"
            if usable(bundled):
                return str(bundled)
    raise ConfigError(
        "Install Codex or add its CLI to PATH, then run trading212-mcp connect again."
    )


def run_codex(codex: str, *args: str) -> str:
    # Broker credentials are only for the server. Never forward them to the CLI.
    env = {k: v for k, v in os.environ.items() if not k.startswith("T212_")}
    try:
        result = subprocess.run(
            [codex, "mcp", *args],
            capture_output=True,
            encoding="utf-8",
            env=env,
            stdin=subprocess.DEVNULL,
            timeout=30,
            check=True,
        )
    except (OSError, subprocess.SubprocessError, UnicodeError):
        raise ConfigError(
            f"Codex could not complete 'mcp {args[0]}'. Check your Codex configuration and retry."
        ) from None
    return result.stdout


def previous_launcher(path: Path) -> bool:
    """Identify an earlier installation independently of the new launcher's location."""
    if not stable_launcher(path):
        return False
    script = path.resolve()
    venv = script.parent.parent
    if script.parent.name.lower() not in {"bin", "scripts"}:
        return False
    try:
        # A wheel's RECORD names the actual console script the installer created.
        sites = [
            venv / "Lib" / "site-packages",
            *venv.glob("lib/python*/site-packages"),
        ]
        for site in sites:
            for info in site.glob("moein_trading212_mcp-*.dist-info"):
                dist = Distribution.at(info)
                if dist.metadata.get("Name") == "moein-trading212-mcp" and any(
                    entry.name == script.name and entry.locate().resolve() == script
                    for entry in dist.files or ()
                ):
                    return True

        if venv.name == ".venv":
            with (venv.parent / "pyproject.toml").open("rb") as source:
                return (
                    tomllib.load(source).get("project", {}).get("name")
                    == "moein-trading212-mcp"
                )
    except (OSError, ValueError, AttributeError, RecursionError):
        pass
    return False


@dataclass(frozen=True)
class Registration:
    name: str
    config: Path


def find_registration(
    codex: str, launcher: Path, requested: Path | None
) -> Registration | None:
    output = run_codex(codex, "list", "--json")
    try:
        rows = json.loads(output)
    except (ValueError, RecursionError):
        raise ConfigError(
            "Could not read the server list from Codex. Check 'codex mcp list --json'."
        ) from None
    if not isinstance(rows, list) or not all(
        isinstance(r, dict) and isinstance(r.get("name"), str) for r in rows
    ):
        raise ConfigError("Codex returned an unrecognized server list.")
    matches = []
    for row in rows:
        transport = row.get("transport")
        if (
            not row.get("enabled")
            or not isinstance(transport, dict)
            or transport.get("type") != "stdio"
        ):
            continue
        if transport.get("args") or transport.get("env_vars"):
            continue
        env = transport.get("env") or {}
        command = transport.get("command")
        if (
            not isinstance(command, str)
            or os.path.normcase(Path(command).name) not in LAUNCHERS
            or not isinstance(env, dict)
            or env.keys() - {"T212_CONFIG_FILE"}
        ):
            continue
        path = Path(command)
        if os.path.normcase(command) in LAUNCHERS:
            resolved = shutil.which(command)
            if not resolved:
                continue
            path = Path(resolved)
        if not (
            usable(path)
            and (path.resolve() == launcher.resolve() or previous_launcher(path))
        ):
            continue
        filename = env.get("T212_CONFIG_FILE")
        if filename is None:
            config = cli.default_config()
        elif isinstance(filename, str) and Path(filename).is_absolute():
            config = Path(filename)
        else:
            continue
        if requested is None or config.resolve() == requested.resolve():
            matches.append(Registration(row["name"], config))
    if len({r.config.resolve() for r in matches}) > 1:
        raise ConfigError(
            "Several Trading 212 registrations use different files. Select one with T212_CONFIG_FILE."
        )
    if matches:
        return next((r for r in matches if r.name == SERVER), matches[0])
    if any(row["name"] == SERVER for row in rows):
        raise ConfigError(
            "Codex already has a different or disabled 'trading212' server. Inspect it with 'codex mcp get trading212' before connecting."
        )
    return None


def ensure_account(path: Path, account: str | None) -> None:
    stored = configured_accounts(
        {"T212_CONFIG_FILE": str(path)} if path.exists() else {}
    )
    if any(
        api.credentials_configured
        for label, api in stored.items()
        if account is None or label == account
    ):
        return

    # An already-exported pair can be saved privately without typing it again.
    exported = configured_accounts(
        {
            k: os.environ[k]
            for k in CONFIG_KEYS
            if k in os.environ and k != "T212_CONFIG_FILE"
        }
    )
    label = account or next(
        (k for k, api in exported.items() if api.credentials_configured), "primary"
    )
    api = exported.get(label)
    if api and api.credentials_configured:
        if not sys.stdin.isatty() or input(
            f"Save the environment key pair for {label} in the private account file for Codex? [y/N] "
        ).strip().lower() not in {"y", "yes"}:
            raise ConfigError(
                "Connect cancelled. You can also select an existing private file with T212_CONFIG_FILE."
            )
        cli.save_account(path, api.env, api.key, api.secret, label)
    else:
        cli.setup(label, path=path)
    saved = configured_accounts({"T212_CONFIG_FILE": str(path)}).get(label)
    if saved is None or not saved.credentials_configured:
        raise ConfigError(
            "Complete the key pair in the selected account file, then connect again."
        )


def connect(account: str | None = None) -> None:
    if account is not None:
        cli.section_name(account)
    filename = os.environ.get("T212_CONFIG_FILE")
    requested = Path(filename) if filename is not None else None
    if requested is not None and not requested.is_absolute():
        raise ConfigError("Set T212_CONFIG_FILE to an absolute path.")

    launcher, codex = installed_launcher(), codex_executable()
    existing = find_registration(codex, launcher, requested)
    path = existing.config if existing else requested or cli.default_config()
    if not path.is_absolute():
        raise ConfigError("Select an absolute account settings path.")
    ensure_account(path, account)
    if existing is None:
        # An interactive setup may take time. Recheck before editing Codex.
        existing = find_registration(codex, launcher, path)
    if existing is None:
        run_codex(
            codex,
            "add",
            SERVER,
            "--env",
            f"T212_CONFIG_FILE={path}",
            "--",
            str(launcher),
        )
        print("Registered Trading 212 with Codex.")
    else:
        print(f"Codex already has Trading 212 registered as {existing.name}.")
    print("Restart Codex and ask it to show your Trading 212 accounts.")
