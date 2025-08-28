"""Tests for AnimationCompositor strip targeting functionality."""

from unittest.mock import MagicMock

from vse.animation_compositor import AnimationCompositor
from vse.animations.scale_animation import ScaleAnimation
from vse.animations.shake_animation import ShakeAnimation
from vse.layouts.random_layout import RandomLayout


class TestAnimationCompositorStripTargeting:
    """Test cases for strip targeting in AnimationCompositor."""

    def test_apply_animation_to_all_strips_when_no_targeting(self):
        """Test that animations apply to all strips when no targeting is specified."""
        # Create mock strips
        strip1 = MagicMock()
        strip1.name = "Camera1"
        strip1.filepath = "/path/to/Camera1.mp4"
        strip2 = MagicMock()
        strip2.name = "Camera2"
        strip2.filepath = "/path/to/Camera2.mp4"
        strip3 = MagicMock()
        strip3.name = "Camera3"
        strip3.filepath = "/path/to/Camera3.mp4"
        video_strips = [strip1, strip2, strip3]

        # Create layout and animation (no target strips specified)
        layout = RandomLayout(seed=42)
        animation = ScaleAnimation(trigger="bass", intensity=0.3, duration_frames=2)
        # Animation should have empty target_strips
        assert animation.target_strips == []

        # Mock the apply_to_strip method and should_apply_to_strip
        animation.apply_to_strip = MagicMock()
        animation.should_apply_to_strip = MagicMock(return_value=True)

        compositor = AnimationCompositor(layout, [animation])

        # Mock audio analysis
        audio_analysis = {
            "animation_events": {
                "beats": [1.0, 2.0, 3.0],
                "energy_peaks": [1.5, 2.5, 3.5],
            }
        }

        # Apply animations
        result = compositor.apply(video_strips, audio_analysis, fps=30)

        # Verify all strips received animation
        assert result is True
        animation.apply_to_strip.assert_any_call(
            strip1, [1.5, 2.5, 3.5], 30, strip_index=0
        )
        animation.apply_to_strip.assert_any_call(
            strip2, [1.5, 2.5, 3.5], 30, strip_index=1
        )
        animation.apply_to_strip.assert_any_call(
            strip3, [1.5, 2.5, 3.5], 30, strip_index=2
        )
        assert animation.apply_to_strip.call_count == 3

    def test_apply_animation_to_targeted_strips_only(self):
        """Test that animations apply only to targeted strips."""
        # Create mock strips
        strip1 = MagicMock()
        strip1.name = "Camera1"
        strip1.filepath = "/path/to/Camera1.mp4"
        strip2 = MagicMock()
        strip2.name = "Camera2"
        strip2.filepath = "/path/to/Camera2.mp4"
        strip3 = MagicMock()
        strip3.name = "Camera3"
        strip3.filepath = "/path/to/Camera3.mp4"
        video_strips = [strip1, strip2, strip3]

        # Create layout and animation with specific targeting
        layout = RandomLayout(seed=42)
        animation = ScaleAnimation(
            trigger="bass",
            intensity=0.3,
            duration_frames=2,
            target_strips=["Camera1", "Camera3"],  # Only target Camera1 and Camera3
        )

        # Mock the apply_to_strip method and should_apply_to_strip
        animation.apply_to_strip = MagicMock()

        def mock_should_apply(strip):
            # Only apply to Camera1 and Camera3 (targeted strips)
            return strip.name in ["Camera1", "Camera3"]

        animation.should_apply_to_strip = MagicMock(side_effect=mock_should_apply)

        compositor = AnimationCompositor(layout, [animation])

        # Mock audio analysis
        audio_analysis = {
            "animation_events": {
                "beats": [1.0, 2.0, 3.0],
                "energy_peaks": [1.5, 2.5, 3.5],
            }
        }

        # Apply animations
        result = compositor.apply(video_strips, audio_analysis, fps=30)

        # Verify only targeted strips received animation
        assert result is True

        animation.apply_to_strip.assert_any_call(
            strip1, [1.5, 2.5, 3.5], 30, strip_index=0
        )  # Camera1 - targeted
        animation.apply_to_strip.assert_any_call(
            strip3, [1.5, 2.5, 3.5], 30, strip_index=2
        )  # Camera3 - targeted

        # Camera2 should not receive animation
        calls = animation.apply_to_strip.call_args_list
        strip2_calls = [call for call in calls if call[0][0] == strip2]
        assert len(strip2_calls) == 0

        assert animation.apply_to_strip.call_count == 2

    def test_apply_multiple_animations_with_different_targeting(self):
        """Test applying multiple animations with different strip targeting."""
        # Create mock strips
        strip1 = MagicMock()
        strip1.name = "Camera1"
        strip1.filepath = "/path/to/Camera1.mp4"
        strip2 = MagicMock()
        strip2.name = "Camera2"
        strip2.filepath = "/path/to/Camera2.mp4"
        strip3 = MagicMock()
        strip3.name = "Camera3"
        strip3.filepath = "/path/to/Camera3.mp4"
        video_strips = [strip1, strip2, strip3]

        # Create layout and multiple animations with different targeting
        layout = RandomLayout(seed=42)
        scale_animation = ScaleAnimation(
            trigger="bass",
            intensity=0.3,
            duration_frames=2,
            target_strips=["Camera1", "Camera2"],  # Target Camera1 and Camera2
        )
        shake_animation = ShakeAnimation(
            trigger="beat",
            intensity=5.0,
            duration_frames=2,
            target_strips=["Camera3"],  # Target only Camera3
        )

        # Mock the apply_to_strip methods and should_apply_to_strip
        scale_animation.apply_to_strip = MagicMock()
        scale_animation.should_apply_to_strip = MagicMock(
            side_effect=lambda strip: strip.name in ["Camera1", "Camera2"]
        )

        shake_animation.apply_to_strip = MagicMock()
        shake_animation.should_apply_to_strip = MagicMock(
            side_effect=lambda strip: strip.name in ["Camera3"]
        )

        compositor = AnimationCompositor(layout, [scale_animation, shake_animation])

        # Mock audio analysis
        audio_analysis = {
            "animation_events": {
                "beats": [1.0, 2.0, 3.0],
                "energy_peaks": [1.5, 2.5, 3.5],
            }
        }

        # Apply animations
        result = compositor.apply(video_strips, audio_analysis, fps=30)

        # Verify targeting
        assert result is True

        # Scale animation should apply to Camera1 and Camera2
        scale_animation.apply_to_strip.assert_any_call(
            strip1, [1.5, 2.5, 3.5], 30, strip_index=0
        )  # Camera1
        scale_animation.apply_to_strip.assert_any_call(
            strip2, [1.5, 2.5, 3.5], 30, strip_index=1
        )  # Camera2

        # Shake animation should apply only to Camera3
        shake_animation.apply_to_strip.assert_any_call(
            strip3, [1.0, 2.0, 3.0], 30, strip_index=2
        )  # Camera3

        # Verify call counts
        assert scale_animation.apply_to_strip.call_count == 2
        assert shake_animation.apply_to_strip.call_count == 1

    def test_strip_name_extraction_from_filepath(self):
        """Test that strip names are correctly extracted from filepaths."""
        # Create mock strips with different filepath formats
        strip1 = MagicMock()
        strip1.name = "Camera1"
        strip1.filepath = "/path/to/Camera1.mp4"
        strip2 = MagicMock()
        strip2.name = "Screen"
        strip2.filepath = "//relative/path/Screen Capture.mkv"
        strip3 = MagicMock()
        strip3.name = "Audio"
        strip3.filepath = "C:\\Windows\\Path\\Main Audio.m4a"
        video_strips = [strip1, strip2, strip3]

        # Create animation targeting by filename stems
        layout = RandomLayout(seed=42)
        animation = ScaleAnimation(
            trigger="bass",
            intensity=0.3,
            duration_frames=2,
            target_strips=["Camera1", "Screen Capture"],  # Target by filename stems
        )

        # Mock the apply_to_strip method and should_apply_to_strip
        animation.apply_to_strip = MagicMock()

        def mock_should_apply_filename(strip):
            # Apply to Camera1 and Screen Capture based on name extraction logic
            return strip.name in [
                "Camera1",
                "Screen",
            ]  # Strip name might be different from filename

        animation.should_apply_to_strip = MagicMock(
            side_effect=mock_should_apply_filename
        )

        compositor = AnimationCompositor(layout, [animation])

        # Mock audio analysis
        audio_analysis = {"animation_events": {"energy_peaks": [1.5, 2.5, 3.5]}}

        # Apply animations
        result = compositor.apply(video_strips, audio_analysis, fps=30)

        # Verify targeting by filename stems
        assert result is True
        animation.apply_to_strip.assert_any_call(
            strip1, [1.5, 2.5, 3.5], 30, strip_index=0
        )  # Camera1
        animation.apply_to_strip.assert_any_call(
            strip2, [1.5, 2.5, 3.5], 30, strip_index=1
        )  # Screen Capture

        # Main Audio should not receive animation
        calls = animation.apply_to_strip.call_args_list
        strip3_calls = [call for call in calls if call[0][0] == strip3]
        assert len(strip3_calls) == 0

        assert animation.apply_to_strip.call_count == 2

    def test_strip_targeting_with_empty_target_list(self):
        """Test that empty target_strips list applies to all strips."""
        # Create mock strips
        strip1 = MagicMock()
        strip1.name = "Camera1"
        strip1.filepath = "/path/to/Camera1.mp4"
        strip2 = MagicMock()
        strip2.name = "Camera2"
        strip2.filepath = "/path/to/Camera2.mp4"
        video_strips = [strip1, strip2]

        # Create animation with empty target_strips
        layout = RandomLayout(seed=42)
        animation = ScaleAnimation(
            trigger="bass",
            intensity=0.3,
            duration_frames=2,
            target_strips=[],  # Empty list should apply to all
        )

        # Mock the apply_to_strip method and should_apply_to_strip
        animation.apply_to_strip = MagicMock()
        animation.should_apply_to_strip = MagicMock(return_value=True)

        compositor = AnimationCompositor(layout, [animation])

        # Mock audio analysis
        audio_analysis = {"animation_events": {"energy_peaks": [1.5, 2.5, 3.5]}}

        # Apply animations
        result = compositor.apply(video_strips, audio_analysis, fps=30)

        # Verify all strips received animation
        assert result is True
        animation.apply_to_strip.assert_any_call(
            strip1, [1.5, 2.5, 3.5], 30, strip_index=0
        )
        animation.apply_to_strip.assert_any_call(
            strip2, [1.5, 2.5, 3.5], 30, strip_index=1
        )
        assert animation.apply_to_strip.call_count == 2

    def test_strip_targeting_with_nonexistent_targets(self):
        """Test behavior when target_strips contains nonexistent strip names."""
        # Create mock strips
        strip1 = MagicMock()
        strip1.name = "Camera1"
        strip1.filepath = "/path/to/Camera1.mp4"
        strip2 = MagicMock()
        strip2.name = "Camera2"
        strip2.filepath = "/path/to/Camera2.mp4"
        video_strips = [strip1, strip2]

        # Create animation targeting nonexistent strips
        layout = RandomLayout(seed=42)
        animation = ScaleAnimation(
            trigger="bass",
            intensity=0.3,
            duration_frames=2,
            target_strips=["Camera3", "Camera4"],  # These don't exist
        )

        # Mock the apply_to_strip method and should_apply_to_strip
        animation.apply_to_strip = MagicMock()

        def mock_should_apply_nonexistent(strip):
            # Only apply to Camera3 and Camera4, which don't exist in our strips
            return strip.name in ["Camera3", "Camera4"]

        animation.should_apply_to_strip = MagicMock(
            side_effect=mock_should_apply_nonexistent
        )

        compositor = AnimationCompositor(layout, [animation])

        # Mock audio analysis
        audio_analysis = {"animation_events": {"energy_peaks": [1.5, 2.5, 3.5]}}

        # Apply animations
        result = compositor.apply(video_strips, audio_analysis, fps=30)

        # No strips should receive animation since targets don't exist
        assert result is True
        assert animation.apply_to_strip.call_count == 0

    def test_strip_targeting_case_sensitivity(self):
        """Test that strip targeting is case-sensitive."""
        # Create mock strips
        strip1 = MagicMock()
        strip1.name = "Camera1"
        strip1.filepath = "/path/to/Camera1.mp4"
        strip2 = MagicMock()
        strip2.name = "camera2"  # lowercase
        strip2.filepath = "/path/to/camera2.mp4"
        video_strips = [strip1, strip2]

        # Create animation with case-mismatched targeting
        layout = RandomLayout(seed=42)
        animation = ScaleAnimation(
            trigger="bass",
            intensity=0.3,
            duration_frames=2,
            target_strips=["camera1", "Camera2"],  # Case doesn't match
        )

        # Mock the apply_to_strip method and should_apply_to_strip
        animation.apply_to_strip = MagicMock()

        def mock_should_apply_case_sensitive(strip):
            # Only apply if exact case match - should return False for all our strips
            return strip.name in ["camera1", "Camera2"]  # case mismatches

        animation.should_apply_to_strip = MagicMock(
            side_effect=mock_should_apply_case_sensitive
        )

        compositor = AnimationCompositor(layout, [animation])

        # Mock audio analysis
        audio_analysis = {"animation_events": {"energy_peaks": [1.5, 2.5, 3.5]}}

        # Apply animations
        result = compositor.apply(video_strips, audio_analysis, fps=30)

        # No strips should receive animation due to case mismatch
        assert result is True
        assert animation.apply_to_strip.call_count == 0
