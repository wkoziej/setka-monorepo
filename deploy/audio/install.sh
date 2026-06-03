#!/usr/bin/env bash
# ABOUTME: Instaluje drop-iny systemd --user dla stacku audio (wireplumber auto-restart po wybudzeniu).
# ABOUTME: Idempotentny; kopiuje override do ~/.config/systemd/user/<unit>.d/ i robi daemon-reload.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYSTEMD_USER_DIR="${SYSTEMD_USER_DIR:-$HOME/.config/systemd/user}"
DEFAULT_SYSTEMD_USER_DIR="$HOME/.config/systemd/user"

install_dropin() {
  local src="$1" dest="$2"
  mkdir -p "$(dirname "$dest")"
  if [ -f "$dest" ] && cmp -s "$src" "$dest"; then
    printf '  = %s (bez zmian)\n' "$dest"
    return
  fi
  install -m 0644 "$src" "$dest"
  printf '  + %s\n' "$dest"
}

printf 'Instaluję drop-iny audio → %s\n' "$SYSTEMD_USER_DIR"
install_dropin "$SCRIPT_DIR/wireplumber.service.d/override.conf" \
  "$SYSTEMD_USER_DIR/wireplumber.service.d/override.conf"

if [ "$SYSTEMD_USER_DIR" = "$DEFAULT_SYSTEMD_USER_DIR" ] && command -v systemctl >/dev/null 2>&1; then
  systemctl --user daemon-reload
  printf 'systemctl --user daemon-reload — OK\n'
  printf 'UWAGA: zmiana Restart= wchodzi w życie przy następnym (re)starcie usługi:\n'
  printf '       systemctl --user restart wireplumber\n'
else
  printf 'Pomijam daemon-reload (niestandardowy SYSTEMD_USER_DIR)\n'
fi

printf 'Gotowe.\n'
