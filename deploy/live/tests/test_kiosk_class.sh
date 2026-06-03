#!/usr/bin/env bash
# ABOUTME: Test statyczny paternologia-kiosk.sh — kiosk (nie-snap google-chrome) dostaje stały
# ABOUTME: --class=setka-kiosk i własny profil, bez gubienia flag. Czysto statyczny — nie odpala przeglądarki.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KIOSK_SH="$SCRIPT_DIR/../bin/paternologia-kiosk.sh"

PASS=0
FAIL=0
pass() { PASS=$((PASS + 1)); printf 'ok   - %s\n' "$1"; }
fail() { FAIL=$((FAIL + 1)); printf 'FAIL - %s\n' "$1"; }

# Czysto statycznie: kiosk uruchamia realną przeglądarkę i czeka na serwer — nie odpalamy jej w teście.
DESC="kiosk: nadaje --class=setka-kiosk (pewny, unikalny uchwyt okna)"
grep -q -- '--class=setka-kiosk' "$KIOSK_SH" && pass "$DESC" || fail "$DESC"

DESC="kiosk: zachowuje --kiosk (pełnoekranowy tryb kiosku)"
grep -q -- '--kiosk' "$KIOSK_SH" && pass "$DESC" || fail "$DESC"

# Świeży profil chrome pokazuje ekran „Witamy"/wybór domyślnej przeglądarki ZAMIAST /live —
# te flagi przeskakują first-run, by kiosk od razu ładował aplikację.
DESC="kiosk: --no-first-run (pomija ekran powitalny świeżego profilu)"
grep -q -- '--no-first-run' "$KIOSK_SH" && pass "$DESC" || fail "$DESC"
DESC="kiosk: --no-default-browser-check (pomija pytanie o domyślną przeglądarkę)"
grep -q -- '--no-default-browser-check' "$KIOSK_SH" && pass "$DESC" || fail "$DESC"

# Nie-snap google-chrome: deterministyczne pozycjonowanie i poprawne śledzenie przez systemd.
# (snap Brave dwoił pozycję okna i odłączał się od usługi — patrz historia.)
DESC="kiosk: używa nie-snapowego google-chrome"
grep -q -- 'exec google-chrome' "$KIOSK_SH" && pass "$DESC" || fail "$DESC"
DESC="kiosk: nie używa snapowego brave (źródło podwojenia pozycji i detachu)"
grep -q -- 'exec brave' "$KIOSK_SH" && fail "$DESC" || pass "$DESC"

# Bez confinementu profil może (i ma) leżeć w ~/.local/share — osobna instancja kiosku.
DESC="kiosk: profil w ~/.local/share/paternologia-kiosk (osobna instancja, bez confinementu)"
grep -q -- '--user-data-dir="\$HOME/.local/share/paternologia-kiosk"' "$KIOSK_SH" \
  && pass "$DESC" || fail "$DESC"

printf '\n=== %d passed, %d failed ===\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
