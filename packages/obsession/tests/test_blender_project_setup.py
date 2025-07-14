"""
ABOUTME: Tests for BlenderProjectSetup class - validates Blender VSE project setup functionality.
ABOUTME: TDD approach - tests written first to define expected project setup behavior.
"""

import pytest
from pathlib import Path
import sys
from unittest.mock import Mock, patch

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.blender_vse.project_setup import BlenderProjectSetup


class TestBlenderProjectSetupBasic:
    """Test basic BlenderProjectSetup functionality."""

    def test_project_setup_initialization(self):
        """BlenderProjectSetup should initialize with provided parameters."""
        config = {
            "fps": 30,
            "resolution_x": 1280,
            "resolution_y": 720,
            "video_files": [Path("video1.mp4"), Path("video2.mp4")],
            "main_audio": Path("audio.m4a"),
            "output_blend": Path("project.blend"),
            "render_output": Path("render.mp4"),
        }

        setup = BlenderProjectSetup(config)

        assert setup is not None
        assert hasattr(setup, "config")
        assert setup.config == config

    def test_project_setup_has_required_methods(self):
        """BlenderProjectSetup should have required setup methods."""
        config = {"fps": 30, "resolution_x": 1280, "resolution_y": 720}
        setup = BlenderProjectSetup(config)

        required_methods = [
            "setup_scene",
            "setup_sequence_editor",
            "setup_render_settings",
            "add_main_audio",
            "add_video_strips",
            "calculate_timeline_length",
            "save_project",
            "setup_project",
        ]

        for method in required_methods:
            assert hasattr(setup, method), f"Missing method: {method}"
            assert callable(getattr(setup, method)), f"Method {method} is not callable"

    def test_project_setup_validates_config(self):
        """BlenderProjectSetup should validate configuration on initialization."""
        # Valid config should not raise
        valid_config = {
            "fps": 30,
            "resolution_x": 1280,
            "resolution_y": 720,
            "video_files": [],
            "main_audio": None,
            "output_blend": None,
            "render_output": None,
        }

        setup = BlenderProjectSetup(valid_config)
        assert setup is not None

        # Invalid FPS should raise
        invalid_config = {"fps": 0, "resolution_x": 1280, "resolution_y": 720}

        with pytest.raises(ValueError, match="FPS must be positive"):
            BlenderProjectSetup(invalid_config)

        # Invalid resolution should raise
        invalid_config = {"fps": 30, "resolution_x": 0, "resolution_y": 720}

        with pytest.raises(ValueError, match="Resolution must be positive"):
            BlenderProjectSetup(invalid_config)


class TestBlenderProjectSetupSceneSetup:
    """Test scene setup functionality."""

    @patch("core.blender_vse.project_setup.bpy")
    def test_setup_scene_clears_default_scene(self, mock_bpy):
        """Should clear default scene and create new one."""
        config = {"fps": 30, "resolution_x": 1280, "resolution_y": 720}
        setup = BlenderProjectSetup(config)

        result = setup.setup_scene()

        assert result is True
        mock_bpy.ops.wm.read_factory_settings.assert_called_once_with(use_empty=True)

    @patch("core.blender_vse.project_setup.bpy")
    def test_setup_scene_configures_basic_settings(self, mock_bpy):
        """Should configure basic scene settings (FPS, resolution)."""
        config = {"fps": 60, "resolution_x": 1920, "resolution_y": 1080}
        setup = BlenderProjectSetup(config)

        # Mock scene object
        mock_scene = Mock()
        mock_scene.render = Mock()
        mock_bpy.context.scene = mock_scene

        result = setup.setup_scene()

        assert result is True
        assert mock_scene.render.fps == 60
        assert mock_scene.render.resolution_x == 1920
        assert mock_scene.render.resolution_y == 1080
        assert mock_scene.frame_start == 1

    @patch("core.blender_vse.project_setup.bpy")
    def test_setup_scene_handles_errors(self, mock_bpy):
        """Should handle Blender API errors gracefully."""
        config = {"fps": 30, "resolution_x": 1280, "resolution_y": 720}
        setup = BlenderProjectSetup(config)

        # Mock error
        mock_bpy.ops.wm.read_factory_settings.side_effect = Exception("Blender error")

        result = setup.setup_scene()

        assert result is False


