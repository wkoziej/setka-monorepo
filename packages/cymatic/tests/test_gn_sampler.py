# ABOUTME: Tests for the in-Blender GN sampler builder (bridge-B, Spike 2)
# ABOUTME: Structural / API-shape assertions via mock bpy; live correctness proven in Spike 2

"""Unit 7 tests: build_sampler_group builds the GN time-sampling node group.

These are STRUCTURAL assertions against the autouse ``mock_bpy`` fixture
(conftest). Real sampling correctness was already proven live in Spike 2
(research/spike2_gn_sampling.py, Blender 5.1.2, max abs err ~6e-08). Here we
only guard structure / API shape:

  - a ``GeometryNodeTree`` node group is created,
  - sockets are created via ``interface.new_socket`` (the 4.0+ API), NOT via the
    removed ``node_group.inputs`` / ``node_group.outputs`` collections,
  - the expected node ``bl_idname``s are instantiated,
  - ``clamp=True`` and ``data_type='FLOAT'`` are set on the Sample Index nodes,
  - ``dt`` is threaded through as a node default (not hardcoded).

NOTE (plan/feasibility review): a plain ``Mock`` fabricates every attribute, so a
naive ``mock_ng.inputs`` and ``mock_ng.interface`` are indistinguishably truthy
and a mock test cannot detect a 3.x->4.x regression by attribute existence. We
therefore use a ``spec``-restricted node-group mock whose ``inputs``/``outputs``
attributes do NOT exist: touching them raises ``AttributeError``. That asserts on
the *code path* — the builder must route through ``interface.new_socket``.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Make the in-Blender module importable (also done in conftest; defensive).
blender_script_path = Path(__file__).parent.parent / "blender_script"
if str(blender_script_path) not in sys.path:
    sys.path.insert(0, str(blender_script_path))

import gn_sampler  # noqa: E402

build_sampler_group = gn_sampler.build_sampler_group
DEFAULT_CHANNELS = gn_sampler.DEFAULT_CHANNELS


class _NodeGroup:
    """Stand-in for a GeometryNodeTree.

    Crucially has ``interface``, ``nodes``, ``links`` but NO ``inputs`` /
    ``outputs`` attributes — so any use of the removed 3.x API raises
    ``AttributeError`` rather than being silently fabricated by ``Mock``.
    """

    def __init__(self):
        self.interface = MagicMock()
        self.nodes = MagicMock()
        self.links = MagicMock()
        # Each nodes.new(bl_idname) returns a fresh node recording its idname.
        self.created_nodes = []

        def _new_node(bl_idname, *args, **kwargs):
            node = MagicMock()
            node.bl_idname = bl_idname
            self.created_nodes.append(node)
            return node

        self.nodes.new.side_effect = _new_node


@pytest.fixture
def node_group(mock_bpy):
    """Wire ``bpy.data.node_groups.new`` to return our spec'd node group."""
    ng = _NodeGroup()
    mock_bpy.data.node_groups.new.return_value = ng
    return ng


def _build(node_group, channels=DEFAULT_CHANNELS):
    data_obj = MagicMock(name="data_obj")
    return build_sampler_group("sampler", dt=0.010667, data_obj=data_obj, channels=channels)


def test_creates_geometry_node_tree(mock_bpy, node_group):
    result = _build(node_group)
    args, _ = mock_bpy.data.node_groups.new.call_args
    assert args[1] == "GeometryNodeTree"
    assert result is node_group


def test_sockets_created_via_interface_new_socket(mock_bpy, node_group):
    """Geometry IN/OUT + one FLOAT OUT per channel, all via interface.new_socket."""
    _build(node_group)
    calls = node_group.interface.new_socket.call_args_list
    # 2 geometry sockets + one per channel.
    assert len(calls) == 2 + len(DEFAULT_CHANNELS)

    geo_in = [c for c in calls if c.kwargs.get("socket_type") == "NodeSocketGeometry"
              and c.kwargs.get("in_out") == "INPUT"]
    geo_out = [c for c in calls if c.kwargs.get("socket_type") == "NodeSocketGeometry"
               and c.kwargs.get("in_out") == "OUTPUT"]
    assert len(geo_in) == 1
    assert len(geo_out) == 1

    float_out_names = [
        c.args[0] for c in calls
        if c.kwargs.get("socket_type") == "NodeSocketFloat"
        and c.kwargs.get("in_out") == "OUTPUT"
    ]
    for name in DEFAULT_CHANNELS:
        assert name in float_out_names


