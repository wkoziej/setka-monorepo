# ABOUTME: VisibilityAnimation implementation - animates strip visibility using blend_alpha
# ABOUTME: Supports alternating visibility patterns for main cameras based on audio events

"""Visibility animation for addon."""

from typing import List, Optional

from .base_effect_animation import BaseEffectAnimation


class VisibilityAnimation(BaseEffectAnimation):
    """
    Animation that controls strip visibility based on audio events.

    Useful for alternating between main cameras or showing/hiding strips
    on beat events or section changes.

    Attributes:
        trigger: Event type to react to ("beat", "sections", "energy_peaks")
        pattern: Visibility pattern ("alternate", "show", "hide", "pulse")
        duration_frames: How many frames visibility change lasts (for pulse mode)
    """

    def __init__(self,
                 trigger: str = "beat",
                 pattern: str = "alternate",
                 duration_frames: int = 10,
                 target_strips: Optional[List[str]] = None):
        """
        Initialize VisibilityAnimation.

        Args:
            trigger: Event type to trigger animation
            pattern: Visibility pattern:
                - "alternate": Alternate between strips on each event
                - "show": Show strip on event, hide otherwise
                - "hide": Hide strip on event, show otherwise
                - "pulse": Brief visibility pulse on event
            duration_frames: Duration for pulse pattern
            target_strips: List of strip names to target (None = all strips)
        """
        super().__init__(target_strips=target_strips)
        self.trigger = trigger
        self.pattern = pattern
        self.duration_frames = duration_frames
        self._event_counter = 0  # Track events for alternating

    def apply_to_strip(self, strip, events: List[float], fps: int, **kwargs) -> bool:
        """
        Apply visibility animation to strip based on events.

        Args:
            strip: Blender video strip object
            events: List of event times in seconds
            fps: Frames per second
            **kwargs: Additional parameters (may contain 'strip_index')

        Returns:
            True if animation was applied successfully
        """
        print(f"    👁 VisibilityAnimation.apply_to_strip: strip={strip.name}, events={len(events)}, pattern={self.pattern}")

        if not hasattr(strip, 'blend_alpha'):
            print(f"    ❌ Strip {strip.name} has no blend_alpha property")
            return False

        # Get strip index for alternating pattern
        strip_index = kwargs.get('strip_index', 0)

        # Set initial visibility at frame 1
        if self.pattern == "alternate":
            # Even-indexed strips start visible, odd start hidden
            initial_alpha = 1.0 if strip_index % 2 == 0 else 0.0
        else:
            # Other patterns start visible
            initial_alpha = 1.0

        self.keyframe_helper.insert_blend_alpha_keyframe(strip, 1, initial_alpha)

        # Apply visibility changes for each event
        print(f"    🎯 Adding visibility keyframes for {len(events)} events")
        for i, event in enumerate(events):
            # Handle both time values (beats, energy_peaks) and section objects
            if isinstance(event, dict) and 'start' in event:
                event_time = event['start']
            else:
                event_time = event
            frame = int(event_time * fps)

            if self.pattern == "alternate":
                # Alternate visibility: switch which strip is visible on each event
                # Strip 0: visible on even events (0, 2, 4...)
                # Strip 1: visible on odd events (1, 3, 5...)
                if strip_index == 0:
                    target_alpha = 1.0 if (i % 2) == 0 else 0.0
                elif strip_index == 1:
                    target_alpha = 1.0 if (i % 2) == 1 else 0.0
                else:
                    # For strips beyond main cameras, always visible
                    target_alpha = 1.0

            elif self.pattern == "show":
                target_alpha = 1.0

            elif self.pattern == "hide":
                target_alpha = 0.0

            elif self.pattern == "pulse":
                # Brief pulse: show for duration_frames, then hide
                target_alpha = 1.0

            print(f"    📍 Event {i+1}: time={event_time:.2f}s, frame={frame}, strip_index={strip_index}, alpha={target_alpha}")

            self.keyframe_helper.insert_blend_alpha_keyframe(strip, frame, target_alpha)

            # For pulse pattern, add return to previous state
            if self.pattern == "pulse":
                return_frame = frame + self.duration_frames
                return_alpha = 0.0 if target_alpha == 1.0 else 1.0
                self.keyframe_helper.insert_blend_alpha_keyframe(strip, return_frame, return_alpha)
                print(f"    📍 Return frame: {return_frame}, alpha={return_alpha}")

            # Only show first 3 events to avoid spam
            if i >= 2:
                print(f"    📍 ... and {len(events)-3} more events")
                break

        return True

    def get_required_properties(self) -> List[str]:
        """
        Get list of required strip properties.

        Returns:
            List containing 'blend_alpha' property requirement
        """
        return ['blend_alpha']
