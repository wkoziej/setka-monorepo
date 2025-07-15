"""
Tests for AudioValidator.

This module contains unit tests for the AudioValidator class.
"""

import pytest

from src.core.audio_validator import (
    AudioValidator,
    NoAudioFileError,
    MultipleAudioFilesError,
)


class TestAudioValidator:
    """Test cases for AudioValidator class."""

    def test_init(self):
        """Test AudioValidator initialization."""
        validator = AudioValidator()
        # AudioValidator no longer stores audio_extensions after migration to setka-common
        # Test that it initializes without errors
        assert validator is not None

    def test_find_audio_files_empty_directory(self, tmp_path):
        """Test find_audio_files with empty directory."""
        validator = AudioValidator()
        audio_files = validator.find_audio_files(tmp_path)
        assert audio_files == []

    def test_find_audio_files_nonexistent_directory(self, tmp_path):
        """Test find_audio_files with nonexistent directory."""
        nonexistent = tmp_path / "nonexistent"
        validator = AudioValidator()
        audio_files = validator.find_audio_files(nonexistent)
        assert audio_files == []

    def test_find_audio_files_with_audio(self, tmp_path):
        """Test find_audio_files with audio files."""
        # Create test audio files
        audio_files = [
            tmp_path / "main.mp3",
            tmp_path / "background.wav",
            tmp_path / "video.mp4",  # Should be ignored
            tmp_path / "document.txt",  # Should be ignored
        ]

        for file_path in audio_files:
            file_path.touch()

        validator = AudioValidator()
        found_audio = validator.find_audio_files(tmp_path)

        # Should find only audio files, sorted by name
        expected = [tmp_path / "background.wav", tmp_path / "main.mp3"]
        assert found_audio == expected

    def test_find_audio_files_sorting(self, tmp_path):
        """Test that find_audio_files returns sorted results."""
        # Create audio files in non-alphabetical order
        audio_files = [
            tmp_path / "zebra.mp3",
            tmp_path / "alpha.wav",
            tmp_path / "beta.m4a",
        ]

        for file_path in audio_files:
            file_path.touch()

        validator = AudioValidator()
        found_audio = validator.find_audio_files(tmp_path)

        # Should be sorted alphabetically
        expected = [
            tmp_path / "alpha.wav",
            tmp_path / "beta.m4a",
            tmp_path / "zebra.mp3",
        ]
        assert found_audio == expected

    def test_find_audio_files_case_insensitive(self, tmp_path):
        """Test that find_audio_files handles case insensitive extensions."""
        audio_files = [
            tmp_path / "audio1.MP3",
            tmp_path / "audio2.WAV",
            tmp_path / "audio3.M4A",
        ]

        for file_path in audio_files:
            file_path.touch()

        validator = AudioValidator()
        found_audio = validator.find_audio_files(tmp_path)

        assert len(found_audio) == 3
        assert all(f.suffix.lower() in [".mp3", ".wav", ".m4a"] for f in found_audio)

    def test_detect_main_audio_single_file(self, tmp_path):
        """Test detect_main_audio with single audio file."""
        audio_file = tmp_path / "main.mp3"
        audio_file.touch()

        validator = AudioValidator()
        result = validator.detect_main_audio(tmp_path)

        assert result == audio_file

    def test_detect_main_audio_no_files(self, tmp_path):
        """Test detect_main_audio with no audio files."""
        validator = AudioValidator()

        with pytest.raises(
            NoAudioFileError, match="Brak plików audio w katalogu extracted/"
        ):
            validator.detect_main_audio(tmp_path)

    def test_detect_main_audio_multiple_files_no_specification(self, tmp_path):
        """Test detect_main_audio with multiple files but no specification."""
        audio_files = [tmp_path / "audio1.mp3", tmp_path / "audio2.wav"]

        for file_path in audio_files:
            file_path.touch()

        validator = AudioValidator()

        with pytest.raises(MultipleAudioFilesError, match="Znaleziono 2 plików audio"):
            validator.detect_main_audio(tmp_path)

    def test_detect_main_audio_specified_valid(self, tmp_path):
        """Test detect_main_audio with valid specified audio."""
        audio_files = [tmp_path / "audio1.mp3", tmp_path / "audio2.wav"]

        for file_path in audio_files:
            file_path.touch()

        validator = AudioValidator()
        result = validator.detect_main_audio(tmp_path, "audio2.wav")

        assert result == tmp_path / "audio2.wav"

    def test_detect_main_audio_specified_not_found(self, tmp_path):
        """Test detect_main_audio with specified audio that doesn't exist."""
        audio_file = tmp_path / "existing.mp3"
        audio_file.touch()

        validator = AudioValidator()

        with pytest.raises(
            ValueError, match="Specified audio file not found: nonexistent.mp3"
        ):
            validator.detect_main_audio(tmp_path, "nonexistent.mp3")

    def test_detect_main_audio_specified_not_file(self, tmp_path):
        """Test detect_main_audio with specified path that's not a file."""
        # Create a directory instead of file
        audio_dir = tmp_path / "audio_dir"
        audio_dir.mkdir()

        validator = AudioValidator()

        with pytest.raises(
            ValueError, match="Specified audio path is not a file: audio_dir"
        ):
            validator.detect_main_audio(tmp_path, "audio_dir")

    def test_detect_main_audio_specified_invalid_format(self, tmp_path):
        """Test detect_main_audio with specified file that's not audio."""
        text_file = tmp_path / "document.txt"
        text_file.touch()

        validator = AudioValidator()

        with pytest.raises(
            ValueError, match="Specified file is not a valid audio file: document.txt"
        ):
            validator.detect_main_audio(tmp_path, "document.txt")

    def test_validate_specified_audio_valid(self, tmp_path):
        """Test _validate_specified_audio with valid audio file."""
        audio_file = tmp_path / "test.mp3"
        audio_file.touch()

        validator = AudioValidator()
        result = validator._validate_specified_audio(tmp_path, "test.mp3")

        assert result == audio_file

    def test_validate_specified_audio_not_found(self, tmp_path):
        """Test _validate_specified_audio with nonexistent file."""
        validator = AudioValidator()

        with pytest.raises(
            ValueError, match="Specified audio file not found: missing.mp3"
        ):
            validator._validate_specified_audio(tmp_path, "missing.mp3")

    def test_validate_specified_audio_invalid_extension(self, tmp_path):
        """Test _validate_specified_audio with invalid extension."""
        text_file = tmp_path / "document.txt"
        text_file.touch()

        validator = AudioValidator()

        with pytest.raises(
            ValueError, match="Specified file is not a valid audio file"
        ):
            validator._validate_specified_audio(tmp_path, "document.txt")
