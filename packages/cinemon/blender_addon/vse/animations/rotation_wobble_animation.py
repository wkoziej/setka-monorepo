# ABOUTME: RotationWobbleAnimation implementation - creates subtle rotation wobble effect
# ABOUTME: Refactored to use EventDrivenAnimation base class for cleaner code

"""Rotation wobble animation for VSE strips using EventDrivenAnimation base."""

import math
import random
from typing import List, Optional, Any

from .event_driven_animation import EventDrivenAnimation


class RotationWobbleAnimation(EventDrivenAnimation):
    """
    Animation that creates rotation wobble effect on strips.

    Now uses EventDrivenAnimation base class to eliminate code duplication.

    Attributes:
        trigger: Event type to react to ("beat", "bass", "energy_peaks")
        wobble_degrees: Maximum wobble angle in degrees (or 'degrees' for compatibility)
        return_frames: How many frames until return to base rotation
        oscillate: Whether to alternate wobble direction
    """

    def __init__(
        self,
        trigger: str = "beat",
        wobble_degrees: float = None,
        degrees: float = None,  # Support both parameter names
        return_frames: int = 3,
        oscillate: bool = True,
        target_strips: Optional[List[str]] = None,
    ):
        """
        Initialize RotationWobbleAnimation.

        Args:
            trigger: Event type to trigger animation
            wobble_degrees: Maximum rotation in degrees (legacy parameter)
            degrees: Maximum rotation in degrees (new parameter)
            return_frames: Frames until rotation returns to normal
            oscillate: If True, alternate wobble direction between events
            target_strips: List of strip names to target (None = all strips)
        """
        # Support both 'wobble_degrees' and 'degrees' parameters
        rotation_amount = degrees if degrees is not None else wobble_degrees
        if rotation_amount is None:
            rotation_amount = 1.0  # Default value

        super().__init__(
            trigger=trigger,
            intensity=rotation_amount,  # Store as intensity for base class
            return_frames=return_frames,
            target_strips=target_strips,
            oscillate=oscillate,  # Store in extra_params
        )
        self.wobble_degrees = rotation_amount
        self.oscillate = oscillate
        self.direction = 1  # Track oscillation direction

    def get_animated_property(self, strip) -> List:
        """
        Get rotation property to animate.

        Args:
            strip: Blender strip object

        Returns:
            List with single tuple for rotation property
        """
        if not hasattr(strip, "transform"):
            return []

        # Return rotation property (base value is always 0 for rotation)
        return [("transform.rotation", 0.0)]

    def calculate_effect_value(self, base_value: float, prop_path: str, strip) -> float:
        """
        Calculate wobble rotation value.

        Args:
            base_value: Base rotation value (always 0)
            prop_path: Property path being animated
            strip: Blender strip object (unused)

        Returns:
            Rotation in radians with wobble applied
        """
        # Calculate wobble rotation with oscillation support
        if self.oscillate:
            # Alternate direction for each event
            wobble_rotation = (
                random.uniform(-self.wobble_degrees, self.wobble_degrees)
                * self.direction
            )
            self.direction *= -1  # Flip for next event
        else:
            # Random in full range
            wobble_rotation = random.uniform(-self.wobble_degrees, self.wobble_degrees)

        # Convert to radians (Blender uses radians for rotation)
        return math.radians(wobble_rotation)

    def get_required_properties(self) -> List[str]:
        """
        Get list of required strip properties.

        Returns:
            List containing 'transform' property requirement
        """
        return ["transform"]
