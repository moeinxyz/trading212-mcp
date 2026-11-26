import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from trading212_mcp import cli, connect


def executable(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()
    path.chmod(0o700)
    return path


def stdio(name, command, config=None):
    return {
        "name": name,
        "enabled": True,
        "transport": {
            "type": "stdio",
            "command": str(command),
            "args": [],
            "env_vars": [],
            "env": {"T212_CONFIG_FILE": str(config)} if config else None,
        },
    }


@pytest.fixture
def local(tmp_path, monkeypatch):
    for key in (*cli.CONFIG_KEYS, "UV_CACHE_DIR", "T212_MCP_EXECUTABLE"):
        monkeypatch.delenv(key, raising=False)
    launcher = executable(tmp_path / "tool bin" / connect.LAUNCHER)
    codex = str(tmp_path / "codex")
    settings = tmp_path / "my private files" / "settings.toml"
    monkeypatch.setenv("T212_MCP_EXECUTABLE", str(launcher))
    monkeypatch.setattr(cli, "default_config", lambda: settings)
    monkeypatch.setattr(
        connect.shutil,
        "which",
        {
            "codex": codex,
            "trading212-mcp": str(launcher),
            connect.LAUNCHER: str(launcher),
        }.get,
    )
    calls, servers = [], []

    def stub(argv, **kwargs):
        assert argv[:2] == [codex, "mcp"]
        assert not any(k.startswith("T212_") for k in kwargs["env"])
        assert "shell" not in kwargs and kwargs["stdin"] == subprocess.DEVNULL
        calls.append(argv[2:])
        if argv[2:] == ["list", "--json"]:
            return SimpleNamespace(stdout=json.dumps(servers))
        assert argv[2:5] == ["add", "trading212", "--env"]
        assert len(argv) == 8 and argv[6] == "--"
        key, value = argv[5].split("=", 1)
        assert key == "T212_CONFIG_FILE"
        servers.append(stdio(argv[3], argv[7], value))
        return SimpleNamespace(stdout="")

    monkeypatch.setattr(connect.subprocess, "run", stub)
    return SimpleNamespace(
        settings=settings, launcher=launcher, servers=servers, calls=calls
    )


def test_new_connection_prompts_once_and_keeps_keys_out_of_codex(
    local, monkeypatch, capsys
):
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: "live")
    prompt = Mock(side_effect=["synthetic-key", "synthetic-secret"])
    monkeypatch.setattr(cli.getpass, "getpass", prompt)
    monkeypatch.setattr(cli.sys, "argv", ["trading212-mcp", "connect"])
    cli.main()
    cli.main()
    assert prompt.call_count == 2
    assert cli.configured_accounts({"T212_CONFIG_FILE": str(local.settings)})[
        "primary"
    ].credentials_configured
    assert [c for c in local.calls if c[0] == "add"] == [
        [
            "add",
            "trading212",
            "--env",
            f"T212_CONFIG_FILE={local.settings}",
            "--",
            str(local.launcher),
        ]
    ]
    out = capsys.readouterr()
    assert "synthetic-" not in str(local.calls) + out.out + out.err


def test_named_accounts_alone_are_sufficient_when_registration_targets_explicit_file(
    local, monkeypatch
):
    other = local.settings.with_suffix(".user.toml")
    cli.save_account(other, "live", "file-key", "file-secret", "invest")
    monkeypatch.setenv("T212_CONFIG_FILE", str(other))
    monkeypatch.setattr(cli, "setup", Mock(side_effect=AssertionError))
    connect.connect()
    assert local.calls[-1][3] == f"T212_CONFIG_FILE={other}"
    assert not local.settings.exists()


