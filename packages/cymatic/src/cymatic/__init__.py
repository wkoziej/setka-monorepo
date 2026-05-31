# ABOUTME: cymatic package — 3D audio visualizer (Geometry Nodes) host-side API
# ABOUTME: Generates a procedural 3D scene from beatrix analysis, rendered to mp4

"""cymatic — procedural 3D audio visualizer driven by beatrix analysis."""

from cymatic.analysis_loader import AnalysisData, load_analysis
from cymatic.config import PresetParams, VisualizerConfig
from cymatic.normalization import normalize_band, precompute_envelope
from cymatic.runner import CymaticRunner, render
from cymatic.sync_verification import SyncReport, verify_sync

__all__ = [
    "VisualizerConfig",
    "PresetParams",
    "AnalysisData",
    "load_analysis",
    "normalize_band",
    "precompute_envelope",
    "CymaticRunner",
    "render",
    "SyncReport",
    "verify_sync",
]

__version__ = "0.1.0"
