# ABOUTME: Per-track p99 band normalization + precomputed decay envelopes (host-side)
# ABOUTME: Lifted from the proven Spike 1 norm()/env() in research/build_visualizer_v2.py

"""Deterministic, per-track normalization and event-envelope precompute.

Settled by Spike 1 (real CC0 jazz, 48k): the band anchor is the **p99**
percentile — robust to single transients (max-scaling under-uses the range;
p95 clips ~5%). Normalization is per-band, deterministic, and zero-guarded.

Event envelopes (beats / energy_peaks) are precomputed in numpy as separate
float channels — moving the event semantics out of the Geometry Nodes graph
(approach C). For each event we fill a decaying ramp ``max(0, 1 - k*dt/decay)``
from the event's nearest sample index onward, taking the elementwise max so
overlapping events do not cancel.

Both functions return ``float32`` arrays ready to be written as mesh attributes
via ``foreach_set``.
"""

from __future__ import annotations

from typing import Sequence, Union

import numpy as np

ArrayLike = Union[Sequence[float], np.ndarray]


def normalize_band(arr: ArrayLike) -> np.ndarray:
    """Normalize a raw STFT band to ``[0, 1]`` using the p99 anchor.

    ``clip(arr / p99, 0, 1)``. If ``p99 <= 0`` (constant/near-zero band) the
    result is all zeros — the zero-guard prevents division by zero.

    Args:
        arr: Raw band magnitudes (e.g. ``frequency_bands.bass_energy``).

    Returns:
        ``float32`` array of the same length, values in ``[0, 1]``.
    """
    a = np.asarray(arr, dtype=float)
    p = np.percentile(a, 99)
    if p > 0:
        out = np.clip(a / p, 0.0, 1.0)
    else:
        out = np.zeros_like(a)
    return out.astype(np.float32)


def precompute_envelope(
    event_times: Sequence[float],
    times: np.ndarray,
    decay: float,
) -> np.ndarray:
    """Precompute a decaying envelope over the analysis time grid.

    For each event time, the nearest sample index ``i = round(t/dt)`` is set to
    ``1.0`` and a linear ramp ``max(0, 1 - k*dt/decay)`` decays over the
    following ``int(decay/dt)`` samples. Overlapping events combine via
    elementwise max, so a fresh event always re-peaks to ``1.0``.

    Args:
        event_times: Event timestamps in seconds (beats or energy_peaks).
            An empty sequence yields an all-zeros envelope (no exception).
        times: The analysis time grid (``frequency_bands.times``).
        decay: Ramp length in seconds.

    Returns:
        ``float32`` array of length ``len(times)``, values in ``[0, 1]``.
    """
    times = np.asarray(times, dtype=float)
    n = len(times)
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
