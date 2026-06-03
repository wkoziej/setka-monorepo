#!/usr/bin/env bash
# ABOUTME: Test live-layout.sh (plain shell). Karmi czyste funkcje geometrii realnym wyjściem
# ABOUTME: xrandr --listmonitors i przypadkami brzegowymi; warstwę live testuje przez rec>ndr/wmctrl.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAYOUT_SH="$SCRIPT_DIR/../bin/live-layout.sh"

PASS=0
FAIL=0
pass() { PASS=$((PASS + 1)); printf 'ok   - %s\n' "$1"; }
fail() { FAIL=$((FAIL + 1)); printf 'FAIL - %s\n' "$1"; }
assert_eq() { # got want desc
  if [ "$1" = "$2" ]; then pass "$3"; else fail "$3 (got '$1' want '$2')"; fi
}

# Sourcing nie może odpalić main() — guard w skrypcie ma to zapewnić.
# shellcheck disable=SC1090
source "$LAYOUT_SH"

# --- Realne wyjście `xrandr --listmonitors` (przechwycone z maszyny) ---
# Uwaga: HDMI (prawy, offset 1280) wypisany PRZED DVI (lewy, offset 0) — parser musi sortować po X.
XRANDR_REAL="Monitors: 2
 0: +*HDMI-0 1440/530x900/300+1280+0  HDMI-0
 1: +DVI-D-0 1280/376x1024/301+0+0  DVI-D-0"

# --- layout_parse_monitors: token W/mm x H/mm + X + Y → 'x y w h', sort po X ---
parsed="$(layout_parse_monitors "$XRANDR_REAL")"
assert_eq "$(printf '%s' "$parsed" | sed -n 1p)" "0 0 1280 1024" \
  "parse: lewy monitor pierwszy (offset 0) → '0 0 1280 1024'"
assert_eq "$(printf '%s' "$parsed" | sed -n 2p)" "1280 0 1440 900" \
  "parse: prawy monitor drugi (offset 1280) → '1280 0 1440 900'"

# --- sloty: bitwig = cały lewy; obs = górna połowa prawego; paternologia = dolna połowa ---
assert_eq "$(layout_slot_bitwig 0 0 1280 1024)" "0 0 1280 1024" \
  "slot bitwig: cały lewy monitor"
assert_eq "$(layout_slot_obs 1280 0 1440 900)" "1280 0 1440 450" \
  "slot obs: górna połowa prawego"
assert_eq "$(layout_slot_paternologia 1280 0 1440 900)" "1280 450 1440 450" \
  "slot paternologia: dolna połowa prawego"

# --- Edge: nieparzysta wysokość → połówki tilują bez dziury/zakładki (styk == y+h_top) ---
obs_odd="$(layout_slot_obs 1280 0 1440 901)"
pat_odd="$(layout_slot_paternologia 1280 0 1440 901)"
obs_h="$(printf '%s' "$obs_odd" | cut -d' ' -f4)"
pat_y="$(printf '%s' "$pat_odd" | cut -d' ' -f2)"
pat_h="$(printf '%s' "$pat_odd" | cut -d' ' -f4)"
assert_eq "$((obs_h + pat_h))" "901" \
  "slot odd: suma wysokości połówek == pełna wysokość (brak zgubionego piksela)"
assert_eq "$pat_y" "$((0 + obs_h))" \
  "slot odd: dolna połowa zaczyna się dokładnie na styku górnej (brak dziury/zakładki)"

# --- Edge: monitory w odwrotnej kolejności w wejściu → sort i tak daje lewy (X=0) pierwszy ---
XRANDR_REV="Monitors: 2
 0: +*DVI-D-0 1280/376x1024/301+0+0  DVI-D-0
 1: +HDMI-0 1440/530x900/300+1280+0  HDMI-0"
parsed_rev="$(layout_parse_monitors "$XRANDR_REV")"
assert_eq "$(printf '%s' "$parsed_rev" | sed -n 1p)" "0 0 1280 1024" \
  "parse rev: sort po X daje lewy (offset 0) jako pierwszy niezależnie od kolejności wejścia"

