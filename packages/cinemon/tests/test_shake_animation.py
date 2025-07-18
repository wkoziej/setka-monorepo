"""Tests for ShakeAnimation implementation."""

import pytest
from unittest.mock import Mock, patch
from blender.vse.animations.shake_animation import ShakeAnimation


class TestShakeAnimation:
    """Test suite for ShakeAnimation."""
    
    @pytest.fixture
    def mock_strip(self):
        """Create a mock video strip with transform property."""
        strip = Mock()
        strip.name = "test_strip"
        strip.transform = Mock()
        strip.transform.offset_x = 0.0
        strip.transform.offset_y = 0.0
        return strip
    
    @pytest.fixture
    def shake_animation(self):
        """Create ShakeAnimation instance with mocked keyframe helper."""
        animation = ShakeAnimation(
            trigger="beat", 
            intensity=10.0, 
            return_frames=2,
            random_direction=True
        )
        animation.keyframe_helper = Mock()
        return animation
    
    def test_shake_animation_random(self, shake_animation, mock_strip):
        """Test losowych drgań."""
        events = [1.0, 2.0]
        fps = 30
        
        success = shake_animation.apply_to_strip(mock_strip, events, fps)
        
        assert success
        # Should have initial keyframe + 2 events * 2 keyframes each = 5 total
        assert shake_animation.keyframe_helper.insert_transform_position_keyframes.call_count >= 5
        # Final position should return to (0, 0)
        assert mock_strip.transform.offset_x == 0
        assert mock_strip.transform.offset_y == 0
    
    @patch('random.uniform')
    def test_shake_animation_intensity(self, mock_random, mock_strip):
        """Test że intensity kontroluje wielkość drgań."""
        mock_random.side_effect = [5.0, -5.0, -8.0, 8.0]  # Kontrolowane wartości
        
        animation = ShakeAnimation(intensity=10.0, random_direction=True)
        animation.keyframe_helper = Mock()
        
        events = [1.0]
        animation.apply_to_strip(mock_strip, events, 30)
        
        # Check that random.uniform was called with correct intensity range
        mock_random.assert_called_with(-10.0, 10.0)
        assert mock_random.call_count == 2  # x and y
    
    def test_shake_animation_deterministic(self, mock_strip):
        """Test deterministycznych drgań (tylko poziome)."""
        animation = ShakeAnimation(
            intensity=5.0, 
            random_direction=False,
            return_frames=3
        )
        animation.keyframe_helper = Mock()
        
        events = [1.0, 2.0]
        animation.apply_to_strip(mock_strip, events, 30)
        
        calls = animation.keyframe_helper.insert_transform_position_keyframes.call_args_list
        
        # For deterministic shake, all shakes should be horizontal only
        # Check the shake keyframes (not initial or return frames)
        for i in [1, 3]:  # Shake frames
            call = calls[i]
            strip_arg = call[0][0]
            # In deterministic mode, y should not change
            assert mock_strip.transform.offset_y == 0
    
    def test_shake_animation_return_frames(self, mock_strip):
        """Test że return_frames kontroluje czas powrotu."""
        animation = ShakeAnimation(return_frames=5)
        animation.keyframe_helper = Mock()
        
        events = [1.0]  # Event at 1 second
        fps = 30
        
        animation.apply_to_strip(mock_strip, events, fps)
        
        calls = animation.keyframe_helper.insert_transform_position_keyframes.call_args_list
        # Initial keyframe at frame 1
        assert calls[0][0][1] == 1
        # Shake at frame 30 (1 second * 30 fps)
        assert calls[1][0][1] == 30
        # Return at frame 35 (30 + 5 return_frames)
        assert calls[2][0][1] == 35
    
    def test_shake_animation_without_transform(self):
        """Test animacji na stripie bez transform."""
        strip = Mock()
        strip.name = "no_transform"
        if hasattr(strip, 'transform'):
            delattr(strip, 'transform')
        
        animation = ShakeAnimation()
        animation.keyframe_helper = Mock()
        
        success = animation.apply_to_strip(strip, [1.0], 30)
        
        assert not success
        animation.keyframe_helper.insert_transform_position_keyframes.assert_not_called()
    
    def test_shake_animation_preserves_base_position(self, mock_strip):
        """Test że animacja zachowuje bazową pozycję stripu."""
        # Set custom base position
        mock_strip.transform.offset_x = 100.0
        mock_strip.transform.offset_y = -50.0
        
        animation = ShakeAnimation(intensity=10.0)
        animation.keyframe_helper = Mock()
        
        events = [1.0]
        animation.apply_to_strip(mock_strip, events, 30)
        
        # After animation, should return to base position
        assert mock_strip.transform.offset_x == 100.0
        assert mock_strip.transform.offset_y == -50.0
    
    def test_shake_animation_empty_events(self, shake_animation, mock_strip):
        """Test z pustą listą eventów."""
        events = []
        
        success = shake_animation.apply_to_strip(mock_strip, events, 30)
        
        assert success
        # Only initial keyframe should be set
        assert shake_animation.keyframe_helper.insert_transform_position_keyframes.call_count == 1
    
    def test_shake_animation_required_properties(self, shake_animation):
        """Test że animacja wymaga właściwej property."""
        required = shake_animation.get_required_properties()
        
        assert 'transform' in required
        assert len(required) >= 1