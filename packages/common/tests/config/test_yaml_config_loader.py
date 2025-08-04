"""Tests for YAMLConfigLoader class."""

import pytest
import tempfile
from pathlib import Path

from setka_common.config.yaml_config import (
    YAMLConfigLoader,
    BlenderYAMLConfig,
    ProjectConfig,
    AudioAnalysisConfig,
    LayoutConfig,
    ConfigValidationError,
)


class TestYAMLConfigLoader:
    """Test cases for YAMLConfigLoader class."""

    def test_load_config_basic_yaml(self):
        """Test loading a basic YAML configuration."""
        yaml_content = """
project:
  video_files: [camera1.mp4, camera2.mp4]
  main_audio: main_audio.m4a
  fps: 30
  resolution:
    width: 1920
    height: 1080
  beat_division: 8

audio_analysis:
  file: analysis/audio_analysis.json

layout:
  type: random
  config:
    overlap_allowed: false
    seed: 42
    margin: 0.05

strip_animations:
  camera1:
    - type: scale
      trigger: bass
      intensity: 0.3
      duration_frames: 2
  camera2:
    - type: shake
      trigger: beat
      intensity: 5.0
      return_frames: 2
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()

            loader = YAMLConfigLoader()
            config = loader.load_config(Path(f.name))

            assert isinstance(config, BlenderYAMLConfig)
            assert config.project.video_files == ["camera1.mp4", "camera2.mp4"]
            assert config.project.main_audio == "main_audio.m4a"
            assert config.project.fps == 30
            assert config.project.resolution.width == 1920
            assert config.project.resolution.height == 1080
            assert config.project.beat_division == 8

            assert config.audio_analysis.file == "analysis/audio_analysis.json"
            assert config.audio_analysis.data is None

            assert config.layout.type == "random"
            assert config.layout.config["overlap_allowed"] is False
            assert config.layout.config["seed"] == 42
            assert config.layout.config["margin"] == 0.05

            assert len(config.strip_animations) == 2
            assert config.strip_animations["camera1"][0]["type"] == "scale"
            assert config.strip_animations["camera1"][0]["trigger"] == "bass"
            assert config.strip_animations["camera1"][0]["intensity"] == 0.3
            assert config.strip_animations["camera1"][0]["duration_frames"] == 2

            assert config.strip_animations["camera2"][0]["type"] == "shake"
            assert config.strip_animations["camera2"][0]["trigger"] == "beat"
            assert config.strip_animations["camera2"][0]["intensity"] == 5.0
            assert config.strip_animations["camera2"][0]["return_frames"] == 2

            # Cleanup
            Path(f.name).unlink()

    def test_load_config_minimal_yaml(self):
        """Test loading a minimal YAML configuration."""
        yaml_content = """
project:
  video_files: [test.mp4]

audio_analysis: {}

layout:
  type: random

strip_animations: {}
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()

            loader = YAMLConfigLoader()
            config = loader.load_config(Path(f.name))

            assert isinstance(config, BlenderYAMLConfig)
            assert config.project.video_files == ["test.mp4"]
            assert config.project.main_audio is None
            assert config.project.fps == 30  # default
            assert config.project.beat_division == 8  # default

            assert config.audio_analysis.file is None
            assert config.audio_analysis.data is None

            assert config.layout.type == "random"
            assert config.layout.config is None

            assert len(config.strip_animations) == 0

            # Cleanup
            Path(f.name).unlink()

    def test_load_config_file_not_found(self):
        """Test loading config from non-existent file."""
        loader = YAMLConfigLoader()

        with pytest.raises(FileNotFoundError):
            loader.load_config(Path("nonexistent.yaml"))

    def test_load_config_invalid_yaml(self):
        """Test loading invalid YAML content."""
        yaml_content = """
project:
  video_files: [test.mp4
  # Invalid YAML - missing closing bracket
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()

            loader = YAMLConfigLoader()

            with pytest.raises(Exception):  # Should raise YAML parsing error
                loader.load_config(Path(f.name))

            # Cleanup
            Path(f.name).unlink()

    def test_load_config_missing_required_section(self):
        """Test loading YAML with missing required section."""
        yaml_content = """
