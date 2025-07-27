# ABOUTME: Tests for CLI --preset parameter integration after YAML migration
# ABOUTME: Tests CLI argument parsing with required --preset or --config parameters

"""Tests for CLI --preset parameter functionality with YAML-only interface."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cinemon.cli.blend_setup import main, parse_args


class TestCLIPresetParameter:
    """Test cases for CLI --preset parameter integration."""

    def test_parse_args_with_preset_parameter(self):
        """Test that --preset parameter is properly parsed."""
        test_args = ["recording_dir", "--preset", "vintage"]

        with patch.object(sys, "argv", ["blend_setup.py"] + test_args):
            args = parse_args()

        assert hasattr(args, "preset")
        assert args.preset == "vintage"
        assert args.recording_dir == Path("recording_dir")
        assert args.config is None

    def test_parse_args_with_config_parameter(self):
        """Test that --config parameter is properly parsed."""
        test_args = ["recording_dir", "--config", "config.yaml"]

        with patch.object(sys, "argv", ["blend_setup.py"] + test_args):
            args = parse_args()

        assert hasattr(args, "config")
        assert args.config == Path("config.yaml")
        assert args.recording_dir == Path("recording_dir")
        assert args.preset is None

    def test_parse_args_requires_preset_or_config(self):
        """Test that either --preset or --config is required."""
        test_args = ["recording_dir"]

        with patch.object(sys, "argv", ["blend_setup.py"] + test_args):
            with pytest.raises(
                SystemExit
            ):  # argparse exits when required group not provided
                parse_args()

    def test_parse_args_preset_and_config_mutually_exclusive(self):
        """Test that --preset and --config are mutually exclusive."""
        test_args = ["recording_dir", "--preset", "vintage", "--config", "config.yaml"]

        with patch.object(sys, "argv", ["blend_setup.py"] + test_args):
            with pytest.raises(SystemExit):  # argparse exits on mutually exclusive args
                parse_args()

    def test_parse_args_preset_with_other_parameters(self):
        """Test that --preset works with other CLI parameters."""
        test_args = [
            "recording_dir",
            "--preset",
            "music-video",
            "--verbose",
            "--force",
            "--main-audio",
            "custom_audio.m4a",
        ]

        with patch.object(sys, "argv", ["blend_setup.py"] + test_args):
            args = parse_args()

        assert args.preset == "music-video"
        assert args.verbose is True
        assert args.force is True
        assert args.main_audio == "custom_audio.m4a"

    @patch("cinemon.cli.blend_setup.BlenderProjectManager")
    @patch("cinemon.cli.blend_setup.CinemonConfigGenerator")
    @patch("cinemon.cli.blend_setup.load_yaml_config")
    def test_main_with_preset_generates_config(
        self, mock_load_yaml, mock_generator_class, mock_manager_class
    ):
        """Test that main() with --preset generates config via CinemonConfigGenerator."""
        test_args = ["recording_dir", "--preset", "vintage"]

        # Setup mocks
        mock_generator = MagicMock()
        mock_config_path = Path("/tmp/generated_config.yaml")
        mock_generator.generate_preset.return_value = mock_config_path
        mock_generator_class.return_value = mock_generator

        mock_yaml_config = MagicMock()
        mock_load_yaml.return_value = mock_yaml_config

        mock_manager = MagicMock()
        mock_project_path = Path("/test/recording/blender/project.blend")
        mock_manager.create_vse_project_with_config.return_value = mock_project_path
        mock_manager_class.return_value = mock_manager

        with patch.object(sys, "argv", ["blend_setup.py"] + test_args):
            result = main()

        # Verify config generation workflow
        assert result == 0
        mock_generator.generate_preset.assert_called_once_with(
            Path("recording_dir"), "vintage"
        )
        mock_load_yaml.assert_called_once_with(mock_config_path)
        mock_manager.create_vse_project_with_config.assert_called_once_with(
            Path("recording_dir"), mock_yaml_config
        )

    @patch("cinemon.cli.blend_setup.BlenderProjectManager")
    @patch("cinemon.cli.blend_setup.CinemonConfigGenerator")
    @patch("cinemon.cli.blend_setup.load_yaml_config")
    def test_main_with_preset_and_overrides(
        self, mock_load_yaml, mock_generator_class, mock_manager_class
    ):
        """Test that main() with --preset passes override parameters."""
        test_args = [
            "recording_dir",
            "--preset",
            "music-video",
            "--main-audio",
            "custom_main.m4a",
        ]

        # Setup mocks
        mock_generator = MagicMock()
        mock_config_path = Path("/tmp/generated_config.yaml")
        mock_generator.generate_preset.return_value = mock_config_path
        mock_generator_class.return_value = mock_generator

        mock_yaml_config = MagicMock()
        mock_load_yaml.return_value = mock_yaml_config

        mock_manager = MagicMock()
        mock_project_path = Path("/test/recording/blender/project.blend")
        mock_manager.create_vse_project_with_config.return_value = mock_project_path
        mock_manager_class.return_value = mock_manager

        with patch.object(sys, "argv", ["blend_setup.py"] + test_args):
            result = main()

        # Verify overrides are passed to preset generation
        assert result == 0
        mock_generator.generate_preset.assert_called_once_with(
            Path("recording_dir"), "music-video", main_audio="custom_main.m4a"
        )

    @patch("cinemon.cli.blend_setup.BlenderProjectManager")
    @patch("cinemon.cli.blend_setup.load_yaml_config")
    def test_main_with_config_file_skips_preset_generation(
        self, mock_load_yaml, mock_manager_class
    ):
        """Test that main() with --config skips preset generation."""
        test_args = ["recording_dir", "--config", "custom_config.yaml"]

        # Setup mocks
        mock_yaml_config = MagicMock()
        mock_load_yaml.return_value = mock_yaml_config

        mock_manager = MagicMock()
        mock_project_path = Path("/test/recording/blender/project.blend")
        mock_manager.create_vse_project_with_config.return_value = mock_project_path
        mock_manager_class.return_value = mock_manager

        with patch.object(sys, "argv", ["blend_setup.py"] + test_args):
            # Should not import or use CinemonConfigGenerator
            with patch(
                "cinemon.cli.blend_setup.CinemonConfigGenerator"
            ) as mock_generator_class:
                result = main()

                # Verify no config generation
                assert result == 0
                mock_generator_class.assert_not_called()
                mock_load_yaml.assert_called_once_with(Path("custom_config.yaml"))
                mock_manager.create_vse_project_with_config.assert_called_once_with(
                    Path("recording_dir"), mock_yaml_config
                )

    @patch("cinemon.cli.blend_setup.BlenderProjectManager")
    @patch("cinemon.cli.blend_setup.CinemonConfigGenerator")
    @patch("cinemon.cli.blend_setup.load_yaml_config")
    @patch("builtins.print")
    def test_main_preset_with_force_flag(
        self, mock_print, mock_load_yaml, mock_generator_class, mock_manager_class
    ):
        """Test that main() processes --force flag with presets."""
        test_args = ["recording_dir", "--preset", "beat-switch", "--force"]

        # Setup mocks
        mock_generator = MagicMock()
        mock_config_path = Path("/tmp/generated_config.yaml")
        mock_generator.generate_preset.return_value = mock_config_path
        mock_generator_class.return_value = mock_generator

        mock_yaml_config = MagicMock()
        mock_load_yaml.return_value = mock_yaml_config

        mock_manager = MagicMock()
        mock_project_path = Path("/test/recording/blender/project.blend")
        mock_manager.create_vse_project_with_config.return_value = mock_project_path
        mock_manager_class.return_value = mock_manager

        with patch.object(sys, "argv", ["blend_setup.py"] + test_args):
            result = main()

        # Verify success message with preset name
        assert result == 0
        success_calls = [
            call for call in mock_print.call_args_list if "beat-switch" in str(call)
        ]
        assert len(success_calls) > 0

    @patch("cinemon.cli.blend_setup.BlenderProjectManager")
    @patch("cinemon.cli.blend_setup.CinemonConfigGenerator")
    @patch("cinemon.cli.blend_setup.load_yaml_config")
    @patch("logging.getLogger")
    def test_main_preset_mode_logging(
        self, mock_get_logger, mock_load_yaml, mock_generator_class, mock_manager_class
    ):
        """Test that main() logs preset generation steps."""
        test_args = ["recording_dir", "--preset", "minimal"]

        # Setup mocks
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_generator = MagicMock()
        mock_config_path = Path("/tmp/generated_config.yaml")
        mock_generator.generate_preset.return_value = mock_config_path
        mock_generator_class.return_value = mock_generator

        mock_yaml_config = MagicMock()
        mock_load_yaml.return_value = mock_yaml_config

        mock_manager = MagicMock()
        mock_project_path = Path("/test/recording/blender/project.blend")
        mock_manager.create_vse_project_with_config.return_value = mock_project_path
        mock_manager_class.return_value = mock_manager

        with patch.object(sys, "argv", ["blend_setup.py"] + test_args):
            result = main()

        # Verify logging calls
        assert result == 0
        preset_log_calls = [
            call
            for call in mock_logger.info.call_args_list
            if "preset" in str(call).lower()
        ]
        assert len(preset_log_calls) >= 2  # At least generation and creation logs
