"""
ABOUTME: Tests for Blender VSE layout manager module - validates PiP positioning and layout calculations.
ABOUTME: TDD approach - tests written first to define expected layout manager behavior.
"""

from pathlib import Path
import sys

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.blender_vse.layout_manager import BlenderLayoutManager
from core.blender_vse.constants import AnimationConstants


class TestBlenderLayoutManagerBasic:
    """Test basic LayoutManager functionality."""

    def test_layout_manager_initialization(self):
        """LayoutManager should initialize with resolution parameters."""
        manager = BlenderLayoutManager(1280, 720)

        assert manager.resolution_x == 1280
        assert manager.resolution_y == 720

    def test_layout_manager_default_resolution(self):
        """LayoutManager should use default resolution when not specified."""
        manager = BlenderLayoutManager()

        # Should use BlenderConstants defaults
        assert manager.resolution_x == 1280  # DEFAULT_RESOLUTION_X
        assert manager.resolution_y == 720  # DEFAULT_RESOLUTION_Y

    def test_layout_manager_has_required_methods(self):
        """LayoutManager should have all required methods for layout calculations."""
        manager = BlenderLayoutManager()

        required_methods = [
            "calculate_pip_positions",
            "calculate_multi_pip_layout",
            "get_corner_positions",
            "get_center_position",
        ]

        for method in required_methods:
            assert hasattr(manager, method), f"Missing method: {method}"
            assert callable(getattr(manager, method)), (
                f"Method {method} is not callable"
            )


class TestPipPositionsCalculation:
    """Test PiP positions calculation (2x2 grid)."""

    def test_calculate_pip_positions_2x2_grid(self):
        """Should calculate correct 2x2 grid positions."""
        manager = BlenderLayoutManager(1280, 720)

        positions = manager.calculate_pip_positions()

        # Should return 4 positions for 2x2 grid
        assert len(positions) == 4

        # Each position should have required keys
        for pos in positions:
            assert isinstance(pos, dict)
            required_keys = ["x", "y", "width", "height"]
            for key in required_keys:
                assert key in pos, f"Missing key: {key}"
                assert isinstance(pos[key], int), f"Key {key} should be integer"

    def test_calculate_pip_positions_dimensions(self):
        """Should calculate correct dimensions for 2x2 grid."""
        manager = BlenderLayoutManager(1280, 720)

        positions = manager.calculate_pip_positions()

        # Each quadrant should be half the resolution
        expected_width = 1280 // 2  # 640
        expected_height = 720 // 2  # 360

        for pos in positions:
            assert pos["width"] == expected_width
            assert pos["height"] == expected_height

    def test_calculate_pip_positions_coordinates(self):
        """Should calculate correct coordinates for 2x2 grid."""
        manager = BlenderLayoutManager(1280, 720)

        positions = manager.calculate_pip_positions()

        # Positions should cover the four quadrants
        # Top-left, Top-right, Bottom-left, Bottom-right
        expected_positions = [
            {"x": 0, "y": 360, "width": 640, "height": 360},  # Top-left
            {"x": 640, "y": 360, "width": 640, "height": 360},  # Top-right
            {"x": 0, "y": 0, "width": 640, "height": 360},  # Bottom-left
            {"x": 640, "y": 0, "width": 640, "height": 360},  # Bottom-right
        ]

        assert positions == expected_positions

    def test_calculate_pip_positions_different_resolution(self):
        """Should calculate positions correctly for different resolutions."""
        manager = BlenderLayoutManager(1920, 1080)

        positions = manager.calculate_pip_positions()

        # Should adapt to new resolution
        expected_width = 1920 // 2  # 960
        expected_height = 1080 // 2  # 540

        for pos in positions:
            assert pos["width"] == expected_width
            assert pos["height"] == expected_height


