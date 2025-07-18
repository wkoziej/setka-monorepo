# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Cinemon is a **Blender VSE (Video Sequence Editor) automation package** within the Setka monorepo. It creates parametric Blender projects from OBS recordings with audio-driven animations.

## Architecture Overview

### Core Components

- **project_manager.py**: Python API for creating VSE projects via subprocess calls to Blender
- **vse_script.py**: Parametric Blender script executed inside Blender (Polish comments)
- **animation_engine.py**: Delegation pattern routing to specialized animator classes
- **CLI (blend_setup.py)**: Command-line interface with auto-detection of audio analysis needs

### Animation System

Uses **delegation pattern** with three specialized animators:
- **BeatSwitchAnimator**: Alternates video strip visibility on beat events
- **EnergyPulseAnimator**: Scales strips on energy peaks for bass response
- **MultiPipAnimator**: Complex 2x2 grid layout with main cameras + corner PiPs

### Integration Points

- **setka-common**: Uses `RecordingStructureManager` for standardized file organization
- **beatrix**: Consumes audio analysis JSON for animation timing data
- **Blender 4.3+**: Executes via `snap run blender` with environment variables

## Common Development Commands

```bash
# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=src/blender

# Run specific test file
uv run pytest tests/test_animation_engine.py -v

# Run linting
uv run ruff check src/

# Create VSE project from CLI
cinemon-blend-setup ./recording_dir --animation-mode beat-switch

# Create project with Python API
uv run python -c "
from blender import BlenderProjectManager
manager = BlenderProjectManager()
manager.create_vse_project(Path('./recording_dir'), animation_mode='energy-pulse')
"
```

## Key Technical Patterns

### Parametric Blender Execution

Cinemon uses **environment variables** to pass parameters to Blender:

```python
env_vars = {
    'BLENDER_VSE_VIDEO_FILES': 'video1.mp4,video2.mp4',
    'BLENDER_VSE_MAIN_AUDIO': '/path/to/audio.m4a',
    'BLENDER_VSE_ANIMATION_MODE': 'beat-switch',
    'BLENDER_VSE_AUDIO_ANALYSIS_FILE': '/path/to/analysis.json'
}
```

### Blender Mock System

**Critical for testing**: `conftest.py` provides global `bpy` mock since Blender is not available during tests:

```python
@pytest.fixture(autouse=True)
def mock_bpy(monkeypatch):
    """Mock bpy module for tests running outside Blender."""
```

### Audio Analysis Integration

- **Auto-detection**: CLI checks for existing analysis files before creating new ones
- **Beatrix integration**: Uses `analyze_audio_command()` to generate timing data
- **File naming**: Analysis files follow pattern `{audio_stem}_analysis.json`

## File Structure Conventions

Expected recording structure (managed by setka-common):
```
recording_name/
├── metadata.json           # OBS metadata
├── extracted/              # Video/audio files
│   ├── Camera1.mp4        
│   └── Microphone.m4a     
├── analysis/              # Audio analysis JSON
│   └── audio_analysis.json
└── blender/               # VSE projects (created by cinemon)
    ├── project.blend
    └── render/
        └── final.mp4
```

## Animation Mode Details

### Legacy Animation Modes

#### beat-switch
- **Purpose**: Alternates video strip visibility on beat events
- **Data**: Uses `animation_events.beats` array from beatrix
- **Implementation**: Keyframes `blend_alpha` property

#### energy-pulse
- **Purpose**: Scales all strips simultaneously on energy peaks
- **Data**: Uses `animation_events.energy_peaks` array
- **Implementation**: Keyframes `transform.scale_x/y` properties

#### multi-pip
- **Purpose**: Complex 2x2 grid with main cameras + corner PiPs
- **Data**: Uses `sections`, `beats`, and `energy_peaks` arrays
- **Layout**: Main cameras (strips 0-1) switch on sections, corner PiPs (strips 2+) pulse on energy

