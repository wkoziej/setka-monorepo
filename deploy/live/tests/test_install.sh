#!/usr/bin/env bash
# ABOUTME: Test instalatora deploy/live/install.sh (plain shell — bats nie jest w środowisku).
# ABOUTME: Instaluje do tymczasowych katalogów (env override), bez ruszania prawdziwego ~/.config.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_SH="$SCRIPT_DIR/../install.sh"

PASS=0
FAIL=0
pass() { PASS=$((PASS + 1)); printf 'ok   - %s\n' "$1"; }
fail() { FAIL=$((FAIL + 1)); printf 'FAIL - %s\n' "$1"; }

assert_file() { [ -f "$1" ] && pass "$2" || fail "$2 (brak pliku: $1)"; }
assert_no_file() { [ ! -e "$1" ] && pass "$2" || fail "$2 (plik istnieje: $1)"; }
assert_exit() { [ "$1" -eq "$2" ] && pass "$3" || fail "$3 (exit $1 != $2)"; }

# Buduje izolowane drzewo źródłowe: kopia install.sh + atrapy units/bin.
# install.sh wyznacza źródło z własnej lokalizacji, więc kopia w SRC czyni SRC źródłem.
make_src() {
  local src="$1"
  mkdir -p "$src/units" "$src/bin"
  cp "$INSTALL_SH" "$src/install.sh"
  printf '[Unit]\nDescription=dummy\n' >"$src/units/sample.service"
  printf '[Unit]\nDescription=dummy target\n' >"$src/units/sample.target"
  printf '#!/usr/bin/env bash\necho hi\n' >"$src/bin/sample-script"
}

run_install() {
  # Args: SRC SYSTEMD_DIR BIN_DIR AUTOSTART_DIR [extra PATH]
  local src="$1" sysd="$2" bind="$3" auto="$4"
  SYSTEMD_USER_DIR="$sysd" BIN_DIR="$bind" AUTOSTART_DIR="$auto" \
    PATH="${5:-$PATH}" bash "$src/install.sh" >"$src/out.log" 2>&1
}

# --- Test 1: happy path na czystych katalogach ---
T1="$(mktemp -d)"
make_src "$T1/src"
run_install "$T1/src" "$T1/systemd" "$T1/bin" "$T1/autostart" "$T1/bin:/usr/bin:/bin"
rc=$?
assert_exit "$rc" 0 "happy: install.sh kończy się sukcesem"
assert_file "$T1/systemd/sample.service" "happy: unit .service skopiowany"
assert_file "$T1/systemd/sample.target" "happy: unit .target skopiowany"
assert_file "$T1/bin/sample-script" "happy: skrypt skopiowany"
[ -x "$T1/bin/sample-script" ] && pass "happy: skrypt jest wykonywalny" || fail "happy: skrypt nie jest +x"

# --- Test 2: idempotencja — ponowny run gdy pliki identyczne (bez backupu) ---
run_install "$T1/src" "$T1/systemd" "$T1/bin" "$T1/autostart" "$T1/bin:/usr/bin:/bin"
rc=$?
assert_exit "$rc" 0 "idempotent: ponowny run z identyczną treścią = sukces"
bak_count=$(find "$T1/systemd" -name '*.bak-*' 2>/dev/null | wc -l)
[ "$bak_count" -eq 0 ] && pass "idempotent: brak zbędnych backupów dla identycznej treści" \
  || fail "idempotent: powstały backupy mimo identycznej treści ($bak_count)"

# --- Test 3: backup gdy istniejący plik różni się treścią ---
printf '[Unit]\nDescription=OLD STALE\n' >"$T1/systemd/sample.service"
run_install "$T1/src" "$T1/systemd" "$T1/bin" "$T1/autostart" "$T1/bin:/usr/bin:/bin"
rc=$?
assert_exit "$rc" 0 "backup: run przy różniącej się treści = sukces"
bak_count=$(find "$T1/systemd" -name 'sample.service.bak-*' 2>/dev/null | wc -l)
[ "$bak_count" -ge 1 ] && pass "backup: powstał backup starego unitu" \
  || fail "backup: brak backupu starego unitu"
