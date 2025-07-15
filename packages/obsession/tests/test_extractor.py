"""
Tests for source extraction functionality.
"""

import tempfile
from unittest.mock import patch
from core.extractor import (
    ExtractionResult,
    calculate_crop_params,
    sanitize_filename,
    extract_sources,
)
from pathlib import Path
import pytest


class TestExtractionResult:
    """Test cases for ExtractionResult class."""

    def test_extraction_result_creation_default(self):
        """Test creating ExtractionResult with default values."""
        # When
        result = ExtractionResult()

        # Then
        assert result.success is False
        assert result.extracted_files == []
        assert result.error_message is None

    def test_extraction_result_creation_with_success(self):
        """Test creating ExtractionResult with success."""
        # Given
        files = ["file1.mp4", "file2.mp4"]

        # When
        result = ExtractionResult(success=True, extracted_files=files)

        # Then
        assert result.success is True
        assert result.extracted_files == files
        assert result.error_message is None

    def test_extraction_result_creation_with_error(self):
        """Test creating ExtractionResult with error."""
        # Given
        error_msg = "FFmpeg failed"

        # When
        result = ExtractionResult(success=False, error_message=error_msg)

        # Then
        assert result.success is False
        assert result.extracted_files == []
        assert result.error_message == error_msg

    def test_extraction_result_str_representation(self):
        """Test string representation of ExtractionResult."""
        # Given
        result = ExtractionResult(
            success=True, extracted_files=["file1.mp4", "file2.mp4"]
        )

        # When
        str_repr = str(result)

        # Then
        assert "ExtractionResult(success=True" in str_repr
        assert "extracted_files=2" in str_repr


class TestCropParams:
    """Test cases for crop parameter calculation."""

    def test_calculate_crop_params_basic(self, basic_source_info, standard_canvas_size):
        """Test basic crop parameter calculation."""
        # When
        params = calculate_crop_params(basic_source_info, standard_canvas_size)

        # Then - source at (0,0) with size 1920x1080 fills entire canvas
        assert params["x"] == 0  # Crop from left edge of canvas
        assert params["y"] == 0  # Crop from top edge of canvas
        assert params["width"] == 1920  # Full canvas width
        assert params["height"] == 1080  # Full canvas height

    def test_calculate_crop_params_with_position(
        self, positioned_source_info, wide_canvas_size
    ):
        """Test crop parameters with non-zero position."""
        # When
        params = calculate_crop_params(positioned_source_info, wide_canvas_size)

        # Then - source at position (1920, 0) on 3840x1080 canvas
        assert params["x"] == 1920  # Crop from x=1920 on canvas
        assert params["y"] == 0  # Crop from top of canvas
        assert params["width"] == 1920  # Source width on canvas
        assert params["height"] == 1080  # Source height on canvas

    def test_calculate_crop_params_with_scale(
        self, scaled_source_info, standard_canvas_size
    ):
        """Test crop parameters with scaling."""
        # When
        params = calculate_crop_params(scaled_source_info, standard_canvas_size)

        # Then - scaled source (0.5x) at position (0,0) on canvas
        assert params["x"] == 0
        assert params["y"] == 0
        assert params["width"] == 960  # Scaled width on canvas (1920 * 0.5)
        assert params["height"] == 540  # Scaled height on canvas (1080 * 0.5)

    def test_calculate_crop_params_complex(
        self, complex_source_info, standard_canvas_size
    ):
        """Test crop parameters with both position and scale."""
        # When
        params = calculate_crop_params(complex_source_info, standard_canvas_size)

        # Then - source at position (100, 50) with scale 0.8x0.6 on canvas
        assert params["x"] == 100  # Crop from x=100 on canvas
        assert params["y"] == 50  # Crop from y=50 on canvas
        assert params["width"] == 1536  # Scaled width on canvas (1920 * 0.8)
        assert params["height"] == 648  # Scaled height on canvas (1080 * 0.6)


