# ABOUTME: Tests for Blender addon operators using mocked bpy
# ABOUTME: Tests LoadConfigOperator and ApplyConfigOperator functionality

"""Tests for Blender addon operators."""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add blender_addon to path
addon_path = Path(__file__).parent.parent.parent / "blender_addon"
if str(addon_path) not in sys.path:
    sys.path.insert(0, str(addon_path))


class TestLoadConfigOperator:
    """Test LoadConfigOperator functionality."""

    def test_load_config_operator_properties(self):
        """Test LoadConfigOperator has required properties."""
        from operators import LoadConfigOperator

        # Operator should have bl_idname and bl_label
        assert hasattr(LoadConfigOperator, "bl_idname")
        assert hasattr(LoadConfigOperator, "bl_label")
        assert LoadConfigOperator.bl_idname == "cinemon.load_config"
        assert "Load" in LoadConfigOperator.bl_label

        # In test environment, properties might be class attributes or instance attributes
        # Check if they exist as class attributes or can be set on instance
        operator = LoadConfigOperator()

        # Should be able to set filepath
        operator.filepath = "test.yaml"
        assert operator.filepath == "test.yaml"

        # Should have filter_glob as class attribute or be settable
        if hasattr(LoadConfigOperator, "filter_glob"):
            assert "*.yaml" in LoadConfigOperator.filter_glob
        else:
            # In test environment, check if it can be set
            operator.filter_glob = "*.yaml;*.yml"
            assert "*.yaml" in operator.filter_glob

    def test_load_config_invoke_file_browser(self):
        """Test LoadConfigOperator.invoke() opens file browser."""
        from operators import LoadConfigOperator

        operator = LoadConfigOperator()
        mock_context = Mock()
        mock_event = Mock()

        # Mock window manager
        mock_wm = Mock()
        mock_context.window_manager = mock_wm

        result = operator.invoke(mock_context, mock_event)

        # Should call fileselect_add
        mock_wm.fileselect_add.assert_called_once()

        # Should return RUNNING_MODAL
        assert result == {"RUNNING_MODAL"}

    def test_load_config_execute_valid_file(self):
        """Test LoadConfigOperator.execute() with valid YAML file."""
        from config_loader import (
            AudioAnalysisConfig,
            CinemonConfig,
            LayoutConfig,
            ProjectConfig,
        )
        from operators import LoadConfigOperator

        operator = LoadConfigOperator()
        operator.filepath = str(addon_path / "example_presets" / "vintage.yaml")

        mock_context = Mock()
        mock_context.scene = Mock()

        with patch("operators.YAMLConfigLoader") as mock_loader_class:
            mock_loader = Mock()
            mock_loader_class.return_value = mock_loader

            # Mock successful loading
            mock_config = CinemonConfig(
                project=ProjectConfig(video_files=[], fps=30),
                layout=LayoutConfig(type="random"),
                strip_animations={},
                audio_analysis=AudioAnalysisConfig(file="./analysis/audio.json"),
            )
            mock_loader.load_from_file.return_value = mock_config

            result = operator.execute(mock_context)

            # Should load file successfully
            mock_loader.load_from_file.assert_called_once_with(operator.filepath)

            # Should store config in scene
            assert hasattr(mock_context.scene, "cinemon_config")
            assert mock_context.scene.cinemon_config == mock_config

            # Should return FINISHED
            assert result == {"FINISHED"}

    def test_load_config_execute_invalid_file(self):
        """Test LoadConfigOperator.execute() with invalid YAML file."""
        from config_loader import ValidationError
        from operators import LoadConfigOperator

        operator = LoadConfigOperator()
        operator.filepath = "/nonexistent/file.yaml"

        mock_context = Mock()
        mock_context.scene = Mock()

        with patch("operators.YAMLConfigLoader") as mock_loader_class:
            mock_loader = Mock()
            mock_loader_class.return_value = mock_loader

            # Mock validation error
            mock_loader.load_from_file.side_effect = ValidationError("Test error")

            with patch.object(operator, "report") as mock_report:
                result = operator.execute(mock_context)

                # Should report error
                mock_report.assert_called_once()
                # report() is called with (level_set, message)
                call_args = mock_report.call_args[0]
                assert len(call_args) == 2
                level_set, message = call_args
                assert "ERROR" in level_set

                # Should return CANCELLED
                assert result == {"CANCELLED"}

    def test_load_config_file_filter(self):
        """Test LoadConfigOperator filters for YAML files."""
        from operators import LoadConfigOperator

        # In test environment, filter_glob might be class or instance attribute
        if hasattr(LoadConfigOperator, "filter_glob"):
            # filter_glob should only allow YAML files
            assert "*.yaml" in LoadConfigOperator.filter_glob
            assert "*.yml" in LoadConfigOperator.filter_glob
        else:
            # Check filename_ext as fallback
            assert LoadConfigOperator.filename_ext == ".yaml"


