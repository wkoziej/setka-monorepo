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
| [`packages/cinemon/`](packages/cinemon/) | Tworzenie projektów Blender VSE z animacjami sterowanymi audio |
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

# 4. Create Blender VSE project with preset-based animations
#    Point --main-audio at the master using an ABSOLUTE path. Cinemon is
#    master-aware: it picks analysis/master_analysis.json matching the master.
cinemon-blend-setup /path/to/recording \
  --preset vintage \
  --main-audio "/path/to/recording/mixed/master.wav"

# 5. Upload and publish to social media
python -m medusa.cli upload /path/to/recording/blender/render/output.mp4
```

> Audio/video drift is compensated manually in Blender (the pipeline does not
> auto-sync). Per-instrument stems (`mixed/stems/`) are analyzed automatically
> by `beatrix analyze-recording`; per-strip animation targeting is a future phase.

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

### Konfiguracja YAML (cinemon)

```bash
# Preset-based configuration generation and execution
cinemon-blend-setup /path/to/recording --preset vintage

# Multiple preset options available
cinemon-blend-setup /path/to/recording --preset music-video \
  --main-audio "Przechwytywanie wejścia dźwięku (PulseAudio).m4a"

# Using custom YAML configuration files
cinemon-blend-setup /path/to/recording --config ./custom_animation.yaml

# Advanced configuration generation with Python API
uv run python -c "
from blender.config import CinemonConfigGenerator
generator = CinemonConfigGenerator()

# Generate preset with custom overrides
config_path = generator.generate_preset(
    '/path/to/recording', 'vintage',
    seed=42, fps=60, main_audio='audio.m4a'
)

# Generate completely custom configuration
layout = {'type': 'random', 'config': {'seed': 123, 'margin': 0.15}}
animations = [
    {'type': 'scale', 'trigger': 'bass', 'intensity': 0.8, 'target_strips': ['Camera1']},
    {'type': 'vintage_color', 'trigger': 'one_time', 'sepia_amount': 0.6}
]
config_path = generator.generate_config('/path/to/recording', layout, animations)
print(f'Generated: {config_path}')
"

# Legacy animation modes (still supported)
cinemon-blend-setup /path/to/recording --animation-mode beat-switch
cinemon-blend-setup /path/to/recording --animation-mode energy-pulse
```

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
