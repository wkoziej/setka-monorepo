# ABOUTME: Tests for PresetManager configuration preset functionality
# ABOUTME: Tests built-in presets, custom preset creation, and preset validation

"""Tests for PresetManager class."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from setka_common.config.yaml_config import BlenderYAMLConfig

from cinemon.config.preset_manager import PresetManager


@pytest.fixture(autouse=True)
def isolated_custom_presets(tmp_path, monkeypatch):
    """Ensure each test uses isolated temporary directory for custom presets."""
    temp_presets_dir = tmp_path / "custom_presets"
    temp_presets_dir.mkdir()

    # Mock the custom presets directory method
    monkeypatch.setattr(
        PresetManager, "_get_custom_presets_dir", lambda self: temp_presets_dir
    )

    # Clear any cached presets to ensure isolation
    original_init = PresetManager.__init__

    def patched_init(self):
        original_init(self)
        self._custom_presets_cache = None

    monkeypatch.setattr(PresetManager, "__init__", patched_init)

    yield temp_presets_dir


class TestPresetManager:
    """Test cases for PresetManager preset functionality."""

    def test_get_vintage_preset(self):
        """Test getting the built-in vintage preset."""
        preset_manager = PresetManager()
        vintage_preset = preset_manager.get_preset("vintage")

        assert isinstance(vintage_preset, BlenderYAMLConfig)

        # Check layout configuration
        assert vintage_preset.layout.type == "random"
        assert vintage_preset.layout.config["overlap_allowed"] is False
        assert vintage_preset.layout.config["margin"] == 0.1
        assert vintage_preset.layout.config["seed"] == 42  # From YAML file

        # Check strip_animations
        assert "Camera1" in vintage_preset.strip_animations
        assert "Camera2" in vintage_preset.strip_animations

        # Check Camera1 animations
        camera1_anims = vintage_preset.strip_animations["Camera1"]
        assert len(camera1_anims) == 2
        assert camera1_anims[0]["type"] == "scale"
        assert camera1_anims[0]["trigger"] == "beat"
        assert camera1_anims[1]["type"] == "vintage_color"
        assert camera1_anims[1]["trigger"] == "one_time"

    def test_get_music_video_preset(self):
        """Test getting the built-in music-video preset."""
        preset_manager = PresetManager()
        music_video_preset = preset_manager.get_preset("music-video")

        assert isinstance(music_video_preset, BlenderYAMLConfig)

        # Check layout configuration
        assert music_video_preset.layout.type == "grid"
        assert music_video_preset.layout.config["margin"] == 0.02

        # Check strip_animations - music-video has per-camera animations
        assert "Camera1" in music_video_preset.strip_animations
        assert "Camera2" in music_video_preset.strip_animations
        camera1_anims = music_video_preset.strip_animations["Camera1"]
        animation_types = [anim["type"] for anim in camera1_anims]
        assert "pip_switch" in animation_types
        assert "scale" in animation_types

    def test_list_presets(self):
        """Test listing all available presets."""
        preset_manager = PresetManager()
        presets = preset_manager.list_presets()

        assert isinstance(presets, list)
        assert len(presets) >= 4  # At least 4 built-in presets
        assert "vintage" in presets
        assert "music-video" in presets
        assert "minimal" in presets
        assert "beat-switch" in presets

    def test_get_nonexistent_preset(self):
        """Test getting a preset that doesn't exist."""
        preset_manager = PresetManager()

        with pytest.raises(ValueError, match="Preset 'nonexistent' not found"):
            preset_manager.get_preset("nonexistent")

    def test_preset_config_structure(self):
        """Test the structure of BlenderYAMLConfig objects."""
        preset_manager = PresetManager()
        vintage_preset = preset_manager.get_preset("vintage")

        # Test BlenderYAMLConfig attributes
        assert hasattr(vintage_preset, "project")
        assert hasattr(vintage_preset, "audio_analysis")
        assert hasattr(vintage_preset, "layout")
        assert hasattr(vintage_preset, "strip_animations")

        # Test layout structure
        assert hasattr(vintage_preset.layout, "type")
        assert hasattr(vintage_preset.layout, "config")

        # Test strip_animations structure
        assert isinstance(vintage_preset.strip_animations, dict)
        for strip_name, animations in vintage_preset.strip_animations.items():
            assert isinstance(animations, list)
            for animation in animations:
                assert isinstance(animation, dict)
                assert "type" in animation
                assert "trigger" in animation

    def test_minimal_preset_has_basic_effects(self):
        """Test that minimal preset has only basic effects."""
        preset_manager = PresetManager()
        minimal_preset = preset_manager.get_preset("minimal")

        # Should have strip_animations
        assert hasattr(minimal_preset, "strip_animations")
        strip_anims = minimal_preset.strip_animations

        # Check Camera1 has scale animation
        assert "Camera1" in strip_anims
        assert len(strip_anims["Camera1"]) == 1
        assert strip_anims["Camera1"][0]["type"] == "scale"
        assert strip_anims["Camera1"][0]["trigger"] == "beat"

    def test_beat_switch_legacy_preset(self):
        """Test that beat-switch preset provides legacy compatibility."""
        preset_manager = PresetManager()
        beat_switch_preset = preset_manager.get_preset("beat-switch")

        assert isinstance(beat_switch_preset, BlenderYAMLConfig)

        # Should have pip switching for cameras
        assert "Camera1" in beat_switch_preset.strip_animations
        camera1_anims = beat_switch_preset.strip_animations["Camera1"]
        assert any(anim["type"] == "pip_switch" for anim in camera1_anims)

    @pytest.fixture
    def temp_presets_dir(self):
        """Create temporary directory for custom presets."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_corrupt_custom_preset_file_handling(self, temp_presets_dir):
        """Test handling of corrupt custom preset files."""
        custom_presets_dir = temp_presets_dir / "custom_presets"
        custom_presets_dir.mkdir()

        # Create corrupt preset file
        corrupt_file = custom_presets_dir / "corrupt-preset.json"
        corrupt_file.write_text("invalid json content")

        with patch(
            "cinemon.config.preset_manager.PresetManager._get_custom_presets_dir",
            return_value=custom_presets_dir,
        ):
            preset_manager = PresetManager()

            # Should not include corrupt preset in list
            presets = preset_manager.list_presets()
            assert "corrupt-preset" not in presets

            # Should raise error when trying to get corrupt preset
            with pytest.raises(ValueError, match="Preset 'corrupt-preset' not found"):
                preset_manager.get_preset("corrupt-preset")
