#!/bin/bash

# Skrypt do uruchamiania fermata z właściwymi zmiennymi środowiskowymi

export FERMATA_RECORDINGS_PATH="/home/wojtas/Wideo/obs"
export FERMATA_WORKSPACE_ROOT="/home/wojtas/dev/setka-monorepo"

echo "🎵 Uruchamianie fermata..."
echo "📁 Nagrania: $FERMATA_RECORDINGS_PATH"
echo "🏠 Workspace: $FERMATA_WORKSPACE_ROOT"
echo ""

npm run tauri dev 