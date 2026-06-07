#!/usr/bin/env bash
# ABOUTME: Test dyspozytora setka-live (plain shell). Wstrzykuje rejestrator pod systemctl
# ABOUTME: (env indirekcja), by sprawdzić REALNE komendy bez mutowania żywego systemd.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETKA="$SCRIPT_DIR/../bin/setka-live"

PASS=0
FAIL=0
pass() { PASS=$((PASS + 1)); printf 'ok   - %s\n' "$1"; }
fail() { FAIL=$((FAIL + 1)); printf 'FAIL - %s\n' "$1"; }

WORK="$(mktemp -d)"
REC="$WORK/systemctl-rec"        # rejestrator udający systemctl
REC_LOG="$WORK/calls.log"
cat >"$REC" <<'EOF'
#!/usr/bin/env bash
# Rejestrator: zapisuje argumenty (jeden wpis na linię) i kończy sukcesem.
printf '%s\n' "$*" >> "$SETKA_REC_LOG"
exit 0
EOF
chmod +x "$REC"

# Rejestrator udający live-layout.sh: loguje znacznik do TEGO SAMEGO REC_LOG (widać kolejność
# względem systemctl) i kończy kodem LAYOUT_RC (domyślnie 0; 1 testuje best-effort w start).
LAYOUT_REC="$WORK/layout-rec"
cat >"$LAYOUT_REC" <<'EOF'
#!/usr/bin/env bash
printf 'LAYOUT_BIN_CALLED\n' >> "$SETKA_REC_LOG"
exit "${LAYOUT_RC:-0}"
EOF
chmod +x "$LAYOUT_REC"

# Rejestratory GIO_BIN / ZENITY_BIN / NOTIFY_BIN — wzorzec analogiczny do SYSTEMCTL_BIN.
# Zdefiniowane TU (przed run_setka), bo bramka potwierdzenia w `stop` wymaga zenity także
# w zwykłych wywołaniach run_setka, nie tylko w testach delete-last.
GIO_LOG="$WORK/gio.log"
ZENITY_LOG="$WORK/zenity.log"
NOTIFY_LOG="$WORK/notify.log"

# Rejestrator GIO_BIN: loguje argumenty; domyślnie exit 0; GIO_RC override.
GIO_REC="$WORK/gio-rec"
cat >"$GIO_REC" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$GIO_LOG"
exit "${GIO_RC:-0}"
EOF
chmod +x "$GIO_REC"

# Rejestrator ZENITY_BIN: loguje argumenty; domyślnie exit 0; ZENITY_RC override.
ZENITY_REC="$WORK/zenity-rec"
cat >"$ZENITY_REC" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$ZENITY_LOG"
exit "${ZENITY_RC:-0}"
EOF
chmod +x "$ZENITY_REC"

# Rejestrator NOTIFY_BIN: zawsze exit 0; loguje argumenty.
NOTIFY_REC="$WORK/notify-rec"
cat >"$NOTIFY_REC" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$NOTIFY_LOG"
exit 0
EOF
chmod +x "$NOTIFY_REC"

run_setka() {
  : >"$REC_LOG" >"$ZENITY_LOG"
  # ZENITY_BIN wstrzyknięty domyślnie (RC=0 = potwierdzone), by bramka `stop` przeszła w
  # zwykłych testach. Testy bramki nadpisują ZENITY_RC (anulowanie) lub ZENITY_BIN (brak zenity).
  SYSTEMCTL_BIN="$REC" SETKA_REC_LOG="$REC_LOG" \
    LAYOUT_BIN="$LAYOUT_REC" LAYOUT_RC="${LAYOUT_RC:-0}" \
    ZENITY_BIN="${ZENITY_BIN:-$ZENITY_REC}" ZENITY_RC="${ZENITY_RC:-0}" ZENITY_LOG="$ZENITY_LOG" \
    NOTIFY_BIN="$NOTIFY_REC" NOTIFY_LOG="$NOTIFY_LOG" \
    HEALTH_URL="http://127.0.0.1:59999/health" \
    bash "$SETKA" "$@" >"$WORK/out.log" 2>&1
  echo $?
}

# --- start ---
rc="$(run_setka start)"
[ "$rc" = "0" ] && pass "start: exit 0" || fail "start: exit $rc"
grep -q -- '--user start live-recording.target' "$REC_LOG" \
  && pass "start: woła 'start live-recording.target'" || fail "start: brak start targetu"

# --- stop: potwierdzone (zenity RC=0, wstrzyknięte w run_setka) → zatrzymuje target ---
rc="$(run_setka stop)"
[ "$rc" = "0" ] && pass "stop: exit 0 (potwierdzone)" || fail "stop: exit $rc"
grep -q -- '--user stop live-recording.target' "$REC_LOG" \
  && pass "stop: po potwierdzeniu woła 'stop live-recording.target'" || fail "stop: brak stop targetu"

