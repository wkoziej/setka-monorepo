#!/usr/bin/env bash
# ABOUTME: Runs on the target host: installs uv, Python 3.11 and paternologia into ~/paternologia.
# ABOUTME: Syncs data from the repo, registers cron entries (run.sh, autoupdate.sh), (re)starts the app.
set -euo pipefail

APP=$HOME/paternologia
SRC=$APP/src/packages
HERE=$SRC/paternologia/deploy/remote
UV=$APP/bin/uv
# python-build-standalone ships no 32-bit (i686) build newer than 3.11.
PYTHON_VERSION=3.11

export UV_CACHE_DIR=$APP/cache
export UV_PYTHON_INSTALL_DIR=$APP/python

mkdir -p "$APP/bin"

if [ ! -x "$UV" ]; then
    case "$(uname -m)" in
        i686 | i386) UV_TARGET=i686-unknown-linux-musl ;;
        x86_64) UV_TARGET=x86_64-unknown-linux-musl ;;
        *) echo "Unsupported architecture: $(uname -m)" >&2; exit 1 ;;
    esac
    echo "Installing uv ($UV_TARGET)"
    TMP=$(mktemp -d)
    wget -q -O "$TMP/uv.tgz" "https://github.com/astral-sh/uv/releases/latest/download/uv-$UV_TARGET.tar.gz"
    tar -C "$TMP" -xzf "$TMP/uv.tgz"
    mv "$TMP/uv-$UV_TARGET/uv" "$UV"
    rm -rf "$TMP"
fi

"$UV" python install --no-bin "$PYTHON_VERSION"
"$UV" venv --allow-existing -q -p "$PYTHON_VERSION" "$APP/venv"

# Editable install: paternologia finds templates/ and static/ relative to its source tree.
# overrides.txt drops fastapi[standard] extras (uvloop, httptools, watchfiles), which do not
# build on old toolchains and are not needed at runtime. -std=gnu99 lets gcc < 5 build C extensions.
CFLAGS=-std=gnu99 "$UV" pip install -q -p "$APP/venv" \
    --override "$HERE/overrides.txt" \
    -e "$SRC/common" -e "$SRC/paternologia"

bash "$HERE/sync-data.sh" "$SRC/paternologia/data" "$APP/data"

install -m 755 "$HERE/run.sh" "$APP/bin/run.sh"
install -m 755 "$HERE/autoupdate.sh" "$APP/bin/autoupdate.sh"

for CRON_LINE in \
    "@reboot $APP/bin/run.sh" \
    "*/2 * * * * $APP/bin/autoupdate.sh >> $APP/autoupdate.log 2>&1"; do
    if ! crontab -l 2>/dev/null | grep -qxF "$CRON_LINE"; then
        (crontab -l 2>/dev/null || true; echo "$CRON_LINE") | crontab -
        echo "Cron: added '$CRON_LINE'"
    fi
done

# run.sh restarts uvicorn when it exits, so killing it reloads the new code.
if pgrep -f "$APP/venv/bin/python -m uvicorn" >/dev/null; then
    echo "Restarting paternologia"
    pkill -f "$APP/venv/bin/python -m uvicorn"
else
    echo "Starting paternologia"
    setsid nohup "$APP/bin/run.sh" >/dev/null 2>&1 < /dev/null &
fi
