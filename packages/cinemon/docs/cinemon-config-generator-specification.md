# CinemonConfigGenerator Specification

## Overview

CinemonConfigGenerator is a utility class that simplifies the creation of YAML configuration files for Blender VSE projects. It provides high-level APIs for generating configurations from simple parameters, preset templates, and auto-discovery mechanisms.

## Problem Statement

Currently, creating YAML configuration for cinemon requires:
1. Manual YAML writing with complex syntax
2. Manual discovery of video/audio files in recording directories
3. Manual path resolution and validation
4. Deep knowledge of animation parameters and layout options
5. Understanding of strip targeting syntax

This creates barriers for:
- **Fermata integration** - needs simple API calls
- **CLI users** - want quick config generation
- **Script authors** - need programmatic config creation
- **Interactive users** - want templates to customize

## Solution Architecture

### Core Components

```python
class CinemonConfigGenerator:
    """Main generator class with multiple generation methods."""

    # High-level preset generation
    def generate_preset(recording_dir, preset_name, **overrides) -> Path

    # Custom configuration generation
    def generate_config(recording_dir, **params) -> Path

    # Template generation for manual editing
    def generate_template(recording_dir, **params) -> Path

    # Validation and auto-discovery
    def discover_media_files(recording_dir) -> MediaDiscovery
    def validate_recording_structure(recording_dir) -> ValidationResult

class PresetManager:
    """Manages built-in configuration presets."""

    def get_preset(name) -> PresetConfig
    def list_presets() -> List[str]
    def create_custom_preset(name, config) -> None

class MediaDiscovery:
    """Auto-discovery of media files in recording directory."""

    video_files: List[str]
    audio_files: List[str]
    main_audio: Optional[str]
    analysis_files: List[str]
```

## API Design

### 1. Preset-Based Generation

#### Simple Presets
```python
# Generate vintage film style configuration
config_path = CinemonConfigGenerator.generate_preset(
    recording_dir="./recording_20250105_143022",
    preset="vintage"
)

# Generate energetic music video style
config_path = CinemonConfigGenerator.generate_preset(
    recording_dir="./recording_20250105_143022",
    preset="music-video",
    seed=42  # Override default seed
)
```

#### Available Presets
- **`vintage`** - Classic film effects (jitter, grain, sepia, shake)
- **`music-video`** - High-energy effects (scale on bass, shake on beat, rotation)
- **`podcast`** - Calm, professional (subtle scale, minimal shake)
- **`gaming`** - Energetic gaming content (overlapping layout, multiple effects)
- **`minimal`** - Clean, simple (basic scale on bass only)
- **`beat-switch`** - Legacy compatibility (replicates old beat-switch mode)

### 2. Custom Configuration Generation

#### Flexible Parameter API
```python
config_path = CinemonConfigGenerator.generate_config(
    recording_dir="./recording_20250105_143022",
    main_audio="main_audio.m4a",  # Optional - auto-detected if not specified
    layout={
        "type": "random",
        "config": {
            "overlap_allowed": False,
            "seed": 42,
            "margin": 0.05
        }
    },
    animations=[
        {
            "type": "scale",
            "trigger": "bass",
            "target_strips": ["Camera1", "Camera2"],
            "intensity": 0.3,
            "duration_frames": 2
        },
        {
            "type": "vintage_color",
            "trigger": "one_time",
            "target_strips": ["Camera3"],
            "sepia_amount": 0.4,
            "contrast_boost": 0.3
        }
    ],
    project_overrides={
        "fps": 60,
        "resolution": {"width": 3840, "height": 2160}
    }
)
```

## Built-in Presets

