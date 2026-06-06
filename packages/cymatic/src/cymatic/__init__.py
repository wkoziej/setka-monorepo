# ABOUTME: cymatic package — 3D audio visualizer (Geometry Nodes) host-side API
# ABOUTME: Generates a procedural 3D scene from beatrix analysis, rendered to mp4

"""cymatic — procedural 3D audio visualizer driven by beatrix analysis.

The public API is exposed lazily via module ``__getattr__`` (PEP 562). Only
``config`` is eager-imported because it is pure (dataclasses + json). The other
symbols are resolved on first access so that ``import cymatic`` stays light —
critically, it must NOT eagerly pull ``runner`` -> ``setka_common`` -> PyYAML,
since ``build_scene.py`` imports ``cymatic.*`` inside headless Blender whose
bundled python lacks PyYAML.
"""

from cymatic.config import PresetParams, VisualizerConfig

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
    "StructureBrief",
    "generate_brief",
    "render_markdown",
    "render_heatmap",
]

__version__ = "0.1.0"

# Map lazily-exposed names to their defining submodule.
_LAZY = {
    "AnalysisData": "cymatic.analysis_loader",
    "load_analysis": "cymatic.analysis_loader",
    "normalize_band": "cymatic.normalization",
    "precompute_envelope": "cymatic.normalization",
    "CymaticRunner": "cymatic.runner",
    "render": "cymatic.runner",
    "SyncReport": "cymatic.sync_verification",
    "verify_sync": "cymatic.sync_verification",
    "StructureBrief": "cymatic.brief",
    "generate_brief": "cymatic.brief",
    "render_markdown": "cymatic.brief",
    "render_heatmap": "cymatic.brief",
}


def __getattr__(name):
    """PEP 562 lazy attribute resolution for the public API."""
    module_path = _LAZY.get(name)
    if module_path is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import importlib

    return getattr(importlib.import_module(module_path), name)
