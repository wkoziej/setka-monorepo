# ABOUTME: Tests for PresetManager configuration preset functionality
# ABOUTME: Tests built-in presets, custom preset creation, and preset validation

"""Tests for PresetManager class."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from setka_common.config.yaml_config import BlenderYAMLConfig

from cinemon.config.preset_manager import PresetManager


@pytest.fixture
def test_preset_dir():
    """Return path to test fixtures preset directory."""
    return Path(__file__).parent / "fixtures" / "presets"


@pytest.fixture
def preset_manager(test_preset_dir, tmp_path, monkeypatch):
    """Create PresetManager instance configured to use test fixtures."""
    # Create isolated temp directory for custom presets
    temp_custom_presets_dir = tmp_path / "custom_presets"
    temp_custom_presets_dir.mkdir()

    # Mock the custom presets directory method to use temp directory
    monkeypatch.setattr(
        PresetManager, "_get_custom_presets_dir", lambda self: temp_custom_presets_dir
    )

    # Create PresetManager with test fixture preset directory
    manager = PresetManager(preset_dir=test_preset_dir)
    return manager


class TestPresetManager:
    """Test cases for PresetManager preset functionality."""

    def test_get_test_minimal_preset(self, preset_manager):
        """Test getting the test minimal preset from fixtures."""
        minimal_preset = preset_manager.get_preset("test_minimal")

        assert isinstance(minimal_preset, BlenderYAMLConfig)

        # Check layout configuration (from test fixture)
        assert minimal_preset.layout.type == "random"
        assert minimal_preset.layout.config["overlap_allowed"] is False
        assert minimal_preset.layout.config["margin"] == 0.15
        assert minimal_preset.layout.config["seed"] == 42

        # Check strip_animations - test fixture has generic Camera1/Camera2
        assert "Camera1" in minimal_preset.strip_animations
        assert "Camera2" in minimal_preset.strip_animations

        # Check Camera1 animations
        camera1_anims = minimal_preset.strip_animations["Camera1"]
        assert len(camera1_anims) == 1
        assert camera1_anims[0]["type"] == "scale"
        assert camera1_anims[0]["trigger"] == "beat"
        assert camera1_anims[0]["intensity"] == 0.2

    def test_get_camera2_animations(self, preset_manager):
        """Test Camera2 animations from test fixture."""
        minimal_preset = preset_manager.get_preset("test_minimal")

        assert isinstance(minimal_preset, BlenderYAMLConfig)

        # Check Camera2 animations (from test fixture)
        assert "Camera2" in minimal_preset.strip_animations
        camera2_anims = minimal_preset.strip_animations["Camera2"]
        assert len(camera2_anims) == 1
        assert camera2_anims[0]["type"] == "shake"
        assert camera2_anims[0]["trigger"] == "energy_peaks"
        assert camera2_anims[0]["intensity"] == 1.0
        assert camera2_anims[0]["return_frames"] == 2

    def test_list_presets(self, preset_manager):
        """Test listing all available presets from fixtures."""
        presets = preset_manager.list_presets()

        assert isinstance(presets, list)
        assert len(presets) >= 1  # At least 1 test preset
        assert "test_minimal" in presets

    def test_get_nonexistent_preset(self, preset_manager):
        """Test getting a preset that doesn't exist."""
        with pytest.raises(ValueError, match="Preset 'nonexistent' not found"):
            preset_manager.get_preset("nonexistent")

    def test_preset_config_structure(self, preset_manager):
        """Test the structure of BlenderYAMLConfig objects."""
        minimal_preset = preset_manager.get_preset("test_minimal")

        # Test BlenderYAMLConfig attributes
        assert hasattr(minimal_preset, "project")
        assert hasattr(minimal_preset, "audio_analysis")
        assert hasattr(minimal_preset, "layout")
        assert hasattr(minimal_preset, "strip_animations")

        # Test layout structure
        assert hasattr(minimal_preset.layout, "type")
        assert hasattr(minimal_preset.layout, "config")

        # Test strip_animations structure
        assert isinstance(minimal_preset.strip_animations, dict)
        for strip_name, animations in minimal_preset.strip_animations.items():
            assert isinstance(animations, list)
            for animation in animations:
                assert isinstance(animation, dict)
                assert "type" in animation
                assert "trigger" in animation

    def test_test_minimal_preset_has_basic_effects(self, preset_manager):
        """Test that test minimal preset has only basic effects."""
        minimal_preset = preset_manager.get_preset("test_minimal")

        # Should have strip_animations
        assert hasattr(minimal_preset, "strip_animations")
        strip_anims = minimal_preset.strip_animations

        # Check Camera1 has scale animation (from test fixture)
        assert "Camera1" in strip_anims
        assert len(strip_anims["Camera1"]) == 1
        assert strip_anims["Camera1"][0]["type"] == "scale"
        assert strip_anims["Camera1"][0]["trigger"] == "beat"
        assert strip_anims["Camera1"][0]["easing"] == "EASE_IN_OUT"

    def test_test_minimal_audio_analysis_config(self, preset_manager):
        """Test audio analysis configuration in test fixture."""
        minimal_preset = preset_manager.get_preset("test_minimal")

        assert isinstance(minimal_preset, BlenderYAMLConfig)

        # Check audio analysis configuration (from test fixture)
        assert hasattr(minimal_preset, "audio_analysis")
        assert (
            minimal_preset.audio_analysis.file == "./analysis/main_audio_analysis.json"
        )
        assert minimal_preset.audio_analysis.beat_division == 4
        assert minimal_preset.audio_analysis.min_onset_interval == 2.0

    def test_corrupt_custom_preset_file_handling(
        self, test_preset_dir, tmp_path, monkeypatch
    ):
        """Test handling of corrupt custom preset files."""
        custom_presets_dir = tmp_path / "custom_presets"
        custom_presets_dir.mkdir()

        # Create corrupt preset file
        corrupt_file = custom_presets_dir / "corrupt-preset.json"
        corrupt_file.write_text("invalid json content")

        # Mock the custom presets directory method to use temp directory
        monkeypatch.setattr(
            PresetManager, "_get_custom_presets_dir", lambda self: custom_presets_dir
        )

        # Create PresetManager with test fixture preset directory
        preset_manager = PresetManager(preset_dir=test_preset_dir)

        # Should not include corrupt preset in list
        presets = preset_manager.list_presets()
        assert "corrupt-preset" not in presets

        # Should raise error when trying to get corrupt preset
        with pytest.raises(ValueError, match="Preset 'corrupt-preset' not found"):
            preset_manager.get_preset("corrupt-preset")
