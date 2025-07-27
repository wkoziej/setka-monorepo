"""
Tests for blend_setup CLI with YAML-only interface.

This module contains unit tests for the blend_setup CLI module
after migration to YAML-only configuration.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from beatrix import AudioValidationError

from cinemon.cli.blend_setup import (
    load_yaml_config,
    main,
    parse_args,
    setup_logging,
    validate_recording_directory,
)


class TestParseArgs:
    """Test cases for parse_args function with YAML-only interface."""

    def test_parse_args_with_preset(self):
        """Test parsing with preset parameter."""
        with patch(
            "sys.argv", ["blend_setup.py", "/path/to/recording", "--preset", "vintage"]
        ):
            args = parse_args()
            assert args.recording_dir == Path("/path/to/recording")
            assert args.preset == "vintage"
            assert args.config is None
            assert args.verbose is False
            assert args.force is False
            assert args.main_audio is None

    def test_parse_args_with_config(self):
        """Test parsing with config parameter."""
        with patch(
            "sys.argv",
            ["blend_setup.py", "/path/to/recording", "--config", "config.yaml"],
        ):
            args = parse_args()
            assert args.recording_dir == Path("/path/to/recording")
            assert args.config == Path("config.yaml")
            assert args.preset is None

    def test_parse_args_with_all_flags(self):
        """Test parsing with all optional flags."""
        with patch(
            "sys.argv",
            [
                "blend_setup.py",
                "/path/to/recording",
                "--preset",
                "music-video",
                "--verbose",
                "--force",
                "--main-audio",
                "audio.mp3",
            ],
        ):
            args = parse_args()
            assert args.recording_dir == Path("/path/to/recording")
            assert args.preset == "music-video"
            assert args.verbose is True
            assert args.force is True
            assert args.main_audio == "audio.mp3"

    def test_parse_args_requires_preset_or_config(self):
        """Test that either --preset or --config is required."""
        with patch("sys.argv", ["blend_setup.py", "/path/to/recording"]):
            with pytest.raises(SystemExit):
                parse_args()

    def test_parse_args_preset_and_config_mutually_exclusive(self):
        """Test that --preset and --config are mutually exclusive."""
        with patch(
            "sys.argv",
            [
                "blend_setup.py",
                "/path/to/recording",
                "--preset",
                "vintage",
                "--config",
                "config.yaml",
            ],
        ):
            with pytest.raises(SystemExit):
                parse_args()

    def test_parse_args_short_flags(self):
        """Test parsing short flag versions."""
        with patch(
            "sys.argv",
            ["blend_setup.py", "/path/to/recording", "--preset", "minimal", "-v", "-f"],
        ):
            args = parse_args()
            assert args.verbose is True
            assert args.force is True


class TestValidateRecordingDirectory:
    """Test cases for validate_recording_directory function."""

    def test_validate_nonexistent_directory(self):
        """Test validation of nonexistent directory."""
        nonexistent_dir = Path("/nonexistent/path")
        with pytest.raises(ValueError, match="Katalog nagrania nie istnieje"):
            validate_recording_directory(nonexistent_dir)

    def test_validate_not_directory(self, tmp_path):
        """Test validation when path is not a directory."""
        file_path = tmp_path / "not_a_directory.txt"
        file_path.write_text("test")

        with pytest.raises(ValueError, match="Ścieżka nie jest katalogiem"):
            validate_recording_directory(file_path)

    def test_validate_missing_metadata(self, tmp_path):
        """Test validation when metadata.json is missing."""
        with pytest.raises(ValueError, match="Stare nagranie bez metadata.json"):
            validate_recording_directory(tmp_path)

    def test_validate_missing_extracted_directory(self, tmp_path):
        """Test validation when extracted directory is missing."""
        (tmp_path / "metadata.json").write_text("{}")

        with pytest.raises(ValueError, match="Brak katalogu extracted/"):
            validate_recording_directory(tmp_path)

    def test_validate_extracted_not_directory(self, tmp_path):
        """Test validation when extracted is not a directory."""
        (tmp_path / "metadata.json").write_text("{}")
        (tmp_path / "extracted").write_text("not a directory")

        with pytest.raises(ValueError, match="extracted/ nie jest katalogiem"):
            validate_recording_directory(tmp_path)

    def test_validate_empty_extracted_directory(self, tmp_path):
        """Test validation when extracted directory is empty."""
        (tmp_path / "metadata.json").write_text("{}")
        (tmp_path / "extracted").mkdir()

        with pytest.raises(ValueError, match="Katalog extracted/ jest pusty"):
            validate_recording_directory(tmp_path)

    def test_validate_valid_directory(self, tmp_path):
        """Test validation of valid directory structure."""
        (tmp_path / "metadata.json").write_text("{}")
        extracted_dir = tmp_path / "extracted"
        extracted_dir.mkdir()
        (extracted_dir / "video.mp4").write_text("test video")

        # Should not raise exception
        validate_recording_directory(tmp_path)


class TestLoadYAMLConfig:
    """Test cases for load_yaml_config function."""

    def test_load_yaml_config_success(self, tmp_path):
        """Test successful YAML config loading."""
        config_file = tmp_path / "config.yaml"
        config_content = """
