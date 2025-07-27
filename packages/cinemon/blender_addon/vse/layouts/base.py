# ABOUTME: Base layout classes - defines abstract interface and data structures for all layout implementations
# ABOUTME: LayoutPosition holds position and scale data, BaseLayout defines the contract for layout calculators

"""Base classes for VSE layout system."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class LayoutPosition:
    """
    Position and scale data for a video strip.

    Attributes:
        x: Horizontal position (0 is center)
        y: Vertical position (0 is center)
        scale: Uniform scale factor (1.0 is original size)
    """

    x: int
    y: int
    scale: float


class BaseLayout(ABC):
    """Abstract base class for all layout implementations."""

    @abstractmethod
    def calculate_positions(
        self, strip_count: int, resolution: Tuple[int, int]
    ) -> List[LayoutPosition]:
        """
        Calculate positions for all strips in the layout.

        Args:
            strip_count: Number of video strips to position
            resolution: Canvas resolution (width, height)

        Returns:
            List of LayoutPosition objects, one for each strip
        """
        raise NotImplementedError

    def supports_strip_count(self, count: int) -> bool:
        """
        Check if this layout supports the given number of strips.

        Args:
            count: Number of strips

        Returns:
            True if layout can handle this strip count
        """
        return count > 0