# --- stop: anulowane (zenity RC=1) → fail-safe, NIE zatrzymuje, exit 0 ---
rc="$(ZENITY_RC=1 run_setka stop)"
[ "$rc" = "0" ] && pass "stop anulowane: exit 0 (fail-safe)" || fail "stop anulowane: exit $rc"
grep -q -- '--user stop live-recording.target' "$REC_LOG" \
  && fail "stop anulowane: NIE powinno wołać stop targetu" \
  || pass "stop anulowane: nie tknęło targetu (bezpieczne)"

# --- stop --yes: pomija potwierdzenie → zatrzymuje BEZ wywołania zenity ---
rc="$(run_setka stop --yes)"
[ "$rc" = "0" ] && pass "stop --yes: exit 0" || fail "stop --yes: exit $rc"
grep -q -- '--user stop live-recording.target' "$REC_LOG" \
  && pass "stop --yes: woła stop targetu" || fail "stop --yes: brak stop targetu"
[ -s "$ZENITY_LOG" ] \
  && fail "stop --yes: zenity NIE powinien być wołany" \
  || pass "stop --yes: pominął zenity (brak dialogu)"

# --- stop bez zenity i bez --yes → odmowa (exit !=0), NIE zatrzymuje ---
: >"$REC_LOG"
rc="$(ZENITY_BIN="$WORK/nie-ma-zenity" run_setka stop)"
[ "$rc" != "0" ] && pass "stop bez-zenity: niezerowy exit (odmowa)" || fail "stop bez-zenity: exit 0 (powinno != 0)"
grep -q -- '--user stop live-recording.target' "$REC_LOG" \
  && fail "stop bez-zenity: NIE powinno wołać stop targetu" \
  || pass "stop bez-zenity: nie tknęło targetu"
grep -qi -- '--yes' "$WORK/out.log" \
  && pass "stop bez-zenity: komunikat wskazuje furtkę --yes" || fail "stop bez-zenity: brak wskazówki --yes"

# --- restart: kluczowe inwarianty ---
rc="$(run_setka restart)"
[ "$rc" = "0" ] && pass "restart: exit 0" || fail "restart: exit $rc"
grep -q -- '--user stop live-recording.target' "$REC_LOG" \
  && pass "restart: zawiera stop targetu" || fail "restart: brak stop"
grep -q -- '--user start live-recording.target' "$REC_LOG" \
  && pass "restart: zawiera start targetu" || fail "restart: brak start"
# PUŁAPKA: nigdy `restart <target>` (nie propaguje na członków).
grep -q -- 'restart live-recording.target' "$REC_LOG" \
  && fail "restart: użyto zakazanego 'restart <target>'" \
  || pass "restart: NIE używa zakazanego 'restart <target>'"
# Kolejność: stop przed start.
stop_line="$(grep -n -- '--user stop live-recording.target' "$REC_LOG" | head -1 | cut -d: -f1)"
start_line="$(grep -n -- '--user start live-recording.target' "$REC_LOG" | head -1 | cut -d: -f1)"
[ -n "$stop_line" ] && [ -n "$start_line" ] && [ "$stop_line" -lt "$start_line" ] \
  && pass "restart: stop poprzedza start" || fail "restart: zła kolejność stop/start"
# Re-weryfikacja preflight: stop jawnie obejmuje live-preflight.service.
grep -- '--user stop' "$REC_LOG" | grep -q 'live-preflight.service' \
  && pass "restart: stop obejmuje live-preflight (re-weryfikacja przy starcie)" \
  || fail "restart: stop nie obejmuje live-preflight"

# --- NIGDY nie tyka paternologii (w żadnej komendzie, włącznie z delete-last) ---
touched_pat=0
for cmd in start stop restart status; do
  run_setka "$cmd" >/dev/null
  grep -q 'paternologia' "$REC_LOG" && touched_pat=1
done
[ "$touched_pat" -eq 0 ] && pass "żadna komenda nie dotyka paternologia.service (most MIDI nietknięty)" \
  || fail "któraś komenda dotknęła paternologia.service"

# --- status: paternologia 'down' (martwy port) → raportuje, nie wybucha ---
rc="$(run_setka status)"
[ "$rc" = "0" ] && pass "status: exit 0 mimo martwego /health" || fail "status: exit $rc"
grep -qi 'health' "$WORK/out.log" && pass "status: raportuje sekcję /health" || fail "status: brak /health w wyjściu"

# --- show: woła LAYOUT_BIN, exit 0 ---
rc="$(run_setka show)"
[ "$rc" = "0" ] && pass "show: exit 0" || fail "show: exit $rc"
grep -q -- 'LAYOUT_BIN_CALLED' "$REC_LOG" \
  && pass "show: woła LAYOUT_BIN (układanie okien)" || fail "show: nie wywołał LAYOUT_BIN"
grep -q -- '--user start' "$REC_LOG" \
  && fail "show: niepotrzebnie ruszył systemd" || pass "show: nie dotyka systemd (czysto okienkowe)"

