"""
ABOUTME: Configuration module for setka-common - provides YAML configuration classes and utilities.
ABOUTME: Exports configuration classes for use by other packages in the monorepo.
"""

from .yaml_config import (
    BlenderYAMLConfig,
    ProjectConfig,
    AudioAnalysisConfig,
    LayoutConfig,
    YAMLConfigLoader,
    AnimationSpec,
    StripAnimations,
    ConfigValidationError,
    Resolution,
)
from .validation import ConfigValidator

# Expose validation constants from YAMLConfigLoader
_loader = YAMLConfigLoader()
VALID_ANIMATION_TYPES = _loader.VALID_ANIMATION_TYPES
VALID_TRIGGERS = _loader.VALID_TRIGGERS
VALID_LAYOUT_TYPES = _loader.VALID_LAYOUT_TYPES

__all__ = [
    "BlenderYAMLConfig",
    "ProjectConfig",
    "AudioAnalysisConfig",
    "LayoutConfig",
    "YAMLConfigLoader",
    "ConfigValidator",
    "AnimationSpec",
    "StripAnimations",
    "ConfigValidationError",
    "Resolution",
    "VALID_ANIMATION_TYPES",
    "VALID_TRIGGERS",
    "VALID_LAYOUT_TYPES",
]
