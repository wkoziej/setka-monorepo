# ABOUTME: Animation module initialization - provides base classes and implementations for compositional animations
# ABOUTME: Supports various animation types like scale, shake, rotation that can be combined independently

"""Animation module for Blender VSE strip effects."""

from .animation_factory import AnimationFactory
from .base_effect_animation import BaseEffectAnimation
from .event_driven_animation import EventDrivenAnimation
from .modifier_animation_mixin import ModifierAnimationMixin
from .black_white_animation import BlackWhiteAnimation
from .brightness_flicker_animation import BrightnessFlickerAnimation
from .jitter_animation import JitterAnimation
from .rotation_wobble_animation import RotationWobbleAnimation
from .scale_animation import ScaleAnimation
from .shake_animation import ShakeAnimation
from .vintage_color_grade_animation import VintageColorGradeAnimation
from .visibility_animation import VisibilityAnimation

__all__ = [
    "BaseEffectAnimation",
    "EventDrivenAnimation",
    "ModifierAnimationMixin",
    "ScaleAnimation",
    "ShakeAnimation",
    "RotationWobbleAnimation",
    "JitterAnimation",
    "BrightnessFlickerAnimation",
    "BlackWhiteAnimation",
    "VintageColorGradeAnimation",
    "VisibilityAnimation",
    "AnimationFactory",
]
