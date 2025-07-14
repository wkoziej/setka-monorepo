# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OBS Canvas Recorder is a comprehensive system for automatic extraction of sources from OBS canvas recordings and creation of Blender VSE projects. The system integrates with OBS Studio to capture scene layout, uses FFmpeg for precise video/audio extraction, and provides automated Blender Video Sequence Editor project generation.

## Key Architecture

### Core Components
- **`src/core/metadata.py`**: Handles metadata creation and OBS API integration for source capabilities detection
- **`src/core/extractor.py`**: FFmpeg-based video/audio extraction with crop parameter calculation
- **`src/core/file_structure.py`**: Manages organized file structure for recordings (metadata.json, extracted/, blender/, analysis/)
- **`src/core/blender_project.py`**: Creates Blender VSE projects from extracted recordings using parametric scripts
- **`src/core/audio_validator.py`**: Validates and selects main audio files for projects
- **`src/core/audio_analyzer.py`**: Audio analysis for animation events (beats, energy peaks, sections)
- **`src/core/blender_vse_script.py`**: Parametric Blender script for VSE project creation with audio-driven animations
- **`src/obs_integration/obs_script.py`**: OBS Studio script that collects scene metadata and auto-organizes files
- **`src/cli/extract.py`**: Command-line interface for source extraction
- **`src/cli/blend_setup.py`**: CLI for creating Blender VSE projects from recordings with automatic audio analysis
- **`src/cli/analyze_audio.py`**: CLI for standalone audio analysis
- **`src/cli/cameras.py`**: CLI for managing multiple camera setup with RPi cameras

### Data Flow
1. OBS script collects scene metadata on recording start/stop
2. Files are automatically organized into structured directories using FileStructureManager
3. Metadata includes source positions, dimensions, and capabilities (audio/video flags)
4. CLI tool uses metadata to extract individual sources via FFmpeg to extracted/ directory
5. Audio analysis automatically performed when creating animated Blender projects (analysis/ directory)
6. Blender VSE projects created from extracted files with audio-driven animations and automatic main audio detection
7. Final structure: recording_name/[video_file, metadata.json, extracted/, analysis/, blender/]

## Development Commands

### Setup
```bash
# Install dependencies
uv sync

# Install development dependencies
uv sync --group dev
```

### Testing (TDD Approach)
```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test categories
uv run pytest -m unit          # Unit tests only
uv run pytest -m integration   # Integration tests only
uv run pytest -m "not slow"    # Skip slow tests

# Run single test file
uv run pytest tests/test_extractor.py -v
```

### Code Quality
```bash
# Format code
uv run black src/ tests/

# Type checking
uv run mypy src/

# Linting (via flake8 in dev dependencies)
uv run flake8 src/ tests/
```

### CLI Usage
```bash
# Extract sources from recording
uv run python -m cli.extract recording.mkv metadata.json

# With output directory
uv run python -m cli.extract recording.mkv metadata.json --output-dir ./extracted/

# With verbose output and auto-detection
uv run python -m cli.extract recording.mkv --auto --verbose

# Create Blender VSE project from extracted recording
uv run python -m cli.blend_setup ./recording_20250105_143022

# With specific main audio file
uv run python -m cli.blend_setup ./recording_20250105_143022 --main-audio "main_audio.m4a"

# Create animated VSE project (automatic audio analysis)
uv run python -m cli.blend_setup ./recording_20250105_143022 --animation-mode beat-switch
uv run python -m cli.blend_setup ./recording_20250105_143022 --animation-mode energy-pulse 
uv run python -m cli.blend_setup ./recording_20250105_143022 --animation-mode multi-pip

# Standalone audio analysis (optional - done automatically when needed)
uv run python -m cli.analyze_audio ./extracted/main_audio.m4a ./analysis --beat-division 8

# Manage camera setup (RPi cameras)
uv run python -m cli.cameras --help
```

## Key Design Patterns

### Metadata Format (v2.0)
The system uses a structured metadata format with source capabilities:
- `has_audio`/`has_video` flags determined via OBS API
- Source positioning and dimensions for crop calculations
- Recording timestamps and canvas size

### FFmpeg Integration
- Video extraction uses crop filter: `crop=width:height:x:y`
- Audio extraction strips video: `-vn` flag
- Separate files for video (.mp4) and audio (.m4a) based on capabilities

