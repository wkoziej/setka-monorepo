"""
Tests for per-source audio extraction via ffmpeg -map and ffmpeg timeout handling.

These cover the Unit 5.1 remediation:
- each ``has_audio`` source must carry its OWN audio stream (``-map 0:a:<i>``),
  not an identical full-canvas copy shared by every source;
- a hung/over-long ffmpeg run must surface as a failed ``ExtractionResult``
  (``subprocess.TimeoutExpired``), not hang or raise.
"""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

from obsession.core.extractor import extract_sources


def _make_video(temp_dir: str) -> Path:
    video = Path(temp_dir) / "canvas.mkv"
    video.write_text("dummy")
    return video


class TestPerSourceAudioMapping:
    """Each audio source gets its own -map stream, not N identical copies."""

    def test_each_audio_source_maps_its_own_stream(self):
        """Two audio sources => two distinct ``-map 0:a:N`` indices."""
        metadata = {
            "canvas_size": [1920, 1080],
            "fps": 30.0,
            "timestamp": 1.0,
            "sources": {
                "Microphone": {
                    "position": {"x": 0, "y": 0},
                    "has_video": False,
                    "has_audio": True,
                },
                "Desktop": {
                    "position": {"x": 0, "y": 0},
                    "has_video": False,
                    "has_audio": True,
                },
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            video = _make_video(temp_dir)

            with patch(
                "obsession.core.extractor.subprocess.run"
            ) as mock_run:
                mock_run.return_value = subprocess.CompletedProcess(
                    args=[], returncode=0, stdout="", stderr=""
                )

                result = extract_sources(str(video), metadata)

        assert result.success is True

        # Collect the -map argument that followed each "-map" flag.
        map_values = []
        for call in mock_run.call_args_list:
            cmd = call[0][0]
            for i, token in enumerate(cmd):
                if token == "-map":
                    map_values.append(cmd[i + 1])

        # Two audio sources => stream indices 0:a:0 and 0:a:1, each used once.
        assert "0:a:0" in map_values
        assert "0:a:1" in map_values
        assert len(set(map_values)) == len(map_values), (
            f"audio sources share a stream mapping (duplicate copies): {map_values}"
        )

    def test_audio_stream_index_skips_video_only_sources(self):
        """Audio stream index counts audio sources only, ignoring video-only ones."""
        metadata = {
            "canvas_size": [1920, 1080],
            "fps": 30.0,
            "timestamp": 1.0,
            "sources": {
                "Camera1": {
                    "position": {"x": 0, "y": 0},
                    "dimensions": {"source_width": 800, "source_height": 600},
                    "has_video": True,
                    "has_audio": False,
                },
                "Microphone": {
                    "position": {"x": 0, "y": 0},
                    "has_video": False,
                    "has_audio": True,
                },
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            video = _make_video(temp_dir)

            with patch(
                "obsession.core.extractor.subprocess.run"
            ) as mock_run:
                mock_run.return_value = subprocess.CompletedProcess(
                    args=[], returncode=0, stdout="", stderr=""
                )

                result = extract_sources(str(video), metadata)

        assert result.success is True

        audio_calls = [
            call[0][0]
            for call in mock_run.call_args_list
            if "-vn" in call[0][0]
        ]
        assert len(audio_calls) == 1
        # The single (first) audio source maps to 0:a:0 regardless of the
        # preceding video-only source.
        cmd = audio_calls[0]
        assert "-map" in cmd
        assert cmd[cmd.index("-map") + 1] == "0:a:0"


class TestFfmpegTimeout:
    """A hung ffmpeg surfaces as a failed result, not a hang."""

    def test_audio_timeout_yields_failed_result(self):
        metadata = {
            "canvas_size": [1920, 1080],
            "fps": 30.0,
            "timestamp": 1.0,
            "sources": {
                "Microphone": {
                    "position": {"x": 0, "y": 0},
                    "has_video": False,
                    "has_audio": True,
                },
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            video = _make_video(temp_dir)

            with patch(
                "obsession.core.extractor.subprocess.run",
                side_effect=subprocess.TimeoutExpired(cmd="ffmpeg", timeout=1800),
            ):
                result = extract_sources(str(video), metadata)

        assert result.success is False
        assert "timeout" in result.error_message.lower()

    def test_video_timeout_yields_failed_result(self):
        metadata = {
            "canvas_size": [1920, 1080],
            "fps": 30.0,
            "timestamp": 1.0,
            "sources": {
                "Camera1": {
                    "position": {"x": 0, "y": 0},
                    "dimensions": {"source_width": 800, "source_height": 600},
                    "has_video": True,
                    "has_audio": False,
                },
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            video = _make_video(temp_dir)

            with patch(
                "obsession.core.extractor.subprocess.run",
                side_effect=subprocess.TimeoutExpired(cmd="ffmpeg", timeout=1800),
            ):
                result = extract_sources(str(video), metadata)

        assert result.success is False
        assert "timeout" in result.error_message.lower()

    def test_run_invoked_with_timeout_kwarg(self):
        """ffmpeg invocation must pass a bounded timeout."""
        metadata = {
            "canvas_size": [1920, 1080],
            "fps": 30.0,
            "timestamp": 1.0,
            "sources": {
                "Microphone": {
                    "position": {"x": 0, "y": 0},
                    "has_video": False,
                    "has_audio": True,
                },
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            video = _make_video(temp_dir)

            with patch(
                "obsession.core.extractor.subprocess.run"
            ) as mock_run:
                mock_run.return_value = subprocess.CompletedProcess(
                    args=[], returncode=0, stdout="", stderr=""
                )

                extract_sources(str(video), metadata)

        assert mock_run.call_args_list, "ffmpeg was never invoked"
        for call in mock_run.call_args_list:
            assert call.kwargs.get("timeout"), "subprocess.run called without timeout"
