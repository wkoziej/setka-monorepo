# ABOUTME: Keyframe insertion and cleanup helper for Blender addon animation system
# ABOUTME: Provides unified interface for keyframes operations on video strips

"""Keyframe helper for addon animations."""

import traceback

try:
    import bpy
except ImportError:
    # For testing outside Blender
    bpy = None


class KeyframeHelper:
    """Helper class for inserting keyframes into Blender strips."""

    def insert_transform_position_keyframes(
        self, strip, frame: int, offset_x: float, offset_y: float
    ):
        """Insert position keyframes for strip transform.

        Args:
            strip: Blender video strip object
            frame: Frame number for keyframe
            offset_x: X offset value
            offset_y: Y offset value
        """
        if not hasattr(strip, "transform"):
            return

        # Set current values
        strip.transform.offset_x = offset_x
        strip.transform.offset_y = offset_y

        # Insert keyframes
        strip.transform.keyframe_insert(data_path="offset_x", frame=frame)
        strip.transform.keyframe_insert(data_path="offset_y", frame=frame)

    def insert_transform_scale_keyframes(
        self, strip, frame: int, scale_x: float, scale_y: float
    ):
        """Insert scale keyframes for strip transform.

        Args:
            strip: Blender video strip object
            frame: Frame number for keyframe
            scale_x: X scale value
            scale_y: Y scale value
        """
        if not hasattr(strip, "transform"):
            return

        # Set current values
        strip.transform.scale_x = scale_x
        strip.transform.scale_y = scale_y

        # Insert keyframes
        strip.transform.keyframe_insert(data_path="scale_x", frame=frame)
        strip.transform.keyframe_insert(data_path="scale_y", frame=frame)

    def insert_transform_rotation_keyframe(self, strip, frame: int, rotation: float):
        """Insert rotation keyframe for strip transform.

        Args:
            strip: Blender video strip object
            frame: Frame number for keyframe
            rotation: Rotation value in radians
        """
        if not hasattr(strip, "transform"):
            return

        # Set current value
        strip.transform.rotation = rotation

        # Insert keyframe
        strip.transform.keyframe_insert(data_path="rotation", frame=frame)

    def insert_blend_alpha_keyframe(self, strip, frame: int, alpha: float):
        """Insert blend alpha keyframe for strip.

        Args:
            strip: Blender video strip object
            frame: Frame number for keyframe
            alpha: Alpha value (0.0 to 1.0)
        """
        if not hasattr(strip, "blend_alpha"):
            return

        # Set current value
        strip.blend_alpha = alpha

        # Insert keyframe
        strip.keyframe_insert(data_path="blend_alpha", frame=frame)


