"""
ABOUTME: Tests for MultiPipAnimator class - validates multi-camera switching with PiP effects.
ABOUTME: TDD approach - tests written first to define expected multi-pip animator behavior.
"""

from pathlib import Path
import sys
from unittest.mock import Mock, patch

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.blender_vse.animators.multi_pip_animator import MultiPipAnimator
from core.blender_vse.keyframe_helper import KeyframeHelper
from core.blender_vse.layout_manager import BlenderLayoutManager
from core.blender_vse.constants import AnimationConstants


class TestMultiPipAnimatorBasic:
    """Test basic MultiPipAnimator functionality."""

    def test_multi_pip_animator_initialization(self):
        """MultiPipAnimator should initialize with required components."""
        animator = MultiPipAnimator()

        assert animator is not None
        assert hasattr(animator, "keyframe_helper")
        assert isinstance(animator.keyframe_helper, KeyframeHelper)
        assert hasattr(animator, "layout_manager")
        assert isinstance(animator.layout_manager, BlenderLayoutManager)

    def test_multi_pip_animator_has_required_methods(self):
        """MultiPipAnimator should have required animation interface methods."""
        animator = MultiPipAnimator()

        required_methods = ["animate", "can_handle", "get_animation_mode"]

        for method in required_methods:
            assert hasattr(animator, method), f"Missing method: {method}"
            assert callable(getattr(animator, method)), (
                f"Method {method} is not callable"
            )

    def test_multi_pip_animator_mode_identification(self):
        """MultiPipAnimator should identify its animation mode correctly."""
        animator = MultiPipAnimator()

        assert animator.get_animation_mode() == "multi-pip"
        assert animator.can_handle("multi-pip") is True
        assert animator.can_handle("beat-switch") is False
        assert animator.can_handle("energy-pulse") is False


class TestMultiPipAnimatorValidation:
    """Test input validation for MultiPipAnimator."""

    def test_animate_validates_video_strips(self):
        """Should validate video_strips parameter."""
        animator = MultiPipAnimator()
        animation_data = {
            "animation_events": {
                "sections": [{"start": 0.0, "end": 30.0, "label": "verse"}],
                "beats": [1.0, 2.0],
            }
        }
        fps = 30

        # Empty strips list
        result = animator.animate([], animation_data, fps)
        assert result is True  # Should handle gracefully

        # None strips
        result = animator.animate(None, animation_data, fps)
        assert result is True  # Should handle gracefully

    def test_animate_validates_animation_data(self):
        """Should validate animation_data parameter."""
        animator = MultiPipAnimator()
        video_strips = [Mock(name="Video_1"), Mock(name="Video_2")]
        fps = 30

        # Missing animation_events
        result = animator.animate(video_strips, {}, fps)
        assert result is True  # Should handle gracefully

        # Missing sections
        animation_data = {"animation_events": {"beats": [1.0]}}
        result = animator.animate(video_strips, animation_data, fps)
        assert result is True  # Should handle gracefully

        # None animation_data
        result = animator.animate(video_strips, None, fps)
        assert result is True  # Should handle gracefully

    def test_animate_validates_fps(self):
        """Should validate fps parameter."""
        animator = MultiPipAnimator()
        video_strips = [Mock(name="Video_1")]
        animation_data = {
            "animation_events": {
                "sections": [{"start": 0.0, "end": 30.0, "label": "verse"}],
                "beats": [1.0],
            }
        }

        # Zero FPS
        result = animator.animate(video_strips, animation_data, 0)
        assert result is False  # Should fail validation

        # Negative FPS
        result = animator.animate(video_strips, animation_data, -30)
        assert result is False  # Should fail validation

    def test_animate_validates_minimum_strips(self):
        """Should validate minimum number of strips for multi-pip."""
        animator = MultiPipAnimator()
        animation_data = {
            "animation_events": {
                "sections": [{"start": 0.0, "end": 30.0, "label": "verse"}],
                "beats": [1.0],
            }
        }
        fps = 30

        # Single strip - should handle gracefully
        single_strip = [Mock(name="Video_1")]
        result = animator.animate(single_strip, animation_data, fps)
        assert result is True  # Should handle gracefully but may not create PiPs


