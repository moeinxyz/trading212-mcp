#!/bin/sh
# Install the tagged server for this user, then open its interactive connector.
set -eu
umask 077

fail() {
    printf '%s\n' "$*" >&2
    exit 1
}

install_uv() (
    version=0.13.10
    case "$1" in
        arm64)  target=aarch64-apple-darwin
                digest=e419bf07533bdbf48795fc793601c834dd79db57a8c49ce8e25cfe3a8639958d ;;
        x86_64) target=x86_64-apple-darwin
                digest=153e03197588204c04fc4c81cc4bafbfa4280222a385e4ee36a87aeec0ae63b4 ;;
    esac
    stage=$(mktemp -d "$app/.uv-XXXXXXXX")
    trap 'rm -rf "$stage"' 0
    trap 'exit 1' HUP INT TERM
    printf 'Downloading uv %s for %s…\n' "$version" "$target" >&2
    curl -q --fail --silent --show-error --location --proto '=https' --proto-redir '=https' \
        --output "$stage/uv.tar.gz" "https://github.com/astral-sh/uv/releases/download/$version/uv-$target.tar.gz"
    actual=$(shasum -a 256 < "$stage/uv.tar.gz")
    [ "${actual%% *}" = "$digest" ] || fail "The uv download did not match its release checksum."
    tar -xzOf "$stage/uv.tar.gz" "uv-$target/uv" > "$stage/uv"
    chmod 700 "$stage/uv"
    mv -f "$stage/uv" "$app/bin/uv"
)

main() {
    [ "$(uname -s)" = Darwin ] || fail "This installer runs on macOS."
    arch=$(uname -m)
    case "$arch" in arm64|x86_64) ;; *) fail "Unsupported Mac architecture: $arch." ;; esac
    if ! ( : </dev/tty ) 2>/dev/null; then
        fail "Run this command in an interactive terminal to connect your account."
    fi

    app="${XDG_DATA_HOME:-$HOME/.local/share}/trading212-mcp"
    case "$app" in /*) ;; *) fail "Choose an absolute path for your application data." ;; esac
    mkdir -p "$app/bin"
    export UV_TOOL_DIR="$app/tools" UV_TOOL_BIN_DIR="$app/bin"
    export UV_PYTHON_INSTALL_DIR="$app/python" UV_PYTHON_BIN_DIR="$app/bin"
    export UV_CACHE_DIR="$app/cache" UV_NO_MODIFY_PATH=1 UV_PYTHON_DOWNLOADS=automatic

    # Older uv releases may lack managed Python or isolated tool installs.
    if ! uv_command=$(command -v uv) ||
        ! "$uv_command" --quiet --no-config tool install --managed-python --python 3.13 --help >/dev/null 2>&1; then
        uv_command="$app/bin/uv"
        [ -x "$uv_command" ] || install_uv "$arch"
    fi
    source_url="https://github.com/moeinxyz/trading212-mcp/archive/refs/tags/v0.4.0.tar.gz"
    printf 'Installing Trading 212 MCP and its private Python environment…\n' >&2
    "$uv_command" --quiet --no-config tool install --managed-python --python 3.13 "moein-trading212-mcp @ $source_url"
    launcher="$app/bin/trading212-mcp"
    [ -x "$launcher" ] || fail "Installation finished without the trading212-mcp command."
    export T212_MCP_EXECUTABLE="$launcher"
    exec "$launcher" connect "$@" </dev/tty
}

main "$@"
