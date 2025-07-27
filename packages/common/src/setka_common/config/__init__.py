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
)
from .validation import ConfigValidator

__all__ = [
    "BlenderYAMLConfig",
    "ProjectConfig",
    "AudioAnalysisConfig",
    "LayoutConfig",
    "YAMLConfigLoader",
    "ConfigValidator",
    "AnimationSpec",
    "StripAnimations",
]