def test_does_not_use_removed_inputs_outputs_api(mock_bpy, node_group):
    """The 3.x ng.inputs / ng.outputs collections must never be touched."""
    # _NodeGroup has no such attributes; if the builder used them this raises.
    assert not hasattr(node_group, "inputs")
    assert not hasattr(node_group, "outputs")
    _build(node_group)  # must complete without AttributeError


def test_expected_node_bl_idnames_instantiated(mock_bpy, node_group):
    _build(node_group)
    idnames = [n.bl_idname for n in node_group.created_nodes]
    for expected in (
        "NodeGroupInput",
        "NodeGroupOutput",
        "GeometryNodeInputSceneTime",
        "ShaderNodeMath",
        "GeometryNodeObjectInfo",
        "GeometryNodeInputNamedAttribute",
        "GeometryNodeSampleIndex",
        "ShaderNodeMix",
    ):
        assert expected in idnames, f"missing node {expected}"


def test_single_scene_time_shared_across_channels(mock_bpy, node_group):
    _build(node_group)
    scene_times = [
        n for n in node_group.created_nodes
        if n.bl_idname == "GeometryNodeInputSceneTime"
    ]
    assert len(scene_times) == 1


def test_two_sample_index_per_channel(mock_bpy, node_group):
    _build(node_group)
    sample_nodes = [
        n for n in node_group.created_nodes
        if n.bl_idname == "GeometryNodeSampleIndex"
    ]
    assert len(sample_nodes) == 2 * len(DEFAULT_CHANNELS)


def test_sample_index_clamp_and_data_type(mock_bpy, node_group):
    _build(node_group)
    sample_nodes = [
        n for n in node_group.created_nodes
        if n.bl_idname == "GeometryNodeSampleIndex"
    ]
    assert sample_nodes
    for sample in sample_nodes:
        assert sample.clamp is True
        assert sample.data_type == "FLOAT"
        assert sample.domain == "POINT"


def test_named_attribute_is_float(mock_bpy, node_group):
    _build(node_group)
    named = [
        n for n in node_group.created_nodes
        if n.bl_idname == "GeometryNodeInputNamedAttribute"
    ]
    assert named
    for n in named:
        assert n.data_type == "FLOAT"


def test_mix_node_is_float(mock_bpy, node_group):
    _build(node_group)
    mixes = [n for n in node_group.created_nodes if n.bl_idname == "ShaderNodeMix"]
    assert len(mixes) == len(DEFAULT_CHANNELS)
    for m in mixes:
        assert m.data_type == "FLOAT"


def test_dt_threaded_into_divide_default(mock_bpy, node_group):
    """dt is set as a node default (param), not hardcoded constant."""
    dt = 0.011610
    data_obj = MagicMock()
    build_sampler_group("sampler", dt=dt, data_obj=data_obj, channels=("bass_n",))

    divides = [
        n for n in node_group.created_nodes
        if n.bl_idname == "ShaderNodeMath" and getattr(n, "operation", None) == "DIVIDE"
    ]
    assert divides, "expected a DIVIDE math node (index = Seconds / dt)"
    # The divide's second input default_value must have been set to dt.
    set_to_dt = any(
        d.inputs.__getitem__.return_value.default_value == dt for d in divides
    )
    assert set_to_dt


def test_custom_channels_subset(mock_bpy, node_group):
    _build(node_group, channels=("bass_n", "mid_n"))
    float_out_names = [
        c.args[0] for c in node_group.interface.new_socket.call_args_list
        if c.kwargs.get("socket_type") == "NodeSocketFloat"
    ]
    assert float_out_names == ["bass_n", "mid_n"]


def test_empty_channels_raise(mock_bpy, node_group):
    with pytest.raises(ValueError):
        _build(node_group, channels=())
