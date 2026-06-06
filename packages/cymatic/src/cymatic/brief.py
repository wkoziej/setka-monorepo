# ABOUTME: Host-side audio structure brief for cymatic clip authoring (no bpy).
# ABOUTME: Derives per-stem activity + master energy/drops from beatrix analyses.

"""Structure brief: a compact, LLM-facing map of what a recording's audio does.

The brief is built from the beatrix per-track analyses (``analysis/index.json``
plus the per-stem ``*_analysis.json``) and answers the questions a clip author
needs *before* authoring a cymatic scene:

- **Per-stem activity** ("who plays when") — time intervals where each stem is
  audible, derived from a smoothed, p99-normalized broadband energy envelope.
- **ENTER/EXIT events** — when instruments come in and drop out.
- **Master energy profile** — coarse low/mid/high levels over time plus the
  moments where energy jumps (drops).

The segmentation here is **energy/activity-based**, deliberately NOT the beatrix
``animation_events.sections`` (chroma/MFCC agglomerative ``k=10``), which wastes
resolution on silence and merges the musical body into one block.

This module is host-side (pure numpy + matplotlib for the optional heatmap); it
never imports ``bpy``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple

import numpy as np

from cymatic.normalization import normalize_band

# --- detection parameters (defaults validated on real recordings; tunable) --- #
SMOOTH_S = 1.0  # moving-average window for the energy envelope
ACTIVITY_THRESH = 0.10  # smoothed p99-normalized energy above this == "active"
GAP_MERGE_S = 2.0  # merge active intervals separated by a gap shorter than this
MIN_SEGMENT_S = 2.5  # drop active intervals shorter than this
SILENT_MAX_S = 5.0  # a stem active for less than this total is flagged silent
DROP_DELTA = 0.30  # master energy jump between windows that counts as a drop
MASTER_WINDOW_S = 5.0  # coarse window for master energy levels/drops
LEVEL_LOW = 0.25  # mean energy below this -> "low"
LEVEL_HIGH = 0.55  # mean energy at/above this -> "high"; between -> "mid"

# Marker recorded in the brief so consumers know the segmentation source (R8).
SEGMENTATION_SOURCE = "energy/activity-based (NOT beatrix.sections)"

Interval = Tuple[float, float]


@dataclass
class StemActivity:
    """Activity of one stem across the recording timeline."""

    label: str
    active: List[Interval] = field(default_factory=list)
    silent: bool = False


@dataclass
class StructureEvent:
    """A stem entering or exiting the mix at a point in time."""

    t: float
    kind: str  # "enter" | "exit"
    stem: str


@dataclass
class EnergyLevel:
    """A contiguous span of master energy at a coarse level."""

    start: float
    end: float
    level: str  # "low" | "mid" | "high"


@dataclass
class StructureBrief:
    """The complete structure brief for one recording."""

    recording: str
    duration: float
    bpm: float
    stems: List[StemActivity] = field(default_factory=list)
    events: List[StructureEvent] = field(default_factory=list)
    master_levels: List[EnergyLevel] = field(default_factory=list)
    drops: List[float] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to the canonical, JSON-safe brief dict (R5).

        All numeric fields are coerced to plain ``float`` so no ``np.float64``
        leaks into the JSON. The ``segmentation`` field records the source of the
        timeline split (R8).
        """
        return {
            "recording": self.recording,
            "duration": round(float(self.duration), 1),
            "bpm": round(float(self.bpm), 1),
            "segmentation": SEGMENTATION_SOURCE,
            "stems": [
                {
                    "label": s.label,
                    "active": [[float(a), float(b)] for a, b in s.active],
                    "silent": bool(s.silent),
                }
                for s in self.stems
            ],
            "events": [
                {"t": float(e.t), "kind": e.kind, "stem": e.stem} for e in self.events
            ],
            "master_energy": {
                "levels": [
                    {
                        "start": float(lvl.start),
                        "end": float(lvl.end),
                        "level": lvl.level,
                    }
                    for lvl in self.master_levels
                ],
                "drops": [float(d) for d in self.drops],
            },
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


def _fmt_intervals(intervals: List[Interval]) -> str:
    """Render activity intervals as a compact ``[a–b, c–d]`` string."""
    if not intervals:
        return "[]"
    return "[" + ", ".join(f"{a:.1f}–{b:.1f}" for a, b in intervals) + "]"


def render_markdown(brief: StructureBrief) -> str:
    """Render a compact, LLM-facing markdown view of the brief (R5).

    Designed for a clip-authoring agent to read once: exact timestamps, semantic
    grouping, small footprint. Silent stems are flagged "skip mapping".
    """
    lines = [
        f"# Structure brief — {brief.recording}",
        (
            f"{brief.duration:.1f}s · ~{brief.bpm:.0f} BPM · "
            f"{len(brief.stems)} stems · {SEGMENTATION_SOURCE}"
        ),
        "",
        "## Per-stem activity (who plays when)",
    ]
    if brief.stems:
        for s in brief.stems:
            tag = "  (≈silent — skip mapping)" if s.silent else ""
            lines.append(f"- {s.label}: {_fmt_intervals(s.active)}{tag}")
    else:
        lines.append("- (no stems — master-only brief)")

    lines += ["", "## Events"]
    if brief.events:
        for e in brief.events:
            lines.append(f"- {e.t:.1f}s  {e.kind.upper()}  {e.stem}")
    else:
        lines.append("- (none)")

    lines += ["", "## Master energy"]
    for lvl in brief.master_levels:
        lines.append(f"- {lvl.start:.1f}–{lvl.end:.1f}s  {lvl.level}")
    drops = ", ".join(f"{d:.1f}s" for d in brief.drops) if brief.drops else "none"
    lines.append(f"drops: {drops}")

    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# Pure detection helpers
# --------------------------------------------------------------------------- #
def _smooth(values: np.ndarray, dt: float, window_s: float) -> np.ndarray:
    """Boxcar moving average over a ``window_s``-second window."""
    win = max(1, int(round(window_s / dt)))
    if win <= 1:
        return np.asarray(values, dtype=float)
    kernel = np.ones(win, dtype=float) / win
    return np.convolve(np.asarray(values, dtype=float), kernel, mode="same")


def activity_intervals(
    times: np.ndarray,
    energy_norm: np.ndarray,
    *,
    threshold: float = ACTIVITY_THRESH,
    smooth_s: float = SMOOTH_S,
    gap_merge_s: float = GAP_MERGE_S,
    min_segment_s: float = MIN_SEGMENT_S,
) -> List[Interval]:
    """Find intervals where a (already p99-normalized) energy envelope is active.

    Smooths the envelope, thresholds it, groups consecutive active samples into
    runs, merges runs separated by a gap shorter than ``gap_merge_s``, then drops
    runs shorter than ``min_segment_s``. Returns ``(start, end)`` pairs in seconds
    rounded to 0.1 s.
    """
    times = np.asarray(times, dtype=float)
    if len(times) < 2:
        return []
    dt = float(times[1] - times[0])
    sm = _smooth(energy_norm, dt, smooth_s)
    mask = sm > threshold
    idx = np.where(mask)[0]
    if len(idx) == 0:
        return []

    # Group consecutive indices into runs.
    splits = np.where(np.diff(idx) > 1)[0] + 1
    groups = np.split(idx, splits)
    runs: List[Interval] = [
        (float(times[g[0]]), float(times[g[-1]] + dt)) for g in groups
    ]

    # Merge runs separated by a sub-threshold gap.
    merged: List[Interval] = []
    for start, end in runs:
        if merged and start - merged[-1][1] < gap_merge_s:
            merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))

    # Drop too-short segments; round for a tidy brief.
    return [
        (round(start, 1), round(end, 1))
        for start, end in merged
        if (end - start) >= min_segment_s
    ]


