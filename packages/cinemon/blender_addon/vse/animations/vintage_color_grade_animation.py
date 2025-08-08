# ABOUTME: VintageColorGradeAnimation implementation - applies vintage color grading with sepia tint
# ABOUTME: Dual-mode animation: static (one_time) or event-driven (beat/bass/energy_peaks)

"""Vintage color grading animation for VSE strips."""

from typing import List, Optional, Tuple, Any

from .event_driven_animation import EventDrivenAnimation


class VintageColorGradeAnimation(EventDrivenAnimation):
    """
    Animation that applies vintage color grading to strips.

    Dual-mode animation supporting:
    - one_time: Static sepia and contrast applied to entire strip
    - event-driven: Pulsing sepia/contrast synchronized with audio events

    Uses color balance modifiers for warm/cool tinting and contrast.

    Attributes:
        trigger: Event type ("one_time", "beat", "bass", "energy_peaks")
        sepia_amount: Sepia tint intensity (0.0 to 1.0)
        contrast_boost: Contrast boost amount (0.0 to 1.0)
        return_frames: Frames to return to base (event-driven only)
        animate_property: What to animate ("sepia", "contrast", "both")
    """

    def __init__(
        self,
        trigger: str = "one_time",
        sepia_amount: float = 0.3,
        contrast_boost: float = 0.2,
        return_frames: int = 6,
        animate_property: str = "sepia",
        target_strips: Optional[List[str]] = None,
    ):
        """
        Initialize VintageColorGradeAnimation.

        Args:
            trigger: Event type ("one_time" for static, or "beat"/"bass"/"energy_peaks" for animated)
            sepia_amount: Sepia tint intensity (0.0 to 1.0)
            contrast_boost: Contrast boost amount (0.0 to 1.0)
            return_frames: Frames until return to base (event-driven only)
            animate_property: What to animate - "sepia", "contrast", or "both"
            target_strips: List of strip names to target (None = all strips)
        """
        # For event-driven mode, intensity is derived from sepia or contrast
        intensity = sepia_amount if animate_property == "sepia" else contrast_boost

        super().__init__(
            trigger=trigger,
            intensity=intensity,
            return_frames=return_frames,
            target_strips=target_strips,
        )
        self.sepia_amount = sepia_amount
        self.contrast_boost = contrast_boost
        self.animate_property = animate_property

    def get_animated_property(self, strip) -> List[Tuple[str, Any]]:
        """
        Get the properties to animate for event-driven mode.

        Uses color_multiply and color_saturation to simulate vintage effect.

        Args:
            strip: Blender strip object

        Returns:
            List of (property_path, base_value) tuples
        """
        # For sepia effect, we'll animate saturation and color multiply
        if self.animate_property == "sepia":
            # Animate saturation to create sepia-like desaturation
            return [("color_saturation", 1.0)]
        elif self.animate_property == "contrast":
            # Animate color multiply for contrast changes
            return [("color_multiply", 1.0)]
        else:  # both
            # Animate both properties
            return [("color_saturation", 1.0), ("color_multiply", 1.0)]

    def calculate_effect_value(self, base_value: Any, prop_path: str, strip) -> Any:
        """
        Calculate vintage effect value for event-driven mode.

        Args:
            base_value: Base property value
            prop_path: Property path being animated
            strip: Blender strip object

        Returns:
            Modified value for vintage effect pulse
        """
        if "saturation" in prop_path:  # Sepia-like effect through desaturation
            # Reduce saturation on event to create vintage look
            # Lower saturation = more sepia-like
            return max(0.3, 1.0 - self.sepia_amount * 0.7)
        elif "multiply" in prop_path:  # Contrast effect through color multiply
            # Darken slightly for vintage contrast
            # Lower value = higher contrast/darker
            return max(0.6, 1.0 - self.contrast_boost * 0.4)
        return base_value

    def apply_one_time(self, strip, **kwargs) -> bool:
        """
        Apply static vintage color grade (one_time mode).

        Uses color modifiers in Blender for true vintage effect.

        Args:
            strip: Blender video strip object
            **kwargs: Additional parameters

        Returns:
            True if effect was applied successfully
        """
        try:
            # Create color balance modifier directly
            color_modifier = strip.modifiers.new(
                name="Vintage_Grade", type="COLOR_BALANCE"
            )

            # Apply sepia tinting
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

            # Apply contrast boost
            color_modifier.color_balance.gamma = tuple(
                g * (1.0 + self.contrast_boost * 0.3)
                for g in color_modifier.color_balance.gamma
            )

            return True

        except Exception as e:
            print(
                f"Warning: Could not apply vintage color grade one_time to {strip.name}: {e}"
            )
            return False

    def get_required_properties(self) -> List[str]:
        """
        Get list of required strip properties.

        Returns:
            List containing 'modifiers' property requirement
        """
        return ["modifiers"]