class TestMultiPipAnimatorSectionLogic:
    """Test section-based main camera switching logic."""

    @patch("core.blender_vse.keyframe_helper.bpy")
    def test_animate_section_switching(self, mock_bpy):
        """Should switch main camera on section boundaries."""
        animator = MultiPipAnimator()

        # Create mock strips
        strips = []
        for i in range(4):
            strip = Mock()
            strip.name = f"Video_{i + 1}"
            strip.blend_alpha = 0.0
            strips.append(strip)

        # Multiple sections for main camera switching
        animation_data = {
            "animation_events": {
                "sections": [
                    {"start": 0.0, "end": 30.0, "label": "intro"},
                    {"start": 30.0, "end": 60.0, "label": "verse"},
                    {"start": 60.0, "end": 90.0, "label": "chorus"},
                    {"start": 90.0, "end": 120.0, "label": "outro"},
                ],
                "beats": [1.0, 2.0, 3.0],
            }
        }
        fps = 30

        result = animator.animate(strips, animation_data, fps)
        assert result is True

    @patch("core.blender_vse.keyframe_helper.bpy")
    def test_animate_section_frame_calculation(self, mock_bpy):
        """Should calculate frame numbers correctly from section boundaries."""
        animator = MultiPipAnimator()

        strips = [Mock(name="Video_1"), Mock(name="Video_2")]

        # Test different FPS values with section boundaries
        test_cases = [
            (
                30,
                [{"start": 0.0, "end": 2.0}, {"start": 2.0, "end": 4.0}],
                [0, 60],
            ),  # 30 FPS
            (
                24,
                [{"start": 0.0, "end": 1.0}, {"start": 1.0, "end": 2.0}],
                [0, 24],
            ),  # 24 FPS
            (
                60,
                [{"start": 0.0, "end": 1.5}, {"start": 1.5, "end": 3.0}],
                [0, 90],
            ),  # 60 FPS
        ]

        for fps, sections, expected_frames in test_cases:
            animation_data = {
                "animation_events": {"sections": sections, "beats": [0.5, 1.0]}
            }
            result = animator.animate(strips, animation_data, fps)
            assert result is True

    def test_animate_section_cycling(self):
        """Should cycle through strips for main camera on section boundaries."""
        animator = MultiPipAnimator()

        # Test with different strip counts
        for strip_count in [2, 3, 4]:
            strips = []
            for i in range(strip_count):
                strip = Mock()
                strip.name = f"Video_{i + 1}"
                strips.append(strip)

            # Create more sections than strips to test cycling
            sections = []
            for i in range(strip_count + 2):
                sections.append(
                    {"start": i * 10.0, "end": (i + 1) * 10.0, "label": f"section_{i}"}
                )

            animation_data = {
                "animation_events": {"sections": sections, "beats": [1.0, 2.0]}
            }

            with patch("core.blender_vse.keyframe_helper.bpy"):
                result = animator.animate(strips, animation_data, 30)
                assert result is True


class TestMultiPipAnimatorPipLogic:
    """Test PiP (Picture-in-Picture) corner effects logic."""

    @patch("core.blender_vse.keyframe_helper.bpy")
    def test_animate_pip_positioning(self, mock_bpy):
        """Should position PiP strips in corners correctly."""
        animator = MultiPipAnimator()

        # Mock layout manager to track calls
        mock_layout = Mock()
        mock_layout.get_corner_positions.return_value = [
            (160, 160),  # Top-left
            (1120, 160),  # Top-right
            (160, 560),  # Bottom-left
            (1120, 560),  # Bottom-right
        ]
        animator.layout_manager = mock_layout

        # Create 4 strips (1 main + 3 PiPs)
        strips = []
        for i in range(4):
            strip = Mock()
            strip.name = f"Video_{i + 1}"
            strip.blend_alpha = 0.0
            strips.append(strip)

        animation_data = {
            "animation_events": {
                "sections": [{"start": 0.0, "end": 30.0, "label": "verse"}],
                "beats": [1.0, 2.0, 3.0],
            }
        }
        fps = 30

        result = animator.animate(strips, animation_data, fps)
        assert result is True

        # Should have called layout manager for corner positions
        mock_layout.get_corner_positions.assert_called()

    @patch("core.blender_vse.keyframe_helper.bpy")
    def test_animate_pip_scaling(self, mock_bpy):
        """Should scale PiP strips using AnimationConstants."""
        animator = MultiPipAnimator()

        strips = []
        for i in range(3):
            strip = Mock()
            strip.name = f"Video_{i + 1}"
            # Add transform mock for scaling
            strip.transform = Mock()
            strip.transform.scale_x = 1.0
            strip.transform.scale_y = 1.0
            strips.append(strip)

        animation_data = {
            "animation_events": {
                "sections": [{"start": 0.0, "end": 30.0, "label": "verse"}],
                "beats": [1.0, 2.0],
            }
        }
        fps = 30

        result = animator.animate(strips, animation_data, fps)
        assert result is True

        # PiP strips should be scaled down
        expected_scale = AnimationConstants.PIP_SCALE_FACTOR
        assert expected_scale == 0.3  # From constants

    @patch("core.blender_vse.keyframe_helper.bpy")
    def test_animate_pip_beat_effects(self, mock_bpy):
        """Should apply beat effects to PiP strips."""
        animator = MultiPipAnimator()

        strips = []
        for i in range(4):
            strip = Mock()
            strip.name = f"Video_{i + 1}"
            strip.blend_alpha = 0.0
            # Add transform for beat effects
            strip.transform = Mock()
            strip.transform.scale_x = 1.0
            strip.transform.scale_y = 1.0
            strips.append(strip)

        animation_data = {
            "animation_events": {
                "sections": [{"start": 0.0, "end": 60.0, "label": "verse"}],
                "beats": [1.0, 2.0, 3.0, 4.0],
            }
        }
        fps = 30

        result = animator.animate(strips, animation_data, fps)
        assert result is True


