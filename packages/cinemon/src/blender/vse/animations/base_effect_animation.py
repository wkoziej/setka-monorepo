# ABOUTME: Base class for all effect animations - provides common interface and keyframe handling
# ABOUTME: Serves as foundation for compositional animation system with required property checking

"""Base class for VSE effect animations."""

from abc import ABC, abstractmethod
from typing import List

from ..keyframe_helper import KeyframeHelper


class BaseEffectAnimation(ABC):
    """
    Base class for all effect animations.
    
    Provides common interface and keyframe handling for animations
    that can be composed together in the animation system.
    """
    
    def __init__(self, keyframe_helper: KeyframeHelper = None):
        """
        Initialize base animation.
        
        Args:
            keyframe_helper: KeyframeHelper instance (creates new if None)
        """
        self.keyframe_helper = keyframe_helper or KeyframeHelper()
    
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