def enter_exit_events(stems: List[StemActivity]) -> List[StructureEvent]:
    """Derive ENTER/EXIT events from per-stem activity intervals, sorted by time."""
    events: List[StructureEvent] = []
    for stem in stems:
        for start, end in stem.active:
            events.append(StructureEvent(t=start, kind="enter", stem=stem.label))
            events.append(StructureEvent(t=end, kind="exit", stem=stem.label))
    events.sort(key=lambda e: (e.t, e.kind, e.stem))
    return events


def _level_for(mean: float) -> str:
    if mean < LEVEL_LOW:
        return "low"
    if mean < LEVEL_HIGH:
        return "mid"
    return "high"


def master_profile(
    times: np.ndarray,
    energy_norm: np.ndarray,
    *,
    window_s: float = MASTER_WINDOW_S,
    drop_delta: float = DROP_DELTA,
) -> Tuple[List[EnergyLevel], List[float]]:
    """Reduce a master energy envelope to coarse levels + drop timestamps.

    Windows the envelope into ``window_s`` chunks, buckets each window mean into
    low/mid/high, merges adjacent equal levels into contiguous spans, and marks a
    drop wherever a window mean jumps by more than ``drop_delta`` over the prior
    window.
    """
    times = np.asarray(times, dtype=float)
    energy_norm = np.asarray(energy_norm, dtype=float)
    if len(times) < 2:
        return [], []
    dt = float(times[1] - times[0])
    win = max(1, int(window_s / dt))

    means: List[float] = []
    starts: List[float] = []
    for i in range(0, len(energy_norm), win):
        means.append(float(energy_norm[i : i + win].mean()))
        starts.append(float(times[i]))
    ends = starts[1:] + [float(times[-1] + dt)]

    # Merge adjacent windows sharing a level into contiguous spans.
    levels: List[EnergyLevel] = []
    for start, end, mean in zip(starts, ends, means):
        lvl = _level_for(mean)
        if levels and levels[-1].level == lvl:
            levels[-1] = EnergyLevel(levels[-1].start, round(end, 1), lvl)
        else:
            levels.append(EnergyLevel(round(start, 1), round(end, 1), lvl))

    drops = [
        round(starts[k], 1)
        for k in range(1, len(means))
        if means[k] - means[k - 1] > drop_delta
    ]
    return levels, drops


