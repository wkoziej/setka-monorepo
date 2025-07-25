"""
ABOUTME: Keyframe helper module for Blender VSE - eliminates code duplication in keyframe insertion.
ABOUTME: Provides centralized utilities for common keyframe patterns used in animations.
"""

from typing import Union

try:
    import bpy
except ImportError:
    # Running outside Blender - provide mock for testing
    bpy = None


class KeyframeHelper:
    """Helper class for Blender VSE keyframe insertion operations."""

    def __init__(self):
        """Initialize keyframe helper."""
        pass

    def _get_strip_object(self, strip: Union[str, object]) -> tuple:
        """
        Get strip object from either a string name or strip object.

        Args:
            strip: Strip name (str) or strip object

        Returns:
            tuple: (strip_object, strip_name) or (None, None) if not found
        """
        if isinstance(strip, str):
            strip_name = strip
            if bpy and bpy.context.scene.sequence_editor:
                strip_obj = bpy.context.scene.sequence_editor.sequences_all.get(strip_name)
                if not strip_obj:
                    print(f"Strip '{strip_name}' not found in sequence editor")
                    return None, None
                return strip_obj, strip_name
            else:
                return None, None
        else:
            return strip, strip.name

    def insert_blend_alpha_keyframe(
        self, strip: Union[str, object], frame: int, alpha_value: float = None
    ) -> bool:
        """
        Insert blend_alpha keyframe for a strip.

        Args:
            strip: Strip name (str) or strip object with .name attribute
            frame: Frame number for keyframe
            alpha_value: Alpha value (0.0-1.0). If None, uses strip's current value

        Returns:
            bool: True if keyframe inserted successfully
        """
        try:
            strip_obj, strip_name = self._get_strip_object(strip)
            if not strip_obj:
                return False

            # Set alpha value
            if alpha_value is None:
                alpha_value = strip_obj.blend_alpha if hasattr(strip_obj, 'blend_alpha') else 1.0

            # Use direct method - blend_alpha is a direct property of the strip
            strip_obj.blend_alpha = alpha_value
            strip_obj.keyframe_insert(data_path="blend_alpha", frame=frame)
            return True

        except Exception as e:
            print(f"Error inserting blend_alpha keyframe: {e}")
            import traceback
            traceback.print_exc()
            return False

    def insert_transform_scale_keyframes(
        self,
        strip: Union[str, object],
        frame: int,
        scale_x: float = None,
        scale_y: float = None,
    ) -> bool:
        """
        Insert transform.scale_x and transform.scale_y keyframes for a strip.

        Args:
            strip: Strip name (str) or strip object with .name attribute
            frame: Frame number for keyframe
            scale_x: Scale X value. If None, uses strip's current value
            scale_y: Scale Y value. If None, uses scale_x or strip's current value

        Returns:
            bool: True if keyframes inserted successfully
        """
        try:
            strip_obj, strip_name = self._get_strip_object(strip)
            if not strip_obj:
                return False

            if not hasattr(strip_obj, 'transform'):
                print(f"Strip '{strip_name}' has no transform property")
                return False

            # Set scale values
            if scale_x is None:
                scale_x = strip_obj.transform.scale_x if hasattr(strip_obj.transform, 'scale_x') else 1.0
            if scale_y is None:
                scale_y = scale_x  # Uniform scaling by default

            # Use direct method like addon system
            strip_obj.transform.scale_x = scale_x
            strip_obj.transform.scale_y = scale_y
            strip_obj.transform.keyframe_insert(data_path="scale_x", frame=frame)
            strip_obj.transform.keyframe_insert(data_path="scale_y", frame=frame)
            return True

        except Exception as e:
            print(f"Error inserting scale keyframes: {e}")
            import traceback
            traceback.print_exc()
            return False

    def insert_transform_offset_keyframes(
        self,
        strip: Union[str, object],
        frame: int,
        offset_x: int = None,
        offset_y: int = None,
    ) -> bool:
        """
        Insert transform.offset_x and transform.offset_y keyframes for a strip.

        Args:
            strip: Strip name (str) or strip object with .name attribute
            frame: Frame number for keyframe
            offset_x: Offset X value. If None, uses strip's current value
            offset_y: Offset Y value. If None, uses strip's current value

        Returns:
            bool: True if keyframes inserted successfully
        """
        try:
            strip_obj, strip_name = self._get_strip_object(strip)
            if not strip_obj:
                return False

            if not hasattr(strip_obj, 'transform'):
                print(f"Strip '{strip_name}' has no transform property")
                return False

            # Set offset values
            if offset_x is None:
                offset_x = strip_obj.transform.offset_x if hasattr(strip_obj.transform, 'offset_x') else 0
            if offset_y is None:
                offset_y = strip_obj.transform.offset_y if hasattr(strip_obj.transform, 'offset_y') else 0

            # Use direct method like addon system
            strip_obj.transform.offset_x = offset_x
            strip_obj.transform.offset_y = offset_y
            strip_obj.transform.keyframe_insert(data_path="offset_x", frame=frame)
            strip_obj.transform.keyframe_insert(data_path="offset_y", frame=frame)
            return True

        except Exception as e:
            print(f"Error inserting offset keyframes: {e}")
            import traceback
            traceback.print_exc()
            return False

    def build_data_path(self, strip_name: str, property_path: str) -> str:
        """
        Build Blender data path for keyframe insertion.

        Args:
            strip_name: Name of the strip
            property_path: Property path (e.g., "blend_alpha", "transform.scale_x")

        Returns:
            str: Complete data path for bpy.context.scene.keyframe_insert()

        Raises:
            ValueError: If strip_name is empty or None
        """
        if not strip_name:
            raise ValueError("Strip name cannot be empty or None")

        return f'sequence_editor.sequences_all["{strip_name}"].{property_path}'

    def insert_transform_position_keyframes(
        self,
        strip: Union[str, object],
        frame: int,
        offset_x: int = None,
        offset_y: int = None,
    ) -> bool:
        """
        Insert transform position keyframes (alias for insert_transform_offset_keyframes).

        Args:
            strip: Strip name (str) or strip object with .name attribute
            frame: Frame number for keyframe
            offset_x: Offset X value. If None, uses strip's current value
            offset_y: Offset Y value. If None, uses strip's current value

        Returns:
            bool: True if keyframes inserted successfully
        """
        return self.insert_transform_offset_keyframes(strip, frame, offset_x, offset_y)

    def insert_transform_rotation_keyframe(
        self, strip: Union[str, object], frame: int, rotation: float = None
    ) -> bool:
        """
        Insert transform.rotation keyframe for a strip.

        Args:
            strip: Strip name (str) or strip object with .name attribute
            frame: Frame number for keyframe
            rotation: Rotation value in radians. If None, uses strip's current value

        Returns:
            bool: True if keyframes inserted successfully
        """
        try:
            strip_obj, strip_name = self._get_strip_object(strip)
            if not strip_obj:
                return False

            if not hasattr(strip_obj, 'transform'):
                print(f"Strip '{strip_name}' has no transform property")
                return False

            # Set rotation value
            if rotation is None:
                rotation = strip_obj.transform.rotation if hasattr(strip_obj.transform, 'rotation') else 0.0

            # Use direct method like addon system
            strip_obj.transform.rotation = rotation
            strip_obj.transform.keyframe_insert(data_path="rotation", frame=frame)
            return True

        except Exception as e:
            print(f"Error inserting rotation keyframe: {e}")
            import traceback
            traceback.print_exc()
            return False
