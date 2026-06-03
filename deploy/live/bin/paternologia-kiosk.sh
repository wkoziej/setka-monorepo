#!/usr/bin/env bash
# ABOUTME: Czeka aż serwer paternologii odpowie, potem otwiera /live w google-chrome --kiosk.
# ABOUTME: Uruchamiany jako kiosk.service (członek live-recording.target).
set -euo pipefail
URL="http://localhost:8000/live"

# Poll aż serwer zacznie odpowiadać (max ~30 s), eliminuje wyścig startu.
for _ in $(seq 1 60); do
  curl -sf -o /dev/null "http://localhost:8000/" && break
  sleep 0.5
done

# Używamy nie-snapowego google-chrome (/opt/google/chrome): snap Brave dwoił pozycję okna
# (wmctrl -e lądował poza ekranem) i odłączał się od kiosk.service (Type=exec → inactive).
# Osobny profil wymusza niezależną instancję kiosku, nawet gdy przeglądarka już działa
# (bez tego URL trafia do istniejącego okna i --kiosk jest ignorowany). Bez confinementu
# profil może leżeć w ~/.local/share. --class=setka-kiosk nadaje oknu stały, unikalny WM_CLASS —
# pewny uchwyt dla układania okien (setka-live show), nie kolidujący ze zwykłą przeglądarką.
exec google-chrome --kiosk --noerrdialogs \
  --no-first-run --no-default-browser-check \
  --disable-session-crashed-bubble --disable-infobars \
  --class=setka-kiosk \
  --user-data-dir="$HOME/.local/share/paternologia-kiosk" "$URL"
