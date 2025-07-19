"""Tests for YAMLConfigLoader class."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

from setka_common.config.yaml_config import (
    YAMLConfigLoader,
    BlenderYAMLConfig,
    ProjectConfig,
    AudioAnalysisConfig,
    LayoutConfig,
    AnimationSpec,
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

animations:
  - type: scale
    trigger: bass
    target_strips: [camera1]
    intensity: 0.3
    duration_frames: 2
  - type: shake
    trigger: beat
    target_strips: [camera2]
    intensity: 5.0
    return_frames: 2
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            
            loader = YAMLConfigLoader()
            config = loader.load_config(Path(f.name))
            
            assert isinstance(config, BlenderYAMLConfig)
            assert config.project.video_files == ["camera1.mp4", "camera2.mp4"]
            assert config.project.main_audio == "main_audio.m4a"
            assert config.project.fps == 30
            assert config.project.resolution == {"width": 1920, "height": 1080}
            assert config.project.beat_division == 8
            
            assert config.audio_analysis.file == "analysis/audio_analysis.json"
            assert config.audio_analysis.data is None
            
            assert config.layout.type == "random"
            assert config.layout.config["overlap_allowed"] is False
            assert config.layout.config["seed"] == 42
            assert config.layout.config["margin"] == 0.05
            
            assert len(config.animations) == 2
            assert config.animations[0].type == "scale"
            assert config.animations[0].trigger == "bass"
            assert config.animations[0].target_strips == ["camera1"]
            assert config.animations[0].intensity == 0.3
            assert config.animations[0].duration_frames == 2
            
            assert config.animations[1].type == "shake"
            assert config.animations[1].trigger == "beat"
            assert config.animations[1].target_strips == ["camera2"]
            assert config.animations[1].intensity == 5.0
            assert config.animations[1].return_frames == 2
            
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

animations: []
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
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
            
            assert len(config.animations) == 0
            
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
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            
            loader = YAMLConfigLoader()
            
            with pytest.raises(Exception):  # Should raise YAML parsing error
                loader.load_config(Path(f.name))
            
            # Cleanup
            Path(f.name).unlink()

    def test_load_config_missing_required_fields(self):
        """Test loading YAML with missing required fields."""
        yaml_content = """
