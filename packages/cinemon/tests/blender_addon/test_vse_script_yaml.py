# ABOUTME: Tests for vse_script.py YAML integration with real file creation
# ABOUTME: Validates YAML loading and conversion to internal format

"""Tests for vse_script.py YAML configuration integration."""

import pytest
import sys
import yaml
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

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
        from vse_script import BlenderVSEConfigurator
        
        # Create mock YAML config (internal format - already converted)
        mock_config = {
            "project": {
                "video_files": ["Camera1.mp4", "Camera2.mp4"],
                "fps": 30
            },
            "layout": {"type": "random"},
            "animations": [],
            "audio_analysis": {"file": "./analysis/audio.json"}
        }
        
        # Create temporary YAML file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
            yaml.dump(mock_config, temp_file, default_flow_style=False)
            temp_path = temp_file.name
        
        try:
            configurator = BlenderVSEConfigurator(temp_path)
            
            # Verify attributes are set correctly
            assert len(configurator.video_files) == 2
            assert configurator.fps == 30
            assert configurator.config_data["layout"]["type"] == "random"
        finally:
            os.unlink(temp_path)
    
    def test_yaml_config_validation_errors(self):
        """Test validation errors are properly handled with YAML configs."""
        from vse_script import BlenderVSEConfigurator
        
        # Create invalid YAML config (missing required fields)
        invalid_config = {
            "project": {
                "video_files": [],
                # fps missing
            },
            "layout": {"type": "random"},
            "animations": [],
            # audio_analysis missing
        }
        
        # Create temporary YAML file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
            yaml.dump(invalid_config, temp_file, default_flow_style=False)
            temp_path = temp_file.name
        
        try:
            configurator = BlenderVSEConfigurator(temp_path)
            is_valid, errors = configurator.validate_parameters()
            
            assert not is_valid
            assert len(errors) > 0
            assert any("audio_analysis" in error for error in errors)
        finally:
            os.unlink(temp_path)
    
    def test_yaml_strip_animations_conversion(self):
        """Test conversion of new YAML strip_animations format to internal format."""
        from vse_script import BlenderVSEConfigurator
        
        # Create grouped format YAML (strip_animations - this triggers conversion)
        grouped_config = {
            "project": {"video_files": ["Camera1.mp4"], "fps": 30},
            "layout": {"type": "random"},
            "strip_animations": {
                "Camera1": [
                    {"type": "scale", "trigger": "beat", "intensity": 0.5},
                    {"type": "shake", "trigger": "energy_peaks", "intensity": 1.0}
                ],
                "Camera2": [
                    {"type": "vintage_color", "trigger": "one_time", "sepia_amount": 0.6}
                ]
            },
            "audio_analysis": {"file": "./analysis/audio.json"}
        }
        
        # Create temporary YAML file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
            yaml.dump(grouped_config, temp_file, default_flow_style=False)
            temp_path = temp_file.name
        
        try:
            configurator = BlenderVSEConfigurator(temp_path)
            
            # Verify animations were converted to internal format properly
            assert len(configurator.config_data["animations"]) == 3
            animations = configurator.config_data["animations"]
            
            # Check that target_strips were added during conversion
            for anim in animations:
                assert "target_strips" in anim
                assert len(anim["target_strips"]) == 1
            
            # Check specific conversions
            camera1_anims = [a for a in animations if a["target_strips"] == ["Camera1"]]
            camera2_anims = [a for a in animations if a["target_strips"] == ["Camera2"]]
            
            assert len(camera1_anims) == 2  # scale + shake
            assert len(camera2_anims) == 1  # vintage_color
            
            # Check animation types are preserved
            anim_types = [a["type"] for a in animations]
            assert "scale" in anim_types
            assert "shake" in anim_types
            assert "vintage_color" in anim_types
        finally:
            os.unlink(temp_path)
    
    def test_yaml_command_line_detection(self):
        """Test that .yaml files are properly detected in command line arguments."""
        from vse_script import BlenderVSEConfigurator
        
        # Create valid config
        mock_config = {
            "project": {"video_files": [], "fps": 30},
            "layout": {"type": "random"},
            "animations": [],
            "audio_analysis": {"file": "./analysis/audio.json"}
        }
        
        # Create temporary YAML file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
            yaml.dump(mock_config, temp_file, default_flow_style=False)
            temp_path = temp_file.name
        
        try:
            # Mock sys.argv with YAML config
            with patch('vse_script.sys.argv', ['script.py', '--config', temp_path]):
                # Should accept .yaml file without issues
                configurator = BlenderVSEConfigurator()
                assert configurator.fps == 30
        finally:
            os.unlink(temp_path)
    
    def test_yaml_preset_loading_integration(self):
        """Test loading example preset files through vse_script.py."""
        from vse_script import BlenderVSEConfigurator
        
        # Test with vintage preset content (strip_animations format)
        vintage_config = {
            "project": {
                "video_files": ["Camera1.mp4"],  # Add video files for validation
                "fps": 30
            },
            "layout": {
                "type": "random",
                "config": {
                    "margin": 0.1,
                    "seed": 1950
                }
            },
            "strip_animations": {
                "Camera1": [
                    {"type": "scale", "trigger": "beat", "intensity": 0.3, "easing": "EASE_OUT"},
                    {"type": "vintage_color", "trigger": "one_time", "sepia_amount": 0.6, "contrast_boost": 0.2}
                ],
                "Camera2": [
                    {"type": "shake", "trigger": "energy_peaks", "intensity": 2.0, "return_frames": 2}
                ]
            },
            "audio_analysis": {
                "file": "./analysis/main_audio_analysis.json",
                "beat_division": 4
            }
        }
        
        # Create temporary YAML file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
            yaml.dump(vintage_config, temp_file, default_flow_style=False)
            temp_path = temp_file.name
        
        try:
            configurator = BlenderVSEConfigurator(temp_path)
            
            # Verify preset characteristics
            assert configurator.fps == 30
            assert configurator.config_data["layout"]["type"] == "random"
            
            # Check converted animations
            animations = configurator.config_data["animations"]
            assert len(animations) == 3
            
            # Check vintage-specific animation
            vintage_anim = next((a for a in animations if a["type"] == "vintage_color"), None)
            assert vintage_anim is not None
            assert vintage_anim["sepia_amount"] == 0.6
        finally:
            os.unlink(temp_path)
    
    def test_yaml_error_handling_malformed(self):
        """Test error handling for malformed YAML files."""
        from vse_script import BlenderVSEConfigurator
        
        # Create malformed YAML content
        malformed_yaml = "project:\n  video_files: [\n  fps: 30\nlayout:\n  type: random\n"
        
        # Create temporary file with malformed YAML
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
            temp_file.write(malformed_yaml)
            temp_path = temp_file.name
        
        try:
            # Should raise an exception when trying to load malformed YAML
            with pytest.raises(Exception):  # Could be yaml.YAMLError or other parsing error
                configurator = BlenderVSEConfigurator(temp_path)
        finally:
            os.unlink(temp_path)
    
    def test_yaml_unicode_support(self):
        """Test Unicode support in YAML configurations."""
        from vse_script import BlenderVSEConfigurator
        
        # Create config with Unicode filenames
        unicode_config = {
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
        
        # Create temporary YAML file with Unicode content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as temp_file:
            yaml.dump(unicode_config, temp_file, default_flow_style=False, allow_unicode=True)
            temp_path = temp_file.name
        
        try:
            configurator = BlenderVSEConfigurator(temp_path)
            
            # Verify Unicode content is preserved
            assert "Przechwytywanie" in str(configurator.video_files[0])
            assert configurator.main_audio.name == "Audio główne.m4a"
            
            # Check animation with Unicode target
            animations = configurator.config_data["animations"]
            assert len(animations) == 1
            assert "🎥 Camera główna" in animations[0]["target_strips"]
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])