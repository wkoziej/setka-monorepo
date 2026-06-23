# ABOUTME: Tests for cymatic.normalization (per-track p99 norm + envelope precompute)
# ABOUTME: Settled by Spike 1 — p99 anchor, per-band, deterministic, zero-guard.

"""Tests for normalization.normalize_band and precompute_envelope.

Method settled by Spike 1: per-track p99 normalization with a zero-guard,
deterministic. Envelope precompute uses the proven env() pattern from
research/build_visualizer_v2.py: for each event, fill a decaying ramp
``max(0, 1 - k*dt/decay)`` from the event index onward.
"""

import numpy as np
import pytest

from cymatic.normalization import normalize_band, precompute_envelope


class TestNormalizeBand:
    def test_output_in_unit_interval(self):
        arr = np.array([0.0, 1.0, 2.0, 5.0, 10.0])
        out = normalize_band(arr)
        assert out.min() >= 0.0
        assert out.max() <= 1.0

    def test_length_preserved(self):
        arr = np.linspace(0.0, 7.0, 137)
        out = normalize_band(arr)
        assert len(out) == len(arr)

    def test_p99_anchor_clips_above(self):
        # A single big transient must not collapse the rest of the range:
        # p99 anchor clips the outlier to 1.0 rather than scaling everything
        # down. With ~1% of samples above the bulk, p99 sits near the bulk so
        # the bulk maps high, and the transient clips to 1.0.
        bulk = np.full(990, 1.0)
        transients = np.full(10, 100.0)
        arr = np.concatenate([bulk, transients])
        out = normalize_band(arr)
        # The transients clip to 1.0 rather than defining the scale.
        assert out.max() == pytest.approx(1.0)
        assert out[-1] == pytest.approx(1.0)
        # Anchor is p99, so the divisor stays far below the 100.0 transient
        # peak — the bulk is not crushed to near-zero the way max-scaling
        # (divide by 100) would crush it.
        p99 = np.percentile(arr, 99)
        assert p99 < 100.0
        assert out[0] == pytest.approx(min(1.0, 1.0 / p99))

    def test_zero_guard_all_zeros(self):
        # Constant (near-)zero energy band: p99 == 0 -> zeros, no div-by-zero.
        arr = np.zeros(50)
        out = normalize_band(arr)
        assert np.all(out == 0.0)
        assert len(out) == 50

    def test_zero_guard_no_exception_and_finite(self):
        arr = np.zeros(10)
        out = normalize_band(arr)
        assert np.all(np.isfinite(out))

    def test_deterministic_bit_for_bit(self):
        rng = np.random.default_rng(0)
        arr = rng.random(200) * 13.0
        a = normalize_band(arr)
        b = normalize_band(arr)
        assert np.array_equal(a, b)

    def test_returns_float32(self):
        arr = np.array([1.0, 2.0, 3.0])
        out = normalize_band(arr)
        assert out.dtype == np.float32

    def test_accepts_plain_list(self):
        out = normalize_band([0.0, 1.0, 2.0, 3.0])
        assert isinstance(out, np.ndarray)
        assert out.max() <= 1.0