project:
  video_files: ["video1.mp4"]
  fps: 30
  resolution:
    width: 1920
    height: 1080
audio_analysis:
  file: null
layout:
  type: "random"
  config: {}
animations: []
"""
        config_file.write_text(config_content)

        with patch("cinemon.cli.blend_setup.YAMLConfigLoader") as mock_loader_class:
            mock_loader = Mock()
            mock_config = Mock()
            mock_loader.load_config.return_value = mock_config
            mock_loader_class.return_value = mock_loader

            result = load_yaml_config(config_file)

            assert result == mock_config
            mock_loader.load_config.assert_called_once_with(config_file)

    def test_load_yaml_config_file_not_found(self, tmp_path):
        """Test YAML config loading with missing file."""
        config_file = tmp_path / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            load_yaml_config(config_file)

    def test_load_yaml_config_validation_error(self, tmp_path):
        """Test YAML config loading with validation error."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("invalid: yaml: content:")

        with patch("cinemon.cli.blend_setup.YAMLConfigLoader") as mock_loader_class:
            mock_loader = Mock()
            mock_loader.load_config.side_effect = Exception("Invalid YAML")
            mock_loader_class.return_value = mock_loader

            with pytest.raises(ValueError, match="Failed to load YAML configuration"):
                load_yaml_config(config_file)


class TestSetupLogging:
    """Test cases for setup_logging function."""

    @patch("logging.basicConfig")
    def test_setup_logging_normal(self, mock_basicConfig):
        """Test normal logging setup."""
        setup_logging(False)
        mock_basicConfig.assert_called_once()
        args, kwargs = mock_basicConfig.call_args
        assert kwargs["level"] == 20  # logging.INFO

    @patch("logging.basicConfig")
    def test_setup_logging_verbose(self, mock_basicConfig):
        """Test verbose logging setup."""
        setup_logging(True)
        mock_basicConfig.assert_called_once()
        args, kwargs = mock_basicConfig.call_args
        assert kwargs["level"] == 10  # logging.DEBUG


