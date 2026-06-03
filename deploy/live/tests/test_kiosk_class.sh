#!/usr/bin/env bash
# ABOUTME: Test statyczny paternologia-kiosk.sh — kiosk dostaje stały --class=setka-kiosk
# ABOUTME: (deterministyczny uchwyt okna do układania), bez gubienia dotychczasowych flag. Nie odpala brave.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KIOSK_SH="$SCRIPT_DIR/../bin/paternologia-kiosk.sh"

PASS=0
FAIL=0
pass() { PASS=$((PASS + 1)); printf 'ok   - %s\n' "$1"; }
fail() { FAIL=$((FAIL + 1)); printf 'FAIL - %s\n' "$1"; }

# Czysto statycznie: kiosk uruchamia realne brave i czeka na serwer — nie wolno go odpalać w teście.
DESC="kiosk: nadaje --class=setka-kiosk (pewny, unikalny uchwyt okna)"
grep -q -- '--class=setka-kiosk' "$KIOSK_SH" && pass "$DESC" || fail "$DESC"

# Regresja: nowa flaga nie może wyprzeć istniejących — kiosk dalej --kiosk + osobny profil.
DESC="kiosk: zachowuje --kiosk (pełnoekranowy tryb kiosku)"
grep -q -- '--kiosk' "$KIOSK_SH" && pass "$DESC" || fail "$DESC"
DESC="kiosk: profil w obszarze snapa (~/snap/brave/common) — confinement nie zablokuje zapisu"
grep -q -- '--user-data-dir="\$HOME/snap/brave/common/paternologia-kiosk"' "$KIOSK_SH" \
  && pass "$DESC" || fail "$DESC"

# Regresja: NIE używać ~/.local/share — snap Brave nie ma tam dostępu, ignoruje --user-data-dir,
# forwarduje URL do zwykłej przeglądarki i wychodzi (okno kiosku się nie pojawia).
DESC="kiosk: nie używa ~/.local/share (poza obszarem snapa → confinement blokuje)"
grep -q -- '--user-data-dir="\$HOME/.local/share/paternologia-kiosk"' "$KIOSK_SH" \
  && fail "$DESC" || pass "$DESC"

printf '\n=== %d passed, %d failed ===\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
