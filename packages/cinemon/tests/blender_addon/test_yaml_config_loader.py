# ABOUTME: Test for YAMLConfigLoader with new strip_animations format
# ABOUTME: Tests validation, loading, and conversion of new YAML schema

"""Test YAMLConfigLoader for new YAML format with strip_animations grouping."""

import pytest
import sys
from pathlib import Path

# Add blender_addon to path
addon_path = Path(__file__).parent.parent.parent / "blender_addon"
if str(addon_path) not in sys.path:
    sys.path.insert(0, str(addon_path))


class TestYAMLConfigLoaderValidation:
    """Test validation of new YAML format."""
    
    def test_valid_minimal_config(self):
        """Test loading minimal valid configuration."""
        from config_loader import YAMLConfigLoader
        
        minimal_config = """
project:
  video_files: [Camera1.mp4]
  fps: 30

layout:
  type: "random"
  config:
    seed: 42

strip_animations:
  Camera1:
    - type: "scale"
      trigger: "beat"
      intensity: 0.3

audio_analysis:
  file: "./analysis/audio.json"
"""
        loader = YAMLConfigLoader()
        config = loader.load_from_string(minimal_config)
        
        assert config is not None
        assert config.project.fps == 30
        assert len(config.project.video_files) == 1
        assert "Camera1" in config.strip_animations
    
    def test_valid_full_config(self):
        """Test loading complete configuration with all options."""
        from config_loader import YAMLConfigLoader
        
        full_config = """
project:
  video_files: [Camera1.mp4, Camera2.mp4, Screen.mp4]
  main_audio: "main_audio.m4a"
  fps: 60
  resolution:
    width: 1920
    height: 1080

layout:
  type: "grid"
  config:
    rows: 2
    cols: 2
    margin: 0.05
    overlap_allowed: false

strip_animations:
  Camera1:
    - type: "scale"
      trigger: "beat"
      intensity: 0.5
      easing: "EASE_OUT"
    - type: "shake"
      trigger: "energy_peaks" 
      intensity: 1.5
      return_frames: 3

  Camera2:
    - type: "vintage_color"
      trigger: "one_time"
      sepia_amount: 0.6
      contrast_boost: 0.4
  
  Screen:
    - type: "pip_switch"
      trigger: "beat"
      positions: ["TOP_LEFT", "TOP_RIGHT", "BOTTOM_LEFT"]

audio_analysis:
  file: "./analysis/main_audio_analysis.json"
  beat_division: 4
  min_onset_interval: 1.0
"""
        loader = YAMLConfigLoader()
        config = loader.load_from_string(full_config)
        
        assert config.project.fps == 60
        assert len(config.project.video_files) == 3
        assert config.project.resolution.width == 1920
        assert len(config.strip_animations["Camera1"]) == 2
        assert config.strip_animations["Camera1"][0]["easing"] == "EASE_OUT"
    
    def test_missing_required_fields(self):
        """Test validation fails for missing required fields."""
        from config_loader import YAMLConfigLoader, ValidationError
        
        # Missing project section
        invalid_config = """
layout:
  type: "random"
strip_animations: {}
"""
        loader = YAMLConfigLoader()
        with pytest.raises(ValidationError, match="Missing required section: project"):
            loader.load_from_string(invalid_config)
    
    def test_invalid_animation_type(self):
        """Test validation fails for unknown animation types."""
        from config_loader import YAMLConfigLoader, ValidationError
        
        invalid_config = """
project:
  video_files: [test.mp4]
  fps: 30
layout:
  type: "random"
strip_animations:
  test:
    - type: "unknown_animation"
      trigger: "beat"
audio_analysis:
  file: "./analysis/audio.json"
"""
        loader = YAMLConfigLoader()
        with pytest.raises(ValidationError, match="Unknown animation type: unknown_animation"):
            loader.load_from_string(invalid_config)
    
    def test_invalid_trigger_type(self):
        """Test validation fails for unknown trigger types."""
        from config_loader import YAMLConfigLoader, ValidationError
        
        invalid_config = """
project:
  video_files: [test.mp4]
  fps: 30
layout:
  type: "random"
strip_animations:
  test:
    - type: "scale"
      trigger: "unknown_trigger"
audio_analysis:
  file: "./analysis/audio.json"
"""
        loader = YAMLConfigLoader()
        with pytest.raises(ValidationError, match="Unknown trigger type: unknown_trigger"):
            loader.load_from_string(invalid_config)


