#!/usr/bin/env bash
# ABOUTME: Twarda brama gotowości warstwy live: virmidi + PipeWire 44100 + paternologia /health.
# ABOUTME: Tylko weryfikuje (nic nie ładuje/nie restartuje); niezerowy exit blokuje start GUI.
set -uo pipefail

HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:8000/health}"
# Okna retry/grace per warunek (s). virmidi jest binarny/utrwalony → krótkie; rate i health
# bywają chwilowo niegotowe (graf PipeWire się ustala, PACER replug) → dłuższe, dostrojone
# pod watchdog paternologii (RestartSec=2) i stabilizację PipeWire po wybudzeniu.
GRACE_VIRMIDI="${GRACE_VIRMIDI:-2}"
GRACE_RATE="${GRACE_RATE:-8}"
GRACE_HEALTH="${GRACE_HEALTH:-8}"
GRACE_AUDIO="${GRACE_AUDIO:-8}"

# Karty audio rigu, które MUSZĄ być widoczne w PipeWire przed startem GUI. Po re-enumeracji
# USB WirePlumber bywa, że gubi kartę (przegapiony hotplug add) — wtedy wejście na set bez
# interfejsu. Lista po fragmencie nazwy karty (pactl list cards short); konfigurowalna.
REQUIRED_AUDIO_CARDS="${REQUIRED_AUDIO_CARDS:-RC-600 Notepad}"

log() { printf 'preflight: %s\n' "$*"; }
err() { printf 'preflight: %s\n' "$*" >&2; }

# --- Czyste funkcje decyzyjne (testowalne, karmione tekstem) ---

# Wydobywa DOKŁADNIE clock.rate i porównuje z 44100. Nie może łapać clock.allowed-rates
# (np. '[ 44100, 48000 ]') ani clock.force-rate — stąd dopasowanie pełnego klucza key:'clock.rate'.
preflight_rate_ok() {
  local rate
  rate="$(printf '%s\n' "$1" | sed -n "s/.*key:'clock\.rate' value:'\([0-9]*\)'.*/\1/p" | head -1)"
  [ "$rate" = "44100" ]
}

preflight_virmidi_ok() {
  printf '%s\n' "$1" | grep -q 'snd_virmidi'
}

# Każda karta z REQUIRED_AUDIO_CARDS musi wystąpić w `pactl list cards short`. Brak choć
# jednej = WirePlumber nie ma interfejsu (najczęściej przegapiony hotplug po re-enumeracji).
preflight_audio_cards_ok() {
  local cards="$1" name
  for name in $REQUIRED_AUDIO_CARDS; do
    printf '%s\n' "$cards" | grep -qi -- "$name" || return 1
  done
  return 0
}

# /health musi mieć pacer_input_open && bridge_port_active. obs_connected celowo POMIJANE:
# OBS startuje PO preflighcie, więc websocket nie jest jeszcze podniesiony.
preflight_health_ok() {
  local json="$1"
  [ -n "$json" ] || return 1
  printf '%s' "$json" | jq -e '.pacer_input_open == true and .bridge_port_active == true' >/dev/null 2>&1
}

# --- Pętla retry/grace: nie wisi, twardo kończy po wyczerpaniu okna ---
poll_ok() {
  local grace="$1"; shift
  local deadline=$((SECONDS + grace))
  while :; do
    if "$@"; then return 0; fi
    [ "$SECONDS" -ge "$deadline" ] && return 1
    sleep 0.5
  done
}

# --- Warstwa pobierająca świeże dane przy każdej próbie (realne komendy) ---
virmidi_check_live()     { preflight_virmidi_ok "$(lsmod 2>/dev/null)"; }
rate_check_live()        { preflight_rate_ok "$(pw-metadata -n settings 2>/dev/null)"; }
health_check_live()      { preflight_health_ok "$(curl -sf "$HEALTH_URL" 2>/dev/null)"; }
audio_cards_check_live() { preflight_audio_cards_ok "$(pactl list cards short 2>/dev/null)"; }

main() {
  local rc=0
  log "sprawdzam gotowość audio/MIDI/paternologii…"

  if poll_ok "$GRACE_VIRMIDI" virmidi_check_live; then
    log "  [OK] snd-virmidi załadowany"
  else
    err "  [FAIL] snd-virmidi nie załadowany — uruchom: sudo modprobe snd-virmidi midi_devs=2"
    rc=1
  fi

  if poll_ok "$GRACE_RATE" rate_check_live; then
    log "  [OK] PipeWire clock.rate == 44100"
  else
    err "  [FAIL] PipeWire clock.rate != 44100 — RC-600 jest taktowany na 44100; ustaw graf na 44100 PRZED Bitwigiem"
    rc=1
  fi

  if poll_ok "$GRACE_AUDIO" audio_cards_check_live; then
    log "  [OK] karty audio rigu obecne w PipeWire ($REQUIRED_AUDIO_CARDS)"
  else
    err "  [FAIL] brak karty audio w PipeWire ($REQUIRED_AUDIO_CARDS) — WirePlumber zgubił interfejs po re-enumeracji USB; odzysk: systemctl --user restart wireplumber"
    rc=1
  fi

  if poll_ok "$GRACE_HEALTH" health_check_live; then
    log "  [OK] paternologia /health: pacer_input_open && bridge_port_active"
  else
    err "  [FAIL] paternologia niegotowa — podłącz PACER i sprawdź most MIDI ($HEALTH_URL)"
    rc=1
  fi

  if [ "$rc" -eq 0 ]; then
    log "preflight OK — warstwa GUI może wstać"
  else
    err "preflight FAILED — GUI nie wstanie, dopóki warunki nie będą spełnione"
  fi
  return "$rc"
}

# Odpal main tylko przy bezpośrednim wykonaniu — sourcing (testy) ma dać same funkcje.
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
  main "$@"
fi
