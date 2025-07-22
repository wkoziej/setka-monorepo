# ABOUTME: Tests for animation UI controls and property groups in Blender addon
# ABOUTME: Validates animation parameter controls, add/remove buttons, and property synchronization

"""Tests for animation UI controls in Cinemon addon."""

import pytest
import sys
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add blender_addon to path for testing
addon_path = Path(__file__).parent.parent / "blender_addon"
if str(addon_path) not in sys.path:
    sys.path.insert(0, str(addon_path))


class TestAnimationUIControls:
    """Test UI controls for animation parameters."""
    
    def test_animation_property_group_creation(self, mock_bpy):
        """Test creating property group for single animation."""
        from animation_ui import AnimationPropertyGroup
        
        # Mock property group with animation data
        prop_group = Mock()
        prop_group.animation_type = 'scale'
        prop_group.trigger = 'beat'
        prop_group.intensity = 0.3
        prop_group.enabled = True
        
        # Property should map to dict
        animation_dict = {
            'type': prop_group.animation_type,
            'trigger': prop_group.trigger,
            'intensity': prop_group.intensity,
            'enabled': prop_group.enabled
        }
        
        assert animation_dict['type'] == 'scale'
        assert animation_dict['trigger'] == 'beat'
        assert animation_dict['intensity'] == 0.3
    
    def test_populate_ui_from_strip_animations(self, mock_bpy):
        """Test populating UI controls from strip animations data."""
        from animation_ui import AnimationUIManager
        
        # Mock scene with property collections
        mock_scene = Mock()
        mock_scene.cinemon_animations.clear = Mock()
        
        # Create mock animation items
        anim1 = Mock()
        anim1.animation_type = 'scale'
        anim1.trigger = 'beat'
        anim1.intensity = 0.3
        anim1.enabled = True
        
        anim2 = Mock()
        anim2.animation_type = 'shake'
        anim2.trigger = 'energy_peaks'
        anim2.intensity = 2.0
        anim2.enabled = True
        
        mock_scene.cinemon_animations.add.side_effect = [anim1, anim2]
        
        # Test data
        strip_animations = [
            {'type': 'scale', 'trigger': 'beat', 'intensity': 0.3},
            {'type': 'shake', 'trigger': 'energy_peaks', 'intensity': 2.0}
        ]
        
        ui_manager = AnimationUIManager()
        ui_manager.populate_from_animations(mock_scene, strip_animations)
        
        # Verify clear was called
        mock_scene.cinemon_animations.clear.assert_called_once()
        
        # Verify two animations were added
        assert mock_scene.cinemon_animations.add.call_count == 2
    
    def test_add_new_animation_to_ui(self, mock_bpy):
        """Test adding new animation through UI."""
        from animation_ui import AnimationUIManager
        
        mock_scene = Mock()
        new_anim = Mock()
        new_anim.animation_type = 'rotation'
        new_anim.trigger = 'beat'
        new_anim.degrees = 5.0
        new_anim.enabled = True
        
        mock_scene.cinemon_animations.add.return_value = new_anim
        
        ui_manager = AnimationUIManager()
        result = ui_manager.add_new_animation(mock_scene, 'rotation', 'beat')
        
        assert result is not None
        mock_scene.cinemon_animations.add.assert_called_once()
    
    def test_remove_animation_from_ui(self, mock_bpy):
        """Test removing animation through UI."""
        from animation_ui import AnimationUIManager
        
        mock_scene = Mock()
        mock_scene.cinemon_animations.remove = Mock()
        
        ui_manager = AnimationUIManager()
        ui_manager.remove_animation(mock_scene, 1)  # Remove index 1
        
        mock_scene.cinemon_animations.remove.assert_called_once_with(1)
    
    def test_sync_ui_to_context_manager(self, mock_bpy):
        """Test syncing UI changes to context manager."""
        from animation_ui import AnimationUIManager
        from strip_context import StripContextManager
        
        # Mock scene with animation properties
        mock_scene = Mock()
        
        anim1 = Mock()
        anim1.animation_type = 'scale'
        anim1.trigger = 'beat'
        anim1.intensity = 0.5  # Changed from default
        anim1.enabled = True
        
        anim2 = Mock()
        anim2.animation_type = 'shake'
        anim2.trigger = 'energy_peaks'
        anim2.intensity = 3.0  # Changed from default
        anim2.enabled = False   # Disabled
        
        mock_scene.cinemon_animations = [anim1, anim2]
        
        # Mock context manager
        context_manager = Mock(spec=StripContextManager)
        
        ui_manager = AnimationUIManager()
        animations = ui_manager.extract_animations_from_ui(mock_scene)
        
        # Should extract enabled animations with their parameters
        assert len(animations) == 1  # Only enabled ones
        assert animations[0]['type'] == 'scale'
        assert animations[0]['intensity'] == 0.5
    
    def test_animation_parameter_validation(self, mock_bpy):
        """Test validation of animation parameters."""
        from animation_ui import AnimationUIManager
        
        ui_manager = AnimationUIManager()
        
        # Test valid parameters
        valid_params = {
            'type': 'scale',
            'trigger': 'beat',
            'intensity': 0.3
        }
        assert ui_manager.validate_animation_params(valid_params) == True
        
        # Test invalid trigger
        invalid_trigger = {
            'type': 'scale',
            'trigger': 'invalid_trigger',
            'intensity': 0.3
        }
        assert ui_manager.validate_animation_params(invalid_trigger) == False
        
        # Test invalid animation type
        invalid_type = {
            'type': 'invalid_type',
            'trigger': 'beat',
            'intensity': 0.3
        }
        assert ui_manager.validate_animation_params(invalid_type) == False
    
    def test_parameter_defaults_by_animation_type(self, mock_bpy):
        """Test getting parameter defaults for different animation types."""
        from animation_ui import AnimationUIManager
        
        ui_manager = AnimationUIManager()
        
        # Test scale animation defaults
        scale_defaults = ui_manager.get_parameter_defaults('scale')
        assert 'intensity' in scale_defaults
        assert 'duration_frames' in scale_defaults
        
        # Test brightness_flicker animation defaults
        flicker_defaults = ui_manager.get_parameter_defaults('brightness_flicker')
        assert 'intensity' in flicker_defaults
        assert 'duration_frames' in flicker_defaults
    
    def test_dynamic_parameter_ui_generation(self, mock_bpy):
        """Test generating UI elements based on animation type."""
        from animation_ui import AnimationUIManager
        
        ui_manager = AnimationUIManager()
        
        # Mock layout object
        mock_layout = Mock()
        mock_layout.prop = Mock()
        
        # Mock animation property
        mock_anim = Mock()
        mock_anim.animation_type = 'scale'
        
        # Should generate appropriate UI controls
        ui_manager.draw_animation_parameters(mock_layout, mock_anim)
        
        # Layout.prop should be called for each parameter
        assert mock_layout.prop.call_count >= 1
    
    def test_trigger_dropdown_population(self, mock_bpy):
        """Test populating trigger dropdown with available options."""
        from animation_ui import AnimationUIManager
        
        ui_manager = AnimationUIManager()
        triggers = ui_manager.get_available_triggers()
        
        expected_triggers = ['beat', 'bass', 'energy_peaks', 'one_time', 'continuous']
        for trigger in expected_triggers:
            assert trigger in triggers
    
    def test_animation_type_dropdown_population(self, mock_bpy):
        """Test populating animation type dropdown."""
        from animation_ui import AnimationUIManager
        
        ui_manager = AnimationUIManager()
        types = ui_manager.get_available_animation_types()
        
        expected_types = ['scale', 'shake', 'rotation', 'jitter', 'brightness_flicker', 'visibility']
        for atype in expected_types:
            assert atype in types