# --- start: woła start targetu ORAZ następnie LAYOUT_BIN (layout po starcie) ---
rc="$(run_setka start)"
[ "$rc" = "0" ] && pass "start: exit 0 (z auto-layoutem)" || fail "start: exit $rc"
grep -q -- 'LAYOUT_BIN_CALLED' "$REC_LOG" \
  && pass "start: po starcie układa okna (auto-layout)" || fail "start: brak auto-layoutu"
start_ln="$(grep -n -- '--user start live-recording.target' "$REC_LOG" | head -1 | cut -d: -f1)"
layout_ln="$(grep -n -- 'LAYOUT_BIN_CALLED' "$REC_LOG" | head -1 | cut -d: -f1)"
[ -n "$start_ln" ] && [ -n "$layout_ln" ] && [ "$start_ln" -lt "$layout_ln" ] \
  && pass "start: layout następuje PO starcie targetu" || fail "start: zła kolejność start/layout"

# --- start: layout best-effort — błąd układania NIE wywraca startu (R3/R5) ---
rc="$(LAYOUT_RC=1 run_setka start)"
[ "$rc" = "0" ] && pass "start: exit 0 mimo błędu layoutu (best-effort)" || fail "start: błąd layoutu wywrócił start (exit $rc)"

# --- nieznana komenda → niezerowy exit, usage ---
rc="$(run_setka frobnicate)"
[ "$rc" != "0" ] && pass "unknown: niezerowy exit dla nieznanej komendy" || fail "unknown: exit 0 (powinno != 0)"
grep -qi 'show' "$WORK/out.log" && pass "unknown: usage wymienia komendę show" || fail "unknown: usage bez show"

# =============================================================================
# Testy delete-last (Unit 1)
# =============================================================================
# Strategia sourcowania: setka-live ma `set -euo pipefail` i source-guard wokół main "$@".
# Sourcujemy w subshellach (przez `bash -c "source ..."`), żeby:
#   (a) uniknąć zarażenia powłoki testowej przez set -e,
#   (b) każdy test miał izolowany stan.
# Funkcje testowane czysto przez sourcing ze SETKA_LIVE_SOURCED=1 (guard).
#
# Rejestratory GIO_BIN / ZENITY_BIN / NOTIFY_BIN zdefiniowane wyżej (przed run_setka).

# Pomocnicza funkcja wywołująca setka-live delete-last z wstrzykniętymi rejestratorami.
# Czyści logi przed każdym wywołaniem; dodatkowe zmienne env przez $@.
run_delete_last() {
  : >"$GIO_LOG" >"$ZENITY_LOG" >"$NOTIFY_LOG"
  GIO_LOG="$GIO_LOG" ZENITY_LOG="$ZENITY_LOG" NOTIFY_LOG="$NOTIFY_LOG" \
    GIO_BIN="$GIO_REC" ZENITY_BIN="$ZENITY_REC" NOTIFY_BIN="$NOTIFY_REC" \
    GIO_RC="${GIO_RC:-0}" ZENITY_RC="${ZENITY_RC:-0}" \
    SYSTEMCTL_BIN="$REC" SETKA_REC_LOG="$REC_LOG" \
    LAYOUT_BIN="$LAYOUT_REC" \
    HEALTH_URL="http://127.0.0.1:59999/health" \
    "$@" \
    bash "$SETKA" delete-last >"$WORK/out.log" 2>&1
  echo $?
}

# Funkcja sourcująca setka-live w subshellach dla testów czystych funkcji.
# Wywołaj: call_fn "SETKA_RECORDINGS_ROOT=/tmp/... resolve_recordings_root"
# Zwraca: stdout funkcji; exit code z subshella.
call_fn() {
  local env_and_fn="$1"
  bash -c "
    set +e
    source '$SETKA'
    $env_and_fn
  " 2>&1
}

call_fn_rc() {
  local env_and_fn="$1"
  bash -c "
    set +e
    source '$SETKA'
    $env_and_fn
  " >/dev/null 2>&1
  echo $?
}

# Pomocnicza: utwórz katalog nagrania (z metadata.json + plikiem wideo).
mk_recording() {
  local dir="$1"
  mkdir -p "$dir"
  touch "$dir/metadata.json"
  touch "$dir/clip.mp4"
}

# Pomocnicza: utwórz katalog nagrania tylko z metadata.json (bez wideo).
mk_no_video() {
  local dir="$1"
  mkdir -p "$dir"
  touch "$dir/metadata.json"
}

# Pomocnicza: utwórz katalog z wideo bez metadata.json.
mk_no_meta() {
  local dir="$1"
  mkdir -p "$dir"
  touch "$dir/clip.mp4"
}

