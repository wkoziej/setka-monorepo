# ABOUTME: Tests for the host-side structure-brief tool (cymatic.brief).
# ABOUTME: Pure-numpy activity/energy detection + brief assembly from analyses.

"""Tests for ``cymatic.brief`` — the audio structure brief for clip authoring.

Covers the pure detection helpers on synthetic envelopes (known inputs) and the
end-to-end ``generate_brief`` over a synthetic recording directory built in
``tmp_path`` (no external fixture files, so nothing skips).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from cymatic import brief as brief_mod
from cymatic.brief import (
    SEGMENTATION_SOURCE,
    EnergyLevel,
    StemActivity,
    StructureBrief,
    StructureEvent,
    activity_intervals,
    enter_exit_events,
    generate_brief,
    main,
    master_profile,
    render_ass,
    render_heatmap,
    render_markdown,
)


# --------------------------------------------------------------------------- #
# Synthetic data helpers
# --------------------------------------------------------------------------- #
def _grid(duration: float, dt: float = 0.5) -> np.ndarray:
    return np.arange(0.0, duration, dt)


def _block(
    times: np.ndarray, start: float, end: float, level: float = 1.0
) -> np.ndarray:
    """Energy array that is ``level`` inside [start, end) and 0 elsewhere."""
    e = np.zeros_like(times)
    e[(times >= start) & (times < end)] = level
    return e


def _write_analysis(
    path: Path, times, bass, mid=None, high=None, *, bpm=120.0, duration=None
):
    times = np.asarray(times, dtype=float)
    bass = np.asarray(bass, dtype=float)
    mid = np.zeros_like(bass) if mid is None else np.asarray(mid, dtype=float)
    high = np.zeros_like(bass) if high is None else np.asarray(high, dtype=float)
    dur = float(times[-1]) if duration is None else duration
    payload = {
        "duration": dur,
        "sample_rate": 44100,
        "tempo": {"bpm": bpm, "beat_times": [], "beat_count": 0},
        "animation_events": {
            "beats": [],
            "sections": [],
            "onsets": [],
            "energy_peaks": [],
        },
        "frequency_bands": {
            "times": times.tolist(),
            "bass_energy": bass.tolist(),
            "mid_energy": mid.tolist(),
            "high_energy": high.tolist(),
        },
    }
    path.write_text(json.dumps(payload))


def _build_recording(
    tmp_path: Path, stems: dict, *, with_master=True, master_energy=None
):
    """Create a recording dir with analysis/index.json + per-stem analyses.

    Args:
        stems: mapping label -> (times, bass_energy) for each stem.
        with_master: whether to include a master entry.
        master_energy: optional (times, energy) for the master; defaults to the
            sum of stem energies on the first stem's grid.
    """
    analysis_dir = tmp_path / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    sources = []

    if with_master:
        if master_energy is None:
            first = next(iter(stems.values()))
            times = first[0]
            energy = np.sum([s[1] for s in stems.values()], axis=0)
        else:
            times, energy = master_energy
        _write_analysis(analysis_dir / "master_analysis.json", times, energy)
        sources.append(
            {
                "role": "master",
                "origin": "mixed",
                "label": "master",
                "source": "mixed/master.wav",
                "analysis": "analysis/master_analysis.json",
                "duration": float(times[-1]),
                "sample_rate": 44100,
            }
        )

    for label, (times, energy) in stems.items():
        fname = f"{label}_analysis.json"
        _write_analysis(analysis_dir / fname, times, energy)
        sources.append(
            {
                "role": "stem",
                "origin": "bitwig",
                "label": label,
                "source": f"bitwig/samples/{label}.wav",
                "analysis": f"analysis/{fname}",
                "duration": float(times[-1]),
                "sample_rate": 44100,
            }
        )

    (analysis_dir / "index.json").write_text(
        json.dumps({"version": 1, "sources": sources})
    )
    return tmp_path


# --------------------------------------------------------------------------- #
# activity_intervals — happy path & edges
# --------------------------------------------------------------------------- #
class TestActivityIntervals:
    def test_single_block(self):
        t = _grid(30.0)
        e = _block(t, 10.0, 20.0)
        iv = activity_intervals(t, e)
        assert len(iv) == 1
        start, end = iv[0]
        assert start == pytest.approx(10.0, abs=1.5)
        assert end == pytest.approx(20.0, abs=1.5)

    def test_all_silent(self):
        t = _grid(30.0)
        e = np.zeros_like(t)
        assert activity_intervals(t, e) == []

    def test_gap_below_merge_is_merged(self):
        t = _grid(40.0)
        # two blocks separated by 1s gap (< GAP_MERGE_S=2.0) -> merged
        e = _block(t, 5.0, 12.0) + _block(t, 13.0, 20.0)
        iv = activity_intervals(t, e)
        assert len(iv) == 1
        assert iv[0][0] == pytest.approx(5.0, abs=1.5)
        assert iv[0][1] == pytest.approx(20.0, abs=1.5)

    def test_gap_above_merge_stays_split(self):
        t = _grid(60.0)
        # two blocks separated by 10s gap -> separate intervals
        e = _block(t, 5.0, 15.0) + _block(t, 35.0, 50.0)
        iv = activity_intervals(t, e)
        assert len(iv) == 2

    def test_short_segment_dropped(self):
        t = _grid(40.0)
        # 1s active block (< MIN_SEGMENT_S=2.5) -> dropped
        e = _block(t, 10.0, 11.0)
        assert activity_intervals(t, e) == []


# --------------------------------------------------------------------------- #
# enter_exit_events
# --------------------------------------------------------------------------- #
class TestEnterExitEvents:
    def test_events_from_intervals(self):
        stems = [
            StemActivity(label="gtr", active=[(7.0, 58.0)], silent=False),
            StemActivity(label="bass", active=[(54.0, 120.0)], silent=False),
        ]
        events = enter_exit_events(stems)
        kinds = {(e.t, e.kind, e.stem) for e in events}
        assert (7.0, "enter", "gtr") in kinds
        assert (58.0, "exit", "gtr") in kinds
        assert (54.0, "enter", "bass") in kinds
        assert (120.0, "exit", "bass") in kinds
        # sorted by time
        assert [e.t for e in events] == sorted(e.t for e in events)

    def test_silent_stem_has_no_events(self):
        stems = [StemActivity(label="dead", active=[], silent=True)]
        assert enter_exit_events(stems) == []


# --------------------------------------------------------------------------- #
# master_profile — levels + drops
# --------------------------------------------------------------------------- #
class TestMasterProfile:
    def test_drop_after_silence_detected(self):
        t = _grid(60.0)
        # silence then a loud body -> a drop near the onset
        e = _block(t, 0.0, 20.0, level=0.0) + _block(t, 20.0, 60.0, level=1.0)
        levels, drops = master_profile(t, e)
        assert any(d == pytest.approx(20.0, abs=6.0) for d in drops)

    def test_levels_cover_low_and_high(self):
        t = _grid(60.0)
        e = _block(t, 0.0, 30.0, level=0.0) + _block(t, 30.0, 60.0, level=1.0)
        levels, _ = master_profile(t, e)
        seen = {lvl.level for lvl in levels}
        assert "low" in seen
        assert "high" in seen
        # levels are contiguous and ordered
        assert levels[0].start == pytest.approx(0.0, abs=0.6)


# --------------------------------------------------------------------------- #
# generate_brief — integration over a synthetic recording dir
# --------------------------------------------------------------------------- #
class TestGenerateBrief:
    def test_happy_master_and_stems(self, tmp_path):
        t = _grid(60.0)
        rec = _build_recording(
            tmp_path,
            stems={
                "gtr": (t, _block(t, 5.0, 30.0)),
                "drums": (t, _block(t, 30.0, 58.0)),
            },
        )
        b = generate_brief(rec)
        assert isinstance(b, StructureBrief)
        assert b.bpm == pytest.approx(120.0)
        assert b.duration == pytest.approx(60.0, abs=1.0)
        labels = {s.label for s in b.stems}
        assert labels == {"gtr", "drums"}
        gtr = next(s for s in b.stems if s.label == "gtr")
        assert not gtr.silent
        assert gtr.active[0][0] == pytest.approx(5.0, abs=1.5)
        # enter/exit events present
        assert any(e.kind == "enter" and e.stem == "gtr" for e in b.events)

    def test_silent_stem_flagged(self, tmp_path):
        t = _grid(60.0)
        rec = _build_recording(
            tmp_path,
            stems={
                "lead": (t, _block(t, 10.0, 40.0)),
                "dead": (t, np.zeros_like(t)),
            },
        )
        b = generate_brief(rec)
        dead = next(s for s in b.stems if s.label == "dead")
        assert dead.silent
        assert dead.active == []

    def test_no_index_raises(self, tmp_path):
        (tmp_path / "analysis").mkdir()
        with pytest.raises((FileNotFoundError, ValueError)):
            generate_brief(tmp_path)

    def test_no_stems_degrades_to_master_only(self, tmp_path):
        t = _grid(60.0)
        analysis_dir = tmp_path / "analysis"
        analysis_dir.mkdir()
        _write_analysis(analysis_dir / "master_analysis.json", t, _block(t, 10.0, 50.0))
        (analysis_dir / "index.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "sources": [
                        {
                            "role": "master",
                            "origin": "mixed",
                            "label": "master",
                            "source": "mixed/master.wav",
                            "analysis": "analysis/master_analysis.json",
                            "duration": float(t[-1]),
                            "sample_rate": 44100,
                        }
                    ],
                }
            )
        )
        b = generate_brief(tmp_path)
        assert b.stems == []
        assert b.master_levels  # master energy profile still present

    def test_stems_with_different_grids(self, tmp_path):
        # one stem at dt=0.5, another at dt=0.25 -> each on its own time axis
        t1 = _grid(60.0, dt=0.5)
        t2 = _grid(60.0, dt=0.25)
        rec = _build_recording(
            tmp_path,
            stems={
                "a": (t1, _block(t1, 5.0, 30.0)),
                "b": (t2, _block(t2, 35.0, 55.0)),
            },
            master_energy=(t1, _block(t1, 5.0, 55.0)),
        )
        b = generate_brief(rec)
        assert {s.label for s in b.stems} == {"a", "b"}


# --------------------------------------------------------------------------- #
# Serialization — JSON canon + markdown render
# --------------------------------------------------------------------------- #
class TestSerialization:
    def _brief(self) -> StructureBrief:
        return StructureBrief(
            recording="rec",
            duration=60.0,
            bpm=120.0,
            stems=[
                StemActivity("gtr", [(5.0, 30.0)], False),
                StemActivity("dead", [], True),
            ],
            events=[
                StructureEvent(5.0, "enter", "gtr"),
                StructureEvent(30.0, "exit", "gtr"),
            ],
            master_levels=[
                EnergyLevel(0.0, 20.0, "low"),
                EnergyLevel(20.0, 60.0, "high"),
            ],
            drops=[20.0],
        )

    def test_to_dict_is_json_serializable(self):
        d = self._brief().to_dict()
        json.dumps(d)  # must not raise (no np.float64 leaking through)
        assert d["segmentation"] == SEGMENTATION_SOURCE
        assert d["stems"][0]["label"] == "gtr"
        assert d["stems"][0]["active"] == [[5.0, 30.0]]
        assert d["stems"][1]["silent"] is True
        assert d["master_energy"]["drops"] == [20.0]
        assert d["master_energy"]["levels"][0]["level"] == "low"

    def test_to_json_roundtrips(self):
        d = json.loads(self._brief().to_json())
        assert d["bpm"] == 120.0
        assert d["duration"] == 60.0
        assert len(d["stems"]) == 2

    def test_markdown_lists_stems_and_marks_silent(self):
        md = render_markdown(self._brief())
        assert "gtr" in md
        assert "dead" in md
        assert "NOT beatrix.sections" in md
        assert "skip" in md.lower()  # silent stem flagged to skip mapping

    def test_markdown_no_stems_does_not_crash(self):
        b = StructureBrief(
            recording="solo",
            duration=60.0,
            bpm=90.0,
            stems=[],
            events=[],
            master_levels=[EnergyLevel(0.0, 60.0, "mid")],
            drops=[],
        )
        md = render_markdown(b)
        assert "solo" in md

    def test_markdown_stays_compact(self):
        md = render_markdown(self._brief())
        assert len(md.encode("utf-8")) < 6000


# --------------------------------------------------------------------------- #
# Heatmap PNG (arrangement map)
# --------------------------------------------------------------------------- #
class TestHeatmap:
    def test_creates_nonempty_png(self, tmp_path):
        t = _grid(60.0)
        rec = _build_recording(
            tmp_path,
            stems={
                "gtr": (t, _block(t, 5.0, 30.0)),
                "drums": (t, _block(t, 30.0, 58.0)),
            },
        )
        out = tmp_path / "structure_map.png"
        render_heatmap(rec, out)
        assert out.exists()
        assert out.stat().st_size > 0

    def test_no_stems_does_not_crash(self, tmp_path):
        t = _grid(60.0)
        analysis_dir = tmp_path / "analysis"
        analysis_dir.mkdir()
        _write_analysis(analysis_dir / "master_analysis.json", t, _block(t, 10.0, 50.0))
        (analysis_dir / "index.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "sources": [
                        {
                            "role": "master",
                            "origin": "mixed",
                            "label": "master",
                            "source": "mixed/master.wav",
                            "analysis": "analysis/master_analysis.json",
                            "duration": float(t[-1]),
                            "sample_rate": 44100,
                        }
                    ],
                }
            )
        )
        out = tmp_path / "structure_map.png"
        render_heatmap(tmp_path, out)
        assert out.exists()


# --------------------------------------------------------------------------- #
# CLI — main() writes the three artifacts to analysis/
# --------------------------------------------------------------------------- #
class TestCLI:
    def test_happy_writes_three_artifacts(self, tmp_path):
        t = _grid(60.0)
        rec = _build_recording(
            tmp_path,
            stems={
                "gtr": (t, _block(t, 5.0, 30.0)),
                "drums": (t, _block(t, 30.0, 58.0)),
            },
        )
        rc = main([str(rec)])
        assert rc == 0
        analysis = rec / "analysis"
        assert (analysis / "structure_brief.json").exists()
        assert (analysis / "structure_brief.md").exists()
        assert (analysis / "structure_map.png").exists()
        assert (analysis / "structure_brief.ass").exists()
        # JSON is valid and carries the segmentation marker
        data = json.loads((analysis / "structure_brief.json").read_text())
        assert data["segmentation"] == SEGMENTATION_SOURCE

    def test_no_index_returns_nonzero(self, tmp_path):
        (tmp_path / "analysis").mkdir()
        rc = main([str(tmp_path)])
        assert rc != 0

    def test_missing_dir_returns_nonzero(self, tmp_path):
        rc = main([str(tmp_path / "does_not_exist")])
        assert rc != 0

    def test_no_stems_degrades(self, tmp_path):
        t = _grid(60.0)
        analysis_dir = tmp_path / "analysis"
        analysis_dir.mkdir()
        _write_analysis(analysis_dir / "master_analysis.json", t, _block(t, 10.0, 50.0))
        (analysis_dir / "index.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "sources": [
                        {
                            "role": "master",
                            "origin": "mixed",
                            "label": "master",
                            "source": "mixed/master.wav",
                            "analysis": "analysis/master_analysis.json",
                            "duration": float(t[-1]),
                            "sample_rate": 44100,
                        }
                    ],
                }
            )
        )
        rc = main([str(tmp_path)])
        assert rc == 0
        assert (analysis_dir / "structure_brief.json").exists()

    def test_output_overrides(self, tmp_path):
        t = _grid(60.0)
        rec = _build_recording(tmp_path, stems={"gtr": (t, _block(t, 5.0, 30.0))})
        bj = tmp_path / "custom_brief.json"
        md = tmp_path / "custom.md"
        png = tmp_path / "custom.png"
        ass = tmp_path / "custom.ass"
        rc = main(
            [
                str(rec),
                "--output-brief",
                str(bj),
                "--output-markdown",
                str(md),
                "--output-heatmap",
                str(png),
                "--output-ass",
                str(ass),
            ]
        )
        assert rc == 0
        assert bj.exists() and md.exists() and png.exists() and ass.exists()


# --------------------------------------------------------------------------- #
# ASS subtitle overlay (brief on the source video)
# --------------------------------------------------------------------------- #
class TestAssOverlay:
    def _brief(self) -> StructureBrief:
        return StructureBrief(
            recording="rec",
            duration=60.0,
            bpm=120.0,
            stems=[
                StemActivity("gtr", [(5.0, 30.0)], False),
                StemActivity("dead", [], True),
            ],
            events=[
                StructureEvent(5.0, "enter", "gtr"),
                StructureEvent(30.0, "exit", "gtr"),
            ],
            master_levels=[
                EnergyLevel(0.0, 20.0, "low"),
                EnergyLevel(20.0, 60.0, "high"),
            ],
            drops=[20.0],
        )

    def test_ass_has_header_and_markers(self):
        ass = render_ass(self._brief())
        assert "[Script Info]" in ass
        assert "[Events]" in ass
        assert "Dialogue:" in ass
        assert "energy: low" in ass
        assert "energy: high" in ass
        assert "ENTER gtr" in ass
        assert "EXIT gtr" in ass
        assert "DROP" in ass

    def test_ass_skips_silent_stem_in_column(self):
        ass = render_ass(self._brief())
        # active stem appears as a column label; silent stem must not
        assert "● gtr" in ass
        assert "● dead" not in ass

    def test_ass_timestamps_are_well_formed(self):
        ass = render_ass(self._brief())
        # drop at 20.0s -> 0:00:20.00 start
        assert "0:00:20.00" in ass

    def test_ass_no_stems_does_not_crash(self):
        b = StructureBrief(
            recording="solo",
            duration=60.0,
            bpm=90.0,
            stems=[],
            events=[],
            master_levels=[EnergyLevel(0.0, 60.0, "mid")],
            drops=[],
        )
        ass = render_ass(b)
        assert "[Events]" in ass
        assert "energy: mid" in ass