audio_analysis: {}
layout: {}
strip_animations: {}
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()

            loader = YAMLConfigLoader()

            with pytest.raises(
                Exception
            ):  # Should raise validation error for missing project
                loader.load_config(Path(f.name))

            # Cleanup
            Path(f.name).unlink()

    def test_validate_config_valid(self):
        """Test validating a valid configuration."""
        project = ProjectConfig(video_files=["test.mp4"])
        audio_analysis = AudioAnalysisConfig(file="analysis.json")
        layout = LayoutConfig(type="random")
        strip_animations = {"test": [{"type": "scale", "trigger": "bass"}]}

        config = BlenderYAMLConfig(
            project=project,
            audio_analysis=audio_analysis,
            layout=layout,
            strip_animations=strip_animations,
        )

        loader = YAMLConfigLoader()
        is_valid, errors = loader.validate_config(config)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_config_empty_video_files(self):
        """Test validating config with empty video files (now allowed for auto-discovery)."""
        project = ProjectConfig(video_files=[])
        audio_analysis = AudioAnalysisConfig()
        layout = LayoutConfig()
        strip_animations = {}

        config = BlenderYAMLConfig(
            project=project,
            audio_analysis=audio_analysis,
            layout=layout,
            strip_animations=strip_animations,
        )

        loader = YAMLConfigLoader()
        is_valid, errors = loader.validate_config(config)

        # Empty video_files are now allowed for auto-discovery
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_config_invalid_fps(self):
        """Test validating config with invalid FPS."""
        project = ProjectConfig(video_files=["test.mp4"], fps=0)
        audio_analysis = AudioAnalysisConfig()
        layout = LayoutConfig()
        strip_animations = {}

        config = BlenderYAMLConfig(
            project=project,
            audio_analysis=audio_analysis,
            layout=layout,
            strip_animations=strip_animations,
        )

        loader = YAMLConfigLoader()
        is_valid, errors = loader.validate_config(config)

        assert is_valid is False
        assert len(errors) > 0
        assert any("fps" in error.lower() for error in errors)

    def test_validate_config_invalid_resolution(self):
        """Test validating config with invalid resolution."""
        project = ProjectConfig(
            video_files=["test.mp4"], resolution={"width": 0, "height": 1080}
        )
        audio_analysis = AudioAnalysisConfig()
        layout = LayoutConfig()
        strip_animations = {}

        config = BlenderYAMLConfig(
            project=project,
            audio_analysis=audio_analysis,
            layout=layout,
            strip_animations=strip_animations,
        )

        loader = YAMLConfigLoader()
        is_valid, errors = loader.validate_config(config)

        assert is_valid is False
        assert len(errors) > 0
        assert any("resolution" in error.lower() for error in errors)

    def test_validate_config_invalid_animation_type(self):
        """Test validating config with invalid animation type."""
        project = ProjectConfig(video_files=["test.mp4"])
        audio_analysis = AudioAnalysisConfig()
        layout = LayoutConfig()
        strip_animations = {"test": [{"type": "invalid_type", "trigger": "bass"}]}

        config = BlenderYAMLConfig(
            project=project,
            audio_analysis=audio_analysis,
            layout=layout,
            strip_animations=strip_animations,
        )

        loader = YAMLConfigLoader()
        is_valid, errors = loader.validate_config(config)

        assert is_valid is False
        assert len(errors) > 0
        assert any("animation" in error.lower() for error in errors)

    def test_resolve_paths_disabled(self):
        """Test loading config with resolve_paths=False (presets mode)."""
        yaml_content = """
project:
  video_files: [camera1.mp4, camera2.mp4]
  main_audio: main_audio.m4a
  
audio_analysis:
  file: analysis/audio_analysis.json

layout:
  type: random

strip_animations: {}
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()

            # Loader with resolve_paths=False (preset mode)
            loader = YAMLConfigLoader(resolve_paths=False)
            config = loader.load_config(Path(f.name))

            # Paths should remain as relative paths (not resolved)
            assert config.project.video_files == ["camera1.mp4", "camera2.mp4"]
            assert config.project.main_audio == "main_audio.m4a"
            assert config.audio_analysis.file == "analysis/audio_analysis.json"

            # Cleanup
            Path(f.name).unlink()

    def test_resolve_paths_enabled_with_base_directory(self):
        """Test loading config with resolve_paths=True and base_directory."""
        # Create temporary test directory structure
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            extracted_dir = base_path / "extracted"
            analysis_dir = base_path / "analysis"
            
            extracted_dir.mkdir()
            analysis_dir.mkdir()
            
            # Create test files
            (extracted_dir / "camera1.mp4").touch()
            (extracted_dir / "main_audio.m4a").touch()
            (analysis_dir / "audio_analysis.json").touch()

            yaml_content = f"""
project:
  base_directory: {base_path}
  video_files: [camera1.mp4, camera2.mp4]
  main_audio: main_audio.m4a
  
audio_analysis:
  file: analysis/audio_analysis.json

layout:
  type: random

strip_animations: {{}}
"""

            with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                f.write(yaml_content)
                f.flush()

                # Loader with resolve_paths=True (default)
                loader = YAMLConfigLoader(resolve_paths=True)
                config = loader.load_config(Path(f.name))

                # Paths should be resolved to absolute paths
                assert config.project.base_directory == str(base_path)
                assert config.project.video_files == [
                    str(extracted_dir / "camera1.mp4"),
                    str(extracted_dir / "camera2.mp4")
                ]
                assert config.project.main_audio == str(extracted_dir / "main_audio.m4a")
                assert config.audio_analysis.file == str(analysis_dir / "audio_analysis.json")

                # Cleanup
                Path(f.name).unlink()

    def test_resolve_paths_enabled_without_base_directory(self):
        """Test loading config with resolve_paths=True but no base_directory."""
        yaml_content = """
