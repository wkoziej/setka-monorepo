# ABOUTME: ScaleAnimation implementation - animates strip scale based on audio events
# ABOUTME: Refactored to use EventDrivenAnimation base class for cleaner code

"""Scale animation for VSE strips using EventDrivenAnimation base."""

from typing import List, Optional, Any

from .event_driven_animation import EventDrivenAnimation


class ScaleAnimation(EventDrivenAnimation):
    """
    Animation that scales strips based on audio events.

    Now uses EventDrivenAnimation base class to eliminate code duplication.

    Attributes:
        trigger: Event type to react to ("bass", "beat", "energy_peaks")
        intensity: Scale increase factor (0.3 = 30% larger)
        duration_frames: How many frames the scale effect lasts (renamed from return_frames)
        easing: Easing type (currently only "linear" supported)
    """

    def __init__(
        self,
        trigger: str = "bass",
        intensity: float = 0.3,
        duration_frames: int = 2,
        easing: str = "linear",
        target_strips: Optional[List[str]] = None,
    ):
        """
        Initialize ScaleAnimation.

        Args:
            trigger: Event type to trigger animation
            intensity: How much to scale up (0.1 = 10% increase)
            duration_frames: Duration of scale effect in frames
            easing: Type of easing (future feature)
            target_strips: List of strip names to target (None = all strips)
        """
        # Pass duration_frames as return_frames to base class
        super().__init__(
            trigger=trigger,
            intensity=intensity,
            return_frames=duration_frames,
            target_strips=target_strips,
            easing=easing,  # Store for potential future use
        )

    def get_animated_property(self, strip) -> List:
        """
        Get scale properties to animate.

        Args:
            strip: Blender strip object

        Returns:
            List of (property_path, base_value) tuples for scale_x and scale_y
        """
        if not hasattr(strip, "transform"):
            print(f"🎵 Strip {strip.name} has no transform property")
            return []

        # Return both scale_x and scale_y for uniform scaling
        return [
            ("transform.scale_x", strip.transform.scale_x),
            ("transform.scale_y", strip.transform.scale_y),
        ]

    def calculate_effect_value(self, base_value: float, prop_path: str, strip) -> float:
        """
        Calculate scaled value.

        Args:
            base_value: Base scale value
            prop_path: Property path being animated
            strip: Blender strip object (unused)

        Returns:
            Scaled value
        """
        # Scale up by intensity factor
        return base_value * (1.0 + self.intensity)

    def get_required_properties(self) -> List[str]:
        """
        Get list of required strip properties.

        Returns:
            List containing 'transform' property requirement
        """
        return ["transform"]
