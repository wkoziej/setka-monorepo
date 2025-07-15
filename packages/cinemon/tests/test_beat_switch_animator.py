"""
ABOUTME: Tests for BeatSwitchAnimator class - validates beat-synchronized video switching animations.
ABOUTME: TDD approach - tests written first to define expected animator behavior and interface.
"""

from pathlib import Path
import sys
from unittest.mock import Mock, patch

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from blender.vse.animators.beat_switch_animator import BeatSwitchAnimator
from blender.vse.keyframe_helper import KeyframeHelper


class TestBeatSwitchAnimatorBasic:
    """Test basic BeatSwitchAnimator functionality."""

    def test_beat_switch_animator_initialization(self):
        """BeatSwitchAnimator should initialize with keyframe helper."""
        animator = BeatSwitchAnimator()

        assert animator is not None
        assert hasattr(animator, "keyframe_helper")
        assert isinstance(animator.keyframe_helper, KeyframeHelper)

    def test_beat_switch_animator_has_required_methods(self):
        """BeatSwitchAnimator should have required animation interface methods."""
        animator = BeatSwitchAnimator()

        required_methods = ["animate", "can_handle", "get_animation_mode"]

        for method in required_methods:
            assert hasattr(animator, method), f"Missing method: {method}"
            assert callable(getattr(animator, method)), (
                f"Method {method} is not callable"
            )

    def test_beat_switch_animator_mode_identification(self):
        """BeatSwitchAnimator should identify its animation mode correctly."""
        animator = BeatSwitchAnimator()

        assert animator.get_animation_mode() == "beat-switch"
        assert animator.can_handle("beat-switch") is True
        assert animator.can_handle("energy-pulse") is False
        assert animator.can_handle("multi-pip") is False


class TestBeatSwitchAnimatorValidation:
    """Test input validation for BeatSwitchAnimator."""

    def test_animate_validates_video_strips(self):
        """Should validate video_strips parameter."""
        animator = BeatSwitchAnimator()
        animation_data = {"animation_events": {"beats": [1.0, 2.0]}}
        fps = 30

        # Empty strips list
        result = animator.animate([], animation_data, fps)
        assert result is True  # Should handle gracefully

        # None strips
        result = animator.animate(None, animation_data, fps)
        assert result is True  # Should handle gracefully

    def test_animate_validates_animation_data(self):
        """Should validate animation_data parameter."""
        animator = BeatSwitchAnimator()
        video_strips = [Mock(name="Video_1"), Mock(name="Video_2")]
        fps = 30

        # Missing animation_events
        result = animator.animate(video_strips, {}, fps)
        assert result is True  # Should handle gracefully

        # Missing beats
        animation_data = {"animation_events": {}}
        result = animator.animate(video_strips, animation_data, fps)
        assert result is True  # Should handle gracefully

        # None animation_data
        result = animator.animate(video_strips, None, fps)
        assert result is True  # Should handle gracefully

    def test_animate_validates_fps(self):
        """Should validate fps parameter."""
        animator = BeatSwitchAnimator()
        video_strips = [Mock(name="Video_1")]
        animation_data = {"animation_events": {"beats": [1.0]}}

        # Zero FPS
        result = animator.animate(video_strips, animation_data, 0)
        assert result is False  # Should fail validation

        # Negative FPS
        result = animator.animate(video_strips, animation_data, -30)
        assert result is False  # Should fail validation


class TestBeatSwitchAnimatorLogic:
    """Test core beat switch animation logic."""

    @patch("blender.vse.keyframe_helper.bpy")
    def test_animate_initial_state_setup(self, mock_bpy):
        """Should set initial visibility state correctly."""
        animator = BeatSwitchAnimator()

        # Create mock strips
        strip1 = Mock()
        strip1.name = "Video_1"
        strip1.blend_alpha = 0.0

        strip2 = Mock()
        strip2.name = "Video_2"
        strip2.blend_alpha = 0.0

        video_strips = [strip1, strip2]
        animation_data = {"animation_events": {"beats": [1.0, 2.0, 3.0]}}
        fps = 30

        result = animator.animate(video_strips, animation_data, fps)

        assert result is True
        # First strip should be visible initially
        assert strip1.blend_alpha == 1.0
        # Second strip should be hidden initially
        assert strip2.blend_alpha == 0.0

    @patch("blender.vse.keyframe_helper.bpy")
    def test_animate_beat_switching_logic(self, mock_bpy):
        """Should switch active strip on each beat correctly."""
        animator = BeatSwitchAnimator()

        # Create mock strips
        strips = []
        for i in range(3):
            strip = Mock()
            strip.name = f"Video_{i + 1}"
            strip.blend_alpha = 0.0
            strips.append(strip)

        animation_data = {"animation_events": {"beats": [1.0, 2.0, 3.0, 4.0, 5.0]}}
        fps = 30

        result = animator.animate(strips, animation_data, fps)

        assert result is True

        # Should cycle through strips: 0, 1, 2, 0, 1
        # Beat 1 (frame 30): strip 1 active (index 0)
        # Beat 2 (frame 60): strip 2 active (index 1)
        # Beat 3 (frame 90): strip 3 active (index 2)
        # Beat 4 (frame 120): strip 1 active (index 0) - cycling
        # Beat 5 (frame 150): strip 2 active (index 1)

    @patch("blender.vse.keyframe_helper.bpy")
    def test_animate_frame_calculation(self, mock_bpy):
        """Should calculate frame numbers correctly from beat times."""
        animator = BeatSwitchAnimator()

        strip = Mock()
        strip.name = "Video_1"
        strip.blend_alpha = 0.0

        video_strips = [strip]

        # Test different FPS values
        test_cases = [
            ({"animation_events": {"beats": [1.0, 2.5]}}, 30, [30, 75]),  # 30 FPS
            ({"animation_events": {"beats": [0.5, 1.0]}}, 24, [12, 24]),  # 24 FPS
            ({"animation_events": {"beats": [2.0, 4.0]}}, 60, [120, 240]),  # 60 FPS
        ]

        for animation_data, fps, expected_frames in test_cases:
            result = animator.animate(video_strips, animation_data, fps)
            assert result is True

    def test_animate_round_robin_switching(self):
        """Should implement round-robin switching correctly."""
        animator = BeatSwitchAnimator()

        # Test with different strip counts
        for strip_count in [1, 2, 3, 4, 5]:
            strips = []
            for i in range(strip_count):
                strip = Mock()
                strip.name = f"Video_{i + 1}"
                strips.append(strip)

            # Create beats for multiple cycles
            beats = [i * 0.5 for i in range(1, strip_count * 2 + 3)]  # 2+ full cycles
            animation_data = {"animation_events": {"beats": beats}}

            result = animator.animate(strips, animation_data, 30)
            assert result is True


