# Cinemon

Blender VSE project preparation and animation tools for the Setka monorepo.

## Features

- Automated Blender VSE project creation from OBS recordings
- Audio-driven animations (beat-switch, energy-pulse, multi-pip)
- Parametric VSE script generation
- Layout management for multi-camera setups
- Keyframe animation helpers

## Installation

```bash
# From monorepo root
uv sync
```

## Usage

### CLI

```bash
# Create Blender VSE project
cinemon-blend-setup ./recording_dir

# With animation
cinemon-blend-setup ./recording_dir --animation-mode beat-switch
```

### Python API

```python
from blender import BlenderProjectManager

manager = BlenderProjectManager()
blend_file = manager.create_vse_project(
    recording_path=Path("./recording_dir"),
    animation_mode="beat-switch"
)
```

## Testing

```bash
# Run tests
uv run pytest

# With coverage
uv run pytest --cov=src/blender
```