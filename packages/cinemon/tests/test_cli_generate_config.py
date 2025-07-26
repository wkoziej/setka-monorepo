# ABOUTME: Tests for cinemon-generate-config CLI command functionality
# ABOUTME: Tests config generation with presets, listing presets, and command-line interface

"""Tests for cinemon-generate-config CLI."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml

from blender.cli.generate_config import (
    generate_config_command,
    list_presets_command,
    main,
)


class TestCinemonGenerateConfigCLI:
    """Test cases for cinemon-generate-config CLI command."""

    def test_main_with_preset_argument_success(self, tmp_path):
        """Test successful main function with --preset argument."""
        # Setup test recording structure
        recording_dir = tmp_path / "test_recording"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        # Create test media files
        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "Camera2.mp4").touch()
        (extracted_dir / "main_audio.m4a").touch()
        (recording_dir / "metadata.json").write_text('{"recording_info": "test"}')

        with patch(
            "sys.argv",
            ["cinemon-generate-config", str(recording_dir), "--preset", "vintage"],
        ):
            result = main()

        assert result == 0

        # Verify config file was created
        config_file = recording_dir / "animation_config_vintage.yaml"
        assert config_file.exists()

        # Verify config content
        with config_file.open("r") as f:
            config_data = yaml.safe_load(f)

        assert "project" in config_data
        assert "layout" in config_data
        assert "animations" in config_data
        assert config_data["project"]["main_audio"] == "main_audio.m4a"

    def test_main_with_preset_and_seed_override(self, tmp_path):
        """Test main function with preset and seed override."""
        recording_dir = tmp_path / "test_recording"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "main_audio.m4a").touch()

        with patch(
            "sys.argv",
            [
                "cinemon-generate-config",
                str(recording_dir),
                "--preset",
                "vintage",
                "--seed",
                "42",
            ],
        ):
            result = main()

        assert result == 0

        config_file = recording_dir / "animation_config_vintage.yaml"
        with config_file.open("r") as f:
            config_data = yaml.safe_load(f)

        assert config_data["layout"]["config"]["seed"] == 42

    def test_main_with_preset_and_main_audio_override(self, tmp_path):
        """Test main function with preset and main audio override."""
        recording_dir = tmp_path / "test_recording"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "audio1.m4a").touch()
        (extracted_dir / "audio2.wav").touch()

        with patch(
            "sys.argv",
            [
                "cinemon-generate-config",
                str(recording_dir),
                "--preset",
                "music-video",
                "--main-audio",
                "audio2.wav",
            ],
        ):
            result = main()

        assert result == 0

        config_file = recording_dir / "animation_config_music-video.yaml"
        with config_file.open("r") as f:
            config_data = yaml.safe_load(f)

        assert config_data["project"]["main_audio"] == "audio2.wav"

    def test_main_list_presets_command(self, capsys):
        """Test main function with --list-presets argument."""
        with patch("sys.argv", ["cinemon-generate-config", "--list-presets"]):
            result = main()

        assert result == 0

        captured = capsys.readouterr()
        assert "Available presets:" in captured.out
        assert "vintage" in captured.out
        assert "music-video" in captured.out
        assert "minimal" in captured.out
        assert "beat-switch" in captured.out

    def test_main_missing_recording_directory(self):
        """Test main function with missing recording directory."""
        with patch(
            "sys.argv",
            ["cinemon-generate-config", "/nonexistent/path", "--preset", "vintage"],
        ):
            result = main()

        assert result == 1

    def test_main_invalid_preset_name(self, tmp_path):
        """Test main function with invalid preset name."""
        recording_dir = tmp_path / "test_recording"
        recording_dir.mkdir()

        with patch(
            "sys.argv",
            ["cinemon-generate-config", str(recording_dir), "--preset", "nonexistent"],
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

        # Only audio file, no video
        (extracted_dir / "audio_only.m4a").touch()

        with patch(
            "sys.argv",
            ["cinemon-generate-config", str(recording_dir), "--preset", "vintage"],
        ):
            result = main()

        assert result == 1

    def test_main_no_audio_files_error(self, tmp_path):
        """Test main function when no audio files are found."""
        recording_dir = tmp_path / "test_recording"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        # Only video file, no audio
        (extracted_dir / "video_only.mp4").touch()

        with patch(
            "sys.argv",
            ["cinemon-generate-config", str(recording_dir), "--preset", "vintage"],
        ):
            result = main()

        assert result == 1

    def test_main_multiple_audio_files_requires_main_audio(self, tmp_path):
        """Test main function with multiple audio files requires --main-audio."""
        recording_dir = tmp_path / "test_recording"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "audio1.m4a").touch()
        (extracted_dir / "audio2.wav").touch()

        with patch(
            "sys.argv",
            ["cinemon-generate-config", str(recording_dir), "--preset", "vintage"],
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
    """Test cases for generate_config_command function."""

    def test_generate_config_command_success(self, tmp_path):
        """Test successful config generation."""
        recording_dir = tmp_path / "test_recording"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "main_audio.m4a").touch()

        args = MagicMock()
        args.recording_dir = recording_dir
        args.preset = "vintage"
        args.seed = None
        args.main_audio = None

        result = generate_config_command(args)

        assert result == 0

        config_file = recording_dir / "animation_config_vintage.yaml"
        assert config_file.exists()

    def test_generate_config_command_with_overrides(self, tmp_path):
        """Test config generation with parameter overrides."""
        recording_dir = tmp_path / "test_recording"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "audio.m4a").touch()

        args = MagicMock()
        args.recording_dir = recording_dir
        args.preset = "music-video"
        args.seed = 123
        args.main_audio = "audio.m4a"

        result = generate_config_command(args)

        assert result == 0

        config_file = recording_dir / "animation_config_music-video.yaml"
        with config_file.open("r") as f:
            config_data = yaml.safe_load(f)

        assert config_data["layout"]["config"]["seed"] == 123
        assert config_data["project"]["main_audio"] == "audio.m4a"

    def test_generate_config_command_file_not_found_error(self):
        """Test config generation with nonexistent directory."""
        args = MagicMock()
        args.recording_dir = Path("/nonexistent/path")
        args.preset = "vintage"
        args.seed = None
        args.main_audio = None

        result = generate_config_command(args)

        assert result == 1

    def test_generate_config_command_invalid_preset_error(self, tmp_path):
        """Test config generation with invalid preset."""
        recording_dir = tmp_path / "test_recording"
        recording_dir.mkdir()

        args = MagicMock()
        args.recording_dir = recording_dir
        args.preset = "nonexistent"
        args.seed = None
        args.main_audio = None

        result = generate_config_command(args)

        assert result == 1


class TestListPresetsCommand:
    """Test cases for list_presets_command function."""

    def test_list_presets_command_success(self, capsys):
        """Test successful preset listing."""
        result = list_presets_command()

        assert result == 0

        captured = capsys.readouterr()
        assert "Available presets:" in captured.out
        assert "vintage" in captured.out
        assert "music-video" in captured.out
        assert "minimal" in captured.out
        assert "beat-switch" in captured.out

    def test_list_presets_command_shows_descriptions(self, capsys):
        """Test that preset listing shows descriptions."""
        result = list_presets_command()

        assert result == 0

        captured = capsys.readouterr()
        assert "Classic film effects" in captured.out
        assert "High-energy effects" in captured.out
        assert "Clean, simple animation" in captured.out
        assert "Legacy compatibility" in captured.out


class TestCLIIntegration:
    """Test CLI integration and error handling."""

    def test_cli_preserves_current_directory(self, tmp_path):
        """Test that CLI doesn't change current working directory."""
        original_cwd = Path.cwd()

        recording_dir = tmp_path / "test_recording"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "main_audio.m4a").touch()

        with patch(
            "sys.argv",
            ["cinemon-generate-config", str(recording_dir), "--preset", "vintage"],
        ):
            main()

        assert Path.cwd() == original_cwd

    def test_cli_handles_polish_characters(self, tmp_path):
        """Test CLI with Polish character filenames."""
        recording_dir = tmp_path / "nagranie_testowe"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        (extracted_dir / "Kamera główna.mp4").touch()
        (extracted_dir / "Przechwytywanie dźwięku.m4a").touch()

        with patch(
            "sys.argv",
            ["cinemon-generate-config", str(recording_dir), "--preset", "vintage"],
        ):
            result = main()

        assert result == 0

        config_file = recording_dir / "animation_config_vintage.yaml"
        with config_file.open("r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        assert config_data["project"]["main_audio"] == "Przechwytywanie dźwięku.m4a"
        assert "Kamera główna.mp4" in config_data["project"]["video_files"]

    def test_cli_overwrites_existing_config(self, tmp_path):
        """Test that CLI overwrites existing configuration files."""
        recording_dir = tmp_path / "test_recording"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "main_audio.m4a").touch()

        config_file = recording_dir / "animation_config_vintage.yaml"
        config_file.write_text("existing: config")

        with patch(
            "sys.argv",
            ["cinemon-generate-config", str(recording_dir), "--preset", "vintage"],
        ):
            result = main()

        assert result == 0

        # Verify file was overwritten
        with config_file.open("r") as f:
            config_data = yaml.safe_load(f)

        assert "existing" not in config_data
        assert "project" in config_data
