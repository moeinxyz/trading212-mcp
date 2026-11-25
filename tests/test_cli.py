import os
import stat
import tomllib
from unittest.mock import Mock

import pytest

from trading212_mcp import cli


def test_setup_saves_hidden_inputs_only_in_private_config(
    tmp_path, monkeypatch, capsys
):
    path = tmp_path / "test-settings" / "accounts.toml"
    monkeypatch.setattr(cli, "default_config", lambda: path)
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: "LIVE")
    monkeypatch.setattr(
        cli.getpass, "getpass", Mock(side_effect=['fictional"key', "fictional-secret"])
    )

    cli.setup()
    cli.setup()  # A second run preserves the first account.
    assert tomllib.loads(path.read_text())["trading"] == {
        "T212_ENV": "live",
        "T212_API_KEY": 'fictional"key',
        "T212_API_SECRET": "fictional-secret",
        "T212_ENABLE_WRITES": False,
    }
    if os.name == "posix":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert "fictional" not in capsys.readouterr().out


def test_save_refuses_to_replace_existing_file(tmp_path):
    path = tmp_path / "accounts.toml"
    path.write_text("existing contents")
    with pytest.raises(FileExistsError):
        cli.save_account(path, "demo", "fixture-key", "fixture-secret")
    assert path.read_text() == "existing contents"
    assert list(tmp_path.iterdir()) == [path]


def test_setup_requires_private_interactive_input(tmp_path, monkeypatch):
    path = tmp_path / "accounts.toml"
    monkeypatch.setattr(cli, "default_config", lambda: path)
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: False)
    with pytest.raises(SystemExit, match="interactive"):
        cli.setup()
    assert not path.exists()


def test_default_file_respects_explicit_launch_settings(tmp_path, monkeypatch):
    for name in cli.CONFIG_KEYS:
        monkeypatch.delenv(name, raising=False)
    path = tmp_path / "accounts.toml"
    monkeypatch.setattr(cli, "default_config", lambda: path)
    assert cli.server_settings() == {}
    path.touch()
    assert cli.server_settings() == {"T212_CONFIG_FILE": str(path)}
    monkeypatch.setenv("T212_ENV", "demo")
    assert cli.server_settings() == {"T212_ENV": "demo"}
