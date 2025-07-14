"""
Test module for advanced_scene_switcher_extractor functionality.
Tests for updated file finding logic that works with new directory structure.
"""

import os
import tempfile
import time
import json
from pathlib import Path
from unittest.mock import patch, Mock


# Import functions to test
from src.obs_integration.advanced_scene_switcher_extractor import (
    find_latest_recording,
    run_extraction,
)


class TestAdvancedSceneSwitcherExtractor:
    """Test cases for advanced scene switcher extractor functionality."""

    def test_find_latest_recording_new_structure(self):
        """Test finding recording in new reorganized directory structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create new structure: recording_name/recording_name.mkv
            recording_dir = Path(temp_dir) / "recording_2025-01-06_15-30-00"
            recording_dir.mkdir()

            recording_file = recording_dir / "recording_2025-01-06_15-30-00.mkv"
            recording_file.touch()

            # Create metadata.json and extracted/ to confirm it's new structure
            metadata_content = {"sources": {}, "canvas_size": [1920, 1080]}
            with open(recording_dir / "metadata.json", "w") as f:
                json.dump(metadata_content, f)
            (recording_dir / "extracted").mkdir()

            # Mock Path.home() to return our temp directory
            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = Path(temp_dir)

                # Mock the common directories to point to our temp structure
                with patch(
                    "src.obs_integration.advanced_scene_switcher_extractor.Path"
                ) as mock_path:
                    mock_path.home.return_value = Path(temp_dir)

                    # Create the expected directory structure that the function looks for
                    videos_dir = Path(temp_dir) / "Videos" / "obs"
                    videos_dir.mkdir(parents=True)

                    # Create a symlink or copy the recording to the expected location
                    import shutil

                    shutil.copytree(
                        recording_dir, videos_dir / "recording_2025-01-06_15-30-00"
                    )

                    result = find_latest_recording()

                    # Should find the recording file in new structure
                    assert result is not None
                    assert "recording_2025-01-06_15-30-00.mkv" in result
                    assert os.path.exists(result)

    def test_find_latest_recording_mixed_structure(self):
        """Test finding recording when both old and new structure files exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            videos_dir = Path(temp_dir) / "Videos" / "obs"
            videos_dir.mkdir(parents=True)

            # Create old structure file (older)
            old_file = videos_dir / "old_recording.mkv"
            old_file.touch()
            # Make it older
            old_time = time.time() - 60
            os.utime(old_file, (old_time, old_time))

            # Create new structure file (newer)
            recording_dir = videos_dir / "recording_2025-01-06_15-30-00"
            recording_dir.mkdir()
            new_file = recording_dir / "recording_2025-01-06_15-30-00.mkv"
            new_file.touch()
            metadata_content = {"sources": {}, "canvas_size": [1920, 1080]}
            with open(recording_dir / "metadata.json", "w") as f:
                json.dump(metadata_content, f)
            (recording_dir / "extracted").mkdir()

            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = Path(temp_dir)

                result = find_latest_recording()

                # Should find the newer file in new structure
                assert result is not None
                assert "recording_2025-01-06_15-30-00.mkv" in result

    def test_find_latest_recording_no_metadata_no_result(self):
        """Test that directories without metadata.json are ignored (new structure only)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            videos_dir = Path(temp_dir) / "Videos" / "obs"
            videos_dir.mkdir(parents=True)

            # Create directory without metadata.json (old structure - no longer supported)
            recording_dir = videos_dir / "some_recording"
            recording_dir.mkdir()
            recording_file = recording_dir / "some_recording.mkv"
            recording_file.touch()
            # No metadata.json or extracted/ - old structure not supported

            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = Path(temp_dir)

                result = find_latest_recording()

                # Should return None as old structure is not supported
                assert result is None

    def test_find_latest_recording_multiple_new_structure(self):
        """Test finding latest recording among multiple new structure directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            videos_dir = Path(temp_dir) / "Videos" / "obs"
            videos_dir.mkdir(parents=True)

            # Create multiple recording directories with new structure
            recordings = [
                "recording_2025-01-06_15-30-00",
                "recording_2025-01-06_16-00-00",
                "recording_2025-01-06_16-30-00",
            ]

            for i, recording_name in enumerate(recordings):
                recording_dir = videos_dir / recording_name
                recording_dir.mkdir()

                recording_file = recording_dir / f"{recording_name}.mkv"
                recording_file.touch()
                metadata_content = {"sources": {}, "canvas_size": [1920, 1080]}
                with open(recording_dir / "metadata.json", "w") as f:
                    json.dump(metadata_content, f)
                (recording_dir / "extracted").mkdir()

                # Make each subsequent recording newer
                file_time = time.time() - (len(recordings) - i) * 10
                os.utime(recording_file, (file_time, file_time))

            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = Path(temp_dir)

                result = find_latest_recording()

                # Should find the newest recording
                assert result is not None
                assert "recording_2025-01-06_16-30-00.mkv" in result

    def test_find_latest_recording_too_old(self):
        """Test that old recordings are ignored."""
        with tempfile.TemporaryDirectory() as temp_dir:
            videos_dir = Path(temp_dir) / "Videos" / "obs"
            videos_dir.mkdir(parents=True)

            # Create old recording
            recording_dir = videos_dir / "recording_2025-01-06_15-30-00"
            recording_dir.mkdir()
            recording_file = recording_dir / "recording_2025-01-06_15-30-00.mkv"
            recording_file.touch()
            metadata_content = {"sources": {}, "canvas_size": [1920, 1080]}
            with open(recording_dir / "metadata.json", "w") as f:
                json.dump(metadata_content, f)
            (recording_dir / "extracted").mkdir()

            # Make it old (more than 30 seconds)
            old_time = time.time() - 60
            os.utime(recording_file, (old_time, old_time))

            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = Path(temp_dir)

                result = find_latest_recording()

                # Should return None for old files
                assert result is None

    def test_find_latest_recording_no_files(self):
        """Test behavior when no recording files exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            videos_dir = Path(temp_dir) / "Videos" / "obs"
            videos_dir.mkdir(parents=True)

            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = Path(temp_dir)

                result = find_latest_recording()

                assert result is None

    def test_run_extraction_with_new_structure(self):
        """Test run_extraction with new directory structure path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create new structure recording
            recording_dir = Path(temp_dir) / "recording_2025-01-06_15-30-00"
            recording_dir.mkdir()
            recording_file = recording_dir / "recording_2025-01-06_15-30-00.mkv"
            recording_file.touch()
            # Create valid metadata.json
            metadata_content = {"sources": {}, "canvas_size": [1920, 1080]}
            with open(recording_dir / "metadata.json", "w") as f:
                json.dump(metadata_content, f)
            (recording_dir / "extracted").mkdir()

            # Mock subprocess.run
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="Success", stderr="")

                # Mock CLI path existence
                with patch("pathlib.Path.exists") as mock_exists:
                    mock_exists.return_value = True

                    result = run_extraction(str(recording_file))

                    assert result is True

                    # Verify command was called with correct path
                    mock_run.assert_called_once()
                    call_args = mock_run.call_args[0][0]
                    assert str(recording_file) in call_args

    def test_run_extraction_failure(self):
        """Test run_extraction failure handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            recording_file = Path(temp_dir) / "test.mkv"
            recording_file.touch()

            # Mock subprocess.run to return failure
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=1, stdout="", stderr="Error")

                # Mock CLI path existence
                with patch("pathlib.Path.exists") as mock_exists:
                    mock_exists.return_value = True

                    result = run_extraction(str(recording_file))

                    assert result is False
