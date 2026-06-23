# AGENTS.md — obsession

Kanon faktów dla agentów specyficznych dla pakietu `obsession`. Fakty ogólnomonorepowe
(workspace, komendy `uv`, layout nagrania) żyją w root `../../AGENTS.md`. `CLAUDE.md` to stub.

## Project Overview

Obsession is the OBS Canvas Recorder front of the pipeline. An OBS Studio script captures
the scene layout (source positions, dimensions, audio/video capabilities) into a
`metadata.json` at recording start/stop; a CLI then uses that metadata to crop each source
out of the canvas recording with FFmpeg into the `extracted/` directory. Downstream, beatrix
analyzes the extracted/mixed audio and cymatic renders the visualizer — those live in their
own packages, not here. Obsession does **not** create Blender projects or animations.

## Key Architecture

### Core Components
- **`src/obsession/core/metadata.py`**: `create_metadata`, `determine_source_capabilities` (OBS API audio/video flags), and `validate_metadata` (rejects missing/zero canvas, bad positions/bounds/dimensions).
- **`src/obsession/core/extractor.py`**: FFmpeg extraction. `calculate_crop_params` computes the `crop=w:h:x:y` rectangle (clamps sources partly off-canvas); `extract_sources` / `SourceExtractor` drive per-source extraction; `_extract_video_source` / `_extract_audio_source` build the argv (audio uses `-map` for the source's own stream, plus a `timeout`); results are wrapped in `ExtractionResult` (success/failure, including `TimeoutExpired`).
- **`src/obsession/obs_integration/obs_script.py`**: The OBS Studio script. Collects scene metadata and writes `metadata.json`; validates `base_width/height > 0` before emitting `canvas_size`.
- **`src/obsession/obs_integration/advanced_scene_switcher_extractor.py`**: Extraction path for the OBS Advanced Scene Switcher plugin (bounded by `timeout`).
- **`src/obsession/cli/extract.py`**: `obs-extract` — extract sources from a recording.
- **`src/obsession/cli/cameras.py`**: `obs-cameras` — manage a multi-camera (RPi) setup.

Filename sanitization uses the canonical `setka_common.utils.files.sanitize_filename`
(obsession adopted the canonical superset; no local copy).

### Data Flow
1. OBS script collects scene metadata on recording start/stop and writes `metadata.json`.
2. Files are organized into the standard recording structure via `setka_common.RecordingStructureManager`.
3. Metadata carries source positions, dimensions, and `has_audio`/`has_video` flags.
4. `obs-extract` reads the metadata and crops each source via FFmpeg into `extracted/` (video `.mp4`, audio `.m4a` per source).

## Development Commands

### Setup
```bash
# Install dev dependencies (workspace install `uv sync` — patrz root AGENTS.md)
uv sync --group dev
```

### Testing
```bash
# Run from the package directory (per-package gate, 80%)
cd packages/obsession && uv run --package obsession pytest

# Run a single test file
cd packages/obsession && uv run --package obsession pytest tests/test_extractor.py -v

# Selective markers
cd packages/obsession && uv run --package obsession pytest -m unit
cd packages/obsession && uv run --package obsession pytest -m integration
```

### CLI Usage
```bash
# Extract sources using an explicit metadata file
obs-extract recording.mp4 metadata.json

# Choose an output directory
obs-extract recording.mp4 metadata.json --output-dir ./extracted/

# Verbose output
obs-extract recording.mp4 metadata.json --verbose

# Auto mode: wait for the file to settle and auto-detect metadata
obs-extract recording.mp4 --auto --verbose

# Skip audio extraction for sources matching a regex (e.g. RPi cameras)
obs-extract recording.mp4 --auto --skip-audio-pattern "^(RPI|Camera).*"

# Manage RPi camera setup
obs-cameras --help
```

## Key Design Patterns

### Metadata Format (v2.0)
- `canvas_size` is a **list** `[w, h]`; `sources` is a **dict** keyed by source name.
- Each source carries `has_audio`/`has_video` (from the OBS API), plus `position`, `bounds`, and `dimensions` used for crop calculation.
- `validate_metadata` is defensive: it rejects zero/negative canvas size and malformed `position`/`bounds`/`dimensions`.

### FFmpeg Integration
- Video extraction uses the crop filter `crop=width:height:x:y` (`-vn` is not used for video; audio extraction strips video).
- **Per-source audio via `-map`**: each `has_audio` source gets its own correctly-mapped audio track in its own `.m4a` — not N identical full-canvas copies.
- Every FFmpeg call has a `timeout`; a hung/over-long run surfaces as a failed `ExtractionResult` carrying `TimeoutExpired` (mirrors cymatic's runner and the advanced-scene-switcher extractor).

### Error Handling
- `ExtractionResult` wraps success/failure per source.
- Graceful fallbacks when the OBS API is unavailable (under test).
- Cross-platform filename sanitization via the canonical `sanitize_filename`.

## Testing Standards
- Coverage target: 80% (enforced from the package directory).
- Test markers: `unit`, `integration`, `slow`.
- Fixtures use the **real** `metadata.json` shape (`canvas_size` as a list, `sources` as a dict); a fixture-shaped metadata round-trips through `validate_metadata` and `extract_sources`.

## OBS Integration
The `obs_script.py` must be loaded in OBS Studio (Tools → Scripts → Add). It:
- Collects scene metadata on recording start/stop.
- Validates `base_width/height > 0` before writing `canvas_size`.
- Enumerates sources and their audio/video capabilities.
- Organizes files into the standard recording structure.

## Dependencies
- **Runtime**: `ffmpeg-python`, `setka-common`.
- **Development**: `pytest`, `pytest-cov` (plus lint/format tooling).
- **External**: FFmpeg 4.4+ in PATH; OBS Studio with Python scripting support.

## Project Structure (obsession's slice)

```
recording_name/
├── recording_name.mkv       # OBS recording
├── metadata.json            # Scene metadata from OBS (obsession produces this)
└── extracted/               # Cropped per-source media (obsession produces this)
    ├── Camera1.mp4          # video (no audio)
    ├── Camera2.mp4
    └── Microphone.m4a       # audio (own -map'd stream)
```

(`analysis/` and `blender/` are produced by beatrix and cymatic respectively — see root `AGENTS.md`.)
