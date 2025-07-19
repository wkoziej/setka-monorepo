# ABOUTME: ScaleAnimation implementation - animates strip scale based on audio events
# ABOUTME: Supports customizable intensity, duration, and easing for smooth scale transitions

"""Scale animation for VSE strips."""

from typing import List, Optional

from .base_effect_animation import BaseEffectAnimation


class ScaleAnimation(BaseEffectAnimation):
    """
    Animation that scales strips based on audio events.
    
    Attributes:
        trigger: Event type to react to ("bass", "beat", "energy_peaks")
        intensity: Scale increase factor (0.3 = 30% larger)
        duration_frames: How many frames the scale effect lasts
        easing: Easing type (currently only "linear" supported)
    """
    
    def __init__(self, 
                 trigger: str = "bass",
                 intensity: float = 0.3,
                 duration_frames: int = 2,
                 easing: str = "linear",
                 target_strips: Optional[List[str]] = None):
        """
        Initialize ScaleAnimation.
        
        Args:
            trigger: Event type to trigger animation
            intensity: How much to scale up (0.1 = 10% increase)
            duration_frames: Duration of scale effect in frames
            easing: Type of easing (future feature)
            target_strips: List of strip names to target (None = all strips)
        """
        super().__init__(target_strips=target_strips)
        self.trigger = trigger
        self.intensity = intensity
        self.duration_frames = duration_frames
        self.easing = easing
    
    def apply_to_strip(self, strip, events: List[float], fps: int, **kwargs) -> bool:
        """
        Apply scale animation to strip based on events.
        
        Args:
            strip: Blender video strip object
            events: List of event times in seconds
            fps: Frames per second
            **kwargs: Additional parameters (unused)
            
        Returns:
            True if animation was applied successfully
        """
        if not hasattr(strip, 'transform'):
            return False
        
        # Get base scale
        base_scale_x = strip.transform.scale_x
        base_scale_y = strip.transform.scale_y
        
        # Set initial keyframe at frame 1
        self.keyframe_helper.insert_transform_scale_keyframes(
            strip.name, 1, base_scale_x, base_scale_y
        )
        
        # Apply scale animation for each event
        for event_time in events:
            frame = int(event_time * fps)
            
            # Scale up by intensity factor
            scale_factor = 1.0 + self.intensity
            new_scale_x = base_scale_x * scale_factor
            new_scale_y = base_scale_y * scale_factor
            
            strip.transform.scale_x = new_scale_x
            strip.transform.scale_y = new_scale_y
            self.keyframe_helper.insert_transform_scale_keyframes(
                strip.name, frame, new_scale_x, new_scale_y
            )
            
            # Return to base scale after duration_frames
            return_frame = frame + self.duration_frames
            strip.transform.scale_x = base_scale_x
            strip.transform.scale_y = base_scale_y
            self.keyframe_helper.insert_transform_scale_keyframes(
                strip.name, return_frame, base_scale_x, base_scale_y
            )
        
        return True
    
    def get_required_properties(self) -> List[str]:
        """
        Get list of required strip properties.
        
        Returns:
            List containing 'transform' property requirement
        """
        return ['transform']