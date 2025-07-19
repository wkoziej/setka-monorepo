"""
ABOUTME: Constants module for Blender VSE - centralizes magic numbers and configuration values.
ABOUTME: Eliminates code duplication and provides single source of truth for system constants.
"""


class BlenderConstants:
    """Constants for basic Blender VSE project configuration."""

    DEFAULT_FPS = 30
    DEFAULT_RESOLUTION_X = 1280
    DEFAULT_RESOLUTION_Y = 720


class AnimationConstants:
    """Constants for Blender VSE animation effects."""

    ENERGY_SCALE_FACTOR = 1.2
    PIP_SCALE_FACTOR = 0.25
    PIP_MARGIN_PERCENT = (
        0.05  # 5% margin from edges - should work with corrected PiP size calculation
    )
    PIP_MARGIN = PIP_MARGIN_PERCENT  # Alias for backwards compatibility
