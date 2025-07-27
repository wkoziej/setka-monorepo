# ABOUTME: Config package for cinemon configuration management
# ABOUTME: Contains PresetManager and CinemonConfigGenerator classes

"""Configuration management for cinemon."""

from .cinemon_config_generator import CinemonConfigGenerator
from .preset_manager import PresetManager

__all__ = [
    "PresetManager",
    "CinemonConfigGenerator",
]