# --- TEST 1: Happy path — 3 prawidłowe katalogi, zenity rc 0, gio trash wywoływany na najnowszym ---
REC_ROOT="$WORK/recs"
mkdir -p "$REC_ROOT"
mk_recording "$REC_ROOT/2026-01-01_10-00-00"
mk_recording "$REC_ROOT/2026-01-02_10-00-00"
mk_recording "$REC_ROOT/2026-01-03_10-00-00"
# Ustaw mtime: najnowszy to 2026-01-03
touch -d "2026-01-01 10:00:00" "$REC_ROOT/2026-01-01_10-00-00"
touch -d "2026-01-02 10:00:00" "$REC_ROOT/2026-01-02_10-00-00"
touch -d "2026-01-03 10:00:00" "$REC_ROOT/2026-01-03_10-00-00"

rc="$(SETKA_RECORDINGS_ROOT="$REC_ROOT" ZENITY_RC=0 run_delete_last)"
[ "$rc" = "0" ] && pass "delete-last happy: exit 0" || fail "delete-last happy: exit $rc"
grep -q "trash" "$GIO_LOG" \
  && pass "delete-last happy: gio trash wywołany" || fail "delete-last happy: brak gio trash"
grep -q "2026-01-03" "$GIO_LOG" \
  && pass "delete-last happy: gio trash wskazuje najnowszy katalog" \
  || fail "delete-last happy: gio trash nie wskazuje 2026-01-03; log: $(cat "$GIO_LOG" 2>/dev/null)"
grep -q "2026-01-03" "$NOTIFY_LOG" \
  && pass "delete-last happy: notify-send zawiera nazwę katalogu" \
  || fail "delete-last happy: notify-send bez nazwy; log: $(cat "$NOTIFY_LOG" 2>/dev/null)"

# --- TEST 2: Zenity anuluje (rc 1) → BRAK gio trash ---
rc="$(SETKA_RECORDINGS_ROOT="$REC_ROOT" ZENITY_RC=1 run_delete_last)"
[ "$rc" = "0" ] && pass "delete-last cancel: exit 0 po anulowaniu" || fail "delete-last cancel: exit $rc"
grep -q "trash" "$GIO_LOG" \
  && fail "delete-last cancel: gio trash NIE powinien być wywołany" \
  || pass "delete-last cancel: brak gio trash (fail-safe)"

# --- TEST 3: Katalog bez prawidłowych nagrań → notify 'brak nagrania', brak zenity, brak gio ---
EMPTY_ROOT="$WORK/empty_recs"
mkdir -p "$EMPTY_ROOT"
# Tylko zwykłe pliki lub katalogi bez metadata.json
touch "$EMPTY_ROOT/jakis_plik.txt"
mkdir -p "$EMPTY_ROOT/nieprawidlowy_podkatalog"

rc="$(SETKA_RECORDINGS_ROOT="$EMPTY_ROOT" run_delete_last)"
[ "$rc" = "0" ] && pass "delete-last brak-nagrań: exit 0" || fail "delete-last brak-nagrań: exit $rc"
[ -s "$GIO_LOG" ] \
  && fail "delete-last brak-nagrań: gio trash NIE powinien być wywołany; log: $(cat "$GIO_LOG")" \
  || pass "delete-last brak-nagrań: brak gio trash"
[ -s "$ZENITY_LOG" ] \
  && fail "delete-last brak-nagrań: zenity NIE powinien być wywołany" \
  || pass "delete-last brak-nagrań: brak zenity"
grep -qi 'brak' "$NOTIFY_LOG" \
  && pass "delete-last brak-nagrań: notify-send informuje o braku" \
  || fail "delete-last brak-nagrań: brak notify o braku; log: $(cat "$NOTIFY_LOG" 2>/dev/null)"

# --- TEST 4a: Podkatalog z metadata.json ale bez wideo → pominięty ---
PARTIAL_ROOT="$WORK/partial_recs"
mkdir -p "$PARTIAL_ROOT"
mk_no_video "$PARTIAL_ROOT/tylko_meta"
mk_no_meta  "$PARTIAL_ROOT/tylko_wideo"

rc="$(SETKA_RECORDINGS_ROOT="$PARTIAL_ROOT" run_delete_last)"
[ "$rc" = "0" ] && pass "delete-last partial: exit 0 przy braku kompletnych katalogów" \
  || fail "delete-last partial: exit $rc"
[ -s "$GIO_LOG" ] \
  && fail "delete-last partial: gio trash NIE powinien być wywołany; log: $(cat "$GIO_LOG")" \
  || pass "delete-last partial: brak gio trash dla niekompletnych katalogów"

# --- TEST 5: Walidacja roota — pusty string ---
rc="$(SETKA_RECORDINGS_ROOT="" run_delete_last)"
[ "$rc" != "0" ] && pass "delete-last root-pusty: niezerowy exit dla pustego SETKA_RECORDINGS_ROOT" \
  || fail "delete-last root-pusty: exit 0 dla pustego roota"
[ -s "$GIO_LOG" ] && fail "delete-last root-pusty: gio trash NIE powinien być wywołany" \
  || pass "delete-last root-pusty: brak gio trash"

# --- TEST 5b: Walidacja roota — ścieżka względna ---
rc="$(SETKA_RECORDINGS_ROOT="relative/path" run_delete_last)"
[ "$rc" != "0" ] && pass "delete-last root-wzgledny: odmowa dla ścieżki względnej" \
  || fail "delete-last root-wzgledny: exit 0 dla ścieżki względnej"
