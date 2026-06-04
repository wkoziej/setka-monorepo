#!/usr/bin/env bash
# ABOUTME: Testy live-keybindings.sh — weryfikuje idempotentne dodawanie skrótów GNOME przez gsettings.
# ABOUTME: Używa recorder-mock gsettings (env GSETTINGS_BIN) zamiast żywego sesji.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KB_SH="$SCRIPT_DIR/../bin/live-keybindings.sh"

PASS=0
FAIL=0
pass() { PASS=$((PASS + 1)); printf 'ok   - %s\n' "$1"; }
fail() { FAIL=$((FAIL + 1)); printf 'FAIL - %s\n' "$1"; }

WORK="$(mktemp -d)"
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

# ---------------------------------------------------------------------------
# Recorder-mock gsettings
#
# Obsługuje dwa tryby:
#   get  <schema> <key>   → wypisuje wartość z MOCK_LIST (lub @as [] gdy puste)
#   set  <schema> <key> <val> → loguje do GSETTINGS_LOG
#
# Zmienne sterujące:
#   MOCK_LIST  — wartość zwracana przez `get ... custom-keybindings` (domyślnie '@as []')
#   GSETTINGS_LOG — ścieżka do pliku logu (musi być ustawiona przez testy)
# ---------------------------------------------------------------------------
GSETTINGS_REC="$WORK/gsettings-rec"
cat >"$GSETTINGS_REC" <<'EOF'
#!/usr/bin/env bash
# Recorder-mock gsettings: get zwraca MOCK_LIST; set loguje do GSETTINGS_LOG.
cmd="$1"
shift
if [ "$cmd" = "get" ]; then
    # Argumenty: <schema> <key>
    # Zwracamy MOCK_LIST jeśli pytają o custom-keybindings, inaczej pusty as.
    key="${2:-}"
    if [ "$key" = "custom-keybindings" ]; then
        printf '%s\n' "${MOCK_LIST:-@as []}"
    else
        # Dla per-binding get zwracamy puste (nie jest testowane bezpośrednio)
        printf "''\n"
    fi
elif [ "$cmd" = "set" ]; then
    printf 'set %s\n' "$*" >> "${GSETTINGS_LOG:-/dev/null}"
else
    # Passthrough dla innych komend (nieużywane w testach)
    printf 'cmd=%s args=%s\n' "$cmd" "$*" >> "${GSETTINGS_LOG:-/dev/null}"
fi
exit 0
EOF
chmod +x "$GSETTINGS_REC"

GSETTINGS_LOG="$WORK/gsettings.log"

# Uruchamia kb_add z recorder-mock gsettings.
# Argumenty: path name command keys [extra env vars...]
run_kb_add() {
    local path="$1" name="$2" command="$3" keys="$4"
    shift 4
    : >"$GSETTINGS_LOG"
    GSETTINGS_BIN="$GSETTINGS_REC" \
        GSETTINGS_LOG="$GSETTINGS_LOG" \
        MOCK_LIST="${MOCK_LIST:-@as []}" \
        "$@" \
        bash "$KB_SH" kb_add "$path" "$name" "$command" "$keys" >"$WORK/kb.out" 2>&1
    echo $?
}

# Uruchamia install_keybindings z recorder-mock gsettings.
run_install_keybindings() {
    : >"$GSETTINGS_LOG"
    GSETTINGS_BIN="$GSETTINGS_REC" \
        GSETTINGS_LOG="$GSETTINGS_LOG" \
        MOCK_LIST="${MOCK_LIST:-@as []}" \
        "$@" \
        bash "$KB_SH" >"$WORK/kb.out" 2>&1
    echo $?
}

# ---------------------------------------------------------------------------
# TEST 1: Happy path — pusta lista @as [] → kb_add dodaje ścieżkę i ustawia per-binding
# ---------------------------------------------------------------------------
MOCK_LIST="@as []" \
rc="$(run_kb_add \
    '/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/setka-show/' \
    'Setka: Pokaż okna' \
    'setka-live show' \
    '<Super><Shift>s')"
[ "$rc" = "0" ] \
    && pass "kb_add pusta-lista: exit 0" \
    || fail "kb_add pusta-lista: exit $rc"

# Lista custom-keybindings powinna być ustawiona (set na głównej schemie media-keys)
grep -q "set org.gnome.settings-daemon.plugins.media-keys custom-keybindings" "$GSETTINGS_LOG" \
    && pass "kb_add pusta-lista: ustawia custom-keybindings" \
    || fail "kb_add pusta-lista: brak set custom-keybindings; log: $(cat "$GSETTINGS_LOG" 2>/dev/null)"

# Per-binding name ustawione
grep -q "set.*setka-show.*name" "$GSETTINGS_LOG" \
    && pass "kb_add pusta-lista: ustawia name per-binding" \
    || fail "kb_add pusta-lista: brak set name; log: $(cat "$GSETTINGS_LOG" 2>/dev/null)"

# Per-binding command ustawione
grep -q "set.*setka-show.*command" "$GSETTINGS_LOG" \
    && pass "kb_add pusta-lista: ustawia command per-binding" \
    || fail "kb_add pusta-lista: brak set command; log: $(cat "$GSETTINGS_LOG" 2>/dev/null)"

