# ABOUTME: Tests for CLI audio analysis command
# ABOUTME: Validates audio analysis CLI functionality with real files

"""Tests for CLI audio analysis command."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from setka_common.audio import analyze_audio_command


class TestAnalyzeAudioCLI:
    """Test cases for audio analysis CLI command."""

    def test_analyze_audio_command_basic(self, tmp_path):
        """Test basic audio analysis command."""
        # Create test audio file
        audio_file = tmp_path / "test_audio.wav"
        audio_file.touch()

        # Create test output directory
        output_dir = tmp_path / "output"

        # Mock AudioAnalyzer
        with patch("setka_common.audio.AudioAnalyzer") as mock_analyzer_class:
            mock_analyzer = Mock()
            mock_analyzer_class.return_value = mock_analyzer

            # Mock analysis result
            analysis_result = {
                "duration": 5.0,
                "tempo": {"bpm": 120.0},
                "animation_events": {"beats": [1.0, 2.0, 3.0]},
            }
            mock_analyzer.analyze_for_animation.return_value = analysis_result

            # Execute command
            result_path = analyze_audio_command(
                audio_file, output_dir, beat_division=8, min_onset_interval=2.0
            )

            # Verify analyzer was called correctly
            mock_analyzer.analyze_for_animation.assert_called_once_with(
                audio_file, beat_division=8, min_onset_interval=2.0
            )

            # Verify output file was saved
            expected_path = output_dir / "test_audio_analysis.json"
            assert result_path == expected_path
            mock_analyzer.save_analysis.assert_called_once_with(
                analysis_result, expected_path
            )

    def test_analyze_audio_command_with_defaults(self, tmp_path):
        """Test audio analysis command with default parameters."""
        audio_file = tmp_path / "music.m4a"
        audio_file.touch()

        with patch("setka_common.audio.AudioAnalyzer") as mock_analyzer_class:
            mock_analyzer = Mock()
            mock_analyzer_class.return_value = mock_analyzer
            mock_analyzer.analyze_for_animation.return_value = {}

            analyze_audio_command(audio_file, tmp_path)

            # Check default parameters were used
            mock_analyzer.analyze_for_animation.assert_called_once_with(
                audio_file, beat_division=8, min_onset_interval=2.0
            )

    def test_analyze_audio_command_custom_parameters(self, tmp_path):
        """Test audio analysis command with custom parameters."""
        audio_file = tmp_path / "song.wav"
        audio_file.touch()

        with patch("setka_common.audio.AudioAnalyzer") as mock_analyzer_class:
            mock_analyzer = Mock()
            mock_analyzer_class.return_value = mock_analyzer
            mock_analyzer.analyze_for_animation.return_value = {}

            analyze_audio_command(
                audio_file, tmp_path, beat_division=4, min_onset_interval=1.5
            )

            mock_analyzer.analyze_for_animation.assert_called_once_with(
                audio_file, beat_division=4, min_onset_interval=1.5
            )

    def test_analyze_audio_command_missing_file(self, tmp_path):
        """Test audio analysis command with missing audio file."""
        nonexistent_file = tmp_path / "missing.wav"

        with pytest.raises(FileNotFoundError):
            analyze_audio_command(nonexistent_file, tmp_path)

    def test_analyze_audio_command_creates_output_dir(self, tmp_path):
        """Test that output directory is created if it doesn't exist."""
        audio_file = tmp_path / "test.wav"
        audio_file.touch()

        output_dir = tmp_path / "new_output"
        # Output dir doesn't exist yet
        assert not output_dir.exists()

        with patch("setka_common.audio.AudioAnalyzer") as mock_analyzer_class:
            mock_analyzer = Mock()
            mock_analyzer_class.return_value = mock_analyzer
            mock_analyzer.analyze_for_animation.return_value = {}

            analyze_audio_command(audio_file, output_dir)

            # Output dir should be created
            assert output_dir.exists()
            assert output_dir.is_dir()


    def test_analyze_audio_command_integration_with_recording(self, tmp_path):
        """Test audio analysis command with recording structure."""
        # Create recording structure
        recording_dir = tmp_path / "test_recording"
        recording_dir.mkdir()

        video_file = recording_dir / "test_recording.mkv"
        video_file.touch()

        audio_file = recording_dir / "extracted" / "main_audio.m4a"
        audio_file.parent.mkdir()
        audio_file.touch()

        output_dir = tmp_path / "analysis_output"

        # Mock analysis
        with patch("setka_common.audio.AudioAnalyzer") as mock_analyzer_class:
            mock_analyzer = Mock()
            mock_analyzer_class.return_value = mock_analyzer

            analysis_result = {
                "duration": 10.0,
                "tempo": {"bpm": 140.0},
                "animation_events": {"beats": [0.5, 1.0, 1.5]},
            }
            mock_analyzer.analyze_for_animation.return_value = analysis_result

            # Use custom output directory
            result_path = analyze_audio_command(audio_file, output_dir)

            # Should save to specified output directory
            expected_path = output_dir / "main_audio_analysis.json"
            assert result_path == expected_path
            assert output_dir.exists()

    def test_output_filename_generation(self, tmp_path):
        """Test correct output filename generation."""
        test_cases = [
            ("audio.wav", "audio_analysis.json"),
            ("music.m4a", "music_analysis.json"),
            ("test_file.flac", "test_file_analysis.json"),
            ("no_extension", "no_extension_analysis.json"),
        ]

        for input_name, expected_output in test_cases:
            audio_file = tmp_path / input_name
            audio_file.touch()

            with patch("setka_common.audio.AudioAnalyzer") as mock_analyzer_class:
                mock_analyzer = Mock()
                mock_analyzer_class.return_value = mock_analyzer
                mock_analyzer.analyze_for_animation.return_value = {}

                result_path = analyze_audio_command(audio_file, tmp_path)

                assert result_path.name == expected_output
                assert result_path.parent == tmp_path
