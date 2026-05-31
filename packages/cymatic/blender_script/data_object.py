# ABOUTME: In-Blender builder — numpy channels -> mesh with N verts + float attrs
# ABOUTME: X = time = arange(N)*dt; one FLOAT/POINT attribute per channel (foreach_set)

"""Data-object builder for the cymatic 3D audio visualizer (Unit 6).

Encodes the whole song as a single "data object": a mesh with ``N`` vertices
whose X coordinate is time (``arange(N) * dt``) and one FLOAT vertex attribute
(POINT domain) per channel (``bass_n``, ``mid_n``, ``high_n``, ``beat_env``,
``peak_env``). A Geometry Nodes tree (Unit 7) samples this object by scene time
via ``Sample Index`` — the "mesh-as-data" bridge (approach B).

The numpy -> mesh pattern here is lifted verbatim from the proven spike code
(``research/spike2_gn_sampling.py`` and ``research/build_visualizer_v1.py``,
Stage A), confirmed working on Blender 5.1.2:

    mesh.vertices.add(N)
    co[0::3] = arange(N) * dt
    mesh.vertices.foreach_set("co", co)
    attr = mesh.attributes.new(name=..., type='FLOAT', domain='POINT')
    attr.data.foreach_set("value", np.ascontiguousarray(arr, np.float32))

This module is executed inside Blender, so ``bpy`` is guarded for import-time
availability in tests.
"""

import sys

import numpy as np

try:
    import bpy
except ImportError:  # running outside Blender (e.g. unit tests)
    bpy = None


def _bpy():
    """Resolve the live ``bpy`` module.

    Inside Blender this is the module imported at load time. In tests the
    autouse ``mock_bpy`` fixture injects a Mock into ``sys.modules["bpy"]``
    after this module is imported, so fall back to that injected module.

    Raises:
        RuntimeError: if no ``bpy`` is available (not in Blender, no mock).
    """
    mod = bpy if bpy is not None else sys.modules.get("bpy")
    if mod is None:
        raise RuntimeError(
            "build_data_object requires Blender's bpy module (run inside Blender)."
        )
    return mod


def build_data_object(name, dt, channels):
    """Build a Blender data-object mesh from equal-length numpy channels.

    Creates a mesh with ``N`` vertices (``N`` = the common length of every
    channel array), sets each vertex X coordinate to ``arange(N) * dt`` (time),
    and adds one FLOAT/POINT vertex attribute per channel. All attribute
    buffers are coerced to C-contiguous ``float32`` of length ``N`` before
    ``foreach_set``.

    Args:
        name: name for the mesh and object.
        dt: time step between samples (seconds); X = arange(N) * dt.
        channels: mapping of attribute name -> 1-D numpy array. Every array
            must have the same length (== N). Must be non-empty.

    Returns:
        The created Blender object (``bpy.types.Object``), linked into the
        scene collection.

    Raises:
        ValueError: if ``channels`` is empty or arrays differ in length.
    """
    if not channels:
        raise ValueError("channels must be a non-empty mapping of name -> array.")

    lengths = {key: len(arr) for key, arr in channels.items()}
    unique_lengths = set(lengths.values())
    if len(unique_lengths) != 1:
        raise ValueError(
            f"All channel arrays must have equal length; got {lengths}."
        )

    n = unique_lengths.pop()
    if n == 0:
        raise ValueError("channel arrays must have length >= 1.")

    bpy_mod = _bpy()

    # --- mesh: N verts, X = arange(N) * dt (time) ---
    mesh = bpy_mod.data.meshes.new(name)
    mesh.vertices.add(n)
    co = np.zeros(n * 3, dtype=np.float32)
    co[0::3] = np.arange(n, dtype=np.float32) * dt
    mesh.vertices.foreach_set("co", co)

    # --- one FLOAT/POINT attribute per channel ---
    for attr_name, arr in channels.items():
        buf = np.ascontiguousarray(arr, dtype=np.float32)
        attr = mesh.attributes.new(name=attr_name, type="FLOAT", domain="POINT")
        attr.data.foreach_set("value", buf)

    mesh.update()

    obj = bpy_mod.data.objects.new(name, mesh)
    bpy_mod.context.scene.collection.objects.link(obj)
    return obj
