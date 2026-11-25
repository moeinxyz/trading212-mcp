import os
import stat
import tomllib
from unittest.mock import Mock

import pytest

from trading212_mcp import cli


@pytest.fixture(autouse=True)
def ignore_external_config(monkeypatch):
    monkeypatch.delenv("T212_CONFIG_FILE", raising=False)


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
    path.chmod(0o600)
    with pytest.raises(cli.ConfigError, match="valid UTF-8 TOML"):
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


def test_add_named_account_via_cli_preserves_original_toml(
    tmp_path, monkeypatch, capsys
):
    path = tmp_path / "selected.toml"
    original = (
        b'# Keep my comments\r\n["trading"]\r\nT212_ENV="live"\r\n'
        b'T212_API_KEY="first" # keep this\r\nT212_API_SECRET="first-secret"\r\n'
        b'[another.section]\r\ncustom = {a=1, b="unchanged"}'
    )
    path.write_bytes(original)
    path.chmod(0o600)
    monkeypatch.setenv("T212_CONFIG_FILE", str(path))
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(
        cli.sys, "argv", ["trading212-mcp", "setup", "--account", "isa"]
    )
    monkeypatch.setattr("builtins.input", lambda _: "demo")
    prompts = Mock(side_effect=['named-"key"', "named-£\\secret"])
    monkeypatch.setattr(cli.getpass, "getpass", prompts)
    cli.main()
    cli.main()
    assert prompts.call_count == 2
    assert path.read_bytes().startswith(original)
    accounts = cli.configured_accounts({"T212_CONFIG_FILE": str(path)})
    assert accounts["primary"].key == "first"
    assert accounts["isa"].env == "demo" and not accounts["isa"].writes
    assert accounts["isa"].key == 'named-"key"'
    assert accounts["isa"].secret == "named-£\\secret"
    if os.name == "posix":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    output = capsys.readouterr()
    assert "named-" not in output.out + output.err
    assert sorted(tmp_path.iterdir()) == [path]


def test_can_add_named_account_first_then_primary_and_another_label(tmp_path):
    path = tmp_path / "new" / "accounts.toml"
    cli.save_account(path, "live", "fixture-a", "secret-a", "isa")
    cli.save_account(path, "demo", "fixture-b", "secret-b")
    cli.save_account(path, "live", "fixture-c", "secret-c", "long-term_2")
    accounts = cli.configured_accounts({"T212_CONFIG_FILE": str(path)})
    assert set(accounts) == {"primary", "isa", "long-term_2"}
    assert all(not account.writes for account in accounts.values())
    before = path.read_bytes()
    with pytest.raises(cli.ConfigError, match="already configured"):
        cli.save_account(path, "demo", "replace", "forbidden", "isa")
    with pytest.raises(cli.ConfigError, match="separate key pair"):
        cli.save_account(path, "demo", "fixture-b", "different", "other")
    assert path.read_bytes() == before
    assert sorted(path.parent.iterdir()) == [path]


@pytest.mark.parametrize(
    "fields",
    [
        'T212_API_KEY = "part-of-pair"\nT212_API_SECRET = ""',
        'T212_API_KEY = ""\nT212_API_SECRET = "part-of-pair"',
        'T212_API_KEY = ""',
        "T212_API_SECRET = 123",
    ],
)
def test_partial_or_malformed_profile_gives_specific_guidance(
    tmp_path, monkeypatch, capsys, fields
):
    path = tmp_path / "accounts.toml"
    existing = f"# custom\n[trading_accounts.isa]\n{fields}\n"
    path.write_text(existing, encoding="utf-8")
    path.chmod(0o600)
    monkeypatch.setenv("T212_CONFIG_FILE", str(path))
    monkeypatch.setattr(
        cli.getpass, "getpass", lambda _: pytest.fail("unneeded prompt")
    )
    cli.setup("isa")
    result = capsys.readouterr().out
    assert "[trading_accounts.isa]" in result and "T212_API_SECRET" in result
    assert "part-of-pair" not in result
    assert path.read_text() == existing


