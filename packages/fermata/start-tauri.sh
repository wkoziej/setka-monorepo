#!/bin/bash

# Skrypt do uruchamiania fermata z właściwymi zmiennymi środowiskowymi

export FERMATA_RECORDINGS_PATH="/home/wojtas/Wideo/obs"
export FERMATA_WORKSPACE_ROOT="/home/wojtas/dev/setka-monorepo"
export WEBKIT_DISABLE_DMABUF_RENDERER=1
export FERMATA_MAIN_AUDIO="Przechwytywanie wejścia dźwięku (PulseAudio).m4a"

echo "🎵 Uruchamianie fermata..."
echo "📁 Nagrania: $FERMATA_RECORDINGS_PATH"
echo "🏠 Workspace: $FERMATA_WORKSPACE_ROOT"
echo "🔧 EGL Fix: WEBKIT_DISABLE_DMABUF_RENDERER=1"
echo "🎤 Main Audio: $FERMATA_MAIN_AUDIO"
echo ""

npm run tauri dev 