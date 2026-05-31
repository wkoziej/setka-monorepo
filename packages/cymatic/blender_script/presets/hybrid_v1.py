# ABOUTME: hybrid_v1 visual preset — 3 instanced rings (bass/mid/high) + pulsing core
# ABOUTME: Ported from research/build_visualizer_v2.py (proven on Blender 5.1.2); punch toned down

"""The MVP hybrid visual preset for the cymatic 3D audio visualizer.

Continuous bands -> form; beats/peaks -> impulses. The look is three concentric
rings of instanced bars (bass / mid / high) whose per-bar height samples the
band history with a small per-bar time offset (a scrolling "comet tail" of
energy), plus a central icosphere that pulses on ``beat_env``. Emissive
materials over a dark world.

Ported from the proven spike ``research/build_visualizer_v2.py`` (built live on
Blender 5.1.2, sync confirmed). **Deviations from v2, by instruction:**

  - The ring beat-punch in v2 added ``beat_env * 3`` to bar height, which blew
    out to pure-white frames on every beat. Here the punch is a tasteful
    ``beat_env * PUNCH_GAIN`` (default ~1.2) scaled by ``accent_intensity``.
  - Emission strength is lowered so an on-beat reads as a clear pulse, not a
    white-out (ring strength ~2.0, core strength ~4.0 vs v2's 4.0 / 8.0).

Knobs are exposed via ``PresetParams`` (palette, primitive, accent_intensity,
decay, tau). ``decay``/``tau`` are precomputed host-side into ``beat_env`` /
``peak_env`` (Unit 5), so here they are informational; ``accent_intensity``
scales the live punch and emission.

This module is executed inside Blender; ``bpy`` is resolved lazily so the
autouse ``mock_bpy`` test fixture (injected into ``sys.modules`` after import)
is honored.
"""

import math
import sys

try:
    import bpy
except ImportError:  # running outside Blender (unit tests, host-side import)
    bpy = None


# Per-bar time offset (seconds) feeding the scrolling-history look: bar index i
# samples band energy at (SceneTime - i * STRIDE). Matches v2's STRIDE.
STRIDE = 0.045
# Number of instanced bars per ring (circle vertex count). Matches v2's M.
BARS_PER_RING = 128
# Tasteful beat punch gain (v2 used 3.0 on height -> white-out). Toned down.
PUNCH_GAIN = 1.2

# Ring layout: (object name, band attribute, radius, color-ramp [low, high]).
_RINGS = (
    ("viz_bass", "bass_n", 5.0, [(0.0, 0.2, 1.0, 1.0), (0.2, 0.9, 1.0, 1.0)]),
    ("viz_mid", "mid_n", 6.4, [(0.0, 1.0, 0.4, 1.0), (1.0, 1.0, 0.2, 1.0)]),
    ("viz_high", "high_n", 7.8, [(1.0, 0.3, 0.6, 1.0), (1.0, 0.9, 0.9, 1.0)]),
)

# Toned-down emission strengths (v2: rings 4.0, core 8.0).
_RING_EMISSION = 2.0
_CORE_EMISSION = 4.0


def _bpy():
    """Resolve the live ``bpy`` (module import or test-injected mock)."""
    mod = bpy if bpy is not None else sys.modules.get("bpy")
    if mod is None:
        raise RuntimeError(
            "hybrid_v1 requires Blender's bpy module (run inside Blender)."
        )
    return mod


