# ABOUTME: Tests for AnalysisIndex reader - the typed manifest loader for analysis/index.json
# ABOUTME: Covers happy path, edge cases, and error scenarios for the analysis index reader.

import json
import pytest
from pathlib import Path

from setka_common.file_structure.specialized.analysis_index import (
    load_analysis_index,
)
from setka_common.file_structure.specialized.recording import RecordingStructureManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _write_index(recording_dir: Path, data: dict) -> Path:
    """Write index.json to analysis/ subdirectory and return the path."""
    analysis_dir = recording_dir / RecordingStructureManager.ANALYSIS_DIRNAME
    analysis_dir.mkdir(parents=True, exist_ok=True)
    index_path = analysis_dir / "index.json"
    index_path.write_text(json.dumps(data), encoding="utf-8")
    return index_path


MASTER_ENTRY = {
    "role": "master",
    "origin": "mixed",
    "label": "master",
    "source": "mixed/master.wav",
    "analysis": "analysis/master_analysis.json",
    "duration": 182.4,
    "sample_rate": 44100,
}

STEM_ENTRY = {
    "role": "stem",
    "origin": "bitwig",
    "label": "track_4_git",
    "source": "bitwig/samples/track_4_git-24.wav",
    "analysis": "analysis/track_4_git_analysis.json",
    "duration": 182.4,
    "sample_rate": 44100,
}


# ---------------------------------------------------------------------------
# Happy path tests
# ---------------------------------------------------------------------------


class TestHappyPath:
    def test_loads_correct_entry_count(self, tmp_path):
        _write_index(tmp_path, {"version": 1, "sources": [MASTER_ENTRY, STEM_ENTRY]})
        index = load_analysis_index(tmp_path)
        assert index is not None
        assert len(index.sources) == 2

    def test_master_returns_first_master_role(self, tmp_path):
        _write_index(tmp_path, {"version": 1, "sources": [MASTER_ENTRY, STEM_ENTRY]})
        index = load_analysis_index(tmp_path)
        master = index.master()
        assert master is not None
        assert master.role == "master"
        assert master.label == "master"

    def test_stems_returns_stem_role_entries(self, tmp_path):
        _write_index(tmp_path, {"version": 1, "sources": [MASTER_ENTRY, STEM_ENTRY]})
        index = load_analysis_index(tmp_path)
        stems = index.stems()
        assert len(stems) == 1
        assert stems[0].role == "stem"
        assert stems[0].label == "track_4_git"

    def test_by_label_returns_correct_entry(self, tmp_path):
        _write_index(tmp_path, {"version": 1, "sources": [MASTER_ENTRY, STEM_ENTRY]})
        index = load_analysis_index(tmp_path)
        entry = index.by_label("track_4_git")
        assert entry is not None
        assert entry.label == "track_4_git"
        assert entry.origin == "bitwig"

    def test_by_label_unknown_returns_none(self, tmp_path):
        _write_index(tmp_path, {"version": 1, "sources": [MASTER_ENTRY, STEM_ENTRY]})
        index = load_analysis_index(tmp_path)
        assert index.by_label("does_not_exist") is None

    def test_resolved_analysis_path_is_absolute(self, tmp_path):
        _write_index(tmp_path, {"version": 1, "sources": [MASTER_ENTRY]})
        index = load_analysis_index(tmp_path)
        entry = index.master()
        resolved = entry.resolved_analysis_path(tmp_path)
        assert resolved.is_absolute()
        assert resolved == tmp_path / "analysis/master_analysis.json"

    def test_resolved_source_path_is_absolute(self, tmp_path):
        _write_index(tmp_path, {"version": 1, "sources": [MASTER_ENTRY]})
        index = load_analysis_index(tmp_path)
        entry = index.master()
        resolved = entry.resolved_source_path(tmp_path)
        assert resolved.is_absolute()
        assert resolved == tmp_path / "mixed/master.wav"

    def test_resolved_analysis_path_exists_when_file_present(self, tmp_path):
        _write_index(tmp_path, {"version": 1, "sources": [MASTER_ENTRY]})
        # Create the actual analysis file so .exists() can be asserted
        analysis_file = tmp_path / "analysis" / "master_analysis.json"
        analysis_file.parent.mkdir(parents=True, exist_ok=True)
        analysis_file.write_text("{}", encoding="utf-8")

        index = load_analysis_index(tmp_path)
        entry = index.master()
        assert entry.resolved_analysis_path(tmp_path).exists()

    def test_duration_and_sample_rate_populated(self, tmp_path):
        _write_index(tmp_path, {"version": 1, "sources": [MASTER_ENTRY]})
        index = load_analysis_index(tmp_path)
        entry = index.master()
        assert entry.duration == 182.4
        assert entry.sample_rate == 44100


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_missing_index_returns_none(self, tmp_path):
        # No index.json written at all
        result = load_analysis_index(tmp_path)
        assert result is None

    def test_empty_sources_list(self, tmp_path):
        _write_index(tmp_path, {"version": 1, "sources": []})
        index = load_analysis_index(tmp_path)
        assert index is not None
        assert index.sources == []
        assert index.master() is None
        assert index.stems() == []

    def test_entry_without_duration_and_sample_rate(self, tmp_path):
        entry_no_optional = {
            "role": "master",
            "origin": "mixed",
            "label": "master",
            "source": "mixed/master.wav",
            "analysis": "analysis/master_analysis.json",
        }
        _write_index(tmp_path, {"version": 1, "sources": [entry_no_optional]})
        index = load_analysis_index(tmp_path)
        entry = index.master()
        assert entry is not None
        assert entry.duration is None
        assert entry.sample_rate is None


