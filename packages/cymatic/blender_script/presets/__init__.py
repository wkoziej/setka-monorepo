# ABOUTME: Visual preset package for cymatic (in-Blender, executed via bpy)
# ABOUTME: Exposes build_preset_scene from the one MVP hybrid preset (hybrid_v1)

"""Visual presets for the cymatic 3D audio visualizer.

MVP ships exactly one preset (``hybrid_v1``): continuous bands drive form,
beat/peak envelopes drive impulses. Re-exported here as ``build_preset_scene``
so the orchestrator (``build_scene.py``) can stay preset-agnostic.
"""

from .hybrid_v1 import build_preset_scene

__all__ = ["build_preset_scene"]