### New Compositional Animation System

#### compositional
- **Purpose**: Combines custom layouts with multiple independent animations
- **Architecture**: Uses `AnimationCompositor` with `RandomLayout` and modular animations
- **Configuration**: Environment variables control layout and animation parameters
- **Animations**: `ScaleAnimation`, `ShakeAnimation`, `RotationWobbleAnimation`

**Environment Variables:**
```bash
export BLENDER_VSE_ANIMATION_MODE="compositional"
export BLENDER_VSE_LAYOUT_TYPE="random"
export BLENDER_VSE_LAYOUT_CONFIG="overlap_allowed=false,seed=42,margin=0.05"
export BLENDER_VSE_ANIMATION_CONFIG="scale:bass:0.3:2,shake:beat:10.0:2,rotation:beat:1.0:3"
```

**Supported Layouts:**
- `random`: Random positioning with collision detection

**Supported Animations:**
- `scale:trigger:intensity:duration` - Scale animation on events
- `shake:trigger:intensity:frames` - Position shake animation
- `rotation:trigger:degrees:frames` - Rotation wobble animation

## Testing Considerations

### Test Isolation Issues

Some tests may fail when run together due to global state in Blender mocks. If encountering test failures:

```bash
# Run individual test files instead of entire suite
uv run pytest tests/test_animation_engine.py
uv run pytest tests/test_project_manager.py
```

### Mock Configuration

Tests that need specific Blender configurations should use the `mock_bpy` fixture:

```python
def test_something(mock_bpy):
    mock_bpy.context.scene.render.fps = 60
    # test code here
```

## CLI Usage Patterns

### Basic Project Creation
```bash
cinemon-blend-setup ./recording_dir
```

### With Audio Analysis
```bash
# Auto-runs beatrix if no analysis exists
cinemon-blend-setup ./recording_dir --animation-mode beat-switch

# Force new analysis
cinemon-blend-setup ./recording_dir --analyze-audio --animation-mode energy-pulse
```

### Complex Multi-Camera Setups
```bash
# Requires --main-audio when multiple audio files exist
cinemon-blend-setup ./recording_dir \
  --animation-mode multi-pip \
  --main-audio "Main Audio.m4a" \
  --beat-division 4
```

### New Compositional Animation System
```bash
# Random layout with multiple animations
export BLENDER_VSE_ANIMATION_MODE="compositional"
export BLENDER_VSE_LAYOUT_TYPE="random"
export BLENDER_VSE_LAYOUT_CONFIG="overlap_allowed=false,seed=42"
export BLENDER_VSE_ANIMATION_CONFIG="scale:bass:0.3:2,shake:beat:5.0:2"
cinemon-blend-setup ./recording_dir

# Controlled random layout with multiple effects
export BLENDER_VSE_LAYOUT_CONFIG="margin=0.1,min_scale=0.4,max_scale=0.8"
export BLENDER_VSE_ANIMATION_CONFIG="scale:bass:0.5,rotation:beat:2.0:4"
cinemon-blend-setup ./recording_dir --animation-mode compositional
```

## Integration with Broader Pipeline

Cinemon operates as step 3 in the Setka pipeline:
1. **obsession**: Extracts media from OBS recordings
2. **beatrix**: Analyzes audio for timing data
3. **cinemon**: Creates animated Blender projects ← YOU ARE HERE
4. **medusa**: Uploads finished videos to social media

## Error Handling

Common issues and solutions:
- **Missing analysis file**: CLI auto-detects and runs beatrix
- **Blender not found**: Uses `snap run blender` by default
- **No video files**: Validates extracted directory before processing
- **Invalid animation mode**: Validates against supported modes list

## Environment Requirements

- **Blender 4.3+**: Must be available via `snap run blender` or custom executable
- **FFmpeg**: Required for video processing (inherited from obsession)
- **Audio analysis**: Auto-generated via beatrix integration