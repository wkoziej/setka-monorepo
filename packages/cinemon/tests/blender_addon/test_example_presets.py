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

    def test_minimal_preset_loads(self):
        """Test that minimal preset loads correctly."""
        from setka_common.config import YAMLConfigLoader

        preset_path = addon_path / "example_presets" / "minimal.yaml"
        assert preset_path.exists(), f"Minimal preset not found at {preset_path}"

        loader = YAMLConfigLoader()
        config = loader.load_from_file(preset_path)

        # Verify basic structure
        assert config.project.fps == 30
        assert config.layout.type == "cascade"
        assert "RPI_FRONT.mp4" in config.strip_animations

        # Verify minimal-specific settings - using actual content from minimal.yaml
        rpi_front_animations = config.strip_animations["RPI_FRONT.mp4"]
        scale_animation = next(
            (anim for anim in rpi_front_animations if anim["type"] == "scale"), None
        )
        assert scale_animation is not None
        assert scale_animation["intensity"] == 2.0, (
            "Minimal preset scale animation should match file content"
        )

    def test_preset_files_exist(self):
        """Test that all expected preset files exist."""
        # Updated for issue #24 - only minimal.yaml exists
        expected_presets = [
            "minimal.yaml",
        ]

        presets_dir = addon_path / "example_presets"
        assert presets_dir.exists(), (
            f"Example presets directory not found: {presets_dir}"
        )

        for preset_name in expected_presets:
            preset_path = presets_dir / preset_name
            assert preset_path.exists(), (
                f"Expected preset file not found: {preset_path}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