[ -s "$GIO_LOG" ] && fail "delete-last root-wzgledny: gio trash NIE powinien być wywołany" \
  || pass "delete-last root-wzgledny: brak gio trash"

# --- TEST 5c: Walidacja roota — nieistniejąca ścieżka ---
rc="$(SETKA_RECORDINGS_ROOT="/tmp/setka_test_nonexistent_$$" run_delete_last)"
[ "$rc" != "0" ] && pass "delete-last root-nieistniejący: odmowa dla nieistniejącej ścieżki" \
  || fail "delete-last root-nieistniejący: exit 0 dla nieistniejącej ścieżki"
[ -s "$GIO_LOG" ] && fail "delete-last root-nieistniejący: gio trash NIE powinien być wywołany" \
  || pass "delete-last root-nieistniejący: brak gio trash"

# --- TEST 5d: Walidacja roota — plik zamiast katalogu ---
TMPFILE="$WORK/not_a_dir"
touch "$TMPFILE"
rc="$(SETKA_RECORDINGS_ROOT="$TMPFILE" run_delete_last)"
[ "$rc" != "0" ] && pass "delete-last root-plik: odmowa gdy root jest plikiem" \
  || fail "delete-last root-plik: exit 0 gdy root jest plikiem"
[ -s "$GIO_LOG" ] && fail "delete-last root-plik: gio trash NIE powinien być wywołany" \
  || pass "delete-last root-plik: brak gio trash"

# --- TEST 5e: Walidacja roota — $HOME ---
rc="$(SETKA_RECORDINGS_ROOT="$HOME" run_delete_last)"
[ "$rc" != "0" ] && pass "delete-last root-HOME: odmowa gdy root == \$HOME" \
  || fail "delete-last root-HOME: exit 0 gdy root == \$HOME"
[ -s "$GIO_LOG" ] && fail "delete-last root-HOME: gio trash NIE powinien być wywołany" \
  || pass "delete-last root-HOME: brak gio trash"

# --- TEST 5f: Walidacja roota — / ---
rc="$(SETKA_RECORDINGS_ROOT="/" run_delete_last)"
[ "$rc" != "0" ] && pass "delete-last root-slash: odmowa gdy root == /" \
  || fail "delete-last root-slash: exit 0 gdy root == /"
[ -s "$GIO_LOG" ] && fail "delete-last root-slash: gio trash NIE powinien być wywołany" \
  || pass "delete-last root-slash: brak gio trash"

# --- TEST 6: Fallback roota — brak env, ~/Wideo/obs brak, ~/Videos/obs istnieje (bezpieczny HOME) ---
FAKE_HOME="$WORK/fake_home"
mkdir -p "$FAKE_HOME/Videos/obs"
mk_recording "$FAKE_HOME/Videos/obs/2026-01-01_12-00-00"

rc="$(HOME="$FAKE_HOME" ZENITY_RC=0 run_delete_last)"
[ "$rc" = "0" ] && pass "delete-last fallback: exit 0 przy fallbacku na ~/Videos/obs" \
  || fail "delete-last fallback: exit $rc"
grep -q "trash" "$GIO_LOG" \
  && pass "delete-last fallback: gio trash wywołany z katalogu ~/Videos/obs" \
  || fail "delete-last fallback: brak gio trash dla fallbacku"

# --- TEST 7: Symlink-escape — najnowszy 'podkatalog' to symlink poza root → pominięty ---
SYMLINK_ROOT="$WORK/symlink_recs"
OUTSIDE_DIR="$WORK/outside_dir"
mkdir -p "$SYMLINK_ROOT" "$OUTSIDE_DIR"
touch "$OUTSIDE_DIR/metadata.json" "$OUTSIDE_DIR/clip.mp4"
# Symlink w roocie wskazuje poza root
ln -s "$OUTSIDE_DIR" "$SYMLINK_ROOT/symlink_rec"
# Prawidłowy katalog w roocie (starszy)
mk_recording "$SYMLINK_ROOT/2026-01-01_10-00-00"
touch -d "2026-01-01 10:00:00" "$SYMLINK_ROOT/2026-01-01_10-00-00"
# Symlink ma nowszy mtime
touch -d "2026-01-04 10:00:00" "$OUTSIDE_DIR"

rc="$(SETKA_RECORDINGS_ROOT="$SYMLINK_ROOT" ZENITY_RC=0 run_delete_last)"
[ "$rc" = "0" ] && pass "delete-last symlink: exit 0 (nie zawiesza się na symlinkach)" \
  || fail "delete-last symlink: exit $rc"
# Symlink poza root powinien być pominięty; trash na prawidłowym
grep -q "outside_dir" "$GIO_LOG" \
  && fail "delete-last symlink: gio trash NIE powinien trafić poza root; log: $(cat "$GIO_LOG" 2>/dev/null)" \
  || pass "delete-last symlink: gio trash nie wyszedł poza root"

