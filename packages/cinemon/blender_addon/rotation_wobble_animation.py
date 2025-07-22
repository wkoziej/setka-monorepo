# ABOUTME: RotationWobbleAnimation implementation - creates subtle rotation wobble effect
# ABOUTME: Refactored from VintageFilmEffects with oscillation support for natural movement

"""Rotation wobble animation for addon."""

import random
import math
from typing import List, Optional
import sys
from pathlib import Path

# Ensure addon path is available
addon_path = Path(__file__).parent
if str(addon_path) not in sys.path:
    sys.path.insert(0, str(addon_path))

try:
    from .base_effect_animation import BaseEffectAnimation
except ImportError:
    # Fallback for background mode
    try:
        import base_effect_animation
        BaseEffectAnimation = base_effect_animation.BaseEffectAnimation
    except ImportError:
        # If still failing, use a minimal base class
        class BaseEffectAnimation:
            def __init__(self, keyframe_helper=None, target_strips=None):
                self.target_strips = target_strips or []
            
            def should_apply_to_strip(self, strip):
                return not self.target_strips or strip.name in self.target_strips


class RotationWobbleAnimation(BaseEffectAnimation):
    """
    Animation that creates rotation wobble effect on strips.
    
    Refactored from VintageFilmEffects.apply_rotation_wobble with enhanced options.
    
    Attributes:
        trigger: Event type to react to ("beat", "bass", "energy_peaks")
        wobble_degrees: Maximum wobble angle in degrees
        return_frames: How many frames until return to base rotation
        oscillate: Whether to alternate wobble direction
    """
    
    def __init__(self,
                 trigger: str = "beat",
                 wobble_degrees: float = 1.0,
                 return_frames: int = 3,
                 oscillate: bool = True,
                 target_strips: Optional[List[str]] = None):
        """
        Initialize RotationWobbleAnimation.
        
        Args:
            trigger: Event type to trigger animation
            wobble_degrees: Maximum rotation in degrees
            return_frames: Frames until rotation returns to normal
            oscillate: If True, alternate wobble direction between events
            target_strips: List of strip names to target (None = all strips)
        """
        super().__init__(keyframe_helper=None, target_strips=target_strips)
        self.trigger = trigger
        self.wobble_degrees = wobble_degrees
        self.return_frames = return_frames
        self.oscillate = oscillate
    
    def apply_to_strip(self, strip, events: List[float], fps: int, **kwargs) -> bool:
        """
        Apply rotation wobble animation to strip based on events.
        
        Uses the same logic as VintageFilmEffects.apply_rotation_wobble with
        enhanced oscillation support.
        
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
        
        # Set initial rotation keyframe at frame 1
        self.keyframe_helper.insert_transform_rotation_keyframe(strip, 1, 0.0)
        
        # Track direction for oscillation
        direction = 1
        
        # Apply wobble for each event
        for i, event_time in enumerate(events):
            frame = int(event_time * fps)
            
            # Calculate wobble rotation - use VintageFilmEffects logic with oscillation
            if self.oscillate and i > 0:
                direction *= -1  # Alternate direction
                # Use VintageFilmEffects range but with direction
                wobble_rotation = random.uniform(-self.wobble_degrees, self.wobble_degrees) * direction
            else:
                # Original VintageFilmEffects logic: random in full range
                wobble_rotation = random.uniform(-self.wobble_degrees, self.wobble_degrees)
            
            wobble_radians = math.radians(wobble_rotation)
            
            # Apply wobble
            self.keyframe_helper.insert_transform_rotation_keyframe(
                strip, frame, wobble_radians
            )
            
            # Return to normal rotation (same as VintageFilmEffects: 3 frames)
            return_frame = frame + self.return_frames
            self.keyframe_helper.insert_transform_rotation_keyframe(
                strip, return_frame, 0.0
            )
        
        return True
    
    def get_required_properties(self) -> List[str]:
        """
        Get list of required strip properties.
        
        Returns:
            List containing 'transform' property requirement
        """
        return ['transform']