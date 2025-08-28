# ABOUTME: YAML configuration manager for reading and writing animation data
# ABOUTME: Provides caching, path resolution, and parameter updates for single source of truth

"""YAML configuration manager for animation data."""

from pathlib import Path
import sys
from typing import Any, Dict, List

# Import utilities for addon detection
try:
    from .import_utils import is_running_as_addon
except ImportError:
    from import_utils import is_running_as_addon

# Import YAML with context detection
if is_running_as_addon():
    # Running as Blender addon - vendor path is already in sys.path from __init__.py
    import yaml
else:
    # Running standalone/tests - need to add vendor path manually
    vendor_path = Path(__file__).parent / "vendor"
    if str(vendor_path) not in sys.path:
        sys.path.insert(0, str(vendor_path))
    import yaml

try:
    import bpy
except ImportError:
    # For testing without Blender
    class MockBpy:
        class data:
            filepath = ""

    bpy = MockBpy()


class AnimationYAMLManager:
    """Manager for reading and writing animation data to/from YAML."""

    def __init__(self):
        self._cache = {}
        self._mtime = {}

    def resolve_config_path(self, context) -> Path:
        """Resolve config path, handling relative paths from .blend location."""
        config_path = getattr(context.scene, "cinemon_config_path", "")
        if not config_path:
            return None

        path = Path(config_path)

        # If absolute path, use directly
        if path.is_absolute():
            return path

        # If relative path, resolve from .blend file directory
        blend_file = bpy.data.filepath
        if blend_file:
            blend_dir = Path(blend_file).parent
            resolved_path = blend_dir / path
            return resolved_path.resolve()

        return path

    def get_strip_animations(self, context, strip_name: str) -> List[Dict[str, Any]]:
        """Read animations for strip from YAML file with caching."""
        config_path = self.resolve_config_path(context)
        if not config_path or not config_path.exists():
            return []

        try:
            # Check cache
            current_mtime = config_path.stat().st_mtime
            cache_key = str(config_path)

            if cache_key in self._cache and self._mtime.get(cache_key) == current_mtime:
                # Cache hit
                strip_animations = self._cache[cache_key]
            else:
                # Cache miss - reload file
                with open(config_path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f)

                strip_animations = config.get("strip_animations", {}) if config else {}
                self._cache[cache_key] = strip_animations
                self._mtime[cache_key] = current_mtime

            # Return animations for specific strip or "all"
            if strip_name in strip_animations:
                return strip_animations[strip_name]
            elif "all" in strip_animations:
                return strip_animations["all"]

            return []

        except Exception as e:
            print(f"Error reading YAML config: {e}")
            return []

    def update_animation_parameter(
        self,
        context,
        strip_name: str,
        animation_index: int,
        param_name: str,
        new_value: float,
    ) -> bool:
        """Update animation parameter in YAML file."""
        config_path = self.resolve_config_path(context)
        if not config_path or not config_path.exists():
            return False

        try:
            # Read current config
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            if not config or "strip_animations" not in config:
                return False

            # Update parameter
            strip_animations = config["strip_animations"]
            if strip_name in strip_animations:
                animations = strip_animations[strip_name]
                if 0 <= animation_index < len(animations):
                    animations[animation_index][param_name] = new_value

                    # Write back to file
                    with open(config_path, "w", encoding="utf-8") as f:
                        yaml.dump(
                            config,
                            f,
                            default_flow_style=False,
                            allow_unicode=True,
                            sort_keys=False,
                        )

                    # Clear cache
                    cache_key = str(config_path)
                    if cache_key in self._cache:
                        del self._cache[cache_key]

                    return True

            return False

        except Exception as e:
            print(f"Error updating YAML config: {e}")
            return False

    def add_animation_to_strip(
        self, context, strip_name: str, animation: Dict[str, Any]
    ) -> bool:
        """Add animation to strip in YAML file."""
        config_path = self.resolve_config_path(context)
        if not config_path or not config_path.exists():
            return False

        try:
            # Read current config
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            if not config:
                config = {}

            # Initialize strip_animations if needed
            if "strip_animations" not in config:
                config["strip_animations"] = {}

            strip_animations = config["strip_animations"]

            # Initialize strip list if needed
            if strip_name not in strip_animations:
                strip_animations[strip_name] = []

            # Add animation
            strip_animations[strip_name].append(animation)

            # Write back to file
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    config,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )

            # Clear cache
            cache_key = str(config_path)
            if cache_key in self._cache:
                del self._cache[cache_key]

            return True

        except Exception as e:
            print(f"Error adding animation to YAML config: {e}")
            return False

    def remove_animation_from_strip(
        self, context, strip_name: str, animation_index: int
    ) -> bool:
        """Remove animation from strip in YAML file."""
        config_path = self.resolve_config_path(context)
        if not config_path or not config_path.exists():
            return False

        try:
            # Read current config
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            if not config or "strip_animations" not in config:
                return False

            strip_animations = config["strip_animations"]
            if strip_name in strip_animations:
                animations = strip_animations[strip_name]
                if 0 <= animation_index < len(animations):
                    animations.pop(animation_index)

                    # If strip has no animations left, remove the strip entry
                    if not animations:
                        del strip_animations[strip_name]

                    # Write back to file
                    with open(config_path, "w", encoding="utf-8") as f:
                        yaml.dump(
                            config,
                            f,
                            default_flow_style=False,
                            allow_unicode=True,
                            sort_keys=False,
                        )

                    # Clear cache
                    cache_key = str(config_path)
                    if cache_key in self._cache:
                        del self._cache[cache_key]

                    return True

            return False

        except Exception as e:
            print(f"Error removing animation from YAML config: {e}")
            return False

    def get_available_animation_types(self) -> List[str]:
        """Get list of available animation types."""
        return [
            "scale",
            "shake",
            "rotation",
            "jitter",
            "brightness_flicker",
            "black_white",
            "vintage_color",
            "visibility",
        ]

    def get_available_triggers(self) -> List[str]:
        """Get list of available triggers."""
        return ["beat", "bass", "energy_peaks", "one_time", "continuous"]

    def create_default_animation(
        self, animation_type: str, trigger: str
    ) -> Dict[str, Any]:
        """Create animation with default parameters."""
        # Default parameters by animation type
        defaults = {
            "scale": {"intensity": 0.3, "duration_frames": 3},
            "shake": {"intensity": 2.0, "duration_frames": 2},
            "rotation": {"degrees": 5.0, "duration_frames": 3},
            "jitter": {"intensity": 1.0},
            "brightness_flicker": {"intensity": 0.1, "duration_frames": 1},
            "black_white": {"intensity": 0.6, "duration_frames": 2},
            "vintage_color": {
                "sepia_amount": 0.4,
                "contrast_boost": 0.2,
                "duration_frames": 6,
            },
            "visibility": {"fade_duration": 5},
        }

        animation = {"type": animation_type, "trigger": trigger}

        # Add default parameters for this animation type
        if animation_type in defaults:
            animation.update(defaults[animation_type])

        return animation
