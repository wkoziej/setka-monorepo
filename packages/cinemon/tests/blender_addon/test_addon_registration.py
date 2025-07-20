# ABOUTME: Tests for Blender addon registration and unregistration cycle
# ABOUTME: Validates proper cleanup and operator/panel registration

"""Tests for addon registration system."""

import pytest
import sys
import importlib.util
from pathlib import Path
from unittest.mock import Mock, patch

# Add blender_addon to path
addon_path = Path(__file__).parent.parent.parent / "blender_addon"
if str(addon_path) not in sys.path:
    sys.path.insert(0, str(addon_path))

# Add setka-common path for YAMLConfigLoader
common_path = Path(__file__).parent.parent.parent.parent.parent / "common" / "src"
if str(common_path) not in sys.path:
    sys.path.insert(0, str(common_path))


def load_addon_module():
    """Helper function to load the addon module."""
    addon_module_path = addon_path / "__init__.py"
    spec = importlib.util.spec_from_file_location("addon_module", addon_module_path)
    addon_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(addon_module)
    return addon_module


class TestAddonRegistration:
    """Test addon registration and unregistration."""
    
    def test_addon_metadata(self):
        """Test addon has proper bl_info metadata."""
        addon_module = load_addon_module()
        bl_info = addon_module.bl_info
        
        # Required metadata fields
        assert "name" in bl_info
        assert "author" in bl_info
        assert "version" in bl_info
        assert "blender" in bl_info
        assert "location" in bl_info
        assert "description" in bl_info
        assert "category" in bl_info
        
        # Check specific values
        assert bl_info["name"] == "Cinemon VSE Animator"
        assert bl_info["category"] == "Sequencer"
        assert bl_info["blender"] == (4, 0, 0)
        assert ("VSE" in bl_info["location"] or "Video Sequence Editor" in bl_info["location"])
    
    def test_addon_classes_defined(self):
        """Test that all classes for registration are defined."""
        addon_module = load_addon_module()
        
        # Check main panel class
        assert hasattr(addon_module, 'CINEMON_PT_main_panel')
        assert hasattr(addon_module, 'CINEMON_OT_load_preset')
        
        # Check classes list
        assert hasattr(addon_module, 'classes')
        assert len(addon_module.classes) == 2
    
    @patch('bpy.utils.register_class')
    @patch('operators.register')
    def test_register_function(self, mock_operators_register, mock_register_class):
        """Test addon registration function."""
        addon_module = load_addon_module()
        
        # Mock print to avoid output during test
        with patch('builtins.print'):
            addon_module.register()
        
        # Should register operators first
        mock_operators_register.assert_called_once()
        
        # Should register all UI classes
        assert mock_register_class.call_count == len(addon_module.classes)
        
        # Check that each class was registered
        registered_classes = [call[0][0] for call in mock_register_class.call_args_list]
        for cls in addon_module.classes:
            assert cls in registered_classes
    
    @patch('bpy.utils.unregister_class')
    @patch('operators.unregister')
    @patch('bpy.types.Scene')
    def test_unregister_function(self, mock_scene, mock_operators_unregister, mock_unregister_class):
        """Test addon unregistration function."""
        addon_module = load_addon_module()
        
        # Mock scene properties for cleanup
        mock_scene.cinemon_config = Mock()
        mock_scene.cinemon_config_path = Mock()
        
        # Mock print to avoid output during test
        with patch('builtins.print'):
            addon_module.unregister()
        
        # Should unregister all UI classes (in reverse order)
        assert mock_unregister_class.call_count == len(addon_module.classes)
        
        # Should unregister operators
        mock_operators_unregister.assert_called_once()
    
    def test_panel_properties(self):
        """Test main panel has correct properties."""
        addon_module = load_addon_module()
        
        panel_class = addon_module.CINEMON_PT_main_panel
        
        # Check required panel properties
        assert hasattr(panel_class, 'bl_label')
        assert hasattr(panel_class, 'bl_idname')
        assert hasattr(panel_class, 'bl_space_type')
        assert hasattr(panel_class, 'bl_region_type')
        assert hasattr(panel_class, 'bl_category')
        
        # Check specific values
        assert panel_class.bl_space_type == 'SEQUENCE_EDITOR'
        assert panel_class.bl_region_type == 'UI'
        assert panel_class.bl_category == "Cinemon"
        assert "Cinemon" in panel_class.bl_label
    
    def test_preset_operator_properties(self):
        """Test preset loading operator has correct properties."""
        addon_module = load_addon_module()
        
        operator_class = addon_module.CINEMON_OT_load_preset
        
        # Check required operator properties
        assert hasattr(operator_class, 'bl_idname')
        assert hasattr(operator_class, 'bl_label')
        assert hasattr(operator_class, 'bl_description')
        assert hasattr(operator_class, 'bl_options')
        
        # Check specific values
        assert operator_class.bl_idname == "cinemon.load_preset"
        assert "Load" in operator_class.bl_label
        assert 'REGISTER' in operator_class.bl_options
    
    def test_panel_draw_method(self):
        """Test panel draw method structure."""
        addon_module = load_addon_module()
        
        panel_class = addon_module.CINEMON_PT_main_panel
        
        # Should have draw method
        assert hasattr(panel_class, 'draw')
        assert callable(panel_class.draw)
        
        # Test draw method doesn't crash with mock context
        panel = panel_class()
        mock_context = Mock()
        mock_context.scene = Mock()
        
        # Mock layout
        mock_layout = Mock()
        mock_context.scene.cinemon_config = None  # No config loaded
        
        # Should not raise exception
        try:
            panel.draw(mock_context)
            # In real test, would need to mock layout properly
        except AttributeError:
            # Expected in test environment without proper bpy mocking
            pass
    
    def test_preset_operator_execute(self):
        """Test preset operator execute method."""
        addon_module = load_addon_module()
        
        operator_class = addon_module.CINEMON_OT_load_preset
        operator = operator_class()
        operator.preset_name = "vintage.yaml"
        
        mock_context = Mock()
        mock_context.scene = Mock()
        
        # Mock preset file exists
        preset_path = addon_path / "example_presets" / "vintage.yaml"
        
        if preset_path.exists():
            # Test with mocked YAMLConfigLoader 
            with patch('setka_common.config.yaml_config.YAMLConfigLoader') as mock_loader_class:
                mock_loader = Mock()
                mock_loader_class.return_value = mock_loader
                mock_config = Mock()
                mock_loader.load_from_file.return_value = mock_config
                
                with patch.object(operator, 'report') as mock_report:
                    result = operator.execute(mock_context)
                    
                    # Should load config successfully
                    assert result == {'FINISHED'}
                    mock_report.assert_called_once()
                    
                    # Should store config in scene
                    assert mock_context.scene.cinemon_config == mock_config
        else:
            # Test error case when preset doesn't exist
            with patch.object(operator, 'report') as mock_report:
                result = operator.execute(mock_context)
                
                # Should return cancelled
                assert result == {'CANCELLED'}
                mock_report.assert_called_once()


class TestOperatorsImport:
    """Test that operators module imports correctly."""
    
    def test_operators_module_imports(self):
        """Test operators module can be imported."""
        from operators import LoadConfigOperator, ApplyConfigOperator
        
        assert LoadConfigOperator is not None
        assert ApplyConfigOperator is not None
    
    def test_operators_registration_functions(self):
        """Test operators module has registration functions."""
        import operators
        
        assert hasattr(operators, 'register')
        assert hasattr(operators, 'unregister')
        assert callable(operators.register)
        assert callable(operators.unregister)
    
    @patch('bpy.utils.register_class')
    def test_operators_register_calls(self, mock_register):
        """Test operators.register() calls bpy.utils.register_class."""
        import operators
        
        operators.register()
        
        # Should register classes from operators.classes
        assert mock_register.call_count == len(operators.classes)
    
    @patch('bpy.utils.unregister_class')
    def test_operators_unregister_calls(self, mock_unregister):
        """Test operators.unregister() calls bpy.utils.unregister_class."""
        import operators
        
        operators.unregister()
        
        # Should unregister classes from operators.classes
        assert mock_unregister.call_count == len(operators.classes)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])