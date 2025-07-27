# ABOUTME: Additional edge case tests for YAMLConfigLoader
# ABOUTME: Tests boundary conditions and error scenarios

"""Additional edge case tests for YAML configuration loader."""

import sys
from pathlib import Path

import pytest

# Add blender_addon to path
addon_path = Path(__file__).parent.parent.parent / "blender_addon"
if str(addon_path) not in sys.path:
    sys.path.insert(0, str(addon_path))


class TestYAMLConfigLoaderErrorHandling:
    """Test error handling and boundary conditions."""

    def test_empty_video_files_list_allowed(self):
        """Test that empty video files list is allowed for auto-discovery."""
        from config_loader import YAMLConfigLoader

        config = """
project:
  video_files: []
  fps: 30
layout:
  type: "random"
strip_animations: {}
"""
        loader = YAMLConfigLoader()
        result = loader.load_from_string(config)
        assert result.project.video_files == []

    def test_invalid_fps_values(self):
        """Test validation fails for invalid FPS values."""
        from config_loader import ValidationError, YAMLConfigLoader

        # Negative FPS
        config_negative = """
project:
  video_files: [test.mp4]
  fps: -30
layout:
  type: "random"
strip_animations: {}
"""
        loader = YAMLConfigLoader()
        with pytest.raises(ValidationError, match="fps must be a positive integer"):
            loader.load_from_string(config_negative)

        # Zero FPS
        config_zero = """
project:
  video_files: [test.mp4]
  fps: 0
layout:
  type: "random"
strip_animations: {}
"""
        with pytest.raises(ValidationError, match="fps must be a positive integer"):
            loader.load_from_string(config_zero)

        # Non-integer FPS
        config_float = """
project:
  video_files: [test.mp4]
  fps: 30.5
layout:
  type: "random"
strip_animations: {}
"""
        with pytest.raises(ValidationError, match="fps must be a positive integer"):
            loader.load_from_string(config_float)

    def test_incomplete_resolution(self):
        """Test validation fails for incomplete resolution."""
        from config_loader import ValidationError, YAMLConfigLoader

        config = """
project:
  video_files: [test.mp4]
  fps: 30
  resolution:
    width: 1920
    # Missing height
layout:
  type: "random"
strip_animations: {}
"""
        loader = YAMLConfigLoader()
        with pytest.raises(
            ValidationError, match="Resolution must have width and height"
        ):
            loader.load_from_string(config)

    def test_invalid_strip_animations_format(self):
        """Test validation fails for invalid strip animations format."""
        from config_loader import ValidationError, YAMLConfigLoader

        # Strip animations as string instead of list
        config = """
project:
  video_files: [test.mp4]
  fps: 30
layout:
  type: "random"
strip_animations:
  Camera1: "invalid"
"""
        loader = YAMLConfigLoader()
        with pytest.raises(
            ValidationError, match="Animations for strip 'Camera1' must be a list"
        ):
            loader.load_from_string(config)

    def test_animation_missing_required_fields(self):
        """Test validation fails for animations missing required fields."""
        from config_loader import ValidationError, YAMLConfigLoader

        # Missing type
        config_no_type = """
project:
  video_files: [test.mp4]
  fps: 30
layout:
  type: "random"
strip_animations:
  Camera1:
    - trigger: "beat"
      intensity: 0.3
"""
        loader = YAMLConfigLoader()
        with pytest.raises(
            ValidationError,
            match="Animation for strip 'Camera1' missing required field: type",
        ):
            loader.load_from_string(config_no_type)

        # Missing trigger
        config_no_trigger = """
project:
  video_files: [test.mp4]
  fps: 30
layout:
  type: "random"
strip_animations:
  Camera1:
    - type: "scale"
      intensity: 0.3
"""
        with pytest.raises(
            ValidationError,
            match="Animation for strip 'Camera1' missing required field: trigger",
        ):
            loader.load_from_string(config_no_trigger)

    def test_nonexistent_file_loading(self):
        """Test error handling for nonexistent files."""
        from config_loader import ValidationError, YAMLConfigLoader

        loader = YAMLConfigLoader()
        with pytest.raises(ValidationError, match="Configuration file not found"):
            loader.load_from_file("/nonexistent/path/config.yaml")

    def test_none_yaml_content(self):
        """Test handling of None/empty YAML content."""
        from config_loader import ValidationError, YAMLConfigLoader

        loader = YAMLConfigLoader()

        # Completely empty content
        with pytest.raises(ValidationError, match="Empty YAML configuration"):
            loader.load_from_string("")

        # YAML that parses to None
        with pytest.raises(ValidationError, match="Empty YAML configuration"):
            loader.load_from_string("---")


