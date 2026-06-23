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


# ---------------------------------------------------------------------------
# Unit 2.2 — versioned, complete, finite JSON contract
# ---------------------------------------------------------------------------

# JSON-Schema-style description of the EMITTED analysis dict (not the old
# DATA_FLOW_SPECIFICATION body). Validated structurally below.
EMITTED_CONTRACT = {
    "schema_version": str,
    "hop_length": int,
    "n_fft": int,
    "duration": (int, float),
    "sample_rate": int,
    "tempo": {
        "bpm": (int, float),
        "beat_times": list,
        "beat_count": int,
    },
    "animation_events": {
        "beats": list,
        "sections": list,
        "onsets": list,
        "energy_peaks": list,
    },
    "frequency_bands": {
        "times": list,
        "bass_energy": list,
        "mid_energy": list,
        "high_energy": list,
    },
}


def _validate_against(contract, value, path=""):
    """Recursively assert *value* matches the *contract* shape spec."""
    if isinstance(contract, dict):
        assert isinstance(value, dict), f"{path}: expected dict, got {type(value)}"
        for key, sub in contract.items():
            assert key in value, f"{path}: missing key '{key}'"
            _validate_against(sub, value[key], f"{path}.{key}")
    else:
        assert isinstance(value, contract), (
            f"{path}: expected {contract}, got {type(value)}"
        )


class TestContractFields:
    """Unit 2.2: producer contract is explicit, versioned, and correct."""

    @pytest.fixture
    def silence_result(self, tmp_path):
        audio = _write_silence(tmp_path / "contract.wav", 22050)
        return AudioAnalyzer().analyze_for_animation(audio)

    @pytest.fixture
    def tone_result(self, tmp_path):
        """A percussive click track at 120 BPM so beat events are non-empty.

        A pure tone yields no detectable beats, which would make the native-
        float assertion vacuous; clicks guarantee a populated beats array.
        """
        sr = 22050
        n = int(4.0 * sr)
        y = np.zeros(n, dtype=np.float32)
        for i in range(8):  # clicks every 0.5s == 120 BPM
            start = int(i * 0.5 * sr)
            y[start : start + 200] = 0.9
        pcm = np.int16(y * 32000)
        path = tmp_path / "clicks.wav"
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(pcm.tobytes())
        return AudioAnalyzer().analyze_for_animation(path)

    def test_schema_version_emitted(self, silence_result):
        assert silence_result["schema_version"] == "1.0"

    def test_hop_length_and_n_fft_emitted(self, silence_result):
        assert silence_result["hop_length"] == 512
        assert silence_result["n_fft"] == 2048

    def test_beat_events_are_native_float(self, tone_result):
        beats = tone_result["animation_events"]["beats"]
        assert len(beats) > 0, "click track should produce at least one beat event"
        assert all(type(b) is float for b in beats), (
            f"beat_events must be native float, got {[type(b) for b in beats]}"
        )

    def test_output_matches_emitted_contract(self, silence_result):
        _validate_against(EMITTED_CONTRACT, silence_result)

    def test_output_is_json_serializable(self, tone_result):
        import json

        # Must serialize with the default encoder — no numpy scalars leaking.
        json.dumps(tone_result)

    def test_no_nan_or_inf_anywhere(self, silence_result, tone_result):
        for result in (silence_result, tone_result):
            for n in _all_numeric_values(result):
                assert math.isfinite(n), f"non-finite value leaked: {n}"


class TestFrequencyBandsGuard:
    """Unit 2.2: zero analysis frames from a non-empty signal raises."""

    def test_zero_frames_raises_explicit_error(self):
        """A (pathological) empty STFT for a non-empty signal must raise."""
        from unittest.mock import Mock

        analyzer = AudioAnalyzer()
        analyzer._librosa = Mock()
        # STFT yields zero frames despite a non-empty input signal.
        analyzer._librosa.stft.return_value = np.empty((1025, 0))
        analyzer._librosa.fft_frequencies.return_value = np.linspace(0, 22050, 1025)
        analyzer._librosa.frames_to_time.return_value = np.array([])

        with pytest.raises(ValueError, match="no frames"):
            analyzer._analyze_frequency_bands(np.ones(100), 22050)


class TestSanitizeNonFinite:
    """Unit 2.2: NaN/inf in band/peak arrays are scrubbed before serialize."""

    def test_find_bass_peaks_drops_nan_times(self):
        analyzer = AudioAnalyzer()
        times = [0.0, 1.0, float("nan"), 2.0, 3.0]
        bass = [0.0, 5.0, 5.0, 5.0, 0.0]
        peaks = analyzer._find_bass_peaks(times, bass)
        assert all(math.isfinite(p) for p in peaks)

    def test_band_energy_sanitized_in_output(self, tmp_path):
        audio = _write_silence(tmp_path / "s.wav", 22050)
        result = AudioAnalyzer().analyze_for_animation(audio)
        for band in ("bass_energy", "mid_energy", "high_energy"):
            for v in result["frequency_bands"][band]:
                assert math.isfinite(v)
