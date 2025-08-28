# ABOUTME: Unit tests for GridLayout class - tests grid positioning calculations
# ABOUTME: Verifies correct strip placement in grid pattern with various configurations

"""Unit tests for GridLayout class."""

import sys
from pathlib import Path

import pytest

# Add blender_addon to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "blender_addon"))

from vse.layouts.grid_layout import GridLayout


class TestGridLayout:
    """Test suite for GridLayout class."""

    def test_init_default_values(self):
        """Test GridLayout initialization with default values."""
        layout = GridLayout()
        assert layout.rows == 3
        assert layout.cols == 3
        assert layout.margin == 0.02

    def test_init_custom_values(self):
        """Test GridLayout initialization with custom values."""
        layout = GridLayout(rows=2, cols=4, margin=0.05)
        assert layout.rows == 2
        assert layout.cols == 4
        assert layout.margin == 0.05

    def test_init_clamps_values(self):
        """Test that init properly clamps invalid values."""
        # Negative rows/cols should be clamped to 1
        layout = GridLayout(rows=-1, cols=0, margin=0.6)
        assert layout.rows == 1
        assert layout.cols == 1
        assert layout.margin == 0.5  # Margin clamped to max 0.5

    def test_calculate_positions_empty(self):
        """Test calculate_positions with zero strips."""
        layout = GridLayout()
        positions = layout.calculate_positions(0, (1920, 1080))
        assert positions == []

    def test_calculate_positions_single_strip(self):
        """Test calculate_positions with single strip."""
        layout = GridLayout(rows=3, cols=3, margin=0.02)
        positions = layout.calculate_positions(1, (1920, 1080))

        assert len(positions) == 1
        pos = positions[0]

        # Should be in top-left corner of grid
        assert pos.x < 0  # Left side of canvas
        assert pos.y > 0  # Top side of canvas
        assert 0 < pos.scale < 1  # Scaled down to fit in grid cell

    def test_calculate_positions_full_grid(self):
        """Test calculate_positions with exactly grid size strips."""
        layout = GridLayout(rows=3, cols=3, margin=0.02)
        positions = layout.calculate_positions(9, (1920, 1080))

        assert len(positions) == 9

        # Check that all positions are unique
        position_tuples = [(p.x, p.y) for p in positions]
        assert len(set(position_tuples)) == 9

        # Check scale is consistent
        scales = [p.scale for p in positions]
        assert len(set(scales)) == 1  # All should have same scale

    def test_calculate_positions_overflow(self):
        """Test calculate_positions with more strips than grid cells."""
        layout = GridLayout(rows=2, cols=2, margin=0.02)
        positions = layout.calculate_positions(10, (1920, 1080))

        # Should only return positions for grid size (2x2=4)
        assert len(positions) == 4

    def test_calculate_positions_2x2_grid(self):
        """Test 2x2 grid layout positions."""
        layout = GridLayout(rows=2, cols=2, margin=0.0)
        positions = layout.calculate_positions(4, (1000, 1000))

        assert len(positions) == 4

        # With no margin and 1000x1000 canvas:
        # Each cell is 500x500
        # Centers should be at ±250 from center

        # Top-left
        assert positions[0].x == -250
        assert positions[0].y == 250

        # Top-right
        assert positions[1].x == 250
        assert positions[1].y == 250

        # Bottom-left
        assert positions[2].x == -250
        assert positions[2].y == -250

        # Bottom-right
        assert positions[3].x == 250
        assert positions[3].y == -250

    def test_calculate_positions_with_margin(self):
        """Test that margin properly affects positions."""
        # No margin
        layout_no_margin = GridLayout(rows=2, cols=2, margin=0.0)
        pos_no_margin = layout_no_margin.calculate_positions(4, (1000, 1000))

        # With margin
        layout_with_margin = GridLayout(rows=2, cols=2, margin=0.1)
        pos_with_margin = layout_with_margin.calculate_positions(4, (1000, 1000))

        # Positions should be different
        assert pos_no_margin[0].x != pos_with_margin[0].x
        assert pos_no_margin[0].y != pos_with_margin[0].y

        # Scale should be smaller with margin
        assert pos_with_margin[0].scale < pos_no_margin[0].scale

    def test_calculate_positions_rectangular_grid(self):
        """Test rectangular (non-square) grid layout."""
        layout = GridLayout(rows=2, cols=3, margin=0.02)
        positions = layout.calculate_positions(6, (1920, 1080))

        assert len(positions) == 6

        # Check that we have 2 rows
        y_values = sorted(set(p.y for p in positions))
        assert len(y_values) == 2

        # Check that we have 3 columns
        x_values = sorted(set(p.x for p in positions))
        assert len(x_values) == 3

    def test_supports_strip_count(self):
        """Test supports_strip_count method."""
        layout = GridLayout(rows=2, cols=3)  # Max 6 strips

        assert not layout.supports_strip_count(0)
        assert layout.supports_strip_count(1)
        assert layout.supports_strip_count(6)
        assert not layout.supports_strip_count(7)
        assert not layout.supports_strip_count(-1)

    def test_calculate_positions_different_resolutions(self):
        """Test that layout adapts to different canvas resolutions."""
        layout = GridLayout(rows=3, cols=3, margin=0.02)

        # HD resolution
        pos_hd = layout.calculate_positions(9, (1920, 1080))

        # 4K resolution
        pos_4k = layout.calculate_positions(9, (3840, 2160))

        # Positions should scale with resolution
        assert abs(pos_4k[0].x) > abs(pos_hd[0].x)
        assert abs(pos_4k[0].y) > abs(pos_hd[0].y)

        # But relative positions should be similar
        # (first strip should still be top-left in both cases)
        assert pos_hd[0].x < 0 and pos_4k[0].x < 0
        assert pos_hd[0].y > 0 and pos_4k[0].y > 0

    def test_grid_order_left_to_right_top_to_bottom(self):
        """Test that grid fills left-to-right, top-to-bottom."""
        layout = GridLayout(rows=3, cols=3, margin=0.02)
        positions = layout.calculate_positions(9, (1920, 1080))

        # First row (indices 0,1,2) should have same Y
        assert positions[0].y == positions[1].y == positions[2].y

        # First row should be higher than second row
        assert positions[0].y > positions[3].y

        # First column (indices 0,3,6) should have same X
        assert positions[0].x == positions[3].x == positions[6].x

        # First column should be left of second column
        assert positions[0].x < positions[1].x