class TestPrecomputeEnvelope:
    def test_event_on_sample_peaks_at_index(self):
        dt = 0.01
        times = np.arange(100) * dt
        # event exactly on sample index 10 (t = 0.10)
        env = precompute_envelope([0.10], times, decay=0.05)
        assert env[10] == pytest.approx(1.0)
        # decays afterwards
        assert env[11] < env[10]

    def test_event_between_samples_rounds_to_nearest(self):
        dt = 0.01
        times = np.arange(100) * dt
        # event at 0.104 -> round(0.104/0.01) = 10
        env = precompute_envelope([0.104], times, decay=0.05)
        assert env[10] == pytest.approx(1.0)

    def test_decaying_ramp_values(self):
        dt = 0.01
        times = np.arange(100) * dt
        decay = 0.05  # ramp spans 5 samples
        env = precompute_envelope([0.0], times, decay=decay)
        # k=0 -> 1.0; k=1 -> 1 - 1*dt/decay = 0.8; k=2 -> 0.6 ...
        assert env[0] == pytest.approx(1.0)
        assert env[1] == pytest.approx(0.8, abs=1e-6)
        assert env[2] == pytest.approx(0.6, abs=1e-6)

    def test_empty_events_all_zeros_no_exception(self):
        dt = 0.01
        times = np.arange(50) * dt
        env = precompute_envelope([], times, decay=0.1)
        assert np.all(env == 0.0)
        assert len(env) == len(times)

    def test_length_matches_times(self):
        times = np.arange(73) * 0.011
        env = precompute_envelope([0.1, 0.3], times, decay=0.05)
        assert len(env) == len(times)

    def test_overlapping_events_take_max(self):
        dt = 0.01
        times = np.arange(100) * dt
        decay = 0.05
        # two close events; at a shared index the later event's fresh ramp wins via max
        env = precompute_envelope([0.0, 0.02], times, decay=decay)
        # index 2 is k=2 from event0 (0.6) and k=0 from event1 (1.0) -> max 1.0
        assert env[2] == pytest.approx(1.0)

    def test_deterministic(self):
        times = np.arange(100) * 0.01
        a = precompute_envelope([0.1, 0.5, 0.9], times, decay=0.07)
        b = precompute_envelope([0.1, 0.5, 0.9], times, decay=0.07)
        assert np.array_equal(a, b)

    def test_returns_float32(self):
        times = np.arange(20) * 0.01
        env = precompute_envelope([0.05], times, decay=0.03)
        assert env.dtype == np.float32

    def test_no_negative_values(self):
        times = np.arange(100) * 0.01
        env = precompute_envelope([0.0, 0.5], times, decay=0.05)
        assert env.min() >= 0.0

    def test_single_sample_times_returns_zeros_no_index_error(self):
        # len(times) < 2 must not raise IndexError on times[1]; it yields a
        # zero envelope of the same length.
        env = precompute_envelope([0.0], np.array([0.0]), decay=0.05)
        assert env.shape == (1,)
        assert np.all(env == 0.0)
        assert env.dtype == np.float32

    def test_empty_times_returns_empty(self):
        env = precompute_envelope([0.0], np.array([]), decay=0.05)
        assert len(env) == 0


class TestPrecomputeEnvelopeVectorizedEquivalence:
    """The vectorized precompute must match the original scalar semantics
    bit-for-bit: round-to-nearest event index, ramp max(0, 1 - k*dt/decay),
    elementwise max over overlapping events."""

    @staticmethod
    def _scalar_reference(event_times, times, decay):
        times = np.asarray(times, dtype=float)
        n = len(times)
        if n < 2:
            return np.zeros(n, dtype=np.float32)
        dt = float(times[1] - times[0])
        env = np.zeros(n, dtype=np.float32)
        steps = int(decay / dt)
        for t in event_times:
            i = int(round(t / dt))
            for k in range(0, steps + 1):
                j = i + k
                if 0 <= j < n:
                    env[j] = max(env[j], 1.0 - k * dt / decay)
        return env

    @pytest.mark.parametrize("decay", [0.03, 0.05, 0.13, 0.25, 0.5])
    def test_matches_scalar_reference_random_events(self, decay):
        rng = np.random.default_rng(7)
        times = np.arange(500) * 0.010667  # 48k-like grid
        events = sorted(rng.random(40) * (times[-1]))
        got = precompute_envelope(events, times, decay=decay)
        want = self._scalar_reference(events, times, decay)
        assert np.array_equal(got, want)

    def test_matches_scalar_reference_events_past_end(self):
        # events whose ramp runs off the end of the grid clamp identically
        times = np.arange(20) * 0.01
        events = [0.18, 0.19, 0.20]
        got = precompute_envelope(events, times, decay=0.1)
        want = self._scalar_reference(events, times, 0.1)
        assert np.array_equal(got, want)

    def test_matches_scalar_reference_events_before_start(self):
        # negative event time rounds to a negative/zero index; the ramp tail
        # that lands in-grid must match the scalar fill
        times = np.arange(20) * 0.01
        events = [-0.005, 0.0]
        got = precompute_envelope(events, times, decay=0.05)
        want = self._scalar_reference(events, times, 0.05)
        assert np.array_equal(got, want)


class TestNonFiniteBands:
    def test_non_finite_values_coerced_to_zero(self, caplog):
        # NaN/inf must not poison percentile or make the band vanish; they are
        # coerced to 0 with a logged warning, leaving finite values intact.
        arr = np.array([0.0, np.nan, 1.0, np.inf, 2.0, -np.inf])
        with caplog.at_level("WARNING"):
            out = normalize_band(arr)
        assert np.all(np.isfinite(out))
        assert out.max() <= 1.0
        assert out.min() >= 0.0
        # the finite, non-zero entries still produce signal
        assert out.max() > 0.0
        assert any("non-finite" in r.message for r in caplog.records)
