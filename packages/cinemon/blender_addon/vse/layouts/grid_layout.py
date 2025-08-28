# ABOUTME: Grid layout implementation - arranges video strips in a regular grid pattern
# ABOUTME: Supports configurable rows, columns, and margin between grid cells

"""Grid layout implementation for VSE strips."""

from typing import List, Optional, Tuple

from .base import BaseLayout, LayoutPosition


class GridLayout(BaseLayout):
    """
    Arrange strips in a regular grid pattern.

    Attributes:
        rows: Number of rows in the grid
        cols: Number of columns in the grid
        margin: Margin between cells as fraction of canvas size (0.0-1.0)
    """

    def __init__(self, rows: int = 3, cols: int = 3, margin: float = 0.02):
        """
        Initialize grid layout.

        Args:
            rows: Number of rows (default: 3)
            cols: Number of columns (default: 3)
            margin: Margin between cells as fraction (default: 0.02)
        """
        self.rows = max(1, rows)
        self.cols = max(1, cols)
        self.margin = max(0.0, min(0.5, margin))  # Clamp to 0-0.5

    def calculate_positions(
        self, strip_count: int, resolution: Tuple[int, int]
    ) -> List[LayoutPosition]:
        """
        Calculate grid positions for strips.

        Args:
            strip_count: Number of video strips to position
            resolution: Canvas resolution (width, height)

        Returns:
            List of LayoutPosition objects in grid arrangement
        """
        if strip_count <= 0:
            return []

        positions = []
        canvas_width, canvas_height = resolution

        # Calculate effective area after margins
        margin_x = canvas_width * self.margin
        margin_y = canvas_height * self.margin

        # Calculate cell dimensions
        # Available space divided by number of cells
        cell_width = (canvas_width - margin_x * (self.cols + 1)) / self.cols
        cell_height = (canvas_height - margin_y * (self.rows + 1)) / self.rows

        # Calculate scale to fit strips into cells
        # Assuming original strip size is similar to canvas size
        scale_x = cell_width / canvas_width
        scale_y = cell_height / canvas_height
        scale = min(scale_x, scale_y)  # Maintain aspect ratio

        # Generate positions for each strip
        for i in range(min(strip_count, self.rows * self.cols)):
            row = i // self.cols
            col = i % self.cols

            # Calculate cell center position
            # Start from top-left, move right and down
            # In Blender VSE, (0,0) is center, so we need to offset

            # Calculate position in grid space (0 to canvas_width/height)
            grid_x = margin_x + col * (cell_width + margin_x) + cell_width / 2
            grid_y = canvas_height - (
                margin_y + row * (cell_height + margin_y) + cell_height / 2
            )

            # Convert to VSE coordinates (center is 0,0)
            vse_x = int(grid_x - canvas_width / 2)
            vse_y = int(grid_y - canvas_height / 2)

            positions.append(LayoutPosition(x=vse_x, y=vse_y, scale=scale))

        return positions

    def supports_strip_count(self, count: int) -> bool:
        """
        Check if this layout supports the given number of strips.

        Args:
            count: Number of strips

        Returns:
            True if count fits in the grid
        """
        max_strips = self.rows * self.cols
        return 0 < count <= max_strips