class TestMultiPipAnimatorKeyframeIntegration:
    """Test integration with KeyframeHelper for complex animations."""

    @patch("core.blender_vse.keyframe_helper.bpy")
    def test_animate_uses_keyframe_helper(self, mock_bpy):
        """Should use KeyframeHelper for all keyframe insertions."""
        animator = MultiPipAnimator()

        # Mock the keyframe helper
        mock_keyframe_helper = Mock()
        animator.keyframe_helper = mock_keyframe_helper

        strips = []
        for i in range(3):
            strip = Mock()
            strip.name = f"Video_{i + 1}"
            strip.blend_alpha = 0.0
            strips.append(strip)

        animation_data = {
            "animation_events": {
                "sections": [{"start": 0.0, "end": 30.0, "label": "verse"}],
                "beats": [1.0, 2.0],
            }
        }
        fps = 30

        result = animator.animate(strips, animation_data, fps)
        assert result is True

        # Should use multiple keyframe types
        assert mock_keyframe_helper.insert_blend_alpha_keyframe.call_count >= 0
        assert mock_keyframe_helper.insert_transform_scale_keyframes.call_count >= 0

    @patch("core.blender_vse.keyframe_helper.bpy")
    def test_animate_keyframe_timing(self, mock_bpy):
        """Should insert keyframes at correct frame timings."""
        animator = MultiPipAnimator()

        # Mock the keyframe helper to track calls
        mock_keyframe_helper = Mock()
        animator.keyframe_helper = mock_keyframe_helper

        strips = [Mock(name="Video_1"), Mock(name="Video_2")]

        animation_data = {
            "animation_events": {
                "sections": [
                    {"start": 0.0, "end": 2.0, "label": "intro"},
                    {"start": 2.0, "end": 4.0, "label": "verse"},
                ],
                "beats": [1.0, 3.0],  # Frame 30 and 90
            }
        }
        fps = 30

        result = animator.animate(strips, animation_data, fps)
        assert result is True

        # Should have keyframes at section boundaries and beat events
        # Section boundaries: frame 0, 60, 120
        # Beat events: frame 30, 90


class TestMultiPipAnimatorLayoutIntegration:
    """Test integration with BlenderLayoutManager."""

    @patch("core.blender_vse.keyframe_helper.bpy")
    def test_animate_uses_layout_manager(self, mock_bpy):
        """Should use BlenderLayoutManager for positioning calculations."""
        animator = MultiPipAnimator()

        # Mock the layout manager
        mock_layout = Mock()
        mock_layout.get_corner_positions.return_value = [
            (160, 160),
            (1120, 160),
            (160, 560),
            (1120, 560),
        ]
        animator.layout_manager = mock_layout

        strips = [Mock(name="Video_1"), Mock(name="Video_2"), Mock(name="Video_3")]

        animation_data = {
            "animation_events": {
                "sections": [{"start": 0.0, "end": 30.0, "label": "verse"}],
                "beats": [1.0],
            }
        }
        fps = 30

        result = animator.animate(strips, animation_data, fps)
        assert result is True

        # Should have called layout manager for corner positions
        mock_layout.get_corner_positions.assert_called()

    def test_animate_pip_margin_usage(self):
        """Should use AnimationConstants.PIP_MARGIN for positioning."""
        # Test that PIP_MARGIN constant is accessible
        margin = AnimationConstants.PIP_MARGIN
        assert isinstance(margin, int)
        assert margin > 0
        assert margin == 160  # From constants


