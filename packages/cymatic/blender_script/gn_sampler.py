# ABOUTME: In-Blender Geometry Nodes sampler builder (bridge-B, proven in Spike 2)
# ABOUTME: Reads stored band attributes by scene time and outputs interpolated values

"""Programmatic Geometry Nodes time-sampler for the cymatic visualizer.

This is the in-Blender side of the "mesh-as-data" bridge (approach B), proven
live on Blender 5.1.2 in Spike 2 (research/spike2_gn_sampling.py, max abs err
~6e-08). A data-object mesh stores one FLOAT/POINT attribute per channel, laid
out with X = arange(N) * dt. This module builds a GeometryNodeTree that, at any
scene time, computes::

    index_f = SceneTime.Seconds / dt
    i0 = floor(index_f);  i1 = i0 + 1;  frac = index_f - i0
    v0 = SampleIndex(attr, i0, clamp=True)
    v1 = SampleIndex(attr, i1, clamp=True)
    value = Mix(v0, v1, frac)          # linear interpolation between samples

``dt`` is passed in as a parameter (derived host-side from ``times[1]-times[0]``,
NOT hardcoded) so the same builder works across tracks of different sample rate.

Node group construction uses the Blender 4.0+ interface API
(``node_group.interface.new_socket(...)``), never the removed
``node_group.inputs`` / ``node_group.outputs`` collections.
"""

try:
    import bpy
except ImportError:  # running outside Blender (tests, host-side import)
    bpy = None


# Default channels exposed by the sampler, matching the data-object attributes
# (per-track normalized bands + precomputed beat/peak envelopes).
DEFAULT_CHANNELS = ("bass_n", "mid_n", "high_n", "beat_env", "peak_env")


def band_sample_field(node_group, scene_time, dt, data_obj, attr_name):
    """Build one time-sampling + linear-interpolation sub-graph for a channel.

    Wires: SceneTime.Seconds -> DIVIDE by ``dt`` -> (FLOOR=i0, ADD 1=i1,
    SUBTRACT=frac) -> two ``GeometryNodeSampleIndex`` (FLOAT/POINT, clamp=True)
    reading ``attr_name`` from ``data_obj`` -> ``ShaderNodeMix`` (FLOAT) blending
    v0/v1 by ``frac``. This is the exact graph verified in Spike 2.

    Args:
        node_group: the ``GeometryNodeTree`` to add nodes/links into.
        scene_time: an existing ``GeometryNodeInputSceneTime`` node (shared so a
            single Scene Time feeds every channel).
        dt: sample spacing in seconds (``times[1] - times[0]``); a node default,
            never hardcoded.
        data_obj: the data-object holding the per-channel FLOAT attributes.
        attr_name: name of the FLOAT/POINT attribute to sample.

    Returns:
        The terminal ``ShaderNodeMix`` node; its FLOAT output socket carries the
        interpolated channel value.
    """
    nodes, links = node_group.nodes, node_group.links

    # index_f = Seconds / dt
    div = nodes.new("ShaderNodeMath")
    div.operation = "DIVIDE"
    links.new(scene_time.outputs["Seconds"], div.inputs[0])
    div.inputs[1].default_value = dt

    # i0 = floor(index_f)
    floor = nodes.new("ShaderNodeMath")
    floor.operation = "FLOOR"
    links.new(div.outputs[0], floor.inputs[0])

    # frac = index_f - i0
    frac = nodes.new("ShaderNodeMath")
    frac.operation = "SUBTRACT"
    links.new(div.outputs[0], frac.inputs[0])
    links.new(floor.outputs[0], frac.inputs[1])

    # i1 = i0 + 1
    i1 = nodes.new("ShaderNodeMath")
    i1.operation = "ADD"
    i1.inputs[1].default_value = 1.0
    links.new(floor.outputs[0], i1.inputs[0])

    # data object -> geometry to sample from
    obj_info = nodes.new("GeometryNodeObjectInfo")
    obj_info.inputs["Object"].default_value = data_obj
    obj_info.transform_space = "ORIGINAL"

    # named FLOAT attribute to read
    named_attr = nodes.new("GeometryNodeInputNamedAttribute")
    named_attr.data_type = "FLOAT"
    named_attr.inputs["Name"].default_value = attr_name

    # two clamped FLOAT/POINT samples: v0 @ i0, v1 @ i1
    sample0 = nodes.new("GeometryNodeSampleIndex")
    sample0.data_type = "FLOAT"
    sample0.domain = "POINT"
    sample0.clamp = True
    sample1 = nodes.new("GeometryNodeSampleIndex")
    sample1.data_type = "FLOAT"
    sample1.domain = "POINT"
    sample1.clamp = True
    for sample, index_node in ((sample0, floor), (sample1, i1)):
        links.new(obj_info.outputs["Geometry"], sample.inputs["Geometry"])
        links.new(named_attr.outputs["Attribute"], sample.inputs["Value"])
        links.new(index_node.outputs[0], sample.inputs["Index"])

    # value = mix(v0, v1, frac)  (linear interpolation)
    mix = nodes.new("ShaderNodeMix")
    mix.data_type = "FLOAT"
    links.new(frac.outputs[0], mix.inputs["Factor"])
    links.new(sample0.outputs[0], mix.inputs[2])  # A = v0
    links.new(sample1.outputs[0], mix.inputs[3])  # B = v1

    return mix


