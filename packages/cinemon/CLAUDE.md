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
- **config/**: YAML configuration system with preset management and auto-discovery
  - **CinemonConfigGenerator**: High-level API for generating YAML configurations
  - **MediaDiscovery**: Auto-discovery of video/audio files in recording directories
  - **PresetManager**: Built-in and custom preset management

### Animation System

Uses **delegation pattern** with three specialized animators:
- **BeatSwitchAnimator**: Alternates video strip visibility on beat events
- **EnergyPulseAnimator**: Scales strips on energy peaks for bass response
- **MultiPipAnimator**: Complex 2x2 grid layout with main cameras + corner PiPs

### Integration Points

- **setka-common**: Uses `RecordingStructureManager` for standardized file organization
- **beatrix**: Consumes audio analysis JSON for animation timing data
- **Blender 4.3+**: Executes via `snap run blender` with YAML configuration system

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

# Create VSE project from CLI with preset
cinemon-blend-setup ./recording_dir --preset vintage

# Create VSE project with legacy mode
cinemon-blend-setup ./recording_dir --animation-mode beat-switch

# Generate YAML config with Python API
uv run python -c "
from blender.config import CinemonConfigGenerator
generator = CinemonConfigGenerator()
config_path = generator.generate_preset('./recording_dir', 'vintage')
print(f'Generated: {config_path}')
"
```

## Key Technical Patterns

### YAML Configuration System

Cinemon uses **YAML configuration files** for parametric Blender execution:

```yaml
project:
  video_files: [Camera1.mp4, Camera2.mp4]
  main_audio: "main_audio.m4a"
  fps: 30
  resolution: {width: 1920, height: 1080}

layout:
  type: random
  config:
    overlap_allowed: false
    seed: 42
    margin: 0.1

animations:
  - type: scale
    trigger: bass
    intensity: 0.3
    target_strips: [Camera1, Camera2]
  - type: vintage_color
    trigger: one_time
    sepia_amount: 0.4
    target_strips: []
```

### Configuration Generation

```python
from blender.config import CinemonConfigGenerator

generator = CinemonConfigGenerator()

# Generate from preset
config_path = generator.generate_preset("./recording", "vintage")

# Generate custom configuration
config_path = generator.generate_config(
    "./recording",
    layout={"type": "random", "config": {"seed": 42}},
    animations=[{"type": "scale", "trigger": "bass", "intensity": 0.5}]
)
```

### Blender Mock System

**Critical for testing**: `conftest.py` provides global `bpy` mock since Blender is not available during tests:

```python
@pytest.fixture(autouse=True)
def mock_bpy(monkeypatch):
    """Mock bpy module for tests running outside Blender."""
```

### Media Discovery and Auto-Detection

- **Auto-discovery**: `MediaDiscovery` class automatically finds video/audio files in recording directories
- **Validation**: Validates recording structure before processing
- **Main audio detection**: Automatically detects main audio file or prompts for selection with multiple files
- **Polish filename support**: Full UTF-8 support for Polish characters in filenames

### Audio Analysis Integration

- **Auto-detection**: CLI checks for existing analysis files before creating new ones
- **Beatrix integration**: Uses `analyze_audio_command()` to generate timing data
- **File naming**: Analysis files follow pattern `{audio_stem}_analysis.json`

## File Structure Conventions

Expected recording structure (managed by setka-common):
```
recording_name/
├── metadata.json                    # OBS metadata
├── extracted/                       # Video/audio files
│   ├── Camera1.mp4        
│   ├── Camera2.mp4
│   └── main_audio.m4a     
├── analysis/                        # Audio analysis JSON
│   └── audio_analysis.json
├── animation_config_vintage.yaml    # Generated YAML config (preset-based)
├── animation_config.yaml            # Generated YAML config (custom)
└── blender/                         # VSE projects (created by cinemon)
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

### YAML Configuration System with Presets

#### Built-in Presets

**vintage** - Classic film effects:
```yaml
layout:
  type: random
  config: {margin: 0.1, seed: 1950}
animations:
  - {type: shake, trigger: beat, intensity: 2.0}
  - {type: jitter, trigger: continuous, intensity: 1.0}
  - {type: brightness_flicker, trigger: beat, intensity: 0.1}
  - {type: black_white, trigger: one_time, intensity: 0.6}
  - {type: film_grain, trigger: one_time, intensity: 0.15}
  - {type: vintage_color, trigger: one_time, sepia_amount: 0.4}
```

**music-video** - High-energy effects:
```yaml
layout:
  type: random
  config: {margin: 0.05, seed: 100, min_scale: 0.4, max_scale: 0.9}
animations:
  - {type: scale, trigger: bass, intensity: 0.5, duration_frames: 3}
  - {type: shake, trigger: beat, intensity: 12.0}
  - {type: rotation, trigger: energy_peaks, degrees: 2.0}
```

**minimal** - Basic effects:
```yaml
animations:
  - {type: scale, trigger: bass, intensity: 0.2, duration_frames: 3}
```

**beat-switch** - Legacy compatibility:
```yaml
animations:
  - {type: scale, trigger: beat, intensity: 0.2}
```

#### Selective Strip Targeting

All animations support `target_strips` for selective application:

```yaml
animations:
  - type: scale
    trigger: bass
    intensity: 0.5
    target_strips: [Camera1, Camera2]  # Only these strips
    
  - type: vintage_color
    trigger: one_time
    sepia_amount: 0.4
    target_strips: []  # All strips (default)
```

#### Supported Animation Types

**Transform Animations:**
- `scale` - Scale changes on audio events
- `shake` - Position shake effects  
- `rotation` - Rotation wobble effects
- `jitter` - Continuous random position changes

**Visual Effects:**
- `brightness_flicker` - Brightness modulation
- `vintage_color` - Sepia tint and contrast boost
- `black_white` - Desaturation effects
- `film_grain` - Grain overlay effects

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

### Preset-Based Project Creation
```bash
# Basic preset usage
cinemon-blend-setup ./recording_dir --preset vintage

# Preset with custom overrides
cinemon-blend-setup ./recording_dir --preset music-video \
  --main-audio "main_audio.m4a" \
  --beat-division 8

# Available presets: vintage, music-video, minimal, beat-switch
cinemon-blend-setup ./recording_dir --preset minimal
```

### YAML Configuration File Usage
```bash
# Generate YAML config first, then use it
cinemon-blend-setup ./recording_dir --config ./animation_config.yaml

# Config takes precedence over other parameters
cinemon-blend-setup ./recording_dir --config ./custom_config.yaml
```

### Legacy Animation Modes (Deprecated)
```bash
# Still supported for backwards compatibility
cinemon-blend-setup ./recording_dir --animation-mode beat-switch
cinemon-blend-setup ./recording_dir --animation-mode energy-pulse

# Auto-runs beatrix if no analysis exists
cinemon-blend-setup ./recording_dir --analyze-audio --animation-mode multi-pip
```

### Advanced Configuration Generation
```bash
# Using Python API for custom configurations
uv run python -c "
from blender.config import CinemonConfigGenerator
generator = CinemonConfigGenerator()

# Generate from preset with overrides
config_path = generator.generate_preset(
    './recording', 'vintage', 
    seed=42, fps=60, main_audio='audio.m4a'
)

# Generate completely custom configuration  
layout = {'type': 'random', 'config': {'seed': 123}}
animations = [
    {'type': 'scale', 'trigger': 'bass', 'intensity': 0.8, 'target_strips': ['Camera1']},
    {'type': 'vintage_color', 'trigger': 'one_time', 'sepia_amount': 0.6}
]
config_path = generator.generate_config('./recording', layout, animations)
print(f'Generated: {config_path}')
"

## Integration with Broader Pipeline

Cinemon operates as step 3 in the Setka pipeline:
1. **obsession**: Extracts media from OBS recordings
2. **beatrix**: Analyzes audio for timing data
3. **cinemon**: Creates animated Blender projects ← YOU ARE HERE
4. **medusa**: Uploads finished videos to social media

## Configuration Management

### Built-in Presets
- **vintage**: Classic film effects with grain, jitter, and sepia tones
- **music-video**: High-energy effects with scale, shake, and rotation
- **minimal**: Basic scale animation for subtle effects
- **beat-switch**: Legacy compatibility mode

### Media Discovery
```python
from blender.config import MediaDiscovery

discovery = MediaDiscovery(Path("./recording"))
video_files = discovery.discover_video_files()  # Auto-find video files
audio_files = discovery.discover_audio_files()  # Auto-find audio files
main_audio = discovery.detect_main_audio()     # Auto-detect main audio
validation = discovery.validate_structure()    # Validate directory structure
```

### Preset Customization
```python
from blender.config import PresetManager

manager = PresetManager()
presets = manager.list_presets()              # List all available presets
vintage = manager.get_preset("vintage")       # Get specific preset
manager.create_custom_preset("my-style", {...})  # Create custom preset
```

## Error Handling

Common issues and solutions:
- **Missing analysis file**: CLI auto-detects and runs beatrix
- **Blender not found**: Uses `snap run blender` by default
- **No video files**: `MediaDiscovery` validates directory structure before processing
- **Multiple audio files**: Prompts for `--main-audio` parameter selection
- **Invalid preset**: Validates against available preset list
- **Invalid configuration**: YAML validation with clear error messages

## Environment Requirements

- **Blender 4.3+**: Must be available via `snap run blender` or custom executable
- **FFmpeg**: Required for video processing (inherited from obsession)
- **Audio analysis**: Auto-generated via beatrix integration