grep -q 'dummy' "$T1/systemd/sample.service" && pass "backup: docelowy plik nadpisany nową treścią" \
  || fail "backup: docelowy plik nie został nadpisany"

# --- Test 4: wycofanie starego kiosk-autostartu ---
T4="$(mktemp -d)"
make_src "$T4/src"
mkdir -p "$T4/autostart"
printf '[Desktop Entry]\nExec=foo\n' >"$T4/autostart/paternologia-kiosk.desktop"
run_install "$T4/src" "$T4/systemd" "$T4/bin" "$T4/autostart" "$T4/bin:/usr/bin:/bin"
rc=$?
assert_exit "$rc" 0 "autostart: install z istniejącym kioskiem = sukces"
assert_no_file "$T4/autostart/paternologia-kiosk.desktop" "autostart: stary kiosk .desktop usunięty z autostartu"
moved=$(find "$T4/autostart" -name 'paternologia-kiosk.desktop.*' 2>/dev/null | wc -l)
[ "$moved" -ge 1 ] && pass "autostart: stary kiosk zachowany jako backup (odwracalność)" \
  || fail "autostart: backup starego kiosku nie powstał"

# --- Test 5: brak autostartu = no-op, nie błąd ---
T5="$(mktemp -d)"
make_src "$T5/src"
mkdir -p "$T5/autostart"  # pusty
run_install "$T5/src" "$T5/systemd" "$T5/bin" "$T5/autostart" "$T5/bin:/usr/bin:/bin"
rc=$?
assert_exit "$rc" 0 "autostart-noop: brak kiosk .desktop = sukces (no-op)"

# --- Test 6: BIN_DIR poza PATH = ostrzeżenie, ale sukces ---
T6="$(mktemp -d)"
make_src "$T6/src"
run_install "$T6/src" "$T6/systemd" "$T6/bin" "$T6/autostart" "/usr/bin:/bin"
rc=$?
assert_exit "$rc" 0 "path-warn: BIN_DIR poza PATH = nadal sukces"
grep -qi 'PATH' "$T6/src/out.log" && pass "path-warn: instalator ostrzega o PATH" \
  || fail "path-warn: brak ostrzeżenia o PATH"

# --- Test 7: brak wmctrl = ostrzeżenie, ale NIE błąd (niefatalna zależność show) ---
T7="$(mktemp -d)"
make_src "$T7/src"
# Sandbox PATH: tylko narzędzia, których install.sh używa — BEZ wmctrl, niezależnie od tego,
# czy wmctrl jest zainstalowany w systemie (inaczej test fałszywie zielenił/czerwienił).
mkdir -p "$T7/nowmctrl"
for tool in bash mkdir cmp cp install basename date mv; do ln -s "$(command -v "$tool")" "$T7/nowmctrl/"; done
run_install "$T7/src" "$T7/systemd" "$T7/bin" "$T7/autostart" "$T7/nowmctrl"
rc=$?
assert_exit "$rc" 0 "wmctrl-missing: brak wmctrl NIE przerywa instalacji (niefatalne)"
grep -qi 'wmctrl' "$T7/src/out.log" && pass "wmctrl-missing: instalator ostrzega o braku wmctrl" \
  || fail "wmctrl-missing: brak ostrzeżenia o wmctrl"

# --- Test 8: wmctrl obecny = sukces bez fałszywego ostrzeżenia o instalacji ---
T8="$(mktemp -d)"
make_src "$T8/src"
mkdir -p "$T8/fakebin"
printf '#!/usr/bin/env bash\nexit 0\n' >"$T8/fakebin/wmctrl"
chmod +x "$T8/fakebin/wmctrl"
run_install "$T8/src" "$T8/systemd" "$T8/bin" "$T8/autostart" "$T8/fakebin:/usr/bin:/bin"
rc=$?
assert_exit "$rc" 0 "wmctrl-present: instalacja z dostępnym wmctrl = sukces"
grep -qi 'install wmctrl\|brak wmctrl' "$T8/src/out.log" \
  && fail "wmctrl-present: zbędne ostrzeżenie o wmctrl mimo obecności" \
  || pass "wmctrl-present: brak fałszywego ostrzeżenia gdy wmctrl jest"

