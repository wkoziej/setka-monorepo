# ABOUTME: Tests to verify the cinemon package structure is correct
# ABOUTME: Ensures all modules can be imported and basic functionality works

"""Test package structure and imports for cinemon."""

from pathlib import Path


class TestPackageStructure:
    """Test that the package structure is correct after YAML migration."""

    def test_package_imports(self):
        """Test that main package can be imported."""
        import cinemon

        assert hasattr(cinemon, "ProjectManager")
        assert hasattr(cinemon, "CinemonConfigGenerator")

    def test_vse_module_imports(self):
        """Test VSE submodule imports."""

    def test_new_compositional_system_imports(self):
        """Test new compositional animation system imports."""

    def test_effects_module_imports(self):
        """Test effects submodule imports."""

    def test_cli_module_imports(self):
        """Test CLI module imports."""
        from cinemon.cli import blend_setup

        assert hasattr(blend_setup, "main")

    def test_config_module_imports(self):
        """Test config module imports."""

    def test_file_structure(self):
        """Test that all expected files exist."""
        package_root = Path(__file__).parent.parent

        # Check main modules
        assert (package_root / "src/cinemon/project_manager.py").exists()
        assert (package_root / "blender_addon/vse_script.py").exists()

        # Check VSE modules (in blender_addon)
        assert (package_root / "blender_addon/vse/__init__.py").exists()
        assert (package_root / "blender_addon/vse/yaml_config.py").exists()
        assert (package_root / "blender_addon/vse/animation_compositor.py").exists()

        # Check config modules
        assert (package_root / "src/cinemon/config/__init__.py").exists()

        # Check CLI modules
        assert (package_root / "src/cinemon/cli/blend_setup.py").exists()

        # Check test files
        assert (package_root / "tests/test_project_manager.py").exists()
        assert (package_root / "tests/test_cinemon_config_generator.py").exists()
