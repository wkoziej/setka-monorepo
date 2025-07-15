# ABOUTME: Tests to verify the cinemon package structure is correct
# ABOUTME: Ensures all modules can be imported and basic functionality works

"""Test package structure and imports for cinemon."""

import pytest
from pathlib import Path


class TestPackageStructure:
    """Test that the package structure is correct after migration."""

    def test_package_imports(self):
        """Test that main package can be imported."""
        import blender
        
        assert hasattr(blender, "__version__")
        assert hasattr(blender, "BlenderProjectManager")

    def test_vse_module_imports(self):
        """Test VSE submodule imports."""
        from blender import vse
        from blender.vse import animation_engine
        from blender.vse import config
        from blender.vse import constants
        from blender.vse import keyframe_helper
        from blender.vse import layout_manager
        from blender.vse import project_setup

    def test_animators_module_imports(self):
        """Test animator submodule imports."""
        from blender.vse import animators
        from blender.vse.animators import beat_switch_animator
        from blender.vse.animators import energy_pulse_animator
        from blender.vse.animators import multi_pip_animator

    def test_effects_module_imports(self):
        """Test effects submodule imports."""
        from blender.vse import effects
        from blender.vse.effects import vintage_film_effects

    def test_cli_module_imports(self):
        """Test CLI module imports."""
        from blender.cli import blend_setup
        
        assert hasattr(blend_setup, "main")

    def test_file_structure(self):
        """Test that all expected files exist."""
        package_root = Path(__file__).parent.parent
        
        # Check main modules
        assert (package_root / "src/blender/project_manager.py").exists()
        assert (package_root / "src/blender/vse_script.py").exists()
        
        # Check VSE modules
        assert (package_root / "src/blender/vse/__init__.py").exists()
        assert (package_root / "src/blender/vse/animation_engine.py").exists()
        
        # Check test files
        assert (package_root / "tests/test_project_manager.py").exists()
        assert (package_root / "tests/test_animation_engine.py").exists()