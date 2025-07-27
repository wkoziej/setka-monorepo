# ABOUTME: Tests for MediaDiscovery auto-discovery functionality
# ABOUTME: Tests file discovery, validation, and main audio detection in recording directories

"""Tests for MediaDiscovery class."""


import pytest

from cinemon.config.media_discovery import MediaDiscovery


class TestMediaDiscovery:
    """Test cases for MediaDiscovery auto-discovery functionality."""

    def test_init_with_valid_recording_directory(self, tmp_path):
        """Test MediaDiscovery initialization with valid recording directory."""
        # Create test directory structure
        recording_dir = tmp_path / "recording_20250105_143022"
        recording_dir.mkdir()
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir()

        # Create test media files
        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "Camera2.mp4").touch()
        (extracted_dir / "main_audio.m4a").touch()

        discovery = MediaDiscovery(recording_dir)

        assert discovery.recording_dir == recording_dir
        assert discovery.extracted_dir == extracted_dir

    def test_init_with_nonexistent_directory(self, tmp_path):
        """Test MediaDiscovery initialization with nonexistent directory."""
        nonexistent_dir = tmp_path / "nonexistent"

        with pytest.raises(FileNotFoundError):
            MediaDiscovery(nonexistent_dir)

    def test_init_with_missing_extracted_directory(self, tmp_path):
        """Test MediaDiscovery initialization with missing extracted directory."""
        recording_dir = tmp_path / "recording_20250105_143022"
        recording_dir.mkdir()
        # No extracted directory

        with pytest.raises(FileNotFoundError):
            MediaDiscovery(recording_dir)

    def test_discover_video_files_mp4_and_mkv(self, tmp_path):
        """Test discovery of MP4 and MKV video files."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        # Create test video files
        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "Camera2.mkv").touch()
        (extracted_dir / "Screen_Capture.mp4").touch()
        (extracted_dir / "audio_file.m4a").touch()  # Should be ignored
        (extracted_dir / "subtitle.srt").touch()  # Should be ignored

        discovery = MediaDiscovery(recording_dir)
        video_files = discovery.discover_video_files()

        assert len(video_files) == 3
        assert "Camera1.mp4" in video_files
        assert "Camera2.mkv" in video_files
        assert "Screen_Capture.mp4" in video_files
        assert "audio_file.m4a" not in video_files

    def test_discover_audio_files_m4a_and_wav(self, tmp_path):
        """Test discovery of M4A and WAV audio files."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        # Create test audio files
        (extracted_dir / "main_audio.m4a").touch()
        (extracted_dir / "Microphone.wav").touch()
        (extracted_dir / "Background_Music.m4a").touch()
        (extracted_dir / "video_file.mp4").touch()  # Should be ignored

        discovery = MediaDiscovery(recording_dir)
        audio_files = discovery.discover_audio_files()

        assert len(audio_files) == 3
        assert "main_audio.m4a" in audio_files
        assert "Microphone.wav" in audio_files
        assert "Background_Music.m4a" in audio_files
        assert "video_file.mp4" not in audio_files

    def test_discover_analysis_files_json(self, tmp_path):
        """Test discovery of JSON analysis files."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        analysis_dir = recording_dir / "analysis"
        extracted_dir.mkdir(parents=True)
        analysis_dir.mkdir()

        # Create test analysis files
        (analysis_dir / "main_audio_analysis.json").touch()
        (analysis_dir / "microphone_analysis.json").touch()
        (analysis_dir / "config.yaml").touch()  # Should be ignored

        discovery = MediaDiscovery(recording_dir)
        analysis_files = discovery.discover_analysis_files()

        assert len(analysis_files) == 2
        assert "main_audio_analysis.json" in analysis_files
        assert "microphone_analysis.json" in analysis_files
        assert "config.yaml" not in analysis_files

    def test_detect_main_audio_with_main_audio_file(self, tmp_path):
        """Test main audio detection when main_audio file exists."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        # Create audio files including main_audio
        (extracted_dir / "main_audio.m4a").touch()
        (extracted_dir / "Microphone.wav").touch()
        (extracted_dir / "Desktop_Audio.m4a").touch()

        discovery = MediaDiscovery(recording_dir)
        main_audio = discovery.detect_main_audio()

        assert main_audio == "main_audio.m4a"

    def test_detect_main_audio_with_single_audio_file(self, tmp_path):
        """Test main audio detection with only one audio file."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        # Create single audio file
        (extracted_dir / "Microphone.wav").touch()

        discovery = MediaDiscovery(recording_dir)
        main_audio = discovery.detect_main_audio()

        assert main_audio == "Microphone.wav"

    def test_detect_main_audio_with_multiple_files_no_main(self, tmp_path):
        """Test main audio detection with multiple files but no main_audio."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        # Create multiple audio files without main_audio
        (extracted_dir / "Microphone.wav").touch()
        (extracted_dir / "Desktop_Audio.m4a").touch()
        (extracted_dir / "Background_Music.m4a").touch()

        discovery = MediaDiscovery(recording_dir)
        main_audio = discovery.detect_main_audio()

        # Should return None when multiple files and no main_audio
        assert main_audio is None

    def test_detect_main_audio_with_no_audio_files(self, tmp_path):
        """Test main audio detection with no audio files."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        # No audio files
        (extracted_dir / "Camera1.mp4").touch()

        discovery = MediaDiscovery(recording_dir)
        main_audio = discovery.detect_main_audio()

        assert main_audio is None

    def test_validate_structure_with_complete_directory(self, tmp_path):
        """Test structure validation with complete recording directory."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        analysis_dir = recording_dir / "analysis"
        extracted_dir.mkdir(parents=True)
        analysis_dir.mkdir()

        # Create complete structure
        (extracted_dir / "Camera1.mp4").touch()
        (extracted_dir / "main_audio.m4a").touch()
        (analysis_dir / "main_audio_analysis.json").touch()
        (recording_dir / "metadata.json").touch()

        discovery = MediaDiscovery(recording_dir)
        validation_result = discovery.validate_structure()

        assert validation_result.is_valid is True
        assert len(validation_result.errors) == 0
        assert validation_result.has_video_files is True
        assert validation_result.has_audio_files is True
        assert validation_result.has_analysis_files is True

    def test_validate_structure_with_missing_video_files(self, tmp_path):
        """Test structure validation with missing video files."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        # Only audio files, no video
        (extracted_dir / "main_audio.m4a").touch()

        discovery = MediaDiscovery(recording_dir)
        validation_result = discovery.validate_structure()

        assert validation_result.is_valid is False
        assert "No video files found in extracted directory" in validation_result.errors
        assert validation_result.has_video_files is False
        assert validation_result.has_audio_files is True

    def test_validate_structure_with_missing_audio_files(self, tmp_path):
        """Test structure validation with missing audio files."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        # Only video files, no audio
        (extracted_dir / "Camera1.mp4").touch()

        discovery = MediaDiscovery(recording_dir)
        validation_result = discovery.validate_structure()

        assert validation_result.is_valid is False
        assert "No audio files found in extracted directory" in validation_result.errors
        assert validation_result.has_video_files is True
        assert validation_result.has_audio_files is False

    def test_case_insensitive_file_extensions(self, tmp_path):
        """Test that file discovery is case-insensitive for extensions."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        # Create files with mixed case extensions
        (extracted_dir / "Camera1.MP4").touch()
        (extracted_dir / "Camera2.MKV").touch()
        (extracted_dir / "audio.M4A").touch()
        (extracted_dir / "sound.WAV").touch()

        discovery = MediaDiscovery(recording_dir)
        video_files = discovery.discover_video_files()
        audio_files = discovery.discover_audio_files()

        assert len(video_files) == 2
        assert "Camera1.MP4" in video_files
        assert "Camera2.MKV" in video_files

        assert len(audio_files) == 2
        assert "audio.M4A" in audio_files
        assert "sound.WAV" in audio_files

    def test_polish_filename_support(self, tmp_path):
        """Test support for Polish characters in filenames."""
        recording_dir = tmp_path / "recording_20250105_143022"
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir(parents=True)

        # Create files with Polish characters
        (extracted_dir / "Przechwytywanie ekranu.mp4").touch()
        (extracted_dir / "Przechwytywanie wejścia dźwięku.m4a").touch()
        (extracted_dir / "Kamera główna.mkv").touch()

        discovery = MediaDiscovery(recording_dir)
        video_files = discovery.discover_video_files()
        audio_files = discovery.discover_audio_files()

        assert len(video_files) == 2
        assert "Przechwytywanie ekranu.mp4" in video_files
        assert "Kamera główna.mkv" in video_files

        assert len(audio_files) == 1
        assert "Przechwytywanie wejścia dźwięku.m4a" in audio_files
