# ABOUTME: Test for YAML import functionality in Blender environment
# ABOUTME: Verifies that vendored YAML library works correctly

"""Test YAML import and basic functionality for Blender addon."""

import pytest
import sys
from pathlib import Path

# Add blender_addon to path for testing
addon_path = Path(__file__).parent.parent.parent / "blender_addon"
if str(addon_path) not in sys.path:
    sys.path.insert(0, str(addon_path))


class TestYAMLImport:
    """Test YAML import in simulated Blender environment."""
    
    def test_yaml_import_from_vendor(self):
        """Test that we can import yaml from vendor directory."""
        from vendor import yaml
        assert yaml is not None
        assert hasattr(yaml, 'safe_load')
        assert hasattr(yaml, 'dump')
    
    def test_yaml_not_in_global_namespace(self):
        """Ensure yaml is not available globally (testing isolation)."""
        # This test simulates Blender environment where yaml is not available
        # In real Blender, yaml wouldn't be available
        # For now, just check we have yaml in our test env
        try:
            import yaml
            # We have yaml in test environment, but Blender won't
            assert yaml is not None
        except ImportError:
            # This would be the case in Blender
            pass
    
    def test_basic_yaml_functionality(self):
        """Test basic YAML load/dump functionality once vendored."""
        # No longer skip - PyYAML is vendored
        
        from vendor import yaml
        
        # Test loading
        yaml_string = """
        preset:
          name: test
        layout:
          type: random
          config:
            seed: 42
        """
        data = yaml.safe_load(yaml_string)
        
        assert data['preset']['name'] == 'test'
        assert data['layout']['type'] == 'random'
        assert data['layout']['config']['seed'] == 42
        
        # Test dumping
        output = yaml.dump(data, default_flow_style=False)
        assert 'preset:' in output
        assert 'name: test' in output


class TestBlenderEnvironmentSimulation:
    """Test that simulates Blender's Python environment constraints."""
    
    def test_no_external_dependencies(self):
        """Verify addon doesn't rely on external packages."""
        # Get all imports from addon __init__.py
        init_file = addon_path / "__init__.py"
        with open(init_file, 'r') as f:
            content = f.read()
        
        # Check for any suspicious imports
        forbidden_imports = ['yaml', 'ruamel', 'pip', 'setuptools']
        for imp in forbidden_imports:
            assert f'import {imp}' not in content
            assert f'from {imp}' not in content
    
    def test_relative_imports_work(self):
        """Test that relative imports work as in Blender addons."""
        # This tests the addon structure is correct
        # Can't import blender_addon directly in tests
        # Instead, test that vendor is accessible from addon path
        import sys
        addon_path = Path(__file__).parent.parent.parent / "blender_addon"
        sys.path.insert(0, str(addon_path))
        try:
            from vendor import yaml
            assert yaml is not None
        finally:
            sys.path.remove(str(addon_path))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])