class TestMultiPipLayoutCalculation:
    """Test Multi-PiP layout calculation (main cameras + corner PiPs)."""

    def test_calculate_multi_pip_layout_basic(self):
        """Should calculate Multi-PiP layout with main cameras and corner PiPs."""
        manager = BlenderLayoutManager(1280, 720)

        layout = manager.calculate_multi_pip_layout(4)  # 4 video strips

        # Should return list of (pos_x, pos_y, scale) tuples
        assert len(layout) == 4

        for position in layout:
            assert isinstance(position, tuple)
            assert len(position) == 3  # (pos_x, pos_y, scale)
            pos_x, pos_y, scale = position
            assert isinstance(pos_x, int)
            assert isinstance(pos_y, int)
            assert isinstance(scale, float)

    def test_calculate_multi_pip_layout_main_cameras(self):
        """First two strips should be main cameras (fullscreen, center)."""
        manager = BlenderLayoutManager(1280, 720)

        layout = manager.calculate_multi_pip_layout(4)

        # First two should be main cameras at center (0,0) with scale 1.0
        main_cam1 = layout[0]
        main_cam2 = layout[1]

        assert main_cam1 == (0, 0, 1.0)  # Fullscreen at center
        assert main_cam2 == (0, 0, 1.0)  # Fullscreen at center

    def test_calculate_multi_pip_layout_corner_pips(self):
        """Remaining strips should be corner PiPs with appropriate positioning."""
        manager = BlenderLayoutManager(1280, 720)

        layout = manager.calculate_multi_pip_layout(4)

        # Third and fourth should be corner PiPs
        corner_pip1 = layout[2]
        corner_pip2 = layout[3]

        # Should be scaled down (0.25 = 25% size)
        assert corner_pip1[2] == 0.25
        assert corner_pip2[2] == 0.25

        # Should be positioned in corners (not center)
        assert corner_pip1[:2] != (0, 0)
        assert corner_pip2[:2] != (0, 0)

    def test_calculate_multi_pip_layout_corner_positions(self):
        """Corner PiPs should be positioned with proper margin from edges."""
        manager = BlenderLayoutManager(1280, 720)

        layout = manager.calculate_multi_pip_layout(4)

        # Get corner positions
        corner_pip1_pos = layout[2][:2]  # (pos_x, pos_y)
        corner_pip2_pos = layout[3][:2]  # (pos_x, pos_y)

        # Should use AnimationConstants.PIP_MARGIN (160)
        margin = AnimationConstants.PIP_MARGIN
        half_width = 1280 // 2  # 640
        half_height = 720 // 2  # 360

        # Expected corner positions relative to center (0,0)
        expected_top_right = (half_width - margin, half_height - margin)  # (480, 200)
        expected_top_left = (
            -(half_width - margin),
            half_height - margin,
        )  # (-480, 200)

        expected_positions = [expected_top_right, expected_top_left]

        assert corner_pip1_pos in expected_positions
        assert corner_pip2_pos in expected_positions

    def test_calculate_multi_pip_layout_variable_strip_count(self):
        """Should handle different numbers of strips correctly."""
        manager = BlenderLayoutManager(1280, 720)

        # Test with different strip counts
        for strip_count in [1, 2, 3, 4, 5, 6]:
            layout = manager.calculate_multi_pip_layout(strip_count)
            assert len(layout) == strip_count

            # First two should always be main cameras (if they exist)
            if strip_count >= 1:
                assert layout[0] == (0, 0, 1.0)
            if strip_count >= 2:
                assert layout[1] == (0, 0, 1.0)

            # Rest should be corner PiPs with 0.25 scale
            for i in range(2, strip_count):
                assert layout[i][2] == 0.25  # PiP scale


