# ABOUTME: Tests to verify the cinemon package structure is correct
# ABOUTME: Ensures all modules can be imported and basic functionality works

"""Test package structure and imports for cinemon."""

from pathlib import Path


class TestPackageStructure:
    """Test that the package structure is correct after YAML migration."""

    def test_package_imports(self):
        """Test that main package can be imported."""
        import blender

        assert hasattr(blender, "__version__")
        assert hasattr(blender, "BlenderProjectManager")

    def test_vse_module_imports(self):
        """Test VSE submodule imports."""

    def test_new_compositional_system_imports(self):
        """Test new compositional animation system imports."""

    def test_effects_module_imports(self):
        """Test effects submodule imports."""

    def test_cli_module_imports(self):
        """Test CLI module imports."""
        from blender.cli import blend_setup

        assert hasattr(blend_setup, "main")

    def test_config_module_imports(self):
        """Test config module imports."""

    def test_file_structure(self):
        """Test that all expected files exist."""
        package_root = Path(__file__).parent.parent

        # Check main modules
        assert (package_root / "src/blender/project_manager.py").exists()
        assert (package_root / "src/blender/vse_script.py").exists()

        # Check VSE modules
        assert (package_root / "src/blender/vse/__init__.py").exists()
        assert (package_root / "src/blender/vse/yaml_config.py").exists()
        assert (package_root / "src/blender/vse/animation_compositor.py").exists()

        # Check config modules
        assert (package_root / "src/blender/config/__init__.py").exists()

        # Check CLI modules
        assert (package_root / "src/blender/cli/blend_setup.py").exists()

        # Check test files
        assert (package_root / "tests/test_project_manager.py").exists()
        assert (package_root / "tests/test_cinemon_config_generator.py").exists()
