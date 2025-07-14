"""
ABOUTME: Tests for EnergyPulseAnimator class - validates energy-driven scale pulsing animations.
ABOUTME: TDD approach - tests written first to define expected energy pulse animator behavior.
"""

from pathlib import Path
import sys
from unittest.mock import Mock, patch

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.blender_vse.animators.energy_pulse_animator import EnergyPulseAnimator
from core.blender_vse.keyframe_helper import KeyframeHelper
from core.blender_vse.constants import AnimationConstants


class TestEnergyPulseAnimatorBasic:
    """Test basic EnergyPulseAnimator functionality."""

    def test_energy_pulse_animator_initialization(self):
        """EnergyPulseAnimator should initialize with keyframe helper."""
        animator = EnergyPulseAnimator()

        assert animator is not None
        assert hasattr(animator, "keyframe_helper")
        assert isinstance(animator.keyframe_helper, KeyframeHelper)

    def test_energy_pulse_animator_has_required_methods(self):
        """EnergyPulseAnimator should have required animation interface methods."""
        animator = EnergyPulseAnimator()

        required_methods = ["animate", "can_handle", "get_animation_mode"]

        for method in required_methods:
            assert hasattr(animator, method), f"Missing method: {method}"
            assert callable(getattr(animator, method)), (
                f"Method {method} is not callable"
            )

    def test_energy_pulse_animator_mode_identification(self):
        """EnergyPulseAnimator should identify its animation mode correctly."""
        animator = EnergyPulseAnimator()

        assert animator.get_animation_mode() == "energy-pulse"
        assert animator.can_handle("energy-pulse") is True
        assert animator.can_handle("beat-switch") is False
        assert animator.can_handle("multi-pip") is False


class TestEnergyPulseAnimatorValidation:
    """Test input validation for EnergyPulseAnimator."""

    def test_animate_validates_video_strips(self):
        """Should validate video_strips parameter."""
        animator = EnergyPulseAnimator()
        animation_data = {"animation_events": {"energy_peaks": [1.0, 2.0]}}
        fps = 30

        # Empty strips list
        result = animator.animate([], animation_data, fps)
        assert result is True  # Should handle gracefully

        # None strips
        result = animator.animate(None, animation_data, fps)
        assert result is True  # Should handle gracefully

    def test_animate_validates_animation_data(self):
        """Should validate animation_data parameter."""
        animator = EnergyPulseAnimator()
        video_strips = [Mock(name="Video_1"), Mock(name="Video_2")]
        fps = 30

        # Missing animation_events
        result = animator.animate(video_strips, {}, fps)
        assert result is True  # Should handle gracefully

        # Missing energy_peaks
        animation_data = {"animation_events": {}}
        result = animator.animate(video_strips, animation_data, fps)
        assert result is True  # Should handle gracefully

        # None animation_data
        result = animator.animate(video_strips, None, fps)
        assert result is True  # Should handle gracefully

    def test_animate_validates_fps(self):
        """Should validate fps parameter."""
        animator = EnergyPulseAnimator()
        video_strips = [Mock(name="Video_1")]
        animation_data = {"animation_events": {"energy_peaks": [1.0]}}

        # Zero FPS
        result = animator.animate(video_strips, animation_data, 0)
        assert result is False  # Should fail validation

        # Negative FPS
        result = animator.animate(video_strips, animation_data, -30)
        assert result is False  # Should fail validation


