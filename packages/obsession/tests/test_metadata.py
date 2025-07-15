"""
Tests for metadata management functionality.
"""

import json
import time
import importlib
from unittest.mock import Mock, patch
from core.metadata import (
    create_metadata,
    validate_metadata,
    determine_source_capabilities,
)


class TestSourceCapabilitiesDetection:
    """Test source capabilities detection using OBS API."""

    def setup_method(self):
        """Reset module state before each test."""
        import sys
        import metadata

        # Only reload if module is already in sys.modules
        if 'metadata' in sys.modules:
            importlib.reload(metadata)

    def test_determine_source_capabilities_audio_only(self):
        """Test detection of audio-only source."""
        # Mock OBS source with only audio flag
        mock_source = Mock()
        mock_obs = Mock()
        mock_obs.obs_source_get_output_flags.return_value = 0x002  # OBS_SOURCE_AUDIO

        with patch("metadata.obs", mock_obs):
            result = determine_source_capabilities(mock_source)

            assert result == {"has_audio": True, "has_video": False}
            mock_obs.obs_source_get_output_flags.assert_called_once_with(mock_source)

    def test_determine_source_capabilities_video_only(self):
        """Test detection of video-only source."""
        mock_source = Mock()
        mock_obs = Mock()
        mock_obs.obs_source_get_output_flags.return_value = 0x001  # OBS_SOURCE_VIDEO

        with patch("metadata.obs", mock_obs):
            result = determine_source_capabilities(mock_source)

            assert result == {"has_audio": False, "has_video": True}

    def test_determine_source_capabilities_both(self):
        """Test detection of audio+video source."""
        mock_source = Mock()
        mock_obs = Mock()
        mock_obs.obs_source_get_output_flags.return_value = (
            0x003  # OBS_SOURCE_VIDEO | OBS_SOURCE_AUDIO
        )

        with patch("metadata.obs", mock_obs):
            result = determine_source_capabilities(mock_source)

            assert result == {"has_audio": True, "has_video": True}

    @patch("metadata.obs")
    def test_determine_source_capabilities_none(self, mock_obs):
        """Test detection of source with no audio/video."""
        mock_source = Mock()
        mock_obs.obs_source_get_output_flags.return_value = 0x000  # No flags

        result = determine_source_capabilities(mock_source)

        assert result == {"has_audio": False, "has_video": False}

    def test_determine_source_capabilities_none_source(self):
        """Test handling of None source."""
        result = determine_source_capabilities(None)
        assert result == {"has_audio": False, "has_video": False}

    def test_determine_source_capabilities_obs_none_fallback(self):
        """Test behavior when obs module is None (import failure scenario)."""
        # This test ensures that the function handles the case where obs import fails
        # It directly tests the fallback behavior that should occur

        # Mock the obs module to be None at the module level
        with patch("metadata.obs", None):
            mock_source = Mock()
            result = determine_source_capabilities(mock_source)

            # When obs is None, should return False for both capabilities
            assert result == {"has_audio": False, "has_video": False}

            # This test would catch the import bug because it verifies the fallback works


class TestMetadataWithCapabilities:
    """Test metadata creation with new has_audio/has_video fields."""

    def setup_method(self):
        """Reset module state before each test."""
        import sys
        import metadata

        # Only reload if module is already in sys.modules
        if 'metadata' in sys.modules:
            importlib.reload(metadata)

    def test_metadata_has_audio_video_flags(self):
        """Test that metadata contains has_audio and has_video fields."""
        sources = [
            {"name": "Camera", "x": 0, "y": 0, "obs_source": Mock()},
            {"name": "Microphone", "x": 100, "y": 100, "obs_source": Mock()},
        ]

        with patch("metadata.determine_source_capabilities") as mock_caps:
            mock_caps.side_effect = [
                {"has_audio": True, "has_video": True},  # Camera
                {"has_audio": True, "has_video": False},  # Microphone
            ]

            metadata = create_metadata(sources)

            # Check Camera source
            camera = metadata["sources"]["Camera"]
            assert camera["has_audio"] is True
            assert camera["has_video"] is True
            assert "type" not in camera  # Old field should not exist

            # Check Microphone source
            mic = metadata["sources"]["Microphone"]
            assert mic["has_audio"] is True
            assert mic["has_video"] is False
            assert "type" not in mic

    def test_metadata_without_obs_source(self):
        """Test metadata creation when obs_source is not provided."""
        sources = [{"name": "Unknown Source", "x": 0, "y": 0}]

        metadata = create_metadata(sources)

        source = metadata["sources"]["Unknown Source"]
        assert source["has_audio"] is False
        assert source["has_video"] is False


