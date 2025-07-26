# ABOUTME: JitterAnimation implementation - creates continuous film jitter effect
# ABOUTME: Refactored from VintageFilmEffects with irregular timing patterns like old film

"""Jitter animation for VSE strips."""

import random
from typing import List

from .base_effect_animation import BaseEffectAnimation


class JitterAnimation(BaseEffectAnimation):
    """
    Animation that creates continuous film jitter effect on strips.
    
    Refactored from VintageFilmEffects.apply_film_jitter with enhanced options.
    
    This animation doesn't use events but applies continuous jitter throughout
    the strip duration, simulating old film projection irregularities.
    
    Attributes:
        trigger: Event type (ignored for continuous effect)
        intensity: Jitter intensity in pixels
        min_interval: Minimum frames between jitter changes
        max_interval: Maximum frames between jitter changes
    """

    def __init__(self,
                 trigger: str = "continuous",
                 intensity: float = 2.0,
                 min_interval: int = 3,
                 max_interval: int = 8):
        """
        Initialize JitterAnimation.
        
        Args:
            trigger: Event type (ignored for continuous effect)
            intensity: Maximum jitter offset in pixels
            min_interval: Minimum frames between jitter changes
            max_interval: Maximum frames between jitter changes
        """
        super().__init__()
        self.trigger = trigger
        self.intensity = intensity
        self.min_interval = min_interval
        self.max_interval = max_interval

    def apply_to_strip(self, strip, events: List[float], fps: int, **kwargs) -> bool:
        """
        Apply continuous jitter animation to strip.
        
        Args:
            strip: Blender video strip object
            events: List of event times (ignored for continuous effect)
            fps: Frames per second
            **kwargs: Additional parameters, expects 'duration_frames'
            
        Returns:
            True if animation was applied successfully
        """
        if not hasattr(strip, 'transform'):
            return False

        # Get duration from kwargs or calculate from strip
        duration_frames = kwargs.get('duration_frames')
        if duration_frames is None:
            # Calculate duration from strip length
            duration_frames = int(strip.frame_final_duration)

        # Get base position
        base_x = strip.transform.offset_x
        base_y = strip.transform.offset_y

        # Apply jitter every min_interval-max_interval frames (irregular timing like old film)
        current_frame = 1
        while current_frame < duration_frames:
            # Random small offsets
            jitter_x = random.uniform(-self.intensity, self.intensity)
            jitter_y = random.uniform(-self.intensity, self.intensity)

            # Apply jitter
            strip.transform.offset_x = base_x + jitter_x
            strip.transform.offset_y = base_y + jitter_y
            self.keyframe_helper.insert_transform_position_keyframes(
                strip.name, current_frame
            )

            # Next jitter in random interval
            current_frame += random.randint(self.min_interval, self.max_interval)

        return True

    def get_required_properties(self) -> List[str]:
        """
        Get list of required strip properties.
        
        Returns:
            List containing 'transform' property requirement
        """
        return ['transform']
