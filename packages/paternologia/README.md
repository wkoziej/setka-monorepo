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
  routers/           # songs, devices, pacer, live
  midi/              # listener (rtmidi), index, EventBus, ports
  pacer/             # SysEx, mappings A1-D6, export .syx
templates/           # Jinja2 + HTMX + TailwindCSS (CDN)
static/              # zasoby statyczne (CSS)
data/                # devices.yaml, pacer.yaml, songs/*.yaml, songs_order.yaml
scripts/             # backup_all.sh, restore_device.sh
tests/               # pytest (modele, storage, API, E2E, MIDI, Pacer)
docs/                # plany, brainstormy
workspace/           # pacer-editor (submodule), notatki, eksperymenty
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
