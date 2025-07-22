# ABOUTME: Tests for Apply system that buffers changes and regenerates animations for modified strips
# ABOUTME: Validates change detection, selective regeneration, and VSE integration

"""Tests for Apply system in Cinemon addon."""

import pytest
import sys
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add blender_addon to path for testing
addon_path = Path(__file__).parent.parent / "blender_addon"
if str(addon_path) not in sys.path:
    sys.path.insert(0, str(addon_path))


class TestApplySystem:
    """Test Apply system for buffered changes and selective regeneration."""
    
    def test_detect_pending_changes(self, mock_bpy):
        """Test detection of pending changes in buffer."""
        from strip_context import StripContextManager
        
        manager = StripContextManager()
        
        # Initially no changes
        assert manager.has_pending_changes() == False
        assert manager.get_changed_strips() == []
        
        # Mock active strip and add animation
        mock_strip = Mock()
        mock_strip.name = "Camera1"
        mock_bpy.context.scene.sequence_editor.active_strip = mock_strip
        
        manager.load_config({'strip_animations': {}})
        
        # Add animation - should create pending change
        new_anim = {'type': 'scale', 'trigger': 'beat', 'intensity': 0.5}
        manager.add_animation_to_active_strip(new_anim)
        
        assert manager.has_pending_changes() == True
        assert "Camera1" in manager.get_changed_strips()
    
    def test_apply_changes_to_config(self, mock_bpy):
        """Test applying buffered changes to main config."""
        from strip_context import StripContextManager
        
        manager = StripContextManager()
        
        # Initial config
        initial_config = {
            'strip_animations': {
                'Camera1': [
                    {'type': 'shake', 'trigger': 'energy_peaks', 'intensity': 1.0}
                ]
            }
        }
        manager.load_config(initial_config)
        
        # Mock active strip and modify animation
        mock_strip = Mock()
        mock_strip.name = "Camera1"
        mock_bpy.context.scene.sequence_editor.active_strip = mock_strip
        
        # Update animation parameter
        manager.update_animation_parameter(0, 'intensity', 2.0)
        
        # Apply changes
        updated_config = manager.apply_changes()
        
        # Verify changes were applied
        assert updated_config['strip_animations']['Camera1'][0]['intensity'] == 2.0
        
        # Buffer should be cleared
        assert manager.has_pending_changes() == False
    
    def test_discard_pending_changes(self, mock_bpy):
        """Test discarding pending changes without applying."""
        from strip_context import StripContextManager
        
        manager = StripContextManager()
        manager.load_config({'strip_animations': {}})
        
        # Mock active strip and add animation
        mock_strip = Mock()
        mock_strip.name = "Camera1"
        mock_bpy.context.scene.sequence_editor.active_strip = mock_strip
        
        new_anim = {'type': 'scale', 'trigger': 'beat', 'intensity': 0.5}
        manager.add_animation_to_active_strip(new_anim)
        
        # Should have pending changes
        assert manager.has_pending_changes() == True
        
        # Discard changes
        manager.discard_changes()
        
        # No more pending changes
        assert manager.has_pending_changes() == False
        assert manager.get_changed_strips() == []
    
    def test_get_current_config_with_buffer(self, mock_bpy):
        """Test getting current config with buffered changes applied temporarily."""
        from strip_context import StripContextManager
        
        manager = StripContextManager()
        
        # Initial config
        initial_config = {
            'strip_animations': {
                'Camera1': [
                    {'type': 'shake', 'trigger': 'energy_peaks', 'intensity': 1.0}
                ]
            }
        }
        manager.load_config(initial_config)
        
        # Mock active strip and modify
        mock_strip = Mock()
        mock_strip.name = "Camera1"
        mock_bpy.context.scene.sequence_editor.active_strip = mock_strip
        
        # Add new animation (buffered)
        new_anim = {'type': 'scale', 'trigger': 'beat', 'intensity': 0.5}
        manager.add_animation_to_active_strip(new_anim)
        
        # Get current config (should include buffered changes)
        current_config = manager.get_current_config()
        
        # Should have both original and new animation
        camera1_anims = current_config['strip_animations']['Camera1']
        assert len(camera1_anims) == 2
        assert any(anim['type'] == 'shake' for anim in camera1_anims)
        assert any(anim['type'] == 'scale' for anim in camera1_anims)
        
        # Original config should be unchanged
        original_camera1_anims = manager.config['strip_animations']['Camera1']
        assert len(original_camera1_anims) == 1
        assert original_camera1_anims[0]['type'] == 'shake'
    
    def test_apply_operator_integration(self, mock_bpy):
        """Test Apply operator that regenerates animations."""
        from apply_system import CINEMON_OT_apply_changes
        
        # Mock operator context
        operator = CINEMON_OT_apply_changes()
        operator.report = Mock()  # Mock Blender's report method
        mock_context = Mock()
        mock_context.scene = Mock()
        
        # Mock strip context manager with changes
        with patch('apply_system.get_strip_context_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_manager.has_pending_changes.return_value = True
            mock_manager.get_changed_strips.return_value = ['Camera1', 'Camera2']
            mock_manager.apply_changes.return_value = {'strip_animations': {'Camera1': []}}
            mock_get_manager.return_value = mock_manager
            
            # Mock animation regenerator
            with patch('apply_system.regenerate_animations_for_strips') as mock_regen:
                result = operator.execute(mock_context)
                
                # Should succeed
                assert result == {'FINISHED'}
                
                # Should regenerate only changed strips
                mock_regen.assert_called_once_with(['Camera1', 'Camera2'], {'strip_animations': {'Camera1': []}})
    
    def test_apply_operator_no_changes(self, mock_bpy):
        """Test Apply operator when no changes pending."""
        from apply_system import CINEMON_OT_apply_changes
        
        operator = CINEMON_OT_apply_changes()
        operator.report = Mock()  # Mock Blender's report method
        mock_context = Mock()
        
        # Mock strip context manager with no changes
        with patch('apply_system.get_strip_context_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_manager.has_pending_changes.return_value = False
            mock_get_manager.return_value = mock_manager
            
            result = operator.execute(mock_context)
            
            # Should still succeed but do nothing
            assert result == {'FINISHED'}
    
    def test_ui_sync_with_apply_system(self, mock_bpy):
        """Test UI synchronization with apply system."""
        from apply_system import ApplyUIManager
        
        ui_manager = ApplyUIManager()
        mock_scene = Mock()
        
        # Mock pending changes indicator
        with patch('apply_system.get_strip_context_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_manager.has_pending_changes.return_value = True
            mock_manager.get_changed_strips.return_value = ['Camera1']
            mock_get_manager.return_value = mock_manager
            
            # Should indicate pending changes
            has_changes = ui_manager.has_pending_changes()
            changed_strips = ui_manager.get_changed_strips()
            
            assert has_changes == True
            assert 'Camera1' in changed_strips
    
    def test_error_handling_in_apply(self, mock_bpy):
        """Test error handling during apply operation."""
        from apply_system import CINEMON_OT_apply_changes
        
        operator = CINEMON_OT_apply_changes()
        operator.report = Mock()  # Mock Blender's report method
        mock_context = Mock()
        
        # Mock strip context manager that raises exception
        with patch('apply_system.get_strip_context_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_manager.has_pending_changes.return_value = True
            mock_manager.apply_changes.side_effect = Exception("Test error")
            mock_get_manager.return_value = mock_manager
            
            result = operator.execute(mock_context)
            
            # Should handle error gracefully
            assert result == {'CANCELLED'}