def test_existing_checkout_alias_supplies_effective_path_and_account_selection(
    local, tmp_path, monkeypatch
):
    project = tmp_path / "another checkout"
    launcher = executable(project / ".venv" / "bin" / connect.LAUNCHER)
    (project / "pyproject.toml").write_text('[project]\nname="moein-trading212-mcp"')
    other = tmp_path / "existing" / "accounts.toml"
    cli.save_account(other, "live", "fixture-a", "fixture-s", "invest")
    local.servers.extend(
        [
            stdio("my-portfolio", launcher, other),
            stdio("trading212", "/another/application"),
        ]
    )
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: "demo")
    prompt = Mock(side_effect=["fixture-b", "fixture-t"])
    monkeypatch.setattr(cli.getpass, "getpass", prompt)
    monkeypatch.setattr(
        cli.sys, "argv", ["trading212-mcp", "connect", "--account", "isa"]
    )
    cli.main()
    cli.main()
    assert prompt.call_count == 2
    assert (
        cli.configured_accounts({"T212_CONFIG_FILE": str(other)})["isa"].env == "demo"
    )
    assert not any(c[0] == "add" for c in local.calls)
    assert not local.settings.exists()


def test_recognizes_existing_documented_bare_command(local):
    cli.save_account(local.settings, "demo", "fixture", "secret")
    local.servers.append(stdio("investment", "trading212-mcp"))
    connect.connect()
    assert local.calls == [["list", "--json"]]


@pytest.mark.parametrize(
    "case",
    [
        "remote",
        "unrelated",
        "disabled",
        "arguments",
        "wrong_file",
        "overrides",
        "other_checkout",
    ],
)
def test_conflict_never_changes_registration_or_prompts(
    local, tmp_path, monkeypatch, case
):
    registration = stdio("trading212", local.launcher, local.settings)
    transport = registration["transport"]
    if case == "remote":
        transport.update(type="streamable_http", url="https://example.invalid")
    elif case == "unrelated":
        transport["command"] = "unrelated"
    elif case == "disabled":
        registration["enabled"] = False
    elif case == "arguments":
        transport["args"] = ["anything"]
    elif case == "wrong_file":
        monkeypatch.setenv("T212_CONFIG_FILE", str(tmp_path / "other.toml"))
    elif case == "overrides":
        transport["env"]["T212_API_KEY"] = "synthetic-key"
    elif case == "other_checkout":
        wrong = executable(tmp_path / "unrelated" / ".venv" / "bin" / connect.LAUNCHER)
        (tmp_path / "unrelated" / "pyproject.toml").write_text(
            '[project]\nname="unrelated"'
        )
        transport["command"] = str(wrong)
    local.servers.append(registration)
    with pytest.raises(cli.ConfigError, match="already has a different or disabled"):
        connect.connect()
    assert local.calls == [["list", "--json"]]
    assert not local.settings.exists()


def test_same_command_different_accounts_requires_explicit_file(local, tmp_path):
    local.servers.extend(
        [
            stdio("one", local.launcher, local.settings),
            stdio("two", local.launcher, tmp_path / "other"),
        ]
    )
    with pytest.raises(cli.ConfigError, match="different files"):
        connect.connect()
    assert local.calls == [["list", "--json"]]


def test_cancellation_before_secret_save_never_registers(local, monkeypatch):
    monkeypatch.setattr(cli.sys, "argv", ["trading212-mcp", "connect"])
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: "demo")
    monkeypatch.setattr(
        cli.getpass, "getpass", Mock(side_effect=["fixture-key", KeyboardInterrupt])
    )
    with pytest.raises(SystemExit, match="cancelled"):
        cli.main()
    assert local.calls == [["list", "--json"]]
    assert not local.settings.exists()


def test_conflict_created_while_typing_never_overwritten(local, monkeypatch):
    def setup(label, *, path):
        cli.save_account(path, "demo", "fixture-key", "fixture-secret", label)
        local.servers.append(stdio("trading212", "different-server"))

    monkeypatch.setattr(cli, "setup", setup)
    with pytest.raises(cli.ConfigError, match="already has a different"):
        connect.connect()
    assert local.calls == [["list", "--json"], ["list", "--json"]]


