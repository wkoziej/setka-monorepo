# ABOUTME: Edge-case tests for AudioAnalyzer crash hardening + JSON contract
# ABOUTME: Covers degenerate audio (1-sample, sub-second, pure silence) and emitted contract keys

"""Edge-case and contract tests for AudioAnalyzer.

These use real (tiny) audio buffers written to disk rather than mocks, because
the crash paths live inside librosa/scipy calls that mocks would hide.
"""

import math
import wave

import numpy as np
import pytest

from beatrix import AudioAnalyzer


def _write_silence(path, n_samples, sample_rate=22050):
    """Write *n_samples* of pure silence to a mono 16-bit WAV at *path*."""
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * n_samples)
    return path


def _all_numeric_values(obj):
    """Yield every numeric scalar found anywhere in a nested dict/list."""
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _all_numeric_values(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _all_numeric_values(v)
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        yield obj


class TestCrashHardeningShortAudio:
    """Unit 2.1(a): degenerate short / empty input must not crash."""

    def test_one_sample_audio_does_not_crash(self, tmp_path):
        """A 1-sample file must return empty events, not raise."""
        audio = _write_silence(tmp_path / "onesample.wav", 1)
        analyzer = AudioAnalyzer()

        result = analyzer.analyze_for_animation(audio)

        assert result["animation_events"]["energy_peaks"] == []
        assert result["animation_events"]["beats"] == []
        assert result["tempo"]["beat_count"] == 0

    def test_sub_second_audio_does_not_crash(self, tmp_path):
        """A ~0.1s clip (boundaries cluster danger zone) must not crash.

        Few frames previously crashed agglomerative clustering ("more
        clusters than samples"); it must now complete and yield no bass peaks.
        """
        audio = _write_silence(tmp_path / "short.wav", int(0.1 * 22050))
        analyzer = AudioAnalyzer()

        result = analyzer.analyze_for_animation(audio)

        assert result["animation_events"]["energy_peaks"] == []
        assert isinstance(result["animation_events"]["sections"], list)

    def test_empty_audio_does_not_crash(self, tmp_path):
        """A zero-length file must be handled gracefully."""
        audio = _write_silence(tmp_path / "empty.wav", 0)
        analyzer = AudioAnalyzer()

        result = analyzer.analyze_for_animation(audio)

        assert result["animation_events"]["energy_peaks"] == []
        assert result["tempo"]["beat_count"] == 0


class TestCrashHardeningSilentAudio:
    """Unit 2.1(b): silent-but-long input yields an explicit no-rhythm signal."""

    def test_one_second_silence_has_no_rhythm(self, tmp_path):
        """1s of silence: empty peaks and zero beats (not merely no-crash)."""
        audio = _write_silence(tmp_path / "silence1s.wav", 22050)
        analyzer = AudioAnalyzer()

        result = analyzer.analyze_for_animation(audio)

        assert result["animation_events"]["energy_peaks"] == []
        assert result["tempo"]["beat_count"] == 0
        assert result["animation_events"]["beats"] == []

    def test_silent_band_returns_no_bass_peaks(self):
        """Near-zero band energy returns [] before find_peaks is consulted."""
        analyzer = AudioAnalyzer()
        times = list(np.linspace(0.0, 3.0, 130))
        bass_energy = [0.0] * len(times)

        peaks = analyzer._find_bass_peaks(times, bass_energy)

        assert peaks == []


class TestFindBassPeaksGuards:
    """Unit 2.1: direct guards on _find_bass_peaks degenerate inputs."""

    def test_single_time_point_returns_empty(self):
        """len(times) < 2 must short-circuit, not divide by times[-1]."""
        analyzer = AudioAnalyzer()
        assert analyzer._find_bass_peaks([0.0], [0.0]) == []

    def test_zero_duration_returns_empty(self):
        """times[-1] == 0 must not raise OverflowError on int(2/0)."""
        analyzer = AudioAnalyzer()
        assert analyzer._find_bass_peaks([0.0, 0.0], [1.0, 1.0]) == []

    def test_empty_times_returns_empty(self):
        analyzer = AudioAnalyzer()
        assert analyzer._find_bass_peaks([], []) == []
