# ABOUTME: ModifierAnimationMixin - helper mixin for animations using Blender modifiers
# ABOUTME: Provides utilities for creating and animating VSE strip modifiers

"""Mixin for animations that use Blender VSE modifiers."""

from typing import Any, Optional

try:
    import bpy
except ImportError:
    bpy = None


class ModifierAnimationMixin:
    """
    Mixin class providing utilities for animations that use Blender modifiers.

    Provides methods for:
    - Ensuring modifiers exist on strips
    - Animating modifier properties
    - Managing modifier keyframes
    """

    def ensure_modifier_exists(self, strip, modifier_name: str, modifier_type: str):
        """
        Ensure a modifier exists on a strip, creating it if necessary.

        Args:
            strip: Blender video strip object
            modifier_name: Name for the modifier
            modifier_type: Type of modifier (e.g., "COLOR_BALANCE", "GAUSSIAN_BLUR")

        Returns:
            The modifier object
        """
        # Check if modifier already exists
        modifier = None
        for mod in strip.modifiers:
            if mod.name == modifier_name:
                modifier = mod
                break

        # Create modifier if it doesn't exist
        if not modifier:
            modifier = strip.modifiers.new(name=modifier_name, type=modifier_type)

        return modifier

    def animate_modifier_property(
        self, strip, modifier, property_path: str, frame: int, value: Any
    ) -> bool:
        """
        Set and keyframe a modifier property.

        Args:
            strip: Blender strip object (for context)
            modifier: The modifier object
            property_path: Property path within modifier (e.g., "color_balance.gain")
            frame: Frame number for keyframe
            value: Value to set

        Returns:
            True if successful
        """
        try:
            # Navigate nested properties if needed
            parts = property_path.split(".")
            obj = modifier

            # Navigate to the parent of the final property
            for part in parts[:-1]:
                obj = getattr(obj, part)

            # Set the final property value
            setattr(obj, parts[-1], value)

            # Insert keyframe at scene level
            # Modifiers are animated through the scene, not the strip
            if bpy and hasattr(self, "keyframe_helper"):
                # Build full data path for scene keyframing
                strip_path = f'sequence_editor.sequences_all["{strip.name}"]'
                mod_path = f'{strip_path}.modifiers["{modifier.name}"].{property_path}'

                # Insert keyframe at scene level
                bpy.context.scene.keyframe_insert(data_path=mod_path, frame=frame)

            return True

        except Exception as e:
            print(f"Error animating modifier property {property_path}: {e}")
            return False

    def get_modifier_property_value(self, modifier, property_path: str) -> Any:
        """
        Get the current value of a modifier property.

        Args:
            modifier: The modifier object
            property_path: Property path within modifier

        Returns:
            The property value
        """
        parts = property_path.split(".")
        obj = modifier

        for part in parts:
            obj = getattr(obj, part)

        return obj

    def remove_modifier(self, strip, modifier_name: str) -> bool:
        """
        Remove a modifier from a strip if it exists.

        Args:
            strip: Blender video strip object
            modifier_name: Name of the modifier to remove

        Returns:
            True if modifier was removed, False if it didn't exist
        """
        for i, mod in enumerate(strip.modifiers):
            if mod.name == modifier_name:
                strip.modifiers.remove(mod)
                return True
        return False