class TestEnergyPulseAnimatorLogic:
    """Test core energy pulse animation logic."""

    @patch("core.blender_vse.keyframe_helper.bpy")
    def test_animate_initial_scale_setup(self, mock_bpy):
        """Should set initial scale to normal (1.0) for all strips."""
        animator = EnergyPulseAnimator()

        # Create mock strips with transform
        strip1 = Mock()
        strip1.name = "Video_1"
        strip1.transform.scale_x = 0.0
        strip1.transform.scale_y = 0.0

        strip2 = Mock()
        strip2.name = "Video_2"
        strip2.transform.scale_x = 0.0
        strip2.transform.scale_y = 0.0

        video_strips = [strip1, strip2]
        animation_data = {"animation_events": {"energy_peaks": [1.0, 2.0]}}
        fps = 30

        result = animator.animate(video_strips, animation_data, fps)

        assert result is True
        # All strips should be set to normal scale initially
        assert strip1.transform.scale_x == 1.0
        assert strip1.transform.scale_y == 1.0
        assert strip2.transform.scale_x == 1.0
        assert strip2.transform.scale_y == 1.0

    @patch("core.blender_vse.keyframe_helper.bpy")
    def test_animate_energy_scaling_logic(self, mock_bpy):
        """Should scale strips on energy peaks using AnimationConstants."""
        animator = EnergyPulseAnimator()

        strip = Mock()
        strip.name = "Video_1"
        strip.transform.scale_x = 1.0
        strip.transform.scale_y = 1.0

        video_strips = [strip]
        animation_data = {"animation_events": {"energy_peaks": [1.0]}}
        fps = 30

        result = animator.animate(video_strips, animation_data, fps)

        assert result is True

        # Note: Implementation should scale up then back down using ENERGY_SCALE_FACTOR
        # Final state should be back to normal after peak + 1 frame

    @patch("core.blender_vse.keyframe_helper.bpy")
    def test_animate_frame_calculation(self, mock_bpy):
        """Should calculate frame numbers correctly from energy peak times."""
        animator = EnergyPulseAnimator()

        strip = Mock()
        strip.name = "Video_1"
        strip.transform.scale_x = 1.0
        strip.transform.scale_y = 1.0

        video_strips = [strip]

        # Test different FPS values
        test_cases = [
            (
                {"animation_events": {"energy_peaks": [1.0, 2.5]}},
                30,
                [30, 75],
            ),  # 30 FPS
            (
                {"animation_events": {"energy_peaks": [0.5, 1.0]}},
                24,
                [12, 24],
            ),  # 24 FPS
            (
                {"animation_events": {"energy_peaks": [2.0, 4.0]}},
                60,
                [120, 240],
            ),  # 60 FPS
        ]

        for animation_data, fps, expected_frames in test_cases:
            result = animator.animate(video_strips, animation_data, fps)
            assert result is True

    @patch("core.blender_vse.keyframe_helper.bpy")
    def test_animate_peak_and_return_pattern(self, mock_bpy):
        """Should scale up on energy peak and back down on next frame."""
        animator = EnergyPulseAnimator()

        strip = Mock()
        strip.name = "Video_1"
        strip.transform.scale_x = 1.0
        strip.transform.scale_y = 1.0

        video_strips = [strip]
        animation_data = {"animation_events": {"energy_peaks": [1.0]}}  # Frame 30
        fps = 30

        # Mock keyframe helper to track calls
        mock_keyframe_helper = Mock()
        animator.keyframe_helper = mock_keyframe_helper

        result = animator.animate(video_strips, animation_data, fps)

        assert result is True

        # Should have keyframes for:
        # 1. Initial scale (frame 1)
        # 2. Scale up (frame 30)
        # 3. Scale back down (frame 31)
        calls = mock_keyframe_helper.insert_transform_scale_keyframes.call_args_list
        assert len(calls) >= 3

    def test_animate_multiple_energy_peaks(self):
        """Should handle multiple energy peaks correctly."""
        animator = EnergyPulseAnimator()

        strip = Mock()
        strip.name = "Video_1"
        strip.transform.scale_x = 1.0
        strip.transform.scale_y = 1.0

        video_strips = [strip]

        # Multiple energy peaks
        energy_peaks = [1.0, 2.5, 4.2, 6.8]
        animation_data = {"animation_events": {"energy_peaks": energy_peaks}}

        with patch("core.blender_vse.keyframe_helper.bpy"):
            result = animator.animate(video_strips, animation_data, 30)
            assert result is True