# =====================================================================================
# Warstwa live: recordery podstawiane pod XRANDR_BIN/WMCTRL_BIN (NIE mock realnego WM —
# zero realnych okien; weryfikujemy REALNE argumenty wywołań i logikę bramek/braku okna).
# =====================================================================================

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# Recorder xrandr: zwraca utrwalone wyjście --listmonitors (HDMI prawy, DVI lewy).
XRR="$WORK/xrandr-rec"
cat >"$XRR" <<'EOF'
#!/usr/bin/env bash
printf 'Monitors: 2\n 0: +*HDMI-0 1440/530x900/300+1280+0  HDMI-0\n 1: +DVI-D-0 1280/376x1024/301+0+0  DVI-D-0\n'
EOF
chmod +x "$XRR"

# Recorder wmctrl: na zapytanie -lx wypisuje po jednej linii na klasę z REC_WINDOWS
# (udaje istniejące okna); każde inne wywołanie (akcje -e/-a/-b) loguje do WMCTRL_REC_LOG.
WMC="$WORK/wmctrl-rec"
cat >"$WMC" <<'EOF'
#!/usr/bin/env bash
case "$*" in
  *-lx*)
    for c in $REC_WINDOWS; do printf '0x0300000a  0 %s  host  Tytuł\n' "$c"; done ;;
  *)
    printf '%s\n' "$*" >> "$WMCTRL_REC_LOG" ;;
esac
exit 0
EOF
chmod +x "$WMC"

WMLOG="$WORK/wmctrl.log"
ALL_WINDOWS="obs.obs com.bitwig.BitwigStudio setka-kiosk"

# Uruchamia live-layout.sh z recorderami; kolejne env (WMCTRL_BIN/XDG_SESSION_TYPE/...) z "$@"
# nadpisują domyślne (env: ostatnie przypisanie wygrywa). GRACE_WINDOW=0 → brak okna nie wisi.
layout_run() {
  : >"$WMLOG"
  env XRANDR_BIN="$XRR" WMCTRL_BIN="$WMC" WMCTRL_REC_LOG="$WMLOG" \
    REC_WINDOWS="$ALL_WINDOWS" GRACE_WINDOW=0 \
    XDG_SESSION_TYPE=x11 DISPLAY=:1 "$@" \
    bash "$LAYOUT_SH" >"$WORK/out.log" 2>&1
  echo $?
}

# --- Happy path: wszystkie okna istnieją → -e z prostokątami R2 dla każdej klasy + -a ---
rc="$(layout_run)"
assert_eq "$rc" "0" "live happy: exit 0 gdy wszystkie okna obecne"
grep -q -- '-r com.bitwig.BitwigStudio -e 0,0,0,1280,1024' "$WMLOG" \
  && pass "live happy: Bitwig → cały lewy (0,0,1280,1024)" || fail "live happy: zły slot Bitwiga"
grep -q -- '-r obs.obs -e 0,1280,0,1440,450' "$WMLOG" \
  && pass "live happy: OBS → górna połowa prawego (1280,0,1440,450)" || fail "live happy: zły slot OBS"
grep -q -- '-r setka-kiosk -e 0,1280,450,1440,450' "$WMLOG" \
  && pass "live happy: kiosk → dolna połowa prawego (1280,450,1440,450)" || fail "live happy: zły slot kiosku"
# Na wierzch: każda klasa aktywowana (-a).
for cls in obs.obs com.bitwig.BitwigStudio setka-kiosk; do
  grep -q -- "-a $cls" "$WMLOG" && pass "live happy: $cls aktywowany (-a, na wierzch)" \
    || fail "live happy: brak aktywacji $cls"
done