def test_setup_completes_empty_isa_and_preserves_existing_format(
    tmp_path, monkeypatch, capsys
):
    path = tmp_path / "accounts.toml"
    primary = (
        b'# primary comment\r\n[trading]\r\nT212_ENV="live"\r\n'
        b'T212_API_KEY="existing-a"\r\nT212_API_SECRET="existing-b" # private\r\n'
    )
    other = b"[other]\r\n  flags = [1, 2] # keep spacing\r\n"
    section = (
        b'[trading_accounts."isa"] # profile comment\n'
        b'  T212_ENV = "demo"  # chosen environment\n'
        b"  T212_API_KEY = ''  # key comment\n"
        b'  T212_API_SECRET = ""  # secret comment\n'
        b"  T212_ENABLE_WRITES = true # own comment\n"
        b"  custom = { show = true } # keep in profile\n"
    )
    path.write_bytes(primary + section + other)
    path.chmod(0o600)
    monkeypatch.setenv("T212_CONFIG_FILE", str(path))
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: "live")
    prompts = Mock(side_effect=["new-'key", "new-secret£"])
    monkeypatch.setattr(cli.getpass, "getpass", prompts)
    monkeypatch.setattr(
        cli.sys, "argv", ["trading212-mcp", "setup", "--account", "isa"]
    )
    cli.main()
    cli.main()
    assert prompts.call_count == 2
    contents = path.read_bytes()
    assert contents.startswith(primary) and contents.endswith(other)
    for expected in (
        b'[trading_accounts."isa"] # profile comment',
        b"# key comment",
        b"# secret comment",
        b'  T212_ENV = "live"  # chosen environment',
        b"false # own comment",
        b"  custom = { show = true } # keep in profile",
    ):
        assert expected in contents
    isa = cli.configured_accounts({"T212_CONFIG_FILE": str(path)})["isa"]
    assert (isa.env, isa.key, isa.secret, isa.writes) == (
        "live",
        "new-'key",
        "new-secret£",
        False,
    )
    assert "new-" not in capsys.readouterr().out
    if os.name == "posix":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600


@pytest.mark.parametrize(
    "existing, label",
    [
        ("[trading_accounts.isa]\n# reserved for later\n", "isa"),
        ("[trading]\n# reserved for later\n", "primary"),
        (
            'trading_accounts = { isa = { T212_API_KEY = "", T212_API_SECRET = "" } } # reserved for later\n',
            "isa",
        ),
    ],
)
def test_can_fill_section_only_or_inline_stub(tmp_path, existing, label):
    path = tmp_path / "accounts.toml"
    path.write_text(existing)
    path.chmod(0o600)
    cli.save_account(path, "demo", "chosen-key", "chosen-secret", label)
    profile = cli.configured_accounts({"T212_CONFIG_FILE": str(path)})[label]
    assert (profile.env, profile.key, profile.secret, profile.writes) == (
        "demo",
        "chosen-key",
        "chosen-secret",
        False,
    )
    assert "# reserved for later" in path.read_text()


def test_setup_does_not_read_or_write_on_invalid_label_or_relative_path(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("T212_CONFIG_FILE", "relative.toml")
    with pytest.raises(cli.ConfigError, match="absolute"):
        cli.setup("isa")
    monkeypatch.setenv("T212_CONFIG_FILE", str(tmp_path / "settings"))
    with pytest.raises(cli.ConfigError, match="label"):
        cli.setup("isa.unrelated")
    assert not list(tmp_path.iterdir())


def test_other_setup_has_an_exclusive_lock_and_can_be_retried(tmp_path):
    path = tmp_path / "accounts.toml"
    cli.save_account(path, "live", "one", "s1")
    before = path.read_bytes()
    with cli.setup_lock(path):
        with pytest.raises(cli.ConfigError, match="Another setup"):
            cli.save_account(path, "live", "two", "s2", "isa")
        assert path.read_bytes() == before
    cli.save_account(path, "live", "two", "s2", "isa")
    assert set(cli.configured_accounts({"T212_CONFIG_FILE": str(path)})) == {
        "primary",
        "isa",
    }


def test_external_editor_filling_a_stub_wins_without_losing_its_changes(
    tmp_path, monkeypatch
):
    path = tmp_path / "accounts.toml"
    path.write_text("[trading_accounts.isa]\n")
    path.chmod(0o600)
    read_state = cli.existing_profile_message
    edit = b'[trading_accounts.isa]\nT212_API_KEY="other-key"\nT212_API_SECRET="other-secret"\n'

    def replace_after_check(path, account):
        state = read_state(path, account)
        replacement = tmp_path / "external-edit.toml"
        replacement.write_bytes(edit)
        replacement.chmod(0o600)
        os.replace(replacement, path)
        return state

    monkeypatch.setattr(cli, "existing_profile_message", replace_after_check)
    with pytest.raises(cli.ConfigError, match="Settings changed"):
        cli.save_account(path, "live", "fixture", "secret", "isa")
    assert path.read_bytes() == edit
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.skipif(os.name != "posix", reason="POSIX file permissions and links")
def test_setup_requires_private_settings_and_preserves_read_only_mode(tmp_path):
    path = tmp_path / "settings.toml"
    original = '[custom]\na = "other"\n'
    path.write_text(original)
    path.chmod(0o644)
    with pytest.raises(cli.ConfigError, match="owner-only"):
        cli.save_account(path, "live", "fixture", "secret", "isa")
    assert path.read_text() == original
    path.chmod(0o400)
    link = tmp_path / "settings-link.toml"
    link.symlink_to(path)
    with pytest.raises(cli.ConfigError, match="symbolic link"):
        cli.save_account(link, "live", "fixture", "secret", "isa")
    cli.save_account(path, "live", "fixture", "secret", "isa")
    assert stat.S_IMODE(path.stat().st_mode) == 0o400
