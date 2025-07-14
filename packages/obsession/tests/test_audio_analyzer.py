# ABOUTME: Unit and integration tests for AudioAnalyzer class
# ABOUTME: Tests audio analysis functionality for animation timing data

"""Tests for audio analyzer module."""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import numpy as np

from src.core.audio_analyzer import AudioAnalyzer


class TestAudioAnalyzerInit:
    """Test AudioAnalyzer initialization and setup."""

    def test_init_creates_instance(self):
        """Test that AudioAnalyzer can be instantiated."""
        analyzer = AudioAnalyzer()
        assert analyzer is not None
        assert analyzer._librosa is None
        assert analyzer._scipy is None

    def test_lazy_loading_librosa(self):
        """Test lazy loading of librosa library."""
        analyzer = AudioAnalyzer()

        # Mock the import inside the property
        mock_librosa = Mock()
        with patch("builtins.__import__") as mock_import:
            mock_import.return_value = mock_librosa
            mock_librosa.librosa = mock_librosa  # For module access

            # Access property - should trigger import
            _ = analyzer.librosa

            # Verify import was called
            mock_import.assert_called()
            assert analyzer._librosa is not None

    def test_lazy_loading_scipy(self):
        """Test lazy loading of scipy find_peaks."""
        analyzer = AudioAnalyzer()

        # Create a mock module structure
        mock_scipy = Mock()
        mock_scipy.signal.find_peaks = Mock()

        with patch.dict(
            "sys.modules", {"scipy": mock_scipy, "scipy.signal": mock_scipy.signal}
        ):
            # Access property - should trigger import
            result = analyzer.scipy

            # Verify find_peaks was imported
            assert analyzer._scipy is not None
            assert callable(result)

    def test_missing_librosa_raises_error(self):
        """Test that missing librosa raises ImportError with helpful message."""
        analyzer = AudioAnalyzer()

        with patch(
            "builtins.__import__", side_effect=ImportError("No module named 'librosa'")
        ):
            with pytest.raises(ImportError) as exc_info:
                _ = analyzer.librosa

            assert "librosa is required" in str(exc_info.value)
            assert "pip install librosa" in str(exc_info.value)

    def test_missing_scipy_raises_error(self):
        """Test that missing scipy raises ImportError with helpful message."""
        analyzer = AudioAnalyzer()

        with patch(
            "builtins.__import__", side_effect=ImportError("No module named 'scipy'")
        ):
            with pytest.raises(ImportError) as exc_info:
                _ = analyzer.scipy

            assert "scipy is required" in str(exc_info.value)
            assert "pip install scipy" in str(exc_info.value)


