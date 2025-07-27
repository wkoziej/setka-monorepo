# ABOUTME: Main package for Blender VSE project preparation tools
# ABOUTME: Provides project management, VSE scripting, and animation capabilities

"""Cinemon - Blender VSE project preparation and animation tools."""

__version__ = "0.1.0"

from .project_manager import BlenderProjectManager as ProjectManager
from .config.cinemon_config_generator import CinemonConfigGenerator

# vse_script contains bpy imports that only work in Blender
# so we don't import it by default

__all__ = ["ProjectManager", "CinemonConfigGenerator"]
