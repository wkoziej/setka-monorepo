"""
ABOUTME: Main package entry point for setka-common - provides shared utilities and configuration.
ABOUTME: Exports key classes for easy importing by other packages in the monorepo.
"""

from .file_structure.specialized import RecordingStructureManager
from .config import (
    BlenderYAMLConfig,
    YAMLConfigLoader,
    ConfigValidator,
    AnimationSpec,
    StripAnimations,
    ConfigValidationError,
    ProjectConfig,
    AudioAnalysisConfig,
    LayoutConfig,
    Resolution,
    VALID_ANIMATION_TYPES,
    VALID_TRIGGERS,
    VALID_LAYOUT_TYPES,
)

__all__ = [
    "RecordingStructureManager",
    "BlenderYAMLConfig",
    "YAMLConfigLoader",
    "ConfigValidator",
    "AnimationSpec",
    "StripAnimations",
    "ConfigValidationError",
    "ProjectConfig",
    "AudioAnalysisConfig",
    "LayoutConfig",
    "Resolution",
    "VALID_ANIMATION_TYPES",
    "VALID_TRIGGERS",
    "VALID_LAYOUT_TYPES",
]
