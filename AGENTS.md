# AGENTS.md

Kanoniczna warstwa "schema" dla agentów AI pracujących w tym repo (narzędzio-niezależna:
Claude Code, Codex, Cursor i inne). `CLAUDE.md` jest cienkim stubem importującym ten plik.
README opisuje projekt narracyjnie dla ludzi i zawiera przykłady użycia (usage); tutaj żyją
zwięzłe fakty, których agent potrzebuje, by operować w repo.

## Project Overview

Setka is a monorepo containing eight interconnected media processing and automation packages:

- **setka-common**: Shared utilities for file structure management
- **obsession**: OBS Canvas Recorder with FFmpeg extraction and metadata collection
- **beatrix**: Dedicated audio analysis for animation timing and beat detection
- **cinemon**: Blender VSE project creation with audio-driven animations
- **cymatic**: Blender Geometry Nodes 3D audio visualizer driven by beatrix analysis
- **medusa**: Media upload automation to YouTube/Vimeo and social media publishing
- **fermata**: Tauri-based desktop GUI for managing recordings and batch operations
- **paternologia**: FastAPI/HTMX web app for managing per-song MIDI configurations of a live rig (Nektar Pacer foot controller + Boss RC-600, Elektron Model:Samples, Arturia MicroFreak). Edits songs, exports `.syx` to the Pacer, bridges the Pacer MIDI stream to Bitwig, and drives OBS one-button recording.

## Monorepo Structure and Workflow

This is a uv workspace with shared dependencies. All packages depend on `setka-common` for core functionality.

### Workspace gotchas

- Full dev env needs `uv sync --all-packages` — plain `uv sync` installs only the root env (member dev/runtime deps missing → ModuleNotFound in per-package tests and the commit hook).
- A bare `uv run pytest` (or `--package X pytest` without a path) fails collection: packages share test-file basenames without `tests/__init__.py`. Run tests by path: `uv run pytest packages/<pkg>/tests`.

## Architecture Overview

### Core Data Flow

1. **OBS Recording** → metadata collection via `obsession/obs_script.py`
2. **File Extraction** → FFmpeg processing via `obsession/extractor.py`
3. **Audio Analysis** → librosa processing via `beatrix/core/`
4. **Blender VSE** → parametric project creation via `cinemon/vse_script.py`
5. **Media Upload** → YouTube/social automation via `medusa/uploaders/`

### Key Integration Points

- **File Structure**: All packages use `setka-common.file_structure.specialized.RecordingStructureManager`
- **Audio Processing**: Dedicated audio analysis via `beatrix.core.AudioAnalyzer`
- **3D Visualization**: `cymatic` consumes the beatrix `*_analysis.json` to drive a Blender Geometry Nodes scene
- **CLI Integration**:
  - `obs-extract` → extract sources from OBS recordings
  - `beatrix` → analyze audio for animation timing
  - `cinemon-blend-setup` → create Blender projects with animations
  - `cymatic-render` → render a 3D Geometry Nodes audio visualizer from a beatrix analysis
  - `cymatic-structure-brief` → build an audio structure brief (per-stem activity + master energy) for clip authoring; writes `analysis/structure_brief.{json,md,ass}` + `structure_map.png`
  - `medusa` → upload and publish media
- **GUI Integration**:
  - `fermata` → Tauri desktop app for batch operations and recording management; the recording view's **Play + Brief** action plays the source video in VLC with `analysis/structure_brief.ass` overlaid

## Critical Architecture Patterns

### Per-package details

Package-specific architecture, key files and gotchas live in `packages/<pkg>/AGENTS.md` (loaded lazily when working in that package): cinemon (Blender VSE, bpy mock), cymatic (Geometry Nodes visualizer, `dt` / data-object bridge, headless render), obsession (OBS script, FFmpeg extraction), beatrix (AudioAnalyzer), medusa (uploaders).

### File Structure Management (setka-common)