class TestBlenderProjectSetupSequenceEditor:
    """Test sequence editor setup functionality."""

    @patch("core.blender_vse.project_setup.bpy")
    def test_setup_sequence_editor_creates_if_not_exists(self, mock_bpy):
        """Should create sequence editor if it doesn't exist."""
        config = {"fps": 30, "resolution_x": 1280, "resolution_y": 720}
        setup = BlenderProjectSetup(config)

        # Mock no existing sequence editor
        mock_scene = Mock()
        mock_scene.sequence_editor = None
        mock_bpy.context.scene = mock_scene

        result = setup.setup_sequence_editor()

        assert result is True
        mock_bpy.context.scene.sequence_editor_create.assert_called_once()

    @patch("core.blender_vse.project_setup.bpy")
    def test_setup_sequence_editor_uses_existing(self, mock_bpy):
        """Should use existing sequence editor if available."""
        config = {"fps": 30, "resolution_x": 1280, "resolution_y": 720}
        setup = BlenderProjectSetup(config)

        # Mock existing sequence editor
        mock_scene = Mock()
        mock_scene.sequence_editor = Mock()
        mock_bpy.context.scene = mock_scene

        result = setup.setup_sequence_editor()

        assert result is True
        # Should not call sequence_editor_create
        assert (
            not hasattr(mock_scene, "sequence_editor_create")
            or not mock_scene.sequence_editor_create.called
        )


class TestBlenderProjectSetupRenderSettings:
    """Test render settings configuration."""

    @patch("core.blender_vse.project_setup.bpy")
    def test_setup_render_settings_configures_mp4_h264(self, mock_bpy):
        """Should configure render settings for MP4/H.264 output."""
        config = {
            "fps": 30,
            "resolution_x": 1280,
            "resolution_y": 720,
            "render_output": Path("/path/to/render.mp4"),
        }
        setup = BlenderProjectSetup(config)

        # Mock render object
        mock_render = Mock()
        mock_render.image_settings = Mock()
        mock_render.ffmpeg = Mock()
        mock_scene = Mock()
        mock_scene.render = mock_render
        mock_bpy.context.scene = mock_scene

        result = setup.setup_render_settings()

        assert result is True
        assert mock_render.image_settings.file_format == "FFMPEG"
        assert mock_render.ffmpeg.format == "MPEG4"
        assert mock_render.ffmpeg.codec == "H264"
        assert mock_render.ffmpeg.constant_rate_factor == "HIGH"
        assert mock_render.filepath == "/path/to/render.mp4"

    @patch("core.blender_vse.project_setup.bpy")
    def test_setup_render_settings_handles_no_render_output(self, mock_bpy):
        """Should handle missing render output path gracefully."""
        config = {
            "fps": 30,
            "resolution_x": 1280,
            "resolution_y": 720,
            "render_output": None,
        }
        setup = BlenderProjectSetup(config)

        # Mock render object
        mock_render = Mock()
        mock_render.image_settings = Mock()
        mock_render.ffmpeg = Mock()
        mock_scene = Mock()
        mock_scene.render = mock_render
        mock_bpy.context.scene = mock_scene

        result = setup.setup_render_settings()

        assert result is True
        # Should still configure format settings but not filepath
        assert mock_render.image_settings.file_format == "FFMPEG"
        assert (
            not hasattr(mock_render, "filepath")
            or mock_render.filepath != "/path/to/render.mp4"
        )


