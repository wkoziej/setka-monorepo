# ABOUTME: Tests for CinemonConfigGenerator main configuration generation functionality
# ABOUTME: Tests preset generation, custom configuration generation, and validation

"""Tests for CinemonConfigGenerator class."""

from unittest.mock import MagicMock, patch

import pytest
import yaml

from blender.config.cinemon_config_generator import CinemonConfigGenerator
from blender.config.media_discovery import ValidationResult
from blender.config.preset_manager import PresetConfig


class TestCinemonConfigGeneratorPreset:
    """Test cases for CinemonConfigGenerator.generate_preset method."""

    def test_generate_preset_vintage_basic(self, tmp_path):
        """Test generating vintage preset with basic recording structure."""
        # Create test recording structure
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        # Create test media files
        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "Camera2.mp4").touch()
        (extracted_dir / "main_audio.m4a").touch()

        generator = CinemonConfigGenerator()
        config_path = generator.generate_preset(recording_dir, "vintage")

        # Verify config file was created
        assert config_path.exists()
        assert config_path.name == "animation_config_vintage.yaml"
        assert config_path.parent == recording_dir

        # Verify config content
        with config_path.open('r') as f:
            config_data = yaml.safe_load(f)

        assert config_data["project"]["main_audio"] == "main_audio.m4a"
        assert config_data["layout"]["type"] == "random"
        assert config_data["layout"]["config"]["seed"] == 1950
        assert len(config_data["animations"]) == 6  # Vintage has 6 animations

        # Check for vintage-specific animations
        animation_types = [anim["type"] for anim in config_data["animations"]]
        assert "shake" in animation_types
        assert "vintage_color" in animation_types
        assert "film_grain" in animation_types

    def test_generate_preset_music_video(self, tmp_path):
        """Test generating music-video preset."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "microphone.wav").touch()

        generator = CinemonConfigGenerator()
        config_path = generator.generate_preset(recording_dir, "music-video")

        assert config_path.exists()
        assert config_path.name == "animation_config_music-video.yaml"

        with config_path.open('r') as f:
            config_data = yaml.safe_load(f)

        assert config_data["project"]["main_audio"] == "microphone.wav"
        assert config_data["layout"]["config"]["margin"] == 0.05
        assert len(config_data["animations"]) == 3  # Music video has 3 animations

        animation_types = [anim["type"] for anim in config_data["animations"]]
        assert "scale" in animation_types
        assert "shake" in animation_types
        assert "rotation" in animation_types

    def test_generate_preset_with_overrides(self, tmp_path):
        """Test generating preset with parameter overrides."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "main_audio.m4a").touch()

        generator = CinemonConfigGenerator()
        config_path = generator.generate_preset(
            recording_dir,
            "vintage",
            seed=42,  # Override default seed of 1950
            main_audio="main_audio.m4a"  # Explicit main audio
        )

        with config_path.open('r') as f:
            config_data = yaml.safe_load(f)

        # Verify override was applied
        assert config_data["layout"]["config"]["seed"] == 42
        assert config_data["project"]["main_audio"] == "main_audio.m4a"

    def test_generate_preset_with_multiple_audio_files_no_main(self, tmp_path):
        """Test generating preset when multiple audio files exist but no main_audio."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "microphone.wav").touch()
        (extracted_dir / "desktop_audio.m4a").touch()
        (extracted_dir / "background_music.mp3").touch()

        generator = CinemonConfigGenerator()

        # Should raise error when multiple audio files and no main_audio specified
        with pytest.raises(ValueError, match="Multiple audio files found"):
            generator.generate_preset(recording_dir, "vintage")

    def test_generate_preset_with_explicit_main_audio(self, tmp_path):
        """Test generating preset with explicitly specified main audio."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "microphone.wav").touch()
        (extracted_dir / "desktop_audio.m4a").touch()

        generator = CinemonConfigGenerator()
        config_path = generator.generate_preset(
            recording_dir,
            "vintage",
            main_audio="microphone.wav"
        )

        with config_path.open('r') as f:
            config_data = yaml.safe_load(f)

        assert config_data["project"]["main_audio"] == "microphone.wav"

    def test_generate_preset_nonexistent_preset(self, tmp_path):
        """Test generating nonexistent preset raises error."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "main_audio.m4a").touch()

        generator = CinemonConfigGenerator()

        with pytest.raises(ValueError, match="Preset 'nonexistent' not found"):
            generator.generate_preset(recording_dir, "nonexistent")

    def test_generate_preset_invalid_recording_directory(self, tmp_path):
        """Test generating preset with invalid recording directory."""
        nonexistent_dir = tmp_path / "nonexistent"

        generator = CinemonConfigGenerator()

        with pytest.raises(FileNotFoundError):
            generator.generate_preset(nonexistent_dir, "vintage")

    def test_generate_preset_missing_video_files(self, tmp_path):
        """Test generating preset when no video files found."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        # Only audio files, no video
        (extracted_dir / "main_audio.m4a").touch()

        generator = CinemonConfigGenerator()

        with pytest.raises(ValueError, match="No video files found"):
            generator.generate_preset(recording_dir, "vintage")

    def test_generate_preset_missing_audio_files(self, tmp_path):
        """Test generating preset when no audio files found."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        # Only video files, no audio
        (extracted_dir / "Camera1.mp4").touch()

        generator = CinemonConfigGenerator()

        with pytest.raises(ValueError, match="No audio files found"):
            generator.generate_preset(recording_dir, "vintage")

    def test_generate_preset_output_file_naming(self, tmp_path):
        """Test that preset output files are named correctly."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "main_audio.m4a").touch()

        generator = CinemonConfigGenerator()

        # Test different preset names
        vintage_path = generator.generate_preset(recording_dir, "vintage")
        music_path = generator.generate_preset(recording_dir, "music-video")
        minimal_path = generator.generate_preset(recording_dir, "minimal")

        assert vintage_path.name == "animation_config_vintage.yaml"
        assert music_path.name == "animation_config_music-video.yaml"
        assert minimal_path.name == "animation_config_minimal.yaml"

    def test_generate_preset_overwrites_existing_file(self, tmp_path):
        """Test that generating preset overwrites existing config file."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "main_audio.m4a").touch()

        generator = CinemonConfigGenerator()

        # Generate first version
        config_path1 = generator.generate_preset(recording_dir, "vintage", seed=100)

        with config_path1.open('r') as f:
            config_data1 = yaml.safe_load(f)
        assert config_data1["layout"]["config"]["seed"] == 100

        # Generate second version with different parameters
        config_path2 = generator.generate_preset(recording_dir, "vintage", seed=200)

        # Should be same path
        assert config_path1 == config_path2

        # But different content
        with config_path2.open('r') as f:
            config_data2 = yaml.safe_load(f)
        assert config_data2["layout"]["config"]["seed"] == 200

    def test_generate_preset_with_polish_filenames(self, tmp_path):
        """Test generating preset with Polish character filenames."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        (extracted_dir / "Kamera główna.mp4").touch()
        (extracted_dir / "Przechwytywanie wejścia dźwięku.m4a").touch()

        generator = CinemonConfigGenerator()
        config_path = generator.generate_preset(recording_dir, "vintage")

        with config_path.open('r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)

        assert config_data["project"]["main_audio"] == "Przechwytywanie wejścia dźwięku.m4a"

    def test_generate_preset_uses_media_discovery(self, tmp_path):
        """Test that generate_preset properly uses MediaDiscovery."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "main_audio.m4a").touch()

        with patch('blender.config.cinemon_config_generator.MediaDiscovery') as mock_discovery_class:
            # Mock MediaDiscovery instance
            mock_discovery = MagicMock()
            mock_discovery.discover_video_files.return_value = ["Camera1.mp4"]
            mock_discovery.discover_audio_files.return_value = ["main_audio.m4a"]
            mock_discovery.detect_main_audio.return_value = "main_audio.m4a"
            mock_discovery.validate_structure.return_value = ValidationResult(
                is_valid=True,
                errors=[],
                has_video_files=True,
                has_audio_files=True,
                has_analysis_files=False
            )
            mock_discovery_class.return_value = mock_discovery

            generator = CinemonConfigGenerator()
            generator.generate_preset(recording_dir, "vintage")

            # Verify MediaDiscovery was used
            mock_discovery_class.assert_called_once_with(recording_dir)
            mock_discovery.validate_structure.assert_called_once()
            mock_discovery.detect_main_audio.assert_called_once()

    def test_generate_preset_uses_preset_manager(self, tmp_path):
        """Test that generate_preset properly uses PresetManager."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "main_audio.m4a").touch()

        with patch('blender.config.cinemon_config_generator.PresetManager') as mock_preset_class:
            # Mock PresetManager instance
            mock_preset_manager = MagicMock()
            mock_preset_config = PresetConfig(
                name="vintage",
                description="Test vintage",
                layout={"type": "random", "config": {"seed": 1950}},
                animations=[{"type": "scale", "trigger": "bass", "intensity": 0.3}]
            )
            mock_preset_manager.get_preset.return_value = mock_preset_config
            mock_preset_class.return_value = mock_preset_manager

            generator = CinemonConfigGenerator()
            generator.generate_preset(recording_dir, "vintage")

            # Verify PresetManager was used
            mock_preset_class.assert_called_once()
            mock_preset_manager.get_preset.assert_called_once_with("vintage")

    def test_generate_preset_yaml_output_format(self, tmp_path):
        """Test that generated YAML follows correct format."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "main_audio.m4a").touch()

        generator = CinemonConfigGenerator()
        config_path = generator.generate_preset(recording_dir, "vintage")

        with config_path.open('r') as f:
            config_data = yaml.safe_load(f)

        # Verify YAML structure follows setka-common format
        assert "project" in config_data
        assert "audio_analysis" in config_data
        assert "layout" in config_data
        assert "animations" in config_data

        # Verify project section
        assert "main_audio" in config_data["project"]
        assert "fps" in config_data["project"]
        assert "resolution" in config_data["project"]

        # Verify audio_analysis section
        assert "beat_division" in config_data["audio_analysis"]
        assert "min_onset_interval" in config_data["audio_analysis"]

        # Verify layout section
        assert "type" in config_data["layout"]
        assert "config" in config_data["layout"]

        # Verify animations section
        assert isinstance(config_data["animations"], list)
        for animation in config_data["animations"]:
            assert "type" in animation
            assert "trigger" in animation


class TestCinemonConfigGeneratorCustom:
    """Test cases for CinemonConfigGenerator.generate_config method."""

    def test_generate_config_basic(self, tmp_path):
        """Test generating custom configuration with basic parameters."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "Camera2.mp4").touch()
        (extracted_dir / "main_audio.m4a").touch()

        layout = {
            "type": "random",
            "config": {
                "overlap_allowed": False,
                "seed": 42,
                "margin": 0.05
            }
        }

        animations = [
            {
                "type": "scale",
                "trigger": "bass",
                "intensity": 0.3,
                "duration_frames": 2,
                "target_strips": ["Camera1"]
            },
            {
                "type": "shake",
                "trigger": "beat",
                "intensity": 5.0,
                "return_frames": 2,
                "target_strips": ["Camera2"]
            }
        ]

        generator = CinemonConfigGenerator()
        config_path = generator.generate_config(
            recording_dir,
            layout=layout,
            animations=animations
        )

        # Verify config file was created
        assert config_path.exists()
        assert config_path.name == "animation_config.yaml"
        assert config_path.parent == recording_dir

        # Verify config content
        with config_path.open('r') as f:
            config_data = yaml.safe_load(f)

        assert config_data["project"]["main_audio"] == "main_audio.m4a"
        assert config_data["layout"]["type"] == "random"
        assert config_data["layout"]["config"]["seed"] == 42
        assert len(config_data["animations"]) == 2

        # Check targeting
        scale_anim = next(anim for anim in config_data["animations"] if anim["type"] == "scale")
        assert scale_anim["target_strips"] == ["Camera1"]

    def test_generate_config_with_explicit_main_audio(self, tmp_path):
        """Test generating custom config with explicit main audio."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "microphone.wav").touch()
        (extracted_dir / "desktop_audio.m4a").touch()

        layout = {"type": "random", "config": {"seed": 100}}
        animations = [{"type": "scale", "trigger": "bass", "intensity": 0.2}]

        generator = CinemonConfigGenerator()
        config_path = generator.generate_config(
            recording_dir,
            layout=layout,
            animations=animations,
            main_audio="microphone.wav"
        )

        with config_path.open('r') as f:
            config_data = yaml.safe_load(f)

        assert config_data["project"]["main_audio"] == "microphone.wav"

    def test_generate_config_with_project_overrides(self, tmp_path):
        """Test generating custom config with project setting overrides."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "main_audio.m4a").touch()

        layout = {"type": "random", "config": {"seed": 42}}
        animations = [{"type": "scale", "trigger": "bass", "intensity": 0.3}]

        project_overrides = {
            "fps": 60,
            "resolution": {
                "width": 3840,
                "height": 2160
            }
        }

        generator = CinemonConfigGenerator()
        config_path = generator.generate_config(
            recording_dir,
            layout=layout,
            animations=animations,
            project_overrides=project_overrides
        )

        with config_path.open('r') as f:
            config_data = yaml.safe_load(f)

        assert config_data["project"]["fps"] == 60
        assert config_data["project"]["resolution"]["width"] == 3840
        assert config_data["project"]["resolution"]["height"] == 2160

    def test_generate_config_with_audio_analysis_params(self, tmp_path):
        """Test generating custom config with audio analysis parameters."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "main_audio.m4a").touch()

        layout = {"type": "random", "config": {"seed": 42}}
        animations = [{"type": "scale", "trigger": "bass", "intensity": 0.3}]

        generator = CinemonConfigGenerator()
        config_path = generator.generate_config(
            recording_dir,
            layout=layout,
            animations=animations,
            beat_division=8,
            min_onset_interval=1.5
        )

        with config_path.open('r') as f:
            config_data = yaml.safe_load(f)

        assert config_data["audio_analysis"]["beat_division"] == 8
        assert config_data["audio_analysis"]["min_onset_interval"] == 1.5

    def test_generate_config_complex_animations(self, tmp_path):
        """Test generating config with complex animation targeting."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "Camera2.mp4").touch()
        (extracted_dir / "Camera3.mp4").touch()
        (extracted_dir / "main_audio.m4a").touch()

        layout = {"type": "random", "config": {"overlap_allowed": True, "seed": 123}}

        animations = [
            {
                "type": "scale",
                "trigger": "bass",
                "intensity": 0.5,
                "duration_frames": 3,
                "target_strips": ["Camera1", "Camera2"]
            },
            {
                "type": "vintage_color",
                "trigger": "one_time",
                "sepia_amount": 0.4,
                "contrast_boost": 0.3,
                "target_strips": ["Camera3"]
            },
            {
                "type": "shake",
                "trigger": "beat",
                "intensity": 10.0,
                "return_frames": 2,
                "target_strips": []  # All strips
            }
        ]

        generator = CinemonConfigGenerator()
        config_path = generator.generate_config(
            recording_dir,
            layout=layout,
            animations=animations
        )

        with config_path.open('r') as f:
            config_data = yaml.safe_load(f)

        assert len(config_data["animations"]) == 3

        # Check targeting specificity
        scale_anim = next(anim for anim in config_data["animations"] if anim["type"] == "scale")
        vintage_anim = next(anim for anim in config_data["animations"] if anim["type"] == "vintage_color")
        shake_anim = next(anim for anim in config_data["animations"] if anim["type"] == "shake")

        assert scale_anim["target_strips"] == ["Camera1", "Camera2"]
        assert vintage_anim["target_strips"] == ["Camera3"]
        assert shake_anim["target_strips"] == []

    def test_generate_config_missing_required_parameters(self, tmp_path):
        """Test generating config with missing required parameters."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "main_audio.m4a").touch()

        generator = CinemonConfigGenerator()

        # Missing layout parameter
        with pytest.raises(TypeError):
            generator.generate_config(
                recording_dir,
                animations=[{"type": "scale", "trigger": "bass", "intensity": 0.3}]
            )

        # Missing animations parameter
        with pytest.raises(TypeError):
            generator.generate_config(
                recording_dir,
                layout={"type": "random", "config": {"seed": 42}}
            )

    def test_generate_config_multiple_audio_no_main_specified(self, tmp_path):
        """Test generating config when multiple audio files exist but no main specified."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "microphone.wav").touch()
        (extracted_dir / "desktop_audio.m4a").touch()

        layout = {"type": "random", "config": {"seed": 42}}
        animations = [{"type": "scale", "trigger": "bass", "intensity": 0.3}]

        generator = CinemonConfigGenerator()

        with pytest.raises(ValueError, match="Multiple audio files found"):
            generator.generate_config(recording_dir, layout=layout, animations=animations)

    def test_generate_config_invalid_directory(self, tmp_path):
        """Test generating config with invalid recording directory."""
        nonexistent_dir = tmp_path / "nonexistent"

        layout = {"type": "random", "config": {"seed": 42}}
        animations = [{"type": "scale", "trigger": "bass", "intensity": 0.3}]

        generator = CinemonConfigGenerator()

        with pytest.raises(FileNotFoundError):
            generator.generate_config(nonexistent_dir, layout=layout, animations=animations)

    def test_generate_config_overwrites_existing(self, tmp_path):
        """Test that generate_config overwrites existing config file."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "main_audio.m4a").touch()

        layout1 = {"type": "random", "config": {"seed": 100}}
        animations1 = [{"type": "scale", "trigger": "bass", "intensity": 0.2}]

        layout2 = {"type": "random", "config": {"seed": 200}}
        animations2 = [{"type": "shake", "trigger": "beat", "intensity": 5.0}]

        generator = CinemonConfigGenerator()

        # Generate first config
        config_path1 = generator.generate_config(recording_dir, layout=layout1, animations=animations1)

        with config_path1.open('r') as f:
            config_data1 = yaml.safe_load(f)
        assert config_data1["layout"]["config"]["seed"] == 100

        # Generate second config (should overwrite)
        config_path2 = generator.generate_config(recording_dir, layout=layout2, animations=animations2)

        assert config_path1 == config_path2  # Same path

        with config_path2.open('r') as f:
            config_data2 = yaml.safe_load(f)
        assert config_data2["layout"]["config"]["seed"] == 200
        assert config_data2["animations"][0]["type"] == "shake"

    def test_generate_config_empty_animations_list(self, tmp_path):
        """Test generating config with empty animations list."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "main_audio.m4a").touch()

        layout = {"type": "random", "config": {"seed": 42}}
        animations = []  # Empty list

        generator = CinemonConfigGenerator()
        config_path = generator.generate_config(
            recording_dir,
            layout=layout,
            animations=animations
        )

        with config_path.open('r') as f:
            config_data = yaml.safe_load(f)

        assert config_data["animations"] == []
        assert config_data["layout"]["type"] == "random"

    def test_generate_config_yaml_format_consistency(self, tmp_path):
        """Test that generate_config produces YAML consistent with generate_preset."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "main_audio.m4a").touch()

        layout = {"type": "random", "config": {"seed": 42}}
        animations = [{"type": "scale", "trigger": "bass", "intensity": 0.3}]

        generator = CinemonConfigGenerator()

        # Generate custom config
        custom_path = generator.generate_config(recording_dir, layout=layout, animations=animations)

        # Generate preset config for comparison
        preset_path = generator.generate_preset(recording_dir, "minimal")

        with custom_path.open('r') as f:
            custom_data = yaml.safe_load(f)

        with preset_path.open('r') as f:
            preset_data = yaml.safe_load(f)

        # Both should have same structure
        assert set(custom_data.keys()) == set(preset_data.keys())
        assert set(custom_data["project"].keys()) == set(preset_data["project"].keys())
        assert set(custom_data["audio_analysis"].keys()) == set(preset_data["audio_analysis"].keys())
        assert set(custom_data["layout"].keys()) == set(preset_data["layout"].keys())

    def test_generate_config_with_polish_filenames(self, tmp_path):
        """Test generating config with Polish character filenames."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        (extracted_dir / "Kamera główna.mp4").touch()
        (extracted_dir / "Przechwytywanie wejścia dźwięku.m4a").touch()

        layout = {"type": "random", "config": {"seed": 42}}
        animations = [{"type": "scale", "trigger": "bass", "intensity": 0.3}]

        generator = CinemonConfigGenerator()
        config_path = generator.generate_config(
            recording_dir,
            layout=layout,
            animations=animations
        )

        with config_path.open('r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)

        assert config_data["project"]["main_audio"] == "Przechwytywanie wejścia dźwięku.m4a"
