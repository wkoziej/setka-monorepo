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

run_setka() {
  : >"$REC_LOG"
  SYSTEMCTL_BIN="$REC" SETKA_REC_LOG="$REC_LOG" \
    HEALTH_URL="http://127.0.0.1:59999/health" \
    bash "$SETKA" "$@" >"$WORK/out.log" 2>&1
  echo $?
}

# --- start ---
rc="$(run_setka start)"
[ "$rc" = "0" ] && pass "start: exit 0" || fail "start: exit $rc"
grep -q -- '--user start live-recording.target' "$REC_LOG" \
  && pass "start: woła 'start live-recording.target'" || fail "start: brak start targetu"

# --- stop ---
rc="$(run_setka stop)"
[ "$rc" = "0" ] && pass "stop: exit 0" || fail "stop: exit $rc"
grep -q -- '--user stop live-recording.target' "$REC_LOG" \
  && pass "stop: woła 'stop live-recording.target'" || fail "stop: brak stop targetu"

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

# --- NIGDY nie tyka paternologii (w żadnej komendzie) ---
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

# --- nieznana komenda → niezerowy exit, usage ---
rc="$(run_setka frobnicate)"
[ "$rc" != "0" ] && pass "unknown: niezerowy exit dla nieznanej komendy" || fail "unknown: exit 0 (powinno != 0)"

rm -rf "$WORK"
printf '\n=== %d passed, %d failed ===\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
