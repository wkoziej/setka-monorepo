"""
ABOUTME: Keyframe helper module for Blender VSE - eliminates code duplication in keyframe insertion.
ABOUTME: Provides centralized utilities for common keyframe patterns used in animations.
"""

import bpy
from typing import Union


class KeyframeHelper:
    """Helper class for Blender VSE keyframe insertion operations."""

    def __init__(self):
        """Initialize keyframe helper."""
        pass

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
            # Extract strip name and alpha value
            if isinstance(strip, str):
                strip_name = strip
                if alpha_value is None:
                    alpha_value = 1.0  # Default alpha
            else:
                strip_name = strip.name
                if alpha_value is None:
                    alpha_value = strip.blend_alpha

            # Build data path and insert keyframe
            data_path = self.build_data_path(strip_name, "blend_alpha")
            bpy.context.scene.keyframe_insert(data_path=data_path, frame=frame)
            return True

        except Exception:
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
            # Extract strip name and scale values
            if isinstance(strip, str):
                strip_name = strip
                if scale_x is None:
                    scale_x = 1.0  # Default scale
                if scale_y is None:
                    scale_y = scale_x  # Uniform scaling
            else:
                strip_name = strip.name
                if scale_x is None:
                    scale_x = strip.transform.scale_x
                if scale_y is None:
                    scale_y = (
                        scale_x if scale_x is not None else strip.transform.scale_y
                    )

            # Build data paths and insert keyframes
            data_path_x = self.build_data_path(strip_name, "transform.scale_x")
            data_path_y = self.build_data_path(strip_name, "transform.scale_y")

            bpy.context.scene.keyframe_insert(data_path=data_path_x, frame=frame)
            bpy.context.scene.keyframe_insert(data_path=data_path_y, frame=frame)
            return True

        except Exception:
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
            # Extract strip name and offset values
            if isinstance(strip, str):
                strip_name = strip
                if offset_x is None:
                    offset_x = 0  # Default offset
                if offset_y is None:
                    offset_y = 0  # Default offset
            else:
                strip_name = strip.name
                if offset_x is None:
                    offset_x = strip.transform.offset_x
                if offset_y is None:
                    offset_y = strip.transform.offset_y

            # Build data paths and insert keyframes
            data_path_x = self.build_data_path(strip_name, "transform.offset_x")
            data_path_y = self.build_data_path(strip_name, "transform.offset_y")

            bpy.context.scene.keyframe_insert(data_path=data_path_x, frame=frame)
            bpy.context.scene.keyframe_insert(data_path=data_path_y, frame=frame)
            return True

        except Exception:
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
            bool: True if keyframe inserted successfully
        """
        try:
            # Extract strip name and rotation value
            if isinstance(strip, str):
                strip_name = strip
                if rotation is None:
                    rotation = 0.0  # Default rotation
            else:
                strip_name = strip.name
                if rotation is None:
                    rotation = strip.transform.rotation

            # Build data path and insert keyframe
            data_path = self.build_data_path(strip_name, "transform.rotation")
            bpy.context.scene.keyframe_insert(data_path=data_path, frame=frame)
            return True

        except Exception:
            return False
