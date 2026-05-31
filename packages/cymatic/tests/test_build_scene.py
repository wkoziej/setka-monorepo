# ABOUTME: Tests for the in-Blender orchestration entry point (Unit 8)
# ABOUTME: Structural via mock bpy + spies; live correctness proven in Spike 0/2

"""Unit 8 tests: build_scene.main() ties config -> data-object -> sampler -> preset.

These are STRUCTURAL assertions against the autouse ``mock_bpy`` fixture
(conftest). Live visual correctness was already proven in Spike 0/2 (Blender
5.1.2). Here we only verify orchestration:

  - ``main()`` parses ``--config`` and loads the ``VisualizerConfig``,
  - it calls data_object builder, then sampler builder, then the preset's
    ``build_scene`` in that order, threading the loaded analysis through,
  - it returns 0 on success,
  - a missing ``--config`` yields a non-zero code with a clear error.

The host-side numpy modules (analysis_loader / normalization) are pure-numpy
(no bpy) and are imported by build_scene by injecting the package ``src/`` onto
sys.path; the loader itself is spied so these tests stay structural.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# Make the in-Blender module importable (also done in conftest; defensive).
blender_script_path = Path(__file__).parent.parent / "blender_script"
if str(blender_script_path) not in sys.path:
    sys.path.insert(0, str(blender_script_path))

import build_scene  # noqa: E402


def _write_config(tmp_path: Path) -> Path:
    """Write a minimal serialized VisualizerConfig to a temp file."""
    cfg = {
        "analysis_file": str(tmp_path / "song_analysis.json"),
        "output_mp4": str(tmp_path / "out.mp4"),
        "base_directory": str(tmp_path),
        "fps": 30,
        "resolution": [1280, 720],
        "blender_executable": "/bin/true",
        "preset": {
            "palette": "default",
            "primitive": "icosphere",
            "accent_intensity": 0.5,
            "decay": 0.13,
            "tau": 0.15,
        },
    }
    p = tmp_path / "config.json"
    p.write_text(json.dumps(cfg))
    return p


def _fake_analysis():
    """A MagicMock standing in for analysis_loader.AnalysisData."""
    n = 16
    data = MagicMock(name="AnalysisData")
    data.bass = np.linspace(0, 1, n, dtype=np.float32)
    data.mid = np.linspace(0, 1, n, dtype=np.float32)
    data.high = np.linspace(0, 1, n, dtype=np.float32)
    data.beat_env = np.zeros(n, dtype=np.float32)
    data.peak_env = np.zeros(n, dtype=np.float32)
    data.times = np.arange(n, dtype=float) * 0.01
    data.dt = 0.01
    data.sample_rate = 48000
    data.duration = n * 0.01
    data.fps = 30
    return data


@pytest.fixture
def spies(tmp_path):
    """Patch the three collaborators build_scene orchestrates and the loader."""
    cfg_path = _write_config(tmp_path)
    analysis = _fake_analysis()

    with patch.object(
        build_scene, "load_analysis", return_value=analysis
    ) as load, patch.object(
        build_scene, "build_data_object", return_value=MagicMock(name="data_obj")
    ) as data_obj, patch.object(
        build_scene, "build_sampler_group", return_value=MagicMock(name="sampler")
    ) as sampler, patch.object(
        build_scene, "build_preset_scene", return_value=MagicMock(name="scene")
    ) as preset:
        yield {
            "cfg_path": cfg_path,
            "analysis": analysis,
            "load": load,
            "data_obj": data_obj,
            "sampler": sampler,
            "preset": preset,
        }


def test_main_returns_zero_on_success(mock_bpy, spies):
    rc = build_scene.main(["--config", str(spies["cfg_path"])])
    assert rc == 0


def test_main_loads_config_and_analysis(mock_bpy, spies):
    build_scene.main(["--config", str(spies["cfg_path"])])
    spies["load"].assert_called_once()
    # load_analysis received a VisualizerConfig with our analysis_file.
    (cfg_arg,), _ = spies["load"].call_args
    assert cfg_arg.fps == 30
    assert cfg_arg.analysis_file.endswith("song_analysis.json")


def test_main_calls_collaborators_in_order(mock_bpy, spies):
    """data_object -> sampler -> preset, threading analysis + sampler through."""
    manager = MagicMock()
    manager.attach_mock(spies["load"], "load")
    manager.attach_mock(spies["data_obj"], "data_obj")
    manager.attach_mock(spies["sampler"], "sampler")
    manager.attach_mock(spies["preset"], "preset")

    build_scene.main(["--config", str(spies["cfg_path"])])

    order = [c[0] for c in manager.mock_calls if c[0] in
             ("load", "data_obj", "sampler", "preset")]
    assert order == ["load", "data_obj", "sampler", "preset"]


def test_sampler_receives_data_object(mock_bpy, spies):
    build_scene.main(["--config", str(spies["cfg_path"])])
    data_obj_ret = spies["data_obj"].return_value
    _, sampler_kwargs = spies["sampler"].call_args
    sampler_args = spies["sampler"].call_args.args
    assert data_obj_ret in sampler_args or data_obj_ret in sampler_kwargs.values()


def test_preset_receives_sampler(mock_bpy, spies):
    build_scene.main(["--config", str(spies["cfg_path"])])
    sampler_ret = spies["sampler"].return_value
    preset_args = spies["preset"].call_args.args
    preset_kwargs = spies["preset"].call_args.kwargs
    assert sampler_ret in preset_args or sampler_ret in preset_kwargs.values()


def test_data_object_built_from_five_channels(mock_bpy, spies):
    build_scene.main(["--config", str(spies["cfg_path"])])
    _, kwargs = spies["data_obj"].call_args
    args = spies["data_obj"].call_args.args
    # channels mapping is passed positionally or by keyword.
    channels = kwargs.get("channels")
    if channels is None:
        channels = next((a for a in args if isinstance(a, dict)), None)
    assert channels is not None
    for name in ("bass_n", "mid_n", "high_n", "beat_env", "peak_env"):
        assert name in channels


def test_missing_config_returns_nonzero(mock_bpy):
    rc = build_scene.main([])
    assert rc != 0


def test_missing_config_does_not_call_collaborators(mock_bpy):
    with patch.object(build_scene, "load_analysis") as load:
        rc = build_scene.main([])
        assert rc != 0
        load.assert_not_called()
