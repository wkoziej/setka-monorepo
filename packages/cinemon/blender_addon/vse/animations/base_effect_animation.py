# ABOUTME: Base class for all effect animations - provides common interface and keyframe handling
# ABOUTME: Serves as foundation for compositional animation system with required property checking

"""Base class for VSE effect animations."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional

from ..keyframe_helper import KeyframeHelper


class BaseEffectAnimation(ABC):
    """
    Base class for all effect animations.

    Provides common interface and keyframe handling for animations
    that can be composed together in the animation system.
    """

    def __init__(
        self,
        keyframe_helper: KeyframeHelper = None,
        target_strips: Optional[List[str]] = None,
    ):
        """
        Initialize base animation.

        Args:
            keyframe_helper: KeyframeHelper instance (creates new if None)
            target_strips: List of strip names to target (None = all strips)
        """
        self.keyframe_helper = keyframe_helper or KeyframeHelper()
        self.target_strips = target_strips or []

    @abstractmethod
    def apply_to_strip(self, strip, events: List[float], fps: int, **kwargs) -> bool:
        """
        Apply animation to a single strip.

        Args:
            strip: Blender video strip object
            events: List of event times in seconds
            fps: Frames per second
            **kwargs: Additional animation parameters

        Returns:
            True if animation was applied successfully
        """
        raise NotImplementedError

    def should_apply_to_strip(self, strip) -> bool:
        """
        Check if animation should be applied to the given strip.

        Args:
            strip: Blender video strip object

        Returns:
            True if animation should be applied to this strip
        """
        # If no targeting specified, apply to all strips
        if not self.target_strips:
            return True

        # Get strip name from filepath
        strip_name = self._get_strip_name(strip)

        # Check if strip name is in target list
        return strip_name in self.target_strips

    def _get_strip_name(self, strip) -> str:
        """
        Extract strip name from video file path.

        Args:
            strip: Blender video strip object

        Returns:
            Strip name (filename with extension)
        """
        if hasattr(strip, "filepath") and strip.filepath:
            # Extract filename with extension from filepath to match YAML config
            return Path(strip.filepath).name
        elif hasattr(strip, "name") and strip.name:
            # Fallback to strip name
            return strip.name
        else:
            return ""

    @abstractmethod
    def get_required_properties(self) -> List[str]:
        """
        Get list of required strip properties.

        Returns:
            List of property names that strip must have (e.g., 'transform', 'blend_alpha')
        """
        raise NotImplementedError

    def can_apply_to_strip(self, strip) -> bool:
        """
        Check if animation can be applied to given strip.

        Args:
            strip: Blender video strip object

        Returns:
            True if strip has all required properties
        """
        for prop in self.get_required_properties():
            if not hasattr(strip, prop):
                return False
        return True
