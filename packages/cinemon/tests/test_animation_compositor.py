"""Tests for AnimationCompositor implementation."""

from unittest.mock import Mock, patch

import pytest

from vse.animation_compositor import AnimationCompositor
from vse.animations import ScaleAnimation, ShakeAnimation
from vse.layouts import LayoutPosition, RandomLayout


class TestAnimationCompositor:
    """Test suite for AnimationCompositor."""

    @pytest.fixture
    def mock_video_strips(self):
        """Create mock video strips with transform property."""
        strips = []
        for i in range(3):
            strip = Mock()
            strip.name = f"strip_{i}"
            strip.transform = Mock()
            strip.transform.offset_x = 0
            strip.transform.offset_y = 0
            strip.transform.scale_x = 1.0
            strip.transform.scale_y = 1.0
            strip.transform.rotation = 0.0
            strips.append(strip)
        return strips

    @pytest.fixture
    def mock_audio_analysis(self):
        """Create mock audio analysis data."""
        return {
            "duration": 10.0,
            "tempo": {"bpm": 120.0},
            "animation_events": {
                "beats": [1.0, 2.0, 3.0, 4.0],
                "energy_peaks": [1.5, 2.5, 3.5],
                "sections": [
                    {"start": 0.0, "end": 5.0, "label": "intro"},
                    {"start": 5.0, "end": 10.0, "label": "main"}
                ]
            }
        }

    @pytest.fixture
    def simple_layout(self):
        """Create a simple test layout."""
        layout = Mock()
        layout.calculate_positions = Mock(return_value=[
            LayoutPosition(x=100, y=50, scale=0.5),
            LayoutPosition(x=-100, y=-50, scale=0.6),
            LayoutPosition(x=0, y=0, scale=0.7)
        ])
        return layout

    @pytest.fixture
    def simple_animations(self):
        """Create simple test animations."""
        scale_anim = Mock()
        scale_anim.trigger = "bass"
        scale_anim.apply_to_strip = Mock(return_value=True)

        shake_anim = Mock()
        shake_anim.trigger = "beat"
        shake_anim.apply_to_strip = Mock(return_value=True)

        return [scale_anim, shake_anim]

    @patch('vse.animation_compositor.bpy')
    def test_compositor_full_pipeline(self, mock_bpy, mock_video_strips, mock_audio_analysis):
        """Test pełnego pipeline: layout + animacje."""
        # Setup scene resolution
        mock_bpy.context.scene.render.resolution_x = 1920
        mock_bpy.context.scene.render.resolution_y = 1080

        layout = RandomLayout(seed=42)
        animations = [
            ScaleAnimation(trigger="bass", intensity=0.2),
            ShakeAnimation(trigger="beat", intensity=5.0)
        ]

        # Mock keyframe helpers to avoid actual Blender calls
        for anim in animations:
            anim.keyframe_helper = Mock()

        compositor = AnimationCompositor(layout, animations)
        success = compositor.apply(mock_video_strips, mock_audio_analysis, 30)

        assert success
        # Check that positions were set
        for strip in mock_video_strips:
            assert strip.transform.offset_x != 0 or strip.transform.offset_y != 0
            assert 0.3 <= strip.transform.scale_x <= 0.8

    def test_compositor_apply_layout(self, simple_layout, mock_video_strips, mock_audio_analysis):
        """Test że compositor aplikuje layout."""
        compositor = AnimationCompositor(simple_layout, [])
        compositor._get_scene_resolution = Mock(return_value=(1920, 1080))

        success = compositor.apply(mock_video_strips, mock_audio_analysis, 30)

        assert success
        # Check layout was calculated
        simple_layout.calculate_positions.assert_called_once_with(3, (1920, 1080))
        # Check positions were applied
        assert mock_video_strips[0].transform.offset_x == 100
        assert mock_video_strips[0].transform.offset_y == 50
        assert mock_video_strips[0].transform.scale_x == 0.5

    def test_compositor_apply_animations(self, simple_layout, simple_animations,
                                       mock_video_strips, mock_audio_analysis):
        """Test że compositor aplikuje animacje."""
        compositor = AnimationCompositor(simple_layout, simple_animations)
        compositor._get_scene_resolution = Mock(return_value=(1920, 1080))

        success = compositor.apply(mock_video_strips, mock_audio_analysis, 30)

        assert success
        # Check animations were applied to each strip
        for anim in simple_animations:
            assert anim.apply_to_strip.call_count == 3  # Called for each strip

    def test_compositor_extract_events(self):
        """Test ekstrakcji eventów z analizy audio."""
        compositor = AnimationCompositor(Mock(), [])

        audio_analysis = {
            "animation_events": {
                "beats": [1.0, 2.0],
                "energy_peaks": [1.5, 2.5],
                "sections": [{"start": 0, "end": 5}]
            }
        }

        # Test different trigger mappings
        assert compositor._extract_events(audio_analysis, "beat") == [1.0, 2.0]
        assert compositor._extract_events(audio_analysis, "bass") == [1.5, 2.5]
        assert compositor._extract_events(audio_analysis, "energy_peaks") == [1.5, 2.5]
        assert compositor._extract_events(audio_analysis, "sections") == [{"start": 0, "end": 5}]
        assert compositor._extract_events(audio_analysis, "unknown") == []

    def test_compositor_empty_animations(self, simple_layout, mock_video_strips, mock_audio_analysis):
        """Test compositor z pustą listą animacji."""
        compositor = AnimationCompositor(simple_layout, [])
        compositor._get_scene_resolution = Mock(return_value=(1920, 1080))

        success = compositor.apply(mock_video_strips, mock_audio_analysis, 30)

        assert success
        # Only layout should be applied
        simple_layout.calculate_positions.assert_called_once()

    def test_compositor_no_events_for_animation(self, simple_layout, mock_video_strips):
        """Test gdy brak eventów dla animacji."""
        animation = Mock()
        animation.trigger = "non_existent_trigger"
        animation.apply_to_strip = Mock(return_value=True)

        compositor = AnimationCompositor(simple_layout, [animation])
        compositor._get_scene_resolution = Mock(return_value=(1920, 1080))

        audio_analysis = {"animation_events": {}}
        success = compositor.apply(mock_video_strips, audio_analysis, 30)

        assert success
        # Animation should not be called since no events
        animation.apply_to_strip.assert_not_called()

    @patch('vse.animation_compositor.bpy')
    def test_compositor_error_handling(self, mock_bpy, simple_layout, mock_video_strips):
        """Test obsługi błędów."""
        # Simulate error getting resolution
        mock_bpy.context.scene.render.resolution_x = None

        compositor = AnimationCompositor(simple_layout, [])

        # Should handle error gracefully
        success = compositor.apply(mock_video_strips, {}, 30)

        assert not success

    def test_compositor_with_real_components(self, mock_video_strips, mock_audio_analysis):
        """Test z rzeczywistymi komponentami (integration test)."""
        layout = RandomLayout(seed=42, overlap_allowed=False)
        animations = [
            ScaleAnimation(trigger="bass", intensity=0.3),
            ShakeAnimation(trigger="beat", intensity=10.0),
        ]

        # Mock keyframe helpers
        for anim in animations:
            anim.keyframe_helper = Mock()

        compositor = AnimationCompositor(layout, animations)
        compositor._get_scene_resolution = Mock(return_value=(1920, 1080))

        success = compositor.apply(mock_video_strips, mock_audio_analysis, 30)

        assert success
        # Verify animations were called
        for anim in animations:
            assert anim.keyframe_helper.insert_transform_scale_keyframes.called or \
                   anim.keyframe_helper.insert_transform_position_keyframes.called
