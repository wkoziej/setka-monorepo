# ABOUTME: Keyframe insertion helper for Blender addon animation system
# ABOUTME: Provides unified interface for inserting transform keyframes on video strips

"""Keyframe helper for addon animations."""

try:
    import bpy
except ImportError:
    # For testing outside Blender
    bpy = None


class KeyframeHelper:
    """Helper class for inserting keyframes into Blender strips."""
    
    def insert_transform_position_keyframes(self, strip, frame: int, offset_x: float, offset_y: float):
        """Insert position keyframes for strip transform.
        
        Args:
            strip: Blender video strip object
            frame: Frame number for keyframe
            offset_x: X offset value
            offset_y: Y offset value
        """
        if not hasattr(strip, 'transform'):
            return
            
        # Set current values
        strip.transform.offset_x = offset_x
        strip.transform.offset_y = offset_y
        
        # Insert keyframes
        strip.transform.keyframe_insert(data_path="offset_x", frame=frame)
        strip.transform.keyframe_insert(data_path="offset_y", frame=frame)
    
    def insert_transform_scale_keyframes(self, strip, frame: int, scale_x: float, scale_y: float):
        """Insert scale keyframes for strip transform.
        
        Args:
            strip: Blender video strip object
            frame: Frame number for keyframe
            scale_x: X scale value
            scale_y: Y scale value
        """
        if not hasattr(strip, 'transform'):
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
        if not hasattr(strip, 'transform'):
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
        if not hasattr(strip, 'blend_alpha'):
            return
            
        # Set current value
        strip.blend_alpha = alpha
        
        # Insert keyframe
        strip.keyframe_insert(data_path="blend_alpha", frame=frame)