# ABOUTME: Tests for CinemonConfigGenerator main configuration generation functionality
# ABOUTME: Tests preset generation, custom configuration generation, and validation

"""Tests for CinemonConfigGenerator class."""

from unittest.mock import MagicMock, patch

import pytest
import yaml

from cinemon.config.cinemon_config_generator import CinemonConfigGenerator
from cinemon.config.media_discovery import ValidationResult
from setka_common.config.yaml_config import BlenderYAMLConfig


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
        assert config_data["layout"]["config"]["seed"] == 42  # From vintage.yaml
        assert "strip_animations" in config_data
        
        # Check for vintage-specific animations per strip
        assert "Camera1" in config_data["strip_animations"]
        camera1_anims = config_data["strip_animations"]["Camera1"]
        animation_types = [anim["type"] for anim in camera1_anims]
        assert "scale" in animation_types

    def test_generate_preset_music_video(self, tmp_path):
        """Test generating music-video preset."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "Camera2.mp4").touch()
        (extracted_dir / "microphone.wav").touch()

        generator = CinemonConfigGenerator()
        config_path = generator.generate_preset(
            recording_dir,
            "music-video",
            main_audio="microphone.wav"
        )

        with config_path.open('r') as f:
            config_data = yaml.safe_load(f)

        assert config_data["project"]["main_audio"] == "microphone.wav"
        assert config_data["layout"]["config"]["margin"] == 0.02
        assert "strip_animations" in config_data
        
        # Music video preset applies to specific strips
        assert "Camera1" in config_data["strip_animations"]
        camera1_anims = config_data["strip_animations"]["Camera1"]
        animation_types = [anim["type"] for anim in camera1_anims]
        assert "scale" in animation_types or "pip_switch" in animation_types

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
            seed=99,  # Override default seed
            main_audio="main_audio.m4a"  # Explicit main audio
        )

        with config_path.open('r') as f:
            config_data = yaml.safe_load(f)

        # Verify override was applied
        assert config_data["layout"]["config"]["seed"] == 99
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
            main_audio="desktop_audio.m4a"
        )

        with config_path.open('r') as f:
            config_data = yaml.safe_load(f)

        assert config_data["project"]["main_audio"] == "desktop_audio.m4a"

    def test_generate_preset_nonexistent_preset(self, tmp_path):
        """Test generating with nonexistent preset name."""
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

        with pytest.raises(FileNotFoundError, match="Recording directory not found"):
            generator.generate_preset(nonexistent_dir, "vintage")

    def test_generate_preset_missing_video_files(self, tmp_path):
        """Test generating preset when no video files exist."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        # Only audio file, no video
        (extracted_dir / "main_audio.m4a").touch()

        generator = CinemonConfigGenerator()

        with pytest.raises(ValueError, match="No video files found"):
            generator.generate_preset(recording_dir, "vintage")

    def test_generate_preset_missing_audio_files(self, tmp_path):
        """Test generating preset when no audio files exist."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        # Only video file, no audio
        (extracted_dir / "Camera1.mp4").touch()

        generator = CinemonConfigGenerator()

        with pytest.raises(ValueError, match="No audio files found"):
            generator.generate_preset(recording_dir, "vintage")

    def test_generate_preset_output_file_naming(self, tmp_path):
        """Test that output files are named correctly for different presets."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "main_audio.m4a").touch()

        generator = CinemonConfigGenerator()

        # Test different preset names
        vintage_path = generator.generate_preset(recording_dir, "vintage")
        assert vintage_path.name == "animation_config_vintage.yaml"

        music_video_path = generator.generate_preset(recording_dir, "music-video")
        assert music_video_path.name == "animation_config_music-video.yaml"

        minimal_path = generator.generate_preset(recording_dir, "minimal")
        assert minimal_path.name == "animation_config_minimal.yaml"

    def test_generate_preset_overwrites_existing_file(self, tmp_path):
        """Test that generate_preset overwrites existing config file."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "main_audio.m4a").touch()

        generator = CinemonConfigGenerator()

        # Generate first time
        config_path1 = generator.generate_preset(recording_dir, "vintage", seed=100)

        with config_path1.open('r') as f:
            config_data1 = yaml.safe_load(f)
        assert config_data1["layout"]["config"]["seed"] == 100

        # Generate second time with different seed
        config_path2 = generator.generate_preset(recording_dir, "vintage", seed=200)

        assert config_path1 == config_path2  # Same path

        with config_path2.open('r') as f:
            config_data2 = yaml.safe_load(f)
        assert config_data2["layout"]["config"]["seed"] == 200

    def test_generate_preset_with_polish_filenames(self, tmp_path):
        """Test generating preset with Polish character filenames."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        (extracted_dir / "Kamera główna.mp4").touch()
        (extracted_dir / "Kamera dodatkowa.mp4").touch()
        (extracted_dir / "Przechwytywanie wejścia dźwięku.m4a").touch()

        generator = CinemonConfigGenerator()
        config_path = generator.generate_preset(recording_dir, "vintage")

        with config_path.open('r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)

        assert config_data["project"]["main_audio"] == "Przechwytywanie wejścia dźwięku.m4a"
        assert "Kamera główna.mp4" in config_data["project"]["video_files"]
        assert "Kamera dodatkowa.mp4" in config_data["project"]["video_files"]

    def test_generate_preset_uses_media_discovery(self, tmp_path):
        """Test that generate_preset properly uses MediaDiscovery for file detection."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        # Create various file types
        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "Camera2.mp4").touch()
        (extracted_dir / "Screen.mkv").touch()  # Different video extension
        (extracted_dir / "main_audio.m4a").touch()
        (extracted_dir / "backup_audio.wav").touch()
        (extracted_dir / "thumbnail.jpg").touch()  # Should be ignored

        generator = CinemonConfigGenerator()

        # Should auto-detect main_audio since only one .m4a file
        config_path = generator.generate_preset(recording_dir, "vintage")

        with config_path.open('r') as f:
            config_data = yaml.safe_load(f)

        # Should include all video files
        assert len(config_data["project"]["video_files"]) == 3
        assert "Camera1.mp4" in config_data["project"]["video_files"]
        assert "Camera2.mp4" in config_data["project"]["video_files"]
        assert "Screen.mkv" in config_data["project"]["video_files"]

        # Should not include image files
        assert "thumbnail.jpg" not in config_data["project"]["video_files"]

        # Should auto-detect main audio
        assert config_data["project"]["main_audio"] == "main_audio.m4a"

    def test_generate_preset_uses_preset_manager(self):
        """Test that generate_preset properly uses PresetManager."""
        with patch('cinemon.config.cinemon_config_generator.PresetManager') as MockPresetManager:
            # Create test directory first
            import tempfile
            from pathlib import Path
            with tempfile.TemporaryDirectory() as tmp_dir:
                recording_dir = Path(tmp_dir) / "recording"
                extracted_dir = recording_dir / "extracted"
                extracted_dir.mkdir(parents=True)
                (extracted_dir / "Camera1.mp4").touch()
                (extracted_dir / "audio.m4a").touch()

                # Configure mock to return a known preset
                from cinemon.config.preset_manager import PresetManager
                mock_manager = MockPresetManager.return_value
                mock_manager.get_preset.side_effect = lambda name: (
                    PresetManager().get_preset("vintage") if name == "test-preset" else None
                )

                generator = CinemonConfigGenerator()
                generator.generate_preset(recording_dir, "test-preset")

                # Verify PresetManager was used correctly
                mock_manager.get_preset.assert_called_once_with("test-preset")

    def test_generate_preset_yaml_output_format(self, tmp_path):
        """Test that generated YAML follows expected structure."""
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
        assert "strip_animations" in config_data

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

        # Verify strip_animations section
        assert isinstance(config_data["strip_animations"], dict)
        for strip_name, animations in config_data["strip_animations"].items():
            assert isinstance(animations, list)
            for animation in animations:
                assert "type" in animation
                assert "trigger" in animation


# TestCinemonConfigGeneratorCustom removed - generate_config method was removed from API