class TestBlenderProjectSetupAudioVideo:
    """Test audio and video strip addition."""

    @patch("core.blender_vse.project_setup.bpy")
    def test_add_main_audio_creates_audio_strip(self, mock_bpy):
        """Should add main audio file to channel 1."""
        config = {
            "fps": 30,
            "resolution_x": 1280,
            "resolution_y": 720,
            "main_audio": Path("/path/to/audio.m4a"),
        }
        setup = BlenderProjectSetup(config)

        # Mock sequence editor
        mock_sequencer = Mock()
        mock_sequencer.sequences = Mock()
        mock_scene = Mock()
        mock_scene.sequence_editor = mock_sequencer
        mock_bpy.context.scene = mock_scene

        result = setup.add_main_audio()

        assert result is True
        mock_sequencer.sequences.new_sound.assert_called_once_with(
            name="Main_Audio", filepath="/path/to/audio.m4a", channel=1, frame_start=1
        )

    @patch("core.blender_vse.project_setup.bpy")
    def test_add_main_audio_handles_no_audio(self, mock_bpy):
        """Should handle missing main audio gracefully."""
        config = {
            "fps": 30,
            "resolution_x": 1280,
            "resolution_y": 720,
            "main_audio": None,
        }
        setup = BlenderProjectSetup(config)

        result = setup.add_main_audio()

        assert result is True  # Should succeed even without audio

    @patch("core.blender_vse.project_setup.bpy")
    def test_add_video_strips_creates_video_strips(self, mock_bpy):
        """Should add video files to channels starting from 2."""
        config = {
            "fps": 30,
            "resolution_x": 1280,
            "resolution_y": 720,
            "video_files": [Path("/path/video1.mp4"), Path("/path/video2.mp4")],
        }
        setup = BlenderProjectSetup(config)

        # Mock sequence editor
        mock_sequencer = Mock()
        mock_sequencer.sequences = Mock()
        mock_scene = Mock()
        mock_scene.sequence_editor = mock_sequencer
        mock_bpy.context.scene = mock_scene

        result = setup.add_video_strips()

        assert result is True

        # Should call new_movie for each video file with correct parameters
        # First video file
        mock_sequencer.sequences.new_movie.assert_any_call(
            name="Video_1",
            filepath="/path/video1.mp4",
            channel=2,
            frame_start=1,
        )
        # Second video file
        mock_sequencer.sequences.new_movie.assert_any_call(
            name="Video_2",
            filepath="/path/video2.mp4",
            channel=3,
            frame_start=1,
        )

        actual_calls = mock_sequencer.sequences.new_movie.call_args_list
        assert len(actual_calls) == 2

    @patch("core.blender_vse.project_setup.bpy")
    def test_add_video_strips_handles_errors(self, mock_bpy):
        """Should handle video file loading errors."""
        config = {
            "fps": 30,
            "resolution_x": 1280,
            "resolution_y": 720,
            "video_files": [Path("/invalid/video.mp4")],
        }
        setup = BlenderProjectSetup(config)

        # Mock sequence editor with error
        mock_sequencer = Mock()
        mock_sequencer.sequences = Mock()
        mock_sequencer.sequences.new_movie.side_effect = Exception("File not found")
        mock_scene = Mock()
        mock_scene.sequence_editor = mock_sequencer
        mock_bpy.context.scene = mock_scene

        result = setup.add_video_strips()

        assert result is False


class TestBlenderProjectSetupTimeline:
    """Test timeline configuration."""

    @patch("core.blender_vse.project_setup.bpy")
    def test_calculate_timeline_length_finds_longest_sequence(self, mock_bpy):
        """Should set timeline end to longest sequence."""
        config = {"fps": 30, "resolution_x": 1280, "resolution_y": 720}
        setup = BlenderProjectSetup(config)

        # Mock sequences with different lengths
        mock_seq1 = Mock()
        mock_seq1.frame_final_end = 300
        mock_seq2 = Mock()
        mock_seq2.frame_final_end = 450
        mock_seq3 = Mock()
        mock_seq3.frame_final_end = 200

        mock_sequencer = Mock()
        mock_sequencer.sequences = [mock_seq1, mock_seq2, mock_seq3]
        mock_scene = Mock()
        mock_scene.sequence_editor = mock_sequencer
        mock_bpy.context.scene = mock_scene

        result = setup.calculate_timeline_length()

        assert result is True
        assert mock_scene.frame_end == 450  # Longest sequence

    @patch("core.blender_vse.project_setup.bpy")
    def test_calculate_timeline_length_handles_no_sequences(self, mock_bpy):
        """Should handle empty sequence list gracefully."""
        config = {"fps": 30, "resolution_x": 1280, "resolution_y": 720}
        setup = BlenderProjectSetup(config)

        # Mock empty sequences
        mock_sequencer = Mock()
        mock_sequencer.sequences = []
        mock_scene = Mock()
        mock_scene.sequence_editor = mock_sequencer
        mock_bpy.context.scene = mock_scene

        result = setup.calculate_timeline_length()

        assert result is True  # Should succeed even with no sequences