class TestMain:
    """Test cases for main function with YAML configuration."""

    @patch("cinemon.cli.blend_setup.BlenderProjectManager")
    @patch("cinemon.cli.blend_setup.CinemonConfigGenerator")
    @patch("cinemon.cli.blend_setup.load_yaml_config")
    @patch("cinemon.cli.blend_setup.parse_args")
    def test_main_with_preset_success(
        self, mock_parse_args, mock_load_yaml, mock_generator_class, mock_manager_class
    ):
        """Test successful main execution with preset."""
        # Setup mocks
        mock_args = Mock()
        mock_args.preset = "vintage"
        mock_args.config = None
        mock_args.recording_dir = Path("/test/recording")
        mock_args.main_audio = None
        mock_args.verbose = False
        mock_parse_args.return_value = mock_args

        mock_generator = Mock()
        mock_config_path = Path("/tmp/config.yaml")
        mock_generator.generate_preset.return_value = mock_config_path
        mock_generator_class.return_value = mock_generator

        mock_yaml_config = Mock()
        mock_load_yaml.return_value = mock_yaml_config

        mock_manager = Mock()
        mock_blend_path = Path("/test/recording/blender/project.blend")
        mock_manager.create_vse_project_with_config.return_value = mock_blend_path
        mock_manager_class.return_value = mock_manager

        # Run main
        result = main()

        # Verify calls
        assert result == 0
        mock_generator.generate_preset.assert_called_once_with(
            mock_args.recording_dir, "vintage"
        )
        mock_load_yaml.assert_called_once_with(mock_config_path)
        mock_manager.create_vse_project_with_config.assert_called_once_with(
            mock_args.recording_dir, mock_yaml_config
        )

    @patch("cinemon.cli.blend_setup.BlenderProjectManager")
    @patch("cinemon.cli.blend_setup.load_yaml_config")
    @patch("cinemon.cli.blend_setup.parse_args")
    def test_main_with_config_success(
        self, mock_parse_args, mock_load_yaml, mock_manager_class
    ):
        """Test successful main execution with config file."""
        # Setup mocks
        mock_args = Mock()
        mock_args.preset = None
        mock_args.config = Path("/test/config.yaml")
        mock_args.recording_dir = Path("/test/recording")
        mock_args.verbose = False
        mock_parse_args.return_value = mock_args

        mock_yaml_config = Mock()
        mock_load_yaml.return_value = mock_yaml_config

        mock_manager = Mock()
        mock_blend_path = Path("/test/recording/blender/project.blend")
        mock_manager.create_vse_project_with_config.return_value = mock_blend_path
        mock_manager_class.return_value = mock_manager

        # Run main
        result = main()

        # Verify calls
        assert result == 0
        mock_load_yaml.assert_called_once_with(mock_args.config)
        mock_manager.create_vse_project_with_config.assert_called_once_with(
            mock_args.recording_dir, mock_yaml_config
        )

    @patch("cinemon.cli.blend_setup.parse_args")
    def test_main_audio_validation_error(self, mock_parse_args):
        """Test main with audio validation error."""
        mock_args = Mock()
        mock_args.preset = "vintage"
        mock_args.config = None
        mock_args.verbose = False
        mock_parse_args.return_value = mock_args

        with patch(
            "cinemon.cli.blend_setup.CinemonConfigGenerator"
        ) as mock_generator_class:
            mock_generator = Mock()
            mock_generator.generate_preset.side_effect = AudioValidationError(
                "Audio error"
            )
            mock_generator_class.return_value = mock_generator

            result = main()

            assert result == 1

    @patch("cinemon.cli.blend_setup.parse_args")
    def test_main_validation_error(self, mock_parse_args):
        """Test main with validation error."""
        mock_args = Mock()
        mock_args.preset = "vintage"
        mock_args.config = None
        mock_args.verbose = False
        mock_parse_args.return_value = mock_args

        with patch(
            "cinemon.cli.blend_setup.CinemonConfigGenerator"
        ) as mock_generator_class:
            mock_generator = Mock()
            mock_generator.generate_preset.side_effect = ValueError("Validation error")
            mock_generator_class.return_value = mock_generator

            result = main()

            assert result == 1

    @patch("cinemon.cli.blend_setup.parse_args")
    def test_main_unexpected_error(self, mock_parse_args):
        """Test main with unexpected error."""
        mock_args = Mock()
        mock_args.preset = "vintage"
        mock_args.config = None
        mock_args.verbose = False
        mock_parse_args.return_value = mock_args

        with patch(
            "cinemon.cli.blend_setup.CinemonConfigGenerator"
        ) as mock_generator_class:
            mock_generator = Mock()
            mock_generator.generate_preset.side_effect = Exception("Unexpected error")
            mock_generator_class.return_value = mock_generator

            result = main()

            assert result == 1


class TestMainWithPresetOverrides:
    """Test main function with preset overrides."""

    @patch("cinemon.cli.blend_setup.BlenderProjectManager")
    @patch("cinemon.cli.blend_setup.CinemonConfigGenerator")
    @patch("cinemon.cli.blend_setup.load_yaml_config")
    @patch("cinemon.cli.blend_setup.parse_args")
    def test_main_with_preset_and_main_audio_override(
        self, mock_parse_args, mock_load_yaml, mock_generator_class, mock_manager_class
    ):
        """Test main with preset and main audio override."""
        # Setup mocks
        mock_args = Mock()
        mock_args.preset = "music-video"
        mock_args.config = None
        mock_args.recording_dir = Path("/test/recording")
        mock_args.main_audio = "custom_audio.m4a"
        mock_args.verbose = False
        mock_parse_args.return_value = mock_args

        mock_generator = Mock()
        mock_config_path = Path("/tmp/config.yaml")
        mock_generator.generate_preset.return_value = mock_config_path
        mock_generator_class.return_value = mock_generator

        mock_yaml_config = Mock()
        mock_load_yaml.return_value = mock_yaml_config

        mock_manager = Mock()
        mock_blend_path = Path("/test/recording/blender/project.blend")
        mock_manager.create_vse_project_with_config.return_value = mock_blend_path
        mock_manager_class.return_value = mock_manager

        # Run main
        result = main()

        # Verify calls with overrides
        assert result == 0
        mock_generator.generate_preset.assert_called_once_with(
            mock_args.recording_dir, "music-video", main_audio="custom_audio.m4a"
        )
