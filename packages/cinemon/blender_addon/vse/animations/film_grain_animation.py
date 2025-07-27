# ABOUTME: FilmGrainAnimation implementation - adds film grain noise effect using Blender modifiers
# ABOUTME: Refactored from VintageFilmEffects with blur and color adjustments for grain simulation

"""Film grain animation for VSE strips."""

from typing import List, Optional

from .base_effect_animation import BaseEffectAnimation


class FilmGrainAnimation(BaseEffectAnimation):
    """
    Animation that adds film grain noise effect to strips.
    
    Refactored from VintageFilmEffects.apply_film_grain_noise.
    
    This is a one-time effect that applies film grain simulation using
    Blender modifiers (Gaussian blur + color adjustments).
    
    Attributes:
        trigger: Event type (ignored for one-time effect)
        intensity: Grain intensity (0.0 to 1.0)
    """

    def __init__(self,
                 trigger: str = "one_time",
                 intensity: float = 0.1,
                 target_strips: Optional[List[str]] = None):
        """
        Initialize FilmGrainAnimation.
        
        Args:
            trigger: Event type (ignored for one-time effect)
            intensity: Grain intensity (0.0 to 1.0)
            target_strips: List of strip names to target (None = all strips)
        """
        super().__init__(target_strips=target_strips)
        self.trigger = trigger
        self.intensity = intensity

    def apply_to_strip(self, strip, events: List[float], fps: int, **kwargs) -> bool:
        """
        Apply film grain noise effect to strip.
        
        Args:
            strip: Blender video strip object
            events: List of event times (ignored for one-time effect)
            fps: Frames per second
            **kwargs: Additional parameters (unused)
            
        Returns:
            True if animation was applied successfully
        """
        try:
            # Add Gaussian Blur modifier with noise-like settings
            # Note: Blender VSE doesn't have direct noise modifier,
            # but we can simulate grain with subtle blur + contrast adjustments

            # First add a slight blur to soften the image (film-like)
            blur_modifier = strip.modifiers.new(
                name="Vintage_Grain_Blur", type="GAUSSIAN_BLUR"
            )
            blur_modifier.sigma_x = self.intensity * 0.5
            blur_modifier.sigma_y = self.intensity * 0.5

            # Add contrast/brightness adjustment for grain effect
            color_modifier = strip.modifiers.new(
                name="Vintage_Grain_Color", type="COLOR_BALANCE"
            )
            color_modifier.color_balance.gain = (
                1.0 + self.intensity * 0.2,  # R
                1.0 + self.intensity * 0.2,  # G
                1.0 + self.intensity * 0.2,  # B
            )
            color_modifier.color_balance.gamma = (
                1.0 + self.intensity * 0.1,  # R
                1.0 + self.intensity * 0.1,  # G
                1.0 + self.intensity * 0.1,  # B
            )

            return True

        except Exception as e:
            print(f"Warning: Could not apply film grain to {strip.name}: {e}")
            return False

    def get_required_properties(self) -> List[str]:
        """
        Get list of required strip properties.
        
        Returns:
            List containing 'modifiers' property requirement
        """
        return ['modifiers']
