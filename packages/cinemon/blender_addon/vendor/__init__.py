# ABOUTME: Vendor package initialization for Blender addon dependencies
# ABOUTME: Provides access to vendored PyYAML library without external dependencies

"""Vendor package for Cinemon Blender addon."""

# Make yaml available from vendor
from . import yaml

__all__ = ['yaml']