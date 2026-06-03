#!/usr/bin/env bash
# ABOUTME: Instaluje unity i skrypty warstwy live do katalogów użytkownika (systemd --user, ~/.local/bin).
# ABOUTME: Idempotentny, backupuje różniące się pliki, wycofuje stary kiosk-autostart na rzecz trybu na żądanie.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Katalogi docelowe — nadpisywalne przez env (na potrzeby testów i nietypowych konfiguracji).
SYSTEMD_USER_DIR="${SYSTEMD_USER_DIR:-$HOME/.config/systemd/user}"
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"
AUTOSTART_DIR="${AUTOSTART_DIR:-$HOME/.config/autostart}"

# Default dla porównania, czy warto robić daemon-reload (sensowny tylko dla prawdziwego katalogu).
DEFAULT_SYSTEMD_USER_DIR="$HOME/.config/systemd/user"

STAMP="$(date +%Y%m%d-%H%M%S)"

# Kopiuje plik z backupem tylko gdy treść się różni (idempotencja: identyczna treść = no-op).
install_file() {
  local src="$1" dest="$2" mode="$3"
  if [ -f "$dest" ] && cmp -s "$src" "$dest"; then
    printf '  = %s (bez zmian)\n' "$dest"
    return
  fi
  if [ -f "$dest" ]; then
    local bak="${dest}.bak-${STAMP}"
    cp -p "$dest" "$bak"
    printf '  ~ backup: %s\n' "$bak"
  fi
  install -m "$mode" "$src" "$dest"
  printf '  + %s\n' "$dest"
}

main() {
  mkdir -p "$SYSTEMD_USER_DIR" "$BIN_DIR"

  printf 'Instaluję unity systemd → %s\n' "$SYSTEMD_USER_DIR"
  shopt -s nullglob
  for unit in "$SCRIPT_DIR"/units/*; do
    install_file "$unit" "$SYSTEMD_USER_DIR/$(basename "$unit")" 0644
  done

  printf 'Instaluję skrypty → %s\n' "$BIN_DIR"
  for script in "$SCRIPT_DIR"/bin/*; do
    install_file "$script" "$BIN_DIR/$(basename "$script")" 0755
  done
  shopt -u nullglob

  # Wycofanie starego kiosk-autostartu: kiosk przechodzi pod systemd (tryb na żądanie, R5).
  # Zmiana nazwy poza rozszerzenie .desktop wyłącza autostart GNOME, zachowując odwracalność.
  local old_kiosk="$AUTOSTART_DIR/paternologia-kiosk.desktop"
  if [ -f "$old_kiosk" ]; then
    local bak="${old_kiosk}.disabled-${STAMP}"
    mv "$old_kiosk" "$bak"
    printf 'Wycofano stary kiosk-autostart → %s\n' "$bak"
  else
    printf 'Stary kiosk-autostart nieobecny — pomijam (no-op)\n'
  fi

  # daemon-reload ma sens tylko dla prawdziwego katalogu systemd usera.
  if [ "$SYSTEMD_USER_DIR" = "$DEFAULT_SYSTEMD_USER_DIR" ] && command -v systemctl >/dev/null 2>&1; then
    systemctl --user daemon-reload
    printf 'systemctl --user daemon-reload — OK\n'
  else
    printf 'Pomijam daemon-reload (niestandardowy SYSTEMD_USER_DIR)\n'
  fi

  # Ostrzeżenie o PATH — nie błąd: instalacja plików się powiodła, ale skrypty mogą być niewidoczne.
  case ":$PATH:" in
    *":$BIN_DIR:"*) : ;;
    *) printf 'UWAGA: %s nie jest w PATH — dodaj go, by komendy (np. setka-live) były widoczne.\n' "$BIN_DIR" ;;
  esac

  printf 'Gotowe.\n'
}

main "$@"