# --- TEST 8: describe_recording zawiera nazwę, wiek i rozmiar ---
DESC_DIR="$WORK/desc_recs/2026-01-05_15-30-00"
mk_recording "$DESC_DIR"
desc="$(call_fn "describe_recording '$DESC_DIR'")"
printf '%s' "$desc" | grep -q "2026-01-05" \
  && pass "describe_recording: zawiera nazwę katalogu" \
  || fail "describe_recording: brak nazwy; wynik: $desc"
# Wiek — jakakolwiek liczba lub jednostka czasu (s, min, godz, h, d, temu, ago)
printf '%s' "$desc" | grep -qE '[0-9]' \
  && pass "describe_recording: zawiera wiek (cyfry)" \
  || fail "describe_recording: brak cyfr w opisie; wynik: $desc"
# Rozmiar — du -sh zwraca np. '4,0K' lub '4.0K'
printf '%s' "$desc" | grep -qiE '[0-9]' \
  && pass "describe_recording: zawiera rozmiar" \
  || fail "describe_recording: brak rozmiaru; wynik: $desc"

# --- TEST 9: Błąd gio (rc != 0) → notify-send z błędem, nie z 'przeniesiono' ---
GIO_ROOT="$WORK/gio_err_recs"
mkdir -p "$GIO_ROOT"
mk_recording "$GIO_ROOT/2026-01-06_10-00-00"

rc="$(SETKA_RECORDINGS_ROOT="$GIO_ROOT" ZENITY_RC=0 GIO_RC=1 run_delete_last)"
# Błąd gio → niezerowy exit LUB exit 0 z powiadomieniem o błędzie
grep -qi "błąd\|error\|nie udało\|fail" "$NOTIFY_LOG" \
  && pass "delete-last gio-error: notify-send informuje o błędzie gio" \
  || fail "delete-last gio-error: brak powiadomienia o błędzie; log: $(cat "$NOTIFY_LOG" 2>/dev/null)"
grep -qi "przeniesion" "$NOTIFY_LOG" \
  && fail "delete-last gio-error: notify NIE powinien pisać 'przeniesiono' przy błędzie gio" \
  || pass "delete-last gio-error: brak fałszywego 'przeniesiono'"

# --- TEST 10a: Dispatch delete-last trafia w cmd_delete_last ---
mk_recording "$REC_ROOT/2026-01-10_10-00-00"
touch -d "2026-01-10 10:00:00" "$REC_ROOT/2026-01-10_10-00-00"
rc="$(SETKA_RECORDINGS_ROOT="$REC_ROOT" ZENITY_RC=1 run_delete_last)"
# Zenity rc=1 = anulowanie → exit 0 (nie exit 2 jak nieznana komenda)
[ "$rc" = "0" ] && pass "dispatch: delete-last → cmd_delete_last (exit 0 przy anulowaniu)" \
  || fail "dispatch: delete-last nie trafia w cmd_delete_last; exit $rc"

# --- TEST 10b: Nieznana komenda → exit 2 (regresja) ---
rc="$(run_setka frobnicate)"
[ "$rc" = "2" ] && pass "dispatch: nieznana komenda → exit 2 (regresja)" \
  || fail "dispatch: nieznana komenda exit $rc (oczekiwano 2)"

# --- TEST 10c: delete-last nie dotyka paternologia.service ---
SETKA_RECORDINGS_ROOT="$REC_ROOT" ZENITY_RC=1 run_delete_last >/dev/null
grep -q 'paternologia' "$REC_LOG" \
  && fail "delete-last: NIE powinien tykać paternologia.service" \
  || pass "delete-last: nie dotyka paternologia.service"

# --- TEST: is_recording_dir rozróżnia struktury ---
IS_REC_DIR="$WORK/is_rec_test"
mkdir -p "$IS_REC_DIR/pełny" "$IS_REC_DIR/bez_meta" "$IS_REC_DIR/bez_wideo"
touch "$IS_REC_DIR/pełny/metadata.json" "$IS_REC_DIR/pełny/clip.mkv"
touch "$IS_REC_DIR/bez_meta/clip.mp4"
touch "$IS_REC_DIR/bez_wideo/metadata.json"

rc_pelny="$(call_fn_rc "is_recording_dir '$IS_REC_DIR/pełny'")"
[ "$rc_pelny" = "0" ] && pass "is_recording_dir: pełny katalog → 0" \
  || fail "is_recording_dir: pełny katalog → $rc_pelny (oczekiwano 0)"

rc_bez_meta="$(call_fn_rc "is_recording_dir '$IS_REC_DIR/bez_meta'")"
[ "$rc_bez_meta" != "0" ] && pass "is_recording_dir: bez metadata.json → niezerowy" \
  || fail "is_recording_dir: bez metadata.json → 0 (błędnie)"

