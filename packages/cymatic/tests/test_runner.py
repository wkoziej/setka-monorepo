# ABOUTME: Tests for the host-side cymatic runner (Blender subprocess orchestration).
# ABOUTME: Uses the autouse mock_subprocess fixture from conftest; no real Blender.

"""Unit 9 — host-side runner tests.

Mirrors cinemon's BlenderProjectManager subprocess pattern:
  [blender_exec, "--background", "--python", build_scene.py, "--", "--config", <file>]
with capture_output/text/check, RuntimeError carrying stderr on failure.
"""

import shutil
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from cymatic.config import VisualizerConfig
from cymatic.runner import CymaticRunner, render

# Capture the real mux before the autouse fixture below patches it to a no-op,
# so the dedicated mux test can exercise the real implementation.
_REAL_MUX = CymaticRunner._mux_frames
_REAL_VALIDATE = CymaticRunner._validate_frame_count


@pytest.fixture(autouse=True)
def _skip_mux(monkeypatch):
    """Stub out frame muxing + frame-count validation for invocation tests.

    These tests verify the Blender invocation, not video encoding; the mocked
    subprocess never renders real frames, so the real _mux_frames would raise
    "No frames rendered" and _validate_frame_count would have nothing to count.
    The dedicated mux test uses _REAL_MUX directly.
    """
    monkeypatch.setattr(
        CymaticRunner, "_mux_frames", lambda self, fdir, out, cfg=None: None
    )
    monkeypatch.setattr(
        CymaticRunner, "_validate_frame_count", lambda self, fdir, cfg: None
    )


@pytest.fixture
def recording_dir(tmp_path):
    """A recording directory with the expected analysis layout."""
    (tmp_path / "analysis").mkdir()
    analysis_file = tmp_path / "analysis" / "song_analysis.json"
    analysis_file.write_text("{}")
    return tmp_path


@pytest.fixture
def config(recording_dir):
    return VisualizerConfig(
        analysis_file=str(recording_dir / "analysis" / "song_analysis.json"),
        output_mp4="",  # runner resolves it under blender/render/
        base_directory=str(recording_dir),
        blender_executable="/Applications/Blender.app/Contents/MacOS/Blender",
    )


def _captured_cmd(mock_run):
    """Return the command list passed to the mocked subprocess.run."""
    assert mock_run.called, "subprocess.run was not called"
    args, _kwargs = mock_run.call_args
    return list(args[0])


def test_command_built_with_config_and_build_scene_path(config):
    """Command includes --config <file> and the resolved build_scene.py path."""
    runner = CymaticRunner(config)
    runner.run()

    cmd = _captured_cmd(subprocess.run)

    # Resolved build_scene.py path (mirrors cinemon resolution from runner.py).
    expected_script = (
        Path(__file__).parent.parent / "blender_script" / "build_scene.py"
    )
    assert str(expected_script) in cmd
    assert expected_script.exists()

    # Blender headless invocation structure.
    assert "--background" in cmd
    assert "--python" in cmd
    assert "--" in cmd  # separator between Blender args and script args
    assert "--config" in cmd

    # --config is followed by a path, and after the "--" separator.
    cfg_idx = cmd.index("--config")
    assert cfg_idx > cmd.index("--")
    config_path = cmd[cfg_idx + 1]
    assert Path(config_path).name  # non-empty path token


def test_explicit_executable_used_directly_macos(config):
    """An explicit blender_executable path is used directly (no snap wrapper)."""
    config.blender_executable = "/Applications/Blender.app/Contents/MacOS/Blender"
    runner = CymaticRunner(config)
    runner.run()

    cmd = _captured_cmd(subprocess.run)
    assert cmd[0] == "/Applications/Blender.app/Contents/MacOS/Blender"
    assert "snap" not in cmd


def test_default_blender_executable_uses_snap_branch_linux(config):
    """blender_executable == 'blender' -> snap run blender (Linux branch)."""
    config.blender_executable = "blender"
    runner = CymaticRunner(config)
    runner.run()

    cmd = _captured_cmd(subprocess.run)
    assert cmd[:3] == ["snap", "run", "blender"]


def test_called_process_error_raises_runtime_error_with_stderr(config, monkeypatch):
    """CalledProcessError is re-raised as RuntimeError carrying stderr."""
    error = subprocess.CalledProcessError(
        returncode=1, cmd=["blender"], output="", stderr="boom: GN build failed"
    )
    monkeypatch.setattr(subprocess, "run", Mock(side_effect=error))

    runner = CymaticRunner(config)
    with pytest.raises(RuntimeError) as exc_info:
        runner.run()

    assert "boom: GN build failed" in str(exc_info.value)


def test_output_path_under_blender_render(config, recording_dir):
    """Output mp4 is resolved under blender/render/ via ensure_blender_dir."""
    runner = CymaticRunner(config)
    output = runner.run()

    output = Path(output)
    assert output.parent == recording_dir / "blender" / "render"
    assert output.suffix == ".mp4"
    # ensure_blender_dir created the directory tree.
    assert (recording_dir / "blender" / "render").is_dir()


def test_temp_config_file_cleaned_up(config):
    """The serialized temp config file is removed after the subprocess."""
    runner = CymaticRunner(config)

    captured_paths = []

    real_run = subprocess.run  # the mock from conftest

    def capturing_run(cmd, *a, **k):
        # Record the --config path and confirm it exists DURING the call.
        cmd = list(cmd)
        idx = cmd.index("--config")
        cfg_path = cmd[idx + 1]
        captured_paths.append(cfg_path)
        assert Path(cfg_path).exists(), "config file must exist during subprocess"
        return real_run(cmd, *a, **k)

    import unittest.mock as _mock

    with _mock.patch.object(subprocess, "run", side_effect=capturing_run):
        runner.run()

    assert captured_paths, "subprocess.run was not invoked"
    for p in captured_paths:
        assert not Path(p).exists(), f"temp config not cleaned up: {p}"


