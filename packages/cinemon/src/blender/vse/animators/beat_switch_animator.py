"""
ABOUTME: BeatSwitchAnimator class - handles beat-synchronized video switching animations.
ABOUTME: Extracts beat-switch logic from BlenderVSEConfigurator for better modularity and testability.
"""

from typing import List, Dict

from ..keyframe_helper import KeyframeHelper


class BeatSwitchAnimator:
    """Animator for beat-synchronized video strip switching."""

    def __init__(self):
        """Initialize BeatSwitchAnimator with KeyframeHelper."""
        self.keyframe_helper = KeyframeHelper()

    def get_animation_mode(self) -> str:
        """
        Get the animation mode this animator handles.

        Returns:
            str: Animation mode identifier
        """
        return "beat-switch"

    def can_handle(self, animation_mode: str) -> bool:
        """
        Check if this animator can handle the specified animation mode.

        Args:
            animation_mode: Animation mode to check

        Returns:
            bool: True if this animator can handle the mode
        """
        return animation_mode == "beat-switch"

    def animate(self, video_strips: List, animation_data: Dict, fps: int) -> bool:
        """
        Apply beat-switch animation to video strips.

        Args:
            video_strips: List of video strips from Blender VSE
            animation_data: Animation data containing beat events
            fps: Frames per second for frame calculation

        Returns:
            bool: True if animation was applied successfully
        """
        # Validate inputs
        if fps <= 0:
            return False

        if not video_strips:
            return True  # Nothing to animate

        if not animation_data or "animation_events" not in animation_data:
            return True  # No animation data

        beats = animation_data["animation_events"].get("beats", [])
        if not beats:
            return True  # No beats to animate

        print(
            f"✓ Animating {len(video_strips)} strips on {len(beats)} beats at {fps} FPS"
        )

        # Set initial visibility - first strip visible, others hidden
        for i, strip in enumerate(video_strips):
            alpha_value = 1.0 if i == 0 else 0.0
            strip.blend_alpha = alpha_value
            self.keyframe_helper.insert_blend_alpha_keyframe(strip.name, 1, alpha_value)

        # Animate on beat events
        for beat_index, beat_time in enumerate(beats):
            frame = int(beat_time * fps)
            active_strip_index = beat_index % len(video_strips)

            print(
                f"  Beat {beat_index + 1}: frame {frame}, active strip {active_strip_index}"
            )

            # Set visibility for all strips
            for strip_index, strip in enumerate(video_strips):
                alpha_value = 1.0 if strip_index == active_strip_index else 0.0
                strip.blend_alpha = alpha_value
                self.keyframe_helper.insert_blend_alpha_keyframe(
                    strip.name, frame, alpha_value
                )

        print("✓ Beat switch animation applied successfully")
        return True