rc_bez_wideo="$(call_fn_rc "is_recording_dir '$IS_REC_DIR/bez_wideo'")"
[ "$rc_bez_wideo" != "0" ] && pass "is_recording_dir: bez wideo → niezerowy" \
  || fail "is_recording_dir: bez wideo → 0 (błędnie)"

# --- TEST (regresja): plik wideo ze SPACJAMI w nazwie (realny format OBS) ---
# Realne nagrania OBS to np. "2026-06-04 17-30-58.mp4" lub "Projekt bez nazwy.mp4".
# Wcześniejsze `ls "$dir"/$glob | grep` rozbijało nazwę na osobne argumenty i zawodziło.
mkdir -p "$IS_REC_DIR/ze spacją"
touch "$IS_REC_DIR/ze spacją/metadata.json" "$IS_REC_DIR/ze spacją/Projekt bez nazwy.mp4"
rc_spacje="$(call_fn_rc "is_recording_dir '$IS_REC_DIR/ze spacją'")"
[ "$rc_spacje" = "0" ] && pass "is_recording_dir: plik wideo ze spacjami w nazwie → 0" \
  || fail "is_recording_dir: plik wideo ze spacjami → $rc_spacje (oczekiwano 0)"

# find_latest_recording też musi znaleźć katalog z wideo ze spacjami w nazwie.
FLR_SP="$WORK/flr_spacje"
mkdir -p "$FLR_SP/2026-06-04 17-30-58"
touch "$FLR_SP/2026-06-04 17-30-58/metadata.json" "$FLR_SP/2026-06-04 17-30-58/2026-06-04 17-30-58.mp4"
latest_sp="$(call_fn "find_latest_recording '$FLR_SP'")"
printf '%s' "$latest_sp" | grep -q "17-30-58" \
  && pass "find_latest_recording: znajduje katalog z wideo ze spacjami w nazwie" \
  || fail "find_latest_recording: zwrócił '$latest_sp' (oczekiwano 17-30-58)"

# --- TEST: find_latest_recording zwraca najnowszy z kilku ---
FLR_ROOT="$WORK/flr_recs"
mkdir -p "$FLR_ROOT"
mk_recording "$FLR_ROOT/2026-02-01_10-00-00"
mk_recording "$FLR_ROOT/2026-02-02_10-00-00"
mk_recording "$FLR_ROOT/2026-02-03_10-00-00"
touch -d "2026-02-01 10:00:00" "$FLR_ROOT/2026-02-01_10-00-00"
touch -d "2026-02-02 10:00:00" "$FLR_ROOT/2026-02-02_10-00-00"
touch -d "2026-02-03 10:00:00" "$FLR_ROOT/2026-02-03_10-00-00"
latest="$(call_fn "find_latest_recording '$FLR_ROOT'")"
printf '%s' "$latest" | grep -q "2026-02-03" \
  && pass "find_latest_recording: zwraca najnowszy katalog" \
  || fail "find_latest_recording: zwrócił '$latest' (oczekiwano 2026-02-03)"

# --- TEST: resolve_recordings_root używa SETKA_RECORDINGS_ROOT gdy ustawiony ---
rr="$(call_fn "SETKA_RECORDINGS_ROOT='$REC_ROOT' resolve_recordings_root")"
[ "$rr" = "$REC_ROOT" ] \
  && pass "resolve_recordings_root: zwraca SETKA_RECORDINGS_ROOT gdy ustawiony i prawidłowy" \
  || fail "resolve_recordings_root: zwrócił '$rr' (oczekiwano $REC_ROOT)"

# --- TEST: usage wymienia delete-last ---
rc="$(run_setka frobnicate)"
grep -qi 'delete-last' "$WORK/out.log" \
  && pass "usage: wymienia delete-last" \
  || fail "usage: nie wymienia delete-last"

# =============================================================================
# Testy new-take (otwarcie czystego projektu Bitwig z szablonu)
# =============================================================================
# Mechanizm: `flatpak run <app-id> <template>` — działający Bitwig otwiera plik
# i daje nienazwany projekt z szablonu. Rejestrator FLATPAK_BIN — wzorzec jak GIO_BIN.

FLATPAK_LOG="$WORK/flatpak.log"
FLATPAK_REC="$WORK/flatpak-rec"
cat >"$FLATPAK_REC" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$FLATPAK_LOG"
exit "${FLATPAK_RC:-0}"
EOF
chmod +x "$FLATPAK_REC"

# Szablon-atrapa: .bwtemplate to katalog-pakiet, więc tworzymy katalog (test -e, nie -f).
NT_TEMPLATE="$WORK/template.bwtemplate"
mkdir -p "$NT_TEMPLATE"