# --- Integration (cross-layer): współrzędne liczone z podstawionego XRANDR_BIN, nie zaszyte ---
# Dowód: gdyby zaszyte, zmiana wyjścia xrandr nic by nie dała. Podmieniamy szerokość lewego
# monitora (1280→1366) i sprawdzamy, że slot Bitwiga podąża za danymi z xrandr.
XRR2="$WORK/xrandr-rec2"
cat >"$XRR2" <<'EOF'
#!/usr/bin/env bash
printf 'Monitors: 2\n 0: +*HDMI-0 1440/530x900/300+1366+0  HDMI-0\n 1: +DVI-D-0 1366/376x1024/301+0+0  DVI-D-0\n'
EOF
chmod +x "$XRR2"
: >"$WMLOG"
env XRANDR_BIN="$XRR2" WMCTRL_BIN="$WMC" WMCTRL_REC_LOG="$WMLOG" \
  REC_WINDOWS="$ALL_WINDOWS" GRACE_WINDOW=0 XDG_SESSION_TYPE=x11 DISPLAY=:1 \
  bash "$LAYOUT_SH" >"$WORK/out.log" 2>&1
grep -q -- '-r com.bitwig.BitwigStudio -e 0,0,0,1366,1024' "$WMLOG" \
  && pass "live integ: slot liczony z xrandr (lewy 1366) — nie zaszyty" \
  || fail "live integ: współrzędne nie podążają za xrandr"
grep -q -- '-r obs.obs -e 0,1366,0,1440,450' "$WMLOG" \
  && pass "live integ: prawy monitor przesunięty zgodnie z offsetem z xrandr (X=1366)" \
  || fail "live integ: offset prawego nie z xrandr"

# --- Error path: sesja Wayland → twardy FAIL, ZERO wywołań wmctrl ---
rc="$(layout_run XDG_SESSION_TYPE=wayland)"
[ "$rc" != "0" ] && pass "live wayland: niezerowy exit (jawna odmowa)" || fail "live wayland: exit 0 (powinno !=0)"
[ ! -s "$WMLOG" ] && pass "live wayland: zero wywołań wmctrl (bramka przed akcjami)" \
  || fail "live wayland: wmctrl wywołany mimo Waylanda"
grep -qi 'wayland\|x11' "$WORK/out.log" && pass "live wayland: komunikat o braku wsparcia nie-X11" \
  || fail "live wayland: brak komunikatu o sesji"

# --- Error path: brak wmctrl w PATH → twardy FAIL z podpowiedzią instalacji ---
rc="$(layout_run WMCTRL_BIN="$WORK/nie-ma-wmctrl")"
[ "$rc" != "0" ] && pass "live no-wmctrl: niezerowy exit gdy brak wmctrl" || fail "live no-wmctrl: exit 0 (powinno !=0)"
grep -qi 'wmctrl' "$WORK/out.log" && pass "live no-wmctrl: podpowiedź instalacji wmctrl" \
  || fail "live no-wmctrl: brak podpowiedzi o wmctrl"

# --- Edge (R5): brak okna Bitwiga → pozostałe ułożone, Bitwig raportowany, exit 0 ---
rc="$(layout_run REC_WINDOWS="obs.obs setka-kiosk")"
assert_eq "$rc" "0" "live R5: exit 0 mimo brakującego okna (brak okna != awaria)"
grep -q -- '-r obs.obs -e 0,1280,0,1440,450' "$WMLOG" \
  && pass "live R5: OBS ułożony mimo braku Bitwiga" || fail "live R5: OBS nie ułożony"
grep -q -- '-r setka-kiosk -e 0,1280,450,1440,450' "$WMLOG" \
  && pass "live R5: kiosk ułożony mimo braku Bitwiga" || fail "live R5: kiosk nie ułożony"
grep -q -- '-r com.bitwig.BitwigStudio -e' "$WMLOG" \
  && fail "live R5: ustawiono geometrię nieistniejącego Bitwiga" || pass "live R5: brakujący Bitwig pominięty (nie ustawiono geometrii)"
grep -qi 'bitwig' "$WORK/out.log" && pass "live R5: raport wymienia brakujący Bitwig" \
  || fail "live R5: brak raportu o brakującym oknie"

# --- Idempotencja (R4): dwa przebiegi → identyczny zestaw wywołań geometrii ---
layout_run >/dev/null; run1="$(grep -- ' -e ' "$WMLOG" | sort)"
layout_run >/dev/null; run2="$(grep -- ' -e ' "$WMLOG" | sort)"
assert_eq "$run2" "$run1" "live R4: dwa przebiegi dają identyczne wywołania geometrii (idempotencja)"

printf '\n=== %d passed, %d failed ===\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
