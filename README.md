# Setka — Media Processing and Automation

Monorepo zawierający narzędzia do przetwarzania mediów i automatyzacji publikacji — od nagrania
w OBS, przez analizę audio i animacje w Blenderze, po upload do social media i sterowanie
sprzętem live.

> **Dla agentów AI** (Claude Code, Codex, Cursor): wytyczne i fakty operacyjne żyją w
> [`AGENTS.md`](AGENTS.md). **Mapa dokumentacji procesu:** [`docs/README.md`](docs/README.md).

## Pakiety

| Pakiet | Opis |
|---|---|
| [`packages/common/`](packages/common/) | Wspólne narzędzia zarządzania strukturą plików nagrań |
| [`packages/obsession/`](packages/obsession/) | OBS Canvas Recorder: ekstrakcja źródeł przez FFmpeg + zbieranie metadanych |
| [`packages/beatrix/`](packages/beatrix/) | Analiza audio (beaty, energia, sekcje) na potrzeby timingu animacji |
| [`packages/cymatic/`](packages/cymatic/) | Wizualizer 3D (Blender Geometry Nodes) sterowany analizą z beatrix |
| [`packages/medusa/`](packages/medusa/) | Automatyzacja uploadu mediów (YouTube/Vimeo) i publikacji w social media |
| [`packages/fermata/`](packages/fermata/) | Desktopowe GUI (Tauri) do zarządzania nagraniami i operacjami wsadowymi |
| [`packages/paternologia/`](packages/paternologia/) | Aplikacja web (FastAPI/HTMX) do konfiguracji MIDI live-rigu (Pacer + RC-600 + Model:Samples + MicroFreak) |

## Szybki start

```bash
# Instalacja wszystkich zależności (uv workspace)
uv sync

# Uruchomienie testów
uv run pytest

# Praca z konkretnym pakietem
uv run --package obsession python -m cli.extract --help
uv run --package medusa python -m medusa.cli --help
```

Pełny zestaw komend deweloperskich (testy per-pakiet, markery, lint) — patrz [`AGENTS.md`](AGENTS.md).

## Przykładowe użycie

### Kompletny pipeline

```bash
# 0. Stand up the live recording environment in one shot (OBS + Bitwig + paternologia
#    kiosk) before recording. On-demand systemd --user target; see deploy/live/README.md.
#    Holistic restart of the whole GUI layer: `setka-live restart`. `setka-live show`
#    arranges the windows across the two monitors (Bitwig left; OBS + Paternologia right) —
#    start auto-arranges at the end (best-effort); run show manually if windows drift.
#    Needs wmctrl on X11 (sudo apt install wmctrl).
setka-live start

# 1. Extract sources from OBS recording
obs-extract /path/to/recording.mkv

# 2. Mix/level audio manually in Bitwig, then export the master mix to mixed/
#    (File -> Export Audio -> Project Master). The polished master from mixed/
#    drives analysis AND becomes the final clip soundtrack; extracted/ stays as
#    the video source. The mixed/ directory is managed by RecordingStructureManager.

# 3. Analyze audio for animation timing (one click in Fermata / CLI below)
#    beatrix analyze-recording analyzes ALL tracks in one shot:
#      - master from mixed/master.wav
#      - stems from mixed/stems/ (or bitwig/samples/ as fallback, or extracted/ as last resort)
#    Writes per-track *_analysis.json + discovery manifest analysis/index.json.
#    Consumers read the manifest via: from setka_common import load_analysis_index
beatrix analyze-recording "/path/to/recording"
# (legacy single-file form still works for one-off analysis:)
# uv run --package beatrix python -m beatrix.cli.analyze_audio \
#   "/path/to/recording/mixed/master.wav" \
#   "/path/to/recording/analysis"

# 4. Render the 3D Geometry Nodes visualizer (cymatic) from the analysis.
#    Resolves analysis/*_analysis.json under the recording dir; --main-audio
#    selects the master track. Renders PNG frames headless and muxes to mp4
#    under blender/render/. Needs Blender (5.1.2) on PATH or via
#    --blender-executable /Applications/Blender.app/Contents/MacOS/Blender.
cymatic-render /path/to/recording \
  --main-audio "master.wav"

# 5. Upload and publish to social media
python -m medusa.cli upload /path/to/recording/blender/render/output.mp4
```

> Audio/video drift is compensated manually in Blender (the pipeline does not
> auto-sync). Per-instrument stems (`mixed/stems/`) are analyzed automatically
> by `beatrix analyze-recording`.

### Analiza audio (beatrix)

```bash
# Basic analysis with default settings
uv run --package beatrix python -m beatrix.cli.analyze_audio \
  "audio.m4a" "./analysis"

# Analysis with custom parameters
uv run --package beatrix python -m beatrix.cli.analyze_audio \
  "audio.m4a" "./analysis" \
  --beat-division 4 \
  --min-onset-interval 1.5

# Python API usage
uv run --package beatrix python -c "
from beatrix import AudioAnalyzer
analyzer = AudioAnalyzer()
result = analyzer.analyze_for_animation('audio.m4a', beat_division=8)
print(f'Detected {len(result[\"animation_events\"][\"beats\"])} beats')
"
```

### Wizualizer 3D (cymatic)

```bash
# Render the Geometry Nodes visualizer from a recording's analysis
cymatic-render /path/to/recording --main-audio "master.wav"

# Pin the Blender executable explicitly (macOS install)
cymatic-render /path/to/recording \
  --main-audio "master.wav" \
  --blender-executable /Applications/Blender.app/Contents/MacOS/Blender

# Use a specific analysis JSON (skips auto-detection) and a custom fps
cymatic-render /path/to/recording \
  --analysis-file /path/to/recording/analysis/master_analysis.json \
  --fps 60

# Build an audio structure brief (per-stem activity + master energy) for clip
# authoring → analysis/structure_brief.{json,md,ass} + structure_map.png
cymatic-structure-brief /path/to/recording
```

Bespoke scenes are authored live via the Blender MCP bridge and saved into the
recording's `blender/*.blend`; production rendering is headless. See
[`AGENTS.md`](AGENTS.md) for the cymatic architecture (audio data bridge, the
per-track `dt`, presets).

## Development

Ten projekt używa **uv workspace** do zarządzania wieloma pakietami w jednym repozytorium.
Wszystkie pakiety zależą od `setka-common`. Szczegóły architektury, wzorce, warningi
(Pacer, gotchas Blender) — patrz [`AGENTS.md`](AGENTS.md).

```bash
# Dodawanie zależności do konkretnego pakietu
uv add --package obsession numpy

# Dodawanie zależności dev do workspace
uv add --dev pytest-xdist
```