def _band_history_height(node_group, scene_time, dt, data_obj, attr_name,
                         punch_gain):
    """Per-bar scrolling-history sample for one band, plus a toned beat punch.

    Builds the v2 ``band_field`` sub-graph: each instanced bar (by its point
    Index) samples the band attribute at ``floor((SceneTime - Index*STRIDE)/dt)``
    so a wave of past energy scrolls outward around the ring. Adds a global
    ``beat_env(now) * punch_gain`` term (toned down from v2's *3 white-out).

    Returns the terminal math node whose output [0] is the bar height factor.
    """
    nodes, links = node_group.nodes, node_group.links

    idx = nodes.new("GeometryNodeInputIndex")
    offs = nodes.new("ShaderNodeMath")
    offs.operation = "MULTIPLY"
    offs.inputs[1].default_value = STRIDE
    links.new(idx.outputs["Index"], offs.inputs[0])

    tsec = nodes.new("ShaderNodeMath")
    tsec.operation = "SUBTRACT"
    links.new(scene_time.outputs["Seconds"], tsec.inputs[0])
    links.new(offs.outputs[0], tsec.inputs[1])

    sidx = nodes.new("ShaderNodeMath")
    sidx.operation = "DIVIDE"
    sidx.inputs[1].default_value = dt
    links.new(tsec.outputs[0], sidx.inputs[0])

    flo = nodes.new("ShaderNodeMath")
    flo.operation = "FLOOR"
    links.new(sidx.outputs[0], flo.inputs[0])

    obj_info = nodes.new("GeometryNodeObjectInfo")
    obj_info.inputs["Object"].default_value = data_obj
    obj_info.transform_space = "ORIGINAL"

    named = nodes.new("GeometryNodeInputNamedAttribute")
    named.data_type = "FLOAT"
    named.inputs["Name"].default_value = attr_name

    sample = nodes.new("GeometryNodeSampleIndex")
    sample.data_type = "FLOAT"
    sample.domain = "POINT"
    sample.clamp = True
    links.new(obj_info.outputs["Geometry"], sample.inputs["Geometry"])
    links.new(named.outputs["Attribute"], sample.inputs["Value"])
    links.new(flo.outputs[0], sample.inputs["Index"])

    # --- toned-down global beat punch: + beat_env(now) * punch_gain ---
    sidx0 = nodes.new("ShaderNodeMath")
    sidx0.operation = "DIVIDE"
    sidx0.inputs[1].default_value = dt
    links.new(scene_time.outputs["Seconds"], sidx0.inputs[0])

    flo0 = nodes.new("ShaderNodeMath")
    flo0.operation = "FLOOR"
    links.new(sidx0.outputs[0], flo0.inputs[0])

    beat_named = nodes.new("GeometryNodeInputNamedAttribute")
    beat_named.data_type = "FLOAT"
    beat_named.inputs["Name"].default_value = "beat_env"

    beat_sample = nodes.new("GeometryNodeSampleIndex")
    beat_sample.data_type = "FLOAT"
    beat_sample.domain = "POINT"
    beat_sample.clamp = True
    links.new(obj_info.outputs["Geometry"], beat_sample.inputs["Geometry"])
    links.new(beat_named.outputs["Attribute"], beat_sample.inputs["Value"])
    links.new(flo0.outputs[0], beat_sample.inputs["Index"])

    punch = nodes.new("ShaderNodeMath")
    punch.operation = "MULTIPLY"
    punch.inputs[1].default_value = punch_gain
    links.new(beat_sample.outputs[0], punch.inputs[0])

    add = nodes.new("ShaderNodeMath")
    add.operation = "ADD"
    links.new(sample.outputs[0], add.inputs[0])
    links.new(punch.outputs[0], add.inputs[1])
    return add


def _emissive_material(name, color, strength):
    """A simple emission material (toned-down strength)."""
    b = _bpy()
    mat = b.data.materials.new(name)
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    em = tree.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = color
    em.inputs["Strength"].default_value = strength
    tree.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return mat


def _ramp_emissive_material(name, ramp_colors, strength):
    """Emission material whose color ramps by instance Z (bar height)."""
    b = _bpy()
    mat = b.data.materials.new(name)
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    em = tree.nodes.new("ShaderNodeEmission")
    geo = tree.nodes.new("ShaderNodeNewGeometry")
    sep = tree.nodes.new("ShaderNodeSeparateXYZ")
    mr = tree.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.0
    mr.inputs["From Max"].default_value = 6.0
    ramp = tree.nodes.new("ShaderNodeValToRGB")
    elements = ramp.color_ramp.elements
    elements[0].position = 0.0
    elements[0].color = ramp_colors[0]
    elements[1].position = 1.0
    elements[1].color = ramp_colors[1]
    tree.links.new(geo.outputs["Position"], sep.inputs["Vector"])
    tree.links.new(sep.outputs["Z"], mr.inputs["Value"])
    tree.links.new(mr.outputs["Result"], ramp.inputs["Fac"])
    tree.links.new(ramp.outputs["Color"], em.inputs["Color"])
    em.inputs["Strength"].default_value = strength
    tree.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return mat


