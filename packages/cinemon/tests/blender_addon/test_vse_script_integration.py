# ABOUTME: Integration tests for vse_script.py with real YAML presets
# ABOUTME: Tests loading actual preset files without mocking

"""Integration tests for vse_script.py with real YAML preset files."""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch

# Add paths
addon_path = Path(__file__).parent.parent.parent / "blender_addon"
blender_path = Path(__file__).parent.parent.parent / "src" / "blender"
if str(addon_path) not in sys.path:
    sys.path.insert(0, str(addon_path))
if str(blender_path) not in sys.path:
    sys.path.insert(0, str(blender_path))


class TestVSEScriptIntegration:
    """Test vse_script.py integration with real YAML presets."""
    
    def test_load_vintage_preset_real(self):
        """Test loading real vintage preset file."""
        from vse_script import BlenderVSEConfigurator
        
        vintage_path = addon_path / "example_presets" / "vintage.yaml"
        assert vintage_path.exists(), f"Vintage preset not found: {vintage_path}"
        
        # Should load without errors
        configurator = BlenderVSEConfigurator(str(vintage_path))
        
        # Verify basic configuration
        assert configurator.fps == 30
        assert configurator.config_data["layout"]["type"] == "random"
        
        # Verify animations were converted properly
        animations = configurator.config_data.get("animations", [])
        assert len(animations) > 0
        
        # Check for vintage-specific animations
        animation_types = [anim["type"] for anim in animations]
        assert "vintage_color" in animation_types
        
        print(f"✓ Vintage preset loaded: {len(animations)} animations")
    
    def test_load_music_video_preset_real(self):
        """Test loading real music-video preset file."""
        from vse_script import BlenderVSEConfigurator
        
        preset_path = addon_path / "example_presets" / "music-video.yaml"
        assert preset_path.exists(), f"Music video preset not found: {preset_path}"
        
        # Should load without errors
        configurator = BlenderVSEConfigurator(str(preset_path))
        
        # Verify music-video characteristics
        assert configurator.fps == 60  # Higher FPS for music videos
        assert configurator.config_data["layout"]["type"] == "grid"
        
        # Verify animations
        animations = configurator.config_data.get("animations", [])
        assert len(animations) > 0
        
        # Check for music-video specific animations
        animation_types = [anim["type"] for anim in animations]
        assert "pip_switch" in animation_types
        
        print(f"✓ Music-video preset loaded: {len(animations)} animations")
    
    def test_load_minimal_preset_real(self):
        """Test loading real minimal preset file."""
        from vse_script import BlenderVSEConfigurator
        
        preset_path = addon_path / "example_presets" / "minimal.yaml"
        assert preset_path.exists(), f"Minimal preset not found: {preset_path}"
        
        # Should load without errors
        configurator = BlenderVSEConfigurator(str(preset_path))
        
        # Verify minimal characteristics
        assert configurator.fps == 30
        assert configurator.config_data["layout"]["type"] == "cascade"
        
        # Verify low-intensity animations
        animations = configurator.config_data.get("animations", [])
        assert len(animations) > 0
        
        # Check that intensities are low (minimal preset)
        scale_animations = [a for a in animations if a["type"] == "scale"]
        if scale_animations:
            assert scale_animations[0]["intensity"] <= 0.2
        
        print(f"✓ Minimal preset loaded: {len(animations)} animations")
    
    def test_load_beat_switch_preset_real(self):
        """Test loading real beat-switch preset file."""
        from vse_script import BlenderVSEConfigurator
        
        preset_path = addon_path / "example_presets" / "beat-switch.yaml"
        assert preset_path.exists(), f"Beat switch preset not found: {preset_path}"
        
        # Should load without errors
        configurator = BlenderVSEConfigurator(str(preset_path))
        
        # Verify beat-switch characteristics
        assert configurator.fps == 30
        assert configurator.config_data["layout"]["type"] == "random"
        
        # Verify animations
        animations = configurator.config_data.get("animations", [])
        assert len(animations) > 0
        
        # Check for beat-switch specific animations
        animation_types = [anim["type"] for anim in animations]
        assert "pip_switch" in animation_types
        
        print(f"✓ Beat-switch preset loaded: {len(animations)} animations")
    
    def test_preset_validation_passes(self):
        """Test that all presets pass validation."""
        from vse_script import BlenderVSEConfigurator
        
        preset_files = [
            "vintage.yaml",
            "music-video.yaml", 
            "minimal.yaml",
            "beat-switch.yaml"
        ]
        
        for preset_file in preset_files:
            preset_path = addon_path / "example_presets" / preset_file
            configurator = BlenderVSEConfigurator(str(preset_path))
            
            # All presets should pass validation
            is_valid, errors = configurator.validate_parameters()
            
            if not is_valid:
                print(f"Validation errors for {preset_file}: {errors}")
            
            assert is_valid, f"Preset {preset_file} failed validation: {errors}"
            print(f"✓ {preset_file} passes validation")
    
    def test_animation_data_structure(self):
        """Test that converted animation data has correct structure."""
        from vse_script import BlenderVSEConfigurator
        
        preset_path = addon_path / "example_presets" / "vintage.yaml"
        configurator = BlenderVSEConfigurator(str(preset_path))
        
        animations = configurator.config_data.get("animations", [])
        
        for i, animation in enumerate(animations):
            # Each animation should have required fields
            assert "type" in animation, f"Animation {i} missing 'type'"
            assert "trigger" in animation, f"Animation {i} missing 'trigger'"
            assert "target_strips" in animation, f"Animation {i} missing 'target_strips'"
            
            # target_strips should be a list
            assert isinstance(animation["target_strips"], list), f"Animation {i} target_strips not a list"
            
            print(f"✓ Animation {i}: {animation['type']} -> {animation['target_strips']}")
    
    def test_command_line_arg_parsing(self):
        """Test command line argument parsing with real preset."""
        from vse_script import BlenderVSEConfigurator
        
        preset_path = addon_path / "example_presets" / "vintage.yaml"
        
        # Mock sys.argv
        with patch('vse_script.sys.argv', ['script.py', '--config', str(preset_path)]):
            configurator = BlenderVSEConfigurator()
            
            # Should load vintage preset
            assert configurator.fps == 30
            assert configurator.config_data["layout"]["type"] == "random"
            
            animations = configurator.config_data.get("animations", [])
            animation_types = [anim["type"] for anim in animations]
            assert "vintage_color" in animation_types
            
            print("✓ Command line argument parsing works with real preset")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])