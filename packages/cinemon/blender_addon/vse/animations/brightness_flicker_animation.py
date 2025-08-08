# ABOUTME: BrightnessFlickerAnimation implementation - creates brightness flicker effect
# ABOUTME: Refactored to use EventDrivenAnimation base class for cleaner code

"""Brightness flicker animation for VSE strips using EventDrivenAnimation base."""

import random
from typing import List, Optional, Any

from .event_driven_animation import EventDrivenAnimation


class BrightnessFlickerAnimation(EventDrivenAnimation):
    """
    Animation that creates brightness flicker effect on strips.

    Now uses EventDrivenAnimation base class to eliminate code duplication.
    Animates both brightness (color_multiply) and saturation for dramatic effect.

    Attributes:
        trigger: Event type to react to ("beat", "bass", "energy_peaks")
        intensity: Flicker intensity (0.0 to 1.0, how much dimmer/brighter)
        duration_frames: How many frames until return to normal brightness
    """

    def __init__(
        self,
        trigger: str = "beat",
        intensity: float = 0.15,
        duration_frames: int = 1,
        target_strips: Optional[List[str]] = None,
    ):
        """
        Initialize BrightnessFlickerAnimation.

        Args:
            trigger: Event type to trigger animation
            intensity: Maximum brightness change (0.0 to 1.0)
            duration_frames: Frames until brightness returns to normal
            target_strips: List of strip names to target (None = all strips)
        """
        super().__init__(
            trigger=trigger,
            intensity=intensity,
            duration_frames=duration_frames,
            target_strips=target_strips,
        )

    def get_animated_property(self, strip) -> List:
        """
        Get brightness and saturation properties to animate.

        Args:
            strip: Blender strip object

        Returns:
            List of (property_path, base_value) tuples for color properties
        """
        # Check for required properties
        if not hasattr(strip, "color_multiply") or not hasattr(
            strip, "color_saturation"
        ):
            return []

        # Return both color_multiply and color_saturation for flicker effect
        return [
            ("color_multiply", 1.0),  # Base brightness is 1.0
            ("color_saturation", 1.0),  # Base saturation is 1.0
        ]

    def calculate_effect_value(self, base_value: float, prop_path: str, strip) -> float:
        """
        Calculate flicker value for brightness or saturation.

        Args:
            base_value: Base value (always 1.0 for both properties)
            prop_path: Property path being animated
            strip: Blender strip object (unused)

        Returns:
            Flickered value for the property
        """
        # Determine if we're brightening or darkening (50/50 chance)
        # Use consistent random for both properties in same frame
        if not hasattr(self, "_current_brighten"):
            self._current_brighten = random.random() > 0.5
            self._flicker_calculated = False

        # Calculate flicker values once per event
        if not self._flicker_calculated:
            if self._current_brighten:
                # Brighten: increase values based on intensity
                self._brightness_value = 1.0 + random.uniform(0, self.intensity)
                self._saturation_value = 1.0 + random.uniform(0, self.intensity)
            else:
                # Darken: decrease values
                darken_amount = min(
                    self.intensity, 1.0 / 0.7
                )  # Max darken to near-black
                self._brightness_value = 1.0 - random.uniform(0, darken_amount * 0.7)
                self._saturation_value = 1.0 - random.uniform(
                    0, min(self.intensity, 1.0)
                )
            self._flicker_calculated = True

        # Return appropriate value based on property
        if "color_multiply" in prop_path:
            value = self._brightness_value
        else:  # color_saturation
            value = self._saturation_value

        # Reset flags after both properties are calculated
        if "color_saturation" in prop_path:
            self._current_brighten = None
            self._flicker_calculated = False

        return value

    def get_required_properties(self) -> List[str]:
        """
        Get list of required strip properties.

        Returns:
            List containing 'color_multiply' and 'color_saturation' property requirements
        """
        return ["color_multiply", "color_saturation"]
