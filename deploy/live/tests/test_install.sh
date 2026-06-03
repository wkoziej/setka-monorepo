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

rm -rf "$T1" "$T4" "$T5" "$T6"

printf '\n=== %d passed, %d failed ===\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
