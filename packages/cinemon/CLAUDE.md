# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Cinemon is a **Blender VSE (Video Sequence Editor) automation package** within the Setka monorepo. It creates parametric Blender projects from OBS recordings with audio-driven animations.

## Architecture Overview

### Core Components

- **src/cinemon/project_manager.py**: Python API for creating VSE projects via subprocess calls to Blender
- **blender_addon/vse_script.py**: Parametric Blender script executed inside Blender (Polish comments)
- **src/cinemon/animation_engine.py**: Delegation pattern routing to specialized animator classes (being migrated)
- **src/cinemon/cli/blend_setup.py**: Command-line interface with auto-detection of audio analysis needs
- **src/cinemon/config/**: YAML configuration system with preset management and auto-discovery
  - **CinemonConfigGenerator**: High-level API for generating YAML configurations
  - **MediaDiscovery**: Auto-discovery of video/audio files in recording directories
  - **PresetManager**: Built-in and custom preset management
- **blender_addon/**: Complete Blender addon with VSE automation modules
  - **vse/**: Core VSE modules (constants, layout_manager, keyframe_helper, etc.)
  - **operators.py**: Blender UI operators
  - **layout_ui.py**: Blender UI panels

### Animation System

Uses **delegation pattern** with three specialized animators:
- **BeatSwitchAnimator**: Alternates video strip visibility on beat events
- **EnergyPulseAnimator**: Scales strips on energy peaks for bass response
- **MultiPipAnimator**: Complex 2x2 grid layout with main cameras + corner PiPs

### Integration Points

- **setka-common**: Uses `RecordingStructureManager` for standardized file organization
  - **NEW**: Also imports validation constants (`VALID_ANIMATION_TYPES`, `VALID_TRIGGERS`, `VALID_LAYOUT_TYPES`)
  - **NEW**: Uses `ConfigValidationError` for consistent error handling
  - **NEW**: Imports `AnimationSpec` TypedDict for type-safe animation configuration
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

# Run linting and formatting
uv run ruff check src/
uv run ruff check --fix src/
uv run ruff format src/

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

## File Structure

```
packages/cinemon/
├── blender_addon/          # Blender addon (executed in Blender)
│   ├── __init__.py        # bl_info and addon registration
│   ├── vse_script.py      # Main VSE configuration script
│   ├── operators.py       # Blender operators
│   ├── layout_ui.py       # UI panels
│   ├── vse/               # VSE modules
│   │   ├── __init__.py    # Module exports
│   │   ├── constants.py
│   │   ├── layout_manager.py
│   │   ├── keyframe_helper.py
│   │   ├── yaml_config.py
│   │   ├── animation_compositor.py
│   │   ├── project_setup.py
│   │   ├── animations/    # Animation implementations
│   │   ├── animators/     # Legacy animators
│   │   ├── effects/       # Visual effects
│   │   └── layouts/       # Layout strategies
│   ├── example_presets/   # YAML preset files
│   └── vendor/            # Dependencies (PyYAML)
├── src/cinemon/           # Python API (outside Blender)
│   ├── __init__.py
│   ├── project_manager.py # Calls Blender subprocess
│   ├── cli/
│   │   ├── blend_setup.py # Main CLI interface
│   │   └── generate_config.py # Config generation CLI
│   ├── config/           # YAML configuration generation
│   │   ├── __init__.py
│   │   ├── cinemon_config_generator.py
│   │   ├── media_discovery.py
│   │   └── preset_manager.py
│   └── utils/            # Development and debugging utilities
│       ├── check_blender_animations.py # Verify animations in .blend files
│       ├── check_blender_vse.py        # Test project generation
│       ├── check_fcurves.py            # Debug FCurves and keyframes
│       ├── debug_import_context.py     # Debug addon import issues
│       └── run_animation_showcase.py   # Generate test project with all animations
└── tests/
    ├── test_project_manager.py
    ├── test_animation_engine.py
    ├── test_config/
    └── blender_addon/     # Tests for addon components
```

## Key Technical Patterns

### YAML Configuration System

Cinemon uses **YAML configuration files** for parametric Blender execution:

```yaml
project:
  base_directory: /path/to/recording
  video_files: [Camera1.mp4, Camera2.mp4]
  main_audio: "main_audio.m4a"
  output_blend: blender/project.blend  # Required for file saving
  fps: 30
  resolution: {width: 1920, height: 1080}

audio_analysis:
  file: analysis/audio_analysis.json  # Path to beatrix analysis

layout:
  type: random
  config:
    overlap_allowed: false
    seed: 42
    margin: 0.1

strip_animations:
  Camera1.mp4:  # Must match exact filename
    - type: scale
      trigger: beat
      intensity: 0.3
  Camera2.mp4:
    - type: shake
      trigger: energy_peaks
      intensity: 8.0
```

The `strip_animations` format groups animations by strip name, allowing precise control over which video strips receive which effects. Each strip can have multiple animations applied.

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

### Import Strategy

Due to the separation between Blender addon and Python API:

1. **In blender_addon/** - Use relative imports with context detection:
   ```python
   from .vse import AnimationConstants, BlenderLayoutManager
   from .vse.yaml_config import BlenderYAMLConfigReader

   # Context-aware imports for addon vs test environments
   from .import_utils import is_running_as_addon
   if is_running_as_addon():
       from .yaml_manager import AnimationYAMLManager
   else:
       from yaml_manager import AnimationYAMLManager
   ```

2. **In src/cinemon/** - Use absolute imports:
   ```python
   from cinemon.config import CinemonConfigGenerator
   from cinemon.cli import blend_setup
   ```

3. **project_manager.py** calls Blender with addon script:
   ```python
   self.script_path = Path(__file__).parent.parent.parent / "blender_addon" / "vse_script.py"
   ```

4. **Addon initialization order**: Critical for proper imports:
   ```python
   # In __init__.py - vendor paths MUST be added before imports
   vendor_path = Path(__file__).parent / "vendor"
   sys.path.insert(0, str(vendor_path))
   from . import animation_panel, layout_ui, operators
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
- **Event format**: Audio analysis must use simple timestamps (not dict objects):
  ```json
  {
    "animation_events": {
      "beats": [0.0, 1.0, 2.0, ...],
      "energy_peaks": [2.0, 6.0, 10.0, ...]
    }
  }
  ```

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

**minimal** - Basic effects preset (see `blender_addon/example_presets/minimal.yaml`)

#### Selective Strip Targeting

With the `strip_animations` format, you can precisely control which strips receive which effects:

```yaml
strip_animations:
  Camera1:
    - type: scale
      trigger: bass
      intensity: 0.5
    - type: vintage_color
      trigger: one_time
      sepia_amount: 0.4

  Camera2:
    - type: shake
      trigger: beat
      intensity: 2.0

  all:  # Special key for applying to all strips
    - type: brightness_flicker
      trigger: beat
      intensity: 0.15
```

#### Supported Animation Types

**Transform Animations (Working):**
- `scale` - Scale changes on audio events (triggers: beat, bass, energy_peaks)
- `shake` - Position shake effects (triggers: beat, bass, energy_peaks)
- `rotation` - Rotation wobble effects (triggers: beat, energy_peaks)

**Visual Effects (Working):**
- `brightness_flicker` - Brightness modulation (triggers: beat, bass)
- `black_white` - Desaturation effects (triggers: one_time, beat, bass, energy_peaks) - **NEW: dual-mode support**
- `vintage_color` - Sepia tint and contrast boost (triggers: one_time, beat, bass, energy_peaks) - **NEW: dual-mode support**

**Known Issues:**
- `jitter` - Continuous random position changes (⚠️ Issue #26: continuous trigger not implemented)

## Animation Verification

### Animation Showcase Generator

**NEW**: Complete test project generator for testing all animation types:

```bash
# Generate complete showcase project with all animations
uv run python src/cinemon/utils/run_animation_showcase.py

# Generate in specific directory
uv run python src/cinemon/utils/run_animation_showcase.py --dir ~/path/to/showcase
```

This creates:
- 9 colored test videos (strip_0.mp4 through strip_8.mp4)
- Synthetic audio with regular beats and energy peaks
- Complete audio analysis JSON with beatrix-compatible format
- YAML configuration demonstrating all working animation types
- Fully functional .blend file ready for testing

### Checking Animation Results

Use the provided utilities to verify animations are working correctly:

```bash
# Check animations in generated .blend file
uv run python src/cinemon/utils/check_blender_animations.py "/path/to/file.blend"

# Test full project generation
uv run python src/cinemon/utils/check_blender_vse.py

# Debug FCurves and keyframes
uv run python src/cinemon/utils/check_fcurves.py

# Debug addon import issues
uv run python src/cinemon/utils/debug_import_context.py
```

### Animation Storage in Blender

**CRITICAL**: Animations are stored in `bpy.context.scene.animation_data.action`, NOT on individual strips:

```python
# WRONG - animations are NOT here
if strip.animation_data and strip.animation_data.action:
    # This will be empty

# CORRECT - animations are stored at scene level
if bpy.context.scene.animation_data and bpy.context.scene.animation_data.action:
    action = bpy.context.scene.animation_data.action
    vse_fcurves = [fc for fc in action.fcurves if 'sequence_editor' in fc.data_path]
    # FCurves with paths like: sequence_editor.strips_all["StripName"].transform.scale_x
```

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

### Test Markers

Available pytest markers defined in `pyproject.toml`:
- `unit`: Unit tests (default)
- `integration`: Integration tests requiring external services
- `slow`: Slow tests

### Coverage Configuration

Test coverage is configured with:
- Minimum 80% coverage required (`--cov-fail-under=80`)
- HTML coverage reports generated in `htmlcov/`
- Source coverage from `src/` directory only
- Excludes test files and `__init__.py` from coverage calculation

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
- **vintage**: Classic film effects with jitter, sepia tones, and desaturation pulses
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
- **Addon import errors**: Fixed by proper path ordering in `__init__.py` - vendor paths must be added BEFORE module imports
- **Animation verification**: Use `check_blender_animations.py` to verify keyframes are created correctly
- **.blend file not saved**: Ensure `output_blend` is specified in YAML project section
- **Animations not applying**: Strip names in YAML must match exact video filenames (including .mp4)
- **Event format errors**: Audio analysis events must be simple timestamps, not dict objects

## Troubleshooting

### Addon Not Loading

If Blender addon fails to load:
1. Check import order in `__init__.py` - vendor paths must come before imports
2. Verify `is_running_as_addon()` context detection works correctly
3. Use `debug_import_context.py` to diagnose import issues

### Animations Not Visible

If animations appear to be missing:
1. Check at scene level, not strip level: `bpy.context.scene.animation_data.action`
2. Look for FCurves with `sequence_editor` in data_path
3. Use `check_blender_animations.py` to get detailed keyframe analysis
4. Verify audio analysis file exists and contains events

## Environment Requirements

- **Blender 4.5+**: Must be available via `snap run blender` or custom executable
- **FFmpeg**: Required for video processing (inherited from obsession)
- **Audio analysis**: Auto-generated via beatrix integration
- **PyYAML**: Included in `vendor/` directory for addon compatibility
- **Python 3.11+**: Required for Blender 4.5+ compatibility