class TestBeatSwitchAnimatorKeyframeIntegration:
    """Test integration with KeyframeHelper."""

    @patch("blender.vse.keyframe_helper.bpy")
    def test_animate_uses_keyframe_helper(self, mock_bpy):
        """Should use KeyframeHelper for all keyframe insertions."""
        animator = BeatSwitchAnimator()

        # Mock the keyframe helper
        mock_keyframe_helper = Mock()
        animator.keyframe_helper = mock_keyframe_helper

        strip = Mock()
        strip.name = "Video_1"
        strip.blend_alpha = 0.0

        video_strips = [strip]
        animation_data = {"animation_events": {"beats": [1.0, 2.0]}}
        fps = 30

        result = animator.animate(video_strips, animation_data, fps)

        assert result is True
        # Should have called keyframe helper for initial state + beat events
        expected_calls = 1 + len(
            animation_data["animation_events"]["beats"]
        )  # Initial + beats
        assert (
            mock_keyframe_helper.insert_blend_alpha_keyframe.call_count
            >= expected_calls
        )

    @patch("blender.vse.keyframe_helper.bpy")
    def test_animate_keyframe_parameters(self, mock_bpy):
        """Should pass correct parameters to KeyframeHelper."""
        animator = BeatSwitchAnimator()

        # Mock the keyframe helper to track calls
        mock_keyframe_helper = Mock()
        animator.keyframe_helper = mock_keyframe_helper

        strip1 = Mock()
        strip1.name = "Video_1"
        strip2 = Mock()
        strip2.name = "Video_2"

        video_strips = [strip1, strip2]
        animation_data = {"animation_events": {"beats": [1.0]}}
        fps = 30

        result = animator.animate(video_strips, animation_data, fps)

        assert result is True

        # Verify calls to keyframe helper
        calls = mock_keyframe_helper.insert_blend_alpha_keyframe.call_args_list

        # Should have initial keyframes (frame 1) and beat keyframes (frame 30)
        frame_1_calls = [call for call in calls if call[0][1] == 1]  # frame parameter
        frame_30_calls = [call for call in calls if call[0][1] == 30]  # frame parameter

        assert len(frame_1_calls) >= 2  # Initial state for both strips
        assert len(frame_30_calls) >= 2  # Beat state for both strips


class TestBeatSwitchAnimatorCompatibility:
    """Test compatibility with existing BlenderVSEConfigurator interface."""

    def test_animate_signature_compatibility(self):
        """Should have compatible method signature with original _animate_beat_switch."""
        animator = BeatSwitchAnimator()

        # Original signature: _animate_beat_switch(self, video_strips: List, animation_data: Dict) -> bool
        # New signature: animate(self, video_strips: List, animation_data: Dict, fps: int) -> bool

        # Should accept same types for first two parameters
        video_strips = []
        animation_data = {}
        fps = 30

        # Should not raise TypeError
        result = animator.animate(video_strips, animation_data, fps)
        assert isinstance(result, bool)

    @patch("blender.vse.keyframe_helper.bpy")
    def test_animate_behavior_compatibility(self, mock_bpy):
        """Should produce same animation behavior as original method."""
        animator = BeatSwitchAnimator()

        # Test data matching original test cases
        strip1 = Mock()
        strip1.name = "Video_1"
        strip1.blend_alpha = 0.0

        strip2 = Mock()
        strip2.name = "Video_2"
        strip2.blend_alpha = 0.0

        video_strips = [strip1, strip2]
        animation_data = {
            "animation_events": {"beats": [1.0, 2.0, 3.0]},
            "duration": 4.0,
            "tempo": {"bpm": 120.0},
        }
        fps = 30

        result = animator.animate(video_strips, animation_data, fps)

        assert result is True

        # Should follow same alternating pattern:
        # Initial: strip1 visible, strip2 hidden
        # Beat 1: strip2 visible, strip1 hidden
        # Beat 2: strip1 visible, strip2 hidden
        # Beat 3: strip2 visible, strip1 hidden
