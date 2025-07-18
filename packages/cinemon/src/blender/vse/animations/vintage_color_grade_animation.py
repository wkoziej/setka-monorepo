# ABOUTME: VintageColorGradeAnimation implementation - applies vintage color grading with sepia tint
# ABOUTME: Refactored from VintageFilmEffects with warm highlights and cool shadows for vintage look

"""Vintage color grading animation for VSE strips."""

from typing import List

from .base_effect_animation import BaseEffectAnimation


class VintageColorGradeAnimation(BaseEffectAnimation):
    """
    Animation that applies vintage color grading to strips.
    
    Refactored from VintageFilmEffects.apply_vintage_color_grade.
    
    This is a one-time effect that applies vintage sepia tint and contrast
    adjustments to the entire strip.
    
    Attributes:
        trigger: Event type (ignored for one-time effect)
        sepia_amount: Sepia tint intensity (0.0 to 1.0)
        contrast_boost: Contrast boost amount (0.0 to 1.0)
    """
    
    def __init__(self,
                 trigger: str = "one_time",
                 sepia_amount: float = 0.3,
                 contrast_boost: float = 0.2):
        """
        Initialize VintageColorGradeAnimation.
        
        Args:
            trigger: Event type (ignored for one-time effect)
            sepia_amount: Sepia tint intensity (0.0 to 1.0)
            contrast_boost: Contrast boost amount (0.0 to 1.0)
        """
        super().__init__()
        self.trigger = trigger
        self.sepia_amount = sepia_amount
        self.contrast_boost = contrast_boost
    
    def apply_to_strip(self, strip, events: List[float], fps: int, **kwargs) -> bool:
        """
        Apply vintage color grading to strip.
        
        Args:
            strip: Blender video strip object
            events: List of event times (ignored for one-time effect)
            fps: Frames per second
            **kwargs: Additional parameters (unused)
            
        Returns:
            True if animation was applied successfully
        """
        try:
            # Add color balance modifier for vintage look
            color_modifier = strip.modifiers.new(
                name="Vintage_Grade", type="COLOR_BALANCE"
            )
            
            # Sepia effect: warm highlights, cool shadows
            color_modifier.color_balance.lift = (
                1.0 - self.sepia_amount * 0.1,  # R (shadows slightly cooler)
                1.0 - self.sepia_amount * 0.05,  # G
                1.0 - self.sepia_amount * 0.2,  # B (remove blue from shadows)
            )
            
            color_modifier.color_balance.gamma = (
                1.0 + self.sepia_amount * 0.1,  # R (midtones warmer)
                1.0 + self.sepia_amount * 0.05,  # G
                1.0 - self.sepia_amount * 0.1,  # B (reduce blue in midtones)
            )
            
            color_modifier.color_balance.gain = (
                1.0 + self.sepia_amount * 0.2,  # R (highlights warm)
                1.0 + self.sepia_amount * 0.15,  # G
                1.0 - self.sepia_amount * 0.1,  # B (reduce blue in highlights)
            )
            
            # Increase contrast for vintage look
            color_modifier.color_balance.gamma = tuple(
                g * (1.0 + self.contrast_boost * 0.3)
                for g in color_modifier.color_balance.gamma
            )
            
            return True
            
        except Exception as e:
            print(f"Warning: Could not apply vintage color grade to {strip.name}: {e}")
            return False
    
    def get_required_properties(self) -> List[str]:
        """
        Get list of required strip properties.
        
        Returns:
            List containing 'modifiers' property requirement
        """
        return ['modifiers']