@pytest.mark.parametrize("reply", ["yes", "no"])
def test_exported_pairs_can_save_only_the_selected_one_with_consent(
    local, monkeypatch, capsys, reply
):
    for key in (
        "T212_API_KEY",
        "T212_API_SECRET",
        "T212_ISA_API_KEY",
        "T212_ISA_API_SECRET",
    ):
        monkeypatch.setenv(key, f"synthetic-{key}")
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: reply)
    if reply == "yes":
        connect.connect("isa")
        accounts = cli.configured_accounts({"T212_CONFIG_FILE": str(local.settings)})
        assert (
            accounts["isa"].credentials_configured
            and not accounts["primary"].credentials_configured
        )
        assert local.calls[-1][0] == "add"
    else:
        with pytest.raises(cli.ConfigError, match="cancelled"):
            connect.connect("isa")
        assert not local.settings.exists() and all(c[0] == "list" for c in local.calls)
    assert "synthetic-" not in repr(local.calls) + capsys.readouterr().out


@pytest.mark.parametrize("invalid", ["relative", "missing", "cache", "ephemeral"])
def test_unstable_or_invalid_installer_path_fails_before_setup(
    local, tmp_path, monkeypatch, invalid
):
    if invalid == "cache":
        path = executable(tmp_path / "archive-v0" / "opaque" / "bin" / connect.LAUNCHER)
    elif invalid == "ephemeral":
        path = executable(tmp_path / ".tmpExample" / "bin" / connect.LAUNCHER)
    elif invalid == "relative":
        path = Path(connect.LAUNCHER)
    else:
        path = tmp_path / "missing" / connect.LAUNCHER
    monkeypatch.setenv("T212_MCP_EXECUTABLE", str(path))
    with pytest.raises(cli.ConfigError, match="persistent tool"):
        connect.connect()
    assert local.calls == []


def test_finds_command_on_path_and_mac_desktop_bundle(local, monkeypatch, tmp_path):
    monkeypatch.delenv("T212_MCP_EXECUTABLE")
    assert connect.installed_launcher() == local.launcher
    monkeypatch.setattr(connect.shutil, "which", lambda _: None)
    monkeypatch.setattr(connect.sys, "platform", "darwin")
    monkeypatch.setattr(connect.Path, "home", staticmethod(lambda: tmp_path))
    bundled = tmp_path / "Applications/Codex.app/Contents/Resources/codex"
    # Isolate from any real desktop app installed on the test runner.
    monkeypatch.setattr(connect, "usable", lambda path: path == bundled)
    assert connect.codex_executable() == str(bundled)


@pytest.mark.parametrize("failure", ["invalid-json", "wrong-shape", "subprocess"])
def test_codex_failure_is_sanitized_and_cannot_proceed(local, monkeypatch, failure):
    def fail(*args, **kwargs):
        if failure == "subprocess":
            raise subprocess.CalledProcessError(1, "example", output="sensitive-data")
        return SimpleNamespace(
            stdout="sensitive-data"
            if failure == "invalid-json"
            else '{"sensitive-data":true}'
        )

    monkeypatch.setattr(connect.subprocess, "run", fail)
    with pytest.raises(cli.ConfigError) as result:
        connect.connect()
    assert "sensitive-data" not in str(result.value)
    assert not local.settings.exists()


@pytest.mark.parametrize("owns_script", [True, False])
def test_global_uv_tool_registration_keeps_its_own_version_and_alias(
    local, tmp_path, monkeypatch, owns_script
):
    # The old README registered the bare command. A new installer has a different stable path.
    venv = tmp_path / "old-uv-tools" / "moein-trading212-mcp"
    old_launcher = executable(venv / "bin" / connect.LAUNCHER)
    site = venv / "lib" / "python3.13" / "site-packages"
    info = site / "moein_trading212_mcp-0.3.0.dist-info"
    info.mkdir(parents=True)
    (info / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: moein-trading212-mcp\nVersion: 0.3.0\n"
    )
    target = connect.LAUNCHER if owns_script else "unrelated"
    (info / "RECORD").write_text(f"../../../bin/{target},,\n")
    which = connect.shutil.which
    monkeypatch.setattr(
        connect.shutil,
        "which",
        lambda cmd: str(old_launcher) if cmd == "trading212-mcp" else which(cmd),
    )
    local.servers.append(stdio("trading212", "trading212-mcp", local.settings))
    cli.save_account(local.settings, "live", "fixture-key", "fixture-secret")
    if owns_script:
        connect.connect()
    else:
        with pytest.raises(cli.ConfigError, match="different or disabled"):
            connect.connect()
    assert local.calls == [["list", "--json"]]
