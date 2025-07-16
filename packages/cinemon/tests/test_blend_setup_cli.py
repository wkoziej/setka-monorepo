"""
Tests for blend_setup CLI.

This module contains unit tests for the blend_setup CLI module.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, Mock

from blender.cli.blend_setup import (
    parse_args,
    validate_recording_directory,
    main,
    setup_logging,
)
from beatrix import MultipleAudioFilesError


class TestParseArgs:
    """Test cases for parse_args function."""

    def test_parse_args_basic(self):
        """Test parsing basic arguments."""
        with patch("sys.argv", ["blend_setup.py", "/path/to/recording"]):
            args = parse_args()
            assert args.recording_dir == Path("/path/to/recording")
            assert args.verbose is False
            assert args.force is False
            assert args.main_audio is None

    def test_parse_args_all_flags(self):
        """Test parsing all arguments."""
        with patch(
            "sys.argv",
            [
                "blend_setup.py",
                "/path/to/recording",
                "--verbose",
                "--force",
                "--main-audio",
                "audio.mp3",
            ],
        ):
            args = parse_args()
            assert args.recording_dir == Path("/path/to/recording")
            assert args.verbose is True
            assert args.force is True
            assert args.main_audio == "audio.mp3"

    def test_parse_args_audio_analysis_flags(self):
        """Test parsing audio analysis arguments."""
        with patch(
            "sys.argv",
            [
                "blend_setup.py",
                "/path/to/recording",
                "--animation-mode",
                "beat-switch",
                "--beat-division",
                "4",
            ],
        ):
            args = parse_args()
            assert args.recording_dir == Path("/path/to/recording")
            assert args.animation_mode == "beat-switch"
            assert args.beat_division == 4

    def test_parse_args_audio_analysis_defaults(self):
        """Test default values for audio analysis arguments."""
        with patch("sys.argv", ["blend_setup.py", "/path/to/recording"]):
            args = parse_args()
            assert args.animation_mode == "none"
            assert args.beat_division == 8

    def test_parse_args_analyze_audio_flag(self):
        """Test --analyze-audio flag."""
        with patch(
            "sys.argv",
            [
                "blend_setup.py",
                "/path/to/recording",
                "--analyze-audio",
                "--animation-mode",
                "energy-pulse",
            ],
        ):
            args = parse_args()
            assert args.analyze_audio is True
            assert args.animation_mode == "energy-pulse"

    def test_parse_args_analyze_audio_default(self):
        """Test default value for --analyze-audio flag."""
        with patch("sys.argv", ["blend_setup.py", "/path/to/recording"]):
            args = parse_args()
            assert args.analyze_audio is False

    def test_parse_args_short_flags(self):
        """Test parsing short flag versions."""
        with patch("sys.argv", ["blend_setup.py", "/path/to/recording", "-v", "-f"]):
            args = parse_args()
            assert args.verbose is True
            assert args.force is True


class TestValidateRecordingDirectory:
    """Test cases for validate_recording_directory function."""

    def test_validate_nonexistent_directory(self, tmp_path):
        """Test validation with nonexistent directory."""
        nonexistent = tmp_path / "nonexistent"

        with pytest.raises(ValueError, match="Katalog nagrania nie istnieje"):
            validate_recording_directory(nonexistent)

    def test_validate_not_directory(self, tmp_path):
        """Test validation with file instead of directory."""
        file_path = tmp_path / "file.txt"
        file_path.touch()

        with pytest.raises(ValueError, match="Ścieżka nie jest katalogiem"):
            validate_recording_directory(file_path)

    def test_validate_missing_metadata(self, tmp_path):
        """Test validation with missing metadata.json."""
        recording_dir = tmp_path / "recording"
        recording_dir.mkdir()

        with pytest.raises(ValueError, match="Brak pliku metadata.json"):
            validate_recording_directory(recording_dir)

    def test_validate_missing_extracted_directory(self, tmp_path):
        """Test validation with missing extracted directory."""
        recording_dir = tmp_path / "recording"
        recording_dir.mkdir()

        # Create metadata.json
        metadata_file = recording_dir / "metadata.json"
        metadata_file.touch()

        with pytest.raises(ValueError, match="Brak katalogu extracted/"):
            validate_recording_directory(recording_dir)

    def test_validate_extracted_not_directory(self, tmp_path):
        """Test validation with extracted as file instead of directory."""
        recording_dir = tmp_path / "recording"
        recording_dir.mkdir()

        # Create metadata.json
        metadata_file = recording_dir / "metadata.json"
        metadata_file.touch()

        # Create extracted as file
        extracted_file = recording_dir / "extracted"
        extracted_file.touch()

        with pytest.raises(ValueError, match="extracted/ nie jest katalogiem"):
            validate_recording_directory(recording_dir)

    def test_validate_empty_extracted_directory(self, tmp_path):
        """Test validation with empty extracted directory."""
        recording_dir = tmp_path / "recording"
        recording_dir.mkdir()

        # Create metadata.json
        metadata_file = recording_dir / "metadata.json"
        metadata_file.touch()

        # Create empty extracted directory
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir()

        with pytest.raises(ValueError, match="Katalog extracted/ jest pusty"):
            validate_recording_directory(recording_dir)

    def test_validate_valid_directory(self, tmp_path):
        """Test validation with valid directory structure."""
        recording_dir = tmp_path / "recording"
        recording_dir.mkdir()

        # Create metadata.json
        metadata_file = recording_dir / "metadata.json"
        metadata_file.touch()

        # Create extracted directory with files
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir()

        # Add some files
        (extracted_dir / "video.mp4").touch()
        (extracted_dir / "audio.mp3").touch()

        # Should not raise exception
        validate_recording_directory(recording_dir)


class TestSetupLogging:
    """Test cases for setup_logging function."""

    @patch("logging.basicConfig")
    def test_setup_logging_normal(self, mock_basicConfig):
        """Test setup_logging with normal verbosity."""
        setup_logging(verbose=False)

        mock_basicConfig.assert_called_once()
        args, kwargs = mock_basicConfig.call_args
        assert kwargs["level"] == 20  # logging.INFO

    @patch("logging.basicConfig")
    def test_setup_logging_verbose(self, mock_basicConfig):
        """Test setup_logging with verbose mode."""
        setup_logging(verbose=True)

        mock_basicConfig.assert_called_once()
        args, kwargs = mock_basicConfig.call_args
        assert kwargs["level"] == 10  # logging.DEBUG


class TestMain:
    """Test cases for main function."""

    @patch("src.cli.blend_setup.parse_args")
    @patch("src.cli.blend_setup.validate_recording_directory")
    @patch("src.cli.blend_setup.BlenderProjectManager")
    @patch("src.cli.blend_setup.setup_logging")
    @patch("builtins.print")
    def test_main_success(
        self,
        mock_print,
        mock_setup_logging,
        mock_manager_class,
        mock_validate,
        mock_parse_args,
    ):
        """Test successful main execution."""
        # Setup mocks
        mock_args = Mock()
        mock_args.recording_dir = Path("/test/recording")
        mock_args.verbose = False
        mock_args.main_audio = None
        mock_args.analyze_audio = False
        mock_args.animation_mode = "none"
        mock_args.beat_division = 8
        mock_parse_args.return_value = mock_args

        mock_manager = Mock()
        mock_manager.create_vse_project.return_value = Path(
            "/test/recording/blender/project.blend"
        )
        mock_manager_class.return_value = mock_manager

        # Execute
        result = main()

        # Verify
        assert result == 0
        mock_setup_logging.assert_called_once_with(False)
        mock_validate.assert_called_once_with(mock_args.recording_dir)
        mock_manager.create_vse_project.assert_called_once_with(
            mock_args.recording_dir, None, animation_mode="none", beat_division=8
        )
        mock_print.assert_called_once()

    @patch("src.cli.blend_setup.parse_args")
    @patch("src.cli.blend_setup.validate_recording_directory")
    @patch("builtins.print")
    def test_main_validation_error(self, mock_print, mock_validate, mock_parse_args):
        """Test main with validation error."""
        # Setup mocks
        mock_args = Mock()
        mock_args.recording_dir = Path("/test/recording")
        mock_args.verbose = False
        mock_parse_args.return_value = mock_args

        mock_validate.side_effect = ValueError("Validation error")

        # Execute
        result = main()

        # Verify
        assert result == 1
        mock_print.assert_called_once()

    @patch("src.cli.blend_setup.parse_args")
    @patch("src.cli.blend_setup.validate_recording_directory")
    @patch("src.cli.blend_setup.BlenderProjectManager")
    @patch("builtins.print")
    def test_main_audio_validation_error(
        self, mock_print, mock_manager_class, mock_validate, mock_parse_args
    ):
        """Test main with audio validation error."""
        # Setup mocks
        mock_args = Mock()
        mock_args.recording_dir = Path("/test/recording")
        mock_args.verbose = False
        mock_args.main_audio = None
        mock_parse_args.return_value = mock_args

        mock_manager = Mock()
        mock_manager.create_vse_project.side_effect = MultipleAudioFilesError(
            "Multiple audio files"
        )
        mock_manager_class.return_value = mock_manager

        # Execute
        result = main()

        # Verify
        assert result == 1
        mock_print.assert_called_once()

    @patch("src.cli.blend_setup.parse_args")
    @patch("src.cli.blend_setup.validate_recording_directory")
    @patch("src.cli.blend_setup.BlenderProjectManager")
    @patch("builtins.print")
    def test_main_unexpected_error(
        self, mock_print, mock_manager_class, mock_validate, mock_parse_args
    ):
        """Test main with unexpected error."""
        # Setup mocks
        mock_args = Mock()
        mock_args.recording_dir = Path("/test/recording")
        mock_args.verbose = False
        mock_args.main_audio = None
        mock_parse_args.return_value = mock_args

        mock_manager = Mock()
        mock_manager.create_vse_project.side_effect = RuntimeError("Unexpected error")
        mock_manager_class.return_value = mock_manager

        # Execute
        result = main()

        # Verify
        assert result == 1
        mock_print.assert_called_once()


class TestBlendSetupAudioIntegration:
    """Test cases for blend_setup CLI with audio analysis integration."""

    @patch("src.cli.blend_setup.parse_args")
    @patch("src.cli.blend_setup.setup_logging")
    @patch("src.cli.blend_setup.validate_recording_directory")
    @patch("src.cli.blend_setup.BlenderProjectManager")
    @patch("src.cli.blend_setup.find_main_audio_file")
    @patch("src.cli.blend_setup.perform_audio_analysis")
    @patch("builtins.print")
    def test_main_with_audio_analysis(
        self,
        mock_print,
        mock_perform_analysis,
        mock_find_audio,
        mock_manager_class,
        mock_validate,
        mock_setup_logging,
        mock_parse_args,
    ):
        """Test main function with audio analysis enabled."""
        # Setup mocks
        mock_args = Mock()
        mock_args.recording_dir = Path("/test/recording")
        mock_args.verbose = False
        mock_args.main_audio = None
        mock_args.analyze_audio = True
        mock_args.animation_mode = "beat-switch"
        mock_args.beat_division = 4
        mock_parse_args.return_value = mock_args

        mock_manager = Mock()
        mock_manager.create_vse_project.return_value = Path("/test/output.blend")
        mock_manager_class.return_value = mock_manager

        # Mock audio file detection
        main_audio_file = Path("/test/recording/extracted/main_audio.m4a")
        mock_find_audio.return_value = main_audio_file

        # Mock analysis
        analysis_file = Path("/test/recording/analysis/audio_analysis.json")
        mock_perform_analysis.return_value = analysis_file

        # Execute
        result = main()

        # Verify
        assert result == 0
        mock_find_audio.assert_called_once_with(mock_args.recording_dir)
        mock_perform_analysis.assert_called_once_with(
            mock_args.recording_dir, main_audio_file
        )
        mock_manager.create_vse_project.assert_called_once_with(
            mock_args.recording_dir,
            mock_args.main_audio,
            animation_mode="beat-switch",
            beat_division=4,
        )

    def test_validate_animation_parameters_valid(self):
        """Test validation of valid animation parameters."""
        from blender.cli.blend_setup import validate_animation_parameters

        # Valid combinations
        validate_animation_parameters("none", 8)
        validate_animation_parameters("beat-switch", 4)
        validate_animation_parameters("energy-pulse", 16)

    def test_validate_animation_parameters_invalid(self):
        """Test validation of invalid animation parameters."""
        from blender.cli.blend_setup import validate_animation_parameters

        # Invalid animation mode
        with pytest.raises(ValueError, match="Invalid animation mode"):
            validate_animation_parameters("invalid-mode", 8)

        # Invalid beat division
        with pytest.raises(ValueError, match="Invalid beat division"):
            validate_animation_parameters("beat-switch", 3)
