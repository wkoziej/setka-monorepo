# ABOUTME: Tests for detecting active/selected strip in VSE timeline
# ABOUTME: Validates context-aware UI panel updates based on strip selection

"""Tests for active strip detection in Blender VSE."""

import pytest
import sys
from unittest.mock import Mock, patch
from pathlib import Path

# Add blender_addon to path for testing
addon_path = Path(__file__).parent.parent / "blender_addon"
if str(addon_path) not in sys.path:
    sys.path.insert(0, str(addon_path))


class TestActiveStripDetection:
    """Test detection of active strip in VSE timeline."""
    
    def test_get_active_strip_name_with_selection(self, mock_bpy):
        """Test getting active strip name when strip is selected."""
        from strip_context import StripContextManager
        
        # Setup mock VSE sequence with selected strip
        mock_strip = Mock()
        mock_strip.name = "Camera1"
        mock_strip.type = 'MOVIE'
        mock_bpy.context.scene.sequence_editor.active_strip = mock_strip
        
        manager = StripContextManager()
        active_name = manager.get_active_strip_name()
        
        assert active_name == "Camera1"
    
    def test_get_active_strip_name_no_selection(self, mock_bpy):
        """Test getting active strip name when no strip selected."""
        from strip_context import StripContextManager
        
        # No active strip
        mock_bpy.context.scene.sequence_editor.active_strip = None
        
        manager = StripContextManager()
        active_name = manager.get_active_strip_name()
        
        assert active_name is None
    
    def test_get_active_strip_name_no_sequencer(self, mock_bpy):
        """Test when no sequence editor exists."""
        from strip_context import StripContextManager
        
        # No sequence editor
        mock_bpy.context.scene.sequence_editor = None
        
        manager = StripContextManager()
        active_name = manager.get_active_strip_name()
        
        assert active_name is None
    
    def test_get_strips_animations_for_active(self, mock_bpy):
        """Test getting animations for currently active strip."""
        from strip_context import StripContextManager
        
        # Mock config with strip animations
        test_config = {
            'strip_animations': {
                'Camera1': [
                    {'type': 'scale', 'trigger': 'beat', 'intensity': 0.3},
                    {'type': 'shake', 'trigger': 'energy_peaks', 'intensity': 2.0}
                ],
                'Camera2': [
                    {'type': 'vintage_color', 'trigger': 'one_time', 'sepia_amount': 0.4}
                ]
            }
        }
        
        # Active strip is Camera1
        mock_strip = Mock()
        mock_strip.name = "Camera1"
        mock_bpy.context.scene.sequence_editor.active_strip = mock_strip
        
        manager = StripContextManager()
        manager.load_config(test_config)
        
        animations = manager.get_active_strip_animations()
        
        assert len(animations) == 2
        assert animations[0]['type'] == 'scale'
        assert animations[1]['type'] == 'shake'
    
    def test_get_strips_animations_no_active(self, mock_bpy):
        """Test getting animations when no strip is active."""
        from strip_context import StripContextManager
        
        test_config = {
            'strip_animations': {
                'Camera1': [{'type': 'scale', 'trigger': 'beat', 'intensity': 0.3}]
            }
        }
        
        # No active strip
        mock_bpy.context.scene.sequence_editor.active_strip = None
        
        manager = StripContextManager()
        manager.load_config(test_config)
        
        animations = manager.get_active_strip_animations()
        
        assert animations == []
    
    def test_add_animation_to_active_strip(self, mock_bpy):
        """Test adding animation to currently active strip."""
        from strip_context import StripContextManager
        
        test_config = {
            'strip_animations': {
                'Camera1': [
                    {'type': 'scale', 'trigger': 'beat', 'intensity': 0.3}
                ]
            }
        }
        
        # Active strip is Camera1
        mock_strip = Mock()
        mock_strip.name = "Camera1"
        mock_bpy.context.scene.sequence_editor.active_strip = mock_strip
        
        manager = StripContextManager()
        manager.load_config(test_config)
        
        new_animation = {'type': 'shake', 'trigger': 'energy_peaks', 'intensity': 2.0}
        manager.add_animation_to_active_strip(new_animation)
        
        animations = manager.get_active_strip_animations()
        assert len(animations) == 2
        assert animations[1] == new_animation
    
    def test_remove_animation_from_active_strip(self, mock_bpy):
        """Test removing animation from currently active strip."""
        from strip_context import StripContextManager
        
        test_config = {
            'strip_animations': {
                'Camera1': [
                    {'type': 'scale', 'trigger': 'beat', 'intensity': 0.3},
                    {'type': 'shake', 'trigger': 'energy_peaks', 'intensity': 2.0}
                ]
            }
        }
        
        # Active strip is Camera1
        mock_strip = Mock()
        mock_strip.name = "Camera1"
        mock_bpy.context.scene.sequence_editor.active_strip = mock_strip
        
        manager = StripContextManager()
        manager.load_config(test_config)
        
        # Remove first animation (index 0)
        manager.remove_animation_from_active_strip(0)
        
        animations = manager.get_active_strip_animations()
        assert len(animations) == 1
        assert animations[0]['type'] == 'shake'
    
    def test_update_animation_parameter(self, mock_bpy):
        """Test updating animation parameter for active strip."""
        from strip_context import StripContextManager
        
        test_config = {
            'strip_animations': {
                'Camera1': [
                    {'type': 'scale', 'trigger': 'beat', 'intensity': 0.3}
                ]
            }
        }
        
        # Active strip is Camera1
        mock_strip = Mock()
        mock_strip.name = "Camera1"
        mock_bpy.context.scene.sequence_editor.active_strip = mock_strip
        
        manager = StripContextManager()
        manager.load_config(test_config)
        
        # Update intensity of first animation
        manager.update_animation_parameter(0, 'intensity', 0.5)
        
        animations = manager.get_active_strip_animations()
        assert animations[0]['intensity'] == 0.5
    
    def test_get_available_animation_types(self):
        """Test getting list of available animation types."""
        from strip_context import StripContextManager
        
        manager = StripContextManager()
        animation_types = manager.get_available_animation_types()
        
        expected_types = [
            'scale', 'shake', 'rotation', 'jitter',
            'brightness_flicker', 'visibility'
        ]
        
        for atype in expected_types:
            assert atype in animation_types
    
    def test_get_available_triggers(self):
        """Test getting list of available animation triggers."""
        from strip_context import StripContextManager
        
        manager = StripContextManager()
        triggers = manager.get_available_triggers()
        
        expected_triggers = ['beat', 'bass', 'energy_peaks', 'one_time', 'continuous']
        
        for trigger in expected_triggers:
            assert trigger in triggers