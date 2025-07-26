"""Tests for ScaleAnimation implementation."""

from unittest.mock import Mock

import pytest

from blender.vse.animations import ScaleAnimation


class TestScaleAnimation:
    """Test suite for ScaleAnimation."""

    @pytest.fixture
    def mock_strip(self):
        """Create a mock video strip with transform property."""
        strip = Mock()
        strip.name = "test_strip"
        strip.transform = Mock()
        strip.transform.scale_x = 1.0
        strip.transform.scale_y = 1.0
        return strip

    @pytest.fixture
    def mock_strip_no_transform(self):
        """Create a mock video strip without transform property."""
        strip = Mock()
        strip.name = "test_strip_no_transform"
        # Explicitly remove transform attribute
        if hasattr(strip, 'transform'):
            delattr(strip, 'transform')
        return strip

    @pytest.fixture
    def scale_animation(self):
        """Create ScaleAnimation instance with mocked keyframe helper."""
        animation = ScaleAnimation(trigger="bass", intensity=0.3, duration_frames=2)
        animation.keyframe_helper = Mock()
        return animation

    def test_scale_animation_basic(self, scale_animation, mock_strip):
        """Test podstawowej animacji skali."""
        events = [1.0, 2.0, 3.0]  # Sekundy
        fps = 30

        success = scale_animation.apply_to_strip(mock_strip, events, fps)

        assert success
        # Sprawdź czy keyframes zostały dodane (3 eventy * 2 keyframes każdy = 6)
        assert scale_animation.keyframe_helper.insert_transform_scale_keyframes.call_count >= 6
        # Końcowa wartość powinna wrócić do 1.0
        assert mock_strip.transform.scale_x == 1.0
        assert mock_strip.transform.scale_y == 1.0

    def test_scale_animation_intensity(self, mock_strip):
        """Test że intensity właściwie skaluje wartości."""
        animation = ScaleAnimation(intensity=0.5)  # 50% większe
        animation.keyframe_helper = Mock()

        events = [1.0]
        fps = 30

        animation.apply_to_strip(mock_strip, events, fps)

        # Sprawdź czy scale był ustawiony na 1.5 (1.0 + 0.5)
        calls = animation.keyframe_helper.insert_transform_scale_keyframes.call_args_list
        # Drugi call powinien mieć scale 1.5
        assert calls[1][0][2] == 1.5  # scale_x
        assert calls[1][0][3] == 1.5  # scale_y

    def test_scale_animation_without_transform(self, scale_animation, mock_strip_no_transform):
        """Test animacji na stripie bez transform."""
        events = [1.0]

        success = scale_animation.apply_to_strip(mock_strip_no_transform, events, 30)

        assert not success  # Powinno zwrócić False
        # Keyframes nie powinny być dodane
        scale_animation.keyframe_helper.insert_transform_scale_keyframes.assert_not_called()

    def test_scale_animation_empty_events(self, scale_animation, mock_strip):
        """Test z pustą listą eventów."""
        events = []

        success = scale_animation.apply_to_strip(mock_strip, events, 30)

        assert success  # Powinno się udać, ale nic nie zrobić
        # Tylko początkowy keyframe
        assert scale_animation.keyframe_helper.insert_transform_scale_keyframes.call_count == 1

    def test_scale_animation_duration_frames(self, mock_strip):
        """Test że duration_frames kontroluje czas powrotu."""
        animation = ScaleAnimation(duration_frames=5)
        animation.keyframe_helper = Mock()

        events = [1.0]  # Event at 1 second
        fps = 30

        animation.apply_to_strip(mock_strip, events, fps)

        calls = animation.keyframe_helper.insert_transform_scale_keyframes.call_args_list
        # Pierwszy keyframe at frame 1
        assert calls[0][0][1] == 1
        # Scale up at frame 30 (1 second * 30 fps)
        assert calls[1][0][1] == 30
        # Return to normal at frame 35 (30 + 5 duration_frames)
        assert calls[2][0][1] == 35

    def test_scale_animation_required_properties(self, scale_animation):
        """Test że animacja wymaga właściwej property."""
        required = scale_animation.get_required_properties()

        assert 'transform' in required
        assert len(required) >= 1

    def test_scale_animation_can_apply(self, scale_animation, mock_strip, mock_strip_no_transform):
        """Test metody can_apply_to_strip."""
        assert scale_animation.can_apply_to_strip(mock_strip) is True
        assert scale_animation.can_apply_to_strip(mock_strip_no_transform) is False

    def test_scale_animation_preserves_base_scale(self, mock_strip):
        """Test że animacja zachowuje bazową skalę stripu."""
        # Ustaw niestandardową bazową skalę
        mock_strip.transform.scale_x = 0.5
        mock_strip.transform.scale_y = 0.5

        animation = ScaleAnimation(intensity=0.2)  # 20% większe
        animation.keyframe_helper = Mock()

        events = [1.0]
        animation.apply_to_strip(mock_strip, events, 30)

        calls = animation.keyframe_helper.insert_transform_scale_keyframes.call_args_list
        # Powinno skalować od 0.5 do 0.6 (0.5 * 1.2)
        assert calls[1][0][2] == 0.6  # scale_x
        assert calls[1][0][3] == 0.6  # scale_y
        # I wrócić do 0.5
        assert calls[2][0][2] == 0.5
        assert calls[2][0][3] == 0.5
