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

import logging
from typing import Sequence, Union

import numpy as np

logger = logging.getLogger(__name__)

ArrayLike = Union[Sequence[float], np.ndarray]


def normalize_band(arr: ArrayLike) -> np.ndarray:
    """Normalize a raw STFT band to ``[0, 1]`` using the p99 anchor.

    ``clip(arr / p99, 0, 1)``. If ``p99 <= 0`` (constant/near-zero band) the
    result is all zeros — the zero-guard prevents division by zero.

    Non-finite values (NaN/inf, e.g. a corrupt analysis band) are coerced to
    ``0`` with a logged warning before percentile/clip, so a single bad sample
    does not poison ``np.percentile`` and make the whole band silently vanish.

    Args:
        arr: Raw band magnitudes (e.g. ``frequency_bands.bass_energy``).

    Returns:
        ``float32`` array of the same length, values in ``[0, 1]``.
    """
    a = np.asarray(arr, dtype=float)
    if not np.all(np.isfinite(a)):
        logger.warning(
            "normalize_band: non-finite values in band (n=%d), coercing to 0",
            int(np.count_nonzero(~np.isfinite(a))),
        )
        a = np.nan_to_num(a, nan=0.0, posinf=0.0, neginf=0.0)
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
    # dt needs at least two samples; a degenerate grid yields a zero envelope
    # instead of an IndexError on ``times[1]``.
    if n < 2:
        return np.zeros(n, dtype=np.float32)
    dt = float(times[1] - times[0])
    env = np.zeros(n, dtype=np.float32)

    events = np.asarray(list(event_times), dtype=float)
    if events.size == 0:
        return env

    # Vectorized form of the scalar fill (kept bit-for-bit identical — see the
    # equivalence tests). For each event at rounded index ``i = round(t/dt)``,
    # every ramp step ``k in [0, steps]`` sets index ``i+k`` to the decaying
    # value ``1 - k*dt/decay``; overlapping events combine via elementwise max.
    #
    # Build the full (events x (steps+1)) grid of target indices and ramp
    # values, keep only the in-grid targets, and scatter-max them onto env with
    # ``np.maximum.at`` (the accumulating equivalent of ``env[j] = max(...)``).
    steps = int(decay / dt)
    base = np.round(events / dt).astype(np.int64)  # round-to-nearest, like int(round())
    k = np.arange(steps + 1)
    ramp = (1.0 - k * dt / decay).astype(np.float32)  # k=0 -> 1.0, decaying

    targets = base[:, None] + k[None, :]  # (events, steps+1)
    vals = np.broadcast_to(ramp, targets.shape)

    in_grid = (targets >= 0) & (targets < n)
    flat_idx = targets[in_grid]
    flat_val = vals[in_grid]
    np.maximum.at(env, flat_idx, flat_val)
    return env
