# ABOUTME: Tests for vse_script.py YAML integration
# ABOUTME: Validates YAML loading and conversion to internal format

"""Tests for vse_script.py YAML configuration integration."""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

# Add blender_addon to path
addon_path = Path(__file__).parent.parent.parent / "blender_addon"
if str(addon_path) not in sys.path:
    sys.path.insert(0, str(addon_path))

# Add src/blender to path for vse_script
blender_path = Path(__file__).parent.parent.parent / "src" / "blender"
if str(blender_path) not in sys.path:
    sys.path.insert(0, str(blender_path))


class TestVSEScriptYAMLIntegration:
    """Test YAML integration in vse_script.py"""
    
    def test_yaml_config_loading_basic(self):
        """Test basic YAML configuration loading in BlenderVSEConfigurator."""
        with patch('config_loader.YAMLConfigLoader.load_from_file') as mock_load:
            with patch('config_loader.YAMLConfigLoader.convert_to_internal') as mock_convert:
                from vse_script import BlenderVSEConfigurator
                
                # Mock YAML loading and conversion
                mock_config = Mock()
                mock_load.return_value = mock_config
                
                mock_convert.return_value = {
                    "project": {
                        "video_files": ["Camera1.mp4", "Camera2.mp4"],
                        "fps": 30
                    },
                    "layout": {"type": "random"},
                    "animations": [],
                    "audio_analysis": {"file": "./analysis/audio.json"}
                }
                
                configurator = BlenderVSEConfigurator("test_config.yaml")
                
                # Verify attributes are set correctly
                assert len(configurator.video_files) == 2
                assert configurator.fps == 30
                assert configurator.config_data["layout"]["type"] == "random"
    
    def test_yaml_config_validation_errors(self):
        """Test validation errors are properly handled with YAML configs."""
        with patch('config_loader.YAMLConfigLoader.load_from_file') as mock_load:
            with patch('config_loader.YAMLConfigLoader.convert_to_internal') as mock_convert:
                from vse_script import BlenderVSEConfigurator
                
                # Mock YAML loading and conversion
                mock_config = Mock()
                mock_load.return_value = mock_config
                
                # Mock conversion to invalid internal format
                mock_convert.return_value = {
                    "project": {
                        "video_files": [],
                        # fps missing
                    },
                    "layout": {"type": "random"},
                    "animations": [],
                    # audio_analysis missing
                }
                
                configurator = BlenderVSEConfigurator("test_config.yaml")
                is_valid, errors = configurator.validate_parameters()
                
                assert not is_valid
                assert len(errors) > 0
                assert any("audio_analysis" in error for error in errors)
    
    def test_yaml_strip_animations_conversion(self):
        """Test conversion of new YAML strip_animations format to internal format."""
        with patch('config_loader.YAMLConfigLoader.load_from_file') as mock_load:
            with patch('config_loader.YAMLConfigLoader.convert_to_internal') as mock_convert:
                from vse_script import BlenderVSEConfigurator
                
                # Mock YAML loading and conversion
                mock_config = Mock()
                mock_load.return_value = mock_config
                
                # Mock the converted internal format
                expected_animations = [
                    {"type": "scale", "trigger": "beat", "intensity": 0.5, "target_strips": ["Camera1"]},
                    {"type": "shake", "trigger": "energy_peaks", "intensity": 1.0, "target_strips": ["Camera1"]},
                    {"type": "vintage_color", "trigger": "one_time", "sepia_amount": 0.6, "target_strips": ["Camera2"]}
                ]
                
                mock_convert.return_value = {
                    "project": {"video_files": ["Camera1.mp4"], "fps": 30},
                    "layout": {"type": "random"},
                    "animations": expected_animations,
                    "audio_analysis": {"file": "./analysis/audio.json"}
                }
                
                configurator = BlenderVSEConfigurator("test_config.yaml")
                
                # Verify animations are properly converted
                assert len(configurator.config_data["animations"]) == 3
                
                # Check that target_strips are properly set
                scale_anim = next(a for a in configurator.config_data["animations"] if a["type"] == "scale")
                assert "Camera1" in scale_anim["target_strips"]
                
                vintage_anim = next(a for a in configurator.config_data["animations"] if a["type"] == "vintage_color")
                assert "Camera2" in vintage_anim["target_strips"]
    
    def test_yaml_command_line_detection(self):
        """Test that .yaml files are properly detected in command line arguments."""
        # Mock sys.argv with YAML config
        with patch('vse_script.sys.argv', ['script.py', '--config', 'animation_config.yaml']):
            with patch('config_loader.YAMLConfigLoader.load_from_file') as mock_load:
                with patch('config_loader.YAMLConfigLoader.convert_to_internal') as mock_convert:
                    from vse_script import BlenderVSEConfigurator
                    
                    # Mock YAML loading and conversion
                    mock_config = Mock()
                    mock_load.return_value = mock_config
                    
                    mock_convert.return_value = {
                        "project": {"video_files": [], "fps": 30},
                        "layout": {},
                        "animations": [],
                        "audio_analysis": {}
                    }
                    
                    # Should accept .yaml file without issues
                    configurator = BlenderVSEConfigurator()
                    assert configurator.fps == 30
    
    def test_yaml_preset_loading_integration(self):
        """Test loading example preset files through vse_script.py."""
        # Test with vintage preset content
        vintage_yaml = """
project:
  video_files: []
  fps: 30
layout:
  type: random
  config:
    margin: 0.1
    seed: 1950
strip_animations:
  Camera1:
    - type: scale
      trigger: beat
      intensity: 0.3
      easing: EASE_OUT
    - type: vintage_color
      trigger: one_time
      sepia_amount: 0.6
      contrast_boost: 0.2
  Camera2:
    - type: shake
      trigger: energy_peaks
      intensity: 2.0
      return_frames: 2
audio_analysis:
  file: "./analysis/main_audio_analysis.json"
  beat_division: 4
"""
        
        with patch('builtins.open', mock_open(read_data=vintage_yaml)):
            with patch('config_loader.YAMLConfigLoader.load_from_file') as mock_load:
                with patch('config_loader.YAMLConfigLoader.convert_to_internal') as mock_convert:
                    from vse_script import BlenderVSEConfigurator
                    
                    # Mock YAML loading and conversion
                    mock_config = Mock()
                    mock_load.return_value = mock_config
                    
                    mock_convert.return_value = {
                        "project": {"video_files": [], "fps": 30},
                        "layout": {"type": "random", "config": {"margin": 0.1, "seed": 1950}},
                        "animations": [
                            {"type": "scale", "trigger": "beat", "intensity": 0.3, "target_strips": ["Camera1"]},
                            {"type": "vintage_color", "trigger": "one_time", "sepia_amount": 0.6, "target_strips": ["Camera1"]},
                            {"type": "shake", "trigger": "energy_peaks", "intensity": 2.0, "target_strips": ["Camera2"]}
                        ],
                        "audio_analysis": {"file": "./analysis/main_audio_analysis.json", "beat_division": 4}
                    }
                    
                    configurator = BlenderVSEConfigurator("vintage.yaml")
                    
                    # Verify preset characteristics
                    assert configurator.fps == 30
                    assert configurator.config_data["layout"]["type"] == "random"
                    assert configurator.config_data["layout"]["config"]["seed"] == 1950
                    
                    # Verify animations
                    animations = configurator.config_data["animations"]
                    assert len(animations) == 3
                    
                    # Check for vintage-specific animations
                    has_vintage_color = any(a["type"] == "vintage_color" for a in animations)
                    assert has_vintage_color
    
    def test_yaml_error_handling_malformed(self):
        """Test error handling for malformed YAML files."""
        with patch('config_loader.YAMLConfigLoader.load_from_file') as mock_load:
            from vse_script import BlenderVSEConfigurator
            from config_loader import ValidationError
            
            # Mock YAML loading error
            mock_load.side_effect = ValidationError("Invalid YAML format")
            
            # Should handle YAML parsing errors gracefully
            with pytest.raises(ValidationError):
                BlenderVSEConfigurator("malformed.yaml")
    
    def test_yaml_unicode_support(self):
        """Test Unicode support in YAML configurations."""
        with patch('config_loader.YAMLConfigLoader.load_from_file') as mock_load:
            with patch('config_loader.YAMLConfigLoader.convert_to_internal') as mock_convert:
                from vse_script import BlenderVSEConfigurator
                
                # Mock YAML loading and conversion
                mock_config = Mock()
                mock_load.return_value = mock_config
                
                mock_convert.return_value = {
                    "project": {
                        "video_files": ["Przechwytywanie wejścia dźwięku.mp4"],
                        "main_audio": "Audio główne.m4a",
                        "fps": 30
                    },
                    "layout": {"type": "random"},
                    "animations": [
                        {"type": "scale", "trigger": "beat", "intensity": 0.3, "target_strips": ["🎥 Camera główna"]}
                    ],
                    "audio_analysis": {"file": "./analysis/analiza_główna.json"}
                }
                
                configurator = BlenderVSEConfigurator("unicode.yaml")
                
                # Verify Unicode handling
                assert "Przechwytywanie wejścia dźwięku.mp4" in [str(f) for f in configurator.video_files]
                assert str(configurator.main_audio) == "Audio główne.m4a"
                
                # Check animation target strips with Unicode
                animations = configurator.config_data["animations"]
                unicode_anim = animations[0]
                assert "🎥 Camera główna" in unicode_anim["target_strips"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])