class TestSanitizeFilename:
    """Test cases for filename sanitization."""

    def test_sanitize_filename_basic(self):
        """Test basic filename sanitization."""
        # Given
        filename = "Camera1"

        # When
        result = sanitize_filename(filename)

        # Then
        assert result == "Camera1"

    def test_sanitize_filename_with_special_characters(self):
        """Test sanitization of filename with special characters."""
        # Given
        filename = 'Source/With\\Special:Characters*?<>|"'

        # When
        result = sanitize_filename(filename)

        # Then
        assert result == "Source_With_Special_Characters"
        assert "/" not in result
        assert "\\" not in result
        assert ":" not in result
        assert "*" not in result
        assert "?" not in result
        assert "<" not in result
        assert ">" not in result
        assert "|" not in result
        assert '"' not in result

    def test_sanitize_filename_multiple_underscores(self):
        """Test that multiple consecutive underscores are collapsed."""
        # Given
        filename = "Source///With\\\\\\Many:::Special"

        # When
        result = sanitize_filename(filename)

        # Then
        assert result == "Source_With_Many_Special"

    def test_sanitize_filename_leading_trailing_underscores(self):
        """Test removal of leading and trailing underscores."""
        # Given
        filename = "/Source_Name/"

        # When
        result = sanitize_filename(filename)

        # Then
        assert result == "Source_Name"

    def test_sanitize_filename_empty_after_sanitization(self):
        """Test handling of filename that becomes empty after sanitization."""
        # Given
        filename = "///**???"

        # When
        result = sanitize_filename(filename)

        # Then
        assert result == "source"

    def test_sanitize_filename_only_special_characters(self):
        """Test sanitization of filename with only special characters."""
        # Given
        filename = '<>|*?"'

        # When
        result = sanitize_filename(filename)

        # Then
        assert result == "source"


