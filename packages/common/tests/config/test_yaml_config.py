"""Tests for YAML configuration classes."""

from dataclasses import asdict

from setka_common.config.yaml_config import (
    ProjectConfig,
    AudioAnalysisConfig,
    LayoutConfig,
    BlenderYAMLConfig,
)


class TestProjectConfig:
    """Test cases for ProjectConfig dataclass."""

    def test_project_config_creation_with_defaults(self):
        """Test creating ProjectConfig with minimal required fields."""
        video_files = ["camera1.mp4", "camera2.mp4"]
        config = ProjectConfig(video_files=video_files)

        assert config.video_files == video_files
        assert config.main_audio is None
        assert config.output_blend is None
        assert config.render_output is None
        assert config.fps == 30
        assert config.resolution is None
        assert config.beat_division == 8

    def test_project_config_creation_with_all_fields(self):
        """Test creating ProjectConfig with all fields specified."""
        video_files = ["camera1.mp4", "camera2.mp4"]
        main_audio = "main_audio.m4a"
        output_blend = "blender/project.blend"
        render_output = "blender/render/output.mp4"
        fps = 60
        resolution = {"width": 1920, "height": 1080}
        beat_division = 16

        config = ProjectConfig(
            video_files=video_files,
            main_audio=main_audio,
            output_blend=output_blend,
            render_output=render_output,
            fps=fps,
            resolution=resolution,
            beat_division=beat_division,
        )

        assert config.video_files == video_files
        assert config.main_audio == main_audio
        assert config.output_blend == output_blend
        assert config.render_output == render_output
        assert config.fps == fps
        assert config.resolution == resolution
        assert config.beat_division == beat_division

    def test_project_config_empty_video_files(self):
        """Test creating ProjectConfig with empty video files list."""
        config = ProjectConfig(video_files=[])
        assert config.video_files == []

    def test_project_config_dataclass_conversion(self):
        """Test that ProjectConfig can be converted to dict."""
        video_files = ["test.mp4"]
        config = ProjectConfig(video_files=video_files)

        result = asdict(config)

        assert isinstance(result, dict)
        assert result["video_files"] == video_files
        assert result["main_audio"] is None
        assert result["fps"] == 30


class TestAudioAnalysisConfig:
    """Test cases for AudioAnalysisConfig dataclass."""

    def test_audio_analysis_config_creation_with_defaults(self):
        """Test creating AudioAnalysisConfig with default values."""
        config = AudioAnalysisConfig()

        assert config.file is None
        assert config.data is None

    def test_audio_analysis_config_creation_with_file(self):
        """Test creating AudioAnalysisConfig with file path."""
        file_path = "analysis/audio_analysis.json"
        config = AudioAnalysisConfig(file=file_path)

        assert config.file == file_path
        assert config.data is None

    def test_audio_analysis_config_creation_with_data(self):
        """Test creating AudioAnalysisConfig with inline data."""
        data = {"beats": [1.0, 2.0, 3.0], "energy_peaks": [1.5, 2.5]}
        config = AudioAnalysisConfig(data=data)

        assert config.file is None
        assert config.data == data

    def test_audio_analysis_config_creation_with_both(self):
        """Test creating AudioAnalysisConfig with both file and data."""
        file_path = "analysis/audio_analysis.json"
        data = {"beats": [1.0, 2.0]}
        config = AudioAnalysisConfig(file=file_path, data=data)

        assert config.file == file_path
        assert config.data == data


class TestLayoutConfig:
    """Test cases for LayoutConfig dataclass."""

    def test_layout_config_creation_with_defaults(self):
        """Test creating LayoutConfig with default values."""
        config = LayoutConfig()

        assert config.type == "random"
        assert config.config is None

    def test_layout_config_creation_with_type(self):
        """Test creating LayoutConfig with specific type."""
        config = LayoutConfig(type="grid")

        assert config.type == "grid"
        assert config.config is None

    def test_layout_config_creation_with_config(self):
        """Test creating LayoutConfig with configuration."""
        layout_config = {"overlap_allowed": False, "seed": 42, "margin": 0.05}
        config = LayoutConfig(type="random", config=layout_config)

        assert config.type == "random"
        assert config.config == layout_config

    def test_layout_config_grid_configuration(self):
        """Test creating LayoutConfig for grid layout."""
        layout_config = {"rows": 2, "cols": 2, "spacing": 0.1}
        config = LayoutConfig(type="grid", config=layout_config)

        assert config.type == "grid"
        assert config.config["rows"] == 2
        assert config.config["cols"] == 2
        assert config.config["spacing"] == 0.1


class TestBlenderYAMLConfig:
    """Test cases for BlenderYAMLConfig dataclass."""

    def test_blender_yaml_config_creation_minimal(self):
        """Test creating BlenderYAMLConfig with minimal configuration."""
        project = ProjectConfig(video_files=["test.mp4"])
        audio_analysis = AudioAnalysisConfig()
        layout = LayoutConfig()
        strip_animations = {}

        config = BlenderYAMLConfig(
            project=project,
            audio_analysis=audio_analysis,
            layout=layout,
            strip_animations=strip_animations,
        )

        assert config.project == project
        assert config.audio_analysis == audio_analysis
        assert config.layout == layout
        assert config.strip_animations == strip_animations

    def test_blender_yaml_config_creation_complete(self):
        """Test creating BlenderYAMLConfig with complete configuration."""
        project = ProjectConfig(
            video_files=["camera1.mp4", "camera2.mp4"],
            main_audio="main_audio.m4a",
            output_blend="blender/project.blend",
            render_output="blender/render/output.mp4",
            fps=30,
            resolution={"width": 1920, "height": 1080},
            beat_division=8,
        )

        audio_analysis = AudioAnalysisConfig(file="analysis/audio_analysis.json")

        layout = LayoutConfig(
            type="random", config={"overlap_allowed": False, "seed": 42, "margin": 0.05}
        )

        strip_animations = {
            "camera1": [
                {
                    "type": "scale",
                    "trigger": "bass",
                    "intensity": 0.3,
                    "duration_frames": 2,
                }
            ],
            "camera2": [
                {
                    "type": "shake",
                    "trigger": "beat",
                    "intensity": 5.0,
                    "return_frames": 2,
                }
            ],
        }

        config = BlenderYAMLConfig(
            project=project,
            audio_analysis=audio_analysis,
            layout=layout,
            strip_animations=strip_animations,
        )

        assert config.project.video_files == ["camera1.mp4", "camera2.mp4"]
        assert config.project.main_audio == "main_audio.m4a"
        assert config.audio_analysis.file == "analysis/audio_analysis.json"
        assert config.layout.type == "random"
        assert config.layout.config["overlap_allowed"] is False
        assert len(config.strip_animations) == 2
        assert config.strip_animations["camera1"][0]["type"] == "scale"
        assert config.strip_animations["camera2"][0]["type"] == "shake"

    def test_blender_yaml_config_dataclass_conversion(self):
        """Test that BlenderYAMLConfig can be converted to dict."""
        project = ProjectConfig(video_files=["test.mp4"])
        audio_analysis = AudioAnalysisConfig()
        layout = LayoutConfig()
        strip_animations = {}

        config = BlenderYAMLConfig(
            project=project,
            audio_analysis=audio_analysis,
            layout=layout,
            strip_animations=strip_animations,
        )

        result = asdict(config)

        assert isinstance(result, dict)
        assert "project" in result
        assert "audio_analysis" in result
        assert "layout" in result
        assert "strip_animations" in result
        assert result["project"]["video_files"] == ["test.mp4"]