# Wywołuje setka-live new-take z wstrzykniętym flatpakiem; czyści logi przed każdym wywołaniem.
run_new_take() {
  : >"$FLATPAK_LOG" >"$NOTIFY_LOG" >"$REC_LOG"
  FLATPAK_LOG="$FLATPAK_LOG" NOTIFY_LOG="$NOTIFY_LOG" \
    FLATPAK_BIN="$FLATPAK_REC" NOTIFY_BIN="$NOTIFY_REC" \
    FLATPAK_RC="${FLATPAK_RC:-0}" \
    SYSTEMCTL_BIN="$REC" SETKA_REC_LOG="$REC_LOG" \
    LAYOUT_BIN="$LAYOUT_REC" \
    HEALTH_URL="http://127.0.0.1:59999/health" \
    "$@" \
    bash "$SETKA" new-take >"$WORK/out.log" 2>&1
  echo $?
}

# --- TEST NT1: Happy path — szablon istnieje → flatpak run z app-id + szablonem ---
rc="$(BITWIG_TEMPLATE="$NT_TEMPLATE" run_new_take)"
[ "$rc" = "0" ] && pass "new-take happy: exit 0" || fail "new-take happy: exit $rc"
grep -q -- 'run' "$FLATPAK_LOG" \
  && pass "new-take happy: flatpak run wywołany" || fail "new-take happy: brak flatpak run"
grep -q 'com.bitwig.BitwigStudio' "$FLATPAK_LOG" \
  && pass "new-take happy: woła app-id Bitwiga" \
  || fail "new-take happy: brak app-id; log: $(cat "$FLATPAK_LOG" 2>/dev/null)"
grep -q 'template.bwtemplate' "$FLATPAK_LOG" \
  && pass "new-take happy: przekazuje szablon" \
  || fail "new-take happy: brak szablonu w argumentach; log: $(cat "$FLATPAK_LOG" 2>/dev/null)"
grep -qi 'bitwig\|projekt\|szablon' "$NOTIFY_LOG" \
  && pass "new-take happy: notify-send potwierdza otwarcie" \
  || fail "new-take happy: brak notify; log: $(cat "$NOTIFY_LOG" 2>/dev/null)"

# --- TEST NT2: Brak szablonu → niezerowy exit, flatpak NIE wołany ---
rc="$(BITWIG_TEMPLATE="$WORK/nieistnieje.bwtemplate" run_new_take)"
[ "$rc" != "0" ] && pass "new-take brak-szablonu: niezerowy exit" \
  || fail "new-take brak-szablonu: exit 0 (powinno != 0)"
[ -s "$FLATPAK_LOG" ] \
  && fail "new-take brak-szablonu: flatpak NIE powinien być wołany; log: $(cat "$FLATPAK_LOG")" \
  || pass "new-take brak-szablonu: brak flatpak run (FAIL FAST)"

# --- TEST NT3: Dispatch — new-take trafia w cmd_new_take (exit 0, nie 2) ---
rc="$(BITWIG_TEMPLATE="$NT_TEMPLATE" run_new_take)"
[ "$rc" = "0" ] && pass "dispatch: new-take → cmd_new_take" \
  || fail "dispatch: new-take nie trafia w cmd_new_take; exit $rc"

# --- TEST NT4: new-take nie dotyka paternologia.service (most MIDI nietknięty) ---
BITWIG_TEMPLATE="$NT_TEMPLATE" run_new_take >/dev/null
grep -q 'paternologia' "$REC_LOG" \
  && fail "new-take: NIE powinien tykać paternologia.service" \
  || pass "new-take: nie dotyka paternologia.service"

# --- TEST NT5: Błąd flatpak (rc != 0) → notify o błędzie, niezerowy exit ---
rc="$(BITWIG_TEMPLATE="$NT_TEMPLATE" FLATPAK_RC=1 run_new_take)"
[ "$rc" != "0" ] && pass "new-take flatpak-error: niezerowy exit" \
  || fail "new-take flatpak-error: exit 0 (powinno != 0)"
grep -qi 'błąd\|error\|nie udało\|fail' "$NOTIFY_LOG" \
  && pass "new-take flatpak-error: notify-send informuje o błędzie" \
  || fail "new-take flatpak-error: brak notify o błędzie; log: $(cat "$NOTIFY_LOG" 2>/dev/null)"

# --- TEST NT6: new-take czysto Bitwig — nie rusza systemd (start/stop) ---
BITWIG_TEMPLATE="$NT_TEMPLATE" run_new_take >/dev/null
grep -qE -- '--user (start|stop)' "$REC_LOG" \
  && fail "new-take: niepotrzebnie ruszył systemd" \
  || pass "new-take: nie dotyka systemd (czysto Bitwig)"

# --- TEST NT7: usage wymienia new-take ---
rc="$(run_setka frobnicate)"
grep -qi 'new-take' "$WORK/out.log" \
  && pass "usage: wymienia new-take" \
  || fail "usage: nie wymienia new-take"

# --- usage dokumentuje furtkę stop --yes ---
rc="$(run_setka frobnicate)"
grep -qi -- 'stop \[--yes\]' "$WORK/out.log" \
  && pass "usage: dokumentuje 'stop [--yes]'" \
  || fail "usage: brak 'stop [--yes]'"

rm -rf "$WORK"
printf '\n=== %d passed, %d failed ===\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