# --------------------------------------------------------------------------- #
# Loading + assembly
# --------------------------------------------------------------------------- #
def _load_broadband(analysis_path: Path) -> Tuple[np.ndarray, np.ndarray]:
    """Read a beatrix analysis JSON and return ``(times, broadband_norm)``.

    Broadband energy is the sum of the three frequency bands, p99-normalized via
    the same anchor cymatic uses for its visual channels.
    """
    data = json.loads(Path(analysis_path).read_text())
    fb = data["frequency_bands"]
    times = np.asarray(fb["times"], dtype=float)
    raw = (
        np.asarray(fb["bass_energy"], dtype=float)
        + np.asarray(fb["mid_energy"], dtype=float)
        + np.asarray(fb["high_energy"], dtype=float)
    )
    return times, normalize_band(raw)


def render_heatmap(recording_dir: Path, output_png: Path) -> None:
    """Render the arrangement-map PNG (stem × time × energy) + master panel (R6).

    matplotlib is imported lazily with the headless ``Agg`` backend so importing
    ``cymatic.brief`` (and ``generate_brief``) stays light and works without a
    display. Degrades to a master-only figure when no stems are present.

    Raises:
        FileNotFoundError: when ``analysis/index.json`` is absent.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from setka_common import load_analysis_index

    recording_dir = Path(recording_dir)
    index = load_analysis_index(recording_dir)
    if index is None:
        raise FileNotFoundError(f"analysis/index.json not found under {recording_dir}.")

    stems = index.stems()
    master_entry = index.master()

    # Common time grid spanning the longest known duration.
    durations = [e.duration for e in index.sources if e.duration]
    duration = max(durations) if durations else 60.0
    grid = np.linspace(0.0, duration, 1200)

    matrix: List[np.ndarray] = []
    labels: List[str] = []
    for entry in stems:
        times, energy = _load_broadband(entry.resolved_analysis_path(recording_dir))
        matrix.append(np.interp(grid, times, energy, left=0.0, right=0.0))
        labels.append(entry.label)

    # Master energy + drops for the bottom panel.
    master_curve = None
    drops: List[float] = []
    if master_entry is not None:
        mtimes, menergy = _load_broadband(
            master_entry.resolved_analysis_path(recording_dir)
        )
        master_curve = np.interp(grid, mtimes, menergy, left=0.0, right=0.0)
        _, drops = master_profile(mtimes, menergy)

    n_panels = (1 if matrix else 0) + (1 if master_curve is not None else 0)
    n_panels = max(n_panels, 1)
    fig, axes = plt.subplots(n_panels, 1, figsize=(16, 2 + 2 * n_panels), squeeze=False)
    col = axes[:, 0]
    ax_i = 0

    if matrix:
        ax = col[ax_i]
        ax.imshow(
            np.array(matrix),
            aspect="auto",
            origin="upper",
            extent=[0.0, duration, len(matrix) - 0.5, -0.5],
            cmap="magma",
            vmin=0.0,
            vmax=1.0,
            interpolation="nearest",
        )
        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels(labels, fontsize=9)
        ax.set_title("Who plays when (broadband energy per stem)", fontsize=10)
        ax_i += 1

    if master_curve is not None:
        ax = col[ax_i]
        ax.plot(grid, master_curve, color="#d1495b", lw=0.7)
        ax.fill_between(grid, master_curve, color="#d1495b", alpha=0.15)
        for d in drops:
            ax.axvline(d, color="black", lw=0.8, alpha=0.5)
        ax.set_ylim(0.0, 1.05)
        ax.set_xlim(0.0, duration)
        ax.set_ylabel("master energy")
        ax.set_xlabel("time [s]")
        ax.set_title("Master energy + drops", fontsize=10)

    fig.suptitle(f"Structure map — {recording_dir.name}", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    output_png = Path(output_png)
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, dpi=110)
    plt.close(fig)


def generate_brief(recording_dir: Path) -> StructureBrief:
    """Build a :class:`StructureBrief` from a recording's beatrix analyses.

    Reads ``analysis/index.json`` (via ``setka_common.load_analysis_index``),
    computes the master energy profile and per-stem activity, and assembles the
    brief. Degrades to a master-only brief when no stems are present.

    Raises:
        FileNotFoundError: when ``analysis/index.json`` is absent.
    """
    from setka_common import load_analysis_index

    recording_dir = Path(recording_dir)
    index = load_analysis_index(recording_dir)
    if index is None:
        raise FileNotFoundError(
            f"analysis/index.json not found under {recording_dir}. "
            "Run `beatrix analyze-recording` first."
        )

    duration = 0.0
    bpm = 0.0
    master_levels: List[EnergyLevel] = []
    drops: List[float] = []

    master_entry = index.master()
    if master_entry is not None:
        mpath = master_entry.resolved_analysis_path(recording_dir)
        mdata = json.loads(Path(mpath).read_text())
        bpm = float(mdata.get("tempo", {}).get("bpm", 0.0))
        duration = float(mdata.get("duration", 0.0))
        mtimes, menergy = _load_broadband(mpath)
        master_levels, drops = master_profile(mtimes, menergy)

    stems: List[StemActivity] = []
    for entry in index.stems():
        stimes, senergy = _load_broadband(entry.resolved_analysis_path(recording_dir))
        intervals = activity_intervals(stimes, senergy)
        total_active = sum(end - start for start, end in intervals)
        stems.append(
            StemActivity(
                label=entry.label,
                active=intervals,
                silent=total_active < SILENT_MAX_S,
            )
        )
        if not duration and entry.duration:
            duration = float(entry.duration)

    return StructureBrief(
        recording=recording_dir.name,
        duration=duration,
        bpm=bpm,
        stems=stems,
        events=enter_exit_events(stems),
        master_levels=master_levels,
        drops=drops,
    )
