#!/usr/bin/env bash
# ABOUTME: Instaluje regułę udev wyłączającą USB autosuspend dla sprzętu rigu live.
# ABOUTME: Wymaga roota (zapis do /etc/udev/rules.d); idempotentny; przeładowuje i wyzwala udev.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RULES_DIR="${UDEV_RULES_DIR:-/etc/udev/rules.d}"
RULE="99-setka-rig-no-autosuspend.rules"

if [ "$(id -u)" -ne 0 ]; then
  printf 'Ten instalator zapisuje do %s — uruchom przez sudo:\n' "$RULES_DIR" >&2
  printf '  sudo %s\n' "$0" >&2
  exit 1
fi

src="$SCRIPT_DIR/$RULE"
dest="$RULES_DIR/$RULE"
mkdir -p "$RULES_DIR"
if [ -f "$dest" ] && cmp -s "$src" "$dest"; then
  printf '  = %s (bez zmian)\n' "$dest"
else
  install -m 0644 "$src" "$dest"
  printf '  + %s\n' "$dest"
fi

# Przeładuj reguły i wyzwól je dla JUŻ podłączonych urządzeń (bez przepinania kabli).
udevadm control --reload
udevadm trigger --subsystem-match=usb --action=add
printf 'udev: reload + trigger (usb/add) — OK\n'
printf 'Gotowe. Sprawdź: cat /sys/bus/usb/devices/3-4/power/control  # → on\n'