### File Structure Management
- **FileStructureManager**: Centralized file organization system
- **Auto-reorganization**: OBS script automatically creates proper directory structure
- **Standardized paths**: `metadata.json`, `extracted/`, `blender/` directories
- **Cross-platform compatibility**: File sanitization and path handling

### Error Handling
- `ExtractionResult` class wraps success/failure states
- Graceful fallbacks when OBS API unavailable (testing)
- File sanitization for cross-platform compatibility
- `AudioValidationError` for audio file validation issues
- Comprehensive logging throughout the system

## Testing Standards

- **TDD workflow**: Write failing tests first, implement minimal code to pass
- **Coverage target**: 80% minimum (configured in pyproject.toml)
- **Test markers**: `unit`, `integration`, `slow` for selective test execution
- **Fixture files**: Located in `tests/fixtures/` for sample recordings

## OBS Integration

The `obs_script.py` must be loaded in OBS Studio (Tools → Scripts → Add). It requires:
- Python 3.9+ environment accessible to OBS
- Automatic file reorganization after recording stops
- Scene analysis capabilities for source enumeration
- Integration with FileStructureManager for consistent organization
- Support for both fallback metadata saving and structured organization

## Blender Integration

The system includes comprehensive Blender VSE project generation:
- **Parametric script approach**: Environment variables control project creation
- **Automatic main audio detection**: Uses AudioValidator to select primary audio track
- **Audio-driven animations**: Automatic audio analysis for beat-synchronized effects
- **FPS detection**: Reads frame rate from recording metadata
- **Snap support**: Works with snap-installed Blender
- **Render configuration**: Sets up output paths and resolution
- **VSE timeline setup**: Automatically arranges video and audio tracks with keyframe animations

## Audio-Driven Animations

The system includes sophisticated audio analysis and animation capabilities:
- **AudioAnalyzer**: Uses librosa for beat detection, energy analysis, and structural segmentation
- **Animation Modes**:
  - `beat-switch`: Round-robin video switching synchronized to beats
  - `energy-pulse`: Scale pulsing on energy peaks (bass response)
  - `multi-pip`: Main cameras switch on section boundaries + corner PiPs with beat effects
- **Automatic Analysis**: Audio analysis triggered automatically when animation modes are used
- **Cache-Aware**: Reuses existing analysis files, no duplicate processing
- **Data Exchange**: JSON format for animation events (beats, energy_peaks, sections)

## Dependencies

- **Runtime**: `ffmpeg-python`, `pathlib-extensions`, `librosa`, `numpy`, `scipy`
- **Development**: `pytest`, `pytest-cov`, `black`, `mypy`, `flake8`, `pre-commit`
- **External**: 
  - FFmpeg 4.4+ must be available in PATH
  - Blender 3.0+ for VSE project generation (can be snap-installed)
  - OBS Studio with Python scripting support

## Project Structure

```
recording_name/
├── recording_name.mkv       # Main recording file
├── metadata.json           # Scene metadata from OBS
├── extracted/              # Extracted individual sources
│   ├── source1.mp4
│   ├── source2.m4a
│   └── ...
├── analysis/               # Audio analysis for animations
│   └── main_audio_analysis.json
└── blender/               # Blender VSE projects
    ├── recording_name.blend
    └── render/
        └── recording_name_final.mp4
```

## Advanced Features

### Multi-Camera Setup
- RPi camera management via `cli.cameras`
- Deployment scripts for camera networks
- Integration with OBS for multi-angle recording

### Audio Processing
- Automatic main audio detection based on file size and duration
- Support for multiple audio sources in VSE projects
- Audio validation and error handling

### Advanced Scene Switcher Integration
- Support for OBS Advanced Scene Switcher plugin
- Automatic source extraction based on scene switching metadata
- Enhanced metadata collection for complex setups

### Audio-Driven Animation System (Phase 3A MVP)

The system supports audio-driven animations in Blender VSE projects using beat detection and keyframe animation.

#### Beat-Switch Animation

**How it works:**
- Analyzes main audio file to detect beat events using librosa
- Creates keyframes in Blender VSE timeline synchronized to beat timings
- Alternates video strip visibility on each detected beat
- Uses scene-level keyframes (`bpy.context.scene.keyframe_insert()`) for persistence

