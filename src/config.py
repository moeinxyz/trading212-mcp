"""Load only explicitly selected Trading 212 profiles and credential variables."""

import os
import re
import stat
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import httpx

from .broker import Trading212

CONFIG_KEYS = (
    "T212_CONFIG_FILE",
    "T212_ENV",
    "T212_ENABLE_WRITES",
    "T212_API_KEY",
    "T212_API_SECRET",
    "T212_ISA_API_KEY",
    "T212_ISA_API_SECRET",
)


class ConfigError(ValueError):
    """A configuration problem safe to display without exposing credentials."""


def read_config(path: str) -> dict[str, Any]:
    if not Path(path).is_absolute():
        raise ConfigError("Set T212_CONFIG_FILE to an absolute path.")
    cap = 1024 * 1024
    try:
        fd = os.open(
            path,
            os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0),
        )
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode):
                raise ConfigError("Select a regular TOML settings file.")
            if os.name == "posix" and (
                info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077
            ):
                raise ConfigError(
                    "The TOML file must be owned by the current user and have owner-only permissions (chmod 600)."
                )
            if info.st_size > cap:
                raise ConfigError("The TOML settings file exceeds 1 MiB.")
            with open(fd, "rb", closefd=False) as source:
                raw = source.read(cap + 1)
        finally:
            os.close(fd)
    except OSError:
        raise ConfigError(
            "Could not open T212_CONFIG_FILE. Select a regular TOML file and check its permissions."
        ) from None
    if len(raw) > cap:
        raise ConfigError("The TOML settings file exceeds 1 MiB.")
    try:
        return tomllib.loads(raw.decode("utf-8"))
    except (ValueError, RecursionError):
        raise ConfigError("T212_CONFIG_FILE must contain valid UTF-8 TOML.") from None


def credential_pair(
    profile: dict, env: Mapping[str, str], prefix: str | None
) -> tuple[str, str]:
    key_name, secret_name = "T212_API_KEY", "T212_API_SECRET"
    source = profile
    if prefix and (prefix + "_API_KEY" in env or prefix + "_API_SECRET" in env):
        source = env
        key_name, secret_name = prefix + "_API_KEY", prefix + "_API_SECRET"
        if key_name not in source or secret_name not in source:
            raise ConfigError(
                f"Override credentials together using both {key_name} and {secret_name}."
            )
    key = source.get(key_name, "")
    secret = source.get(secret_name, "")
    if not isinstance(key, str) or not isinstance(secret, str):
        raise ConfigError("Trading account credentials must be strings.")
    key, secret = key.strip(), secret.strip()
    if bool(key) != bool(secret):
        raise ConfigError(f"Set both {key_name} and {secret_name}.")
    return key, secret


def configured_accounts(
    env: Mapping[str, str], transport: httpx.AsyncBaseTransport | None = None
) -> dict[str, Trading212]:
    path = env.get("T212_CONFIG_FILE")
    config = read_config(path) if path else {}
    extras = config.get("trading_accounts", {})
    if not isinstance(extras, dict):
        raise ConfigError("Use named TOML sections such as [trading_accounts.isa].")
    if any(
        name == "primary" or not re.fullmatch(r"[a-z][a-z0-9_-]*", name)
        for name in extras
    ):
        raise ConfigError(
            "Use lower-case account labels starting with a letter. The label primary is reserved."
        )
    profiles = {"primary": config.get("trading", {}), **extras}
    if "T212_ISA_API_KEY" in env or "T212_ISA_API_SECRET" in env:
        profiles.setdefault("isa", {})
    accounts: dict[str, Trading212] = {}
    seen: set[tuple[str, str]] = set()
    for label, profile in profiles.items():
        if not isinstance(profile, dict):
            raise ConfigError("Each trading profile must be a TOML section.")
        writes = False
        prefix = None
        if label == "primary":
            environment = env.get("T212_ENV", profile.get("T212_ENV", "demo"))
            writes = env.get(
                "T212_ENABLE_WRITES", profile.get("T212_ENABLE_WRITES", False)
            )
            prefix = "T212"
        else:
            # Existing named profiles default to live. The env-only ISA shortcut follows primary.
            default_env = "live" if label in extras else accounts["primary"].env
            environment = profile.get("T212_ENV", default_env)
            if label == "isa":
                prefix = "T212_ISA"
        if not isinstance(environment, str) or not isinstance(writes, (str, bool)):
            raise ConfigError(
                "Specify the trading environment as a string and write access as true or false."
            )
        key, secret = credential_pair(profile, env, prefix)
        api = Trading212(
            {
                "T212_ENV": environment,
                "T212_ENABLE_WRITES": str(writes),
                "T212_API_KEY": key,
                "T212_API_SECRET": secret,
            },
            transport,
        )
        if key and (api.env, key) in seen:
            raise ConfigError("Generate a separate key pair in each trading account.")
        seen.add((api.env, key))
        accounts[label] = api
    return accounts
