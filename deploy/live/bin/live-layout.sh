#!/usr/bin/env bash
# ABOUTME: Układa okna warstwy live na dwóch monitorach (Bitwig lewy; OBS+kiosk prawy) przez wmctrl.
# ABOUTME: Czyste funkcje geometrii (xrandr → sloty) są testowalne tekstem; wywołania wmctrl za WMCTRL_BIN.
set -uo pipefail

# Indirekcja przez env wyłącznie dla testów — domyślnie realne narzędzia X11/EWMH.
WMCTRL_BIN="${WMCTRL_BIN:-wmctrl}"
XRANDR_BIN="${XRANDR_BIN:-xrandr}"

# WM_CLASS okien do ułożenia. Kiosk dostaje własny --class=setka-kiosk (patrz paternologia-kiosk.sh).
# OBS i Bitwig (flatpak) dopasowywane po natywnym WM_CLASS — wartości DO POTWIERDZENIA `wmctrl -lx`
# przy żywych oknach; nadpisywalne env, by nie edytować skryptu. R5 sprawia, że błędne dopasowanie
# degraduje się do „okno pominięte", nie do crasha.
OBS_CLASS="${OBS_CLASS:-obs.obs}"
BITWIG_CLASS="${BITWIG_CLASS:-com.bitwig.BitwigStudio}"
KIOSK_CLASS="${KIOSK_CLASS:-setka-kiosk}"

log() { printf 'layout: %s\n' "$*"; }
err() { printf 'layout: %s\n' "$*" >&2; }

# --- Czyste funkcje geometrii (testowalne, karmione tekstem) ---

# Parsuje `xrandr --listmonitors` → linie 'x y w h', posortowane rosnąco po offsecie X
# (lewy monitor = najmniejszy X = pierwszy). Token geometrii ma postać W/Wmm x H/Hmm + X + Y
# (np. '1440/530x900/300+1280+0'); milimetry ignorujemy.
layout_parse_monitors() {
  printf '%s\n' "$1" \
    | sed -n 's#.*[[:space:]]\([0-9]\{1,\}\)/[0-9]\{1,\}x\([0-9]\{1,\}\)/[0-9]\{1,\}+\([0-9]\{1,\}\)+\([0-9]\{1,\}\).*#\3 \4 \1 \2#p' \
    | sort -n -k1,1
}

# Sloty przyjmują geometrię monitora jako 'x y w h' (4 argumenty) i wypisują 'x y w h' slotu.
# Bitwig = cały lewy monitor.
layout_slot_bitwig() {
  printf '%s %s %s %s\n' "$1" "$2" "$3" "$4"
}

# OBS = górna połowa prawego monitora (wysokość dzielona całkowicie; górna bierze podłogę).
layout_slot_obs() {
  local x="$1" y="$2" w="$3" h="$4"
  printf '%s %s %s %s\n' "$x" "$y" "$w" "$((h / 2))"
}

# Paternologia (kiosk) = dolna połowa prawego monitora. Bierze RESZTĘ wysokości (h - h/2),
# więc dla nieparzystej wysokości połówki tilują bez zgubionego piksela i bez zakładki.
layout_slot_paternologia() {
  local x="$1" y="$2" w="$3" h="$4"
  local top=$((h / 2))
  printf '%s %s %s %s\n' "$x" "$((y + top))" "$w" "$((h - top))"
}

# --- Warstwa live: realne komendy X11/EWMH (pobierają świeże dane przy każdym wywołaniu) ---

# Grace per-okno (s): czeka aż okno się pojawi przed ustawieniem geometrii. Bitwig-flatpak
# startuje najwolniej, stąd niezerowy domyślny zapas; nadpisywalny env (dostrajany przy realnym
# `start`). Dla ręcznego `show` (okna już są) predykat-prawda zwraca od razu, więc zapas nie boli.
GRACE_WINDOW="${GRACE_WINDOW:-10}"

# Pętla retry/grace: nie wisi, twardo kończy po wyczerpaniu okna (wzorzec poll_ok z live-preflight.sh).
poll_ok() {
  local grace="$1"; shift
  local deadline=$((SECONDS + grace))
  while :; do
    if "$@"; then return 0; fi
    [ "$SECONDS" -ge "$deadline" ] && return 1
    sleep 0.5
  done
}

# Okno o danym WM_CLASS istnieje? `wmctrl -lx` listuje okna z klasą; dopasowanie po podłańcuchu
# klasy (np. 'setka-kiosk' trafia w 'setka-kiosk.Setka-kiosk').
layout_window_exists() {
  "$WMCTRL_BIN" -lx 2>/dev/null | grep -qiF -- "$1"
}
poll_window_exists() { poll_ok "$GRACE_WINDOW" layout_window_exists "$1"; }

