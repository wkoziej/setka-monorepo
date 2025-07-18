"""
ABOUTME: BlenderAnimationEngine class - delegates animations to specialized animator classes.
ABOUTME: Implements delegation pattern to route animation requests to appropriate handlers.
"""

from typing import List, Dict

from .animators.beat_switch_animator import BeatSwitchAnimator
from .animators.energy_pulse_animator import EnergyPulseAnimator
from .animators.multi_pip_animator import MultiPipAnimator
from .animators.compositional_animator import CompositionalAnimator


class BlenderAnimationEngine:
    """Engine that delegates animation requests to specialized animator classes."""

    def __init__(self):
        """Initialize BlenderAnimationEngine with default animators."""
        self.animators = []
        self._load_default_animators()

    def _load_default_animators(self):
        """Load the default animator implementations."""
        self.animators = [
            BeatSwitchAnimator(),
            EnergyPulseAnimator(),
            MultiPipAnimator(),
            CompositionalAnimator(),
        ]

    def get_available_modes(self) -> List[str]:
        """
        Get list of all available animation modes.

        Returns:
            List[str]: List of animation mode identifiers
        """
        modes = []
        for animator in self.animators:
            mode = animator.get_animation_mode()
            if mode not in modes:
                modes.append(mode)
        return modes

    def add_animator(self, animator) -> None:
        """
        Add a custom animator to the engine.

        Args:
            animator: Animator instance that implements required interface

        Raises:
            ValueError: If animator doesn't implement required methods
        """
        required_methods = ["animate", "can_handle", "get_animation_mode"]

        missing_methods = []
        for method in required_methods:
            if not hasattr(animator, method) or not callable(getattr(animator, method)):
                missing_methods.append(method)

        if missing_methods:
            raise ValueError(f"Animator must have {required_methods} methods")

        self.animators.append(animator)

    def remove_animator(self, animator) -> None:
        """
        Remove an animator from the engine.

        Args:
            animator: Animator instance to remove
        """
        if animator in self.animators:
            self.animators.remove(animator)

    def animate(
        self, video_strips: List, animation_data: Dict, fps: int, animation_mode: str
    ) -> bool:
        """
        Delegate animation to appropriate animator based on mode.

        Args:
            video_strips: List of video strips from Blender VSE
            animation_data: Animation data containing events
            fps: Frames per second for frame calculation
            animation_mode: Animation mode identifier

        Returns:
            bool: True if animation was applied successfully
        """
        # Validate inputs
        if fps <= 0:
            return False

        if not animation_mode:
            return False

        # Find animator that can handle this mode
        for animator in self.animators:
            if animator.can_handle(animation_mode):
                print(
                    f"✓ Delegating {animation_mode} animation to {type(animator).__name__}"
                )
                return animator.animate(video_strips, animation_data, fps)

        print(f"✗ No animator found for mode: {animation_mode}")
        return False
