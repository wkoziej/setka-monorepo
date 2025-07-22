# ABOUTME: Tests for PresetManager configuration preset functionality
# ABOUTME: Tests built-in presets, custom preset creation, and preset validation

"""Tests for PresetManager class."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import json

from blender.config.preset_manager import PresetManager, PresetConfig


@pytest.fixture(autouse=True)
def isolated_custom_presets(tmp_path, monkeypatch):
    """Ensure each test uses isolated temporary directory for custom presets."""
    temp_presets_dir = tmp_path / "custom_presets"
    temp_presets_dir.mkdir()
    
    # Mock the custom presets directory method
    monkeypatch.setattr(PresetManager, '_get_custom_presets_dir', lambda self: temp_presets_dir)
    
    # Clear any cached presets to ensure isolation
    original_init = PresetManager.__init__
    def patched_init(self):
        original_init(self)
        self._custom_presets_cache = None
    monkeypatch.setattr(PresetManager, '__init__', patched_init)
    
    yield temp_presets_dir


class TestPresetManager:
    """Test cases for PresetManager preset functionality."""

    def test_get_vintage_preset(self):
        """Test getting the built-in vintage preset."""
        preset_manager = PresetManager()
        vintage_preset = preset_manager.get_preset("vintage")
        
        assert isinstance(vintage_preset, PresetConfig)
        assert vintage_preset.name == "vintage"
        assert vintage_preset.description == "Classic film effects with jitter, grain, and vintage color"
        
        # Check layout configuration
        assert vintage_preset.layout["type"] == "random"
        assert vintage_preset.layout["config"]["overlap_allowed"] is False
        assert vintage_preset.layout["config"]["margin"] == 0.1
        assert vintage_preset.layout["config"]["seed"] == 1950
        
        # Check animations
        assert len(vintage_preset.animations) == 6
        animation_types = [anim["type"] for anim in vintage_preset.animations]
        assert "shake" in animation_types
        assert "jitter" in animation_types
        assert "brightness_flicker" in animation_types
        assert "black_white" in animation_types
        assert "film_grain" in animation_types
        assert "vintage_color" in animation_types

    def test_get_multi_pip_preset(self):
        """Test getting the built-in multi-pip preset."""
        preset_manager = PresetManager()
        multi_pip_preset = preset_manager.get_preset("multi-pip")
        
        assert isinstance(multi_pip_preset, PresetConfig)
        assert multi_pip_preset.name == "multi-pip"
        assert "main cameras" in multi_pip_preset.description.lower()
        
        # Check layout configuration
        assert multi_pip_preset.layout["type"] == "main-pip"
        assert multi_pip_preset.layout["config"]["pip_scale"] == 0.25
        assert multi_pip_preset.layout["config"]["margin_percent"] == 0.08
        
        # Check animations - should have multiple strips with different animations
        assert len(multi_pip_preset.animations) >= 6
        animation_types = [anim["type"] for anim in multi_pip_preset.animations]
        assert "scale" in animation_types
        assert "shake" in animation_types
        assert "brightness_flicker" in animation_types


    def test_list_presets(self):
        """Test listing all available presets."""
        preset_manager = PresetManager()
        presets = preset_manager.list_presets()
        
        assert isinstance(presets, list)
        assert len(presets) >= 3  # At least 3 built-in presets
        assert "vintage" in presets
        assert "multi-pip" in presets
        assert "minimal" in presets

    def test_get_nonexistent_preset(self):
        """Test getting a preset that doesn't exist."""
        preset_manager = PresetManager()
        
        with pytest.raises(ValueError, match="Preset 'nonexistent' not found"):
            preset_manager.get_preset("nonexistent")

    def test_create_custom_preset(self):
        """Test creating a custom preset."""
        preset_manager = PresetManager()
        
        # Create custom preset configuration
        custom_config = {
            "layout": {
                "type": "random",
                "config": {"seed": 123, "margin": 0.08}
            },
            "animations": [
                {
                    "type": "scale",
                    "trigger": "bass",
                    "intensity": 0.2,
                    "duration_frames": 3
                }
            ]
        }
        
        # Create custom preset
        preset_manager.create_custom_preset("my-style", custom_config, "My custom style")
        
        # Verify it can be retrieved
        custom_preset = preset_manager.get_preset("my-style")
        assert custom_preset.name == "my-style"
        assert custom_preset.description == "My custom style"
        assert custom_preset.layout["config"]["seed"] == 123
        assert len(custom_preset.animations) == 1

    def test_create_custom_preset_overwrites_existing(self):
        """Test that creating custom preset overwrites existing custom preset."""
        preset_manager = PresetManager()
        
        # Create first version
        config1 = {
            "layout": {"type": "random", "config": {"seed": 100}},
            "animations": [{"type": "scale", "trigger": "bass", "intensity": 0.1}]
        }
        preset_manager.create_custom_preset("test-preset", config1, "Test v1")
        
        # Create second version (should overwrite)
        config2 = {
            "layout": {"type": "random", "config": {"seed": 200}},
            "animations": [{"type": "shake", "trigger": "beat", "intensity": 5.0}]
        }
        preset_manager.create_custom_preset("test-preset", config2, "Test v2")
        
        # Verify only the second version exists
        preset = preset_manager.get_preset("test-preset")
        assert preset.description == "Test v2"
        assert preset.layout["config"]["seed"] == 200
        assert preset.animations[0]["type"] == "shake"

    def test_cannot_overwrite_builtin_preset(self):
        """Test that built-in presets cannot be overwritten."""
        preset_manager = PresetManager()
        
        custom_config = {
            "layout": {"type": "random", "config": {"seed": 999}},
            "animations": []
        }
        
        with pytest.raises(ValueError, match="Cannot overwrite built-in preset 'vintage'"):
            preset_manager.create_custom_preset("vintage", custom_config, "Modified vintage")

    def test_custom_presets_persist_across_instances(self):
        """Test that custom presets persist across PresetManager instances."""
        # Create preset with first instance
        preset_manager1 = PresetManager()
        custom_config = {
            "layout": {"type": "random", "config": {"seed": 42}},
            "animations": [{"type": "rotation", "trigger": "beat", "degrees": 1.0}]
        }
        preset_manager1.create_custom_preset("persistent-test", custom_config, "Persistent test")
        
        # Access with second instance
        preset_manager2 = PresetManager()
        persistent_preset = preset_manager2.get_preset("persistent-test")
        
        assert persistent_preset.name == "persistent-test"
        assert persistent_preset.description == "Persistent test"
        assert persistent_preset.layout["config"]["seed"] == 42

    def test_preset_config_validation(self):
        """Test that preset configurations are validated."""
        preset_manager = PresetManager()
        
        # Invalid configuration (missing required fields)
        invalid_config = {
            "animations": []  # Missing layout
        }
        
        with pytest.raises(ValueError, match="Invalid preset configuration"):
            preset_manager.create_custom_preset("invalid", invalid_config, "Invalid preset")

    def test_preset_config_structure(self):
        """Test the structure of PresetConfig objects."""
        preset_manager = PresetManager()
        vintage_preset = preset_manager.get_preset("vintage")
        
        # Test PresetConfig attributes
        assert hasattr(vintage_preset, 'name')
        assert hasattr(vintage_preset, 'description')
        assert hasattr(vintage_preset, 'layout')
        assert hasattr(vintage_preset, 'animations')
        
        # Test layout structure
        assert isinstance(vintage_preset.layout, dict)
        assert "type" in vintage_preset.layout
        assert "config" in vintage_preset.layout
        
        # Test animations structure
        assert isinstance(vintage_preset.animations, list)
        for animation in vintage_preset.animations:
            assert isinstance(animation, dict)
            assert "type" in animation
            assert "trigger" in animation


    def test_minimal_preset_has_basic_effects(self):
        """Test that minimal preset has only basic effects."""
        preset_manager = PresetManager()
        minimal_preset = preset_manager.get_preset("minimal")
        
        # Should have only basic scale animation
        assert len(minimal_preset.animations) == 1
        assert minimal_preset.animations[0]["type"] == "scale"
        assert minimal_preset.animations[0]["trigger"] == "bass"


    @pytest.fixture
    def temp_presets_dir(self):
        """Create temporary directory for custom presets."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_custom_presets_directory_creation(self, temp_presets_dir):
        """Test that custom presets directory is created if it doesn't exist."""
        # Use temporary directory that doesn't exist yet
        nonexistent_dir = temp_presets_dir / "custom_presets"
        
        with patch('blender.config.preset_manager.PresetManager._get_custom_presets_dir', return_value=nonexistent_dir):
            preset_manager = PresetManager()
            
            custom_config = {
                "layout": {"type": "random", "config": {"seed": 123}},
                "animations": [{"type": "scale", "trigger": "bass", "intensity": 0.2}]
            }
            
            preset_manager.create_custom_preset("test-creation", custom_config, "Test directory creation")
            
            # Verify directory was created
            assert nonexistent_dir.exists()
            assert nonexistent_dir.is_dir()

    def test_corrupt_custom_preset_file_handling(self, temp_presets_dir):
        """Test handling of corrupt custom preset files."""
        custom_presets_dir = temp_presets_dir / "custom_presets"
        custom_presets_dir.mkdir()
        
        # Create corrupt preset file
        corrupt_file = custom_presets_dir / "corrupt-preset.json"
        corrupt_file.write_text("invalid json content")
        
        with patch('blender.config.preset_manager.PresetManager._get_custom_presets_dir', return_value=custom_presets_dir):
            preset_manager = PresetManager()
            
            # Should not include corrupt preset in list
            presets = preset_manager.list_presets()
            assert "corrupt-preset" not in presets
            
            # Should raise error when trying to get corrupt preset
            with pytest.raises(ValueError, match="Preset 'corrupt-preset' not found"):
                preset_manager.get_preset("corrupt-preset")