# Ustaw geometrię okna i wyciągnij na wierzch. Zmaksymalizowane LUB pełnoekranowe okno (kiosk
# startuje w --kiosk = fullscreen) ignoruje -e, więc najpierw zdejmujemy oba stany. wmctrl -b
# zmienia max 2 właściwości na wywołanie (limit EWMH), stąd fullscreen osobnym wywołaniem.
# -x każe wmctrl interpretować argument jako WM_CLASS (nie tytuł).
layout_place() {
  local cls="$1" x="$2" y="$3" w="$4" h="$5"
  "$WMCTRL_BIN" -x -r "$cls" -b remove,maximized_vert,maximized_horz 2>/dev/null || true
  "$WMCTRL_BIN" -x -r "$cls" -b remove,fullscreen 2>/dev/null || true
  "$WMCTRL_BIN" -x -r "$cls" -e "0,$x,$y,$w,$h"
  "$WMCTRL_BIN" -x -a "$cls"
}

# Liczniki raportu (R5): ustawiane przez try_place w bieżącej powłoce (nie subshell).
PLACED=0
MISSING=""

# Ułóż jedno okno, jeśli istnieje (z grace); brak → log + odnotuj do raportu, NIE przerywaj (R5).
try_place() {
  local cls="$1" label="$2" geom="$3"
  if poll_window_exists "$cls"; then
    # shellcheck disable=SC2086  # geom to celowo dzielone 'x y w h'.
    layout_place "$cls" $geom
    log "  [OK] $label → $geom"
    PLACED=$((PLACED + 1))
  else
    log "  [--] $label: brak okna (WM_CLASS=$cls) — pomijam"
    MISSING="$MISSING $label"
  fi
}

main() {
  # Bramki środowiska — twardy FAIL (exit !=0). To realne awarie, nie brak pojedynczego okna.
  if [ "${XDG_SESSION_TYPE:-}" != "x11" ]; then
    err "sesja '${XDG_SESSION_TYPE:-?}' != x11 — układanie okien (wmctrl/EWMH) działa tylko na Xorg. Odmawiam."
    return 1
  fi
  if [ -z "${DISPLAY:-}" ]; then
    err "brak DISPLAY — brak aktywnej sesji graficznej do układania okien. Odmawiam."
    return 1
  fi
  if ! command -v "$WMCTRL_BIN" >/dev/null 2>&1; then
    err "brak wmctrl — zainstaluj: sudo apt install wmctrl"
    return 1
  fi

  # Geometria z xrandr (czyste funkcje); oczekujemy 2 monitorów (lewy = mniejszy offset X).
  local monitors left right
  monitors="$(layout_parse_monitors "$("$XRANDR_BIN" --listmonitors 2>/dev/null)")"
  left="$(printf '%s\n' "$monitors" | sed -n 1p)"
  right="$(printf '%s\n' "$monitors" | sed -n 2p)"
  if [ -z "$left" ] || [ -z "$right" ]; then
    err "oczekiwano 2 monitorów z 'xrandr --listmonitors', dostałem: ${monitors:-<nic>}. Odmawiam."
    return 1
  fi

  local bitwig obs pat
  # shellcheck disable=SC2086  # left/right to celowo dzielone 'x y w h'.
  bitwig="$(layout_slot_bitwig $left)"
  # shellcheck disable=SC2086
  obs="$(layout_slot_obs $right)"
  # shellcheck disable=SC2086
  pat="$(layout_slot_paternologia $right)"

  log "układam okna: Bitwig (lewy) | OBS+Paternologia (prawy)…"
  try_place "$BITWIG_CLASS" "Bitwig" "$bitwig"
  try_place "$OBS_CLASS"    "OBS"    "$obs"
  try_place "$KIOSK_CLASS"  "Paternologia" "$pat"

  if [ -n "$MISSING" ]; then
    log "ułożono $PLACED; brakujące okna:$MISSING (uruchom je i powtórz: setka-live show)"
  else
    log "ułożono wszystkie ($PLACED) okna"
  fi
  # Brak okna NIE jest błędem (R5) — exit 0. Niezerowo kończą tylko bramki środowiska wyżej.
  return 0
}

# Odpal main tylko przy bezpośrednim wykonaniu — sourcing (testy) ma dać same funkcje.
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
  main "$@"
fi
