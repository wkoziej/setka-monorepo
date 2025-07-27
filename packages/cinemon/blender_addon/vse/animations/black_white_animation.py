# ABOUTME: BlackWhiteAnimation implementation - applies black and white desaturation effect
# ABOUTME: Refactored from VintageFilmEffects for one-time color effect application

"""Black and white desaturation animation for VSE strips."""

from typing import List, Optional

from .base_effect_animation import BaseEffectAnimation


class BlackWhiteAnimation(BaseEffectAnimation):
    """
    Animation that applies black and white desaturation effect to strips.

    Refactored from VintageFilmEffects.apply_black_white_effect.

    This is a one-time effect that doesn't depend on events but applies
    a consistent desaturation to the entire strip.

    Attributes:
        trigger: Event type (ignored for one-time effect)
        intensity: Desaturation intensity (0.0 = color, 1.0 = full B&W)
    """

    def __init__(
        self,
        trigger: str = "one_time",
        intensity: float = 0.8,
        target_strips: Optional[List[str]] = None,
    ):
        """
        Initialize BlackWhiteAnimation.

        Args:
            trigger: Event type (ignored for one-time effect)
            intensity: Desaturation intensity (0.0 = color, 1.0 = full B&W)
            target_strips: List of strip names to target (None = all strips)
        """
        super().__init__(target_strips=target_strips)
        self.trigger = trigger
        self.intensity = intensity

    def apply_to_strip(self, strip, events: List[float], fps: int, **kwargs) -> bool:
        """
        Apply black and white desaturation to strip.

        Args:
            strip: Blender video strip object
            events: List of event times (ignored for one-time effect)
            fps: Frames per second
            **kwargs: Additional parameters (unused)

        Returns:
            True if animation was applied successfully
        """
        try:
            # Use strip's built-in color_saturation property for B&W effect
            # Setting saturation with controlled intensity for pure B&W at high values
            saturation = max(0.0, 1.0 - self.intensity * 1.2)
            strip.color_saturation = saturation

            return True

        except Exception as e:
            print(f"Warning: Could not apply B&W effect to {strip.name}: {e}")
            return False

    def get_required_properties(self) -> List[str]:
        """
        Get list of required strip properties.

        Returns:
            List containing 'color_saturation' property requirement
        """
        return ["color_saturation"]
