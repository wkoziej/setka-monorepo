"""
ABOUTME: Layout manager module for Blender VSE - handles PiP positioning and layout calculations.
ABOUTME: Centralizes layout logic for different video arrangement patterns and multi-camera setups.
"""

from typing import Dict, List, Tuple

from .constants import AnimationConstants, BlenderConstants


class BlenderLayoutManager:
    """Manager class for Blender VSE layout calculations and positioning."""

    def __init__(self, resolution_x: int = None, resolution_y: int = None):
        """
        Initialize layout manager with resolution parameters.

        Args:
            resolution_x: Canvas width in pixels. Defaults to BlenderConstants.DEFAULT_RESOLUTION_X
            resolution_y: Canvas height in pixels. Defaults to BlenderConstants.DEFAULT_RESOLUTION_Y
        """
        self.resolution_x = resolution_x or BlenderConstants.DEFAULT_RESOLUTION_X
        self.resolution_y = resolution_y or BlenderConstants.DEFAULT_RESOLUTION_Y

    def calculate_pip_positions(self) -> List[Dict]:
        """
        Calculate PiP positions for 2x2 grid layout.

        Returns:
            List[Dict]: List of position dictionaries with x, y, width, height
        """
        # Calculate quadrant dimensions
        pip_width = self.resolution_x // 2
        pip_height = self.resolution_y // 2

        positions = [
            # Top-left
            {"x": 0, "y": pip_height, "width": pip_width, "height": pip_height},
            # Top-right
            {"x": pip_width, "y": pip_height, "width": pip_width, "height": pip_height},
            # Bottom-left
            {"x": 0, "y": 0, "width": pip_width, "height": pip_height},
            # Bottom-right
            {"x": pip_width, "y": 0, "width": pip_width, "height": pip_height},
        ]

        return positions

    def calculate_multi_pip_layout(
        self, strip_count: int
    ) -> List[Tuple[int, int, float]]:
        """
        Calculate Multi-PiP layout positions based on scene resolution.

        In Blender VSE, (0,0) is the center of the screen.
        First two strips are main cameras (fullscreen, center).
        Remaining strips are corner PiPs with reduced scale.

        Args:
            strip_count: Number of video strips

        Returns:
            List of (pos_x, pos_y, scale) tuples for each strip
        """
        if strip_count <= 0:
            return []

        layout = []

        # PiP settings
        pip_scale = AnimationConstants.PIP_SCALE_FACTOR
        corner_positions = self.get_corner_positions()

        for i in range(strip_count):
            if i < 2:
                # First two strips: Main cameras (fullscreen, center)
                layout.append((0, 0, 1.0))
            else:
                # Remaining strips: Corner PiPs
                corner_index = (i - 2) % len(corner_positions)
                pos_x, pos_y = corner_positions[corner_index]
                layout.append((pos_x, pos_y, pip_scale))

        return layout

    def get_corner_positions(
        self, margin_percent: float = None
    ) -> List[Tuple[int, int]]:
        """
        Get corner positions with proportional margin from edges.

        Args:
            margin_percent: Margin as percentage of resolution (0.0-1.0).
                          Defaults to AnimationConstants.PIP_MARGIN_PERCENT

        Returns:
            List of (x, y) tuples for corner positions
        """
        if margin_percent is None:
            margin_percent = AnimationConstants.PIP_MARGIN_PERCENT

        # Calculate half dimensions for center-based coordinates
        half_width = self.resolution_x // 2
        half_height = self.resolution_y // 2

        # Calculate proportional margins based on resolution
        margin_x = int(half_width * margin_percent)
        margin_y = int(half_height * margin_percent)

        # Account for PiP size with resolution-aware scaling
        # PiP videos are typically 640x480, project is 740x554
        # Resolution-aware scaling: min(740/640, 554/480) = 1.15
        # Effective PiP scale: 0.25 * 1.15 = 0.29 (not 0.25!)
        effective_pip_scale = (
            AnimationConstants.PIP_SCALE_FACTOR * 1.15
        )  # Account for typical resolution scaling
        pip_half_width = int(half_width * effective_pip_scale)
        pip_half_height = int(half_height * effective_pip_scale)

        # Corner positions relative to center (0,0)
        # Position PiP centers so their edges are at margin distance from canvas edges
        top_right_x = half_width - margin_x - pip_half_width
        top_right_y = half_height - margin_y - pip_half_height

        print("DEBUG PiP positioning:")
        print(f"  Canvas: {self.resolution_x}x{self.resolution_y}")
        print(f"  Half dimensions: {half_width}x{half_height}")
        print(f"  Margin: {margin_x:.1f}x{margin_y:.1f} ({margin_percent * 100:.1f}%)")
        print(
            f"  PiP half-size: {pip_half_width:.1f}x{pip_half_height:.1f} (effective scale: {effective_pip_scale:.3f})"
        )
        print(f"  Top-right PiP center: ({top_right_x:.1f}, {top_right_y:.1f})")
        print(
            f"  Top-right PiP edges: left={top_right_x - pip_half_width:.1f}, right={top_right_x + pip_half_width:.1f}"
        )
        print(f"  Canvas bounds: left={-half_width}, right={half_width}")

        corners = [
            (top_right_x, top_right_y),  # Top-right
            (-top_right_x, top_right_y),  # Top-left
            (-top_right_x, -top_right_y),  # Bottom-left
            (top_right_x, -top_right_y),  # Bottom-right
        ]

        return corners

    def get_center_position(self) -> Tuple[int, int]:
        """
        Get center position coordinates.

        Returns:
            Tuple[int, int]: Center position (0, 0)
        """
        return (0, 0)