class TestExtractorWithCapabilities:
    """Test extractor with source capabilities detection."""

    @pytest.fixture
    def sample_metadata(self):
        """Sample metadata for testing."""
        return {
            "canvas_size": [1920, 1080],
            "fps": 30.0,
            "timestamp": 1234567890.0,
            "sources": {
                "VideoSource": {
                    "position": {"x": 100, "y": 200},
                    "dimensions": {"source_width": 800, "source_height": 600},
                    "scale": {"x": 1.0, "y": 1.0},
                    "has_video": True,
                    "has_audio": False,
                },
                "AudioSource": {
                    "position": {"x": 0, "y": 0},
                    "dimensions": {"source_width": 0, "source_height": 0},
                    "scale": {"x": 1.0, "y": 1.0},
                    "has_video": False,
                    "has_audio": True,
                },
            },
        }

    def test_extractor_processes_video_sources(self, sample_metadata):
        """Test that extractor processes video sources correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test video file
            test_video = Path(temp_dir) / "test_video.mp4"
            test_video.touch()

            # Mock FFmpeg command
            with patch("extractor.subprocess.run") as mock_run:
                mock_run.return_value = None

                result = extract_sources(str(test_video), sample_metadata)

                assert result.success is True
                assert len(result.extracted_files) == 2  # Video and audio files
                assert any("VideoSource.mp4" in f for f in result.extracted_files)
                assert any("AudioSource.m4a" in f for f in result.extracted_files)

    def test_extractor_extracts_audio_tracks(self, sample_metadata):
        """Test that extractor extracts audio tracks correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test video file
            test_video = Path(temp_dir) / "test_video.mp4"
            test_video.touch()

            # Mock FFmpeg command
            with patch("extractor.subprocess.run") as mock_run:
                mock_run.return_value = None

                extract_sources(str(test_video), sample_metadata)

                # Check that audio extraction was called
                audio_calls = [
                    call
                    for call in mock_run.call_args_list
                    if "-vn" in call[0][0]  # Audio extraction flag
                ]
                assert len(audio_calls) == 1

    def test_extractor_skips_sources_without_capabilities(self):
        """Test that extractor skips sources without video or audio capabilities."""
        metadata = {
            "canvas_size": [1920, 1080],
            "fps": 30.0,
            "timestamp": 1234567890.0,
            "sources": {
                "EmptySource": {
                    "position": {"x": 0, "y": 0},
                    "dimensions": {"source_width": 100, "source_height": 100},
                    "scale": {"x": 1.0, "y": 1.0},
                    "has_video": False,
                    "has_audio": False,
                },
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test video file
            test_video = Path(temp_dir) / "test_video.mp4"
            test_video.touch()

            result = extract_sources(str(test_video), metadata)

            assert result.success is True
            assert len(result.extracted_files) == 0

    def test_extractor_handles_video_only_sources(self):
        """Test that extractor handles video-only sources correctly."""
        metadata = {
            "canvas_size": [1920, 1080],
            "fps": 30.0,
            "timestamp": 1234567890.0,
            "sources": {
                "VideoOnlySource": {
                    "position": {"x": 0, "y": 0},
                    "dimensions": {"source_width": 800, "source_height": 600},
                    "scale": {"x": 1.0, "y": 1.0},
                    "has_video": True,
                    "has_audio": False,
                },
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test video file
            test_video = Path(temp_dir) / "test_video.mp4"
            test_video.touch()

            # Mock FFmpeg command
            with patch("extractor.subprocess.run") as mock_run:
                mock_run.return_value = None

                result = extract_sources(str(test_video), metadata)

                assert result.success is True
                assert len(result.extracted_files) == 1
                assert "VideoOnlySource.mp4" in result.extracted_files[0]

    def test_extractor_handles_audio_only_sources(self):
        """Test that extractor handles audio-only sources correctly."""
        metadata = {
            "canvas_size": [1920, 1080],
            "fps": 30.0,
            "timestamp": 1234567890.0,
            "sources": {
                "AudioOnlySource": {
                    "position": {"x": 0, "y": 0},
                    "dimensions": {"source_width": 0, "source_height": 0},
                    "scale": {"x": 1.0, "y": 1.0},
                    "has_video": False,
                    "has_audio": True,
                },
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test video file
            test_video = Path(temp_dir) / "test_video.mp4"
            test_video.touch()

            # Mock FFmpeg command
            with patch("extractor.subprocess.run") as mock_run:
                mock_run.return_value = None

                result = extract_sources(str(test_video), metadata)

                assert result.success is True
                assert len(result.extracted_files) == 1
                assert "AudioOnlySource.m4a" in result.extracted_files[0]

    def test_extractor_output_directory_new_structure(self):
        """Test that extractor uses 'extracted/' directory for new file structure."""
        metadata = {
            "canvas_size": [1920, 1080],
            "fps": 30.0,
            "timestamp": 1234567890.0,
            "sources": {
                "TestSource": {
                    "position": {"x": 0, "y": 0},
                    "dimensions": {"source_width": 800, "source_height": 600},
                    "scale": {"x": 1.0, "y": 1.0},
                    "has_video": True,
                    "has_audio": False,
                },
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test video file
            test_video = Path(temp_dir) / "test_video.mp4"
            test_video.touch()

            # Create metadata.json to simulate new structure
            metadata_file = Path(temp_dir) / "metadata.json"
            metadata_file.touch()

            # Mock FFmpeg command
            with patch("extractor.subprocess.run") as mock_run:
                mock_run.return_value = None

                result = extract_sources(str(test_video), metadata)

                assert result.success is True
                assert len(result.extracted_files) == 1
                # Should use extracted/ directory, not test_video_extracted/
                assert "/extracted/TestSource.mp4" in result.extracted_files[0]

    def test_extractor_output_directory_always_uses_extracted(self):
        """Test that extractor always uses 'extracted/' directory with FileStructureManager."""
        metadata = {
            "canvas_size": [1920, 1080],
            "fps": 30.0,
            "timestamp": 1234567890.0,
            "sources": {
                "TestSource": {
                    "position": {"x": 0, "y": 0},
                    "dimensions": {"source_width": 800, "source_height": 600},
                    "scale": {"x": 1.0, "y": 1.0},
                    "has_video": True,
                    "has_audio": False,
                },
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test video file
            test_video = Path(temp_dir) / "test_video.mp4"
            test_video.touch()

            # Mock FFmpeg command
            with patch("extractor.subprocess.run") as mock_run:
                mock_run.return_value = None

                result = extract_sources(str(test_video), metadata)

                assert result.success is True
                assert len(result.extracted_files) == 1
                # Should always use extracted/ directory with FileStructureManager
                assert "/extracted/TestSource.mp4" in result.extracted_files[0]


class TestCropParamsEdgeCases:
    """Test edge cases for crop parameter calculation."""

    def test_source_with_missing_dimensions(self):
        """Test source with missing dimension data."""
        # Given - source without dimension info
        source_info = {
            "position": {"x": 100, "y": 50},
            "scale": {"x": 1.0, "y": 1.0},
            # Missing dimensions field
        }
        canvas_size = [1920, 1080]

        # When
        params = calculate_crop_params(source_info, canvas_size)

        # Then - should use fallback dimensions
        assert params["x"] == 100
        assert params["y"] == 50
        assert params["width"] == 1820  # 1920 - 100 (fits on canvas)
        assert params["height"] == 1030  # 1080 - 50 (fits on canvas)

    def test_source_with_bounds_negative_position(self):
        """Test source with bounds and negative position."""
        # Given - source with bounds extending beyond canvas
        source_info = {
            "position": {"x": -50, "y": -30},
            "bounds": {"x": 200, "y": 150, "type": 1},
            "scale": {"x": 1.0, "y": 1.0},
            "dimensions": {
                "source_width": 640,
                "source_height": 360,
                "final_width": 640,
                "final_height": 360,
            },
        }
        canvas_size = [1920, 1080]

        # When
        params = calculate_crop_params(source_info, canvas_size)

        # Then - should crop only visible part on canvas
        assert params["x"] == 0  # Clamp negative position to 0
        assert params["y"] == 0  # Clamp negative position to 0
        assert params["width"] == 150  # 200 - 50 (part outside canvas)
        assert params["height"] == 120  # 150 - 30 (part outside canvas)