class TestBlenderProjectSetupSaveProject:
    """Test project saving functionality."""

    @patch("core.blender_vse.project_setup.bpy")
    def test_save_project_creates_directory_and_saves(self, mock_bpy):
        """Should create directory and save project file."""
        config = {
            "fps": 30,
            "resolution_x": 1280,
            "resolution_y": 720,
            "output_blend": Path("/path/to/project.blend"),
        }
        setup = BlenderProjectSetup(config)

        # Mock Path operations
        with (
            patch("pathlib.Path.mkdir") as mock_mkdir,
            patch("pathlib.Path.exists", return_value=True),
        ):
            result = setup.save_project()

            assert result is True
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
            mock_bpy.ops.wm.save_as_mainfile.assert_called_once_with(
                filepath="/path/to/project.blend"
            )

    @patch("core.blender_vse.project_setup.bpy")
    def test_save_project_handles_no_output_path(self, mock_bpy):
        """Should handle missing output path gracefully."""
        config = {
            "fps": 30,
            "resolution_x": 1280,
            "resolution_y": 720,
            "output_blend": None,
        }
        setup = BlenderProjectSetup(config)

        result = setup.save_project()

        assert result is True  # Should succeed even without output path
        # Should not call save operation
        assert not mock_bpy.ops.wm.save_as_mainfile.called

    @patch("core.blender_vse.project_setup.bpy")
    def test_save_project_handles_save_errors(self, mock_bpy):
        """Should handle Blender save errors gracefully."""
        config = {
            "fps": 30,
            "resolution_x": 1280,
            "resolution_y": 720,
            "output_blend": Path("/path/to/project.blend"),
        }
        setup = BlenderProjectSetup(config)

        # Mock save error
        mock_bpy.ops.wm.save_as_mainfile.side_effect = Exception("Save failed")

        with (
            patch("pathlib.Path.mkdir"),
            patch("pathlib.Path.exists", return_value=False),
        ):
            result = setup.save_project()

            assert result is False


class TestBlenderProjectSetupIntegration:
    """Test integrated project setup functionality."""

    @patch("core.blender_vse.project_setup.bpy")
    def test_setup_project_runs_all_steps(self, mock_bpy):
        """Should run all setup steps in correct order."""
        config = {
            "fps": 30,
            "resolution_x": 1280,
            "resolution_y": 720,
            "video_files": [Path("video1.mp4")],
            "main_audio": Path("audio.m4a"),
            "output_blend": Path("project.blend"),
            "render_output": Path("render.mp4"),
        }
        setup = BlenderProjectSetup(config)

        # Mock all Blender operations
        mock_scene = Mock()
        mock_scene.render = Mock()
        mock_scene.render.ffmpeg = Mock()
        mock_scene.render.image_settings = Mock()

        # Mock sequencer with proper sequences
        mock_sequencer = Mock()
        mock_seq = Mock()
        mock_seq.frame_final_end = 300
        # Create a mock sequences object that has both list behavior and methods
        mock_sequences = Mock()
        mock_sequences.__iter__ = Mock(return_value=iter([mock_seq]))
        mock_sequences.new_sound = Mock()
        mock_sequences.new_movie = Mock()
        mock_sequencer.sequences = mock_sequences
        mock_scene.sequence_editor = mock_sequencer
        mock_bpy.context.scene = mock_scene

        with (
            patch("pathlib.Path.mkdir"),
            patch("pathlib.Path.exists", return_value=True),
        ):
            result = setup.setup_project()

            assert result is True

            # Verify key setup operations were called
            mock_bpy.ops.wm.read_factory_settings.assert_called_once()
            mock_bpy.ops.wm.save_as_mainfile.assert_called()

    @patch("core.blender_vse.project_setup.bpy")
    def test_setup_project_handles_step_failures(self, mock_bpy):
        """Should handle individual step failures gracefully."""
        config = {
            "fps": 30,
            "resolution_x": 1280,
            "resolution_y": 720,
            "video_files": [Path("video1.mp4")],
            "main_audio": Path("audio.m4a"),
        }
        setup = BlenderProjectSetup(config)

        # Mock scene setup failure
        mock_bpy.ops.wm.read_factory_settings.side_effect = Exception("Setup failed")

        result = setup.setup_project()

        assert result is False


class TestBlenderProjectSetupCompatibility:
    """Test compatibility with BlenderVSEConfigurator interface."""

    def test_setup_project_return_type_compatibility(self):
        """Should return boolean like original setup_vse_project method."""
        config = {"fps": 30, "resolution_x": 1280, "resolution_y": 720}
        setup = BlenderProjectSetup(config)

        with patch("core.blender_vse.project_setup.bpy"):
            result = setup.setup_project()
            assert isinstance(result, bool)

    def test_setup_project_accepts_vse_configurator_config(self):
        """Should accept config format used by BlenderVSEConfigurator."""
        # Config format as used in BlenderVSEConfigurator
        vse_config = {
            "fps": 30,
            "resolution_x": 1280,
            "resolution_y": 720,
            "video_files": [],
            "main_audio": None,
            "output_blend": None,
            "render_output": None,
        }

        # Should not raise exception
        setup = BlenderProjectSetup(vse_config)
        assert setup is not None