**Usage:**
```bash
# Create VSE project with beat-switch animation
uv run python -m src.cli.blend_setup ./recording_dir --animation-mode beat-switch

# With specific main audio and beat division
uv run python -m src.cli.blend_setup ./recording_dir \
    --main-audio "main.m4a" \
    --animation-mode beat-switch \
    --beat-division 8
```

**Animation behavior:**
- **Strip 1 visible**: From start until first beat
- **Strip 2 visible**: From first beat until second beat  
- **Strip 3 visible**: From second beat until third beat
- **Cycling**: After last strip, returns to Strip 1 (round-robin)

**Technical details:**
- Beat times converted to frame numbers using project FPS
- Each video strip gets `blend_alpha` keyframes (1.0 = visible, 0.0 = hidden)
- Audio analysis stored in `analysis/[audio_file]_analysis.json`
- Supports up to 2x2 grid layout (4 video sources maximum in MVP)

**Requirements:**
- Main audio file must exist in extracted/ directory
- Audio analysis must be generated (automatic with `--animation-mode`)
- Project must contain video files for animation

**Beat division options:**
- `1`: Every beat (quarter notes)
- `2`: Every half beat (eighth notes)  
- `4`: Every quarter beat (sixteenth notes)
- `8`: Every eighth beat (thirty-second notes) - default
- `16`: Every sixteenth beat (sixty-fourth notes)

**File structure after animation:**
```
recording_name/
├── recording_name.mkv
├── metadata.json
├── extracted/
│   ├── video1.mp4
│   ├── video2.mp4
│   └── main_audio.m4a
├── analysis/
│   └── main_audio_analysis.json
└── blender/
    ├── recording_name.blend      # With keyframes
    └── render/
        └── recording_name_final.mp4
```

#### Energy-Pulse Animation (Phase 3B.1)

**How it works:**
- Analyzes main audio file to detect energy peaks using RMS analysis
- Creates transform.scale keyframes synchronized to energy peak timings
- Scales all video strips simultaneously by 20% on energy peaks
- Uses scene-level keyframes for persistence in Blender VSE

**Usage:**
```bash
# Create VSE project with energy-pulse animation
uv run python -m src.cli.blend_setup ./recording_dir --animation-mode energy-pulse

# With specific parameters
uv run python -m src.cli.blend_setup ./recording_dir \
    --main-audio "main.m4a" \
    --animation-mode energy-pulse \
    --beat-division 8
```

**Animation behavior:**
- **All strips pulse together**: Synchronized scaling on energy peaks
- **Scale pattern**: Normal (1.0) → Peak (1.2) → Normal (1.0)
- **Duration**: 1 frame scale-up, 1 frame scale-down
- **Timing**: Energy peaks converted to frame numbers using project FPS

**Technical details:**
- Energy peak times converted to frame numbers using project FPS
- Each video strip gets `transform.scale_x/y` keyframes
- Audio analysis uses `librosa.feature.rms()` + peak detection
- Scene-level keyframes: `sequence_editor.sequences_all[strip_name].transform.scale_x/y`

#### Audio Analysis Data Format

Both animations use data from `analysis/[audio_file]_analysis.json`:

```json
{
  "duration": 180.36,
  "tempo": {"bpm": 120.0, "confidence": 0.85},
  "animation_events": {
    "beats": [0.5, 1.0, 1.5, 2.0, 2.5, 3.0],
    "energy_peaks": [2.1, 5.8, 12.3, 18.7, 24.2],
    "sections": [
      {"start": 0.0, "end": 32.1, "label": "intro"},
      {"start": 32.1, "end": 96.4, "label": "verse"}
    ],
    "onsets": [0.12, 0.54, 1.02, 1.48, 2.01]
  },
  "frequency_bands": {
    "bass": [0.8, 1.2, 0.6, 1.5, 0.9],
    "mid": [0.5, 0.7, 0.9, 0.6, 0.8],
    "treble": [0.3, 0.6, 0.4, 0.7, 0.5]
  }
}
```

**Data sources:**
- **Beat-switch**: Uses `animation_events.beats` timestamps
- **Energy-pulse**: Uses `animation_events.energy_peaks` timestamps
- **Section-transition** (future): Uses `animation_events.sections` boundaries
- **Multi-PiP** (future): Uses `animation_events.onsets` + `frequency_bands`