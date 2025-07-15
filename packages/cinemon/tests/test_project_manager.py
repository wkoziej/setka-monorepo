"""
Tests for BlenderProjectManager.

This module contains unit tests for the BlenderProjectManager class.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import subprocess

from blender.project_manager import BlenderProjectManager


class TestBlenderProjectManager:
    """Test cases for BlenderProjectManager class."""

    def test_init_default_executable(self):
        """Test BlenderProjectManager initialization with default executable."""
        manager = BlenderProjectManager()
        assert manager.blender_executable == "blender"
        assert manager.script_path.name == "blender_vse_script.py"

    def test_init_custom_executable(self):
        """Test BlenderProjectManager initialization with custom executable."""
        custom_blender = "/usr/local/bin/blender"
        manager = BlenderProjectManager(custom_blender)
        assert manager.blender_executable == custom_blender
        assert manager.script_path.name == "blender_vse_script.py"

    def test_create_vse_project_invalid_structure(self):
        """Test that create_vse_project raises ValueError for invalid structure."""
        manager = BlenderProjectManager()
        recording_path = Path("/tmp/test_recording")

        with pytest.raises(ValueError, match="Invalid recording structure"):
            manager.create_vse_project(recording_path)

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

    def test_prepare_environment_variables(self, tmp_path):
        """Test preparation of environment variables for parametric script."""
        manager = BlenderProjectManager()

        # Create test files
        video_files = [tmp_path / "video1.mp4", tmp_path / "video2.mkv"]
        main_audio = tmp_path / "audio.m4a"
        output_blend = tmp_path / "project.blend"
        render_output = tmp_path / "render" / "output.mp4"

        for file_path in video_files + [main_audio]:
            file_path.touch()

        env_vars = manager._prepare_environment_variables(
            video_files, main_audio, output_blend, render_output, fps=25
        )

        # Check environment variables
        assert "BLENDER_VSE_VIDEO_FILES" in env_vars
        assert "BLENDER_VSE_MAIN_AUDIO" in env_vars
        assert "BLENDER_VSE_OUTPUT_BLEND" in env_vars
        assert "BLENDER_VSE_RENDER_OUTPUT" in env_vars
        assert env_vars["BLENDER_VSE_FPS"] == "25"
        assert env_vars["BLENDER_VSE_RESOLUTION_X"] == "1280"
        assert env_vars["BLENDER_VSE_RESOLUTION_Y"] == "720"

        # Check video files are comma-separated
        video_files_str = env_vars["BLENDER_VSE_VIDEO_FILES"]
        assert str(video_files[0].resolve()) in video_files_str
        assert str(video_files[1].resolve()) in video_files_str
        assert "," in video_files_str

        # Check render output directory was created
        assert render_output.parent.exists()

    @patch("subprocess.run")
    def test_execute_blender_with_params_success(self, mock_run, tmp_path):
        """Test successful execution of Blender with parameters."""
        mock_run.return_value = Mock(stdout="Success", stderr="")

        manager = BlenderProjectManager()
        # Create mock script file
        manager.script_path = tmp_path / "blender_vse_script.py"
        manager.script_path.touch()

        env_vars = {
            "BLENDER_VSE_VIDEO_FILES": "/tmp/video1.mp4,/tmp/video2.mp4",
            "BLENDER_VSE_MAIN_AUDIO": "/tmp/audio.m4a",
            "BLENDER_VSE_OUTPUT_BLEND": "/tmp/project.blend",
            "BLENDER_VSE_RENDER_OUTPUT": "/tmp/render/output.mp4",
            "BLENDER_VSE_FPS": "30",
            "BLENDER_VSE_RESOLUTION_X": "1280",
            "BLENDER_VSE_RESOLUTION_Y": "720",
        }

        # Should not raise exception
        manager._execute_blender_with_params(env_vars)

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
        ]
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True
        assert kwargs["check"] is True

        # Check environment variables were passed
        env = kwargs["env"]
        for key, value in env_vars.items():
            assert env[key] == value

    @patch("subprocess.run")
    def test_execute_blender_with_params_custom_executable(self, mock_run, tmp_path):
        """Test execution with custom Blender executable."""
        mock_run.return_value = Mock(stdout="Success", stderr="")

        manager = BlenderProjectManager("/usr/local/bin/blender")
        # Create mock script file
        manager.script_path = tmp_path / "blender_vse_script.py"
        manager.script_path.touch()

        env_vars = {"BLENDER_VSE_FPS": "30"}

        # Should not raise exception
        manager._execute_blender_with_params(env_vars)

        # Check subprocess.run was called with custom executable
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == [
            "/usr/local/bin/blender",
            "--background",
            "--python",
            str(manager.script_path),
        ]

    def test_execute_blender_with_params_missing_script(self, tmp_path):
        """Test execution when script file doesn't exist."""
        manager = BlenderProjectManager()
        manager.script_path = tmp_path / "nonexistent_script.py"

        env_vars = {"BLENDER_VSE_FPS": "30"}

        with pytest.raises(RuntimeError, match="Blender VSE script not found"):
            manager._execute_blender_with_params(env_vars)

    @patch("subprocess.run")
    def test_execute_blender_with_params_failure(self, mock_run, tmp_path):
        """Test failed execution of Blender with parameters."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "blender", stderr="Blender error"
        )

        manager = BlenderProjectManager()
        # Create mock script file
        manager.script_path = tmp_path / "blender_vse_script.py"
        manager.script_path.touch()

        env_vars = {"BLENDER_VSE_FPS": "30"}

        with pytest.raises(RuntimeError, match="Blender execution failed"):
            manager._execute_blender_with_params(env_vars)

    def test_create_vse_project_no_video_files(self, sample_recording_structure):
        """Test create_vse_project with no video files."""
        # Remove video files from extracted directory
        extracted_dir = sample_recording_structure / "extracted"
        for file_path in extracted_dir.glob("*.mp4"):
            file_path.unlink()

        manager = BlenderProjectManager()

        with pytest.raises(ValueError, match="No video files found"):
            manager.create_vse_project(sample_recording_structure)

    @patch("subprocess.run")
    def test_create_vse_project_success(
        self, mock_run, sample_recording_structure, tmp_path
    ):
        """Test successful create_vse_project execution."""
        # Mock successful subprocess execution
        mock_run.return_value = Mock(stdout="Success", stderr="")

        manager = BlenderProjectManager()
        # Create mock script file
        manager.script_path = tmp_path / "blender_vse_script.py"
        manager.script_path.touch()

        # Should not raise exception and return blend path
        result = manager.create_vse_project(sample_recording_structure)

        # Check result
        expected_blend = (
            sample_recording_structure
            / "blender"
            / f"{sample_recording_structure.name}.blend"
        )
        assert result == expected_blend

        # Check subprocess was called
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[:3] == ["snap", "run", "blender"]

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


class TestBlenderProjectManagerAudioIntegration:
    """Test cases for BlenderProjectManager with audio analysis integration."""

    def test_prepare_environment_variables_with_audio_analysis(self, tmp_path):
        """Test environment variables preparation with audio analysis data."""
        manager = BlenderProjectManager()

        # Create test video files
        video_files = [tmp_path / "camera1.mp4", tmp_path / "screen.mkv"]
        for vf in video_files:
            vf.touch()

        # Create test audio file
        main_audio = tmp_path / "main_audio.m4a"
        main_audio.touch()

        # Create test paths
        output_blend = tmp_path / "project.blend"
        render_output = tmp_path / "render" / "project_final.mp4"

        # Create test audio analysis data
        analysis_data = {
            "duration": 10.0,
            "tempo": {"bpm": 120.0},
            "animation_events": {"beats": [1.0, 2.0, 3.0]},
        }

        # Create a temporary analysis file
        import json as json_module

        analysis_file = tmp_path / "analysis" / "test_analysis.json"
        analysis_file.parent.mkdir(exist_ok=True)
        with open(analysis_file, "w") as f:
            json_module.dump(analysis_data, f)

        # Test with audio analysis
        env_vars = manager._prepare_environment_variables_with_analysis(
            video_files,
            main_audio,
            output_blend,
            render_output,
            fps=30,
            analysis_file_path=analysis_file,
            animation_mode="beat-switch",
            beat_division=8,
        )

        # Check standard variables exist
        assert "BLENDER_VSE_VIDEO_FILES" in env_vars
        assert "BLENDER_VSE_MAIN_AUDIO" in env_vars
        assert "BLENDER_VSE_OUTPUT_BLEND" in env_vars
        assert "BLENDER_VSE_RENDER_OUTPUT" in env_vars
        assert "BLENDER_VSE_FPS" in env_vars

        # Check new audio analysis variables
        assert env_vars["BLENDER_VSE_ANIMATION_MODE"] == "beat-switch"
        assert env_vars["BLENDER_VSE_BEAT_DIVISION"] == "8"
        assert "BLENDER_VSE_AUDIO_ANALYSIS_FILE" in env_vars
        assert env_vars["BLENDER_VSE_AUDIO_ANALYSIS_FILE"] == str(analysis_file)

        # Verify analysis file contains correct data
        with open(analysis_file, "r") as f:
            loaded_analysis = json_module.load(f)
        assert loaded_analysis == analysis_data

    def test_prepare_environment_variables_without_audio_analysis(self, tmp_path):
        """Test environment variables preparation without audio analysis."""
        manager = BlenderProjectManager()

        # Create test video files
        video_files = [tmp_path / "camera1.mp4"]
        for vf in video_files:
            vf.touch()

        main_audio = tmp_path / "main_audio.m4a"
        main_audio.touch()

        output_blend = tmp_path / "project.blend"
        render_output = tmp_path / "render" / "project_final.mp4"

        # Test without audio analysis
        env_vars = manager._prepare_environment_variables_with_analysis(
            video_files, main_audio, output_blend, render_output, fps=30
        )

        # Check standard variables exist
        assert "BLENDER_VSE_VIDEO_FILES" in env_vars
        assert "BLENDER_VSE_MAIN_AUDIO" in env_vars

        # Check audio analysis variables are not set or have defaults
        assert env_vars.get("BLENDER_VSE_ANIMATION_MODE") == "none"
        assert env_vars.get("BLENDER_VSE_BEAT_DIVISION") == "8"
        assert env_vars.get("BLENDER_VSE_AUDIO_ANALYSIS_FILE") == ""

    def test_create_vse_project_with_audio_analysis(
        self, sample_recording_structure, tmp_path
    ):
        """Test create_vse_project with audio analysis integration."""
        # Create audio analysis file
        from setka_common.file_structure.specialized import FileStructureManager

        analysis_data = {
            "duration": 5.0,
            "tempo": {"bpm": 140.0},
            "animation_events": {"beats": [0.5, 1.0, 1.5]},
        }

        # Save analysis to structure
        video_file = sample_recording_structure / "test_video.mkv"
        video_file.touch()
        FileStructureManager.save_audio_analysis(video_file, analysis_data)

        manager = BlenderProjectManager()
        # Create mock script file
        manager.script_path = tmp_path / "blender_vse_script.py"
        manager.script_path.touch()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout="Success", stderr="")

            # Create project with animation mode
            _ = manager.create_vse_project(
                sample_recording_structure,
                animation_mode="beat-switch",
                beat_division=4,
            )

            # Verify subprocess was called
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args

            # Check environment variables were passed
            env_passed = kwargs.get("env", {})
            assert "BLENDER_VSE_ANIMATION_MODE" in env_passed
            assert env_passed["BLENDER_VSE_ANIMATION_MODE"] == "beat-switch"
            assert env_passed["BLENDER_VSE_BEAT_DIVISION"] == "4"

    def test_create_vse_project_missing_audio_analysis(
        self, sample_recording_structure, tmp_path
    ):
        """Test create_vse_project when audio analysis is requested but missing."""
        manager = BlenderProjectManager()
        manager.script_path = tmp_path / "blender_vse_script.py"
        manager.script_path.touch()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout="Success", stderr="")

            # Create project with animation mode but no analysis file
            _ = manager.create_vse_project(
                sample_recording_structure, animation_mode="beat-switch"
            )

            # Should succeed but use default/empty analysis
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            env_passed = kwargs.get("env", {})
            assert env_passed["BLENDER_VSE_ANIMATION_MODE"] == "beat-switch"
            # File path should be generated even if file doesn't exist (Blender will handle gracefully)
            expected_path = (
                sample_recording_structure
                / "analysis"
                / f"{sample_recording_structure.name}_analysis.json"
            )
            assert env_passed["BLENDER_VSE_AUDIO_ANALYSIS_FILE"] == str(expected_path)

    def test_validate_animation_mode_valid_modes(self):
        """Test validation of animation modes."""
        manager = BlenderProjectManager()

        valid_modes = [
            "none",
            "beat-switch",
            "energy-pulse",
            "section-transition",
            "multi-pip",
        ]
        for mode in valid_modes:
            # Should not raise exception
            manager._validate_animation_mode(mode)

    def test_validate_animation_mode_invalid_mode(self):
        """Test validation of invalid animation mode."""
        manager = BlenderProjectManager()

        with pytest.raises(ValueError, match="Invalid animation mode"):
            manager._validate_animation_mode("invalid-mode")

    def test_validate_beat_division_valid_values(self):
        """Test validation of beat division values."""
        manager = BlenderProjectManager()

        valid_divisions = [1, 2, 4, 8, 16]
        for division in valid_divisions:
            # Should not raise exception
            manager._validate_beat_division(division)

    def test_validate_beat_division_invalid_values(self):
        """Test validation of invalid beat division values."""
        manager = BlenderProjectManager()

        invalid_divisions = [0, -1, 3, 5, 32]
        for division in invalid_divisions:
            with pytest.raises(ValueError, match="Invalid beat division"):
                manager._validate_beat_division(division)
