"""
Import verification tests to catch import-related bugs.
These tests verify that modules use correct import statements and handle imports properly.
"""

import ast
import sys
from pathlib import Path
from unittest.mock import Mock, patch
import pytest


class TestImportVerification:
    """Test import statements and module loading."""

    def test_metadata_module_uses_correct_obs_import(self):
        """Verify that metadata.py uses 'import obspython as obs' not 'import obs'."""
        metadata_file = Path("src/core/metadata.py")
        source_code = metadata_file.read_text()

        # Parse the AST to find import statements
        tree = ast.parse(source_code)

        obs_imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if "obs" in alias.name:
                        obs_imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module and "obs" in node.module:
                    obs_imports.append(node.module)

        # Should not have direct 'obs' import
        assert "obs" not in obs_imports, (
            f"Found direct 'obs' import. All imports: {obs_imports}"
        )

        # Check for correct import in source
        assert "import obspython as obs" in source_code, (
            "Should use 'import obspython as obs'"
        )

    def test_obs_script_uses_correct_obs_import(self):
        """Verify that obs_script.py uses 'import obspython as obs' not 'import obs'."""
        obs_script_file = Path("src/obs_integration/obs_script.py")
        source_code = obs_script_file.read_text()

        # Check for correct import in source
        assert "import obspython as obs" in source_code, (
            "OBS script should use 'import obspython as obs'"
        )

    def test_metadata_module_import_without_mocks(self):
        """Test that metadata module can be imported without session-wide mocks."""
        # Remove any cached imports
        modules_to_remove = [name for name in sys.modules.keys() if "metadata" in name]
        for module_name in modules_to_remove:
            del sys.modules[module_name]

        # Import should work (obspython will be None due to ImportError, which is expected)
        from core.metadata import determine_source_capabilities

        # Function should exist and be callable
        assert callable(determine_source_capabilities)

    def test_determine_source_capabilities_import_fallback(self):
        """Test that determine_source_capabilities handles obspython import failure correctly."""
        # Simulate obspython not being available
        with patch.dict("sys.modules", {"obspython": None}):
            # Force reload
            if "metadata" in sys.modules:
                del sys.modules["metadata"]

            from core.metadata import determine_source_capabilities

            # Should return False for both when obs is None
            result = determine_source_capabilities(Mock())
            assert result == {"has_audio": False, "has_video": False}

    def test_obs_module_availability_in_metadata(self):
        """Test that the obs module is properly available in metadata module."""
        # Import the module
        from src.core import metadata

        # The obs variable should be either None or a proper mock/module
        assert hasattr(metadata, "obs"), "metadata module should have 'obs' attribute"

        # If obs is not None, it should have the required function
        if metadata.obs is not None:
            assert hasattr(metadata.obs, "obs_source_get_output_flags"), (
                "obs module should have obs_source_get_output_flags function"
            )


class TestOBSIntegrationImports:
    """Test OBS integration module imports."""

    def test_obs_script_fallback_implementation(self):
        """Test that OBS script has fallback implementation for determine_source_capabilities."""
        obs_script_file = Path("src/obs_integration/obs_script.py")
        source_code = obs_script_file.read_text()

        # Should have fallback implementation
        assert "def determine_source_capabilities(obs_source)" in source_code, (
            "OBS script should have fallback implementation"
        )

        # Should handle obs being None
        assert "if obs_source is None or obs is None:" in source_code, (
            "Fallback should handle obs being None"
        )

    def test_obs_script_import_handling(self):
        """Test that OBS script properly handles import scenarios."""
        # The script should be importable even when obspython is not available
        # (It will use the fallback implementation)

        # Remove any cached imports
        modules_to_remove = [
            name for name in sys.modules.keys() if "obs_integration" in name
        ]
        for module_name in modules_to_remove:
            del sys.modules[module_name]

        # Should be able to import the module
        from src.obs_integration import obs_script

        # Should have the required functions
        assert hasattr(obs_script, "determine_source_capabilities")
        assert callable(obs_script.determine_source_capabilities)