project:
  video_files: [camera1.mp4, camera2.mp4]
  main_audio: main_audio.m4a
  
audio_analysis:
  file: analysis/audio_analysis.json

layout:
  type: random

strip_animations: {}
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()

            # Loader with resolve_paths=True but no base_directory in config
            loader = YAMLConfigLoader(resolve_paths=True)
            config = loader.load_config(Path(f.name))

            # Paths should remain relative (no resolution without base_directory)
            assert config.project.base_directory is None
            assert config.project.video_files == ["camera1.mp4", "camera2.mp4"]
            assert config.project.main_audio == "main_audio.m4a"
            assert config.audio_analysis.file == "analysis/audio_analysis.json"

            # Cleanup
            Path(f.name).unlink()

    def test_resolve_paths_with_absolute_paths(self):
        """Test that absolute paths are preserved during resolution."""
        # Create temporary test directory structure
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            extracted_dir = base_path / "extracted"
            analysis_dir = base_path / "analysis"
            
            extracted_dir.mkdir()
            analysis_dir.mkdir()
            
            # Create test files
            (extracted_dir / "camera1.mp4").touch()
            absolute_audio_path = "/tmp/absolute_audio.m4a"

            yaml_content = f"""
project:
  base_directory: {base_path}
  video_files: [camera1.mp4]
  main_audio: {absolute_audio_path}
  
audio_analysis:
  file: analysis/audio_analysis.json

layout:
  type: random

strip_animations: {{}}
"""

            with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                f.write(yaml_content)
                f.flush()

                # Loader with resolve_paths=True
                loader = YAMLConfigLoader(resolve_paths=True)
                config = loader.load_config(Path(f.name))

                # Relative paths should be resolved, absolute paths preserved
                assert config.project.video_files == [str(extracted_dir / "camera1.mp4")]
                assert config.project.main_audio == absolute_audio_path  # Preserved as absolute
                assert config.audio_analysis.file == str(analysis_dir / "audio_analysis.json")

                # Cleanup
                Path(f.name).unlink()

    def test_validate_for_blender_execution(self):
        """Test validation for Blender execution."""
        # Create temporary test directory
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            
            project = ProjectConfig(
                video_files=["camera1.mp4"],
                base_directory=str(base_path)
            )
            audio_analysis = AudioAnalysisConfig()
            layout = LayoutConfig()
            strip_animations = {}

            config = BlenderYAMLConfig(
                project=project,
                audio_analysis=audio_analysis,
                layout=layout,
                strip_animations=strip_animations,
            )

            loader = YAMLConfigLoader()
            
            # Should not raise exception for valid config
            loader._validate_for_blender_execution(config)

    def test_validate_for_blender_execution_missing_base_directory(self):
        """Test validation fails when base_directory is missing."""
        project = ProjectConfig(video_files=["camera1.mp4"])  # No base_directory
        audio_analysis = AudioAnalysisConfig()
        layout = LayoutConfig()
        strip_animations = {}

        config = BlenderYAMLConfig(
            project=project,
            audio_analysis=audio_analysis,
            layout=layout,
            strip_animations=strip_animations,
        )

        loader = YAMLConfigLoader()
        
        with pytest.raises(ConfigValidationError) as exc_info:
            loader._validate_for_blender_execution(config)
        assert "base_directory required" in str(exc_info.value)

    def test_validate_for_blender_execution_missing_video_files(self):
        """Test validation fails when video_files are missing."""
        # Create temporary test directory
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            
            project = ProjectConfig(
                video_files=[],  # Empty video files
                base_directory=str(base_path)
            )
            audio_analysis = AudioAnalysisConfig()
            layout = LayoutConfig()
            strip_animations = {}

            config = BlenderYAMLConfig(
                project=project,
                audio_analysis=audio_analysis,
                layout=layout,
                strip_animations=strip_animations,
            )

            loader = YAMLConfigLoader()
            
            with pytest.raises(ConfigValidationError) as exc_info:
                loader._validate_for_blender_execution(config)
            assert "video_files required" in str(exc_info.value)

    def test_validate_for_blender_execution_nonexistent_base_directory(self):
        """Test validation fails when base_directory doesn't exist."""
        project = ProjectConfig(
            video_files=["camera1.mp4"],
            base_directory="/nonexistent/path"
        )
        audio_analysis = AudioAnalysisConfig()
        layout = LayoutConfig()
        strip_animations = {}

        config = BlenderYAMLConfig(
            project=project,
            audio_analysis=audio_analysis,
            layout=layout,
            strip_animations=strip_animations,
        )

        loader = YAMLConfigLoader()
        
        with pytest.raises(ConfigValidationError) as exc_info:
            loader._validate_for_blender_execution(config)
        assert "Base directory does not exist" in str(exc_info.value)
