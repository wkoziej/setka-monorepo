# ABOUTME: ShakeAnimation implementation - creates camera shake effect by animating strip position
# ABOUTME: Refactored from VintageFilmEffects with support for random and deterministic shaking

"""Shake animation for addon."""

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

    def __init__(
        self,
        trigger: str = "beat",
        intensity: float = 10.0,
        return_frames: int = 2,
        random_direction: bool = True,
        target_strips: Optional[List[str]] = None,
    ):
        """
        Initialize ShakeAnimation.

        Args:
            trigger: Event type to trigger animation
            intensity: Maximum shake offset in pixels
            return_frames: Frames until position returns to normal
            random_direction: If True, shake randomly; if False, shake horizontally only
            target_strips: List of strip names to target (None = all strips)
        """
        super().__init__(target_strips=target_strips)
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
        if not hasattr(strip, "transform"):
            return False

        # Get base position
        base_x = strip.transform.offset_x
        base_y = strip.transform.offset_y

        # Set initial keyframe at frame 1 (fixed from VSE version)
        self.keyframe_helper.insert_transform_position_keyframes(
            strip, 1, base_x, base_y
        )

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
            new_x = base_x + shake_x
            new_y = base_y + shake_y
            strip.transform.offset_x = new_x
            strip.transform.offset_y = new_y

            self.keyframe_helper.insert_transform_position_keyframes(
                strip, frame, new_x, new_y
            )

            # Return to base position
            return_frame = frame + self.return_frames
            strip.transform.offset_x = base_x
            strip.transform.offset_y = base_y

            self.keyframe_helper.insert_transform_position_keyframes(
                strip, return_frame, base_x, base_y
            )

        return True

    def get_required_properties(self) -> List[str]:
        """
        Get list of required strip properties.

        Returns:
            List containing 'transform' property requirement
        """
        return ["transform"]
