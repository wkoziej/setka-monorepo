"""
ABOUTME: Main package entry point for setka-common - provides shared utilities and configuration.
ABOUTME: Exports key classes for easy importing by other packages in the monorepo.
"""

from .file_structure.specialized import (
    RecordingStructureManager,
    AnalysisIndex,
    AnalysisIndexEntry,
    load_analysis_index,
)
from .config import (
    BlenderYAMLConfig,
    YAMLConfigLoader,
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
from .utils import (
    find_files_by_type,
    find_media_files,
    sanitize_filename,
    MediaDiscovery,
    ValidationResult,
)

__all__ = [
    "RecordingStructureManager",
    "AnalysisIndex",
    "AnalysisIndexEntry",
    "load_analysis_index",
    "BlenderYAMLConfig",
    "YAMLConfigLoader",
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
    "find_files_by_type",
    "find_media_files",
    "sanitize_filename",
    "MediaDiscovery",
    "ValidationResult",
]
