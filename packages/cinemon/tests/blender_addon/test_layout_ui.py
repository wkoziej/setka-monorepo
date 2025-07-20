# ABOUTME: Tests for Blender addon layout UI controls and panels
# ABOUTME: Tests layout type selection, parameter controls, and preview updates

"""Tests for layout UI controls in Blender addon."""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add blender_addon to path
addon_path = Path(__file__).parent.parent.parent / "blender_addon"
if str(addon_path) not in sys.path:
    sys.path.insert(0, str(addon_path))


class TestLayoutControlPanel:
    """Test layout control panel functionality."""
    
    def test_layout_panel_properties(self):
        """Test layout panel has required properties."""
        from layout_ui import CINEMON_PT_layout_panel
        
        # Panel should have bl_idname and bl_label
        assert hasattr(CINEMON_PT_layout_panel, 'bl_idname')
        assert hasattr(CINEMON_PT_layout_panel, 'bl_label')
        assert CINEMON_PT_layout_panel.bl_idname == "CINEMON_PT_layout_panel"
        assert "Layout" in CINEMON_PT_layout_panel.bl_label
        
        # Should be in VSE and UI region
        assert CINEMON_PT_layout_panel.bl_space_type == 'SEQUENCE_EDITOR'
        assert CINEMON_PT_layout_panel.bl_region_type == 'UI'
        assert CINEMON_PT_layout_panel.bl_category == "Cinemon"
    
    def test_layout_panel_draw_method(self):
        """Test layout panel draw method structure."""
        from layout_ui import CINEMON_PT_layout_panel
        
        panel_class = CINEMON_PT_layout_panel
        
        # Should have draw method
        assert hasattr(panel_class, 'draw')
        assert callable(panel_class.draw)
        
        # Test draw method doesn't crash with mock context
        panel = panel_class()
        mock_context = Mock()
        mock_context.scene = Mock()
        
        # Mock layout type property
        mock_context.scene.cinemon_layout_type = "random"
        
        # Should not raise exception
        try:
            panel.draw(mock_context)
        except AttributeError:
            # Expected in test environment without proper bpy mocking
            pass


class TestLayoutTypeOperator:
    """Test layout type selection operator."""
    
    def test_layout_type_operator_properties(self):
        """Test layout type operator has required properties."""
        from layout_ui import CINEMON_OT_set_layout_type
        
        # Operator should have bl_idname and bl_label
        assert hasattr(CINEMON_OT_set_layout_type, 'bl_idname')
        assert hasattr(CINEMON_OT_set_layout_type, 'bl_label')
        assert CINEMON_OT_set_layout_type.bl_idname == "cinemon.set_layout_type"
        assert "Layout" in CINEMON_OT_set_layout_type.bl_label
        
        # Should have layout_type property
        operator = CINEMON_OT_set_layout_type()
        operator.layout_type = "random"
        assert operator.layout_type == "random"
    
    def test_layout_type_execute_random(self):
        """Test layout type operator execute with random type."""
        from layout_ui import CINEMON_OT_set_layout_type
        
        operator = CINEMON_OT_set_layout_type()
        operator.layout_type = "random"
        
        mock_context = Mock()
        mock_context.scene = Mock()
        
        with patch.object(operator, 'report') as mock_report:
            result = operator.execute(mock_context)
            
            # Should set layout type in scene
            assert mock_context.scene.cinemon_layout_type == "random"
            
            # Should return FINISHED
            assert result == {'FINISHED'}
    
    def test_layout_type_execute_grid(self):
        """Test layout type operator execute with grid type."""
        from layout_ui import CINEMON_OT_set_layout_type
        
        operator = CINEMON_OT_set_layout_type()
        operator.layout_type = "grid"
        
        mock_context = Mock()
        mock_context.scene = Mock()
        
        with patch.object(operator, 'report') as mock_report:
            result = operator.execute(mock_context)
            
            # Should set layout type in scene
            assert mock_context.scene.cinemon_layout_type == "grid"
            
            # Should return FINISHED
            assert result == {'FINISHED'}


class TestLayoutParameterOperators:
    """Test layout parameter control operators."""
    
    def test_random_layout_params_operator(self):
        """Test random layout parameters operator."""
        from layout_ui import CINEMON_OT_set_random_params
        
        operator = CINEMON_OT_set_random_params()
        operator.margin = 0.15
        operator.seed = 42
        operator.overlap_allowed = True
        
        mock_context = Mock()
        mock_context.scene = Mock()
        
        with patch.object(operator, 'report') as mock_report:
            result = operator.execute(mock_context)
            
            # Should set parameters in scene
            assert mock_context.scene.cinemon_random_margin == 0.15
            assert mock_context.scene.cinemon_random_seed == 42
            assert mock_context.scene.cinemon_random_overlap == True
            
            # Should return FINISHED
            assert result == {'FINISHED'}
    
    def test_grid_layout_params_operator(self):
        """Test grid layout parameters operator."""
        from layout_ui import CINEMON_OT_set_grid_params
        
        operator = CINEMON_OT_set_grid_params()
        operator.rows = 2
        operator.columns = 2
        operator.gap = 0.05
        
        mock_context = Mock()
        mock_context.scene = Mock()
        
        with patch.object(operator, 'report') as mock_report:
            result = operator.execute(mock_context)
            
            # Should set parameters in scene
            assert mock_context.scene.cinemon_grid_rows == 2
            assert mock_context.scene.cinemon_grid_columns == 2
            assert mock_context.scene.cinemon_grid_gap == 0.05
            
            # Should return FINISHED
            assert result == {'FINISHED'}


