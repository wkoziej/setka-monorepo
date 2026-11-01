#!/usr/bin/env bash
# ABOUTME: Deploys paternologia from this checkout to a remote host over ssh (no systemd needed).
# ABOUTME: Syncs code, seeds data once, then runs install.sh on the host, which (re)starts the app.
set -euo pipefail

HOST=${1:?usage: deploy.sh <ssh-host>}
REPO=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
REMOTE_APP=paternologia

ssh "$HOST" "mkdir -p ~/$REMOTE_APP/src"

# Code only: data lives outside src/ so a redeploy never overwrites edits made on the host.
rsync -az --delete \
    --exclude __pycache__ --exclude .venv --exclude htmlcov --exclude coverage.json \
    --exclude .pytest_cache --exclude /packages/paternologia/data \
    --include /packages/ --include /packages/common/ --include /packages/common/** \
    --include /packages/paternologia/ --include /packages/paternologia/** \
    --exclude '*' \
    "$REPO/" "$HOST:$REMOTE_APP/src/"

if ssh "$HOST" "test -d ~/$REMOTE_APP/data"; then
    echo "Data: ~/$REMOTE_APP/data already exists on $HOST, leaving it untouched."
else
    echo "Data: seeding ~/$REMOTE_APP/data from this checkout."
    rsync -az "$REPO/packages/paternologia/data/" "$HOST:$REMOTE_APP/data/"
fi

ssh "$HOST" "bash ~/$REMOTE_APP/src/packages/paternologia/deploy/remote/install.sh"