rm -rf "$T1" "$T4" "$T5" "$T6" "$T7" "$T8"

# =============================================================================
# Testy Unitu 3: setka-tray, autostart .desktop, skróty GNOME (install.sh extensions)
# =============================================================================

# Rozszerzona make_src z atrapami Unit 3: setka-tray, live-keybindings.sh, autostart/.desktop
make_src3() {
  local src="$1"
  make_src "$src"
  # Atrapa setka-tray (plik wykonywalny Python)
  printf '#!/usr/bin/env python3\n# atrapa setka-tray\nprint("tray")\n' >"$src/bin/setka-tray"
  # Atrapa live-keybindings.sh (recorder-mock lub no-op w zależności od testu)
  printf '#!/usr/bin/env bash\necho "keybindings: $*" >> "${KB_LOG:-/dev/null}"\nexit 0\n' >"$src/bin/live-keybindings.sh"
  # Plik .desktop z placeholderem
  mkdir -p "$src/autostart"
  printf '[Desktop Entry]\nType=Application\nName=Setka Live Tray\nExec=__SETKA_TRAY_EXEC__\nX-GNOME-Autostart-enabled=true\n' \
    >"$src/autostart/setka-tray.desktop"
}

# run_install3: uruchamia install.sh z env dla Unit 3.
# SKIP_KEYBINDINGS=1 → nie woła żywego gsettings.
# Opcjonalnie GDBUS_BIN → mock gdbus (domyślnie noop/ok).
run_install3() {
  local src="$1" sysd="$2" bind="$3" auto="$4"
  local path="${5:-$PATH}"
  SYSTEMD_USER_DIR="$sysd" BIN_DIR="$bind" AUTOSTART_DIR="$auto" \
    SKIP_KEYBINDINGS=1 \
    GDBUS_BIN="${GDBUS_BIN:-true}" \
    PATH="$path" bash "$src/install.sh" >"$src/out.log" 2>&1
}

# --- Test U3-1: Happy path — setka-tray skopiowany, .desktop z podstawioną Exec ---
TU1="$(mktemp -d)"
make_src3 "$TU1/src"
run_install3 "$TU1/src" "$TU1/systemd" "$TU1/bin" "$TU1/autostart"
rc=$?
assert_exit "$rc" 0 "U3 happy: install.sh kończy się sukcesem"
assert_file "$TU1/bin/setka-tray" "U3 happy: setka-tray skopiowany do BIN_DIR"
[ -x "$TU1/bin/setka-tray" ] && pass "U3 happy: setka-tray jest wykonywalny" \
  || fail "U3 happy: setka-tray nie jest +x"
assert_file "$TU1/autostart/setka-tray.desktop" "U3 happy: setka-tray.desktop w AUTOSTART_DIR"

# Placeholder __SETKA_TRAY_EXEC__ musi być zastąpiony absolutną ścieżką
grep -q '__SETKA_TRAY_EXEC__' "$TU1/autostart/setka-tray.desktop" \
  && fail "U3 happy: placeholder __SETKA_TRAY_EXEC__ NIE zastąpiony" \
  || pass "U3 happy: placeholder zastąpiony"

grep -q "$TU1/bin/setka-tray" "$TU1/autostart/setka-tray.desktop" \
  && pass "U3 happy: Exec wskazuje na $TU1/bin/setka-tray" \
  || fail "U3 happy: brak absolutnej ścieżki w Exec; .desktop: $(cat "$TU1/autostart/setka-tray.desktop" 2>/dev/null)"

