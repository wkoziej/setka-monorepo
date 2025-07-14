"""
ABOUTME: EnergyPulseAnimator class - handles energy-driven scale pulsing animations.
ABOUTME: Extracts energy-pulse logic from BlenderVSEConfigurator for better modularity and testability.
"""

from typing import List, Dict

from ..keyframe_helper import KeyframeHelper
from ..constants import AnimationConstants


class EnergyPulseAnimator:
    """Animator for energy-driven scale pulsing on video strips."""

    def __init__(self):
        """Initialize EnergyPulseAnimator with KeyframeHelper."""
        self.keyframe_helper = KeyframeHelper()

    def get_animation_mode(self) -> str:
        """
        Get the animation mode this animator handles.

        Returns:
            str: Animation mode identifier
        """
        return "energy-pulse"

    def can_handle(self, animation_mode: str) -> bool:
        """
        Check if this animator can handle the specified animation mode.

        Args:
            animation_mode: Animation mode to check

        Returns:
            bool: True if this animator can handle the mode
        """
        return animation_mode == "energy-pulse"

    def animate(self, video_strips: List, animation_data: Dict, fps: int) -> bool:
        """
        Apply energy-pulse animation by scaling strips on energy peaks.

        Args:
            video_strips: List of video strips from Blender VSE
            animation_data: Animation data containing energy_peaks events
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

        energy_peaks = animation_data["animation_events"].get("energy_peaks", [])
        if not energy_peaks:
            return True  # No energy peaks to animate

        print(
            f"✓ Animating {len(video_strips)} strips on {len(energy_peaks)} energy peaks at {fps} FPS"
        )

        # Set initial scale to normal
        for strip in video_strips:
            if hasattr(strip, "transform"):
                strip.transform.scale_x = 1.0
                strip.transform.scale_y = 1.0
                self.keyframe_helper.insert_transform_scale_keyframes(
                    strip.name, 1, 1.0, 1.0
                )

        # Animate on energy peak events
        for peak_index, peak_time in enumerate(energy_peaks):
            frame = int(peak_time * fps)

            print(f"  Energy peak {peak_index + 1}: frame {frame}")

            # Scale up on energy peak
            for strip in video_strips:
                if hasattr(strip, "transform"):
                    scale_factor = AnimationConstants.ENERGY_SCALE_FACTOR
                    strip.transform.scale_x = scale_factor
                    strip.transform.scale_y = scale_factor
                    self.keyframe_helper.insert_transform_scale_keyframes(
                        strip.name, frame, scale_factor
                    )

            # Scale back down after peak (1 frame later)
            return_frame = frame + 1
            for strip in video_strips:
                if hasattr(strip, "transform"):
                    strip.transform.scale_x = 1.0  # Back to normal
                    strip.transform.scale_y = 1.0
                    self.keyframe_helper.insert_transform_scale_keyframes(
                        strip.name, return_frame, 1.0
                    )

        print("✓ Energy pulse animation applied successfully")
        return True
