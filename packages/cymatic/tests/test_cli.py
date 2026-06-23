# ABOUTME: Tests for the cymatic CLI (cymatic-render) — arg handling + error routing.
# ABOUTME: Mocks the runner so no Blender/ffmpeg is needed; checks stdout/stderr split.

"""Tests for cymatic.cli.main.

Covers:
- missing recording directory -> stderr + nonzero exit
- missing analysis file -> stderr + nonzero exit
- successful path (runner mocked) -> output path on stdout, exit 0
- runner RuntimeError -> stderr + nonzero exit
- audio forwarding: auto-detected and explicit --audio-file
"""

import logging
from pathlib import Path

import pytest

import cymatic.cli as cli


@pytest.fixture
def recording_dir(tmp_path):
    """A recording dir with analysis/<stem>_analysis.json present."""
    (tmp_path / "analysis").mkdir()
    (tmp_path / "analysis" / "song_analysis.json").write_text("{}")
    return tmp_path


def test_missing_recording_dir_writes_stderr_and_returns_nonzero(tmp_path, capsys):
    missing = tmp_path / "nope"
    rc = cli.main([str(missing)])
    captured = capsys.readouterr()
    assert rc != 0
    assert "recording directory not found" in captured.err
    assert captured.out == ""


def test_missing_analysis_file_writes_stderr_and_returns_nonzero(
    recording_dir, capsys
):
    rc = cli.main(
        [str(recording_dir), "--analysis-file", str(recording_dir / "absent.json")]
    )
    captured = capsys.readouterr()
    assert rc != 0
    assert "Analysis file not found" in captured.err
    assert captured.out == ""


def test_successful_path_prints_output_on_stdout(recording_dir, capsys, monkeypatch):
    analysis = recording_dir / "analysis" / "song_analysis.json"
    fake_output = recording_dir / "blender" / "render" / "song.mp4"

    captured_cfg = {}

    def fake_render(config):
        captured_cfg["config"] = config
        return fake_output

    monkeypatch.setattr(cli, "render", fake_render)

    rc = cli.main([str(recording_dir), "--analysis-file", str(analysis), "--fps", "24"])
    out = capsys.readouterr()
    assert rc == 0
    assert str(fake_output) in out.out
    assert out.err == ""
    assert captured_cfg["config"].fps == 24
    assert captured_cfg["config"].analysis_file == str(analysis)


def test_runner_error_routes_to_stderr_and_nonzero(recording_dir, capsys, monkeypatch):
    analysis = recording_dir / "analysis" / "song_analysis.json"

    def boom(config):
        raise RuntimeError("Blender execution failed: GN build error")

    monkeypatch.setattr(cli, "render", boom)

    rc = cli.main([str(recording_dir), "--analysis-file", str(analysis)])
    captured = capsys.readouterr()
    assert rc != 0
    assert "GN build error" in captured.err
    assert captured.out == ""


def test_explicit_audio_file_forwarded_to_config(recording_dir, monkeypatch):
    analysis = recording_dir / "analysis" / "song_analysis.json"
    audio = recording_dir / "my_audio.wav"
    audio.write_bytes(b"RIFF")

    captured_cfg = {}
    monkeypatch.setattr(
        cli, "render", lambda config: captured_cfg.setdefault("c", config) or Path("/x.mp4")
    )

    rc = cli.main(
        [
            str(recording_dir),
            "--analysis-file",
            str(analysis),
            "--audio-file",
            str(audio),
        ]
    )
    assert rc == 0
    assert captured_cfg["c"].audio_file == str(audio)


def test_detected_audio_forwarded_when_no_explicit_flag(
    recording_dir, monkeypatch
):
    # When detection runs (no --analysis-file), the detected audio is forwarded.
    detected = recording_dir / "extracted" / "main.wav"

    monkeypatch.setattr(
        cli,
        "_resolve_analysis_file",
        lambda rd, af, ma: (
            recording_dir / "analysis" / "song_analysis.json",
            detected,
        ),
    )
    captured_cfg = {}
    monkeypatch.setattr(
        cli, "render", lambda config: captured_cfg.setdefault("c", config) or Path("/x.mp4")
    )

    rc = cli.main([str(recording_dir)])
    assert rc == 0
    assert captured_cfg["c"].audio_file == str(detected)


def test_explicit_analysis_without_audio_logs_silent_info(
    recording_dir, monkeypatch, caplog
):
    """--analysis-file (no detection) and no --audio-file -> INFO 'rendering silent'."""
    analysis = recording_dir / "analysis" / "song_analysis.json"
    monkeypatch.setattr(cli, "render", lambda config: Path("/x.mp4"))

    with caplog.at_level(logging.INFO, logger="cymatic.cli"):
        rc = cli.main([str(recording_dir), "--analysis-file", str(analysis)])

    assert rc == 0
    assert any(
        "silent" in r.message.lower() and r.levelno == logging.INFO
        for r in caplog.records
    ), [r.message for r in caplog.records]


def test_no_audio_detected_logs_warning(recording_dir, monkeypatch, caplog):
    """Detection ran (no --analysis-file) but found no audio -> WARNING, not silent INFO."""
    monkeypatch.setattr(
        cli,
        "_resolve_analysis_file",
        lambda rd, af, ma: (
            recording_dir / "analysis" / "song_analysis.json",
            None,  # detection produced no audio
        ),
    )
    monkeypatch.setattr(cli, "render", lambda config: Path("/x.mp4"))

    with caplog.at_level(logging.WARNING, logger="cymatic.cli"):
        rc = cli.main([str(recording_dir)])

    assert rc == 0
    assert any(
        r.levelno == logging.WARNING and "audio" in r.message.lower()
        for r in caplog.records
    ), [r.message for r in caplog.records]
