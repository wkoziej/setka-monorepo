# ABOUTME: EventDrivenAnimation base class for all event-triggered animations
# ABOUTME: Provides common pattern for apply effect -> return to base animations

"""Base class for event-driven animations that respond to audio events."""

import random
from typing import List, Optional, Tuple, Any

from .base_effect_animation import BaseEffectAnimation


class EventDrivenAnimation(BaseEffectAnimation):
    """
    Base class for animations that respond to audio events with a pattern of:
    1. Apply effect at event time
    2. Return to base value after specified frames

    This eliminates code duplication across scale, shake, rotation, etc.

    Attributes:
        trigger: Event type to react to ("beat", "bass", "energy_peaks")
        intensity: Effect intensity (meaning varies by animation type)
        return_frames: Frames until return to base value
        target_strips: Optional list of strip names to target
    """

    def __init__(
        self,
        trigger: str = "beat",
        intensity: float = 1.0,
        return_frames: int = 3,
        target_strips: Optional[List[str]] = None,
        **kwargs,
    ):
        """
        Initialize EventDrivenAnimation.

        Args:
            trigger: Event type to trigger animation
            intensity: Effect intensity
            return_frames: Frames until return to base value
            target_strips: List of strip names to target (None = all strips)
            **kwargs: Additional parameters passed to subclasses
        """
        super().__init__(target_strips=target_strips)
        self.trigger = trigger
        self.intensity = intensity
        self.return_frames = return_frames
        # Store additional params for subclasses
        self.extra_params = kwargs

    def apply_to_strip(self, strip, events: List[float], fps: int, **kwargs) -> bool:
        """
        Generic apply method for all event-driven animations.

        Args:
            strip: Blender video strip object
            events: List of event times in seconds
            fps: Frames per second
            **kwargs: Additional parameters

        Returns:
            True if animation was applied successfully
        """
        # Special handling for one_time trigger - static mode
        if self.trigger == "one_time":
            return self.apply_one_time(strip, **kwargs)

        try:
            # Get the property to animate and its base value
            prop_data = self.get_animated_property(strip)
            if not prop_data:
                return False

            # Handle different return types from get_animated_property
            if isinstance(prop_data, tuple) and len(prop_data) == 2:
                prop_path, base_value = prop_data
                # For single property animations
                properties = [(prop_path, base_value)]
            else:
                # For multi-property animations (like scale_x and scale_y)
                properties = prop_data

            # Set initial keyframe at frame 1
            for prop_path, base_value in properties:
                self._set_property_value(strip, prop_path, base_value)
            self._insert_keyframes(strip.name, properties, 1)

            # Apply effect for each event
            for event_time in events:
                frame = int(event_time * fps)

                # Calculate and apply effect values
                effect_values = []
                for prop_path, base_value in properties:
                    effect_value = self.calculate_effect_value(
                        base_value, prop_path, strip
                    )
                    self._set_property_value(strip, prop_path, effect_value)
                    effect_values.append((prop_path, effect_value))

                # Keyframe the effect
                self._insert_keyframes(strip.name, effect_values, frame)

                # Return to base values
                return_frame = frame + self.return_frames
                for prop_path, base_value in properties:
                    self._set_property_value(strip, prop_path, base_value)
                self._insert_keyframes(strip.name, properties, return_frame)

            return True

        except Exception as e:
            print(f"Error applying {self.__class__.__name__} to {strip.name}: {e}")
            return False

    def _set_property_value(self, strip, prop_path: str, value: Any):
        """
        Set a property value on a strip using dot notation path.

        Args:
            strip: Blender strip object
            prop_path: Property path like "transform.scale_x"
            value: Value to set
        """
        parts = prop_path.split(".")
        obj = strip
        for part in parts[:-1]:
            obj = getattr(obj, part)
        setattr(obj, parts[-1], value)

    def _get_property_value(self, strip, prop_path: str) -> Any:
        """
        Get a property value from a strip using dot notation path.

        Args:
            strip: Blender strip object
            prop_path: Property path like "transform.scale_x"

        Returns:
            The property value
        """
        parts = prop_path.split(".")
        obj = strip
        for part in parts:
            obj = getattr(obj, part)
        return obj

    def _insert_keyframes(
        self, strip_name: str, properties: List[Tuple[str, Any]], frame: int
    ):
        """
        Insert keyframes for multiple properties.

        Args:
            strip_name: Name of the strip
            properties: List of (property_path, value) tuples
            frame: Frame number
        """
        keyframed = set()  # Track what we've already keyframed

        for prop_path, value in properties:
            if "scale" in prop_path and "scale" not in keyframed:
                self.keyframe_helper.insert_transform_scale_keyframes(strip_name, frame)
                keyframed.add("scale")
            elif "offset" in prop_path and "offset" not in keyframed:
                self.keyframe_helper.insert_transform_position_keyframes(
                    strip_name, frame
                )
                keyframed.add("offset")
            elif "rotation" in prop_path and "rotation" not in keyframed:
                # Use the singular method name with rotation value
                self.keyframe_helper.insert_transform_rotation_keyframe(
                    strip_name, frame, value
                )
                keyframed.add("rotation")
            elif "color_multiply" in prop_path and "color_multiply" not in keyframed:
                self.keyframe_helper.insert_color_multiply_keyframe(
                    strip_name, frame, value
                )
                keyframed.add("color_multiply")
            elif (
                "color_saturation" in prop_path and "color_saturation" not in keyframed
            ):
                self.keyframe_helper.insert_color_saturation_keyframe(
                    strip_name, frame, value
                )
                keyframed.add("color_saturation")
            elif "blend_alpha" in prop_path and "blend_alpha" not in keyframed:
                # This might also need fixing - check if method exists
                self.keyframe_helper.insert_opacity_keyframes(strip_name, frame)
                keyframed.add("blend_alpha")

    # Methods to be overridden by subclasses
    def get_animated_property(self, strip) -> Any:
        """
        Get the property/properties to animate and base values.

        Should return either:
        - Tuple of (property_path, base_value) for single property
        - List of [(property_path, base_value), ...] for multiple properties

        Args:
            strip: Blender strip object

        Returns:
            Property data for animation
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement get_animated_property()"
        )

    def calculate_effect_value(self, base_value: Any, prop_path: str, strip) -> Any:
        """
        Calculate the effect value for a property.

        Args:
            base_value: Base value of the property
            prop_path: Property path being animated
            strip: Blender strip object (for context if needed)

        Returns:
            The calculated effect value
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement calculate_effect_value()"
        )

    def apply_one_time(self, strip, **kwargs) -> bool:
        """
        Apply static one-time effect (no animation).

        Override in subclasses that support dual-mode (static + event-driven).

        Args:
            strip: Blender video strip object
            **kwargs: Additional parameters

        Returns:
            True if effect was applied successfully
        """
        # Default implementation for animations that don't support one_time
        print(f"Warning: {self.__class__.__name__} doesn't support one_time trigger")
        return False