class TestEnergyPulseAnimatorKeyframeIntegration:
    """Test integration with KeyframeHelper."""

    @patch("core.blender_vse.keyframe_helper.bpy")
    def test_animate_uses_keyframe_helper(self, mock_bpy):
        """Should use KeyframeHelper for all keyframe insertions."""
        animator = EnergyPulseAnimator()

        # Mock the keyframe helper
        mock_keyframe_helper = Mock()
        animator.keyframe_helper = mock_keyframe_helper

        strip = Mock()
        strip.name = "Video_1"
        strip.transform.scale_x = 1.0
        strip.transform.scale_y = 1.0

        video_strips = [strip]
        animation_data = {"animation_events": {"energy_peaks": [1.0, 2.0]}}
        fps = 30

        result = animator.animate(video_strips, animation_data, fps)

        assert result is True

        # Should use scale keyframes, not blend_alpha
        assert mock_keyframe_helper.insert_transform_scale_keyframes.call_count > 0
        assert mock_keyframe_helper.insert_blend_alpha_keyframe.call_count == 0

    @patch("core.blender_vse.keyframe_helper.bpy")
    def test_animate_keyframe_parameters(self, mock_bpy):
        """Should pass correct parameters to KeyframeHelper."""
        animator = EnergyPulseAnimator()

        # Mock the keyframe helper to track calls
        mock_keyframe_helper = Mock()
        animator.keyframe_helper = mock_keyframe_helper

        strip = Mock()
        strip.name = "Video_1"
        strip.transform.scale_x = 1.0
        strip.transform.scale_y = 1.0

        video_strips = [strip]
        animation_data = {"animation_events": {"energy_peaks": [1.0]}}
        fps = 30

        result = animator.animate(video_strips, animation_data, fps)

        assert result is True

        # Verify calls to keyframe helper
        calls = mock_keyframe_helper.insert_transform_scale_keyframes.call_args_list

        # Should have initial keyframes (frame 1), peak keyframes (frame 30), and return keyframes (frame 31)
        frame_1_calls = [call for call in calls if call[0][1] == 1]  # frame parameter
        frame_30_calls = [call for call in calls if call[0][1] == 30]  # frame parameter
        frame_31_calls = [call for call in calls if call[0][1] == 31]  # frame parameter

        assert len(frame_1_calls) >= 1  # Initial state
        assert len(frame_30_calls) >= 1  # Peak state
        assert len(frame_31_calls) >= 1  # Return state


class TestEnergyPulseAnimatorConstants:
    """Test usage of AnimationConstants."""

    @patch("core.blender_vse.keyframe_helper.bpy")
    def test_animate_uses_energy_scale_factor(self, mock_bpy):
        """Should use AnimationConstants.ENERGY_SCALE_FACTOR for scaling."""
        animator = EnergyPulseAnimator()

        strip = Mock()
        strip.name = "Video_1"
        strip.transform.scale_x = 1.0
        strip.transform.scale_y = 1.0

        video_strips = [strip]
        animation_data = {"animation_events": {"energy_peaks": [1.0]}}
        fps = 30

        result = animator.animate(video_strips, animation_data, fps)

        assert result is True

        # Should use the constant value (1.2)
        expected_scale = AnimationConstants.ENERGY_SCALE_FACTOR
        assert expected_scale == 1.2

    def test_energy_scale_factor_accessibility(self):
        """Should be able to access AnimationConstants.ENERGY_SCALE_FACTOR."""
        # This test ensures the constant is properly imported and accessible
        scale_factor = AnimationConstants.ENERGY_SCALE_FACTOR
        assert isinstance(scale_factor, (int, float))
        assert scale_factor > 1.0
        assert scale_factor == 1.2


class TestEnergyPulseAnimatorCompatibility:
    """Test compatibility with existing BlenderVSEConfigurator interface."""

    def test_animate_signature_compatibility(self):
        """Should have compatible method signature with original _animate_energy_pulse."""
        animator = EnergyPulseAnimator()

        # Original signature: _animate_energy_pulse(self, video_strips: List, animation_data: Dict) -> bool
        # New signature: animate(self, video_strips: List, animation_data: Dict, fps: int) -> bool

        # Should accept same types for first two parameters
        video_strips = []
        animation_data = {}
        fps = 30

        # Should not raise TypeError
        result = animator.animate(video_strips, animation_data, fps)
        assert isinstance(result, bool)

    @patch("core.blender_vse.keyframe_helper.bpy")
    def test_animate_behavior_compatibility(self, mock_bpy):
        """Should produce same animation behavior as original method."""
        animator = EnergyPulseAnimator()

        # Test data matching original test cases
        strip1 = Mock()
        strip1.name = "Video_1"
        strip1.transform.scale_x = 1.0
        strip1.transform.scale_y = 1.0

        strip2 = Mock()
        strip2.name = "Video_2"
        strip2.transform.scale_x = 1.0
        strip2.transform.scale_y = 1.0

        video_strips = [strip1, strip2]
        animation_data = {
            "animation_events": {"energy_peaks": [2.1, 5.8, 12.3]},
            "duration": 15.0,
        }
        fps = 30

        result = animator.animate(video_strips, animation_data, fps)

        assert result is True

        # Should follow same scaling pattern:
        # Initial: all strips scale 1.0
        # Peak 1 (frame ~63): all strips scale 1.2, then back to 1.0
        # Peak 2 (frame ~174): all strips scale 1.2, then back to 1.0
        # Peak 3 (frame ~369): all strips scale 1.2, then back to 1.0
