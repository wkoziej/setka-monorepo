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

### Development Commands

```bash
# Install all workspace dependencies
uv sync

# Work with specific packages
uv run --package obsession pytest
uv run --package beatrix python -m beatrix.cli.analyze_audio --help
uv run --package cinemon cinemon-blend-setup --help
uv run --package medusa python -m medusa.cli --help

# Add dependencies to specific packages
uv add --package obsession numpy
uv add --package cinemon librosa

# Add workspace-wide dev dependencies
uv add --dev pytest-xdist

# Linting and formatting
uv run ruff check .
uv run ruff check --fix .
uv run ruff format .
```

### Testing Commands

```bash
# Run all tests across all packages
uv run pytest

# Test specific packages
uv run --package obsession pytest
uv run --package beatrix pytest
uv run --package cinemon pytest
uv run --package medusa pytest

# Test with coverage
uv run pytest --cov

# Run single test file
uv run pytest packages/obsession/tests/test_extractor.py -v

# Run specific test
uv run pytest -k "test_audio_analysis" -v

# Run tests by marker
uv run pytest -m unit -v           # Unit tests only
uv run pytest -m integration -v    # Integration tests only
uv run pytest -m "not slow" -v     # Exclude slow tests
uv run pytest -m audio -v          # Audio processing tests
uv run pytest -m manual -v         # Manual intervention tests
```

## Architecture Overview

### Core Data Flow

1. **OBS Recording** → metadata collection via `obsession/obs_script.py`
2. **File Extraction** → FFmpeg processing via `obsession/extractor.py`
3. **Audio Analysis** → librosa processing via `beatrix/core/`
4. **Blender VSE** → parametric project creation via `cinemon/vse_script.py`
5. **Media Upload** → YouTube/social automation via `medusa/uploaders/`

### Package Dependencies

```
fermata ←─┐ (Tauri GUI)
          │
medusa ←──┼─┐
          │ │
cinemon ←─┼─┼─── setka-common (file_structure, utils)
          │ │       ↘ beatrix (audio analysis)
cymatic ←─┼─┤
          │ │
obsession ←┘ │
          │
beatrix ←─┘
```

### Key Integration Points

- **File Structure**: All packages use `setka-common.file_structure.specialized.RecordingStructureManager`
- **Audio Processing**: Dedicated audio analysis via `beatrix.core.AudioAnalyzer`
- **3D Visualization**: `cymatic` consumes the beatrix `*_analysis.json` to drive a Blender Geometry Nodes scene
- **CLI Integration**:
  - `obs-extract` → extract sources from OBS recordings
  - `beatrix` → analyze audio for animation timing
  - `cinemon-blend-setup` → create Blender projects with animations
  - `cymatic-render` → render a 3D Geometry Nodes audio visualizer from a beatrix analysis
  - `medusa` → upload and publish media
- **GUI Integration**:
  - `fermata` → Tauri desktop app for batch operations and recording management

## Critical Architecture Patterns

### Blender Integration (cinemon)

The cinemon package handles Blender VSE automation through:

- **YAML Configuration System**: Replaces environment variables with structured configuration files
- **Preset Management**: Built-in presets (vintage, music-video, minimal, beat-switch) with customization support
- **Media Auto-Discovery**: Automatic detection of video/audio files in recording directories
- **Configuration Generation**: High-level API for generating YAML configurations from presets or custom parameters
- **Selective Animation Targeting**: Apply different animations to specific video strips
- **bpy Mock System**: `conftest.py` provides Mock bpy for testing outside Blender
- **Animation Engine**: Delegation pattern routing to specialized animators
- **Audio-Driven Timing**: Beat detection drives keyframe generation

Key files:
- `cinemon/vse_script.py` - Main Blender script (executed by Blender)
- `cinemon/project_manager.py` - Python API for project creation
- `cinemon/animation_engine.py` - Delegates to beat-switch/energy-pulse/multi-pip animators
- `cinemon/config/cinemon_config_generator.py` - High-level YAML configuration generation API
- `cinemon/config/media_discovery.py` - Auto-discovery of media files in recording directories
- `cinemon/config/preset_manager.py` - Built-in and custom preset management

