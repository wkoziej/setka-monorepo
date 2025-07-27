"""
ABOUTME: Tests for Blender VSE constants module - validates extracted magic numbers.
ABOUTME: TDD approach - tests written first to define expected behavior and values.
"""

import sys
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from vse.constants import AnimationConstants, BlenderConstants


class TestBlenderConstants:
    """Test suite for BlenderConstants class."""

    def test_default_fps_exists_and_is_positive(self):
        """Default FPS should be a positive integer."""
        assert hasattr(BlenderConstants, "DEFAULT_FPS")
        assert isinstance(BlenderConstants.DEFAULT_FPS, int)
        assert BlenderConstants.DEFAULT_FPS > 0

    def test_default_fps_value(self):
        """Default FPS should be 30 (current system default)."""
        assert BlenderConstants.DEFAULT_FPS == 30

    def test_default_resolution_x_exists_and_valid(self):
        """Default resolution X should be a positive integer."""
        assert hasattr(BlenderConstants, "DEFAULT_RESOLUTION_X")
        assert isinstance(BlenderConstants.DEFAULT_RESOLUTION_X, int)
        assert BlenderConstants.DEFAULT_RESOLUTION_X > 0

    def test_default_resolution_x_value(self):
        """Default resolution X should be 1280 (current system default)."""
        assert BlenderConstants.DEFAULT_RESOLUTION_X == 1280

    def test_default_resolution_y_exists_and_valid(self):
        """Default resolution Y should be a positive integer."""
        assert hasattr(BlenderConstants, "DEFAULT_RESOLUTION_Y")
        assert isinstance(BlenderConstants.DEFAULT_RESOLUTION_Y, int)
        assert BlenderConstants.DEFAULT_RESOLUTION_Y > 0

    def test_default_resolution_y_value(self):
        """Default resolution Y should be 720 (current system default)."""
        assert BlenderConstants.DEFAULT_RESOLUTION_Y == 720

    def test_resolution_aspect_ratio(self):
        """Resolution should maintain 16:9 aspect ratio."""
        aspect_ratio = (
            BlenderConstants.DEFAULT_RESOLUTION_X
            / BlenderConstants.DEFAULT_RESOLUTION_Y
        )
        expected_ratio = 16 / 9
        assert abs(aspect_ratio - expected_ratio) < 0.01


class TestAnimationConstants:
    """Test suite for AnimationConstants class."""

    def test_energy_scale_factor_exists_and_valid(self):
        """Energy scale factor should be a positive float greater than 1.0."""
        assert hasattr(AnimationConstants, "ENERGY_SCALE_FACTOR")
        assert isinstance(AnimationConstants.ENERGY_SCALE_FACTOR, (int, float))
        assert AnimationConstants.ENERGY_SCALE_FACTOR > 1.0

    def test_energy_scale_factor_value(self):
        """Energy scale factor should be 1.2 (current system value)."""
        assert AnimationConstants.ENERGY_SCALE_FACTOR == 1.2

    def test_pip_scale_factor_exists_and_valid(self):
        """PiP scale factor should be a positive float for corner scaling."""
        assert hasattr(AnimationConstants, "PIP_SCALE_FACTOR")
        assert isinstance(AnimationConstants.PIP_SCALE_FACTOR, (int, float))
        assert AnimationConstants.PIP_SCALE_FACTOR > 0.0

    def test_pip_scale_factor_value(self):
        """PiP scale factor should be 0.25 (small corner PiP scale)."""
        assert AnimationConstants.PIP_SCALE_FACTOR == 0.25

    def test_pip_margin_exists_and_valid(self):
        """PiP margin should be a positive float (percentage)."""
        assert hasattr(AnimationConstants, "PIP_MARGIN")
        assert isinstance(AnimationConstants.PIP_MARGIN, float)
        assert AnimationConstants.PIP_MARGIN > 0

    def test_pip_margin_value(self):
        """PiP margin should be 0.05 (5% margin from edges)."""
        assert AnimationConstants.PIP_MARGIN == 0.05

    def test_scale_factors_are_reasonable(self):
        """Scale factors should be within reasonable bounds for UI animations."""
        assert AnimationConstants.ENERGY_SCALE_FACTOR <= 2.0  # Not too dramatic
        assert AnimationConstants.PIP_SCALE_FACTOR <= 1.5  # Subtle effect for PiPs

        # Energy effect should be more dramatic than PiP effect
        assert (
            AnimationConstants.ENERGY_SCALE_FACTOR > AnimationConstants.PIP_SCALE_FACTOR
        )


class TestConstantsIntegration:
    """Integration tests for constants classes."""

    def test_constants_are_immutable_like(self):
        """Constants should behave like immutable values (class attributes, not instance)."""
        # Should be accessible from class, not requiring instantiation
        assert BlenderConstants.DEFAULT_FPS == 30
        assert AnimationConstants.ENERGY_SCALE_FACTOR == 1.2

    def test_all_expected_constants_exist(self):
        """All constants identified in current codebase should be present."""
        required_blender_constants = [
            "DEFAULT_FPS",
            "DEFAULT_RESOLUTION_X",
            "DEFAULT_RESOLUTION_Y",
        ]
        required_animation_constants = [
            "ENERGY_SCALE_FACTOR",
            "PIP_SCALE_FACTOR",
            "PIP_MARGIN",
        ]

        for const in required_blender_constants:
            assert hasattr(BlenderConstants, const), f"Missing BlenderConstants.{const}"

        for const in required_animation_constants:
            assert hasattr(AnimationConstants, const), (
                f"Missing AnimationConstants.{const}"
            )

    def test_constants_can_be_used_in_calculations(self):
        """Constants should be usable in typical calculations."""
        # Test resolution calculation
        total_pixels = (
            BlenderConstants.DEFAULT_RESOLUTION_X
            * BlenderConstants.DEFAULT_RESOLUTION_Y
        )
        assert total_pixels == 921600  # 1280 * 720

        # Test animation calculation
        scaled_energy = 100 * AnimationConstants.ENERGY_SCALE_FACTOR
        assert scaled_energy == 120.0

        # Test margin calculation (percentage-based)
        margin_pixels = (
            BlenderConstants.DEFAULT_RESOLUTION_X * AnimationConstants.PIP_MARGIN
        )
        corner_x = BlenderConstants.DEFAULT_RESOLUTION_X // 2 - margin_pixels
        assert corner_x == 576.0  # 640 - (1280 * 0.05) = 640 - 64 = 576
