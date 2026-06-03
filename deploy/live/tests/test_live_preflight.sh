#!/usr/bin/env bash
# ABOUTME: Test logiki preflight (plain shell). Karmi czyste funkcje realnymi kształtami
# ABOUTME: wyjść pw-metadata / lsmod / /health — bez mocków, na przechwyconych danych.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFLIGHT_SH="$SCRIPT_DIR/../bin/live-preflight.sh"

PASS=0
FAIL=0
pass() { PASS=$((PASS + 1)); printf 'ok   - %s\n' "$1"; }
fail() { FAIL=$((FAIL + 1)); printf 'FAIL - %s\n' "$1"; }
assert_ok() { if "$@"; then pass "$DESC"; else fail "$DESC"; fi; }
assert_fail() { if "$@"; then fail "$DESC"; else pass "$DESC"; fi; }

# Sourcing nie może odpalić main() — guard w skrypcie ma to zapewnić.
# shellcheck disable=SC1090
source "$PREFLIGHT_SH"

# --- Realne kształty wyjść (przechwycone z maszyny) ---
PW_OK="update: id:0 key:'clock.rate' value:'44100' type:''
update: id:0 key:'clock.allowed-rates' value:'[ 44100, 48000 ]' type:''
update: id:0 key:'clock.force-rate' value:'0' type:''"

PW_BAD="update: id:0 key:'clock.rate' value:'48000' type:''
update: id:0 key:'clock.allowed-rates' value:'[ 44100, 48000 ]' type:''
update: id:0 key:'clock.force-rate' value:'0' type:''"

LSMOD_OK="snd_virmidi            16384  2
snd_seq_virmidi        20480  2 snd_virmidi
snd                   143360  41 snd_hda_intel,snd_usb_audio,snd_virmidi,snd_pcm"

LSMOD_BAD="snd_hda_intel          61440  3
snd_usb_audio         385024  2
snd_pcm               176128  5 snd_hda_intel,snd_usb_audio"

HEALTH_OK='{"pacer_input_open":true,"bridge_port_active":true,"obs_connected":true,"last_heartbeat_ts":1780470732.5}'
HEALTH_NO_PACER='{"pacer_input_open":false,"bridge_port_active":true,"obs_connected":false,"last_heartbeat_ts":1780470732.5}'
HEALTH_NO_BRIDGE='{"pacer_input_open":true,"bridge_port_active":false,"obs_connected":false,"last_heartbeat_ts":1780470732.5}'

# --- clock.rate: dokładny klucz, odporny na allowed-rates/force-rate ---
DESC="rate: 44100 → OK"; assert_ok preflight_rate_ok "$PW_OK"
DESC="rate: 48000 → fail"; assert_fail preflight_rate_ok "$PW_BAD"
DESC="rate: pusty input → fail (nie wykrztusza 44100 z allowed-rates)"; assert_fail preflight_rate_ok ""
# Twardy test pułapki: gdyby parser brał allowed-rates, ten input dałby fałszywe OK.
PW_TRAP="update: id:0 key:'clock.rate' value:'48000' type:''
update: id:0 key:'clock.allowed-rates' value:'[ 44100, 48000 ]' type:''"
DESC="rate: 48000 mimo 44100 w allowed-rates → fail (brak fałszywego dopasowania)"
assert_fail preflight_rate_ok "$PW_TRAP"

# --- snd-virmidi ---
DESC="virmidi: załadowany → OK"; assert_ok preflight_virmidi_ok "$LSMOD_OK"
DESC="virmidi: brak modułu → fail"; assert_fail preflight_virmidi_ok "$LSMOD_BAD"

# --- /health: pacer_input_open && bridge_port_active (NIE obs_connected) ---
DESC="health: pacer+bridge true → OK"; assert_ok preflight_health_ok "$HEALTH_OK"
DESC="health: pacer_input_open false → fail"; assert_fail preflight_health_ok "$HEALTH_NO_PACER"
DESC="health: bridge_port_active false → fail"; assert_fail preflight_health_ok "$HEALTH_NO_BRIDGE"
DESC="health: pusta odpowiedź (timeout) → fail, nie wybucha"; assert_fail preflight_health_ok ""
# obs_connected=false NIE może blokować (OBS startuje po preflighcie):
HEALTH_OBS_DOWN='{"pacer_input_open":true,"bridge_port_active":true,"obs_connected":false,"last_heartbeat_ts":1.0}'
DESC="health: obs_connected=false nie blokuje (OBS startuje po preflighcie)"
assert_ok preflight_health_ok "$HEALTH_OBS_DOWN"

# --- poll_ok: retry/grace nie wisi w nieskończoność ---
DESC="poll_ok: predykat-prawda zwraca 0 od razu"
assert_ok poll_ok 2 true
DESC="poll_ok: predykat-fałsz kończy się po grace (nie wisi)"
_t0=$SECONDS
if poll_ok 1 false; then fail "$DESC (zwrócił 0)"; else
  _elapsed=$((SECONDS - _t0))
  if [ "$_elapsed" -le 3 ]; then pass "$DESC (${_elapsed}s)"; else fail "$DESC (za długo: ${_elapsed}s)"; fi
fi

printf '\n=== %d passed, %d failed ===\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
