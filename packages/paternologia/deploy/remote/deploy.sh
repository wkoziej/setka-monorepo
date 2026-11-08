#!/usr/bin/env bash
# ABOUTME: Deploys paternologia from this checkout to a remote host over ssh (no systemd needed).
# ABOUTME: Syncs code and data, then runs install.sh on the host, which mirrors data and (re)starts the app.
set -euo pipefail

HOST=${1:?usage: deploy.sh <ssh-host>}
REPO=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
REMOTE_APP=paternologia

ssh "$HOST" "mkdir -p ~/$REMOTE_APP/src"

# Code and data; install.sh mirrors data/ into ~/paternologia/data (repo is the source of truth).
# The host's autoupdate.sh resets src/ to origin/master on its next master change.
rsync -az --delete \
    --exclude __pycache__ --exclude .venv --exclude htmlcov --exclude coverage.json \
    --exclude .pytest_cache \
    --include /packages/ --include /packages/common/ --include /packages/common/** \
    --include /packages/paternologia/ --include /packages/paternologia/** \
    --exclude '*' \
    "$REPO/" "$HOST:$REMOTE_APP/src/"

ssh "$HOST" "bash ~/$REMOTE_APP/src/packages/paternologia/deploy/remote/install.sh"
