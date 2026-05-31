# ABOUTME: Tests for cymatic.sync_verification — DATA-timing sync proof (R2/R3)
# ABOUTME: Runs on synthetic + real fixtures of different sample_rate (48k, 44k).

"""Tests for the data-grounded sync-verification harness (Unit 10).

SCOPE / HONESTY (mirrors the plan's "Zakres tego dowodu"):
This harness proves the **data-timing arithmetic** only — that the precomputed
``beat_env`` impulse peaks at the render frame ``round(beat_sec * fps)`` within
``N`` frames, and that the ``Seconds/dt`` index-sampling that the live Geometry
Nodes graph performs (Spike 2) reproduces the stored channel value in pure
python. It does **NOT** prove perceptual / visual timing ("you can see the
accent land on the beat") — preset easing, motion blur, and linear blur of the
impulse between samples (dt ~11-23 ms) may soften the accent. Perceptual
verification belongs to creator acceptance (R4), not here.

R3 is exercised by running the same harness on two real tracks of different
sample_rate (48 kHz and 44.1 kHz) — therefore different ``dt`` — and asserting
sync holds on both.
"""

from pathlib import Path

import numpy as np
import pytest

from cymatic.analysis_loader import AnalysisData, load_analysis
from cymatic.config import VisualizerConfig
from cymatic.normalization import precompute_envelope
from cymatic.sync_verification import (
    DEFAULT_N_TOLERANCE_FRAMES,
    SyncReport,
    assert_fps_consistency,
    sample_channel_at_frame,
    verify_sync,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
FIX_48K = REPO_ROOT / "research/audio/analysis/jazz_120s_48k_analysis.json"
FIX_44K = REPO_ROOT / "research/audio/analysis/jazz_120s_44k_analysis.json"
FIX_120BPM = REPO_ROOT / "research/audio/analysis/beat_120bpm_12s_analysis.json"


@pytest.fixture(autouse=True)
def _require_fixtures():
    for f in (FIX_48K, FIX_44K, FIX_120BPM):
        if not f.exists():
            pytest.skip(f"fixture missing: {f}")


def _config(analysis_file: Path, fps: int = 30) -> VisualizerConfig:
    return VisualizerConfig(
        analysis_file=str(analysis_file),
        output_mp4="/tmp/out.mp4",
        base_directory=str(analysis_file.parent),
        fps=fps,
    )


def _synthetic(
    beats, fps=30, dt=0.01, duration=None, decay=0.13, sample_rate=48000
) -> AnalysisData:
    """Build a minimal AnalysisData with a beat_env precomputed for ``beats``."""
    if duration is None:
        duration = (max(beats) + 1.0) if beats else 2.0
    n = int(round(duration / dt))
    times = np.arange(n, dtype=float) * dt
    beat_env = precompute_envelope(beats, times, decay=decay)
    zeros = np.zeros(n, dtype=np.float32)
    return AnalysisData(
        bass=zeros,
        mid=zeros.copy(),
        high=zeros.copy(),
        beat_env=beat_env,
        peak_env=zeros.copy(),
        times=times,
        dt=dt,
        sample_rate=sample_rate,
        duration=duration,
        fps=fps,
    )


# --------------------------------------------------------------------------- #
# Value-sampling arithmetic (mirrors the live Seconds/dt mapping from Spike 2) #
# --------------------------------------------------------------------------- #
class TestValueSampling:
    def test_sample_channel_matches_clamped_index(self):
        data = _synthetic([0.5, 1.0], fps=30, dt=0.01)
        chan = data.beat_env
        for frame in range(0, 60):
            expected_idx = int(round((frame / data.fps) / data.dt))
            expected_idx = max(0, min(expected_idx, len(chan) - 1))
            assert sample_channel_at_frame(chan, frame, data.fps, data.dt) == (
                chan[expected_idx]
            )

    def test_sample_clamps_beyond_track_end(self):
        data = _synthetic([0.5], fps=30, dt=0.01, duration=1.0)
        # Frame far past the end must clamp to the last sample, not raise.
        val = sample_channel_at_frame(
            data.beat_env, frame=10_000, fps=data.fps, dt=data.dt
        )
        assert val == data.beat_env[-1]


# --------------------------------------------------------------------------- #
# Happy path: synthetic beat at a known time peaks within +/- N frames         #
# --------------------------------------------------------------------------- #
class TestHappyPath:
    def test_single_beat_peaks_at_expected_frame(self):
        # Beat at 1.0s, fps=30 -> expected frame 30.
        data = _synthetic([1.0], fps=30, dt=0.01)
        report = verify_sync(data)
        assert report.passed
        assert report.max_deviation <= DEFAULT_N_TOLERANCE_FRAMES
        assert len(report.deviations) == 1
        dev = report.deviations[0]
        assert dev.beat_time == pytest.approx(1.0)
        assert dev.expected_frame == 30
        assert abs(dev.peak_frame - 30) <= DEFAULT_N_TOLERANCE_FRAMES

    def test_multiple_beats_all_within_tolerance(self):
        data = _synthetic([0.5, 1.0, 2.5, 4.0], fps=30, dt=0.01)
        report = verify_sync(data)
        assert report.passed
        assert all(d.deviation <= DEFAULT_N_TOLERANCE_FRAMES for d in report.deviations)


# --------------------------------------------------------------------------- #
# R3: real fixtures of different sample_rate -> sync holds on both              #
# --------------------------------------------------------------------------- #
class TestR3RealFixturesBothSampleRates:
    def test_48k_sync_holds(self):
        data = load_analysis(_config(FIX_48K, fps=30))
        report = verify_sync(data)
        assert report.sample_rate == 48000
        assert report.passed, (
            f"48k max deviation {report.max_deviation} > "
            f"{DEFAULT_N_TOLERANCE_FRAMES}"
        )

    def test_44k_sync_holds(self):
        data = load_analysis(_config(FIX_44K, fps=30))
        report = verify_sync(data)
        assert report.sample_rate == 44100
        assert report.passed, (
            f"44k max deviation {report.max_deviation} > "
            f"{DEFAULT_N_TOLERANCE_FRAMES}"
        )

    def test_both_sample_rates_have_different_dt(self):
        d48 = load_analysis(_config(FIX_48K, fps=30))
        d44 = load_analysis(_config(FIX_44K, fps=30))
        # Distinct dt is precisely the R3 regression a single-sr spike misses.
        assert d48.dt != d44.dt

    def test_120bpm_synthetic_fixture_sync_holds(self):
        data = load_analysis(_config(FIX_120BPM, fps=30))
        report = verify_sync(data)
        assert report.passed


# --------------------------------------------------------------------------- #
# Edge: beat near end of track -> clamp, no out-of-range index                  #
# --------------------------------------------------------------------------- #
class TestEdgeBeatNearEnd:
    def test_beat_at_last_sample_does_not_raise(self):
        # Beat at the very last representable time.
        data = _synthetic([1.99], fps=30, dt=0.01, duration=2.0)
        report = verify_sync(data)  # must not raise IndexError
        assert len(report.deviations) == 1
        # Peak frame is clamped within the renderable frame range.
        last_frame = int(round((len(data.beat_env) - 1) * data.dt * data.fps))
        assert report.deviations[0].peak_frame <= last_frame


# --------------------------------------------------------------------------- #
# Error path: track with no beats -> graceful report, no crash                  #
# --------------------------------------------------------------------------- #
class TestEdgeNoBeats:
    def test_no_beats_reports_gracefully(self):
        data = _synthetic([], fps=30, dt=0.01, duration=2.0)
        report = verify_sync(data)
        assert isinstance(report, SyncReport)
        assert report.deviations == []
        # No beats means nothing to violate -> vacuously passing, max dev 0.
        assert report.passed
        assert report.max_deviation == 0


# --------------------------------------------------------------------------- #
# fps-consistency helper                                                        #
# --------------------------------------------------------------------------- #
class TestFpsConsistency:
    def test_matching_fps_ok(self):
        # config.fps must equal the fps used for round(beat_sec*fps);
        # the live scene.render.fps == config.fps check is integration-only.
        assert_fps_consistency(config_fps=30, harness_fps=30)

    def test_mismatched_fps_raises(self):
        with pytest.raises(ValueError):
            assert_fps_consistency(config_fps=30, harness_fps=60)
