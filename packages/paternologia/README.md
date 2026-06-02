# Paternologia

Aplikacja webowa do zarządzania konfiguracjami MIDI dla utworów muzycznych. Głównym kontrolerem jest **Nektar Pacer** (do 6 przycisków, każdy z maksymalnie 6 akcjami MIDI). Paternologia pozwala edytować utwory w UI, eksportować je do plików `.syx`, wysyłać bezpośrednio do Pacera oraz prowadzić widok live z synchronizacją po MIDI.

## Wymagania

- Python ≥ 3.12
- [`uv`](https://docs.astral.sh/uv/) do zarządzania zależnościami
- `amidi` (ALSA) do komunikacji z Pacerem (Linux)
- Opcjonalnie podłączone urządzenia MIDI (Pacer, BOSS RC-600, Elektron Model:Samples, Arturia MicroFreak)

## Instalacja

```bash
uv sync
```

## Uruchomienie

```bash
# Tryb deweloperski (hot reload)
uv run fastapi dev src/paternologia/main.py

# Produkcja
uv run fastapi run src/paternologia/main.py
```

UI dostępne pod `http://127.0.0.1:8000`.

`PATERNOLOGIA_DATA_DIR` nadpisuje domyślną lokalizację konfiguracji (domyślnie
`data/` w katalogu pakietu).

## Model A — orkiestracja MIDI (OBS + Bitwig)

paternologia jest **jedynym czytelnikiem PACER** (czyta **oba** porty USB: MIDI1 +
MIDI2) i robi fan-out całego strumienia (poza System Real-Time) na port MIDI widoczny
dla Bitwiga.

**Most → snd-virmidi (wymagane dla Bitwiga).** Bitwig na Linuksie widzi tylko porty
rawmidi/sprzętowe, **nie** wirtualne porty ALSA seq. Dlatego most pisze wprost do
portu **`snd-virmidi`** (widocznego jako „Virtual Raw MIDI" w Bitwigu); gdy virmidi nie
ma — fallback do własnego portu seq `setka-bridge` (niewidocznego dla Bitwiga).

```bash
# Załaduj moduł (i utrwal na reboot):
sudo modprobe snd-virmidi midi_devs=2
echo snd-virmidi | sudo tee /etc/modules-load.d/snd-virmidi.conf
echo "options snd-virmidi midi_devs=2" | sudo tee /etc/modprobe.d/snd-virmidi.conf
```

**W Bitwigu (Settings → Controllers, Generic MIDI):** MIDI Input = **„Virtual Raw MIDI 1"**
(pierwszy port virmidi — ten sam, który otwiera most). **Wyłącz surowe `PACER MIDI1/2`**
jako wejścia — to usuwa błąd `Device or resource busy` (EBUSY). Record mapujesz przez
**MIDI-learn** na trigger (obecnie **Note 95** z PACER MIDI2). Arm ścieżek ręcznie.

Host Pythona musi być **natywny** (nie Flatpak).

### Nagrywanie OBS (one-button)

paternologia steruje nagrywaniem OBS przez **obs-websocket v5** (`obsws-python`).
Dedykowane przyciski PACER (noty z MIDI2) startują i zatrzymują nagranie:

- **START** = Note 94 → `OBS StartRecord` (+ ta sama nota mostem do Bitwiga → Record).
- **STOP** = Note 93 → `OBS StopRecord`.

Konfiguracja w `data/obs.yaml` (host/port/hasło, `enabled`) oraz w `pacer.yaml`
(`record_trigger_channel`, `record_start_note`, `record_stop_note`). Włącz w OBS:
**Tools → WebSocket Server Settings → Enable** i wpisz hasło do `obs.yaml`.

> „One button" = **dwa nieskoordynowane triggery**: OBS startuje kodem (websocket,
> asynchronicznie + reconnect), Bitwig dostaje tę samą notę mostem (natychmiast,
> passthrough). Jeśli OBS jest rozłączony przy wciśnięciu — Bitwig nagrywa, OBS nie.
> `/health` (`obs_connected`) ujawnia rozjazd. Start nie jest atomowy.

Komendy są **idempotentne** (powtórny START w trakcie nagrania = no-op) i izolowane:
awaria OBS nie wywala listenera MIDI (fan-out do Bitwiga to ścieżka krytyczna live).

### Usługa systemd (--user)

```bash
mkdir -p ~/.config/systemd/user
cp packages/paternologia/deploy/paternologia.service ~/.config/systemd/user/
# Dostosuj WorkingDirectory / ścieżkę do uv w pliku, potem:
systemctl --user daemon-reload
systemctl --user enable --now paternologia
loginctl enable-linger "$USER"   # serwis działa bez aktywnej sesji
```

`Restart=always` + watchdog `Type=notify` (z `NotifyAccess=all`, bo READY/WATCHDOG idzie
spod `uv run`) podnoszą proces po crashu/zawiśnięciu (~2 s). Bitwig słucha sprzętowego
`hw:Virmidi`, który trwa niezależnie od paternologii — link most→virmidi wraca sam po
restarcie usługi.

### Zdrowie i replug

- `GET /health` → `pacer_input_open`, `bridge_port_active`, `obs_connected`,
  `last_heartbeat_ts` (wskaźnik na drugim ekranie podczas występu).
- Po przepięciu PACER wejście jest reotwierane po nazwie (poll co ~2 s); port
  mostka pozostaje aktywny przez cały czas.

## Testy

```bash
uv run pytest                      # wszystkie testy
uv run pytest tests/test_models.py # pojedynczy plik
uv run pytest -k pacer             # filtr po nazwie
```

## Struktura projektu

```
src/paternologia/
  main.py            # punkt wejścia FastAPI + lifespan (MIDI listener)
  models.py          # Pydantic: Device, Action, PacerButton, Song, PacerConfig
  storage.py         # YAML I/O (devices, songs, pacer config, songs_order)
  dependencies.py    # współdzielone zależności (storage, templates)
  cli.py             # konsolowy entry point (uvicorn)
  routers/           # songs, devices, pacer, live, health
  midi/              # listener (rtmidi), bridge (fan-out), index, EventBus, ports
  pacer/             # SysEx, mappings A1-D6, export .syx
deploy/              # paternologia.service (systemd --user)
templates/           # Jinja2 + HTMX + TailwindCSS (CDN)
static/              # zasoby statyczne (CSS)
data/                # devices.yaml, pacer.yaml, songs/*.yaml, songs_order.yaml
tests/               # pytest (modele, storage, API, E2E, MIDI, bridge, health, Pacer)
```

## Główne funkcje

- **Edytor utworów** - definiowanie przycisków Pacera i akcji MIDI (preset / pattern / CC / note)
- **Drag-and-drop** kolejności utworów (`data/songs_order.yaml`)
- **Eksport `.syx`** - generowanie plików dla Pacera (`pacer/export.py`)
- **Bezpośrednia wysyłka** - integracja z `amidi` (z wymaganym `--sysex-interval=20`)
- **Widok live** - nasłuch MIDI z Pacera + SSE → automatyczne podświetlanie aktualnego utworu/przycisku

## Format danych

Patrz `CLAUDE.md` (sekcja "Data Format") oraz `SPEC.md`.

## Specyfikacje

- `SPEC.md` - ogólna specyfikacja produktu
- `SPEC_PACER_BRIDGE.md` - integracja Paternologia ↔ Pacer
- `SPEC_PACER_EXPORT_v2.md` - eksport `.syx` (faza 2)
- `SPEC_DEVICE_BACKUP.md` - backup/restore urządzeń

## Pacer - krytyczne ostrzeżenia

> **NIGDY** nie wysyłaj SysEx z `TARGET_GLOBAL (0x05) + elm=0x1E (Current User Preset)` - to bricuje Pacera i wymaga factory reset. Szczegóły w `CLAUDE.md`.

> **ZAWSZE** używaj `--sysex-interval=20` przy wysyłce do Pacera, inaczej wiadomości giną.

## Licencja

Brak (projekt prywatny).
