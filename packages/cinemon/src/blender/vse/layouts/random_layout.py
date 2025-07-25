# ABOUTME: RandomLayout implementation - positions video strips randomly on the canvas
# ABOUTME: Supports collision detection, margins, scale ranges, and deterministic seeding

"""Random layout implementation for VSE strips."""

import random
from typing import List, Optional, Tuple

from .base import BaseLayout, LayoutPosition


class RandomLayout(BaseLayout):
    """
    Random positioning of strips on the canvas.

    Attributes:
        overlap_allowed: Whether strips can overlap
        margin: Minimum distance from screen edges (0.0-1.0)
        min_scale: Minimum strip scale
        max_scale: Maximum strip scale
        seed: Random seed for reproducibility
    """

    def __init__(self,
                 overlap_allowed: bool = True,
                 margin: float = 0.05,
                 min_scale: float = 0.3,
                 max_scale: float = 0.8,
                 seed: Optional[int] = None):
        """
        Initialize RandomLayout.

        Args:
            overlap_allowed: Whether strips can overlap (default: True)
            margin: Margin from edges as percentage (default: 0.05 = 5%)
            min_scale: Minimum scale factor (default: 0.3)
            max_scale: Maximum scale factor (default: 0.8)
            seed: Random seed for reproducibility (default: None)
        """
        self.overlap_allowed = overlap_allowed
        self.margin = margin
        self.min_scale = min_scale
        self.max_scale = max_scale
        self.seed = seed

    def calculate_positions(self, strip_count: int, resolution: Tuple[int, int]) -> List[LayoutPosition]:
        """
        Calculate random positions for all strips.

        Args:
            strip_count: Number of strips to position
            resolution: Canvas resolution (width, height)

        Returns:
            List of LayoutPosition objects
        """
        if strip_count == 0:
            return []

        # Reset seed for deterministic results
        if self.seed is not None:
            random.seed(self.seed)

        positions = []
        width, height = resolution
        half_width = width // 2
        half_height = height // 2

        # Calculate margins in pixels
        margin_x = int(half_width * self.margin)
        margin_y = int(half_height * self.margin)

        # Track occupied areas for collision detection
        occupied_areas = []

        for i in range(strip_count):
            # Random scale
            scale = random.uniform(self.min_scale, self.max_scale)

            # Try to find non-overlapping position
            position_found = False
            attempts = 0
            max_attempts = 100

            while attempts < max_attempts:
                # Random position within margins
                x = random.randint(-half_width + margin_x, half_width - margin_x)
                y = random.randint(-half_height + margin_y, half_height - margin_y)

                # Check collisions if overlap not allowed
                if not self.overlap_allowed and occupied_areas:
                    collision = self._check_collision(
                        x, y, scale, occupied_areas, resolution
                    )
                    if collision:
                        attempts += 1
                        continue

                # Position is valid
                position = LayoutPosition(x=x, y=y, scale=scale)
                positions.append(position)

                if not self.overlap_allowed:
                    occupied_areas.append((x, y, scale))

                position_found = True
                break

            # If no valid position found after max attempts, use last generated position
            if not position_found:
                position = LayoutPosition(x=x, y=y, scale=scale)
                positions.append(position)
                if not self.overlap_allowed:
                    occupied_areas.append((x, y, scale))

        return positions

    def _check_collision(self, x: int, y: int, scale: float,
                        occupied_areas: List[Tuple[int, int, float]],
                        resolution: Tuple[int, int]) -> bool:
        """
        Check if position would collide with existing strips.

        Args:
            x: X position to check
            y: Y position to check
            scale: Scale of strip to check
            occupied_areas: List of (x, y, scale) tuples for existing strips
            resolution: Canvas resolution

        Returns:
            True if collision detected
        """
        width, height = resolution

        # Calculate approximate strip dimensions
        strip_half_width = int(width * scale * 0.5)
        strip_half_height = int(height * scale * 0.5)

        for occupied_x, occupied_y, occupied_scale in occupied_areas:
            # Calculate occupied strip dimensions
            occupied_half_width = int(width * occupied_scale * 0.5)
            occupied_half_height = int(height * occupied_scale * 0.5)

            # Check for overlap
            x_overlap = abs(x - occupied_x) < (strip_half_width + occupied_half_width)
            y_overlap = abs(y - occupied_y) < (strip_half_height + occupied_half_height)

            if x_overlap and y_overlap:
                return True

        return False
