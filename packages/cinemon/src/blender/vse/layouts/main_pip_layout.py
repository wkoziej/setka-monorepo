# ABOUTME: MainPipLayout implementation - main cameras fullscreen with corner PiPs
# ABOUTME: Two main strips at center (fullscreen), remaining strips as Picture-in-Picture in corners

"""Main-PiP layout implementation for VSE strips."""

from typing import List, Tuple

from .base import BaseLayout, LayoutPosition


class MainPipLayout(BaseLayout):
    """
    Main-PiP layout positioning strips.

    Layout strategy:
    - First 2 strips: Main cameras at center, fullscreen (scale 1.0)
    - Remaining strips: Picture-in-Picture in corners (scale 0.25)

    Attributes:
        pip_scale: Scale factor for PiP strips
        margin_percent: Margin from edges as percentage (0.0-1.0)
    """

    def __init__(self,
                 pip_scale: float = 0.25,
                 margin_percent: float = 0.1):
        """
        Initialize MainPipLayout.

        Args:
            pip_scale: Scale factor for PiP strips (default: 0.25)
            margin_percent: Margin from edges as percentage (default: 0.1 = 10%)
        """
        self.pip_scale = pip_scale
        self.margin_percent = margin_percent

    def calculate_positions(self, strip_count: int, resolution: Tuple[int, int]) -> List[LayoutPosition]:
        """
        Calculate main-pip positions for all strips.

        Args:
            strip_count: Number of strips to position
            resolution: Canvas resolution (width, height)

        Returns:
            List of LayoutPosition objects
        """
        if strip_count == 0:
            return []

        positions = []
        width, height = resolution
        half_width = width // 2
        half_height = height // 2

        # Calculate corner positions with margin
        margin_x = int(half_width * self.margin_percent)
        margin_y = int(half_height * self.margin_percent)

        # Calculate PiP half-dimensions to account for their size
        pip_half_width = int(half_width * self.pip_scale)
        pip_half_height = int(half_height * self.pip_scale)

        # Position PiP centers so their edges are at margin distance from canvas edges
        top_right_x = half_width - margin_x - pip_half_width
        top_right_y = half_height - margin_y - pip_half_height
        top_left_x = -half_width + margin_x + pip_half_width
        top_left_y = half_height - margin_y - pip_half_height
        bottom_right_x = half_width - margin_x - pip_half_width
        bottom_right_y = -half_height + margin_y + pip_half_height
        bottom_left_x = -half_width + margin_x + pip_half_width
        bottom_left_y = -half_height + margin_y + pip_half_height

        # Debug output
        print("DEBUG MainPipLayout positioning:")
        print(f"  Canvas: {width}x{height}")
        print(f"  Half dimensions: {half_width}x{half_height}")
        print(f"  Margin: {margin_x}x{margin_y} ({self.margin_percent * 100:.1f}%)")
        print(f"  PiP half-size: {pip_half_width}x{pip_half_height} (scale: {self.pip_scale})")
        print(f"  Top-right PiP center: ({top_right_x}, {top_right_y})")
        print(f"  Canvas bounds: left={-half_width}, right={half_width}, top={half_height}, bottom={-half_height}")

        # Corner positions (top-right, top-left, bottom-right, bottom-left)
        corner_positions = [
            (top_right_x, top_right_y),      # Top-right
            (top_left_x, top_left_y),        # Top-left
            (bottom_right_x, bottom_right_y), # Bottom-right
            (bottom_left_x, bottom_left_y),   # Bottom-left
        ]

        for i in range(strip_count):
            if i < 2:
                # First two strips: Main cameras (fullscreen, center)
                positions.append(LayoutPosition(x=0, y=0, scale=1.0))
            else:
                # Remaining strips: Corner PiPs
                corner_index = (i - 2) % len(corner_positions)
                pos_x, pos_y = corner_positions[corner_index]
                positions.append(LayoutPosition(x=pos_x, y=pos_y, scale=self.pip_scale))

        return positions

    def supports_strip_count(self, count: int) -> bool:
        """
        Check if this layout supports the given number of strips.

        Args:
            count: Number of strips

        Returns:
            True if layout can handle this strip count (supports any count > 0)
        """
        return count > 0
