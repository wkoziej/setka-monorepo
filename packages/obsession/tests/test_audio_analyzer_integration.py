# ABOUTME: Integration tests for AudioAnalyzer with real audio files
# ABOUTME: Validates output data structure and values for animation use

"""Integration tests for audio analyzer with real audio files."""

import json
import pytest
from pathlib import Path
import numpy as np

from src.core.audio_analyzer import AudioAnalyzer


@pytest.mark.audio
@pytest.mark.integration
class TestAudioAnalyzerIntegration:
    """Integration tests with real audio files."""

    @pytest.fixture
    def audio_fixtures_dir(self):
        """Get path to audio fixtures directory."""
        return Path(__file__).parent / "fixtures" / "audio"

    @pytest.fixture
    def analyzer(self):
        """Create AudioAnalyzer instance."""
        return AudioAnalyzer()

    def test_analyze_sine_wave(self, analyzer, audio_fixtures_dir):
        """Test analysis of simple sine wave."""
        audio_file = audio_fixtures_dir / "sine_440hz_1s.wav"

        if not audio_file.exists():
            pytest.skip(f"Audio fixture not found: {audio_file}")

        result = analyzer.analyze_for_animation(audio_file)

        # Basic checks
        assert result["duration"] == pytest.approx(1.0, rel=0.1)
        assert result["sample_rate"] > 0

        # Tempo detection might be unreliable for pure sine
        assert "tempo" in result
        assert "animation_events" in result

        # Should have minimal beats/onsets for pure tone
        assert len(result["animation_events"]["onsets"]) < 10

    def test_analyze_beat_pattern(self, analyzer, audio_fixtures_dir):
        """Test analysis of audio with clear beat pattern."""
        audio_file = audio_fixtures_dir / "beats_120bpm_5s.wav"

        if not audio_file.exists():
            pytest.skip(f"Audio fixture not found: {audio_file}")

        result = analyzer.analyze_for_animation(audio_file, beat_division=4)

        # Check duration
        assert result["duration"] == pytest.approx(5.0, rel=0.1)

        # Check tempo detection (should be close to 120 BPM)
        assert result["tempo"]["bpm"] == pytest.approx(120.0, rel=0.2)  # 20% tolerance

        # Check beats
        beats = result["tempo"]["beat_times"]
        assert len(beats) > 0

        # Check beat intervals (should be ~0.5s for 120 BPM)
        if len(beats) > 1:
            intervals = np.diff(beats)
            avg_interval = np.mean(intervals)
            assert avg_interval == pytest.approx(0.5, rel=0.3)

        # Check animation events
        events = result["animation_events"]
        assert len(events["beats"]) > 0
        # With beat_division=4, we should have roughly beats/4 events (but can be off by 1)
        expected_beat_events = len(beats) // 4
        assert abs(len(events["beats"]) - expected_beat_events) <= 1

        # Energy peaks should exist
        assert "energy_peaks" in events

    def test_analyze_multi_section(self, analyzer, audio_fixtures_dir):
        """Test analysis of audio with multiple sections."""
        audio_file = audio_fixtures_dir / "multi_section_10s.wav"

        if not audio_file.exists():
            pytest.skip(f"Audio fixture not found: {audio_file}")

        result = analyzer.analyze_for_animation(audio_file)

        # Check duration
        assert result["duration"] == pytest.approx(10.0, rel=0.1)

        # Should detect section boundaries
        sections = result["animation_events"]["sections"]
        assert len(sections) >= 2  # At least some boundaries

        # Check frequency bands over time
        bands = result["frequency_bands"]
        assert "times" in bands
        assert "bass_energy" in bands
        assert "mid_energy" in bands
        assert "high_energy" in bands

        # Verify energy arrays have consistent length
        time_points = len(bands["times"])
        assert len(bands["bass_energy"]) == time_points
        assert len(bands["mid_energy"]) == time_points
        assert len(bands["high_energy"]) == time_points

        # Bass should be strongest in first section (0-3s)
        bass_start = np.mean(bands["bass_energy"][: time_points // 3])
        bass_end = np.mean(bands["bass_energy"][2 * time_points // 3 :])
        # First section should have more bass energy
        assert bass_start > bass_end * 0.5

    def test_onset_filtering(self, analyzer, audio_fixtures_dir):
        """Test onset filtering with different intervals."""
        audio_file = audio_fixtures_dir / "beats_120bpm_5s.wav"

        if not audio_file.exists():
            pytest.skip(f"Audio fixture not found: {audio_file}")

        # Test with different minimum intervals
        result_1s = analyzer.analyze_for_animation(audio_file, min_onset_interval=1.0)
        result_2s = analyzer.analyze_for_animation(audio_file, min_onset_interval=2.0)

        onsets_1s = result_1s["animation_events"]["onsets"]
        onsets_2s = result_2s["animation_events"]["onsets"]

        # Longer interval should result in fewer onsets
        assert len(onsets_2s) <= len(onsets_1s)

        # Verify minimum interval is respected
        for i in range(1, len(onsets_2s)):
            assert onsets_2s[i] - onsets_2s[i - 1] >= 2.0

    def test_save_and_load_analysis(self, analyzer, audio_fixtures_dir, tmp_path):
        """Test saving and loading analysis results."""
        audio_file = audio_fixtures_dir / "short_beat_500ms.wav"

        if not audio_file.exists():
            pytest.skip(f"Audio fixture not found: {audio_file}")

        # Analyze
        result = analyzer.analyze_for_animation(audio_file)

        # Save
        output_file = tmp_path / "analysis_result.json"
        analyzer.save_analysis(result, output_file)

        # Verify file exists and load
        assert output_file.exists()

        with open(output_file) as f:
            loaded = json.load(f)

        # Verify structure
        assert loaded["duration"] == result["duration"]
        assert loaded["tempo"]["bpm"] == result["tempo"]["bpm"]
        assert len(loaded["animation_events"]["beats"]) == len(
            result["animation_events"]["beats"]
        )

    def test_animation_data_validity(self, analyzer, audio_fixtures_dir):
        """Test that animation data is valid for Blender use."""
        audio_file = audio_fixtures_dir / "beats_120bpm_5s.wav"

        if not audio_file.exists():
            pytest.skip(f"Audio fixture not found: {audio_file}")

        result = analyzer.analyze_for_animation(audio_file)

        # All event times should be within duration
        duration = result["duration"]

        for event_type, events in result["animation_events"].items():
            for event in events:
                if event_type == "sections":
                    # Sections are dict objects with start/end times
                    assert isinstance(event, dict), (
                        f"Section should be dict, got {type(event)}"
                    )
                    assert "start" in event and "end" in event, (
                        f"Section missing start/end: {event}"
                    )
                    assert 0 <= event["start"] <= duration, (
                        f"Section start {event['start']} outside duration {duration}"
                    )
                    assert 0 <= event["end"] <= duration, (
                        f"Section end {event['end']} outside duration {duration}"
                    )
                    assert event["start"] <= event["end"], (
                        f"Section start {event['start']} > end {event['end']}"
                    )
                else:
                    # Other events are timestamps (floats)
                    assert 0 <= event <= duration, (
                        f"{event_type} event at {event} outside duration {duration}"
                    )

        # All times should be positive and sorted
        for event_type, events in result["animation_events"].items():
            if len(events) > 0:
                if event_type == "sections":
                    # Sections are sorted by start time
                    start_times = [s["start"] for s in events]
                    assert all(t >= 0 for t in start_times), (
                        f"{event_type} has negative start times"
                    )
                    assert start_times == sorted(start_times), (
                        f"{event_type} sections not sorted by start time"
                    )
                else:
                    # Other events are timestamp lists
                    assert all(t >= 0 for t in events), (
                        f"{event_type} has negative times"
                    )
                    assert events == sorted(events), f"{event_type} events not sorted"

        # Frequency band times should match band data length
        band_times = result["frequency_bands"]["times"]
        for band in ["bass_energy", "mid_energy", "high_energy"]:
            assert len(result["frequency_bands"][band]) == len(band_times)


@pytest.mark.audio
def test_cli_style_usage(tmp_path):
    """Test typical CLI usage pattern."""
    # This test simulates how the CLI will use the analyzer
    # Use existing fixture file instead of generating on the fly
    audio_file = Path(__file__).parent / "fixtures" / "audio" / "beats_120bpm_5s.wav"

    if not audio_file.exists():
        pytest.skip(f"Audio fixture not found: {audio_file}")

    # Create analyzer
    analyzer = AudioAnalyzer()

    # Analyze with typical parameters
    result = analyzer.analyze_for_animation(
        audio_file,
        beat_division=8,  # Switch every 8 beats
        min_onset_interval=1.5,  # Filter close onsets
    )

    # Save results
    output_json = tmp_path / "test_analysis.json"
    analyzer.save_analysis(result, output_json)

    # Verify output is suitable for Blender
    assert output_json.exists()

    with open(output_json) as f:
        data = json.load(f)

    # Check all required fields for animation
    assert "duration" in data
    assert "tempo" in data
    assert "animation_events" in data
    assert all(
        key in data["animation_events"]
        for key in ["beats", "sections", "onsets", "energy_peaks"]
    )