### 3D Visualization (cymatic)

The cymatic package drives a Blender Geometry Nodes 3D audio visualizer from beatrix analysis. The package is **split in two** because the in-Blender code runs under Blender's bundled Python (numpy yes, no PyYAML):

- **Host-side** `packages/cymatic/src/cymatic/` (pure numpy, no `bpy`): `config.py` (`VisualizerConfig`, `PresetParams`), `analysis_loader.py` (`load_analysis`), `normalization.py` (p99 band normalization, envelope precompute), `runner.py` (`CymaticRunner`), `cli.py` (`cymatic-render`), `sync_verification.py`.
- **In-Blender** `packages/cymatic/blender_script/` (`import bpy`, NOT shipped in the wheel): `build_scene.py` (entry executed by Blender), `data_object.py`, `gn_sampler.py`, `presets/` (`hybrid_v1.py`).

Key patterns:

- **Audio data bridge ("most B")**: `data_object.build_data_object(name, dt, channels)` bakes audio into a hidden mesh where **X = time** (`arange(N)*dt`) and each channel is a FLOAT/POINT attribute (`bass_n`, `mid_n`, `high_n`, `beat_env`, `peak_env`). Geometry Nodes sample it via `Scene Time → DIVIDE by dt → FLOOR → Sample Index` against that object. `gn_sampler.build_sampler_group(name, dt, data_obj, channels)` builds a reusable sampler group exposing those channels.
- **`dt` is per-track, never hardcode**: `dt = times[1] - times[0]` from the analysis JSON (host-side in `load_analysis`). It must reach every `DIVIDE` node in the GN graphs, or audio desyncs.
- **Preset pattern**: a preset is a module exposing `build_preset_scene(analysis, data_obj, sampler_group, preset_params, fps, resolution, ...)` (see `presets/hybrid_v1.py`); the in-package preset is dispatched by `build_scene.py`. `PresetParams` is the only surface authoring should manipulate to keep builds deterministic.
- **Headless render**: `runner.py` invokes `snap run blender --background --python build_scene.py -- --config <json>`, renders PNG frames, then `ffmpeg`-muxes them (this Blender 5.1 build has no internal video encoder). Drivers require `--enable-autoexec`. Post-fx (bloom/vignette/grade) is done in the ffmpeg `-filter_complex` pass, NOT in the Blender compositor (`format=rgb24` MUST come after `blend`).
- **Per-track manifest**: per-stem analyses are discovered via `setka_common.load_analysis_index(recording_dir)` (`.master()`, `.stems()`, `entry.resolved_analysis_path()`); select by the `analysis` field, never by deriving `<stem>_analysis.json`. The package CLI/`build_scene.py` currently consumes a single analysis; multi-stem orchestration (one data-object per stem) is done ad-hoc during MCP authoring, not yet wired into the CLI.
- **Bespoke looks live in the recording's `.blend`, not the repo**: rich scenes (grove, mosaic, multistem, rest-in-peace) are authored live via the Blender MCP bridge (`ahujasid/blender-mcp`, socket `localhost:9876`, "Connect to Claude" in the N panel) and saved to `<recording>/blender/*.blend`. They reuse the host-side helpers (`load_analysis`, `build_data_object`, `gn_sampler`) inside the MCP session. The MCP bridge is for authoring/design; production rendering is headless. Freezing a bespoke look into a parametric in-package preset is separate, planned work.

Key files:
- `cymatic/blender_script/build_scene.py` - Main Blender script (executed by Blender)
- `cymatic/blender_script/data_object.py` - Audio data bridge (mesh with time-indexed channel attributes)
- `cymatic/blender_script/gn_sampler.py` - Reusable Geometry Nodes sampler group
- `cymatic/blender_script/presets/hybrid_v1.py` - Reference preset (`build_preset_scene`)
- `cymatic/src/cymatic/{analysis_loader,config,runner,cli}.py` - Host-side load/config/render/CLI

