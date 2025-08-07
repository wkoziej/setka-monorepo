# ABOUTME: AnimationFactory - factory pattern for creating animation instances from YAML specs
# ABOUTME: Centralizes animation creation logic and parameter defaults for easy extension

"""Animation factory for creating animation instances from YAML configuration."""

from typing import Any, Dict, List, Optional, Tuple, Type

from .base_effect_animation import BaseEffectAnimation
from .black_white_animation import BlackWhiteAnimation
from .brightness_flicker_animation import BrightnessFlickerAnimation
from .film_grain_animation import FilmGrainAnimation
from .jitter_animation import JitterAnimation
from .rotation_wobble_animation import RotationWobbleAnimation
from .scale_animation import ScaleAnimation
from .shake_animation import ShakeAnimation
from .vintage_color_grade_animation import VintageColorGradeAnimation
from .visibility_animation import VisibilityAnimation


class AnimationFactory:
    """
    Factory for creating animation instances from YAML configuration specs.

    Uses a registry pattern to map animation types to their classes and default parameters.
    This eliminates repetitive if/elif blocks and makes adding new animations simple.
    """

    # Registry of animation types to (class, default_params) tuples
    _registry: Dict[str, Tuple[Type[BaseEffectAnimation], Dict[str, Any]]] = {}

    @classmethod
    def register(
        cls,
        animation_type: str,
        animation_class: Type[BaseEffectAnimation],
        default_params: Dict[str, Any],
    ) -> None:
        """
        Register an animation type with its class and default parameters.

        Args:
            animation_type: String identifier for the animation (e.g., "scale", "shake")
            animation_class: The animation class to instantiate
            default_params: Default parameter values for the animation
        """
        cls._registry[animation_type] = (animation_class, default_params)

    @classmethod
    def create(cls, animation_spec: Dict[str, Any]) -> Optional[BaseEffectAnimation]:
        """
        Create an animation instance from a YAML specification.

        Args:
            animation_spec: Dictionary containing animation configuration
                           Must include 'type' key, other keys are animation-specific

        Returns:
            Animation instance or None if type is not registered
        """
        animation_type = animation_spec.get("type")
        if not animation_type or animation_type not in cls._registry:
            print(f"⚠️ Unknown animation type: {animation_type}")
            return None

        animation_class, default_params = cls._registry[animation_type]

        # Extract parameters with defaults
        params = {}
        for param_name, default_value in default_params.items():
            params[param_name] = animation_spec.get(param_name, default_value)

        # Handle parameter aliases for rotation animation
        if animation_type == "rotation":
            # Support both 'degrees' (from YAML) and 'wobble_degrees' (internal)
            if "degrees" in animation_spec and "wobble_degrees" not in animation_spec:
                params["wobble_degrees"] = animation_spec["degrees"]
                print(
                    f"🔄 Mapping 'degrees' ({animation_spec['degrees']}) to 'wobble_degrees' for rotation animation"
                )

        # Handle common parameters
        params["trigger"] = animation_spec.get("trigger")
        params["target_strips"] = animation_spec.get("target_strips", [])

        try:
            animation = animation_class(**params)
            # Log creation for debugging
            target_info = (
                f", target_strips={params['target_strips']}"
                if params["target_strips"]
                else ""
            )
            print(
                f"🎨 Created {animation_type.capitalize()}Animation: trigger={params.get('trigger')}, intensity={params.get('intensity', 'N/A')}{target_info}"
            )
            return animation
        except Exception as e:
            print(f"❌ Failed to create {animation_type} animation: {e}")
            return None

    @classmethod
    def create_multiple(
        cls, animation_specs: List[Dict[str, Any]]
    ) -> List[BaseEffectAnimation]:
        """
        Create multiple animations from a list of specifications.

        Args:
            animation_specs: List of animation specification dictionaries

        Returns:
            List of successfully created animation instances
        """
        animations = []
        for spec in animation_specs:
            animation = cls.create(spec)
            if animation:
                animations.append(animation)
        return animations

    @classmethod
    def get_registered_types(cls) -> List[str]:
        """
        Get list of all registered animation types.

        Returns:
            List of animation type identifiers
        """
        return list(cls._registry.keys())


# Register all available animations with their default parameters
AnimationFactory.register(
    "scale",
    ScaleAnimation,
    {"intensity": 0.3, "duration_frames": 2, "easing": "linear"},
)

AnimationFactory.register(
    "shake", ShakeAnimation, {"intensity": 10.0, "return_frames": 2}
)

AnimationFactory.register(
    "rotation", RotationWobbleAnimation, {"wobble_degrees": 1.0, "return_frames": 3}
)

AnimationFactory.register(
    "jitter", JitterAnimation, {"intensity": 2.0, "min_interval": 3, "max_interval": 8}
)

AnimationFactory.register(
    "brightness_flicker",
    BrightnessFlickerAnimation,
    {"intensity": 0.15, "return_frames": 1},
)

AnimationFactory.register("black_white", BlackWhiteAnimation, {"intensity": 0.8})

AnimationFactory.register("film_grain", FilmGrainAnimation, {"intensity": 0.1})

AnimationFactory.register(
    "vintage_color",
    VintageColorGradeAnimation,
    {"sepia_amount": 0.3, "contrast_boost": 0.2},
)

AnimationFactory.register(
    "visibility", VisibilityAnimation, {"pattern": "alternate", "duration_frames": 10}
)