project: {}
audio_analysis: {}
layout: {}
animations: []
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            
            loader = YAMLConfigLoader()
            
            with pytest.raises(Exception):  # Should raise validation error
                loader.load_config(Path(f.name))
            
            # Cleanup
            Path(f.name).unlink()

    def test_validate_config_valid(self):
        """Test validating a valid configuration."""
        project = ProjectConfig(video_files=["test.mp4"])
        audio_analysis = AudioAnalysisConfig(file="analysis.json")
        layout = LayoutConfig(type="random")
        animations = [
            AnimationSpec(type="scale", trigger="bass", target_strips=["test"])
        ]
        
        config = BlenderYAMLConfig(
            project=project,
            audio_analysis=audio_analysis,
            layout=layout,
            animations=animations
        )
        
        loader = YAMLConfigLoader()
        is_valid, errors = loader.validate_config(config)
        
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_config_empty_video_files(self):
        """Test validating config with empty video files."""
        project = ProjectConfig(video_files=[])
        audio_analysis = AudioAnalysisConfig()
        layout = LayoutConfig()
        animations = []
        
        config = BlenderYAMLConfig(
            project=project,
            audio_analysis=audio_analysis,
            layout=layout,
            animations=animations
        )
        
        loader = YAMLConfigLoader()
        is_valid, errors = loader.validate_config(config)
        
        assert is_valid is False
        assert len(errors) > 0
        assert any("video file" in error.lower() for error in errors)

    def test_validate_config_invalid_fps(self):
        """Test validating config with invalid FPS."""
        project = ProjectConfig(video_files=["test.mp4"], fps=0)
        audio_analysis = AudioAnalysisConfig()
        layout = LayoutConfig()
        animations = []
        
        config = BlenderYAMLConfig(
            project=project,
            audio_analysis=audio_analysis,
            layout=layout,
            animations=animations
        )
        
        loader = YAMLConfigLoader()
        is_valid, errors = loader.validate_config(config)
        
        assert is_valid is False
        assert len(errors) > 0
        assert any("fps" in error.lower() for error in errors)

    def test_validate_config_invalid_resolution(self):
        """Test validating config with invalid resolution."""
        project = ProjectConfig(
            video_files=["test.mp4"],
            resolution={"width": 0, "height": 1080}
        )
        audio_analysis = AudioAnalysisConfig()
        layout = LayoutConfig()
        animations = []
        
        config = BlenderYAMLConfig(
            project=project,
            audio_analysis=audio_analysis,
            layout=layout,
            animations=animations
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
        animations = [
            AnimationSpec(type="invalid_type", trigger="bass", target_strips=["test"])
        ]
        
        config = BlenderYAMLConfig(
            project=project,
            audio_analysis=audio_analysis,
            layout=layout,
            animations=animations
        )
        
        loader = YAMLConfigLoader()
        is_valid, errors = loader.validate_config(config)
        
        assert is_valid is False
        assert len(errors) > 0
        assert any("animation" in error.lower() for error in errors)

    def test_convert_to_env_vars_basic(self):
        """Test converting YAML config to environment variables."""
        project = ProjectConfig(
            video_files=["camera1.mp4", "camera2.mp4"],
            main_audio="main_audio.m4a",
            fps=30,
            resolution={"width": 1920, "height": 1080},
            beat_division=8
        )
        audio_analysis = AudioAnalysisConfig(file="analysis.json")
        layout = LayoutConfig(type="random")
        animations = []
        
        config = BlenderYAMLConfig(
            project=project,
            audio_analysis=audio_analysis,
            layout=layout,
            animations=animations
        )
        
        loader = YAMLConfigLoader()
        env_vars = loader.convert_to_env_vars(config)
        
        assert "BLENDER_VSE_VIDEO_FILES" in env_vars
        assert env_vars["BLENDER_VSE_VIDEO_FILES"] == "camera1.mp4,camera2.mp4"
        assert env_vars["BLENDER_VSE_MAIN_AUDIO"] == "main_audio.m4a"
        assert env_vars["BLENDER_VSE_FPS"] == "30"
        assert env_vars["BLENDER_VSE_RESOLUTION_X"] == "1920"
        assert env_vars["BLENDER_VSE_RESOLUTION_Y"] == "1080"
        assert env_vars["BLENDER_VSE_BEAT_DIVISION"] == "8"
        assert env_vars["BLENDER_VSE_AUDIO_ANALYSIS_FILE"] == "analysis.json"
        assert env_vars["BLENDER_VSE_LAYOUT_TYPE"] == "random"

    def test_convert_to_env_vars_with_animations(self):
        """Test converting YAML config with animations to environment variables."""
        project = ProjectConfig(video_files=["test.mp4"])
        audio_analysis = AudioAnalysisConfig()
        layout = LayoutConfig(
            type="random",
            config={"overlap_allowed": False, "seed": 42}
        )
        animations = [
            AnimationSpec(
                type="scale",
                trigger="bass",
                target_strips=["test"],
                intensity=0.3,
                duration_frames=2
            )
        ]
        
        config = BlenderYAMLConfig(
            project=project,
            audio_analysis=audio_analysis,
            layout=layout,
            animations=animations
        )
        
        loader = YAMLConfigLoader()
        env_vars = loader.convert_to_env_vars(config)
        
        assert "BLENDER_VSE_ANIMATION_MODE" in env_vars
        assert env_vars["BLENDER_VSE_ANIMATION_MODE"] == "compositional"
        assert "BLENDER_VSE_LAYOUT_CONFIG" in env_vars
        assert "overlap_allowed=false" in env_vars["BLENDER_VSE_LAYOUT_CONFIG"]
        assert "seed=42" in env_vars["BLENDER_VSE_LAYOUT_CONFIG"]

    def test_convert_to_env_vars_empty_animations(self):
        """Test converting YAML config with no animations."""
        project = ProjectConfig(video_files=["test.mp4"])
        audio_analysis = AudioAnalysisConfig()
        layout = LayoutConfig()
        animations = []
        
        config = BlenderYAMLConfig(
            project=project,
            audio_analysis=audio_analysis,
            layout=layout,
            animations=animations
        )
        
        loader = YAMLConfigLoader()
        env_vars = loader.convert_to_env_vars(config)
        
        assert env_vars["BLENDER_VSE_ANIMATION_MODE"] == "none"
        assert "BLENDER_VSE_ANIMATION_CONFIG" not in env_vars