# --- Test U3-2: Idempotencja .desktop — ponowny install identycznych plików → brak backupu ---
run_install3 "$TU1/src" "$TU1/systemd" "$TU1/bin" "$TU1/autostart"
rc=$?
assert_exit "$rc" 0 "U3 idempotent: ponowny run = sukces"
bak_count=$(find "$TU1/autostart" -name 'setka-tray.desktop.bak-*' 2>/dev/null | wc -l)
[ "$bak_count" -eq 0 ] && pass "U3 idempotent: brak zbędnych backupów .desktop" \
  || fail "U3 idempotent: powstały backupy .desktop mimo identycznej treści ($bak_count)"

# --- Test U3-3: Brak StatusNotifierWatcher (gdbus-mock zwraca błąd) → ostrzeżenie, exit 0 ---
TU3="$(mktemp -d)"
make_src3 "$TU3/src"
# Atrapa gdbus zwracająca błąd (StatusNotifierWatcher niedostępny)
GDBUS_MOCK="$TU3/gdbus-fail"
printf '#!/usr/bin/env bash\nexit 1\n' >"$GDBUS_MOCK"
chmod +x "$GDBUS_MOCK"

GDBUS_BIN="$GDBUS_MOCK" \
  SYSTEMD_USER_DIR="$TU3/systemd" BIN_DIR="$TU3/bin" AUTOSTART_DIR="$TU3/autostart" \
  SKIP_KEYBINDINGS=1 \
  bash "$TU3/src/install.sh" >"$TU3/src/out.log" 2>&1
rc=$?
assert_exit "$rc" 0 "U3 gdbus-fail: brak StatusNotifierWatcher → exit 0 (nieblokujące)"
grep -qi 'StatusNotifierWatcher\|appindicator\|tray\|rozszerzenie' "$TU3/src/out.log" \
  && pass "U3 gdbus-fail: instalator ostrzega o braku StatusNotifierWatcher" \
  || fail "U3 gdbus-fail: brak ostrzeżenia o StatusNotifierWatcher; log: $(cat "$TU3/src/out.log" 2>/dev/null)"

# --- Test U3-4: live-keybindings.sh NIE wywoływany gdy SKIP_KEYBINDINGS=1 ---
TU4="$(mktemp -d)"
make_src3 "$TU4/src"
KB_LOG="$TU4/kb.log"
KB_LOG="$KB_LOG" SKIP_KEYBINDINGS=1 GDBUS_BIN=true \
  SYSTEMD_USER_DIR="$TU4/systemd" BIN_DIR="$TU4/bin" AUTOSTART_DIR="$TU4/autostart" \
  bash "$TU4/src/install.sh" >"$TU4/src/out.log" 2>&1
[ -s "$TU4/kb.log" ] \
  && fail "U3 skip-keybindings: keybindings wywołane mimo SKIP_KEYBINDINGS=1" \
  || pass "U3 skip-keybindings: keybindings pominięte gdy SKIP_KEYBINDINGS=1"

# --- Test U3-5: live-keybindings.sh kopiowany do BIN_DIR ---
assert_file "$TU1/bin/live-keybindings.sh" "U3 happy: live-keybindings.sh skopiowany do BIN_DIR"

# --- Test U3-6: nie-plik w bin/ (np. __pycache__/) pomijany — install nie wywala się ---
TU6="$(mktemp -d)"
make_src3 "$TU6/src"
mkdir -p "$TU6/src/bin/__pycache__"
printf 'dummy bytecode\n' >"$TU6/src/bin/__pycache__/setka-tray.cpython-312.pyc"
run_install3 "$TU6/src" "$TU6/systemd" "$TU6/bin" "$TU6/autostart"
rc=$?
assert_exit "$rc" 0 "U3 pycache: katalog w bin/ pomijany, install kończy się sukcesem"
assert_no_file "$TU6/bin/__pycache__" "U3 pycache: __pycache__ NIE skopiowany do BIN_DIR"
assert_file "$TU6/bin/setka-tray" "U3 pycache: setka-tray nadal skopiowany mimo katalogu obok"

rm -rf "$TU1" "$TU3" "$TU4" "$TU6"

printf '\n=== %d passed, %d failed ===\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