def _build_ring(collection, data_obj, dt, name, attr, radius, ramp_colors,
                punch_gain):
    """One ring of instanced bars whose height samples a band's history."""
    b = _bpy()
    ng = b.data.node_groups.new(name, "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT",
                            socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT",
                            socket_type="NodeSocketGeometry")
    nodes, links = ng.nodes, ng.links
    gout = nodes.new("NodeGroupOutput")

    circ = nodes.new("GeometryNodeMeshCircle")
    circ.fill_type = "NONE"
    circ.inputs["Vertices"].default_value = BARS_PER_RING
    circ.inputs["Radius"].default_value = radius

    cube = nodes.new("GeometryNodeMeshCube")
    cube.inputs["Size"].default_value = (0.18, 0.18, 1.0)

    iop = nodes.new("GeometryNodeInstanceOnPoints")
    links.new(circ.outputs["Mesh"], iop.inputs["Points"])
    links.new(cube.outputs["Mesh"], iop.inputs["Instance"])

    scene_time = nodes.new("GeometryNodeInputSceneTime")
    height = _band_history_height(ng, scene_time, dt, data_obj, attr, punch_gain)

    hsc = nodes.new("ShaderNodeMath")
    hsc.operation = "MULTIPLY_ADD"
    hsc.inputs[1].default_value = 5.0
    hsc.inputs[2].default_value = 0.1
    links.new(height.outputs[0], hsc.inputs[0])

    comb = nodes.new("ShaderNodeCombineXYZ")
    comb.inputs["X"].default_value = 1.0
    comb.inputs["Y"].default_value = 1.0
    links.new(hsc.outputs[0], comb.inputs["Z"])

    scl = nodes.new("GeometryNodeScaleInstances")
    links.new(iop.outputs["Instances"], scl.inputs["Instances"])
    links.new(comb.outputs[0], scl.inputs["Scale"])

    setm = nodes.new("GeometryNodeSetMaterial")
    links.new(scl.outputs[0], setm.inputs["Geometry"])
    mat = _ramp_emissive_material(name + "_m", ramp_colors, _RING_EMISSION)
    setm.inputs["Material"].default_value = mat
    links.new(setm.outputs["Geometry"], gout.inputs[0])

    obj = b.data.objects.new(name, b.data.meshes.new(name))
    collection.objects.link(obj)
    obj.modifiers.new("gn", "NODES").node_group = ng
    return obj


def _build_core(collection, data_obj, dt, primitive, accent_intensity):
    """Central primitive pulsing on beat_env (toned-down punch)."""
    b = _bpy()
    ng = b.data.node_groups.new("viz_core_gn", "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT",
                            socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT",
                            socket_type="NodeSocketGeometry")
    nodes, links = ng.nodes, ng.links
    gout = nodes.new("NodeGroupOutput")

    if primitive == "cube":
        prim = nodes.new("GeometryNodeMeshCube")
        prim.inputs["Size"].default_value = (1.0, 1.0, 1.0)
    elif primitive == "uvsphere":
        prim = nodes.new("GeometryNodeMeshUVSphere")
        prim.inputs["Radius"].default_value = 1.0
    else:  # default / "icosphere"
        prim = nodes.new("GeometryNodeMeshIcoSphere")
        prim.inputs["Radius"].default_value = 1.0
        prim.inputs["Subdivisions"].default_value = 3
    prim_out = prim.outputs["Mesh"]

    scene_time = nodes.new("GeometryNodeInputSceneTime")
    sidx = nodes.new("ShaderNodeMath")
    sidx.operation = "DIVIDE"
    sidx.inputs[1].default_value = dt
    links.new(scene_time.outputs["Seconds"], sidx.inputs[0])
    flo = nodes.new("ShaderNodeMath")
    flo.operation = "FLOOR"
    links.new(sidx.outputs[0], flo.inputs[0])

    obj_info = nodes.new("GeometryNodeObjectInfo")
    obj_info.inputs["Object"].default_value = data_obj
    obj_info.transform_space = "ORIGINAL"
    named = nodes.new("GeometryNodeInputNamedAttribute")
    named.data_type = "FLOAT"
    named.inputs["Name"].default_value = "beat_env"
    sample = nodes.new("GeometryNodeSampleIndex")
    sample.data_type = "FLOAT"
    sample.domain = "POINT"
    sample.clamp = True
    links.new(obj_info.outputs["Geometry"], sample.inputs["Geometry"])
    links.new(named.outputs["Attribute"], sample.inputs["Value"])
    links.new(flo.outputs[0], sample.inputs["Index"])

    # scale = 0.5 + beat_env * (1.0 + accent_intensity)  (v2 used *3 -> over-pulse)
    scale = nodes.new("ShaderNodeMath")
    scale.operation = "MULTIPLY_ADD"
    scale.inputs[1].default_value = 1.0 + accent_intensity
    scale.inputs[2].default_value = 0.5
    links.new(sample.outputs[0], scale.inputs[0])

    cmb = nodes.new("ShaderNodeCombineXYZ")
    links.new(scale.outputs[0], cmb.inputs["X"])
    links.new(scale.outputs[0], cmb.inputs["Y"])
    links.new(scale.outputs[0], cmb.inputs["Z"])

    tr = nodes.new("GeometryNodeTransform")
    links.new(prim_out, tr.inputs["Geometry"])
    links.new(cmb.outputs[0], tr.inputs["Scale"])

    setm = nodes.new("GeometryNodeSetMaterial")
    links.new(tr.outputs[0], setm.inputs["Geometry"])
    mat = _emissive_material("core_m", (1.0, 0.5, 0.05, 1.0), _CORE_EMISSION)
    setm.inputs["Material"].default_value = mat
    links.new(setm.outputs[0], gout.inputs[0])

    obj = b.data.objects.new("viz_core", b.data.meshes.new("viz_core"))
    collection.objects.link(obj)
    obj.modifiers.new("gn", "NODES").node_group = ng
    return obj