# ---------------------------------------------------------------------------
# Error / validation tests
# ---------------------------------------------------------------------------


class TestErrors:
    def test_missing_required_field_role_raises_value_error(self, tmp_path):
        bad_entry = {
            "origin": "mixed",
            "label": "master",
            "source": "mixed/master.wav",
            "analysis": "analysis/master_analysis.json",
        }
        _write_index(tmp_path, {"version": 1, "sources": [bad_entry]})
        with pytest.raises(ValueError, match="role"):
            load_analysis_index(tmp_path)

    def test_missing_required_field_analysis_raises_value_error(self, tmp_path):
        bad_entry = {
            "role": "master",
            "origin": "mixed",
            "label": "master",
            "source": "mixed/master.wav",
        }
        _write_index(tmp_path, {"version": 1, "sources": [bad_entry]})
        with pytest.raises(ValueError, match="analysis"):
            load_analysis_index(tmp_path)

    def test_unknown_version_raises_value_error(self, tmp_path):
        _write_index(tmp_path, {"version": 999, "sources": []})
        with pytest.raises(ValueError, match="version"):
            load_analysis_index(tmp_path)


# ---------------------------------------------------------------------------
# Integration round-trip test
# ---------------------------------------------------------------------------


class TestRoundTrip:
    def test_round_trip_with_manually_crafted_index(self, tmp_path):
        """Verify full round-trip: write index.json in Unit-3 schema, read back without loss."""
        data = {
            "version": 1,
            "sources": [
                {
                    "role": "master",
                    "origin": "mixed",
                    "label": "master",
                    "source": "mixed/master.wav",
                    "analysis": "analysis/master_analysis.json",
                    "duration": 200.0,
                    "sample_rate": 48000,
                },
                {
                    "role": "stem",
                    "origin": "bitwig",
                    "label": "m_s",
                    "source": "bitwig/samples/m_s-24.wav",
                    "analysis": "analysis/m_s_analysis.json",
                    "duration": 200.0,
                    "sample_rate": 48000,
                },
            ],
        }
        _write_index(tmp_path, data)
        index = load_analysis_index(tmp_path)

        assert index.version == 1
        assert len(index.sources) == 2

        master = index.master()
        assert master.role == "master"
        assert master.origin == "mixed"
        assert master.label == "master"
        assert master.source == "mixed/master.wav"
        assert master.analysis == "analysis/master_analysis.json"
        assert master.duration == 200.0
        assert master.sample_rate == 48000

        stem = index.by_label("m_s")
        assert stem is not None
        assert stem.role == "stem"
        assert stem.origin == "bitwig"
        assert stem.source == "bitwig/samples/m_s-24.wav"