Standardized directory organization:

```
recording_name/
├── recording_name.mkv       # OBS recording
├── metadata.json           # Scene metadata
├── extracted/              # Individual sources
├── mixed/                  # Bitwig master (master.wav) + optional stems/ for analysis
├── bitwig/                 # Bitwig project home (Save As here)
│   └── samples/            # Raw per-track capture (non-destructive; effects live in .bwproject)
│                           # Used as stem fallback for analysis when mixed/stems/ is absent
├── analysis/               # Audio analysis JSON ({stem}_analysis.json per source)
│   └── index.json          # Discovery manifest: [{role, origin, label, source, analysis, …}]
│                           # role∈{master,stem,main}; consumers read via load_analysis_index()
└── blender/               # VSE projects
    └── render/            # Final outputs
```

Managed by `setka-common.file_structure.specialized.RecordingStructureManager`

## Testing Architecture

### Package-Specific Test Patterns

- **obsession**: Uses `importlib.reload()` for module isolation (can cause multi-test issues)
- **cinemon**: Uses global `bpy` mock via `conftest.py` for Blender-free testing
- **medusa**: Separates unit tests from integration tests with YouTube/Facebook APIs
- **beatrix**: Uses mock AudioAnalyzer for testing audio processing components
- **setka-common**: Provides file structure utilities and validates directory organization
- **fermata**: Tauri frontend testing with Vitest, backend Rust testing with cargo test

### Test Markers

Available pytest markers defined in workspace `pyproject.toml`:
- `unit`: Unit tests (default)
- `integration`: Integration tests requiring external services
- `audio`: Tests requiring audio processing capabilities
- `manual`: Tests requiring manual intervention
- `asyncio`: Tests using asyncio functionality

### Test Isolation Issues

Some tests in obsession fail when run together due to `importlib.reload()` calls in `setup_method()`. Run individual test files if encountering `ImportError: module core.metadata not in sys.modules`.

## External Dependencies

### Required External Tools

- **FFmpeg 4.4+**: Must be in PATH for video/audio extraction
- **Blender 4.3+**: For VSE project execution (can be snap-installed)
- **OBS Studio**: With Python scripting support for metadata collection

### API Integrations

- **YouTube Data API v3**: Requires OAuth2 setup in `medusa`
- **Facebook Graph API**: Requires app registration for publishing
- **OBS WebSocket API**: For real-time scene metadata collection

## Common Development Patterns

### Extending File Structure (setka-common)

1. Add new directory types to `file_structure/specialized/`
2. Update `RecordingStructureManager` methods
3. Add validation in `file_structure/base.py`
4. Update all consuming packages

## paternologia

`uv run --package paternologia fastapi run src/paternologia/main.py` - Web UI for live-rig MIDI/song management (paternologia). Songs live in `packages/paternologia/data/songs/*.yaml`, ordered by `songs_order.yaml`; devices in `data/devices.yaml`. See `packages/paternologia/SPEC.md` and `README.md` for the data format and Pacer/Bitwig/OBS integration. **Critical Pacer warnings**: always send SysEx with `--sysex-interval=20`; never send `TARGET_GLOBAL (0x05) + elm=0x1E` (bricks the Pacer).

## Dokumentacja — gdzie co żyje

- **README.md** (root) — narracja dla ludzi + przykłady użycia (pełny pipeline workflow, przykłady CLI).
- **AGENTS.md** (ten plik) — kanon faktów dla agentów na poziomie monorepo.
- **packages/<pkg>/AGENTS.md** — kanon faktów specyficznych dla pakietu (ładowany leniwie przy pracy w danym pakiecie).
- **docs/README.md** — indeks taksonomii dokumentacji (brainstorms/plans/solutions/handoffs/ideation/archive) i powiązań ze skillami `ce:*`.
- **docs/solutions/** — wiedza instytucjonalna (konsumowana przez skill `learnings-researcher`).
