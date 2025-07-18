# ABOUTME: Integration tests for complete CinemonConfigGenerator pipeline
# ABOUTME: Tests end-to-end functionality from file discovery to config generation

"""Integration tests for CinemonConfigGenerator pipeline."""

import pytest
import yaml
from pathlib import Path

from blender.config import CinemonConfigGenerator, MediaDiscovery, PresetManager


class TestPipelineIntegration:
    """Test complete pipeline integration for CinemonConfigGenerator."""

    def test_complete_preset_pipeline(self, tmp_path):
        """Test complete pipeline from recording directory to generated config."""
        # Setup test recording structure
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)
        
        # Create media files
        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "Camera2.mp4").touch()
        (extracted_dir / "Screen_Capture.mkv").touch()
        (extracted_dir / "main_audio.m4a").touch()
        (recording_dir / "metadata.json").write_text('{"recording_info": "test"}')
        
        # 1. Test MediaDiscovery
        discovery = MediaDiscovery(recording_dir)
        validation_result = discovery.validate_structure()
        
        assert validation_result.is_valid is True
        assert validation_result.has_video_files is True
        assert validation_result.has_audio_files is True
        
        video_files = discovery.discover_video_files()
        audio_files = discovery.discover_audio_files()
        main_audio = discovery.detect_main_audio()
        
        assert len(video_files) == 3
        assert "Camera1.mp4" in video_files
        assert "Camera2.mp4" in video_files
        assert "Screen_Capture.mkv" in video_files
        
        assert len(audio_files) == 1
        assert "main_audio.m4a" in audio_files
        assert main_audio == "main_audio.m4a"
        
        # 2. Test PresetManager
        preset_manager = PresetManager()
        vintage_preset = preset_manager.get_preset("vintage")
        
        assert vintage_preset.name == "vintage"
        assert len(vintage_preset.animations) == 6
        assert vintage_preset.layout["type"] == "random"
        
        # 3. Test CinemonConfigGenerator
        generator = CinemonConfigGenerator()
        config_path = generator.generate_preset(recording_dir, "vintage", seed=42)
        
        assert config_path.exists()
        assert config_path.name == "animation_config_vintage.yaml"
        
        # 4. Verify generated config structure
        with config_path.open('r') as f:
            config_data = yaml.safe_load(f)
        
        assert "project" in config_data
        assert "audio_analysis" in config_data
        assert "layout" in config_data
        assert "animations" in config_data
        
        assert config_data["project"]["main_audio"] == "main_audio.m4a"
        assert config_data["layout"]["config"]["seed"] == 42
        assert len(config_data["animations"]) == 6

    def test_custom_config_pipeline(self, tmp_path):
        """Test complete pipeline for custom configuration generation."""
        # Setup test recording structure
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)
        
        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "Camera2.mp4").touch()
        (extracted_dir / "microphone.wav").touch()
        
        # Define custom configuration
        layout = {
            "type": "random",
            "config": {
                "overlap_allowed": False,
                "seed": 123,
                "margin": 0.08
            }
        }
        
        animations = [
            {
                "type": "scale",
                "trigger": "bass",
                "intensity": 0.4,
                "duration_frames": 3,
                "target_strips": ["Camera1"]
            },
            {
                "type": "vintage_color",
                "trigger": "one_time",
                "sepia_amount": 0.5,
                "contrast_boost": 0.4,
                "target_strips": ["Camera2"]
            }
        ]
        
        # Generate custom configuration
        generator = CinemonConfigGenerator()
        config_path = generator.generate_config(
            recording_dir,
            layout=layout,
            animations=animations,
            main_audio="microphone.wav"
        )
        
        assert config_path.exists()
        assert config_path.name == "animation_config.yaml"
        
        # Verify configuration content
        with config_path.open('r') as f:
            config_data = yaml.safe_load(f)
        
        assert config_data["project"]["main_audio"] == "microphone.wav"
        assert config_data["layout"]["config"]["seed"] == 123
        assert len(config_data["animations"]) == 2
        
        # Verify targeting
        scale_anim = next(anim for anim in config_data["animations"] if anim["type"] == "scale")
        vintage_anim = next(anim for anim in config_data["animations"] if anim["type"] == "vintage_color")
        
        assert scale_anim["target_strips"] == ["Camera1"]
        assert vintage_anim["target_strips"] == ["Camera2"]

    def test_multiple_audio_files_handling(self, tmp_path):
        """Test pipeline handling of multiple audio files."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)
        
        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "microphone.wav").touch()
        (extracted_dir / "desktop_audio.m4a").touch()
        (extracted_dir / "background_music.mp3").touch()
        
        # Test MediaDiscovery auto-detection
        discovery = MediaDiscovery(recording_dir)
        main_audio = discovery.detect_main_audio()
        
        assert main_audio is None  # Should be None for multiple files
        
        # Test CinemonConfigGenerator error handling
        generator = CinemonConfigGenerator()
        
        with pytest.raises(ValueError, match="Multiple audio files found"):
            generator.generate_preset(recording_dir, "vintage")
        
        # Test explicit main audio specification
        config_path = generator.generate_preset(
            recording_dir, 
            "vintage", 
            main_audio="microphone.wav"
        )
        
        with config_path.open('r') as f:
            config_data = yaml.safe_load(f)
        
        assert config_data["project"]["main_audio"] == "microphone.wav"

    def test_preset_variations_pipeline(self, tmp_path):
        """Test pipeline with different preset variations."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)
        
        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "main_audio.m4a").touch()
        
        generator = CinemonConfigGenerator()
        presets_to_test = ["vintage", "music-video", "minimal", "beat-switch"]
        
        for preset_name in presets_to_test:
            config_path = generator.generate_preset(recording_dir, preset_name)
            
            assert config_path.exists()
            assert config_path.name == f"animation_config_{preset_name}.yaml"
            
            with config_path.open('r') as f:
                config_data = yaml.safe_load(f)
            
            assert config_data["project"]["main_audio"] == "main_audio.m4a"
            assert "layout" in config_data
            assert "animations" in config_data
            assert isinstance(config_data["animations"], list)

    def test_polish_filenames_pipeline(self, tmp_path):
        """Test complete pipeline with Polish character filenames."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)
        
        (extracted_dir / "Kamera główna.mp4").touch()
        (extracted_dir / "Przechwytywanie ekranu.mkv").touch()
        (extracted_dir / "Przechwytywanie wejścia dźwięku.m4a").touch()
        
        # Test MediaDiscovery with Polish filenames
        discovery = MediaDiscovery(recording_dir)
        video_files = discovery.discover_video_files()
        audio_files = discovery.discover_audio_files()
        main_audio = discovery.detect_main_audio()
        
        assert "Kamera główna.mp4" in video_files
        assert "Przechwytywanie ekranu.mkv" in video_files
        assert "Przechwytywanie wejścia dźwięku.m4a" in audio_files
        assert main_audio == "Przechwytywanie wejścia dźwięku.m4a"
        
        # Test config generation with Polish filenames
        generator = CinemonConfigGenerator()
        config_path = generator.generate_preset(recording_dir, "vintage")
        
        with config_path.open('r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        assert config_data["project"]["main_audio"] == "Przechwytywanie wejścia dźwięku.m4a"

    def test_error_handling_pipeline(self, tmp_path):
        """Test pipeline error handling scenarios."""
        generator = CinemonConfigGenerator()
        
        # Test nonexistent directory
        nonexistent_dir = tmp_path / "nonexistent"
        with pytest.raises(FileNotFoundError):
            generator.generate_preset(nonexistent_dir, "vintage")
        
        # Test directory with missing extracted folder
        empty_dir = tmp_path / "empty_recording"
        empty_dir.mkdir()
        with pytest.raises(FileNotFoundError):
            generator.generate_preset(empty_dir, "vintage")
        
        # Test directory with no video files
        recording_dir = tmp_path / "recording_no_video"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)
        (extracted_dir / "audio_only.m4a").touch()
        
        with pytest.raises(ValueError, match="No video files found"):
            generator.generate_preset(recording_dir, "vintage")
        
        # Test directory with no audio files
        recording_dir2 = tmp_path / "recording_no_audio"
        extracted_dir2 = recording_dir2 / "extracted"
        extracted_dir2.mkdir(parents=True)
        (extracted_dir2 / "video_only.mp4").touch()
        
        with pytest.raises(ValueError, match="No audio files found"):
            generator.generate_preset(recording_dir2, "vintage")
        
        # Test invalid preset name
        recording_dir3 = tmp_path / "recording_valid"
        extracted_dir3 = recording_dir3 / "extracted"
        extracted_dir3.mkdir(parents=True)
        (extracted_dir3 / "Camera1.mp4").touch()
        (extracted_dir3 / "main_audio.m4a").touch()
        
        with pytest.raises(ValueError, match="Preset 'nonexistent' not found"):
            generator.generate_preset(recording_dir3, "nonexistent")

    def test_config_file_overwriting(self, tmp_path):
        """Test that configuration files are properly overwritten."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)
        
        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "main_audio.m4a").touch()
        
        generator = CinemonConfigGenerator()
        
        # Generate first config
        config_path1 = generator.generate_preset(recording_dir, "vintage", seed=100)
        
        with config_path1.open('r') as f:
            config_data1 = yaml.safe_load(f)
        assert config_data1["layout"]["config"]["seed"] == 100
        
        # Generate second config with different parameters
        config_path2 = generator.generate_preset(recording_dir, "vintage", seed=200)
        
        # Should be same path
        assert config_path1 == config_path2
        
        # But content should be updated
        with config_path2.open('r') as f:
            config_data2 = yaml.safe_load(f)
        assert config_data2["layout"]["config"]["seed"] == 200