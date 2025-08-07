# ABOUTME: ShakeAnimation implementation - creates camera shake effect by animating strip position
# ABOUTME: Refactored to use EventDrivenAnimation base class for cleaner code

"""Shake animation for VSE strips using EventDrivenAnimation base."""

import random
from typing import List, Optional, Any

from .event_driven_animation import EventDrivenAnimation


class ShakeAnimation(EventDrivenAnimation):
    """
    Animation that creates shaking/vibration effect on strips.

    Now uses EventDrivenAnimation base class to eliminate code duplication.

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
        super().__init__(
            trigger=trigger,
            intensity=intensity,
            return_frames=return_frames,
            target_strips=target_strips,
            random_direction=random_direction,  # Store in extra_params
        )
        self.random_direction = random_direction

    def get_animated_property(self, strip) -> List:
        """
        Get position properties to animate.

        Args:
            strip: Blender strip object

        Returns:
            List of (property_path, base_value) tuples for offset_x and offset_y
        """
        if not hasattr(strip, "transform"):
            return []

        # Return both offset_x and offset_y for shake effect
        return [
            ("transform.offset_x", strip.transform.offset_x),
            ("transform.offset_y", strip.transform.offset_y),
        ]

    def calculate_effect_value(self, base_value: float, prop_path: str, strip) -> float:
        """
        Calculate shake offset value.

        Args:
            base_value: Base position value
            prop_path: Property path being animated (offset_x or offset_y)
            strip: Blender strip object (unused)

        Returns:
            Position with shake offset applied
        """
        if self.random_direction:
            # Random shake in both directions
            shake_offset = random.uniform(-self.intensity, self.intensity)
        else:
            # Deterministic shake (horizontal only for offset_x, no shake for offset_y)
            if "offset_x" in prop_path:
                shake_offset = self.intensity
            else:  # offset_y
                shake_offset = 0

        return base_value + shake_offset

    def get_required_properties(self) -> List[str]:
        """
        Get list of required strip properties.

        Returns:
            List containing 'transform' property requirement
        """
        return ["transform"]