def build_sampler_group(name, dt, data_obj, channels=DEFAULT_CHANNELS):
    """Build a reusable GN node group sampling each channel by scene time.

    Creates a ``GeometryNodeTree`` with a passthrough Geometry input/output
    (sockets via the 4.0+ ``interface.new_socket`` API) plus one FLOAT output
    socket per channel. A single ``GeometryNodeInputSceneTime`` drives a
    :func:`band_sample_field` sub-graph for every channel; each interpolated
    value is routed to its named output socket.

    Args:
        name: node-group name.
        dt: sample spacing in seconds (from ``times[1] - times[0]``); passed
            through to each field, never hardcoded.
        data_obj: data-object holding the FLOAT/POINT channel attributes.
        channels: iterable of attribute names to expose (defaults to the five
            visualizer channels).

    Returns:
        The created ``bpy.types.GeometryNodeTree`` node group.
    """
    channels = tuple(channels)
    if not channels:
        raise ValueError("build_sampler_group requires at least one channel.")

    # Resolve bpy lazily so a test-injected mock (sys.modules["bpy"]) is honored
    # even though the module-level import happened before the mock was set up.
    _bpy = bpy
    if _bpy is None:
        import sys

        _bpy = sys.modules.get("bpy")
    if _bpy is None:
        raise RuntimeError("build_sampler_group requires Blender (bpy unavailable).")

    node_group = _bpy.data.node_groups.new(name, "GeometryNodeTree")

    # Sockets via the Blender 4.0+ interface API (NOT node_group.inputs/outputs).
    node_group.interface.new_socket(
        "Geometry", in_out="INPUT", socket_type="NodeSocketGeometry"
    )
    node_group.interface.new_socket(
        "Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry"
    )
    for attr_name in channels:
        node_group.interface.new_socket(
            attr_name, in_out="OUTPUT", socket_type="NodeSocketFloat"
        )

    nodes, links = node_group.nodes, node_group.links
    group_in = nodes.new("NodeGroupInput")
    group_out = nodes.new("NodeGroupOutput")

    # Single Scene Time feeds every channel's sampler (fps-independent: seconds).
    scene_time = nodes.new("GeometryNodeInputSceneTime")

    # Passthrough geometry: input -> output socket 0.
    links.new(group_in.outputs[0], group_out.inputs[0])

    # One interpolated FLOAT per channel, wired to its named output socket.
    for offset, attr_name in enumerate(channels, start=1):
        mix = band_sample_field(node_group, scene_time, dt, data_obj, attr_name)
        links.new(mix.outputs[0], group_out.inputs[offset])

    return node_group
