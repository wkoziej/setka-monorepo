#!/usr/bin/env bash
# ABOUTME: Keeps paternologia running on a host without systemd: restarts uvicorn whenever it exits.
# ABOUTME: Single instance via flock; listens on PATERNOLOGIA_HOST:PATERNOLOGIA_PORT (default 0.0.0.0:8000).
set -u

APP=$HOME/paternologia
exec 9>"$APP/run.lock"
flock -n 9 || exit 0

export PATERNOLOGIA_DATA_DIR=$APP/data
export PYTHONUNBUFFERED=1
cd "$APP"

while true; do
    echo "=== $(date '+%F %T') starting paternologia" >> "$APP/paternologia.log"
    "$APP/venv/bin/python" -m uvicorn paternologia.main:app \
        --host "${PATERNOLOGIA_HOST:-0.0.0.0}" --port "${PATERNOLOGIA_PORT:-8000}" \
        >> "$APP/paternologia.log" 2>&1
    sleep 2
done
