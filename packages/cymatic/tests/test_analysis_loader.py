# ABOUTME: Tests for cymatic.analysis_loader (load beatrix JSON -> normalized arrays + dt)
# ABOUTME: Uses real fixtures of different sample_rate (R3): 48k and 44k jazz.

"""Tests for analysis_loader.load_analysis.

Covers Unit 5 scenarios:
- bands normalized to [0,1], length == len(times)
- dt derived per sample_rate (R3: 48k and 44k give different dt)
- len(times) < 2 -> clear error (not IndexError)
- empty energy_peaks -> peak_env all zeros, no exception
- fps read from VisualizerConfig, not from JSON
- full loader pipeline on a real file -> equal-length arrays
"""

import json
from pathlib import Path

import numpy as np
import pytest

from cymatic.analysis_loader import load_analysis
from cymatic.config import VisualizerConfig

REPO_ROOT = Path(__file__).resolve().parents[3]
FIX_48K = REPO_ROOT / "research/audio/analysis/jazz_120s_48k_analysis.json"
FIX_44K = REPO_ROOT / "research/audio/analysis/jazz_120s_44k_analysis.json"
FIX_BEATRIX = (
    REPO_ROOT
    / "packages/beatrix/tests/fixtures/audio/beats_120bpm_5s_analysis.json"
)


def _config(analysis_file: Path, fps: int = 30, base_directory: str = "") -> VisualizerConfig:
    return VisualizerConfig(
        analysis_file=str(analysis_file),
        output_mp4="/tmp/out.mp4",
        base_directory=base_directory or str(analysis_file.parent),
        fps=fps,
    )


@pytest.fixture(autouse=True)
def _require_fixtures():
    for f in (FIX_48K, FIX_44K, FIX_BEATRIX):
        if not f.exists():
            pytest.skip(f"fixture missing: {f}")


class TestBandsNormalized:
    def test_bands_in_unit_interval(self):
        res = load_analysis(_config(FIX_48K))
        for band in (res.bass, res.mid, res.high):
            assert band.min() >= 0.0
            assert band.max() <= 1.0

    def test_band_lengths_equal_times(self):
        res = load_analysis(_config(FIX_48K))
        d = json.loads(FIX_48K.read_text())
        n = len(d["frequency_bands"]["times"])
        assert len(res.bass) == n
        assert len(res.mid) == n
        assert len(res.high) == n


class TestDtPerSampleRate:
    def test_dt_48k(self):
        res = load_analysis(_config(FIX_48K))
        assert res.sample_rate == 48000
        assert res.dt == pytest.approx(0.010667, abs=1e-5)

    def test_dt_44k(self):
        res = load_analysis(_config(FIX_44K))
        assert res.sample_rate == 44100
        assert res.dt == pytest.approx(0.011610, abs=1e-5)

    def test_dt_differs_across_sample_rates(self):
        r48 = load_analysis(_config(FIX_48K))
        r44 = load_analysis(_config(FIX_44K))
        assert r48.dt != r44.dt

    def test_dt_consistent_with_hop_over_sr(self):
        # dt should equal hop_length(512)/sample_rate
        res = load_analysis(_config(FIX_48K))
        assert res.dt == pytest.approx(512 / 48000, abs=1e-5)


class TestDegenerateTimes:
    def test_len_times_below_two_raises_clear_error(self, tmp_path):
        bad = {
            "duration": 0.0,
            "sample_rate": 44100,
            "animation_events": {"beats": [], "energy_peaks": []},
            "frequency_bands": {
                "times": [0.0],
                "bass_energy": [0.0],
                "mid_energy": [0.0],
                "high_energy": [0.0],
            },
        }
        p = tmp_path / "x_analysis.json"
        p.write_text(json.dumps(bad))
        with pytest.raises(ValueError) as exc:
            load_analysis(_config(p))
        # must be a clear domain error, not a raw IndexError
        assert not isinstance(exc.value, IndexError)
        msg = str(exc.value).lower()
        assert "times" in msg


class TestEnvelopes:
    def test_empty_energy_peaks_zeros(self, tmp_path):
        d = json.loads(FIX_48K.read_text())
        d["animation_events"]["energy_peaks"] = []
        p = tmp_path / "nopeaks_analysis.json"
        p.write_text(json.dumps(d))
        res = load_analysis(_config(p))
        assert np.all(res.peak_env == 0.0)
        assert len(res.peak_env) == len(res.bass)

    def test_envelopes_equal_length(self):
        res = load_analysis(_config(FIX_48K))
        n = len(res.bass)
        assert len(res.beat_env) == n
        assert len(res.peak_env) == n

    def test_beat_env_has_signal(self):
        res = load_analysis(_config(FIX_48K))
        assert res.beat_env.max() > 0.0


class TestFpsFromConfig:
    def test_fps_read_from_config_not_json(self):
        # beatrix JSON has NO fps key; loader must take it from config.
        d = json.loads(FIX_48K.read_text())
        assert "fps" not in d
        res = load_analysis(_config(FIX_48K, fps=60))
        assert res.fps == 60

    def test_missing_fps_key_no_error(self):
        # absence of 'fps' in JSON must not raise
        res = load_analysis(_config(FIX_48K, fps=24))
        assert res.fps == 24


class TestErrorPaths:
    def test_missing_analysis_file(self, tmp_path):
        missing = tmp_path / "does_not_exist_analysis.json"
        with pytest.raises(FileNotFoundError):
            load_analysis(_config(missing))


class TestFullPipeline:
    def test_real_file_equal_length_arrays(self):
        res = load_analysis(_config(FIX_44K))
        n = len(res.bass)
        for arr in (res.bass, res.mid, res.high, res.beat_env, res.peak_env):
            assert len(arr) == n
            assert arr.dtype == np.float32

    def test_metadata_populated(self):
        res = load_analysis(_config(FIX_44K))
        assert res.sample_rate == 44100
        assert res.duration == pytest.approx(120.0)
        assert res.dt > 0

    def test_beatrix_synthetic_fixture(self):
        # different source (synthetic beatrix fixture, sr 44100)
        res = load_analysis(_config(FIX_BEATRIX))
        n = len(res.bass)
        assert res.sample_rate == 44100
        assert len(res.beat_env) == n
        assert len(res.peak_env) == n
