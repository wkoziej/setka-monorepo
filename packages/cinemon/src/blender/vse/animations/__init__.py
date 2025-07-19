# ABOUTME: Animation module initialization - provides base classes and implementations for compositional animations
# ABOUTME: Supports various animation types like scale, shake, rotation that can be combined independently

"""Animation module for Blender VSE strip effects."""

from .base_effect_animation import BaseEffectAnimation
from .scale_animation import ScaleAnimation
from .shake_animation import ShakeAnimation
from .rotation_wobble_animation import RotationWobbleAnimation
from .jitter_animation import JitterAnimation
from .brightness_flicker_animation import BrightnessFlickerAnimation
from .black_white_animation import BlackWhiteAnimation
from .film_grain_animation import FilmGrainAnimation
from .vintage_color_grade_animation import VintageColorGradeAnimation
from .visibility_animation import VisibilityAnimation

__all__ = [
    "BaseEffectAnimation",
    "ScaleAnimation", 
    "ShakeAnimation",
    "RotationWobbleAnimation",
    "JitterAnimation",
    "BrightnessFlickerAnimation",
    "BlackWhiteAnimation",
    "FilmGrainAnimation",
    "VintageColorGradeAnimation",
    "VisibilityAnimation"
]