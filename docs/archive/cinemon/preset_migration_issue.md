# Unify Preset Formats: Migrate PresetManager to YAML-based System

## Problem

Currently, cinemon has two different preset formats that serve the same purpose but use incompatible structures:

1. **PresetManager format** (Python code in `src/cinemon/config/preset_manager.py`):
   - Uses `animations` field with a flat list
   - Each animation has `target_strips` array (usually empty)
   - Hardcoded in Python as dictionaries

2. **YAML preset format** (files in `blender_addon/example_presets/`):
   - Uses `strip_animations` field with per-strip grouping
   - Animations are organized by strip name (Camera1, Camera2, Screen, etc.)
   - More flexible and allows precise per-strip control
   - Stored as YAML files, easier to edit and share

## Current Impact

- **Confusion**: Developers and users encounter two different formats for the same concept
- **Test failures**: Tests expect one format while implementation uses another
- **Maintenance burden**: Need to maintain two parallel systems
- **Limited functionality**: PresetManager format doesn't support per-strip animations

## Proposed Solution

Migrate PresetManager to use the YAML-based format that's already used in `example_presets/`:

### 1. Change PresetConfig structure

```python
@dataclass
class PresetConfig:
    """Configuration preset for cinemon."""
    name: str
    description: str
    project: Dict[str, Any]  # Optional project settings
    layout: Dict[str, Any]
    strip_animations: Dict[str, List[Dict[str, Any]]]  # Instead of animations
    audio_analysis: Dict[str, Any]  # Optional analysis settings
```

### 2. Load presets from YAML files

Instead of hardcoding presets in Python:

```python
class PresetManager:
    def __init__(self):
        self.preset_dir = Path(__file__).parent.parent.parent / "blender_addon" / "example_presets"
        self._load_builtin_presets()

    def _load_builtin_presets(self):
        """Load all YAML presets from preset directory."""
        self.builtin_presets = {}
        for yaml_file in self.preset_dir.glob("*.yaml"):
            preset_name = yaml_file.stem
            preset_data = self._load_yaml_preset(yaml_file)
            self.builtin_presets[preset_name] = preset_data
```

### 3. Use exiting presets

Use presets from YAML files in `blender_addon/example_presets/`.

### 4. Update CinemonConfigGenerator

The generator already works with both formats, but should be simplified to only handle the YAML format.

No FALLBACK. KISS.

## Benefits

1. **Single source of truth**: One format for all presets
2. **Easier customization**: Users can edit YAML files directly
3. **Better organization**: Per-strip animations are clearer than flat lists
4. **Consistency**: Same format everywhere reduces confusion
5. **Extensibility**: Easy to add new presets without changing code

## Migration Steps

1. Update PresetConfig dataclass to match YAML structure
2. Implement YAML loading in PresetManager
3. Use existins presets to YAML files
4. Update all tests to use new format
5. Update documentation
6. Remove old format support

## Backward Compatibility

Since PresetManager is primarily used internally by CinemonConfigGenerator, the impact should be minimal. The CLI and main APIs remain unchanged.

## Testing

- All existing tests will need updating to expect the new format
- Add tests for YAML preset loading
- Ensure all example presets load correctly

## Related Files to Update

- `src/cinemon/config/preset_manager.py` - Main implementation
- `tests/test_preset_manager.py` - Update tests
- `src/cinemon/config/cinemon_config_generator.py` - Simplify preset handling
- `docs/` - Update documentation
- Any example code using PresetManager directly
