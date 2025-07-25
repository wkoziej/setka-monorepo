# ABOUTME: BrightnessFlickerAnimation implementation - creates brightness flicker effect
# ABOUTME: Refactored from VintageFilmEffects with event-based flickering for vintage film look

"""Brightness flicker animation for addon."""

import random
import sys
from pathlib import Path
from typing import List, Optional

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
                 intensity: float = 0.1,
                 duration_frames: int = 2,
                 return_frames: int = 1,
                 target_strips: Optional[List[str]] = None):
        """
        Initialize BrightnessFlickerAnimation.

        Args:
            trigger: Event type to trigger animation
            intensity: Flicker intensity (0.1 = 10% dimmer)
            duration_frames: Duration of flicker effect in frames
            return_frames: Frames to return to original state
            target_strips: List of strip names to target (None = all strips)
        """
        super().__init__(target_strips=target_strips)
        self.trigger = trigger
        self.intensity = intensity
        self.duration_frames = duration_frames
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
        self.keyframe_helper.insert_blend_alpha_keyframe(strip, 1, 1.0)

        # Apply flicker for each event
        for event_time in events:
            frame = int(event_time * fps)

            # Random flicker (dimmer)
            flicker_alpha = 1.0 - random.uniform(0, self.intensity)

            # Apply flicker at event frame
            self.keyframe_helper.insert_blend_alpha_keyframe(
                strip, frame, flicker_alpha
            )

            # Return to normal brightness
            return_frame = frame + self.return_frames
            self.keyframe_helper.insert_blend_alpha_keyframe(
                strip, return_frame, 1.0
            )

        return True

    def get_required_properties(self) -> List[str]:
        """
        Get list of required strip properties.

        Returns:
            List containing 'blend_alpha' property requirement
        """
        return ['blend_alpha']