def _setup_world_and_render(scene, fps, resolution):
    """Dark world + EEVEE render settings (1280x720 default, fps from config)."""
    b = _bpy()
    width, height = (resolution if resolution else (1280, 720))
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.fps = fps

    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except (TypeError, ValueError):  # older Blender lacks EEVEE Next id
        scene.render.engine = "BLENDER_EEVEE"

    world = b.data.worlds.get("cymatic_world") or b.data.worlds.new("cymatic_world")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg is not None:
        bg.inputs[0].default_value = (0.01, 0.01, 0.02, 1.0)
        bg.inputs[1].default_value = 0.25
    scene.world = world


def _setup_camera_and_sun(collection, scene):
    """Place the camera and a single sun (lifted from v2)."""
    b = _bpy()
    cam_data = b.data.cameras.new("viz_cam")
    cam = b.data.objects.new("viz_cam", cam_data)
    collection.objects.link(cam)
    cam.location = (0, -17, 12)
    cam.rotation_euler = (math.radians(57), 0, 0)
    scene.camera = cam

    sun_data = b.data.lights.new("viz_sun", "SUN")
    sun_data.energy = 1.2
    sun = b.data.objects.new("viz_sun", sun_data)
    collection.objects.link(sun)
    sun.rotation_euler = (math.radians(50), 0, 0.6)
    return cam, sun


def build_preset_scene(analysis, data_obj, sampler_group, preset_params,
                       fps=30, resolution=None):
    """Assemble the hybrid_v1 scene: rings + core + camera + sun + world + render.

    Args:
        analysis: the loaded ``AnalysisData`` (Unit 5) — supplies ``dt`` and
            ``duration`` for frame range.
        data_obj: the data-object mesh (Unit 6) holding the channel attributes.
        sampler_group: the GN sampler node group (Unit 7). Built and passed in
            by the orchestrator so the preset does not reinvent the sampler;
            kept available for reuse/composition (the rings build their own
            per-bar history sub-graph, the core reuses current-time sampling).
        preset_params: ``PresetParams`` (palette/primitive/accent_intensity/
            decay/tau). ``accent_intensity`` scales the beat punch + core pulse.
        fps: render fps (from ``VisualizerConfig``, NOT the analysis).
        resolution: ``(w, h)`` or ``None`` -> 1280x720.

    Returns:
        The Blender scene object that was configured.
    """
    b = _bpy()
    scene = b.context.scene
    dt = float(analysis.dt)

    # accent_intensity (0..1-ish) scales the toned punch around its default.
    accent = getattr(preset_params, "accent_intensity", 0.5) if preset_params else 0.5
    primitive = getattr(preset_params, "primitive", "icosphere") if preset_params else "icosphere"
    punch_gain = PUNCH_GAIN * (0.5 + accent)

    # Fresh collection (idempotent: clear a previous run's objects).
    existing = b.data.collections.get("cymatic_viz")
    if existing is not None:
        for obj in list(existing.objects):
            b.data.objects.remove(obj, do_unlink=True)
        b.data.collections.remove(existing)
    collection = b.data.collections.new("cymatic_viz")
    scene.collection.children.link(collection)

    # Hide the raw data-object from the render/viewport (it is data, not geometry).
    data_obj.hide_render = True
    data_obj.hide_viewport = True

    for name, attr, radius, ramp_colors in _RINGS:
        _build_ring(collection, data_obj, dt, name, attr, radius, ramp_colors,
                    punch_gain)
    _build_core(collection, data_obj, dt, primitive, accent)

    _setup_camera_and_sun(collection, scene)
    _setup_world_and_render(scene, fps, resolution)

    scene.frame_start = 1
    scene.frame_end = max(1, int(float(analysis.duration) * fps))
    return scene
