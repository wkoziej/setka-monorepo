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

# Indirekcja gdbus przez env — dla testów zamienialna na mock.
GDBUS_BIN="${GDBUS_BIN:-gdbus}"

# Gate dla efektów ubocznych gsettings: pomijaj keybindings w testach lub przy env SKIP_KEYBINDINGS.
SKIP_KEYBINDINGS="${SKIP_KEYBINDINGS:-}"

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
    # Pomijaj nie-pliki (np. __pycache__/ powstały po imporcie setka-tray w testach).
    [ -f "$script" ] || continue
    install_file "$script" "$BIN_DIR/$(basename "$script")" 0755
  done
  shopt -u nullglob

  # Instalacja autostart .desktop dla setka-tray z podstawieniem absolutnej ścieżki Exec.
  # Placeholder __SETKA_TRAY_EXEC__ zastępowany przez bezwzględną ścieżkę setka-tray w BIN_DIR.
  local desktop_src="$SCRIPT_DIR/autostart/setka-tray.desktop"
  if [ -f "$desktop_src" ]; then
    mkdir -p "$AUTOSTART_DIR"
    local desktop_tmp
    desktop_tmp="$(mktemp)"
    sed "s|__SETKA_TRAY_EXEC__|${BIN_DIR}/setka-tray|g" "$desktop_src" >"$desktop_tmp"
    install_file "$desktop_tmp" "$AUTOSTART_DIR/setka-tray.desktop" 0644
    rm -f "$desktop_tmp"
    printf 'Zainstalowano autostart traya → %s/setka-tray.desktop\n' "$AUTOSTART_DIR"
  else
    printf 'UWAGA: brak %s — autostart setka-tray pominięty\n' "$desktop_src"
  fi

  # Instalacja skrótów GNOME przez live-keybindings.sh.
  # Efekt uboczny na żywym gsettings — pomijany gdy SKIP_KEYBINDINGS lub niestandardowy BIN_DIR.
  if [ -z "$SKIP_KEYBINDINGS" ] && [ "$BIN_DIR" = "$HOME/.local/bin" ]; then
    if [ -x "$BIN_DIR/live-keybindings.sh" ]; then
      SETKA_LIVE_CMD="$BIN_DIR/setka-live" bash "$BIN_DIR/live-keybindings.sh" \
        && printf 'Skróty GNOME zainstalowane (Super+Shift+S show, Super+Shift+D delete-last)\n' \
        || printf 'UWAGA: instalacja skrótów GNOME nie powiodła się — pomiń i skonfiguruj ręcznie\n'
    else
      printf 'UWAGA: brak %s/live-keybindings.sh — skróty GNOME pominięte\n' "$BIN_DIR"
    fi
  else
    printf 'Pomijam instalację skrótów GNOME (SKIP_KEYBINDINGS lub niestandardowy BIN_DIR)\n'
  fi

  # Defensywny check: rozszerzenie StatusNotifierWatcher (appindicator) dla setka-tray.
  # Brak → ostrzeżenie (nie błąd); tray może nie wyświetlać ikony bez rozszerzenia.
  # ProtocolVersion to właściwość D-Bus, nie metoda — sprawdzamy obecność właściciela nazwy
  # org.kde.StatusNotifierWatcher na busie (zwraca '(true,)' gdy rozszerzenie aktywne).
  if ! "$GDBUS_BIN" call --session \
      --dest org.freedesktop.DBus \
      --object-path /org/freedesktop/DBus \
      --method org.freedesktop.DBus.NameHasOwner org.kde.StatusNotifierWatcher \
      2>/dev/null | grep -q 'true'; then
    printf 'UWAGA: StatusNotifierWatcher niedostępny — zainstaluj rozszerzenie GNOME appindicator.\n'
    printf '       setka-tray może nie wyświetlać ikony do czasu zainstalowania rozszerzenia.\n'
  fi

  # Defensywne checki zależności GUI (niefatalne; ostrzeżenia operatorskie).
  for tool in zenity notify-send gio; do
    if ! command -v "$tool" >/dev/null 2>&1; then
      printf 'UWAGA: brak %s — "setka-live delete-last" może działać nieprawidłowo. Zainstaluj: sudo apt install %s\n' "$tool" "$tool"
    fi
  done
  for pkg in gir1.2-gtk-3.0 gir1.2-ayatanaappindicator3-0.1; do
    if ! dpkg -l "$pkg" >/dev/null 2>&1; then
      printf 'UWAGA: pakiet %s niezainstalowany — setka-tray wymaga go do wyświetlenia ikony.\n' "$pkg"
    fi
  done

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

  # wmctrl jest potrzebny tylko dla `setka-live show` (układanie okien). Jego brak NIE blokuje
  # instalacji unitów/skryptów — to nakładka okienkowa, nie rdzeń nagrywania (FAIL FAST dotyczy
  # błędów krytycznych, nie braku opcjonalnego narzędzia okiennego). Ostrzegamy, nie przerywamy.
  if ! command -v wmctrl >/dev/null 2>&1; then
    printf 'UWAGA: brak wmctrl — "setka-live show" (układanie okien) nie zadziała. Zainstaluj: sudo apt install wmctrl\n'
  fi

  printf 'Gotowe.\n'
}

main "$@"
