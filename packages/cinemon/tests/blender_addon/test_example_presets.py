# ABOUTME: Test loading of example preset files in new YAML format
# ABOUTME: Validates that all example presets are syntactically correct

"""Test example preset files for correct YAML format and validation."""

import sys
from pathlib import Path

import pytest

# Add blender_addon to path
addon_path = Path(__file__).parent.parent.parent / "blender_addon"
if str(addon_path) not in sys.path:
    sys.path.insert(0, str(addon_path))


class TestExamplePresets:
    """Test all example preset files."""

    def test_vintage_preset_loads(self):
        """Test that vintage preset loads correctly."""
        from config_loader import YAMLConfigLoader

        preset_path = addon_path / "example_presets" / "vintage.yaml"
        assert preset_path.exists(), f"Vintage preset not found at {preset_path}"

        loader = YAMLConfigLoader()
        config = loader.load_from_file(preset_path)

        # Verify basic structure
        assert config.project.fps == 30
        assert config.layout.type == "random"
        assert "Camera1" in config.strip_animations
        assert "Camera2" in config.strip_animations

        # Verify vintage-specific settings
        camera1_animations = config.strip_animations["Camera1"]
        has_vintage_color = any(anim["type"] == "vintage_color" for anim in camera1_animations)
        assert has_vintage_color, "Vintage preset should have vintage_color animation"

    def test_multi_pip_preset_loads(self):
        """Test that multi-pip preset loads correctly."""
        from config_loader import YAMLConfigLoader

        preset_path = addon_path / "example_presets" / "multi-pip.yaml"
        assert preset_path.exists(), f"Multi-pip preset not found at {preset_path}"

        loader = YAMLConfigLoader()
        config = loader.load_from_file(preset_path)

        # Verify basic structure
        assert config.project.fps == 30
        assert config.layout.type == "main-pip"
        assert "Video_1" in config.strip_animations
        assert "Video_2" in config.strip_animations

        # Verify multi-pip specific settings
        video1_animations = config.strip_animations["Video_1"]
        has_scale = any(anim["type"] == "scale" for anim in video1_animations)
        assert has_scale, "Multi-pip preset should have scale animation"

    def test_minimal_preset_loads(self):
        """Test that minimal preset loads correctly."""
        from config_loader import YAMLConfigLoader

        preset_path = addon_path / "example_presets" / "minimal.yaml"
        assert preset_path.exists(), f"Minimal preset not found at {preset_path}"

        loader = YAMLConfigLoader()
        config = loader.load_from_file(preset_path)

        # Verify basic structure
        assert config.project.fps == 30
        assert config.layout.type == "cascade"
        assert "Camera1" in config.strip_animations

        # Verify minimal-specific settings (low intensity)
        camera1_animations = config.strip_animations["Camera1"]
        scale_animation = next((anim for anim in camera1_animations if anim["type"] == "scale"), None)
        assert scale_animation is not None
        assert scale_animation["intensity"] <= 0.2, "Minimal preset should have low intensity animations"


    def test_all_presets_convert_to_internal(self):
        """Test that all presets convert to internal format correctly."""
        from config_loader import YAMLConfigLoader

        preset_files = [
            "vintage.yaml",
            "multi-pip.yaml",
            "minimal.yaml"
        ]

        loader = YAMLConfigLoader()

        for preset_file in preset_files:
            preset_path = addon_path / "example_presets" / preset_file
            config = loader.load_from_file(preset_path)

            # Convert to internal format
            internal_format = loader.convert_to_internal(config)

            # Verify internal format structure
            assert "project" in internal_format
            assert "layout" in internal_format
            assert "animations" in internal_format
            assert "audio_analysis" in internal_format

            # Verify project section
            assert "video_files" in internal_format["project"]
            assert "fps" in internal_format["project"]

            print(f"✓ {preset_file} converts to internal format correctly")

    def test_preset_files_exist(self):
        """Test that all expected preset files exist."""
        expected_presets = [
            "vintage.yaml",
            "multi-pip.yaml",
            "minimal.yaml"
        ]

        presets_dir = addon_path / "example_presets"
        assert presets_dir.exists(), f"Example presets directory not found: {presets_dir}"

        for preset_name in expected_presets:
            preset_path = presets_dir / preset_name
            assert preset_path.exists(), f"Expected preset file not found: {preset_path}"

    def test_presets_have_different_characteristics(self):
        """Test that presets have different characteristics as expected."""
        from config_loader import YAMLConfigLoader

        loader = YAMLConfigLoader()

        # Load all presets
        vintage = loader.load_from_file(addon_path / "example_presets" / "vintage.yaml")
        multi_pip = loader.load_from_file(addon_path / "example_presets" / "multi-pip.yaml")
        minimal = loader.load_from_file(addon_path / "example_presets" / "minimal.yaml")

        # Verify different FPS settings
        assert vintage.project.fps == 30
        assert multi_pip.project.fps == 30
        assert minimal.project.fps == 30

        # Verify different layout types
        assert vintage.layout.type == "random"
        assert multi_pip.layout.type == "main-pip"
        assert minimal.layout.type == "cascade"

        # Verify different audio analysis settings
        assert vintage.audio_analysis.beat_division == 4
        assert multi_pip.audio_analysis.beat_division == 4
        assert minimal.audio_analysis.min_onset_interval == 2.0  # Less frequent


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