class TestLayoutPreviewOperator:
    """Test layout preview functionality."""
    
    def test_preview_layout_operator_properties(self):
        """Test preview layout operator has required properties."""
        from layout_ui import CINEMON_OT_preview_layout
        
        # Operator should have bl_idname and bl_label
        assert hasattr(CINEMON_OT_preview_layout, 'bl_idname')
        assert hasattr(CINEMON_OT_preview_layout, 'bl_label')
        assert CINEMON_OT_preview_layout.bl_idname == "cinemon.preview_layout"
        assert "Preview" in CINEMON_OT_preview_layout.bl_label
    
    def test_preview_layout_execute_random(self):
        """Test preview layout operator with random layout."""
        from layout_ui import CINEMON_OT_preview_layout
        
        operator = CINEMON_OT_preview_layout()
        
        mock_context = Mock()
        mock_context.scene = Mock()
        mock_context.scene.cinemon_layout_type = "random"
        mock_context.scene.cinemon_random_margin = 0.1
        mock_context.scene.cinemon_random_seed = 42
        mock_context.scene.cinemon_random_overlap = False
        
        # Mock sequence editor
        mock_sequencer = Mock()
        mock_context.scene.sequence_editor = mock_sequencer
        mock_sequencer.sequences = []
        
        with patch('layout_ui.RandomLayout') as mock_layout_class:
            mock_layout = Mock()
            mock_layout_class.return_value = mock_layout
            mock_layout.generate_positions.return_value = []
            
            with patch.object(operator, 'report') as mock_report:
                result = operator.execute(mock_context)
                
                # Should create RandomLayout with correct parameters
                mock_layout_class.assert_called_once_with(
                    margin=0.1, seed=42, overlap_allowed=False
                )
                
                # Should call generate_positions
                mock_layout.generate_positions.assert_called_once()
                
                # Should return FINISHED
                assert result == {'FINISHED'}
    
    def test_preview_layout_execute_grid(self):
        """Test preview layout operator with grid layout."""
        from layout_ui import CINEMON_OT_preview_layout
        
        operator = CINEMON_OT_preview_layout()
        
        mock_context = Mock()
        mock_context.scene = Mock()
        mock_context.scene.cinemon_layout_type = "grid"
        mock_context.scene.cinemon_grid_rows = 2
        mock_context.scene.cinemon_grid_columns = 2
        mock_context.scene.cinemon_grid_gap = 0.05
        
        # Mock sequence editor
        mock_sequencer = Mock()
        mock_context.scene.sequence_editor = mock_sequencer
        mock_sequencer.sequences = []
        
        with patch('layout_ui.GridLayout') as mock_layout_class:
            mock_layout = Mock()
            mock_layout_class.return_value = mock_layout
            mock_layout.generate_positions.return_value = []
            
            with patch.object(operator, 'report') as mock_report:
                result = operator.execute(mock_context)
                
                # Should create GridLayout with correct parameters
                mock_layout_class.assert_called_once_with(
                    rows=2, columns=2, gap=0.05
                )
                
                # Should call generate_positions
                mock_layout.generate_positions.assert_called_once()
                
                # Should return FINISHED
                assert result == {'FINISHED'}


class TestLayoutUIIntegration:
    """Test layout UI integration with main addon."""
    
    def test_layout_ui_can_be_imported(self):
        """Test that layout UI can be imported without bpy errors."""
        # This test ensures layout UI can be imported in test environment
        from layout_ui import (
            CINEMON_PT_layout_panel,
            CINEMON_OT_set_layout_type,
            CINEMON_OT_set_random_params,
            CINEMON_OT_set_grid_params,
            CINEMON_OT_preview_layout
        )
        
        assert CINEMON_PT_layout_panel is not None
        assert CINEMON_OT_set_layout_type is not None
        assert CINEMON_OT_set_random_params is not None
        assert CINEMON_OT_set_grid_params is not None
        assert CINEMON_OT_preview_layout is not None
    
    def test_layout_classes_have_registration_methods(self):
        """Test layout classes have required registration methods."""
        from layout_ui import (
            CINEMON_PT_layout_panel,
            CINEMON_OT_set_layout_type,
            CINEMON_OT_set_random_params,
            CINEMON_OT_set_grid_params,
            CINEMON_OT_preview_layout
        )
        
        # All classes should have bl_idname and proper structure
        for cls in [CINEMON_PT_layout_panel, CINEMON_OT_set_layout_type, 
                   CINEMON_OT_set_random_params, CINEMON_OT_set_grid_params,
                   CINEMON_OT_preview_layout]:
            assert hasattr(cls, 'bl_idname')
            assert hasattr(cls, 'bl_label')
    
    def test_layout_registration_functions(self):
        """Test layout UI has registration functions."""
        import layout_ui
        
        assert hasattr(layout_ui, 'register')
        assert hasattr(layout_ui, 'unregister')
        assert callable(layout_ui.register)
        assert callable(layout_ui.unregister)
    
    @patch('bpy.utils.register_class')
    def test_layout_register_calls(self, mock_register):
        """Test layout_ui.register() calls bpy.utils.register_class."""
        import layout_ui
        
        layout_ui.register()
        
        # Should register classes from layout_ui.classes
        assert mock_register.call_count == len(layout_ui.classes)
    
    @patch('bpy.utils.unregister_class')
    def test_layout_unregister_calls(self, mock_unregister):
        """Test layout_ui.unregister() calls bpy.utils.unregister_class."""
        import layout_ui
        
        layout_ui.unregister()
        
        # Should unregister classes from layout_ui.classes
        assert mock_unregister.call_count == len(layout_ui.classes)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])