def test_render_convenience_function(config, recording_dir):
    """The module-level render() helper drives the runner end-to-end."""
    output = render(config)
    assert Path(output).parent == recording_dir / "blender" / "render"


def test_mux_frames_builds_ffmpeg_command(config, tmp_path, monkeypatch):
    """_mux_frames feeds the PNG sequence (+audio) to ffmpeg with H.264/yuv420p."""
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    (frames_dir / "frame_0001.png").write_bytes(b"\x89PNG\r\n")  # fake frame
    output = tmp_path / "out.mp4"

    config.fps = 24
    config.frame_start = 1
    config.audio_file = str(tmp_path / "a.wav")
    (tmp_path / "a.wav").write_bytes(b"RIFF")  # exists -> audio muxed

    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/ffmpeg")
    captured = {}

    def fake_run(cmd, *a, **k):
        captured["cmd"] = list(cmd)
        return Mock(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    _REAL_MUX(CymaticRunner(config), frames_dir, output)

    cmd = captured["cmd"]
    assert cmd[0] == "/usr/bin/ffmpeg"
    assert "-framerate" in cmd and "24" in cmd
    assert "-start_number" in cmd
    assert "libx264" in cmd and "yuv420p" in cmd
    assert "aac" in cmd and "-shortest" in cmd  # audio present
    assert str(output) == cmd[-1]


def test_mux_frames_no_frames_raises(config, tmp_path, monkeypatch):
    """Empty frames dir -> clear RuntimeError (not a silent empty mp4)."""
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/ffmpeg")
    with pytest.raises(RuntimeError, match="No frames"):
        _REAL_MUX(CymaticRunner(config), tmp_path / "empty", tmp_path / "o.mp4")


def test_run_does_not_mutate_caller_config(config):
    """run() must not mutate the caller's VisualizerConfig.frames_dir."""
    assert config.frames_dir is None
    runner = CymaticRunner(config)
    runner.run()
    # The runner works on a dataclasses.replace() copy; caller's stays None.
    assert config.frames_dir is None


def test_missing_blender_executable_raises_before_subprocess(config, monkeypatch):
    """A None/empty executable raises a clear RuntimeError before spawning."""
    config.blender_executable = None
    called = {"ran": False}

    def boom(*a, **k):
        called["ran"] = True
        raise AssertionError("subprocess.run must not be called")

    monkeypatch.setattr(subprocess, "run", boom)
    runner = CymaticRunner(config)
    with pytest.raises(RuntimeError, match="Blender executable not found"):
        runner.run()
    assert called["ran"] is False


def test_blender_timeout_raises_runtime_error(config, monkeypatch):
    """A Blender subprocess timeout becomes a RuntimeError with context."""
    config.blender_timeout_sec = 5
    timeout = subprocess.TimeoutExpired(cmd=["blender"], timeout=5)
    monkeypatch.setattr(subprocess, "run", Mock(side_effect=timeout))

    runner = CymaticRunner(config)
    with pytest.raises(RuntimeError, match="timed out after 5s"):
        runner.run()


def test_blender_timeout_value_forwarded(config):
    """The configured blender_timeout_sec is forwarded to subprocess.run."""
    config.blender_timeout_sec = 1234
    CymaticRunner(config).run()
    _args, kwargs = subprocess.run.call_args
    assert kwargs.get("timeout") == 1234


def test_short_frame_count_raises(config, monkeypatch, tmp_path):
    """Fewer rendered frames than expected -> RuntimeError (incomplete render)."""
    # Re-enable the real validator (the autouse fixture stubbed it).
    monkeypatch.setattr(
        CymaticRunner, "_validate_frame_count", _REAL_VALIDATE
    )
    # frame_end set explicitly so we don't need a real analysis file.
    config.frame_start = 1
    config.frame_end = 10  # expect 10 frames

    # Make build_scene render only 3 frames into the temp frames_dir.
    def fake_run(cmd, *a, **k):
        cmd = list(cmd)
        cfg_path = cmd[cmd.index("--config") + 1]
        import json as _json

        cfg = _json.loads(Path(cfg_path).read_text())
        fdir = Path(cfg["frames_dir"])
        for i in range(1, 4):  # only 3 frames
            (fdir / f"frame_{i:04d}.png").write_bytes(b"\x89PNG")
        return Mock(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    runner = CymaticRunner(config)
    with pytest.raises(RuntimeError, match="expected 10"):
        runner.run()


def test_full_frame_count_passes(config, monkeypatch):
    """Exactly the expected frame count passes validation."""
    monkeypatch.setattr(CymaticRunner, "_validate_frame_count", _REAL_VALIDATE)
    config.frame_start = 1
    config.frame_end = 5

    def fake_run(cmd, *a, **k):
        cmd = list(cmd)
        cfg_path = cmd[cmd.index("--config") + 1]
        import json as _json

        cfg = _json.loads(Path(cfg_path).read_text())
        fdir = Path(cfg["frames_dir"])
        for i in range(1, 6):  # exactly 5 frames
            (fdir / f"frame_{i:04d}.png").write_bytes(b"\x89PNG")
        return Mock(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    # mux is still stubbed by the autouse fixture; should not raise.
    CymaticRunner(config).run()
