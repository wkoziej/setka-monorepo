#!/usr/bin/env bash
# ABOUTME: Cron job on the host: deploys paternologia and launchpad-rc600 when origin/master moves.
# ABOUTME: Keeps a sparse git clone in ~/paternologia/src; runs a package's install.sh only if its code changed.
set -euo pipefail

APP=$HOME/paternologia
SRC=$APP/src
BRANCH=master
REPO_URL=${PATERNOLOGIA_REPO_URL:-https://github.com/wkoziej/setka-monorepo.git}
DEPLOYED=$APP/deployed-commit
SPARSE_PATHS=(packages/common packages/paternologia packages/launchpad-rc600)

exec 9>"$APP/autoupdate.lock"
flock -n 9 || exit 0

if [ ! -d "$SRC/.git" ]; then
    rm -rf "$SRC.clone"
    git clone -q --filter=blob:none --no-checkout --branch "$BRANCH" "$REPO_URL" "$SRC.clone"
    rm -rf "$SRC"
    mv "$SRC.clone" "$SRC"
fi

git -C "$SRC" fetch -q origin "$BRANCH"
TARGET=$(git -C "$SRC" rev-parse FETCH_HEAD)
PREVIOUS=$(cat "$DEPLOYED" 2>/dev/null || true)
if [ "$TARGET" = "$PREVIOUS" ]; then
    exit 0
fi

echo "=== $(date '+%F %T') deploying $TARGET"
git -C "$SRC" sparse-checkout set "${SPARSE_PATHS[@]}"
git -C "$SRC" reset -q --hard "$TARGET"

# install_if_changed <package> <path>...: runs the package's install.sh when any path changed
# since the deployed commit (always on the first deploy; a failed diff also counts as changed).
install_if_changed() {
    local package=$1
    shift
    if [ -z "$PREVIOUS" ] || ! git -C "$SRC" diff --quiet "$PREVIOUS" "$TARGET" -- "$@"; then
        echo "--- installing $package"
        bash "$SRC/packages/$package/deploy/remote/install.sh"
    fi
}

install_if_changed paternologia packages/common packages/paternologia
install_if_changed launchpad-rc600 packages/launchpad-rc600
echo "$TARGET" > "$DEPLOYED"
