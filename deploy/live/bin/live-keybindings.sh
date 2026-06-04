#!/usr/bin/env bash
# ABOUTME: Instaluje globalne skróty GNOME dla akcji setka-live przez gsettings (custom-keybindings).
# ABOUTME: Idempotentny: append-if-absent; nie nadpisuje customów użytkownika; obsługuje @as [].
set -uo pipefail

# Indirekcja przez env — dla testów zamienialna na recorder-mock.
GSETTINGS_BIN="${GSETTINGS_BIN:-gsettings}"

# Domyślne klawisze — nadpisywalne przez env.
KB_SHOW="${KB_SHOW:-<Super><Shift>s}"
KB_DELETE="${KB_DELETE:-<Super><Shift>d}"
KB_NEW_TAKE="${KB_NEW_TAKE:-<Super><Shift>n}"

# Komenda setka-live — absolutna ścieżka z env (przekazywana przez install.sh).
# Bez absolutnej ścieżki GNOME może jej nie znaleźć (skróty uruchamiane bez PATH użytkownika).
SETKA_LIVE_CMD="${SETKA_LIVE_CMD:-setka-live}"

# Stałe gsettings
MEDIA_KEYS_SCHEMA="org.gnome.settings-daemon.plugins.media-keys"
BINDING_SCHEMA="org.gnome.settings-daemon.plugins.media-keys.custom-keybinding"
BINDING_PREFIX="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings"

log() { printf 'keybindings: %s\n' "$*"; }
err() { printf 'keybindings: BŁĄD: %s\n' "$*" >&2; }

# Pobiera bieżącą listę custom-keybindings jako surowy string z gsettings.
_get_list() {
    "$GSETTINGS_BIN" get "$MEDIA_KEYS_SCHEMA" custom-keybindings
}

# Sprawdza, czy podana ścieżka <path> już jest w liście gsettings.
# Zwraca 0 jeśli jest, 1 jeśli nie.
_path_in_list() {
    local path="$1"
    local current
    current="$(_get_list)"
    case "$current" in
        *"$path"*) return 0 ;;
        *)          return 1 ;;
    esac
}

# Buduje nową listę gsettings z istniejącą zawartością + nową ścieżką.
# Obsługuje dwa przypadki:
#   @as []  →  nowa lista z jednym elementem
#   [...]   →  dołącz nowy element na końcu
_append_path() {
    local path="$1"
    local current
    current="$(_get_list)"

    local new_list
    if [ "$current" = "@as []" ]; then
        # Pusta lista — tylko nasz element
        new_list="['${path}']"
    else
        # Niepusta lista: usuń końcowy ']', dołącz ', <path>']
        # Format: ['a/', 'b/'] → ['a/', 'b/', '<path>']
        new_list="${current%]}, '${path}']"
    fi

    "$GSETTINGS_BIN" set "$MEDIA_KEYS_SCHEMA" custom-keybindings "$new_list"
}

# Ustawia atrybuty per-binding dla relocatable schema.
# Ścieżka MUSI kończyć się '/'.
_set_binding() {
    local path="$1" name="$2" command="$3" keys="$4"
    local schema_with_path="${BINDING_SCHEMA}:${path}"
    "$GSETTINGS_BIN" set "$schema_with_path" name "$name"
    "$GSETTINGS_BIN" set "$schema_with_path" command "$command"
    "$GSETTINGS_BIN" set "$schema_with_path" binding "$keys"
}

# Dodaje skrót GNOME idempotentnie.
# Argumenty: <path> <name> <command> <keys>
# Ścieżka musi kończyć się '/'.
kb_add() {
    local path="$1" name="$2" command="$3" keys="$4"

    if _path_in_list "$path"; then
        log "skrót już w liście: $path (no-op)"
    else
        log "dodaję skrót: $path"
        _append_path "$path"
    fi

    # Per-binding ustawiamy zawsze (idempotentne set nie szkodzi; może zaktualizować binding/cmd).
    _set_binding "$path" "$name" "$command" "$keys"
    log "  name='$name' command='$command' binding='$keys'"
}

# Instaluje oba skróty setka-live.
main() {
    local show_path="${BINDING_PREFIX}/setka-show/"
    local delete_path="${BINDING_PREFIX}/setka-delete-last/"
    local new_take_path="${BINDING_PREFIX}/setka-new-take/"

    kb_add "$show_path" \
        "Setka: Pokaż okna" \
        "${SETKA_LIVE_CMD} show" \
        "$KB_SHOW"

    kb_add "$delete_path" \
        "Setka: Usuń ostatnie nagranie" \
        "${SETKA_LIVE_CMD} delete-last" \
        "$KB_DELETE"

    kb_add "$new_take_path" \
        "Setka: Nowy projekt Bitwig" \
        "${SETKA_LIVE_CMD} new-take" \
        "$KB_NEW_TAKE"

    log "skróty zainstalowane: show=$KB_SHOW delete-last=$KB_DELETE new-take=$KB_NEW_TAKE"
}

# Odpal main lub zadaną funkcję zależnie od argumentów.
# Bez argumentów: main() instaluje oba skróty.
# Z argumentem 'kb_add ...': wywołuje kb_add (dla testów i ręcznych wywołań).
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    case "${1:-}" in
        kb_add)
            shift
            kb_add "$@"
            ;;
        *)
            main "$@"
            ;;
    esac
fi
