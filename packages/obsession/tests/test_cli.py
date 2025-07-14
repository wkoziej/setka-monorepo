"""
Tests for CLI extract functionality.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from cli.extract import main, parse_args
from core.extractor import ExtractionResult


class TestCLIExtract:
    """Test cases for CLI extract functionality."""

    def test_parse_args_with_valid_arguments(self):
        """Test argument parsing with valid video and metadata files."""
        # Given
        test_args = ["test_video.mp4", "test_metadata.json"]

        # When
        args = parse_args(test_args)

        # Then
        assert args.video_file == "test_video.mp4"
        assert args.metadata_file == "test_metadata.json"
        assert args.output_dir is None  # Default value
        assert args.verbose is False  # Default value

    def test_parse_args_with_optional_arguments(self):
        """Test argument parsing with optional arguments."""
        # Given
        test_args = [
            "video.mp4",
            "metadata.json",
            "--output-dir",
            "custom_output",
            "--verbose",
        ]

        # When
        args = parse_args(test_args)

        # Then
        assert args.video_file == "video.mp4"
        assert args.metadata_file == "metadata.json"
        assert args.output_dir == "custom_output"
        assert args.verbose is True

    def test_main_with_successful_extraction(self):
        """Test main function with successful extraction."""
        # Given
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            video_file = Path(temp_dir) / "test_video.mp4"
            metadata_file = Path(temp_dir) / "test_metadata.json"

            # Create dummy video file
            video_file.write_text("dummy video content")

            # Create test metadata
            test_metadata = {
                "canvas_size": [1920, 1080],
                "sources": {
                    "Camera1": {
                        "position": {"x": 0, "y": 0},
                        "scale": {"x": 1.0, "y": 1.0},
                    }
                },
            }
            metadata_file.write_text(json.dumps(test_metadata))

            # Mock successful extraction
            mock_result = ExtractionResult(
                success=True, extracted_files=[str(Path(temp_dir) / "Camera1.mp4")]
            )

            with patch("cli.extract.extract_sources", return_value=mock_result):
                with patch(
                    "sys.argv", ["extract.py", str(video_file), str(metadata_file)]
                ):
                    # When
                    result = main()

                    # Then
                    assert result == 0

    def test_main_with_failed_extraction(self):
        """Test main function with failed extraction."""
        # Given
        with tempfile.TemporaryDirectory() as temp_dir:
            video_file = Path(temp_dir) / "test_video.mp4"
            metadata_file = Path(temp_dir) / "test_metadata.json"

            video_file.write_text("dummy video content")

            test_metadata = {
                "canvas_size": [1920, 1080],
                "sources": {
                    "Camera1": {
                        "position": {"x": 0, "y": 0},
                        "scale": {"x": 1.0, "y": 1.0},
                    }
                },
            }
            metadata_file.write_text(json.dumps(test_metadata))

            # Mock failed extraction
            mock_result = ExtractionResult(success=False, error_message="FFmpeg failed")

            with patch("cli.extract.extract_sources", return_value=mock_result):
                with patch(
                    "sys.argv", ["extract.py", str(video_file), str(metadata_file)]
                ):
                    # When
                    result = main()

                    # Then
                    assert result == 1

    def test_main_with_missing_video_file(self):
        """Test main function with missing video file."""
        # Given
        with tempfile.TemporaryDirectory() as temp_dir:
            metadata_file = Path(temp_dir) / "test_metadata.json"

            test_metadata = {"canvas_size": [1920, 1080], "sources": {}}
            metadata_file.write_text(json.dumps(test_metadata))

            with patch(
                "sys.argv", ["extract.py", "nonexistent_video.mp4", str(metadata_file)]
            ):
                # When
                result = main()

                # Then
                assert result == 1

    def test_main_with_missing_metadata_file(self):
        """Test main function with missing metadata file."""
        # Given
        with tempfile.TemporaryDirectory() as temp_dir:
            video_file = Path(temp_dir) / "test_video.mp4"
            video_file.write_text("dummy video content")

            with patch(
                "sys.argv", ["extract.py", str(video_file), "nonexistent_metadata.json"]
            ):
                # When
                result = main()

                # Then
                assert result == 1

    def test_main_with_invalid_json_metadata(self):
        """Test main function with invalid JSON metadata."""
        # Given
        with tempfile.TemporaryDirectory() as temp_dir:
            video_file = Path(temp_dir) / "test_video.mp4"
            metadata_file = Path(temp_dir) / "test_metadata.json"

            video_file.write_text("dummy video content")
            metadata_file.write_text("invalid json content")

            with patch("sys.argv", ["extract.py", str(video_file), str(metadata_file)]):
                # When
                result = main()

                # Then
                assert result == 1
