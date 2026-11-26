"""Exercise the macOS pipe-to-shell installer using a temporary home and offline releases."""

import hashlib
import io
import re
import stat
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != "darwin", reason="Uses macOS script(1) to provide a real terminal."
)
INSTALLER = Path(__file__).resolve().parents[2] / "install.sh"

# The fixture CLI only stands in for the already-tested connect command. It must
# read from the terminal even though the shell receives the installer on stdin.
CLI = """#!/bin/sh
set -eu
case "$1" in
    probe) printf 'still installed'; exit ;;
    connect) test "$*" = "connect --account isa" ;;
    *) exit 1 ;;
esac
test -t 0
printf 'Fixture account?\n'
IFS= read -r reply
test "$reply" = fictional
printf '%s\n' "$T212_MCP_EXECUTABLE" >> "$HOME/connections"
"""
UV = """#!/bin/sh
set -eu
case " $* " in *" --help "*) exit 0 ;; esac
test "$1 $2 $3 $4 $5 $6 $7" = "--quiet --no-config tool install --managed-python --python 3.13"
case "$8" in "moein-trading212-mcp @ https://github.com/moeinxyz/trading212-mcp/archive/refs/tags/v"*.tar.gz) ;; *) exit 1 ;; esac
test "$UV_TOOL_DIR" = "$APP/tools"
test "$UV_TOOL_BIN_DIR" = "$APP/bin"
test "$UV_PYTHON_INSTALL_DIR" = "$APP/python"
if [ "${FAIL_TOOL:-}" = yes ]; then exit 42; fi
cp "$HOME/cli-fixture" "$UV_TOOL_BIN_DIR/trading212-mcp"
chmod 700 "$UV_TOOL_BIN_DIR/trading212-mcp"
"""


def executable(path, text):
    path.write_text(text, encoding="utf-8")
    path.chmod(0o700)


@pytest.fixture
def sandbox(tmp_path):
    home = tmp_path / "test home"
    home.mkdir()
    commands = tmp_path / "commands"
    commands.mkdir()
    executable(home / "cli-fixture", CLI)
    executable(
        commands / "uname",
        '#!/bin/sh\ncase "$1" in -s) echo Darwin ;; -m) echo "$ARCH" ;; *) exit 1 ;; esac\n',
    )
    executable(
        commands / "curl",
        """#!/bin/sh
set -eu
while [ "$1" != --output ]; do shift; done
printf '%s\n' "$3" >> "$HOME/downloads"
cp "$HOME/release.tar.gz" "$2"
""",
    )
    data = tmp_path / "private app data"
    return {
        "HOME": str(home),
        "PATH": f"{commands}:/usr/bin:/bin",
        "XDG_DATA_HOME": str(data),
        "APP": str(data / "trading212-mcp"),
        "ARCH": "arm64",
    }


def run_piped(installer, env):
    """Feed script bytes through stdin, while a real controlling TTY supplies the answer."""
    pipeline = 'cat "$1" | /bin/sh -s -- --account isa'
    command = [
        "/usr/bin/script",
        "-q",
        "/dev/null",
        "/bin/sh",
        "-c",
        pipeline,
        "sh",
        str(installer),
    ]
    with subprocess.Popen(
        command,
        cwd=env["HOME"],
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    ) as process:
        # Keep the terminal open while the installer runs. Closing script(1)'s
        # stdin with communicate(input=...) would also send an EOF to the prompt.
        process.stdin.write("fictional\n")
        process.stdin.flush()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            raise
        return process.returncode, process.stdout.read()


def release_fixture(env):
    target = ("aarch64" if env["ARCH"] == "arm64" else "x86_64") + "-apple-darwin"
    archive = Path(env["HOME"]) / "release.tar.gz"
    with tarfile.open(archive, "w:gz") as package:
        member = tarfile.TarInfo(f"uv-{target}/uv")
        member.size = len(UV.encode())
        package.addfile(member, io.BytesIO(UV.encode()))
    return target, hashlib.sha256(archive.read_bytes()).hexdigest()


@pytest.mark.parametrize("arch", ["arm64", "x86_64"])
def test_piped_install_verifies_download_and_reuses_private_launcher(
    tmp_path, sandbox, arch
):
    env = sandbox | {"ARCH": arch}
    home = Path(env["HOME"])
    target, digest = release_fixture(env)
    # Only substitute the pin in the temporary copy. tar, shasum and the
    # installer logic are real. No official release bytes are required in CI.
    fixture_script, pins = re.subn(
        r"(?<=digest=)[a-f0-9]{64}", digest, INSTALLER.read_text()
    )
    assert pins == 2
    local = tmp_path / "install-fixture.sh"
    local.write_text(fixture_script)
    if arch == "x86_64":
        executable(
            tmp_path / "commands" / "uv", "#!/bin/sh\nexit 1\n"
        )  # Incompatible global uv.

    for _ in range(2):
        status, output = run_piped(local, env)
        assert status == 0, output
    app = Path(env["APP"])
    launcher = app / "bin" / "trading212-mcp"
    assert (home / "connections").read_text().splitlines() == [str(launcher)] * 2
    assert stat.S_IMODE(app.stat().st_mode) == 0o700
    assert (
        subprocess.check_output([launcher, "probe"], env=env, text=True)
        == "still installed"
    )
    [download] = (home / "downloads").read_text().splitlines()
    assert re.fullmatch(
        rf"https://github\.com/astral-sh/uv/releases/download/[\d.]+/uv-{target}\.tar\.gz",
        download,
    )


def test_bad_digest_never_installs_or_connects(sandbox):
    home = Path(sandbox["HOME"])
    release_fixture(sandbox)
    # Our fixture is not an official release. The production pins must reject it.
    status, output = run_piped(INSTALLER, sandbox)
    assert status != 0 and "checksum" in output, output
    assert not (Path(sandbox["APP"]) / "bin" / "uv").exists()
    assert not (home / "connections").exists()


def test_failed_package_install_never_connects_even_with_previous_launcher(
    tmp_path, sandbox
):
    app = Path(sandbox["APP"])
    (app / "bin").mkdir(parents=True)
    executable(app / "bin" / "trading212-mcp", CLI)
    executable(tmp_path / "commands" / "uv", UV)
    status, output = run_piped(INSTALLER, sandbox | {"FAIL_TOOL": "yes"})
    assert status == 42, output
    assert "Fixture account?" not in output
    assert not (Path(sandbox["HOME"]) / "connections").exists()
