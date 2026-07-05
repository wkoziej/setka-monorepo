# ABOUTME: Host-side loader for beatrix *_analysis.json -> normalized arrays + dt
# ABOUTME: Derives dt from times[] per-track (R3), fps from config (beatrix has none).

"""Load a beatrix ``*_analysis.json`` and produce GN-ready data.

The analysis path comes **directly from** ``VisualizerConfig.analysis_file`` —
NOT from ``RecordingStructureManager.get_analysis_file_path()`` (that takes a
video path and derives a stem, which is the wrong input shape for cymatic).

``dt`` is derived from the analysis grid (``dt = times[1] - times[0]``), which
equals ``hop_length / sample_rate`` and is therefore per-track — never
hardcoded (R3). A guard raises a clear ``ValueError`` when ``len(times) < 2``
so a degenerate analysis fails loudly instead of raising a raw ``IndexError``.

``fps`` is read from ``VisualizerConfig.fps`` because beatrix does not emit an
fps field (it returns only ``duration``, ``sample_rate``, ``tempo``,
``animation_events``, ``frequency_bands``).

Audio selection reuses ``beatrix.core.audio_validator.AudioValidator`` when an
``extracted/`` directory can be resolved from ``base_directory``; otherwise the
loader works from the analysis file alone (the audio path is advisory metadata
here — the analysis JSON is the data source).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

from .config import VisualizerConfig
from .normalization import normalize_band, precompute_envelope

# NOTE: beatrix.core.audio_validator is imported LAZILY inside _resolve_audio.
# Audio detection is advisory; the analysis JSON is the data source. A top-level
# import would pull beatrix -> setka_common -> PyYAML, which the bundled python
# in headless Blender lacks (build_scene runs there). Lazy import keeps the
# in-Blender path clean while host-side behavior is unchanged.

logger = logging.getLogger(__name__)

# beatrix's default librosa hop_length; dt == hop_length / sample_rate. Used
# only as a FALLBACK when an analysis file omits the emitted hop_length field
# (pre-existing on-disk files predate it). beatrix now emits hop_length and the
# loader reads it from the JSON.
DEFAULT_HOP_LENGTH = 512

# The analysis JSON schema major version this loader understands. beatrix emits
# "1.0"; a file with a different MAJOR is a hard error (the shape may differ in
# ways this consumer cannot interpret). A MISSING schema_version is assumed to
# be "1.0" for backward compatibility with files written before the field
# existed.
SUPPORTED_SCHEMA_MAJOR = 1
ASSUMED_SCHEMA_VERSION = "1.0"

# Default envelope decay windows (seconds). Beats are denser/snappier than
# energy peaks. PresetParams.decay/tau can override per preset later.
_BEAT_DECAY = 0.13
_PEAK_DECAY = 0.25


# eq=False: this dataclass holds np.ndarray fields, and the auto-generated
# __eq__ would do `arr == arr` -> an array, which raises when truthy-tested.
@dataclass(eq=False)
class AnalysisData:
    """Structured, GN-ready result of loading + normalizing an analysis file.

    All arrays are ``float32`` and equal length (== ``len(times)``).

    ``raw_beat_times`` / ``raw_peak_times`` are the ORIGINAL event timestamps
    (seconds) straight from the analysis JSON — kept as the ground truth the
    sync-verification harness compares against (so a wrong envelope index
    produces a real, nonzero deviation rather than a tautology).
    """

    bass: np.ndarray
    mid: np.ndarray
    high: np.ndarray
    beat_env: np.ndarray
    peak_env: np.ndarray
    times: np.ndarray
    dt: float
    sample_rate: int
    duration: float
    fps: int
    raw_beat_times: list[float] = field(default_factory=list)
    raw_peak_times: list[float] = field(default_factory=list)
    audio_file: Optional[Path] = None


def _finite_times(raw, label: str, path: Path) -> list[float]:
    """Coerce event times to float and drop non-finite (NaN/inf) values.

    A corrupt analysis with a NaN/inf timestamp would otherwise crash downstream
    at ``int(round(t/dt))``. Dropped values are logged once with a count.
    """
    out: list[float] = []
    dropped = 0
    for t in raw:
        f = float(t)
        if np.isfinite(f):
            out.append(f)
        else:
            dropped += 1
    if dropped:
        logger.warning(
            "analysis_loader: dropped %d non-finite %s time(s): %s",
            dropped,
            label,
            path,
        )
    return out


def _validate_schema_version(data: dict, path: Path) -> None:
    """Validate the analysis ``schema_version`` major against this consumer.

    - MISSING ``schema_version`` ⇒ assume ``"1.0"`` (backward compat for files
      written before beatrix emitted the field).
    - A parseable major equal to ``SUPPORTED_SCHEMA_MAJOR`` ⇒ OK.
    - A different major ⇒ hard ``ValueError`` (the shape may differ in ways this
      consumer cannot interpret).
    - An unparseable version string ⇒ hard ``ValueError``.

    Args:
        data: the parsed analysis JSON.
        path: the analysis file path (for error messages).

    Raises:
        ValueError: on a mismatched or malformed major version.
    """
    raw = data.get("schema_version", ASSUMED_SCHEMA_VERSION)
    try:
        major = int(str(raw).split(".", 1)[0])
    except (ValueError, TypeError):
        raise ValueError(
            f"Analysis file has a malformed schema_version {raw!r} "
            f"(expected e.g. '1.0'): {path}"
        )
    if major != SUPPORTED_SCHEMA_MAJOR:
        raise ValueError(
            f"Analysis schema_version {raw!r} (major {major}) is incompatible "
            f"with this consumer (supports major {SUPPORTED_SCHEMA_MAJOR}.x). "
            f"Re-run beatrix to regenerate: {path}"
        )


def _resolve_audio(config: VisualizerConfig) -> Optional[Path]:
    """Best-effort audio selection via AudioValidator from ``extracted/``.

    Returns the detected audio path when an ``extracted/`` dir is resolvable,
    otherwise ``None`` (analysis-only path). Never fatal for loading — the
    analysis JSON, not the audio, is the data source here.
    """
    if not config.base_directory:
        return None
    extracted_dir = Path(config.base_directory) / "extracted"
    if not extracted_dir.exists():
        return None
    try:
        from beatrix.core.audio_validator import AudioValidator  # lazy: see module note

        return AudioValidator().detect_main_audio(extracted_dir)
    except Exception as exc:  # noqa: BLE001 — advisory only, don't fail the load
        logger.debug("Audio detection skipped: %s", exc)
        return None


def load_analysis(config: VisualizerConfig) -> AnalysisData:
    """Load and normalize a beatrix analysis into GN-ready arrays.

    Args:
        config: Visualizer config; ``analysis_file`` is the JSON path,
            ``fps`` supplies the render fps (beatrix has no fps),
            ``base_directory`` is used for optional audio resolution.

    Returns:
        ``AnalysisData`` with normalized bass/mid/high, precomputed
        beat_env/peak_env, the time grid, dt, sample_rate, duration, fps.

    Raises:
        FileNotFoundError: When ``analysis_file`` does not exist.
        ValueError: When ``len(times) < 2`` (dt cannot be derived).
    """
    path = Path(config.analysis_file)
    if not path.exists():
        raise FileNotFoundError(f"Analysis file not found: {path}")

    data = json.loads(path.read_text())

    # Validate the producer contract version before reading the body: a
    # mismatched major fails fast with a clear message; a missing version is
    # assumed compatible (1.0) for pre-existing on-disk files.
    _validate_schema_version(data, path)

    # Required-key access is wrapped so a malformed analysis file fails with a
    # clear, path-carrying ValueError instead of a bare KeyError.
    try:
        fb = data["frequency_bands"]
        times = np.asarray(fb["times"], dtype=float)
    except KeyError as exc:
        raise ValueError(f"Analysis file missing required key {exc}: {path}")

    if len(times) < 2:
        raise ValueError(
            f"Analysis 'times' has {len(times)} sample(s); need >= 2 to derive "
            f"dt = times[1] - times[0]. File: {path}"
        )

    dt = float(times[1] - times[0])
    try:
        sample_rate = int(data["sample_rate"])
        duration = float(data["duration"])
        bass_raw = fb["bass_energy"]
        mid_raw = fb["mid_energy"]
        high_raw = fb["high_energy"]
    except KeyError as exc:
        raise ValueError(f"Analysis file missing required key {exc}: {path}")

    # Sanity: dt should match hop_length / sample_rate (advisory log only).
    # Read the EMITTED hop_length (beatrix now writes it); fall back to the
    # default 512 only when the field is absent (pre-existing files).
    hop_length = int(data.get("hop_length", DEFAULT_HOP_LENGTH))
    expected_dt = hop_length / sample_rate
    if not np.isclose(dt, expected_dt, atol=1e-4):
        logger.warning(
            "dt=%.6f from times[] differs from hop/sr=%.6f (hop=%d, sr=%d)",
            dt,
            expected_dt,
            hop_length,
            sample_rate,
        )

    bass = normalize_band(bass_raw)
    mid = normalize_band(mid_raw)
    high = normalize_band(high_raw)

    # Preset can override the envelope decays (PresetParams validates > 0);
    # otherwise fall back to the module defaults.
    beat_decay = config.preset.decay if config.preset is not None else _BEAT_DECAY
    peak_decay = config.preset.tau if config.preset is not None else _PEAK_DECAY

    ae = data.get("animation_events", {})
    # Drop non-finite event times (NaN/inf from a corrupt analysis) before they
    # reach precompute_envelope / verify_sync, where int(round(nan/dt)) would
    # raise "cannot convert float NaN to integer". Mirrors the NaN coercion in
    # normalize_band: a single bad sample must not crash the whole load.
    raw_beat_times = _finite_times(ae.get("beats", []), "beats", path)
    raw_peak_times = _finite_times(ae.get("energy_peaks", []), "energy_peaks", path)
    beat_env = precompute_envelope(raw_beat_times, times, decay=beat_decay)
    peak_env = precompute_envelope(raw_peak_times, times, decay=peak_decay)

    audio_file = _resolve_audio(config)

    return AnalysisData(
        bass=bass,
        mid=mid,
        high=high,
        beat_env=beat_env,
        peak_env=peak_env,
        times=times,
        dt=dt,
        sample_rate=sample_rate,
        duration=duration,
        fps=config.fps,
        raw_beat_times=raw_beat_times,
        raw_peak_times=raw_peak_times,
        audio_file=audio_file,
    )