### 1. Vintage Preset
```yaml
# Equivalent YAML configuration
layout:
  type: random
  config:
    overlap_allowed: false
    margin: 0.1
    min_scale: 0.5
    max_scale: 0.8
    seed: 1950

animations:
  - type: shake
    trigger: beat
    intensity: 2.0
    return_frames: 2
    target_strips: []  # All strips
  - type: jitter
    trigger: continuous
    intensity: 1.0
    min_interval: 3
    max_interval: 8
    target_strips: []
  - type: brightness_flicker
    trigger: beat
    intensity: 0.1
    return_frames: 1
    target_strips: []
  - type: black_white
    trigger: one_time
    intensity: 0.6
    target_strips: []
  - type: film_grain
    trigger: one_time
    intensity: 0.15
    target_strips: []
  - type: vintage_color
    trigger: one_time
    sepia_amount: 0.4
    contrast_boost: 0.3
    target_strips: []
```

### 2. Music Video Preset
```yaml
layout:
  type: random
  config:
    overlap_allowed: false
    margin: 0.05
    min_scale: 0.4
    max_scale: 0.9
    seed: 100

animations:
  - type: scale
    trigger: bass
    intensity: 0.5
    duration_frames: 3
    target_strips: []
  - type: shake
    trigger: beat
    intensity: 12.0
    return_frames: 2
    target_strips: []
  - type: rotation
    trigger: energy_peaks
    degrees: 2.0
    return_frames: 5
    target_strips: []
```

## CLI Integration

### New CLI Commands

#### Config Generation Commands
```bash
# Generate preset configuration
cinemon-generate-config ./recording --preset vintage

# List available presets
cinemon-list-presets

```

#### Enhanced Main CLI
```bash
# Use generated config (current)
cinemon-blend-setup ./recording --config animation_config.yaml

# Generate config on-the-fly with preset
cinemon-blend-setup ./recording --preset vintage

```

## File Organization

### Generated Configuration Files
```
recording_name/
├── animation_config.yaml          # Main configuration
├── animation_config_vintage.yaml  # Preset-based configs
```

### Configuration Naming Convention
- `animation_config.yaml` - Default name for main config
- `animation_config_{preset}.yaml` - Preset-based configs
- `animation_config_custom.yaml` - User-customized configs

## Advanced Features

### 1. Custom Preset Creation
```python
# Create and save custom preset
custom_preset = {
    "layout": {"type": "random", "config": {"seed": 123}},
    "animations": [
        {"type": "scale", "trigger": "bass", "intensity": 0.2}
    ]
}

PresetManager.create_custom_preset("my-style", custom_preset)

# Use custom preset
config_path = CinemonConfigGenerator.generate_preset(
    recording_dir="./recording",
    preset="my-style"
)
```

## Error Handling

## Implementation Considerations


### Integration Points
1. **Fermata Integration** - Simple preset-based generation
2. **CLI Integration** - Enhanced command-line interface

## Migration Strategy

### Phase 1: Core Implementation
1. Implement `CinemonConfigGenerator` class
2. Add basic preset system (vintage)
3. Add basic CLI integration

### Phase 2: Integration and Polish
1. Full fermata integration
2. Enhanced error handling and recovery
3. Documentation and examples

## Success Criteria

1. **Ease of Use** - Generate working config in 1-2 lines of code
2. **Flexibility** - Support both simple presets and complex customization
3. **Reliability** - Robust error handling and validation
4. **Integration** - Seamless fermata and CLI integration

## Example Usage Scenarios

### Scenario 1: Fermata Integration
```python
# In fermata ProcessRunner
config_path = CinemonConfigGenerator.generate_preset(
    recording_dir=recording.path,
    preset="beat-switch"  # Legacy compatibility
)
# Then call: cinemon-blend-setup recording.path --config config_path
```

### Scenario 2: Quick CLI Usage
```bash
# Generate vintage style config and use it
cinemon-blend-setup ./recording --preset vintage
```

### Scenario 3: Custom Script
```python
# Complex custom configuration
config_path = CinemonConfigGenerator.generate_config(
    recording_dir="./my_recording",
    layout={"type": "random", "config": {"seed": 42}},
    animations=[
        {"type": "scale", "trigger": "bass", "target_strips": ["Camera1"]},
        {"type": "vintage_color", "trigger": "one_time", "target_strips": ["Camera2"]}
    ]
)
```
