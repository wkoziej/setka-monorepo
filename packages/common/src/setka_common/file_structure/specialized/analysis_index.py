# ABOUTME: Typed reader for analysis/index.json manifest produced by beatrix analyze-recording.
# ABOUTME: Provides AnalysisIndex and AnalysisIndexEntry dataclasses plus load_analysis_index().

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from .recording import RecordingStructureManager

logger = logging.getLogger(__name__)

# Filename of the manifest inside the analysis directory.
INDEX_FILENAME = "index.json"

# Only version 1 is currently understood.
_SUPPORTED_VERSIONS = {1}

# Required fields in every source entry.
_REQUIRED_ENTRY_FIELDS = ("role", "origin", "label", "source", "analysis")


@dataclass
class AnalysisIndexEntry:
    """Single entry in the analysis index manifest.

    All relative paths (``source``, ``analysis``) are relative to the
    recording directory.  Use ``resolved_*`` helpers to obtain absolute paths.
    """

    role: str
    origin: str
    label: str
    source: str
    analysis: str
    duration: float | None = None
    sample_rate: int | None = None

    def resolved_analysis_path(self, recording_dir: Path) -> Path:
        """Return the absolute path to the analysis JSON file.

        Args:
            recording_dir: Root directory of the recording.

        Returns:
            Absolute ``Path`` constructed from ``recording_dir`` and
            ``self.analysis``.
        """
        return Path(recording_dir) / self.analysis

    def resolved_source_path(self, recording_dir: Path) -> Path:
        """Return the absolute path to the audio source file.

        Args:
            recording_dir: Root directory of the recording.

        Returns:
            Absolute ``Path`` constructed from ``recording_dir`` and
            ``self.source``.
        """
        return Path(recording_dir) / self.source


@dataclass
class AnalysisIndex:
    """Parsed contents of ``analysis/index.json``.

    Provides convenience accessors to retrieve the master entry and per-stem
    entries without ad-hoc JSON parsing in consuming packages.
    """

    version: int
    sources: list[AnalysisIndexEntry] = field(default_factory=list)

    def master(self) -> AnalysisIndexEntry | None:
        """Return the first entry with ``role == "master"``, or ``None``."""
        for entry in self.sources:
            if entry.role == "master":
                return entry
        return None

    def stems(self) -> list[AnalysisIndexEntry]:
        """Return all entries with ``role == "stem"``."""
        return [entry for entry in self.sources if entry.role == "stem"]

    def by_label(self, label: str) -> AnalysisIndexEntry | None:
        """Return the entry matching *label*, or ``None`` if not found."""
        for entry in self.sources:
            if entry.label == label:
                return entry
        return None


def load_analysis_index(recording_dir: Path) -> AnalysisIndex | None:
    """Load and parse ``analysis/index.json`` from *recording_dir*.

    Args:
        recording_dir: Root directory of the recording.

    Returns:
        Parsed :class:`AnalysisIndex` when the manifest file exists, or
        ``None`` when the file is absent (backward compatibility with
        recordings that pre-date the manifest).

    Raises:
        ValueError: When the manifest contains an unsupported ``version`` or
                    when a source entry is missing a required field.
    """
    index_path = (
        Path(recording_dir)
        / RecordingStructureManager.ANALYSIS_DIRNAME
        / INDEX_FILENAME
    )

    if not index_path.exists():
        logger.debug("analysis/index.json not found at %s — skipping", index_path)
        return None

    with open(index_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    version = data.get("version")
    if version not in _SUPPORTED_VERSIONS:
        raise ValueError(
            f"Unsupported analysis index version {version!r}. "
            f"Supported versions: {sorted(_SUPPORTED_VERSIONS)}."
        )

    sources: list[AnalysisIndexEntry] = []
    for i, raw in enumerate(data.get("sources", [])):
        for required_field in _REQUIRED_ENTRY_FIELDS:
            if required_field not in raw:
                raise ValueError(
                    f"analysis/index.json source entry at index {i} is missing "
                    f"required field {required_field!r}."
                )
        entry = AnalysisIndexEntry(
            role=raw["role"],
            origin=raw["origin"],
            label=raw["label"],
            source=raw["source"],
            analysis=raw["analysis"],
            duration=raw.get("duration"),
            sample_rate=raw.get("sample_rate"),
        )
        sources.append(entry)

    return AnalysisIndex(version=version, sources=sources)