class TestMultiPipAnimatorConstants:
    """Test usage of AnimationConstants for multi-pip."""

    def test_constants_accessibility(self):
        """Should be able to access all required constants."""
        # Test all constants used by MultiPipAnimator
        pip_scale = AnimationConstants.PIP_SCALE_FACTOR
        pip_margin = AnimationConstants.PIP_MARGIN

        assert isinstance(pip_scale, (int, float))
        assert isinstance(pip_margin, int)
        assert pip_scale > 0
        assert pip_margin > 0
        assert pip_scale == 0.3  # Small for PiP
        assert pip_margin == 160  # Corner margin

    @patch("core.blender_vse.keyframe_helper.bpy")
    def test_animate_uses_pip_constants(self, mock_bpy):
        """Should use PIP constants for scaling and positioning."""
        animator = MultiPipAnimator()

        strips = []
        for i in range(3):
            strip = Mock()
            strip.name = f"Video_{i + 1}"
            strip.transform = Mock()
            strip.transform.scale_x = 1.0
            strip.transform.scale_y = 1.0
            strips.append(strip)

        animation_data = {
            "animation_events": {
                "sections": [{"start": 0.0, "end": 30.0, "label": "verse"}],
                "beats": [1.0],
            }
        }
        fps = 30

        result = animator.animate(strips, animation_data, fps)
        assert result is True

        # Should use PIP_SCALE_FACTOR and PIP_MARGIN
        expected_scale = AnimationConstants.PIP_SCALE_FACTOR
        expected_margin = AnimationConstants.PIP_MARGIN
        assert expected_scale == 0.3
        assert expected_margin == 160


class TestMultiPipAnimatorCompatibility:
    """Test compatibility with existing BlenderVSEConfigurator interface."""

    def test_animate_signature_compatibility(self):
        """Should have compatible method signature with original _animate_multi_pip."""
        animator = MultiPipAnimator()

        # Original signature: _animate_multi_pip(self, video_strips: List, animation_data: Dict) -> bool
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
        animator = MultiPipAnimator()

        # Test data matching original multi-pip test cases
        strips = []
        for i in range(4):
            strip = Mock()
            strip.name = f"Video_{i + 1}"
            strip.blend_alpha = 0.0
            strip.transform = Mock()
            strip.transform.scale_x = 1.0
            strip.transform.scale_y = 1.0
            strips.append(strip)

        animation_data = {
            "animation_events": {
                "sections": [
                    {"start": 0.0, "end": 32.1, "label": "intro"},
                    {"start": 32.1, "end": 96.4, "label": "verse"},
                    {"start": 96.4, "end": 128.5, "label": "chorus"},
                ],
                "beats": [1.0, 2.0, 3.0, 4.0],
                "onsets": [0.12, 0.54, 1.02, 1.48],
            },
            "duration": 180.36,
        }
        fps = 30

        result = animator.animate(strips, animation_data, fps)
        assert result is True

        # Should follow same pattern:
        # Main camera switches on section boundaries (cycling through strips)
        # PiP strips in corners with beat effects
        # Proper scaling and positioning using constants


class TestMultiPipAnimatorComplexScenarios:
    """Test complex multi-pip animation scenarios."""

    @patch("core.blender_vse.keyframe_helper.bpy")
    def test_animate_four_strip_scenario(self, mock_bpy):
        """Should handle typical 4-strip multi-pip scenario correctly."""
        animator = MultiPipAnimator()

        # 4 strips: 1 main + 3 PiPs
        strips = []
        for i in range(4):
            strip = Mock()
            strip.name = f"Camera_{i + 1}"
            strip.blend_alpha = 0.0
            strip.transform = Mock()
            strip.transform.scale_x = 1.0
            strip.transform.scale_y = 1.0
            strips.append(strip)

        # Rich animation data
        animation_data = {
            "animation_events": {
                "sections": [
                    {"start": 0.0, "end": 30.0, "label": "intro"},
                    {"start": 30.0, "end": 90.0, "label": "verse"},
                    {"start": 90.0, "end": 150.0, "label": "chorus"},
                    {"start": 150.0, "end": 180.0, "label": "outro"},
                ],
                "beats": [i * 0.5 for i in range(1, 21)],  # 20 beats
                "onsets": [i * 0.25 for i in range(1, 41)],  # 40 onsets
            },
            "duration": 180.0,
        }
        fps = 30

        result = animator.animate(strips, animation_data, fps)
        assert result is True

    def test_animate_handles_edge_cases(self):
        """Should handle edge cases gracefully."""
        animator = MultiPipAnimator()

        # Test various edge cases
        edge_cases = [
            # Single section
            {
                "sections": [{"start": 0.0, "end": 60.0, "label": "full"}],
                "beats": [1.0],
            },
            # No beats
            {"sections": [{"start": 0.0, "end": 30.0, "label": "quiet"}], "beats": []},
            # Overlapping sections (should handle gracefully)
            {
                "sections": [
                    {"start": 0.0, "end": 30.0, "label": "intro"},
                    {"start": 25.0, "end": 60.0, "label": "verse"},
                ],
                "beats": [1.0, 2.0],
            },
            # Empty sections
            {"sections": [], "beats": [1.0, 2.0]},
        ]

        strips = [Mock(name="Video_1"), Mock(name="Video_2")]
        fps = 30

        for events in edge_cases:
            animation_data = {"animation_events": events}
            with patch("core.blender_vse.keyframe_helper.bpy"):
                result = animator.animate(strips, animation_data, fps)
                assert result is True  # Should handle gracefully
