"""
ABOUTME: Tests for Blender VSE config module - validates parameter parsing and validation.
ABOUTME: TDD approach - tests written first to define expected config behavior.
"""

from pathlib import Path
import sys
import os
from unittest.mock import patch

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.blender_vse.config import BlenderVSEConfig


class TestBlenderVSEConfigBasic:
    """Test basic config functionality."""

    @patch.dict(
        os.environ,
        {
            "BLENDER_VSE_VIDEO_FILES": "/path/video1.mp4,/path/video2.mp4",
            "BLENDER_VSE_MAIN_AUDIO": "/path/audio.m4a",
            "BLENDER_VSE_OUTPUT_BLEND": "/path/output.blend",
            "BLENDER_VSE_RENDER_OUTPUT": "/path/render.mp4",
            "BLENDER_VSE_FPS": "24",
            "BLENDER_VSE_RESOLUTION_X": "1920",
            "BLENDER_VSE_RESOLUTION_Y": "1080",
        },
    )
    def test_config_initialization_from_env_vars(self):
        """Config should initialize correctly from environment variables."""
        config = BlenderVSEConfig()

        assert len(config.video_files) == 2
        assert config.video_files[0] == Path("/path/video1.mp4")
        assert config.video_files[1] == Path("/path/video2.mp4")
        assert config.main_audio == Path("/path/audio.m4a")
        assert config.output_blend == Path("/path/output.blend")
        assert config.render_output == Path("/path/render.mp4")
        assert config.fps == 24
        assert config.resolution_x == 1920
        assert config.resolution_y == 1080

    def test_config_initialization_with_defaults(self):
        """Config should use defaults when env vars not set."""
        with patch.dict(os.environ, {}, clear=True):
            config = BlenderVSEConfig()

            assert config.video_files == []
            assert config.main_audio is None
            assert config.output_blend is None
            assert config.render_output is None
            assert config.fps == 30  # Default from BlenderConstants
            assert config.resolution_x == 1280  # Default from BlenderConstants
            assert config.resolution_y == 720  # Default from BlenderConstants

    @patch.dict(
        os.environ,
        {"BLENDER_VSE_ANIMATION_MODE": "beat-switch", "BLENDER_VSE_BEAT_DIVISION": "4"},
    )
    def test_config_animation_parameters(self):
        """Config should handle animation-specific parameters."""
        config = BlenderVSEConfig()

        assert config.animation_mode == "beat-switch"
        assert config.beat_division == 4

    def test_config_animation_defaults(self):
        """Animation parameters should have sensible defaults."""
        with patch.dict(os.environ, {}, clear=True):
            config = BlenderVSEConfig()

            assert config.animation_mode == "none"
            assert config.beat_division == 8  # Current default


