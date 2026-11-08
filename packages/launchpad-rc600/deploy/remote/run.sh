#!/usr/bin/env bash
# ABOUTME: Keeps lp-rc600 (Launchpad Mini → real RC-600) running: restarts it whenever it exits.
# ABOUTME: Single instance via flock; a missing Launchpad or RC-600 port means a retry every 5 s.
set -u

APP=$HOME/launchpad-rc600
PKG=$HOME/paternologia/src/packages/launchpad-rc600
exec 9>"$APP/run.lock"
flock -n 9 || exit 0

export PYTHONUNBUFFERED=1

while true; do
    echo "=== $(date '+%F %T') starting lp-rc600" >> "$APP/lp-rc600.log"
    "$APP/venv/bin/lp-rc600" --out "RC-600 MIDI" --config "$PKG/assign.toml" \
        >> "$APP/lp-rc600.log" 2>&1
    sleep 5
done
