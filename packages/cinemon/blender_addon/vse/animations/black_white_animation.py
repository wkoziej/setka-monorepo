# ABOUTME: BlackWhiteAnimation implementation - applies black and white desaturation effect
# ABOUTME: Dual-mode animation: static (one_time) or event-driven (beat/bass/energy_peaks)

"""Black and white desaturation animation for VSE strips."""

from typing import List, Optional, Tuple, Any

from .event_driven_animation import EventDrivenAnimation


class BlackWhiteAnimation(EventDrivenAnimation):
    """
    Animation that applies black and white desaturation effect to strips.

    Dual-mode animation supporting:
    - one_time: Static desaturation applied to entire strip
    - event-driven: Pulsing saturation synchronized with audio events

    Attributes:
        trigger: Event type ("one_time", "beat", "bass", "energy_peaks")
        intensity: Desaturation intensity (0.0 = color, 1.0 = full B&W)
        duration_frames: Frames to return to normal (event-driven only)
        fade_in: Enable gradual fade-in over 30 frames (one_time only)
    """

    def __init__(
        self,
        trigger: str = "one_time",
        intensity: float = 0.8,
        duration_frames: int = 3,
        fade_in: bool = False,
        target_strips: Optional[List[str]] = None,
    ):
        """
        Initialize BlackWhiteAnimation.

        Args:
            trigger: Event type ("one_time" for static, or "beat"/"bass"/"energy_peaks" for animated)
            intensity: Desaturation intensity (0.0 = color, 1.0 = full B&W)
            duration_frames: Frames until return to base value (event-driven only)
            fade_in: Enable gradual fade-in effect (one_time only)
            target_strips: List of strip names to target (None = all strips)
        """
        super().__init__(
            trigger=trigger,
            intensity=intensity,
            duration_frames=duration_frames,
            target_strips=target_strips,
        )
        self.fade_in = fade_in

    def get_animated_property(self, strip) -> Tuple[str, float]:
        """
        Get the property to animate for event-driven mode.

        Args:
            strip: Blender strip object

        Returns:
            Tuple of (property_path, base_value)
        """
        return ("color_saturation", 1.0)  # Base value is full saturation

    def calculate_effect_value(self, base_value: float, prop_path: str, strip) -> float:
        """
        Calculate desaturation value for event-driven mode.

        Args:
            base_value: Base saturation value (1.0)
            prop_path: Property path being animated
            strip: Blender strip object

        Returns:
            Desaturated value (lower = more B&W)
        """
        return max(0.0, 1.0 - self.intensity)  # Desaturate on event

    def apply_one_time(self, strip, **kwargs) -> bool:
        """
        Apply static black and white effect (one_time mode).

        Args:
            strip: Blender video strip object
            **kwargs: Additional parameters

        Returns:
            True if effect was applied successfully
        """
        try:
            if self.fade_in:
                # Gradual fade-in over 30 frames
                for frame in range(1, 31):
                    saturation = 1.0 - (self.intensity * frame / 30)
                    strip.color_saturation = saturation
                    # Use keyframe helper to insert keyframe
                    if hasattr(self, "keyframe_helper"):
                        self.keyframe_helper.insert_color_saturation_keyframe(
                            strip.name, frame, saturation
                        )
            else:
                # Immediate desaturation
                saturation = max(0.0, 1.0 - self.intensity)
                strip.color_saturation = saturation

            return True

        except Exception as e:
            print(f"Warning: Could not apply B&W one_time effect to {strip.name}: {e}")
            return False

    def get_required_properties(self) -> List[str]:
        """
        Get list of required strip properties.

        Returns:
            List containing 'color_saturation' property requirement
        """
        return ["color_saturation"]