class TestAudioAnalyzerCore:
    """Test core audio analysis functionality."""

    @pytest.fixture
    def mock_analyzer(self):
        """Create analyzer with mocked dependencies."""
        analyzer = AudioAnalyzer()

        # Mock librosa
        analyzer._librosa = Mock()
        analyzer._librosa.load.return_value = (
            np.zeros(44100),
            44100,
        )  # 1 second of silence
        analyzer._librosa.beat.beat_track.return_value = (
            120.0,
            np.array([0.5, 1.0, 1.5, 2.0]),
        )
        analyzer._librosa.onset.onset_detect.return_value = np.array(
            [0.1, 0.5, 1.0, 1.5]
        )
        analyzer._librosa.feature.chroma_stft.return_value = np.random.rand(12, 100)
        analyzer._librosa.feature.mfcc.return_value = np.random.rand(13, 100)
        analyzer._librosa.feature.spectral_contrast.return_value = np.random.rand(
            7, 100
        )
        analyzer._librosa.segment.agglomerative.return_value = np.array([0, 50])

        # Mock frames_to_time to return appropriate values based on input length
        def mock_frames_to_time(frames, sr=None):
            if isinstance(frames, (list, np.ndarray)):
                # Return time values based on frame count
                return np.linspace(0, 1.0, len(frames))
            return np.array([0.0, 2.5])

        analyzer._librosa.frames_to_time = mock_frames_to_time
        analyzer._librosa.stft.return_value = np.random.rand(1025, 100)
        analyzer._librosa.fft_frequencies.return_value = np.linspace(0, 22050, 1025)

        # Mock scipy find_peaks properly
        def mock_find_peaks(data, **kwargs):
            # Return indices that are within bounds of the data
            if len(data) > 0:
                # Return some valid indices
                return (np.array([0, min(25, len(data) - 1)]), {})
            return (np.array([]), {})

        analyzer._scipy = mock_find_peaks

        return analyzer

    def test_analyze_for_animation_basic(self, mock_analyzer):
        """Test basic analysis returns expected structure."""
        result = mock_analyzer.analyze_for_animation(Path("test.wav"))

        # Check basic structure
        assert "duration" in result
        assert "sample_rate" in result
        assert "animation_events" in result
        assert "tempo" in result
        assert "frequency_bands" in result

        # Check animation events
        events = result["animation_events"]
        assert "beats" in events
        assert "sections" in events
        assert "onsets" in events
        assert "energy_peaks" in events

    def test_analyze_for_animation_beat_division(self, mock_analyzer):
        """Test beat division parameter."""
        # Test with division of 2
        result = mock_analyzer.analyze_for_animation(Path("test.wav"), beat_division=2)
        beat_events = result["animation_events"]["beats"]

        # With 4 beats and division of 2, we should get beats at indices 0 and 2
        assert len(beat_events) == 2
        assert beat_events == [0.5, 1.5]

    def test_analyze_for_animation_onset_filtering(self, mock_analyzer):
        """Test onset filtering with minimum interval."""
        result = mock_analyzer.analyze_for_animation(
            Path("test.wav"), min_onset_interval=0.6
        )

        filtered_onsets = result["animation_events"]["onsets"]

        # Check that onsets are properly filtered
        for i in range(1, len(filtered_onsets)):
            assert filtered_onsets[i] - filtered_onsets[i - 1] >= 0.6

    def test_tempo_data_structure(self, mock_analyzer):
        """Test tempo data has correct structure."""
        result = mock_analyzer.analyze_for_animation(Path("test.wav"))
        tempo_data = result["tempo"]

        assert "bpm" in tempo_data
        assert "beat_times" in tempo_data
        assert "beat_count" in tempo_data
        assert tempo_data["bpm"] == 120.0
        assert tempo_data["beat_count"] == 4
        assert len(tempo_data["beat_times"]) == 4

    def test_frequency_bands_structure(self, mock_analyzer):
        """Test frequency bands data structure."""
        result = mock_analyzer.analyze_for_animation(Path("test.wav"))
        bands = result["frequency_bands"]

        assert "times" in bands
        assert "bass_energy" in bands
        assert "mid_energy" in bands
        assert "high_energy" in bands

    def test_convert_boundaries_to_sections(self, mock_analyzer):
        """Test conversion of boundaries to section objects."""
        boundaries = [0.0, 30.5, 60.0, 90.5, 120.0]
        sections = mock_analyzer._convert_boundaries_to_sections(boundaries)

        assert len(sections) == 4  # 5 boundaries -> 4 sections
        assert sections[0]["start"] == 0.0
        assert sections[0]["end"] == 30.5
        assert sections[0]["label"] == "section_1"
        assert sections[1]["start"] == 30.5
        assert sections[1]["end"] == 60.0
        assert sections[1]["label"] == "section_2"
        assert sections[3]["start"] == 90.5
        assert sections[3]["end"] == 120.0
        assert sections[3]["label"] == "section_4"

    def test_convert_boundaries_to_sections_empty(self, mock_analyzer):
        """Test conversion with empty or insufficient boundaries."""
        assert mock_analyzer._convert_boundaries_to_sections([]) == []
        assert mock_analyzer._convert_boundaries_to_sections([0.0]) == []


class TestAudioAnalyzerHelpers:
    """Test helper methods of AudioAnalyzer."""

    def test_filter_onsets_empty(self):
        """Test filtering empty onset array."""
        analyzer = AudioAnalyzer()
        result = analyzer._filter_onsets(np.array([]), 1.0)
        assert result == []

    def test_filter_onsets_single(self):
        """Test filtering single onset."""
        analyzer = AudioAnalyzer()
        result = analyzer._filter_onsets(np.array([1.5]), 1.0)
        assert result == [1.5]

    def test_filter_onsets_multiple(self):
        """Test filtering multiple onsets with interval."""
        analyzer = AudioAnalyzer()
        onsets = np.array([0.0, 0.5, 1.0, 1.3, 2.5, 2.7, 4.0])
        result = analyzer._filter_onsets(onsets, 1.0)

        # Should keep: 0.0, 1.0, 2.5, 4.0
        assert result == [0.0, 1.0, 2.5, 4.0]

    def test_save_analysis_creates_json(self, tmp_path):
        """Test saving analysis results to JSON."""
        analyzer = AudioAnalyzer()

        test_data = {
            "duration": 10.0,
            "tempo": {"bpm": 120.0},
            "animation_events": {"beats": [1.0, 2.0, 3.0], "sections": [0.0, 5.0]},
        }

        output_file = tmp_path / "analysis.json"
        analyzer.save_analysis(test_data, output_file)

        assert output_file.exists()

        # Verify content
        with open(output_file) as f:
            loaded = json.load(f)

        assert loaded == test_data


@pytest.mark.audio
class TestAudioAnalyzerIntegration:
    """Integration tests with real audio processing (if libraries available)."""

    @pytest.fixture
    def sample_audio_path(self):
        """Get path to test audio file from fixtures."""
        audio_file = (
            Path(__file__).parent / "fixtures" / "audio" / "beats_120bpm_5s.wav"
        )

        if not audio_file.exists():
            pytest.skip(f"Audio fixture not found: {audio_file}")

        return audio_file

    def test_real_audio_analysis(self, sample_audio_path):
        """Test analysis with real audio file."""
        analyzer = AudioAnalyzer()

        try:
            result = analyzer.analyze_for_animation(sample_audio_path)

            # Verify we got sensible results
            assert result["duration"] > 0
            assert result["sample_rate"] > 0
            assert len(result["animation_events"]["beats"]) > 0
            assert result["tempo"]["bpm"] > 0

        except ImportError:
            pytest.skip("Audio libraries not available")