class TestCornerPositionsUtility:
    """Test corner positions utility method."""

    def test_get_corner_positions_basic(self):
        """Should return 4 corner positions with margin."""
        manager = BlenderLayoutManager(1280, 720)

        corners = manager.get_corner_positions()

        # Should return 4 corner positions
        assert len(corners) == 4

        # Each corner should have x, y coordinates
        for corner in corners:
            assert isinstance(corner, tuple)
            assert len(corner) == 2  # (x, y)
            assert isinstance(corner[0], int)
            assert isinstance(corner[1], int)

    def test_get_corner_positions_coordinates(self):
        """Should calculate correct corner coordinates with margin."""
        manager = BlenderLayoutManager(1280, 720)

        corners = manager.get_corner_positions()

        margin = AnimationConstants.PIP_MARGIN  # 160
        half_width = 640  # 1280 // 2
        half_height = 360  # 720 // 2

        expected_corners = [
            (half_width - margin, half_height - margin),  # Top-right (480, 200)
            (-(half_width - margin), half_height - margin),  # Top-left (-480, 200)
            (
                -(half_width - margin),
                -(half_height - margin),
            ),  # Bottom-left (-480, -200)
            (half_width - margin, -(half_height - margin)),  # Bottom-right (480, -200)
        ]

        assert corners == expected_corners

    def test_get_corner_positions_custom_margin(self):
        """Should accept custom margin parameter."""
        manager = BlenderLayoutManager(1280, 720)

        custom_margin = 100
        corners = manager.get_corner_positions(margin=custom_margin)

        half_width = 640
        half_height = 360

        expected_corners = [
            (half_width - custom_margin, half_height - custom_margin),  # (540, 260)
            (-(half_width - custom_margin), half_height - custom_margin),  # (-540, 260)
            (
                -(half_width - custom_margin),
                -(half_height - custom_margin),
            ),  # (-540, -260)
            (half_width - custom_margin, -(half_height - custom_margin)),  # (540, -260)
        ]

        assert corners == expected_corners


class TestCenterPositionUtility:
    """Test center position utility method."""

    def test_get_center_position(self):
        """Should return center position (0, 0)."""
        manager = BlenderLayoutManager(1280, 720)

        center = manager.get_center_position()

        assert center == (0, 0)

    def test_get_center_position_independent_of_resolution(self):
        """Center should always be (0, 0) regardless of resolution."""
        manager1 = BlenderLayoutManager(1920, 1080)
        manager2 = BlenderLayoutManager(640, 480)

        assert manager1.get_center_position() == (0, 0)
        assert manager2.get_center_position() == (0, 0)


class TestLayoutManagerIntegration:
    """Test integration patterns and edge cases."""

    def test_layout_manager_backwards_compatibility(self):
        """Should provide same results as original _calculate_pip_positions method."""
        manager = BlenderLayoutManager(1280, 720)

        # Original method from blender_vse_script.py
        positions = manager.calculate_pip_positions()

        # Should match expected original behavior
        assert len(positions) == 4
        assert positions[0] == {"x": 0, "y": 360, "width": 640, "height": 360}
        assert positions[1] == {"x": 640, "y": 360, "width": 640, "height": 360}
        assert positions[2] == {"x": 0, "y": 0, "width": 640, "height": 360}
        assert positions[3] == {"x": 640, "y": 0, "width": 640, "height": 360}

    def test_layout_manager_multi_pip_backwards_compatibility(self):
        """Should provide same results as original _calculate_multi_pip_layout method."""
        manager = BlenderLayoutManager(1280, 720)

        # Test with 4 strips (typical scenario)
        layout = manager.calculate_multi_pip_layout(4)

        # Should match original layout calculation
        assert layout[0] == (0, 0, 1.0)  # video1: main camera
        assert layout[1] == (0, 0, 1.0)  # video2: main camera
        assert layout[2][2] == 0.25  # video3: corner PiP scale
        assert layout[3][2] == 0.25  # video4: corner PiP scale

    def test_layout_manager_error_handling(self):
        """Should handle edge cases gracefully."""
        manager = BlenderLayoutManager(1280, 720)

        # Test with zero strips
        layout = manager.calculate_multi_pip_layout(0)
        assert layout == []

        # Test with negative strips (should handle gracefully)
        layout = manager.calculate_multi_pip_layout(-1)
        assert layout == []

    def test_layout_manager_large_strip_counts(self):
        """Should handle large strip counts (beyond typical use)."""
        manager = BlenderLayoutManager(1280, 720)

        # Test with more strips than corners
        layout = manager.calculate_multi_pip_layout(10)
        assert len(layout) == 10

        # First 2 should still be main cameras
        assert layout[0] == (0, 0, 1.0)
        assert layout[1] == (0, 0, 1.0)

        # Rest should be corner PiPs (cycling through available positions)
        for i in range(2, 10):
            assert layout[i][2] == 0.25
