# ABOUTME: BrightnessFlickerAnimation implementation - creates brightness flicker effect
# ABOUTME: Refactored from VintageFilmEffects with event-based flickering for vintage film look

"""Brightness flicker animation for VSE strips."""

import random
from typing import List, Optional

from .base_effect_animation import BaseEffectAnimation


class BrightnessFlickerAnimation(BaseEffectAnimation):
    """
    Animation that creates brightness flicker effect on strips.
    
    Refactored from VintageFilmEffects.apply_brightness_flicker with enhanced options.
    
    Attributes:
        trigger: Event type to react to ("beat", "bass", "energy_peaks")
        intensity: Flicker intensity (0.0 to 1.0, how much dimmer)
        return_frames: How many frames until return to normal brightness
    """

    def __init__(self,
                 trigger: str = "beat",
                 intensity: float = 0.15,
                 return_frames: int = 1,
                 target_strips: Optional[List[str]] = None):
        """
        Initialize BrightnessFlickerAnimation.
        
        Args:
            trigger: Event type to trigger animation
            intensity: Maximum brightness reduction (0.0 to 1.0)
            return_frames: Frames until brightness returns to normal
            target_strips: List of strip names to target (None = all strips)
        """
        super().__init__(target_strips=target_strips)
        self.trigger = trigger
        self.intensity = intensity
        self.return_frames = return_frames

    def apply_to_strip(self, strip, events: List[float], fps: int, **kwargs) -> bool:
        """
        Apply brightness flicker animation to strip based on events.
        
        Args:
            strip: Blender video strip object
            events: List of event times in seconds
            fps: Frames per second
            **kwargs: Additional parameters (unused)
            
        Returns:
            True if animation was applied successfully
        """
        # Set initial brightness keyframe
        strip.blend_alpha = 1.0
        self.keyframe_helper.insert_blend_alpha_keyframe(strip.name, 1, 1.0)

        # Apply flicker for each event
        for event_time in events:
            frame = int(event_time * fps)

            # Random flicker (dimmer)
            flicker_alpha = 1.0 - random.uniform(0, self.intensity)

            # Apply flicker at event frame
            strip.blend_alpha = flicker_alpha
            self.keyframe_helper.insert_blend_alpha_keyframe(
                strip.name, frame, flicker_alpha
            )

            # Return to normal brightness
            return_frame = frame + self.return_frames
            strip.blend_alpha = 1.0
            self.keyframe_helper.insert_blend_alpha_keyframe(
                strip.name, return_frame, 1.0
            )

        return True

    def get_required_properties(self) -> List[str]:
        """
        Get list of required strip properties.
        
        Returns:
            List containing 'blend_alpha' property requirement
        """
        return ['blend_alpha']
