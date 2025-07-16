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

# Test with coverage
uv run pytest --cov

# Run single test file
uv run pytest packages/obsession/tests/test_extractor.py -v

# Run specific test
uv run pytest -k "test_audio_analysis" -v
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

- **Parametric Scripts**: Environment variables control Blender execution
- **bpy Mock System**: `conftest.py` provides Mock bpy for testing outside Blender
- **Animation Engine**: Delegation pattern routing to specialized animators
- **Audio-Driven Timing**: Beat detection drives keyframe generation

Key files:
- `cinemon/vse_script.py` - Main Blender script (executed by Blender)
- `cinemon/project_manager.py` - Python API for project creation
- `cinemon/animation_engine.py` - Delegates to beat-switch/energy-pulse/multi-pip animators

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
- Direct module execution for medusa: `python -m medusa.cli`

## Practical Usage Examples

### Complete Pipeline Workflow

```bash
# 1. Extract sources from OBS recording
obs-extract /path/to/recording.mkv

# 2. Analyze audio for animation timing
uv run --package beatrix python -m beatrix.cli.analyze_audio \
  "/path/to/recording/extracted/main_audio.m4a" \
  "/path/to/recording/analysis"

# 3. Create Blender VSE project with beat-synchronized animations
cinemon-blend-setup /path/to/recording \
  --animation-mode beat-switch \
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

### Cinemon Integration with Beatrix

```bash
# Auto-detects and runs beatrix analysis if needed
cinemon-blend-setup /path/to/recording --animation-mode beat-switch

# Using multiple audio files (requires --main-audio)
cinemon-blend-setup /path/to/recording \
  --animation-mode energy-pulse \
  --main-audio "Przechwytywanie wejścia dźwięku (PulseAudio).m4a"

# Skip audio analysis if already exists
cinemon-blend-setup /path/to/recording \
  --animation-mode multi-pip \
  --use-existing-analysis
```