class TestImportConsistency:
    """Test consistency of imports across modules."""

    def test_all_obs_imports_use_same_pattern(self):
        """Verify all files use the same OBS import pattern."""
        # Files that should use OBS imports
        obs_files = [
            Path("src/core/metadata.py"),
            Path("src/obs_integration/obs_script.py"),
        ]

        for file_path in obs_files:
            if file_path.exists():
                source_code = file_path.read_text()

                # Each file should use the same import pattern
                if "obspython" in source_code:
                    assert "import obspython as obs" in source_code, (
                        f"File {file_path} should use 'import obspython as obs'"
                    )

    def test_no_direct_obs_imports(self):
        """Verify no files use direct 'import obs' statements."""
        # Check all Python files in src/
        src_path = Path("src")
        for python_file in src_path.rglob("*.py"):
            source_code = python_file.read_text()

            # Parse AST to check for direct obs imports
            try:
                tree = ast.parse(source_code)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if alias.name == "obs" and alias.asname is None:
                                pytest.fail(
                                    f"File {python_file} uses direct 'import obs' - should use 'import obspython as obs'"
                                )
            except SyntaxError:
                # Skip files that can't be parsed
                continue


@pytest.mark.integration
class TestRealImportBehavior:
    """Integration tests for real import behavior."""

    def test_metadata_module_with_real_imports(self):
        """Test metadata module behavior with real imports (no mocking)."""
        # Clear all mocks and cached imports
        modules_to_remove = [
            name
            for name in sys.modules.keys()
            if any(part in name for part in ["metadata", "obspython"])
        ]
        for module_name in modules_to_remove:
            if module_name != "obspython":  # Don't remove session mock
                del sys.modules[module_name]

        # Import fresh
        from core.metadata import determine_source_capabilities

        # Test with None source (should always work)
        result = determine_source_capabilities(None)
        assert result == {"has_audio": False, "has_video": False}

    def test_capabilities_with_mock_obs_source(self):
        """Test capabilities detection with a properly mocked OBS source."""
        # Create a mock OBS module with proper structure
        mock_obs = Mock()
        mock_obs.obs_source_get_output_flags.return_value = 0x003  # Audio + Video flags

        with patch.dict("sys.modules", {"obspython": mock_obs}):
            # Force reload
            if "metadata" in sys.modules:
                del sys.modules["metadata"]

            from core.metadata import determine_source_capabilities

            # Test with mock source
            mock_source = Mock()
            result = determine_source_capabilities(mock_source)

            # Should detect both audio and video
            assert result["has_audio"] is True
            assert result["has_video"] is True

            # Verify the OBS function was called
            mock_obs.obs_source_get_output_flags.assert_called_once_with(mock_source)

    def test_bug_scenario_wrong_import_would_fail(self):
        """
        Test that simulates the original bug scenario to ensure it would be caught.
        This test demonstrates what would happen if 'import obs' was used instead of 'import obspython as obs'.
        """
        # Simulate the scenario where someone mistakenly uses 'import obs'
        # In the real bug, this would cause obs to be None, leading to capabilities always being False

        # Create a mock source that should have capabilities
        mock_source = Mock()

        # First, test with a proper obspython mock (what should happen)
        mock_obs_proper = Mock()
        mock_obs_proper.obs_source_get_output_flags.return_value = (
            0x003  # Audio + Video
        )

        with patch.dict("sys.modules", {"obspython": mock_obs_proper}):
            if "metadata" in sys.modules:
                del sys.modules["metadata"]

            from core.metadata import determine_source_capabilities

            result_proper = determine_source_capabilities(mock_source)
            assert result_proper["has_audio"] is True
            assert result_proper["has_video"] is True

        # Now simulate the bug scenario where obs is None (wrong import)
        # In the original bug, 'import obs' would fail or return None
        with patch.dict("sys.modules", {"obspython": None}):
            if "metadata" in sys.modules:
                del sys.modules["metadata"]

            from core.metadata import determine_source_capabilities

            # In the bug scenario, this would always return False
            result_bug = determine_source_capabilities(mock_source)
            assert result_bug["has_audio"] is False
            assert result_bug["has_video"] is False

        # The test above demonstrates that the function behavior changes dramatically
        # based on the import success, which is what the bug was about
        # This test would catch the bug because it verifies both scenarios work differently
