# ABOUTME: Manages context-aware strip animations based on active VSE strip selection
# ABOUTME: Provides API for adding/removing/updating animations for specific strips

"""Strip context management for Cinemon addon."""

import copy
from typing import Any, Dict, List, Optional


class StripContextManager:
    """Manages animations and layout context for VSE project."""

    def __init__(self):
        """Initialize strip context manager."""
        self.config = {}
        self.changes_buffer = {}  # Stores pending animation changes
        self.layout_changes = {}  # Stores pending layout changes

        # Available animation types and their default parameters
        self.animation_types = {
            "scale": {"intensity": 0.3, "duration_frames": 3},
            "shake": {"intensity": 2.0, "return_frames": 2},
            "rotation": {"degrees": 5.0, "duration_frames": 3},
            "jitter": {"intensity": 1.0},
            "brightness_flicker": {"intensity": 0.1, "duration_frames": 2},
            "visibility": {"fade_duration": 5},
            "desaturate_pulse": {"intensity": 0.8, "duration_frames": 3},
            "contrast_flash": {"intensity": 0.5, "duration_frames": 2},
        }

        self.triggers = ["beat", "bass", "energy_peaks", "one_time", "continuous"]

    def load_config(self, config: Dict[str, Any]) -> None:
        """Load configuration from YAML data."""
        self.config = copy.deepcopy(config)
        self.changes_buffer = {}

        # Ensure strip_animations exists
        if "strip_animations" not in self.config:
            self.config["strip_animations"] = {}

    def load_preset_for_apply(self, config: Dict[str, Any]) -> None:
        """Load preset configuration and mark all changes for Apply."""
        self.config = copy.deepcopy(config)

        # Mark all strip animations as changed
        if "strip_animations" in config:
            self.changes_buffer = copy.deepcopy(config["strip_animations"])
        else:
            self.changes_buffer = {}

        # Mark layout as changed
        if "layout" in config:
            self.layout_changes = copy.deepcopy(config["layout"])
        else:
            self.layout_changes = {}

    def get_active_strip_name(self) -> Optional[str]:
        """Get name of currently active strip in VSE."""
        try:
            import bpy

            if (
                bpy.context.scene.sequence_editor
                and bpy.context.scene.sequence_editor.active_strip
            ):
                return bpy.context.scene.sequence_editor.active_strip.name
        except (ImportError, AttributeError):
            # For testing or when bpy not available
            pass
        return None

    def get_active_strip_animations(self) -> List[Dict[str, Any]]:
        """Get animations for currently active strip."""
        # Try to load config from scene if not loaded yet
        self._ensure_config_loaded()

        active_strip = self.get_active_strip_name()
        if not active_strip:
            return []

        # Check changes buffer first, then original config
        if active_strip in self.changes_buffer:
            return copy.deepcopy(self.changes_buffer[active_strip])

        strip_animations = self.config.get("strip_animations", {})
        result = copy.deepcopy(strip_animations.get(active_strip, []))
        return result

    def _ensure_config_loaded(self) -> None:
        """Ensure config is loaded from scene properties if available."""
        # If we already have config with animations, don't reload
        strip_animations = self.config.get("strip_animations", {})
        if strip_animations and any(
            len(anims) > 0 for anims in strip_animations.values()
        ):
            return

        try:
            import bpy

            scene = bpy.context.scene

            # Try to load strip_animations from scene properties
            if "cinemon_strip_animations" in scene:
                strip_animations_str = scene["cinemon_strip_animations"]
                if strip_animations_str:
                    # Parse string back to dict
                    import ast

                    try:
                        strip_animations = ast.literal_eval(strip_animations_str)
                        if isinstance(strip_animations, dict):
                            # Initialize config if empty
                            if not self.config:
                                self.config = {}
                            self.config["strip_animations"] = strip_animations
                            print(
                                f"✓ Loaded {len(strip_animations)} strips from scene properties"
                            )
                        else:
                            print("⚠ Strip animations from scene is not a dict")
                    except (ValueError, SyntaxError) as e:
                        print(f"⚠ Failed to parse strip animations from scene: {e}")

        except (ImportError, AttributeError):
            # For testing or when bpy not available
            pass

    def add_animation_to_active_strip(self, animation: Dict[str, Any]) -> bool:
        """Add animation to currently active strip."""
        active_strip = self.get_active_strip_name()
        if not active_strip:
            return False

        # Get current animations (from buffer or config)
        current_animations = self.get_active_strip_animations()
        current_animations.append(animation)

        # Store in changes buffer
        self.changes_buffer[active_strip] = current_animations
        return True

    def remove_animation_from_active_strip(self, animation_index: int) -> bool:
        """Remove animation from currently active strip by index."""
        active_strip = self.get_active_strip_name()
        if not active_strip:
            return False

        current_animations = self.get_active_strip_animations()
        if 0 <= animation_index < len(current_animations):
            current_animations.pop(animation_index)
            self.changes_buffer[active_strip] = current_animations
            return True
        return False

    def update_animation_parameter(
        self, animation_index: int, param_name: str, value: Any
    ) -> bool:
        """Update parameter of animation for active strip."""
        active_strip = self.get_active_strip_name()
        if not active_strip:
            return False

        current_animations = self.get_active_strip_animations()
        if 0 <= animation_index < len(current_animations):
            current_animations[animation_index][param_name] = value
            self.changes_buffer[active_strip] = current_animations
            return True
        return False

    def get_available_animation_types(self) -> List[str]:
        """Get list of available animation types."""
        return list(self.animation_types.keys())

    def get_available_triggers(self) -> List[str]:
        """Get list of available animation triggers."""
        return self.triggers.copy()

    def get_default_animation_parameters(self, animation_type: str) -> Dict[str, Any]:
        """Get default parameters for animation type."""
        return self.animation_types.get(animation_type, {}).copy()

    def create_default_animation(
        self, animation_type: str, trigger: str
    ) -> Dict[str, Any]:
        """Create animation with default parameters."""
        animation = {"type": animation_type, "trigger": trigger}
        # Add default parameters
        defaults = self.get_default_animation_parameters(animation_type)
        animation.update(defaults)
        return animation

    def has_pending_changes(self) -> bool:
        """Check if there are pending changes in any buffer."""
        return len(self.changes_buffer) > 0 or len(self.layout_changes) > 0

    def get_changed_strips(self) -> List[str]:
        """Get list of strips with pending changes."""
        return list(self.changes_buffer.keys())

    def apply_changes(self) -> Dict[str, Any]:
        """Apply all buffered changes to main config and return updated config."""
        # Apply animation changes
        if "strip_animations" not in self.config:
            self.config["strip_animations"] = {}

        for strip_name, animations in self.changes_buffer.items():
            self.config["strip_animations"][strip_name] = animations

        # Apply layout changes
        if self.layout_changes:
            self.config["layout"] = copy.deepcopy(self.layout_changes)

        # Clear all buffers
        self.changes_buffer = {}
        self.layout_changes = {}

        return copy.deepcopy(self.config)

    def update_layout_parameter(self, param_path: str, value: Any) -> None:
        """Update layout parameter in changes buffer.

        Args:
            param_path: Dot-separated path like 'type' or 'config.margin'
            value: New value for the parameter
        """
        # Initialize layout changes if needed
        if not self.layout_changes:
            self.layout_changes = copy.deepcopy(self.config.get("layout", {}))

        # Handle nested paths
        path_parts = param_path.split(".")
        current = self.layout_changes

        # Navigate to the parent of the target
        for part in path_parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        # Set the value
        if path_parts:
            current[path_parts[-1]] = value

    def get_pending_layout(self) -> Optional[Dict[str, Any]]:
        """Get pending layout configuration."""
        if self.layout_changes:
            return copy.deepcopy(self.layout_changes)
        return None

    def discard_changes(self) -> None:
        """Discard all pending changes."""
        self.changes_buffer = {}
        self.layout_changes = {}

    def get_current_config(self) -> Dict[str, Any]:
        """Get current config with pending changes applied temporarily."""
        config_copy = copy.deepcopy(self.config)

        if "strip_animations" not in config_copy:
            config_copy["strip_animations"] = {}

        # Apply buffer changes temporarily
        for strip_name, animations in self.changes_buffer.items():
            config_copy["strip_animations"][strip_name] = animations

        return config_copy


# Global instance for addon
_strip_context_manager = None


def get_strip_context_manager() -> StripContextManager:
    """Get global strip context manager instance."""
    global _strip_context_manager
    if _strip_context_manager is None:
        _strip_context_manager = StripContextManager()
    return _strip_context_manager
