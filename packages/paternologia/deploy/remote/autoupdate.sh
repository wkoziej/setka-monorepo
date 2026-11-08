#!/usr/bin/env bash
# ABOUTME: Cron job on the host: deploys paternologia whenever origin/master moves past the deployed commit.
# ABOUTME: Keeps a sparse git clone in ~/paternologia/src and runs install.sh (data sync + restart) on change.
set -euo pipefail

APP=$HOME/paternologia
SRC=$APP/src
BRANCH=master
REPO_URL=${PATERNOLOGIA_REPO_URL:-https://github.com/wkoziej/setka-monorepo.git}
DEPLOYED=$APP/deployed-commit

exec 9>"$APP/autoupdate.lock"
flock -n 9 || exit 0

if [ ! -d "$SRC/.git" ]; then
    rm -rf "$SRC.clone"
    git clone -q --filter=blob:none --no-checkout --branch "$BRANCH" "$REPO_URL" "$SRC.clone"
    git -C "$SRC.clone" sparse-checkout set packages/common packages/paternologia
    git -C "$SRC.clone" checkout -q "$BRANCH"
    rm -rf "$SRC"
    mv "$SRC.clone" "$SRC"
fi

git -C "$SRC" fetch -q origin "$BRANCH"
TARGET=$(git -C "$SRC" rev-parse FETCH_HEAD)
if [ "$TARGET" = "$(cat "$DEPLOYED" 2>/dev/null || true)" ]; then
    exit 0
fi

echo "=== $(date '+%F %T') deploying $TARGET"
git -C "$SRC" reset -q --hard "$TARGET"
bash "$SRC/packages/paternologia/deploy/remote/install.sh"
echo "$TARGET" > "$DEPLOYED"