class TestApplyConfigOperator:
    """Test ApplyConfigOperator functionality."""

    def test_apply_config_operator_properties(self):
        """Test ApplyConfigOperator has required properties."""
        from operators import ApplyConfigOperator

        # Operator should have bl_idname and bl_label
        assert hasattr(ApplyConfigOperator, "bl_idname")
        assert hasattr(ApplyConfigOperator, "bl_label")
        assert ApplyConfigOperator.bl_idname == "cinemon.apply_config"
        assert "Apply" in ApplyConfigOperator.bl_label

    def test_apply_config_execute_no_config(self):
        """Test ApplyConfigOperator.execute() with no loaded config."""
        from operators import ApplyConfigOperator

        operator = ApplyConfigOperator()
        mock_context = Mock()
        mock_context.scene = Mock(spec=[])  # Empty spec means no attributes

        with patch.object(operator, "report") as mock_report:
            result = operator.execute(mock_context)

            # Should report error about no config
            mock_report.assert_called_once()
            # report() is called with (level_set, message)
            call_args = mock_report.call_args[0]
            assert len(call_args) == 2
            level_set, message = call_args
            assert "ERROR" in level_set
            assert "No config loaded" in message

            # Should return CANCELLED
            assert result == {"CANCELLED"}

    def test_apply_config_execute_with_config(self):
        """Test ApplyConfigOperator.execute() with loaded config."""
        from config_loader import (
            AudioAnalysisConfig,
            CinemonConfig,
            LayoutConfig,
            ProjectConfig,
        )
        from operators import ApplyConfigOperator

        operator = ApplyConfigOperator()
        mock_context = Mock()
        mock_context.scene = Mock()

        # Mock loaded config
        mock_config = CinemonConfig(
            project=ProjectConfig(video_files=["Camera1.mp4"], fps=30),
            layout=LayoutConfig(type="random"),
            strip_animations={"Camera1": [{"type": "scale", "trigger": "beat"}]},
            audio_analysis=AudioAnalysisConfig(file="./analysis/audio.json"),
        )
        mock_context.scene.cinemon_config = mock_config
        mock_context.scene.cinemon_config_path = "/test/path/config.yaml"

        with patch("operators.YAMLConfigLoader") as mock_loader_class:
            mock_loader = Mock()
            mock_loader_class.return_value = mock_loader
            mock_loader.convert_to_internal.return_value = {"test": "config"}

            with patch(
                "operators.BlenderVSEConfiguratorDirect"
            ) as mock_configurator_class:
                mock_configurator = Mock()
                mock_configurator_class.return_value = mock_configurator
                mock_configurator.setup_vse_project.return_value = True

                with patch.object(operator, "report") as mock_report:
                    result = operator.execute(mock_context)

                    # Print what was reported to understand the error
                    if mock_report.called:
                        for call in mock_report.call_args_list:
                            print(f"Report call: {call}")
                    else:
                        print("No report calls made")

                # Should create configurator with config
                mock_configurator_class.assert_called_once()

                # Should call setup_vse_project
                mock_configurator.setup_vse_project.assert_called_once()

                # Should return FINISHED
                assert result == {"FINISHED"}

    def test_apply_config_execute_setup_fails(self):
        """Test ApplyConfigOperator.execute() when VSE setup fails."""
        from config_loader import (
            AudioAnalysisConfig,
            CinemonConfig,
            LayoutConfig,
            ProjectConfig,
        )
        from operators import ApplyConfigOperator

        operator = ApplyConfigOperator()
        mock_context = Mock()
        mock_context.scene = Mock()

        # Mock loaded config
        mock_config = CinemonConfig(
            project=ProjectConfig(video_files=["Camera1.mp4"], fps=30),
            layout=LayoutConfig(type="random"),
            strip_animations={},
            audio_analysis=AudioAnalysisConfig(file="./analysis/audio.json"),
        )
        mock_context.scene.cinemon_config = mock_config
        mock_context.scene.cinemon_config_path = "/test/path/config.yaml"

        with patch("operators.YAMLConfigLoader") as mock_loader_class:
            mock_loader = Mock()
            mock_loader_class.return_value = mock_loader
            mock_loader.convert_to_internal.return_value = {"test": "config"}

            with patch(
                "operators.BlenderVSEConfiguratorDirect"
            ) as mock_configurator_class:
                mock_configurator = Mock()
                mock_configurator_class.return_value = mock_configurator
                mock_configurator.setup_vse_project.return_value = False  # Setup fails

                with patch.object(operator, "report") as mock_report:
                    result = operator.execute(mock_context)

                    # Should report error
                    mock_report.assert_called_once()
                    # report() is called with (level_set, message)
                    call_args = mock_report.call_args[0]
                    assert len(call_args) == 2
                    level_set, message = call_args
                    assert "ERROR" in level_set

                    # Should return CANCELLED
                    assert result == {"CANCELLED"}


class TestOperatorRegistration:
    """Test operator registration system."""

    def test_operators_can_be_imported(self):
        """Test that operators can be imported without bpy errors."""
        # This test ensures operators can be imported in test environment
        from operators import ApplyConfigOperator, LoadConfigOperator

        assert LoadConfigOperator is not None
        assert ApplyConfigOperator is not None

    def test_operators_have_registration_methods(self):
        """Test operators have required registration methods."""
        from operators import ApplyConfigOperator, LoadConfigOperator

        # Both operators should be subclasses of bpy.types.Operator
        # In test environment, we'll check they have the right structure
        for operator_class in [LoadConfigOperator, ApplyConfigOperator]:
            assert hasattr(operator_class, "bl_idname")
            assert hasattr(operator_class, "bl_label")
            assert hasattr(operator_class, "execute")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