class TestMetadataCreation:
    """Test metadata creation functionality."""

    def test_create_metadata_basic(self):
        """Test basic metadata creation."""
        sources = [
            {"name": "Camera", "x": 0, "y": 0},
            {"name": "Microphone", "x": 100, "y": 100},
        ]

        metadata = create_metadata(sources)

        # Check basic structure
        assert "canvas_size" in metadata
        assert "sources" in metadata
        assert "fps" in metadata
        assert "timestamp" in metadata

        # Check sources
        assert "Camera" in metadata["sources"]
        assert "Microphone" in metadata["sources"]

    def test_create_metadata_with_custom_canvas_size(self):
        """Test metadata creation with custom canvas size."""
        sources = [{"name": "Source1", "x": 0, "y": 0}]
        canvas_size = (1280, 720)

        metadata = create_metadata(sources, canvas_size=canvas_size)

        assert metadata["canvas_size"] == [1280, 720]

    def test_create_metadata_with_custom_fps(self):
        """Test metadata creation with custom FPS."""
        sources = [{"name": "Source1", "x": 0, "y": 0}]
        fps = 60.0

        metadata = create_metadata(sources, fps=fps)

        assert metadata["fps"] == 60.0

    def test_create_metadata_empty_sources(self):
        """Test metadata creation with empty sources list."""
        metadata = create_metadata([])

        assert metadata["sources"] == {}
        assert len(metadata["sources"]) == 0

    def test_create_metadata_source_positions(self):
        """Test that source positions are correctly stored."""
        sources = [
            {"name": "Source1", "x": 100, "y": 200},
            {"name": "Source2", "x": 300, "y": 400},
        ]

        metadata = create_metadata(sources)

        source1 = metadata["sources"]["Source1"]
        source2 = metadata["sources"]["Source2"]

        assert source1["position"]["x"] == 100
        assert source1["position"]["y"] == 200
        assert source2["position"]["x"] == 300
        assert source2["position"]["y"] == 400

    def test_create_metadata_invalid_canvas_size(self):
        """Test metadata creation with invalid canvas size."""
        sources = [{"name": "Source1", "x": 0, "y": 0}]

        try:
            create_metadata(sources, canvas_size=(0, 1080))
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Canvas size must be positive" in str(e)

    def test_create_metadata_negative_position(self):
        """Test metadata creation with negative source position."""
        sources = [{"name": "Source1", "x": -100, "y": 0}]

        try:
            create_metadata(sources)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Source position cannot be negative" in str(e)

    def test_create_metadata_timestamp_is_recent(self):
        """Test that timestamp is set to current time."""
        sources = [{"name": "Source1", "x": 0, "y": 0}]

        before_time = time.time()
        metadata = create_metadata(sources)
        after_time = time.time()

        assert before_time <= metadata["timestamp"] <= after_time


class TestMetadataValidation:
    """Test metadata validation functionality."""

    def test_validate_metadata_valid(self):
        """Test validation of valid metadata."""
        metadata = {
            "canvas_size": [1920, 1080],
            "sources": {
                "Camera": {
                    "has_audio": True,
                    "has_video": True,
                    "position": {"x": 0, "y": 0},
                }
            },
            "fps": 30.0,
            "timestamp": time.time(),
        }

        assert validate_metadata(metadata) is True

    def test_validate_metadata_missing_fields(self):
        """Test validation fails with missing required fields."""
        metadata = {"canvas_size": [1920, 1080], "sources": {}}

        assert validate_metadata(metadata) is False

    def test_validate_metadata_invalid_canvas_size(self):
        """Test validation fails with invalid canvas size."""
        metadata = {
            "canvas_size": [0, 1080],
            "sources": {},
            "fps": 30.0,
            "timestamp": time.time(),
        }

        assert validate_metadata(metadata) is False

    def test_validate_metadata_invalid_fps(self):
        """Test validation fails with invalid FPS."""
        metadata = {
            "canvas_size": [1920, 1080],
            "sources": {},
            "fps": -30.0,
            "timestamp": time.time(),
        }

        assert validate_metadata(metadata) is False

    def test_validate_metadata_invalid_sources(self):
        """Test validation fails with invalid sources format."""
        metadata = {
            "canvas_size": [1920, 1080],
            "sources": [],  # Should be dict, not list
            "fps": 30.0,
            "timestamp": time.time(),
        }

        assert validate_metadata(metadata) is False


class TestMetadataIntegration:
    """Integration tests for metadata functionality."""

    def setup_method(self):
        """Reset module state before each test."""
        import sys
        import metadata

        # Only reload if module is already in sys.modules
        if 'metadata' in sys.modules:
            importlib.reload(metadata)

    def test_metadata_json_serialization(self):
        """Test that metadata can be serialized to JSON."""
        sources = [
            {"name": "Camera", "x": 0, "y": 0},
            {"name": "Microphone", "x": 100, "y": 100},
        ]

        metadata = create_metadata(sources)

        # Should be able to serialize to JSON
        json_str = json.dumps(metadata)
        assert json_str is not None

        # Should be able to deserialize from JSON
        restored_metadata = json.loads(json_str)
        assert validate_metadata(restored_metadata) is True

    def test_metadata_roundtrip_preserves_capabilities(self):
        """Test that JSON roundtrip preserves source capabilities."""
        sources = [{"name": "Camera", "x": 0, "y": 0, "obs_source": Mock()}]

        with patch("metadata.determine_source_capabilities") as mock_caps:
            mock_caps.return_value = {"has_audio": True, "has_video": True}

            metadata = create_metadata(sources)

            # Serialize and deserialize
            json_str = json.dumps(metadata)
            restored_metadata = json.loads(json_str)

            # Check that capabilities are preserved
            camera = restored_metadata["sources"]["Camera"]
            assert camera["has_audio"] is True
            assert camera["has_video"] is True
            assert validate_metadata(restored_metadata) is True