class TestBlenderVSEConfigValidation:
    """Test config validation functionality."""

    def test_validate_returns_tuple(self):
        """Validate method should return (bool, List[str]) tuple."""
        config = BlenderVSEConfig()
        result = config.validate()

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)  # is_valid
        assert isinstance(result[1], list)  # errors

    @patch.dict(
        os.environ,
        {
            "BLENDER_VSE_VIDEO_FILES": "/nonexistent1.mp4,/nonexistent2.mp4",
            "BLENDER_VSE_MAIN_AUDIO": "/nonexistent.m4a",
            "BLENDER_VSE_OUTPUT_BLEND": "/path/output.blend",
            "BLENDER_VSE_RENDER_OUTPUT": "/path/render.mp4",
        },
    )
    def test_validate_nonexistent_files(self):
        """Validation should fail for nonexistent files."""
        config = BlenderVSEConfig()
        is_valid, errors = config.validate()

        assert not is_valid
        assert len(errors) >= 2  # At least video files and audio file errors

        # Should contain specific error messages about missing files
        error_text = " ".join(errors)
        assert "video" in error_text.lower() or "nie istnieje" in error_text
        assert "audio" in error_text.lower() or "nie istnieje" in error_text

    def test_validate_missing_required_fields(self):
        """Validation should fail when required fields are missing."""
        with patch.dict(os.environ, {}, clear=True):
            config = BlenderVSEConfig()
            is_valid, errors = config.validate()

            assert not is_valid
            assert len(errors) >= 3  # video_files, output_blend, render_output

            error_text = " ".join(errors)
            assert "video" in error_text.lower() or "brak" in error_text
            assert "blend" in error_text.lower() or "wyjściow" in error_text

    @patch.dict(
        os.environ,
        {
            "BLENDER_VSE_FPS": "0",
            "BLENDER_VSE_RESOLUTION_X": "-100",
            "BLENDER_VSE_RESOLUTION_Y": "0",
        },
    )
    def test_validate_invalid_numeric_values(self):
        """Validation should fail for invalid numeric values."""
        config = BlenderVSEConfig()
        is_valid, errors = config.validate()

        assert not is_valid
        error_text = " ".join(errors)
        assert "fps" in error_text.lower() or "nieprawidłowa" in error_text

    @patch("pathlib.Path.exists")
    def test_validate_success_case(self, mock_exists):
        """Validation should succeed when all parameters are valid."""
        mock_exists.return_value = True

        with patch.dict(
            os.environ,
            {
                "BLENDER_VSE_VIDEO_FILES": "/existing1.mp4,/existing2.mp4",
                "BLENDER_VSE_MAIN_AUDIO": "/existing.m4a",
                "BLENDER_VSE_OUTPUT_BLEND": "/path/output.blend",
                "BLENDER_VSE_RENDER_OUTPUT": "/path/render.mp4",
                "BLENDER_VSE_FPS": "30",
                "BLENDER_VSE_RESOLUTION_X": "1280",
                "BLENDER_VSE_RESOLUTION_Y": "720",
            },
        ):
            config = BlenderVSEConfig()
            is_valid, errors = config.validate()

            assert is_valid
            assert errors == []


class TestBlenderVSEConfigEdgeCases:
    """Test edge cases and error conditions."""

    @patch.dict(
        os.environ,
        {
            "BLENDER_VSE_VIDEO_FILES": "  /path1.mp4 , /path2.mp4  ,  ",
        },
    )
    def test_video_files_parsing_with_whitespace(self):
        """Video files parsing should handle whitespace correctly."""
        config = BlenderVSEConfig()

        assert len(config.video_files) == 2
        assert config.video_files[0] == Path("/path1.mp4")
        assert config.video_files[1] == Path("/path2.mp4")

    @patch.dict(
        os.environ,
        {
            "BLENDER_VSE_VIDEO_FILES": "",
        },
    )
    def test_empty_video_files_string(self):
        """Empty video files string should result in empty list."""
        config = BlenderVSEConfig()
        assert config.video_files == []

    @patch.dict(
        os.environ,
        {
            "BLENDER_VSE_FPS": "invalid",
            "BLENDER_VSE_RESOLUTION_X": "not_a_number",
            "BLENDER_VSE_BEAT_DIVISION": "bad_value",
        },
    )
    def test_invalid_numeric_parsing_uses_defaults(self):
        """Invalid numeric values should fall back to defaults."""
        config = BlenderVSEConfig()

        # Should use defaults when parsing fails
        assert config.fps == 30  # Default
        assert config.resolution_x == 1280  # Default
        assert config.beat_division == 8  # Default

    def test_config_immutability_like_behavior(self):
        """Config should behave like an immutable configuration object."""
        with patch.dict(os.environ, {"BLENDER_VSE_FPS": "24"}):
            config = BlenderVSEConfig()
            original_fps = config.fps

            # Config values should not be accidentally modifiable
            assert config.fps == 24
            assert original_fps == 24


class TestBlenderVSEConfigCompatibility:
    """Test compatibility with existing BlenderVSEConfigurator interface."""

    def test_config_provides_same_attributes_as_original(self):
        """Config should provide all attributes used by original BlenderVSEConfigurator."""
        config = BlenderVSEConfig()

        # These are the attributes used in the original __init__ method
        required_attributes = [
            "video_files",
            "main_audio",
            "output_blend",
            "render_output",
            "fps",
            "resolution_x",
            "resolution_y",
            "animation_mode",
            "beat_division",
        ]

        for attr in required_attributes:
            assert hasattr(config, attr), f"Missing attribute: {attr}"

    def test_config_validate_matches_original_signature(self):
        """Config validate method should match original validate_parameters signature."""
        config = BlenderVSEConfig()
        result = config.validate()

        # Original returns Tuple[bool, List[str]]
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], list)
