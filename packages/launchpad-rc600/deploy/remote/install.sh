#!/usr/bin/env bash
# ABOUTME: Runs on the target host: installs lp-rc600 into ~/launchpad-rc600 from the autoupdate checkout.
# ABOUTME: Registers an @reboot cron entry and (re)starts the translator via run.sh; safe to re-run.
set -euo pipefail

APP=$HOME/launchpad-rc600
PKG=$HOME/paternologia/src/packages/launchpad-rc600
HERE=$PKG/deploy/remote
# uv and its cache come from the paternologia install (paternologia/deploy/remote/install.sh).
UV=$HOME/paternologia/bin/uv
export UV_CACHE_DIR=$HOME/paternologia/cache

mkdir -p "$APP/bin"

# python-build-standalone ships no i686 build >= 3.12 (the package needs 3.12+), so use the
# system Python; building python-rtmidi needs the system python3-devel and a C compiler.
"$UV" venv --allow-existing -q -p /usr/bin/python3 "$APP/venv"
"$UV" pip install -q -p "$APP/venv" -e "$PKG"

install -m 755 "$HERE/run.sh" "$APP/bin/run.sh"

CRON_LINE="@reboot $APP/bin/run.sh"
if ! crontab -l 2>/dev/null | grep -qxF "$CRON_LINE"; then
    (crontab -l 2>/dev/null || true; echo "$CRON_LINE") | crontab -
    echo "Cron: added '$CRON_LINE'"
fi

# run.sh restarts lp-rc600 when it exits, so killing it reloads the new code.
# Each start sends the startup state (levels 71, FX off) to the RC-600.
if pgrep -f "$APP/venv/bin/lp-rc600" >/dev/null; then
    echo "Restarting lp-rc600"
    pkill -f "$APP/venv/bin/lp-rc600"
else
    echo "Starting lp-rc600"
    setsid nohup "$APP/bin/run.sh" >/dev/null 2>&1 < /dev/null &
fi
