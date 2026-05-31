# ABOUTME: Tests for the in-Blender data-object builder (numpy -> mesh + attrs)
# ABOUTME: Structural assertions via mock bpy; GN-sampling correctness proven in Spike 2

"""Unit 6 tests: build_data_object turns numpy channels into a Blender mesh.

These are structural assertions against the autouse ``mock_bpy`` fixture
(conftest). Real GN-sampling correctness was already proven empirically in
Spike 2 (research/spike2_gn_sampling.py, Blender 5.1.2). Here we only verify
that the builder calls the bpy API correctly:

  - one FLOAT/POINT attribute per channel via ``attributes.new``,
  - ``vertices.add(N)`` with the right N,
  - ``foreach_set`` receives a length-N buffer,
  - mismatched channel lengths raise.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

# Make the in-Blender module importable (also done in conftest, kept defensive).
blender_script_path = Path(__file__).parent.parent / "blender_script"
if str(blender_script_path) not in sys.path:
    sys.path.insert(0, str(blender_script_path))

import data_object  # noqa: E402

build_data_object = data_object.build_data_object


CHANNEL_NAMES = ["bass_n", "mid_n", "high_n", "beat_env", "peak_env"]


def _channels(n):
    """Five equal-length float channels of length ``n``."""
    return {name: np.linspace(0.0, 1.0, n, dtype=np.float64) for name in CHANNEL_NAMES}


def test_creates_attribute_for_each_channel(mock_bpy):
    n = 8
    build_data_object("audio_data", dt=0.01, channels=_channels(n))

    mesh = mock_bpy.data.meshes.new.return_value
    created = [c.kwargs.get("name") for c in mesh.attributes.new.call_args_list]
    for name in CHANNEL_NAMES:
        assert name in created
    assert mesh.attributes.new.call_count == len(CHANNEL_NAMES)


def test_attributes_are_float_point(mock_bpy):
    build_data_object("audio_data", dt=0.01, channels=_channels(8))

    mesh = mock_bpy.data.meshes.new.return_value
    for call in mesh.attributes.new.call_args_list:
        assert call.kwargs.get("type") == "FLOAT"
        assert call.kwargs.get("domain") == "POINT"


def test_vertices_add_called_with_n(mock_bpy):
    n = 13
    build_data_object("audio_data", dt=0.01, channels=_channels(n))

    mesh = mock_bpy.data.meshes.new.return_value
    mesh.vertices.add.assert_called_once_with(n)


def test_attribute_foreach_set_receives_length_n_buffer(mock_bpy):
    n = 10
    build_data_object("audio_data", dt=0.01, channels=_channels(n))

    mesh = mock_bpy.data.meshes.new.return_value
    attr = mesh.attributes.new.return_value
    # One foreach_set("value", buf) per channel.
    assert attr.data.foreach_set.call_count == len(CHANNEL_NAMES)
    for call in attr.data.foreach_set.call_args_list:
        key, buf = call.args
        assert key == "value"
        assert len(buf) == n


def test_attribute_buffer_is_float32_contiguous(mock_bpy):
    build_data_object("audio_data", dt=0.01, channels=_channels(7))

    mesh = mock_bpy.data.meshes.new.return_value
    attr = mesh.attributes.new.return_value
    for call in attr.data.foreach_set.call_args_list:
        _, buf = call.args
        assert isinstance(buf, np.ndarray)
        assert buf.dtype == np.float32
        assert buf.flags["C_CONTIGUOUS"]


def test_x_positions_are_arange_times_dt(mock_bpy):
    n = 6
    dt = 0.0125
    build_data_object("audio_data", dt=dt, channels=_channels(n))

    mesh = mock_bpy.data.meshes.new.return_value
    # vertices.foreach_set("co", co) where co[0::3] == arange(N)*dt
    co_calls = [
        c for c in mesh.vertices.foreach_set.call_args_list if c.args and c.args[0] == "co"
    ]
    assert len(co_calls) == 1
    co = co_calls[0].args[1]
    assert len(co) == n * 3
    np.testing.assert_allclose(co[0::3], np.arange(n) * dt)


def test_mismatched_channel_lengths_raise(mock_bpy):
    channels = _channels(8)
    channels["mid_n"] = np.linspace(0.0, 1.0, 5, dtype=np.float64)  # wrong length

    with pytest.raises(ValueError):
        build_data_object("audio_data", dt=0.01, channels=channels)


def test_empty_channels_raise(mock_bpy):
    with pytest.raises(ValueError):
        build_data_object("audio_data", dt=0.01, channels={})


def test_returns_object(mock_bpy):
    obj = build_data_object("audio_data", dt=0.01, channels=_channels(8))
    assert obj is mock_bpy.data.objects.new.return_value
