"""
ABOUTME: Tests for Blender VSE keyframe helper module - validates keyframe insertion utilities.
ABOUTME: TDD approach - tests written first to define expected keyframe helper behavior.
"""

import pytest
from pathlib import Path
import sys
from unittest.mock import Mock, patch

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from blender.vse.keyframe_helper import KeyframeHelper


class MockBPYContext:
    """Mock bpy.context for testing."""

    def __init__(self):
        self.scene = Mock()
        self.scene.keyframe_insert = Mock()


class TestKeyframeHelperBasic:
    """Test basic KeyframeHelper functionality."""

    def test_keyframe_helper_initialization(self):
        """KeyframeHelper should initialize without parameters."""
        helper = KeyframeHelper()
        assert helper is not None

    def test_keyframe_helper_has_required_methods(self):
        """KeyframeHelper should have all required methods for common patterns."""
        helper = KeyframeHelper()

        # Methods extracted from repeated patterns in blender_vse_script.py
        required_methods = [
            "insert_blend_alpha_keyframe",
            "insert_transform_scale_keyframes",
            "insert_transform_offset_keyframes",
            "build_data_path",
        ]

        for method in required_methods:
            assert hasattr(helper, method), f"Missing method: {method}"
            assert callable(getattr(helper, method)), f"Method {method} is not callable"


class TestBlendAlphaKeyframes:
    """Test blend_alpha keyframe insertion."""

    @patch("blender.vse.keyframe_helper.bpy")
    def test_insert_blend_alpha_keyframe_basic(self, mock_bpy):
        """Should insert blend_alpha keyframe correctly."""
        mock_bpy.context = MockBPYContext()

        helper = KeyframeHelper()
        strip_name = "Video_1"
        frame = 30
        alpha_value = 1.0

        result = helper.insert_blend_alpha_keyframe(strip_name, frame, alpha_value)

        assert result is True
        mock_bpy.context.scene.keyframe_insert.assert_called_once()

        # Check the call arguments
        call_args = mock_bpy.context.scene.keyframe_insert.call_args
        assert call_args[1]["frame"] == frame
        assert "blend_alpha" in call_args[1]["data_path"]
        assert strip_name in call_args[1]["data_path"]

    @patch("blender.vse.keyframe_helper.bpy")
    def test_insert_blend_alpha_keyframe_with_strip_object(self, mock_bpy):
        """Should accept strip object and extract name."""
        mock_bpy.context = MockBPYContext()

        helper = KeyframeHelper()
        mock_strip = Mock()
        mock_strip.name = "Video_2"
        mock_strip.blend_alpha = 0.5
        frame = 60

        result = helper.insert_blend_alpha_keyframe(mock_strip, frame)

        assert result is True
        # Should extract alpha value from strip if not provided
        mock_bpy.context.scene.keyframe_insert.assert_called_once()

    @patch("blender.vse.keyframe_helper.bpy")
    def test_insert_blend_alpha_keyframe_error_handling(self, mock_bpy):
        """Should handle keyframe insertion errors gracefully."""
        mock_bpy.context = MockBPYContext()
        mock_bpy.context.scene.keyframe_insert.side_effect = Exception("Blender error")

        helper = KeyframeHelper()
        result = helper.insert_blend_alpha_keyframe("Video_1", 30, 1.0)

        assert result is False


class TestTransformScaleKeyframes:
    """Test transform scale keyframe insertion."""

    @patch("blender.vse.keyframe_helper.bpy")
    def test_insert_transform_scale_keyframes_basic(self, mock_bpy):
        """Should insert scale_x and scale_y keyframes correctly."""
        mock_bpy.context = MockBPYContext()

        helper = KeyframeHelper()
        strip_name = "Video_1"
        frame = 30
        scale_x = 1.2
        scale_y = 1.2

        result = helper.insert_transform_scale_keyframes(
            strip_name, frame, scale_x, scale_y
        )

        assert result is True
        # Should be called twice (scale_x and scale_y)
        assert mock_bpy.context.scene.keyframe_insert.call_count == 2

    @patch("blender.vse.keyframe_helper.bpy")
    def test_insert_transform_scale_keyframes_uniform_scale(self, mock_bpy):
        """Should accept single scale value for uniform scaling."""
        mock_bpy.context = MockBPYContext()

        helper = KeyframeHelper()
        result = helper.insert_transform_scale_keyframes("Video_1", 30, 1.5)

        assert result is True
        assert mock_bpy.context.scene.keyframe_insert.call_count == 2

    @patch("blender.vse.keyframe_helper.bpy")
    def test_insert_transform_scale_keyframes_with_strip_object(self, mock_bpy):
        """Should accept strip object and extract current scale values."""
        mock_bpy.context = MockBPYContext()

        helper = KeyframeHelper()
        mock_strip = Mock()
        mock_strip.name = "Video_2"
        mock_strip.transform.scale_x = 1.1
        mock_strip.transform.scale_y = 1.1

        result = helper.insert_transform_scale_keyframes(mock_strip, 60)

        assert result is True
        assert mock_bpy.context.scene.keyframe_insert.call_count == 2


