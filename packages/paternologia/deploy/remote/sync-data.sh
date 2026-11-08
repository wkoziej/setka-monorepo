#!/usr/bin/env bash
# ABOUTME: Mirrors the repo's paternologia data/ onto the host data dir; the repo is the source of truth.
# ABOUTME: Host-specific obs.yaml and pacer.yaml are only seeded when missing, never overwritten.
set -euo pipefail

SRC=${1:?usage: sync-data.sh <repo-data-dir> <host-data-dir>}
DST=${2:?usage: sync-data.sh <repo-data-dir> <host-data-dir>}
HOST_SPECIFIC=(--include /obs.yaml --include /pacer.yaml)

mkdir -p "$DST"
# Excluded files are also protected from --delete, so host config survives.
rsync -a --delete --exclude /obs.yaml --exclude /pacer.yaml "$SRC/" "$DST/"
rsync -a --ignore-existing "${HOST_SPECIFIC[@]}" --exclude '*' "$SRC/" "$DST/"
