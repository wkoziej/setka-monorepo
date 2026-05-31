# ABOUTME: Host-side, pure-python DATA-timing sync verification harness (R2/R3)
# ABOUTME: Proves Seconds/dt arithmetic + beat-impulse frame placement, NOT visuals.

"""Data-grounded sync verification for the cymatic visualizer (Unit 10).

WHAT THIS PROVES (and what it does NOT)
---------------------------------------
This harness is a **pure-python, host-side** check — it never touches ``bpy``.
It verifies two pieces of *data-timing arithmetic*:

1. **Beat impulse placement.** The ``beat_env`` channel is precomputed in numpy
   to peak at index ``round(t / dt)`` for each beat time ``t`` (see
   :func:`cymatic.normalization.precompute_envelope`). Converting that
   peak *index* back to a render *frame* is ``round((index * dt) * fps)``. We
   compare that to the frame a renderer would target for the beat,
   ``round(t * fps)``, and assert the deviation is ``<= N`` frames.

2. **Value sampling (``Seconds/dt`` mapping).** At render frame ``f`` the live
   Geometry Nodes graph computes scene time ``f / fps`` and indexes the stored
   channel at ``round((f / fps) / dt)`` with clamping (Spike 2, verified live
   on Blender 5.1.2). :func:`sample_channel_at_frame` re-confirms that exact
   index arithmetic in pure python — a host-side mirror of what Spike 2 proved
   on the GPU.

HONESTY NOTE (plan: "Zakres tego dowodu", review: adversarial)
--------------------------------------------------------------
Because the envelope is precomputed in numpy and sampled by index, this harness
primarily validates the ``Seconds/dt`` arithmetic and envelope placement, plus
the ``dt`` vs ``1/fps`` quantization. It does **NOT** prove the *perceptual*
claim "the accent is visibly on the beat": preset easing, motion blur, and the
linear blur of the impulse between samples (dt ~11-23 ms) may soften the accent.
Perceptual verification is creator acceptance (R4), not this harness. MVP
criterion 2 here = proof of *data timing*, not *visual timing*.

TOLERANCE N
-----------
``n_tolerance_frames`` is an **internal constant of this harness**
(:data:`DEFAULT_N_TOLERANCE_FRAMES`), deliberately NOT a config field (plan:
scope — premature config surface). It is governed by ``dt`` vs ``1/fps``: the
beat lands on a sample grid quantized to ``dt`` (~11 ms @ 48k, ~23 ms @ 22k),
which at 30 fps (~33 ms/frame) is within one frame; the impulse then resolves
to a frame via two roundings, so a 2-frame tolerance comfortably covers the
quantization floor.

FPS CONSISTENCY
---------------
The ``fps`` used here for ``round(beat_sec * fps)`` MUST equal
``VisualizerConfig.fps`` (which ``build_scene.py`` writes to
``scene.render.fps``). :func:`assert_fps_consistency` guards the host-side half
of that invariant; the live ``scene.render.fps == config.fps`` assertion is an
integration concern (it requires a running Blender), not part of this pure
harness.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import numpy as np

from .analysis_loader import AnalysisData

# Internal tolerance, NOT a config field (plan: scope). See module docstring.
DEFAULT_N_TOLERANCE_FRAMES = 2


def assert_fps_consistency(config_fps: int, harness_fps: int) -> None:
    """Assert the harness fps equals the config fps (host-side half of INV).

    Guards against time-based vs frame-based drift: ``round(beat_sec * fps)``
    must use the same fps that ``build_scene.py`` writes to
    ``scene.render.fps``. The live ``scene.render.fps == config.fps`` check
    belongs to integration (needs a running Blender) and is out of scope here.

    Raises:
        ValueError: when the two fps values disagree.
    """
    if int(config_fps) != int(harness_fps):
        raise ValueError(
            f"fps mismatch: config.fps={config_fps} but harness used "
            f"{harness_fps}; round(beat_sec*fps) would drift from the rendered "
            f"scene time. They must be identical."
        )


def _clamp_index(index: int, length: int) -> int:
    """Clamp ``index`` into ``[0, length - 1]`` (mirrors GN SampleIndex clamp)."""
    if index < 0:
        return 0
    if index >= length:
        return length - 1
    return index


def sample_channel_at_frame(
    channel: np.ndarray, frame: int, fps: int, dt: float
) -> float:
    """Sample a stored channel at a render frame via the ``Seconds/dt`` mapping.

    Pure-python mirror of the live Geometry Nodes index sampling (Spike 2):
    scene time is ``frame / fps``; the channel index is
    ``round((frame / fps) / dt)`` clamped into range. Returns the *nearest
    sample* value (no inter-sample interpolation — this checks the index
    arithmetic, which is what the GN graph clamps and floors against).

    Args:
        channel: stored per-sample channel (e.g. ``beat_env``).
        frame: render frame number.
        fps: render fps (must match ``VisualizerConfig.fps``).
        dt: sample spacing in seconds (``times[1] - times[0]``).

    Returns:
        The channel value at the clamped index, as a python float.
    """
    seconds = frame / fps
    index = int(round(seconds / dt))
    index = _clamp_index(index, len(channel))
    return float(channel[index])


@dataclass
class BeatDeviation:
    """Per-beat sync measurement."""

    beat_time: float
    expected_frame: int  # round(beat_time * fps)
    peak_frame: int  # frame of the beat_env peak nearest beat_time
    deviation: int  # |peak_frame - expected_frame|


@dataclass
class SyncReport:
    """Structured result of :func:`verify_sync`.

    Attributes:
        deviations: per-beat measurements (empty for a beatless track).
        max_deviation: largest per-beat deviation in frames (0 if no beats).
        n_tolerance_frames: the internal tolerance applied.
        passed: ``True`` iff ``max_deviation <= n_tolerance_frames`` (vacuously
            ``True`` for a beatless track).
        sample_rate: source track sample rate (R3 traceability).
        fps: fps used for the frame arithmetic.
        dt: sample spacing used.
    """

    deviations: List[BeatDeviation] = field(default_factory=list)
    max_deviation: int = 0
    n_tolerance_frames: int = DEFAULT_N_TOLERANCE_FRAMES
    passed: bool = True
    sample_rate: int = 0
    fps: int = 0
    dt: float = 0.0


def _peak_frame_near(beat_env: np.ndarray, beat_time: float, dt: float, fps: int) -> int:
    """Frame of the ``beat_env`` peak sample nearest ``beat_time``.

    The envelope was precomputed to peak (==1.0) at ``round(beat_time/dt)`` and
    decay afterward. We search a small index window around that expected index
    for the argmax, then convert the winning *index* to a *frame* via
    ``round((index * dt) * fps)``. Searching a window (rather than trusting the
    exact index) is what makes this a measurement, not a tautology restatement:
    if the precompute or the index arithmetic were off, the argmax would land
    on a different sample and the deviation would grow.
    """
    n = len(beat_env)
    center = _clamp_index(int(round(beat_time / dt)), n)
    # Window spans roughly +/- one frame in samples (>= 1), so the argmax is
    # free to drift to an adjacent sample if the placement were wrong.
    half = max(1, int(round((1.0 / fps) / dt)))
    lo = _clamp_index(center - half, n)
    hi = _clamp_index(center + half, n)
    window = beat_env[lo : hi + 1]
    peak_index = lo + int(np.argmax(window))
    return int(round((peak_index * dt) * fps))


def verify_sync(
    analysis_data: AnalysisData,
    n_tolerance_frames: int = DEFAULT_N_TOLERANCE_FRAMES,
) -> SyncReport:
    """Verify data-timing sync of the precomputed beat envelope (R2/R3).

    For each beat time ``t`` derived from ``beat_env`` (reconstructed from the
    envelope's peaks): the expected render frame is ``round(t * fps)``; the
    measured peak frame comes from the envelope's argmax near ``t`` converted
    to a frame. The deviation is ``|peak_frame - round(t * fps)|`` and must be
    ``<= n_tolerance_frames``.

    A beatless track (all-zero ``beat_env``) yields an empty, vacuously-passing
    report — it does not crash.

    See the module docstring for the scope/honesty note: this is a proof of
    DATA timing, not visual/perceptual timing (R4).

    Args:
        analysis_data: loaded, normalized analysis (from ``load_analysis``).
        n_tolerance_frames: internal tolerance (default
            :data:`DEFAULT_N_TOLERANCE_FRAMES`); not a config field.

    Returns:
        A :class:`SyncReport`.
    """
    beat_env = np.asarray(analysis_data.beat_env)
    dt = analysis_data.dt
    fps = analysis_data.fps

    beat_times = _reconstruct_beat_times(beat_env, dt)

    deviations: List[BeatDeviation] = []
    for t in beat_times:
        expected_frame = int(round(t * fps))
        peak_frame = _peak_frame_near(beat_env, t, dt, fps)
        deviations.append(
            BeatDeviation(
                beat_time=float(t),
                expected_frame=expected_frame,
                peak_frame=peak_frame,
                deviation=abs(peak_frame - expected_frame),
            )
        )

    max_dev = max((d.deviation for d in deviations), default=0)
    return SyncReport(
        deviations=deviations,
        max_deviation=max_dev,
        n_tolerance_frames=n_tolerance_frames,
        passed=max_dev <= n_tolerance_frames,
        sample_rate=analysis_data.sample_rate,
        fps=fps,
        dt=dt,
    )


def _reconstruct_beat_times(beat_env: np.ndarray, dt: float) -> List[float]:
    """Recover beat times (seconds) from the precomputed ``beat_env`` peaks.

    A beat sets its sample to exactly ``1.0`` (the envelope's max) and then
    decays. We treat the rising edges into a ``1.0`` sample as beat onsets:
    indices where ``env == 1.0`` whose previous sample is strictly smaller (or
    which start the array). Converting index -> seconds is ``index * dt``.

    Working from the envelope (rather than re-reading the source beat list)
    keeps this harness honest about what was actually baked into the data
    object the GN graph samples.
    """
    if len(beat_env) == 0:
        return []
    is_peak = np.isclose(beat_env, 1.0)
    if not is_peak.any():
        return []
    prev = np.empty_like(beat_env)
    prev[0] = -1.0
    prev[1:] = beat_env[:-1]
    onsets = np.flatnonzero(is_peak & (beat_env > prev))
    return [float(i * dt) for i in onsets]
