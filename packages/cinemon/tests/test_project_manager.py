"""
Tests for BlenderProjectManager with YAML API only.

This module contains unit tests for the BlenderProjectManager class.
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from setka_common.config.yaml_config import (
    AudioAnalysisConfig,
    BlenderYAMLConfig,
    LayoutConfig,
    ProjectConfig,
)

from cinemon.project_manager import BlenderProjectManager


class TestBlenderProjectManager:
    """Test cases for BlenderProjectManager class."""

    def test_init_default_executable(self):
        """Test BlenderProjectManager initialization with default executable."""
        manager = BlenderProjectManager()
        assert manager.blender_executable == "blender"
        assert manager.script_path.name == "vse_script.py"

    def test_init_custom_executable(self):
        """Test BlenderProjectManager initialization with custom executable."""
        custom_blender = "/usr/local/bin/blender"
        manager = BlenderProjectManager(custom_blender)
        assert manager.blender_executable == custom_blender
        assert manager.script_path.name == "vse_script.py"

    def test_find_video_files_empty_directory(self, tmp_path):
        """Test find_video_files with empty directory."""
        manager = BlenderProjectManager()
        video_files = manager.find_video_files(tmp_path)
        assert video_files == []

    def test_find_video_files_with_videos(self, tmp_path):
        """Test find_video_files with video files."""
        # Create test video files
        video_files = [
            tmp_path / "camera1.mp4",
            tmp_path / "screen.mkv",
            tmp_path / "audio.mp3",  # Should be ignored
            tmp_path / "document.txt",  # Should be ignored
        ]

        for file_path in video_files:
            file_path.touch()

        manager = BlenderProjectManager()
        found_videos = manager.find_video_files(tmp_path)

        # Should find only video files, sorted by name
        expected = [tmp_path / "camera1.mp4", tmp_path / "screen.mkv"]
        assert found_videos == expected

    def test_find_video_files_sorting(self, tmp_path):
        """Test that find_video_files returns sorted results."""
        # Create video files in non-alphabetical order
        video_files = [
            tmp_path / "zebra.mp4",
            tmp_path / "alpha.mkv",
            tmp_path / "beta.avi",
        ]

        for file_path in video_files:
            file_path.touch()

        manager = BlenderProjectManager()
        found_videos = manager.find_video_files(tmp_path)

        # Should be sorted alphabetically
        expected = [
            tmp_path / "alpha.mkv",
            tmp_path / "beta.avi",
            tmp_path / "zebra.mp4",
        ]
        assert found_videos == expected

    def test_find_video_files_case_insensitive(self, tmp_path):
        """Test that find_video_files handles case insensitive extensions."""
        video_files = [
            tmp_path / "video1.MP4",
            tmp_path / "video2.MKV",
            tmp_path / "video3.AVI",
        ]

        for file_path in video_files:
            file_path.touch()

        manager = BlenderProjectManager()
        found_videos = manager.find_video_files(tmp_path)

        assert len(found_videos) == 3
        assert all(f.suffix.lower() in [".mp4", ".mkv", ".avi"] for f in found_videos)

    def test_read_fps_from_metadata(self, tmp_path):
        """Test reading FPS from metadata.json file."""
        metadata_file = tmp_path / "metadata.json"
        metadata_content = '{"fps": 25, "resolution": "1280x720"}'
        metadata_file.write_text(metadata_content)

        manager = BlenderProjectManager()
        fps = manager._read_fps_from_metadata(metadata_file)

        assert fps == 25

    def test_read_fps_from_metadata_string_value(self, tmp_path):
        """Test reading FPS from metadata.json with string value."""
        metadata_file = tmp_path / "metadata.json"
        metadata_content = '{"fps": "29.97", "resolution": "1280x720"}'
        metadata_file.write_text(metadata_content)

        manager = BlenderProjectManager()
        fps = manager._read_fps_from_metadata(metadata_file)

        assert fps == 29

    def test_read_fps_from_metadata_default(self, tmp_path):
        """Test reading FPS from metadata.json with missing fps field."""
        metadata_file = tmp_path / "metadata.json"
        metadata_content = '{"resolution": "1280x720"}'
        metadata_file.write_text(metadata_content)

        manager = BlenderProjectManager()
        fps = manager._read_fps_from_metadata(metadata_file)

        assert fps == 30  # Default value

    def test_read_fps_from_metadata_invalid_file(self, tmp_path):
        """Test reading FPS from invalid metadata.json file."""
        metadata_file = tmp_path / "metadata.json"
        metadata_file.write_text("invalid json content")

        manager = BlenderProjectManager()
        fps = manager._read_fps_from_metadata(metadata_file)

        assert fps == 30  # Default value

    def test_read_fps_from_metadata_nonexistent_file(self, tmp_path):
        """Test reading FPS from nonexistent metadata.json file."""
        metadata_file = tmp_path / "nonexistent.json"

        manager = BlenderProjectManager()
        fps = manager._read_fps_from_metadata(metadata_file)

        assert fps == 30  # Default value

    @patch("subprocess.run")
    def test_execute_blender_with_yaml_config_success(self, mock_run, tmp_path):
        """Test successful execution of Blender with YAML config."""
        mock_run.return_value = Mock(stdout="Success", stderr="")

        manager = BlenderProjectManager()
        # Create mock script file
        manager.script_path = tmp_path / "vse_script.py"
        manager.script_path.touch()

        # Create a temporary YAML config file
        config_path = tmp_path / "test_config.yaml"
        config_path.write_text("project:\n  video_files: []\n")

        # Should not raise exception
        manager._execute_blender_with_config(str(config_path))

        # Check subprocess.run was called with correct arguments
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == [
            "snap",
            "run",
            "blender",
            "--background",
            "--python",
            str(manager.script_path),
            "--",
            "--config",
            str(config_path),
        ]
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True
        assert kwargs["check"] is True

    @patch("subprocess.run")
    def test_execute_blender_with_yaml_config_custom_executable(
        self, mock_run, tmp_path
    ):
        """Test execution with custom Blender executable."""
        mock_run.return_value = Mock(stdout="Success", stderr="")

        manager = BlenderProjectManager("/usr/local/bin/blender")
        # Create mock script file
        manager.script_path = tmp_path / "vse_script.py"
        manager.script_path.touch()

        config_path = tmp_path / "test_config.yaml"
        config_path.write_text("project:\n  video_files: []\n")

        # Should not raise exception
        manager._execute_blender_with_config(str(config_path))

        # Check subprocess.run was called with custom executable
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == [
            "/usr/local/bin/blender",
            "--background",
            "--python",
            str(manager.script_path),
            "--",
            "--config",
            str(config_path),
        ]

    def test_execute_blender_with_yaml_config_missing_script(self, tmp_path):
        """Test execution when script file doesn't exist."""
        manager = BlenderProjectManager()
        manager.script_path = tmp_path / "nonexistent_script.py"

        config_path = tmp_path / "test_config.yaml"
        config_path.write_text("project:\n  video_files: []\n")

        with pytest.raises(RuntimeError, match="Blender VSE script not found"):
            manager._execute_blender_with_config(str(config_path))

    @patch("subprocess.run")
    def test_execute_blender_with_yaml_config_failure(self, mock_run, tmp_path):
        """Test failed execution of Blender with YAML config."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "blender", stderr="Blender error"
        )

        manager = BlenderProjectManager()
        # Create mock script file
        manager.script_path = tmp_path / "vse_script.py"
        manager.script_path.touch()

        config_path = tmp_path / "test_config.yaml"
        config_path.write_text("project:\n  video_files: []\n")

        with pytest.raises(RuntimeError, match="Blender execution failed"):
            manager._execute_blender_with_config(str(config_path))

    def test_validate_animation_mode(self):
        """Test _validate_animation_mode method."""
        manager = BlenderProjectManager()

        # Valid mode should not raise
        manager._validate_animation_mode("compositional")

        # Invalid mode should raise
        with pytest.raises(ValueError, match="Invalid animation mode"):
            manager._validate_animation_mode("invalid-mode")

    def test_validate_beat_division(self):
        """Test _validate_beat_division method."""
        manager = BlenderProjectManager()

        # Valid divisions should not raise
        for division in [1, 2, 4, 8, 16]:
            manager._validate_beat_division(division)

        # Invalid divisions should raise
        with pytest.raises(ValueError, match="Invalid beat division"):
            manager._validate_beat_division(3)
