# ABOUTME: AnimationCompositor - orchestrates layout and animation application for VSE strips
# ABOUTME: Central component that combines layout positioning with multiple independent animations

"""Animation compositor for combining layouts and animations."""

from typing import Dict, List, Tuple

try:
    import bpy
except ImportError:
    # For testing outside Blender
    bpy = None

from .animations.base_effect_animation import BaseEffectAnimation
from .layouts.base import BaseLayout, LayoutPosition


class AnimationCompositor:
    """
    Compositor that combines layouts and animations.

    This is the main orchestrator that:
    1. Applies layout positioning to strips
    2. Extracts events from audio analysis
    3. Applies multiple animations independently

    Example:
        layout = RandomLayout(overlap_allowed=False, seed=42)
        animations = [
            ScaleAnimation(trigger="bass", intensity=0.3),
            ShakeAnimation(trigger="beat", intensity=5.0),
            RotationWobbleAnimation(trigger="beat", wobble_degrees=0.5)
        ]
        compositor = AnimationCompositor(layout, animations)
        compositor.apply(video_strips, audio_analysis, fps)
    """

    def __init__(self, layout: BaseLayout, animations: List[BaseEffectAnimation]):
        """
        Initialize compositor with layout and animations.

        Args:
            layout: Layout instance for positioning strips
            animations: List of animation instances to apply
        """
        self.layout = layout
        self.animations = animations

    def apply(self, video_strips: List, audio_analysis: Dict, fps: int) -> bool:
        """
        Apply layout and animations to strips.

        Args:
            video_strips: List of Blender video strip objects
            audio_analysis: Audio analysis data from beatrix
            fps: Frames per second

        Returns:
            True if successfully applied
        """
        try:
            # 1. Get scene resolution
            resolution = self._get_scene_resolution()

            # 2. Apply layout
            positions = self.layout.calculate_positions(len(video_strips), resolution)
            self._apply_layout(video_strips, positions)

            # 3. Apply animations independently with strip targeting
            for animation in self.animations:
                events = self._extract_events(audio_analysis, animation.trigger)
                if events:  # Only apply if events exist
                    for strip_index, strip in enumerate(video_strips):
                        if animation.should_apply_to_strip(strip):
                            animation.apply_to_strip(
                                strip, events, fps, strip_index=strip_index
                            )

            return True

        except Exception as e:
            print(f"Error in AnimationCompositor: {e}")
            return False

    def _get_scene_resolution(self) -> Tuple[int, int]:
        """
        Get current scene resolution from Blender.

        Returns:
            Tuple of (width, height)

        Raises:
            AttributeError: If scene resolution not available
        """
        if bpy is None:
            # For testing
            return (1920, 1080)

        scene = bpy.context.scene
        width = scene.render.resolution_x
        height = scene.render.resolution_y

        if width is None or height is None:
            raise AttributeError("Scene resolution not available")

        return (int(width), int(height))

    def _apply_layout(self, strips: List, positions: List[LayoutPosition]):
        """
        Apply layout positions to strips.

        Args:
            strips: List of video strips
            positions: List of calculated positions
        """
        for strip, position in zip(strips, positions):
            if hasattr(strip, "transform"):
                strip.transform.offset_x = position.x
                strip.transform.offset_y = position.y
                strip.transform.scale_x = position.scale
                strip.transform.scale_y = position.scale

    def _extract_events(self, audio_analysis: Dict, trigger: str) -> List:
        """
        Extract events from audio analysis based on trigger type.

        Args:
            audio_analysis: Audio analysis data
            trigger: Event trigger type

        Returns:
            List of event times or event objects
        """
        events = audio_analysis.get("animation_events", {})

        # Map triggers to event keys
        trigger_map = {
            "bass": "energy_peaks",
            "beat": "beats",
            "energy_peaks": "energy_peaks",
            "sections": "sections",
        }

        event_key = trigger_map.get(trigger, trigger)
        return events.get(event_key, [])