class TestTransformOffsetKeyframes:
    """Test transform offset keyframe insertion."""

    @patch("blender.vse.keyframe_helper.bpy")
    def test_insert_transform_offset_keyframes_basic(self, mock_bpy):
        """Should insert offset_x and offset_y keyframes correctly."""
        mock_bpy.context = MockBPYContext()

        helper = KeyframeHelper()
        strip_name = "Video_1"
        frame = 30
        offset_x = 100
        offset_y = 200

        result = helper.insert_transform_offset_keyframes(
            strip_name, frame, offset_x, offset_y
        )

        assert result is True
        # Should be called twice (offset_x and offset_y)
        assert mock_bpy.context.scene.keyframe_insert.call_count == 2

    @patch("blender.vse.keyframe_helper.bpy")
    def test_insert_transform_offset_keyframes_with_strip_object(self, mock_bpy):
        """Should accept strip object and extract current offset values."""
        mock_bpy.context = MockBPYContext()

        helper = KeyframeHelper()
        mock_strip = Mock()
        mock_strip.name = "Video_2"
        mock_strip.transform.offset_x = 50
        mock_strip.transform.offset_y = -30

        result = helper.insert_transform_offset_keyframes(mock_strip, 60)

        assert result is True
        assert mock_bpy.context.scene.keyframe_insert.call_count == 2


class TestDataPathBuilder:
    """Test data path building utility."""

    def test_build_data_path_blend_alpha(self):
        """Should build correct data path for blend_alpha."""
        helper = KeyframeHelper()

        data_path = helper.build_data_path("Video_1", "blend_alpha")
        expected = 'sequence_editor.sequences_all["Video_1"].blend_alpha'

        assert data_path == expected

    def test_build_data_path_transform_scale_x(self):
        """Should build correct data path for transform.scale_x."""
        helper = KeyframeHelper()

        data_path = helper.build_data_path("Video_2", "transform.scale_x")
        expected = 'sequence_editor.sequences_all["Video_2"].transform.scale_x'

        assert data_path == expected

    def test_build_data_path_transform_offset_y(self):
        """Should build correct data path for transform.offset_y."""
        helper = KeyframeHelper()

        data_path = helper.build_data_path("Video_3", "transform.offset_y")
        expected = 'sequence_editor.sequences_all["Video_3"].transform.offset_y'

        assert data_path == expected

    def test_build_data_path_custom_property(self):
        """Should build data path for any property."""
        helper = KeyframeHelper()

        data_path = helper.build_data_path("Audio_1", "volume")
        expected = 'sequence_editor.sequences_all["Audio_1"].volume'

        assert data_path == expected


class TestKeyframeHelperIntegration:
    """Test integration patterns and edge cases."""

    @patch("blender.vse.keyframe_helper.bpy")
    def test_multiple_keyframes_batch_insertion(self, mock_bpy):
        """Should handle multiple keyframe insertions efficiently."""
        mock_bpy.context = MockBPYContext()

        helper = KeyframeHelper()

        # Insert multiple types of keyframes for same strip/frame
        strip_name = "Video_1"
        frame = 30

        # Blend alpha
        result1 = helper.insert_blend_alpha_keyframe(strip_name, frame, 1.0)
        # Scale
        result2 = helper.insert_transform_scale_keyframes(strip_name, frame, 1.2, 1.2)
        # Offset
        result3 = helper.insert_transform_offset_keyframes(strip_name, frame, 100, 200)

        assert all([result1, result2, result3])
        # Total calls: 1 (alpha) + 2 (scale) + 2 (offset) = 5
        assert mock_bpy.context.scene.keyframe_insert.call_count == 5

    def test_keyframe_helper_is_stateless(self):
        """KeyframeHelper should be stateless and reusable."""
        helper1 = KeyframeHelper()
        helper2 = KeyframeHelper()

        # Should be independent instances with same behavior
        assert helper1.build_data_path(
            "Video_1", "blend_alpha"
        ) == helper2.build_data_path("Video_1", "blend_alpha")

    def test_keyframe_helper_parameter_validation(self):
        """Should validate parameters appropriately."""
        helper = KeyframeHelper()

        # Test invalid strip names
        with pytest.raises((ValueError, TypeError)):
            helper.build_data_path("", "blend_alpha")

        with pytest.raises((ValueError, TypeError)):
            helper.build_data_path(None, "blend_alpha")

    @patch("blender.vse.keyframe_helper.bpy")
    def test_keyframe_helper_backwards_compatibility(self, mock_bpy):
        """Should work with existing code patterns from blender_vse_script.py."""
        mock_bpy.context = MockBPYContext()

        helper = KeyframeHelper()

        # Simulate existing patterns from the script
        video_strips = [Mock(name="Video_1"), Mock(name="Video_2")]
        beats = [1.0, 2.0, 3.0]
        fps = 30

        for beat_index, beat_time in enumerate(beats):
            frame = int(beat_time * fps)
            active_strip_index = beat_index % len(video_strips)

            for strip_index, strip in enumerate(video_strips):
                alpha = 1.0 if strip_index == active_strip_index else 0.0
                result = helper.insert_blend_alpha_keyframe(strip.name, frame, alpha)
                assert result is True

        # Should have made keyframes for all beats and strips
        expected_calls = len(beats) * len(video_strips)
        assert mock_bpy.context.scene.keyframe_insert.call_count == expected_calls