class TestYAMLConfigLoaderConversion:
    """Test conversion from YAML to internal representation."""
    
    def test_convert_to_internal_format(self):
        """Test conversion to format expected by vse_script.py."""
        from config_loader import YAMLConfigLoader
        
        yaml_config = """
project:
  video_files: [Camera1.mp4, Camera2.mp4]
  fps: 30

layout:
  type: "random"
  config:
    seed: 42

strip_animations:
  Camera1:
    - type: "scale"
      trigger: "beat"
      intensity: 0.3
  Camera2:
    - type: "vintage_color"
      trigger: "one_time"
      sepia_amount: 0.5

audio_analysis:
  file: "./analysis/audio.json"
"""
        loader = YAMLConfigLoader()
        config = loader.load_from_string(yaml_config)
        internal_format = loader.convert_to_internal(config)
        
        # Should have flat list of animations with target_strips
        animations = internal_format["animations"]
        assert isinstance(animations, list)
        assert len(animations) == 2

        # Check animation content
        scale_anim = next(a for a in animations if a["type"] == "scale")
        assert scale_anim["trigger"] == "beat"
        assert scale_anim["intensity"] == 0.3
        assert scale_anim["target_strips"] == ["Camera1"]

        vintage_anim = next(a for a in animations if a["type"] == "vintage_color")
        assert vintage_anim["trigger"] == "one_time"
        assert vintage_anim["sepia_amount"] == 0.5
        assert vintage_anim["target_strips"] == ["Camera2"]
    
    def test_handle_empty_strip_animations(self):
        """Test handling strips with no animations."""
        from config_loader import YAMLConfigLoader
        
        yaml_config = """
project:
  video_files: [Camera1.mp4, Camera2.mp4]
  fps: 30

layout:
  type: "random"

strip_animations:
  Camera1:
    - type: "scale"
      trigger: "beat"
      intensity: 0.3
  # Camera2 has no animations

audio_analysis:
  file: "./analysis/audio.json"
"""
        loader = YAMLConfigLoader()
        config = loader.load_from_string(yaml_config)
        internal_format = loader.convert_to_internal(config)
        
        # Should have flat list with only Camera1 animation
        animations = internal_format["animations"]
        assert isinstance(animations, list)
        assert len(animations) == 1
        
        # Only Camera1 should have animations
        assert animations[0]["type"] == "scale"
        assert animations[0]["target_strips"] == ["Camera1"]


class TestYAMLConfigLoaderEdgeCases:
    """Test edge cases and error handling."""
    
    def test_polish_characters_in_filenames(self):
        """Test handling Polish characters in file names."""
        from config_loader import YAMLConfigLoader
        
        polish_config = """
project:
  video_files: ["Kamera główna.mp4"]
  main_audio: "Przechwytywanie wejścia dźwięku.m4a"
  fps: 30

layout:
  type: "random"

strip_animations:
  "Kamera główna":
    - type: "scale"
      trigger: "beat"
      intensity: 0.3

audio_analysis:
  file: "./analysis/audio_ąęć.json"
"""
        loader = YAMLConfigLoader()
        config = loader.load_from_string(polish_config)
        
        assert config.project.main_audio == "Przechwytywanie wejścia dźwięku.m4a"
        assert "Kamera główna" in config.strip_animations
    
    def test_malformed_yaml(self):
        """Test handling malformed YAML."""
        from config_loader import YAMLConfigLoader, ValidationError
        
        malformed_yaml = """
project:
  video_files: [test.mp4
  # Missing closing bracket
layout: {invalid
"""
        loader = YAMLConfigLoader()
        with pytest.raises(ValidationError, match="Invalid YAML format"):
            loader.load_from_string(malformed_yaml)
    
    def test_load_from_file(self):
        """Test loading configuration from file."""
        from config_loader import YAMLConfigLoader
        import tempfile
        
        config_content = """
project:
  video_files: [test.mp4]
  fps: 30
layout:
  type: "random"
strip_animations:
  test:
    - type: "scale"
      trigger: "beat"
audio_analysis:
  file: "./analysis/audio.json"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            temp_path = f.name
        
        try:
            loader = YAMLConfigLoader()
            config = loader.load_from_file(temp_path)
            assert config.project.fps == 30
        finally:
            Path(temp_path).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])