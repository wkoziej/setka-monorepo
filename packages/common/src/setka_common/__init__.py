"""
ABOUTME: Main package entry point for setka-common - provides shared utilities and configuration.
ABOUTME: Exports key classes for easy importing by other packages in the monorepo.
"""

from .file_structure.specialized import RecordingStructureManager
from .config import BlenderYAMLConfig, AnimationSpec, YAMLConfigLoader, ConfigValidator

__all__ = [
    "RecordingStructureManager",
    "BlenderYAMLConfig",
    "AnimationSpec",
    "YAMLConfigLoader",
    "ConfigValidator",
]