class TestYAMLConfigLoaderBoundaryValues:
    """Test boundary values and limits."""

    def test_many_video_files(self):
        """Test handling many video files."""
        from config_loader import YAMLConfigLoader

        # Generate config with many video files
        video_files = [f"camera{i}.mp4" for i in range(100)]
        video_files_yaml = str(video_files).replace("'", '"')

        config = f"""
project:
  video_files: {video_files_yaml}
  fps: 30
layout:
  type: "grid"
  config:
    rows: 10
    cols: 10
strip_animations: {{}}
"""
        loader = YAMLConfigLoader()
        result = loader.load_from_string(config)
        assert len(result.project.video_files) == 100

    def test_many_animations_per_strip(self):
        """Test handling many animations per strip."""
        from config_loader import YAMLConfigLoader

        # Generate many animations for one strip
        animations = []
        for i in range(50):
            animations.append(f"""    - type: "scale"
      trigger: "beat"
      intensity: {0.1 + i * 0.01}""")

        animations_yaml = "\n".join(animations)

        config = f"""
project:
  video_files: [test.mp4]
  fps: 30
layout:
  type: "random"
strip_animations:
  test:
{animations_yaml}
"""
        loader = YAMLConfigLoader()
        result = loader.load_from_string(config)
        assert len(result.strip_animations["test"]) == 50

    def test_very_long_strip_names(self):
        """Test handling very long strip names."""
        from config_loader import YAMLConfigLoader

        long_name = "a" * 1000  # Very long strip name

        config = f"""
project:
  video_files: [test.mp4]
  fps: 30
layout:
  type: "random"
strip_animations:
  "{long_name}":
    - type: "scale"
      trigger: "beat"
      intensity: 0.3
"""
        loader = YAMLConfigLoader()
        result = loader.load_from_string(config)
        assert long_name in result.strip_animations


class TestYAMLConfigLoaderSpecialCharacters:
    """Test handling of special characters and encodings."""

    def test_special_characters_in_filenames(self):
        """Test handling special characters in file names."""
        from config_loader import YAMLConfigLoader

        config = """
project:
  video_files: ["file with spaces.mp4", "file-with-dashes.mp4", "file_with_underscores.mp4"]
  main_audio: "audio (1).m4a"
  fps: 30
layout:
  type: "random"
strip_animations:
  "file with spaces":
    - type: "scale"
      trigger: "beat"
      intensity: 0.3
"""
        loader = YAMLConfigLoader()
        result = loader.load_from_string(config)
        assert len(result.project.video_files) == 3
        assert "file with spaces" in result.strip_animations

    def test_unicode_strip_names(self):
        """Test handling Unicode characters in strip names."""
        from config_loader import YAMLConfigLoader

        config = """
project:
  video_files: [test.mp4]
  fps: 30
layout:
  type: "random"
strip_animations:
  "🎥 Camera główna":
    - type: "scale"
      trigger: "beat"
      intensity: 0.3
  "Ekran 😊":
    - type: "shake"
      trigger: "energy_peaks"
      intensity: 1.0
"""
        loader = YAMLConfigLoader()
        result = loader.load_from_string(config)
        assert "🎥 Camera główna" in result.strip_animations
        assert "Ekran 😊" in result.strip_animations


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
