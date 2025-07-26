# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Setka is a monorepo containing five interconnected media processing and automation packages:

- **setka-common**: Shared utilities for file structure management
- **obsession**: OBS Canvas Recorder with FFmpeg extraction and metadata collection
- **beatrix**: Dedicated audio analysis for animation timing and beat detection
- **cinemon**: Blender VSE project creation with audio-driven animations
- **medusa**: Media upload automation to YouTube/Vimeo and social media publishing

## Monorepo Structure and Workflow

This is a uv workspace with shared dependencies. All packages depend on `setka-common` for core functionality.

### Package Build Systems

- **obsession**: Uses setuptools with src layout (`src/` directory structure)
- **cinemon**: Uses hatchling with src layout, entry points: `cinemon-blend-setup`, `cinemon-generate-config`
- **setka-common**: Uses setuptools with src layout
- **beatrix**: Audio analysis package with librosa dependencies
- **medusa**: Media upload automation package

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

# Test with coverage (80% minimum required)
uv run pytest --cov
uv run pytest --cov --cov-report=html  # Generate HTML report

# Run single test file
uv run pytest packages/obsession/tests/test_extractor.py -v

# Run specific test by marker
uv run pytest -m "unit" -v
uv run pytest -m "integration" -v
uv run pytest -m "slow" -v

# Run specific test pattern
uv run pytest -k "test_audio_analysis" -v

# Parallel testing (faster)
uv run pytest -n auto
```

### Code Quality Commands

```bash
# Format code (black)
uv run black packages/

# Type checking (mypy)
uv run mypy packages/obsession/src
uv run mypy packages/cinemon/src

# Linting (ruff for cinemon, flake8 for obsession)
uv run ruff check packages/cinemon/
uv run flake8 packages/obsession/src

# Format check without changes
uv run black --check packages/
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
medusa ←─┐
         │
cinemon ←─┼─── setka-common (file_structure, utils)
         │       ↘ beatrix (audio analysis)
         │
obsession ←┘
         │
beatrix ←┘
```

### Key Integration Points

- **File Structure**: All packages use `setka-common.file_structure.specialized.RecordingStructureManager`
- **Audio Processing**: Dedicated audio analysis via `beatrix.core.AudioAnalyzer`
- **CLI Integration**:
  - `obs-extract` → extract sources from OBS recordings
  - `beatrix` → analyze audio for animation timing
  - `cinemon-blend-setup` → create Blender projects with animations
  - `medusa` → upload and publish media

## Critical Architecture Patterns

### Blender Integration (cinemon)

The cinemon package handles Blender VSE automation through:

- **Unified Animation System**: Single animation codebase in addon, used by both VSE script and GUI
- **YAML Configuration System**: Replaces environment variables with structured configuration files
- **Preset Management**: Built-in presets (vintage, multi-pip, minimal) with customization support
- **Media Auto-Discovery**: Automatic detection of video/audio files in recording directories
- **Events-Based Animation**: All animations driven by audio analysis events (beats, energy peaks)
- **Strip Name Mapping**: Uses filename-based naming (webcam.mkv) instead of generic (Video_1)
- **bpy Mock System**: `conftest.py` provides Mock bpy for testing outside Blender
- **Audio-Driven Timing**: Beat detection drives keyframe generation

Key files:
- `cinemon/blender_addon/unified_api.py` - Main animation API interface
- `cinemon/blender_addon/animation_applicators.py` - Routes animations to strips
- `cinemon/blender_addon/keyframe_helper.py` - Unified keyframe insertion
- `cinemon/vse_script.py` - Main Blender script (thin wrapper, delegates to addon)
- `cinemon/project_manager.py` - Python API for project creation
- `cinemon/config/preset_manager.py` - Built-in and custom preset management

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
├── analysis/               # Audio analysis JSON
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

### Test Isolation Issues

Some tests in obsession fail when run together due to `importlib.reload()` calls in `setup_method()`. Run individual test files if encountering `ImportError: module core.metadata not in sys.modules`.

## Recent Development Focus

### Unified Animation System (Phase 1 Complete, Issues Found)
- **Single animation codebase** in addon eliminates VSE/addon duplication
- **7/10 animations migrated** to addon with events-based timing
- **Removed all VSE animations** to follow DRY principle
- **Known issues**: Layout import failure, VSE script not calling Animation API

### YAML Configuration Migration (Completed)
- **cinemon** now uses YAML configuration files instead of environment variables
- **YAML→JSON fallback** implemented for Blender compatibility
- **cinemon-generate-config** CLI command added for configuration generation
- **Preset system** with built-in templates (vintage, multi-pip, minimal)

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
- `cinemon-blend-setup` - Create animated Blender VSE projects (cinemon)
- `cinemon-generate-config` - Generate YAML configuration files (cinemon)
- `uv run --package beatrix python -m beatrix.cli.analyze_audio` - Audio analysis (beatrix)
- `uv run --package medusa python -m medusa.cli` - Media upload automation (medusa)

## Practical Usage Examples

### Complete Pipeline Workflow

```bash
# 1. Extract sources from OBS recording
obs-extract /path/to/recording.mkv

# 2. Analyze audio for animation timing
uv run --package beatrix python -m beatrix.cli.analyze_audio \
  "/path/to/recording/extracted/main_audio.m4a" \
  "/path/to/recording/analysis"

# 3. Create Blender VSE project with preset-based animations
cinemon-blend-setup /path/to/recording \
  --preset vintage \
  --main-audio "main_audio.m4a"

# 4. Upload and publish to social media
python -m medusa.cli upload /path/to/recording/blender/render/output.mp4
```

### Beatrix Audio Analysis Examples

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

### Cinemon YAML Configuration Examples

```bash
# Preset-based configuration generation and execution
cinemon-blend-setup /path/to/recording --preset vintage

# Multiple preset options available
cinemon-blend-setup /path/to/recording --preset music-video \
  --main-audio "Przechwytywanie wejścia dźwięku (PulseAudio).m4a"

# Using custom YAML configuration files
cinemon-blend-setup /path/to/recording --config ./custom_animation.yaml

# Advanced configuration generation with Python API
uv run --package cinemon python -c "
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
