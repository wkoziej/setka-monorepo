# ABOUTME: ShakeAnimation implementation - creates camera shake effect by animating strip position
# ABOUTME: Refactored from VintageFilmEffects with support for random and deterministic shaking

"""Shake animation for VSE strips."""

import random
from typing import List

from .base_effect_animation import BaseEffectAnimation


class ShakeAnimation(BaseEffectAnimation):
    """
    Animation that creates shaking/vibration effect on strips.
    
    Refactored from VintageFilmEffects.apply_camera_shake with enhanced options.
    
    Attributes:
        trigger: Event type to react to ("beat", "bass", "energy_peaks")
        intensity: Shake intensity in pixels
        return_frames: How many frames until return to base position
        random_direction: Whether shake direction is random or deterministic
    """
    
    def __init__(self,
                 trigger: str = "beat",
                 intensity: float = 10.0,
                 return_frames: int = 2,
                 random_direction: bool = True):
        """
        Initialize ShakeAnimation.
        
        Args:
            trigger: Event type to trigger animation
            intensity: Maximum shake offset in pixels
            return_frames: Frames until position returns to normal
            random_direction: If True, shake randomly; if False, shake horizontally only
        """
        super().__init__()
        self.trigger = trigger
        self.intensity = intensity
        self.return_frames = return_frames
        self.random_direction = random_direction
    
    def apply_to_strip(self, strip, events: List[float], fps: int, **kwargs) -> bool:
        """
        Apply shake animation to strip based on events.
        
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
        
        # Get base position
        base_x = strip.transform.offset_x
        base_y = strip.transform.offset_y
        
        # Set initial keyframe at frame 1
        self.keyframe_helper.insert_transform_position_keyframes(strip.name, 1)
        
        # Apply shake for each event
        for event_time in events:
            frame = int(event_time * fps)
            
            # Calculate shake offset
            if self.random_direction:
                shake_x = random.uniform(-self.intensity, self.intensity)
                shake_y = random.uniform(-self.intensity, self.intensity)
            else:
                # Deterministic shake (horizontal only)
                shake_x = self.intensity
                shake_y = 0
            
            # Apply shake
            strip.transform.offset_x = base_x + shake_x
            strip.transform.offset_y = base_y + shake_y
            self.keyframe_helper.insert_transform_position_keyframes(strip.name, frame)
            
            # Return to base position
            return_frame = frame + self.return_frames
            strip.transform.offset_x = base_x
            strip.transform.offset_y = base_y
            self.keyframe_helper.insert_transform_position_keyframes(
                strip.name, return_frame
            )
        
        return True
    
    def get_required_properties(self) -> List[str]:
        """
        Get list of required strip properties.
        
        Returns:
            List containing 'transform' property requirement
        """
        return ['transform']