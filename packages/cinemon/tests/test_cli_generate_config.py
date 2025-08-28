# ABOUTME: Tests for cinemon-generate-config CLI command functionality
# ABOUTME: Tests config generation with presets, listing presets, and command-line interface

"""Tests for cinemon-generate-config CLI."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from cinemon.cli.generate_config import (
    generate_config_command,
    list_presets_command,
    main,
)


class TestCinemonGenerateConfigCLI:
    """Test cases for cinemon-generate-config CLI command."""

    def test_main_missing_recording_directory(self):
        """Test main function with missing recording directory."""
        with patch(
            "sys.argv",
            ["cinemon-generate-config", "/nonexistent/path", "--preset", "minimal"],
        ):
            result = main()

        assert result == 1

    def test_main_invalid_preset_name(self, tmp_path):
        """Test main function with invalid preset name."""
        recording_dir = tmp_path / "test_recording"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        (extracted_dir / "Camera1.mp4").touch()

        with patch(
            "sys.argv",
            ["cinemon-generate-config", str(recording_dir), "--preset", "invalid"],
        ):
            result = main()

        assert result == 1

    def test_main_missing_required_arguments(self):
        """Test main function with missing required arguments."""
        with patch("sys.argv", ["cinemon-generate-config"]):
            result = main()

        assert result == 2  # argparse returns 2 for missing required arguments

    def test_main_no_video_files_error(self, tmp_path):
        """Test main function when no video files are found."""
        recording_dir = tmp_path / "test_recording"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        # Create only audio files, no video files
        (extracted_dir / "main_audio.m4a").touch()
        (recording_dir / "metadata.json").write_text('{"recording_info": "test"}')

        with patch(
            "sys.argv",
            ["cinemon-generate-config", str(recording_dir), "--preset", "minimal"],
        ):
            result = main()

        assert result == 1

    def test_main_no_audio_files_error(self, tmp_path):
        """Test main function when no audio files are found."""
        recording_dir = tmp_path / "test_recording"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        # Create only video files, no audio files
        (extracted_dir / "Camera1.mp4").touch()
        (recording_dir / "metadata.json").write_text('{"recording_info": "test"}')

        with patch(
            "sys.argv",
            ["cinemon-generate-config", str(recording_dir), "--preset", "minimal"],
        ):
            result = main()

        assert result == 1

    def test_main_multiple_audio_files_requires_main_audio(self, tmp_path):
        """Test that multiple audio files require --main-audio parameter."""
        recording_dir = tmp_path / "test_recording"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "audio1.m4a").touch()
        (extracted_dir / "audio2.wav").touch()

        with patch(
            "sys.argv",
            ["cinemon-generate-config", str(recording_dir), "--preset", "minimal"],
        ):
            result = main()

        assert result == 1  # Should fail without --main-audio

    def test_main_help_argument(self, capsys):
        """Test main function with --help argument."""
        with patch("sys.argv", ["cinemon-generate-config", "--help"]):
            result = main()

        assert result == 0  # Help should return 0

        captured = capsys.readouterr()
        assert "Generate YAML configuration for cinemon" in captured.out
        assert "--preset" in captured.out
        assert "--list-presets" in captured.out


class TestGenerateConfigCommand:
    """Test generate_config_command function."""

    def test_generate_config_command_file_not_found_error(self):
        """Test config generation with non-existent recording directory."""
        args = MagicMock()
        args.recording_dir = Path("/nonexistent/path")
        args.preset = "minimal"
        args.seed = None
        args.main_audio = None

        result = generate_config_command(args)

        assert result == 1

    def test_generate_config_command_invalid_preset_error(self, tmp_path):
        """Test config generation with invalid preset name."""
        recording_dir = tmp_path / "test_recording"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "main_audio.m4a").touch()

        args = MagicMock()
        args.recording_dir = recording_dir
        args.preset = "invalid_preset"
        args.seed = None
        args.main_audio = None

        result = generate_config_command(args)

        assert result == 1


class TestListPresetsCommand:
    """Test list_presets_command function."""

    def test_list_presets_command_success(self, capsys):
        """Test successful preset listing."""
        result = list_presets_command()

        assert result == 0

        captured = capsys.readouterr()
        assert "Available presets:" in captured.out
        assert "minimal" in captured.out

    def test_list_presets_command_shows_preset_names(self, capsys):
        """Test that preset listing shows preset names."""
        result = list_presets_command()

        assert result == 0

        captured = capsys.readouterr()
        assert "Available presets:" in captured.out
        assert "minimal" in captured.out


class TestCLIIntegration:
    """Test CLI integration and error handling."""

    def test_cli_preserves_current_directory(self, tmp_path):
        """Test that CLI preserves current working directory."""
        recording_dir = tmp_path / "test_recording"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "main_audio.m4a").touch()

        original_cwd = Path.cwd()

        with patch(
            "sys.argv",
            ["cinemon-generate-config", str(recording_dir), "--preset", "minimal"],
        ):
            main()

        assert Path.cwd() == original_cwd