# Per-binding binding ustawione
grep -q "set.*setka-show.*binding" "$GSETTINGS_LOG" \
    && pass "kb_add pusta-lista: ustawia binding per-binding" \
    || fail "kb_add pusta-lista: brak set binding; log: $(cat "$GSETTINGS_LOG" 2>/dev/null)"

# ---------------------------------------------------------------------------
# TEST 2: Idempotencja — ścieżka już w liście → no-op (brak ponownego set listy)
# ---------------------------------------------------------------------------
MOCK_LIST="['/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/setka-show/']" \
rc="$(run_kb_add \
    '/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/setka-show/' \
    'Setka: Pokaż okna' \
    'setka-live show' \
    '<Super><Shift>s')"
[ "$rc" = "0" ] \
    && pass "kb_add idempotent: exit 0" \
    || fail "kb_add idempotent: exit $rc"

# Nie powinno set custom-keybindings gdy ścieżka już jest.
# Szukamy wpisu dla głównej schematy media-keys (klucz 'custom-keybindings'), nie per-binding.
grep -q "set org.gnome.settings-daemon.plugins.media-keys custom-keybindings" "$GSETTINGS_LOG" \
    && fail "kb_add idempotent: zbędny set custom-keybindings przy istniejącej ścieżce; log: $(cat "$GSETTINGS_LOG")" \
    || pass "kb_add idempotent: brak set custom-keybindings (no-op dla listy)"

# ---------------------------------------------------------------------------
# TEST 3: Lista z istniejącym customem użytkownika → nowa ścieżka dopisana, stara zachowana
# ---------------------------------------------------------------------------
USER_CUSTOM="'/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/moj-skrot/'"
MOCK_LIST="[$USER_CUSTOM]" \
rc="$(run_kb_add \
    '/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/setka-show/' \
    'Setka: Pokaż okna' \
    'setka-live show' \
    '<Super><Shift>s')"
[ "$rc" = "0" ] \
    && pass "kb_add zachowaj-custom: exit 0" \
    || fail "kb_add zachowaj-custom: exit $rc"

# Nowa ścieżka musi trafić do listy (set na głównej schemie media-keys)
grep -q "set org.gnome.settings-daemon.plugins.media-keys custom-keybindings" "$GSETTINGS_LOG" \
    && pass "kb_add zachowaj-custom: ustawia custom-keybindings" \
    || fail "kb_add zachowaj-custom: brak set custom-keybindings; log: $(cat "$GSETTINGS_LOG" 2>/dev/null)"

# Stary custom musi być zachowany w nowej liście
grep "set.*custom-keybindings" "$GSETTINGS_LOG" | grep -q "moj-skrot" \
    && pass "kb_add zachowaj-custom: stary custom zachowany w liście" \
    || fail "kb_add zachowaj-custom: stary custom zgubiony; log: $(cat "$GSETTINGS_LOG" 2>/dev/null)"

# ---------------------------------------------------------------------------
# TEST 4: install_keybindings (main) — rejestruje oba skróty (show + delete-last)
# ---------------------------------------------------------------------------
MOCK_LIST="@as []" \
rc="$(SETKA_LIVE_CMD="$WORK/fake-setka-live" \
    KB_SHOW='<Super><Shift>s' \
    KB_DELETE='<Super><Shift>d' \
    run_install_keybindings)"
[ "$rc" = "0" ] \
    && pass "install_keybindings: exit 0" \
    || fail "install_keybindings: exit $rc; out: $(cat "$WORK/kb.out" 2>/dev/null)"

grep -q "setka-show" "$GSETTINGS_LOG" \
    && pass "install_keybindings: rejestruje setka-show" \
    || fail "install_keybindings: brak setka-show; log: $(cat "$GSETTINGS_LOG" 2>/dev/null)"

grep -q "setka-delete-last" "$GSETTINGS_LOG" \
    && pass "install_keybindings: rejestruje setka-delete-last" \
    || fail "install_keybindings: brak setka-delete-last; log: $(cat "$GSETTINGS_LOG" 2>/dev/null)"

# ---------------------------------------------------------------------------
# TEST 5: install_keybindings — SETKA_LIVE_CMD używany w command (absolutna ścieżka)
# ---------------------------------------------------------------------------
MOCK_LIST="@as []"
FAKE_CMD="/opt/setka/bin/setka-live"
rc="$(SETKA_LIVE_CMD="$FAKE_CMD" \
    KB_SHOW='<Super><Shift>s' \
    KB_DELETE='<Super><Shift>d' \
    run_install_keybindings)"
[ "$rc" = "0" ] \
    && pass "install_keybindings cmd-abs: exit 0" \
    || fail "install_keybindings cmd-abs: exit $rc"

grep -q "$FAKE_CMD" "$GSETTINGS_LOG" \
    && pass "install_keybindings cmd-abs: SETKA_LIVE_CMD w komendach" \
    || fail "install_keybindings cmd-abs: brak SETKA_LIVE_CMD w logu; log: $(cat "$GSETTINGS_LOG" 2>/dev/null)"

printf '\n=== %d passed, %d failed ===\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