class KeyframeCleaner:
    """Helper class for cleaning keyframes from Blender strips."""

    def clear_strip_fcurves(self, strip) -> list:
        """Clear all fcurves from strip and transform animation data.

        Args:
            strip: Blender video strip object

        Returns:
            List of cleared items for logging
        """
        cleared_items = []

        try:
            # Clear strip fcurves (including transform fcurves which are stored here in Blender 4.3+)
            if hasattr(strip, "animation_data") and strip.animation_data:
                if strip.animation_data.action:
                    fcurves_to_remove = []
                    transform_fcurves_removed = 0
                    other_fcurves_removed = 0

                    # Collect all fcurves to remove
                    for fcurve in strip.animation_data.action.fcurves:
                        fcurves_to_remove.append(fcurve)
                        # Check if it's a transform fcurve
                        if fcurve.data_path.startswith("transform."):
                            transform_fcurves_removed += 1
                        else:
                            other_fcurves_removed += 1

                    # Remove all fcurves
                    for fcurve in fcurves_to_remove:
                        strip.animation_data.action.fcurves.remove(fcurve)

                    if transform_fcurves_removed > 0:
                        cleared_items.append(
                            f"{transform_fcurves_removed} transform fcurves"
                        )
                    if other_fcurves_removed > 0:
                        cleared_items.append(f"{other_fcurves_removed} strip fcurves")

                # Clear the entire animation data
                strip.animation_data_clear()
                cleared_items.append("animation data cleared")

        except Exception as e:
            print(f"Error clearing fcurves for strip '{strip.name}': {e}")
            traceback.print_exc()

        return cleared_items

    def clear_strip_properties(self, strip) -> list:
        """Clear keyframes from individual strip properties.

        Args:
            strip: Blender video strip object

        Returns:
            List of cleared items for logging
        """
        cleared_items = []

        # Strip properties that might have keyframes
        clearable_properties = [
            "blend_alpha",
            "volume",
            "pitch",
            "pan",
            "use_translation",
            "use_crop",
            "use_mirror",
        ]

        for prop_name in clearable_properties:
            if hasattr(strip, prop_name):
                try:
                    strip.keyframe_delete(data_path=prop_name)
                    cleared_items.append(f"property '{prop_name}' keyframes")
                except (AttributeError, RuntimeError):
                    # Property doesn't support keyframes or no keyframes exist
                    pass

        # Transform properties are handled in clear_strip_fcurves since they're stored
        # in the strip's animation_data with data_path like "transform.scale_x"
        # No need to handle them separately here

        return cleared_items

    def clear_strip_modifiers(self, strip) -> list:
        """Clear Cinemon-created modifiers with their keyframes.

        Args:
            strip: Blender video strip object

        Returns:
            List of cleared items for logging
        """
        cleared_items = []

        cinemon_modifier_names = [
            "Brightness Flicker",
            "Color Effect",
            "Desaturate Pulse",
            "Contrast Flash",
        ]

        modifiers_to_remove = []
        for modifier in strip.modifiers:
            if modifier.name in cinemon_modifier_names:
                modifiers_to_remove.append(modifier)

        for modifier in modifiers_to_remove:
            modifier_name = modifier.name

            # Clear modifier animation data if it exists
            if hasattr(modifier, "animation_data") and modifier.animation_data:
                if modifier.animation_data.action:
                    fcurves_to_remove = list(modifier.animation_data.action.fcurves)
                    for fcurve in fcurves_to_remove:
                        modifier.animation_data.action.fcurves.remove(fcurve)
                modifier.animation_data_clear()
                cleared_items.append(f"modifier '{modifier_name}' keyframes")

            strip.modifiers.remove(modifier)
            cleared_items.append(f"modifier '{modifier_name}'")

        return cleared_items

    def refresh_timeline(self) -> list:
        """Force Blender to refresh the timeline display.

        Returns:
            List of refresh actions for logging
        """
        cleared_items = []

        try:
            if bpy and hasattr(bpy, "context") and hasattr(bpy.context, "scene"):
                bpy.context.scene.frame_set(bpy.context.scene.frame_current)
                cleared_items.append("timeline refresh")
        except Exception as e:
            print(f"Error refreshing timeline: {e}")

        return cleared_items

    def clear_all_strip_animations(self, strip) -> None:
        """Clear ALL animation keyframes for a strip - comprehensive cleanup.

        Args:
            strip: Blender video strip object
        """
        try:
            all_cleared_items = []

            # Use specialized methods
            all_cleared_items.extend(self.clear_strip_fcurves(strip))
            all_cleared_items.extend(self.clear_strip_properties(strip))
            all_cleared_items.extend(self.clear_strip_modifiers(strip))
            all_cleared_items.extend(self.refresh_timeline())

            if all_cleared_items:
                print(
                    f"Cleared for strip '{strip.name}': {', '.join(all_cleared_items)}"
                )
            else:
                print(f"No animations to clear for strip '{strip.name}'")

        except Exception as e:
            print(f"Error clearing animations for strip '{strip.name}': {e}")
            traceback.print_exc()


# Global instances for easy access
keyframe_helper = KeyframeHelper()
keyframe_cleaner = KeyframeCleaner()