> Blender 5.1 GN gotchas (sockets named `"Geometry"` not `"Mesh"`, manual Group Input/Output after `node_groups.new`, Action 2.0 has no `action.fcurves`, `interface.new_socket` over `inputs/outputs`) are documented in the cymatic plans and agent memory.

### OBS Integration (obsession)

The obsession package interfaces with OBS Studio:

- **Metadata Collection**: OBS script captures scene layout during recording
- **FFmpeg Extraction**: Crops individual sources using calculated parameters
- **Capability Detection**: Uses OBS API to determine audio/video flags per source

Key files:
- `obsession/obs_integration/obs_script.py` - OBS Studio script
- `obsession/core/extractor.py` - FFmpeg automation
- `obsession/core/metadata.py` - OBS API integration

### Audio Analysis Pipeline (beatrix)

Shared audio processing using librosa:

- **Beat Detection**: Tempo analysis and beat timing extraction
- **Energy Analysis**: RMS energy peaks for pulse animations
- **Structural Segmentation**: Section boundary detection for scene transitions

Key files:
- `beatrix/core/audio_analyzer.py` - Core analysis engine
- `beatrix/cli/analyze_audio.py` - CLI interface
- `beatrix/core/audio_validator.py` - File validation and selection

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

### Adding New Animation Modes (cinemon)

1. Create animator class in `cinemon/vse/animators/`
2. Implement `get_animation_mode()` and `animate()` methods
3. Register in `animation_engine.py`
4. Add CLI option in `blend_setup.py`
5. Update audio analysis data consumption

### Adding New Uploader/Publisher (medusa)

1. Inherit from `BaseUploader` or `BasePublisher`
2. Implement required authentication flow
3. Add configuration schema to `config.py`
4. Register in `registry.py`
5. Add integration tests with real API mocking

### Extending File Structure (setka-common)

1. Add new directory types to `file_structure/specialized/`
2. Update `RecordingStructureManager` methods
3. Add validation in `file_structure/base.py`
4. Update all consuming packages

## CLI Entry Points

Each package provides specific commands:

- `obs-extract` - Extract sources from OBS recordings (obsession)
- `beatrix` - Analyze audio for animation timing (beatrix)
- `cinemon-blend-setup` - Create animated Blender VSE projects (cinemon)
- `cinemon-generate-config` - Generate YAML configuration files (cinemon)
- `cymatic-render` - Render a 3D Geometry Nodes audio visualizer from a beatrix analysis (cymatic)
- Direct module execution for medusa: `python -m medusa.cli`
- `uv run --package paternologia fastapi run src/paternologia/main.py` - Web UI for live-rig MIDI/song management (paternologia). Songs live in `packages/paternologia/data/songs/*.yaml`, ordered by `songs_order.yaml`; devices in `data/devices.yaml`. See `packages/paternologia/SPEC.md` and `README.md` for the data format and Pacer/Bitwig/OBS integration. **Critical Pacer warnings**: always send SysEx with `--sysex-interval=20`; never send `TARGET_GLOBAL (0x05) + elm=0x1E` (bricks the Pacer).

## Dokumentacja — gdzie co żyje

- **README.md** (root) — narracja dla ludzi + przykłady użycia (pełny pipeline workflow, przykłady CLI).
- **AGENTS.md** (ten plik) — kanon faktów dla agentów na poziomie monorepo.
- **packages/<pkg>/AGENTS.md** — kanon faktów specyficznych dla pakietu (ładowany leniwie przy pracy w danym pakiecie).
- **docs/README.md** — indeks taksonomii dokumentacji (brainstorms/plans/solutions/handoffs/ideation/archive) i powiązań ze skillami `ce:*`.
- **docs/solutions/** — wiedza instytucjonalna (konsumowana przez skill `learnings-researcher`).
