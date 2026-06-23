"""
Coverage-focused tests for obsession.cli.extract helper functions and the
auto/verbose/pattern-filter branches of main() (Unit 5.3).
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from obsession.cli.extract import (
    apply_audio_pattern_filter,
    find_metadata_file,
    wait_for_file_ready,
    main,
    parse_args,
)
from obsession.core.extractor import ExtractionResult


class TestApplyAudioPatternFilter:
    def test_no_pattern_returns_metadata_unchanged(self):
        metadata = {"sources": {"RPI_Cam": {"has_audio": True}}}
        assert apply_audio_pattern_filter(metadata, "") is metadata

    def test_matching_source_audio_disabled(self):
        metadata = {
            "sources": {
                "RPI_Cam": {"has_audio": True, "has_video": True},
                "Mic": {"has_audio": True, "has_video": False},
            }
        }
        out = apply_audio_pattern_filter(metadata, "RPI.*")
        assert out["sources"]["RPI_Cam"]["has_audio"] is False
        assert out["sources"]["Mic"]["has_audio"] is True
        # Original metadata is not mutated.
        assert metadata["sources"]["RPI_Cam"]["has_audio"] is True

    def test_invalid_regex_returns_metadata_unchanged(self):
        metadata = {"sources": {"Cam": {"has_audio": True}}}
        out = apply_audio_pattern_filter(metadata, "(unclosed")
        assert out == metadata

    def test_matching_source_already_silent_no_change(self):
        metadata = {"sources": {"RPI_Cam": {"has_audio": False}}}
        out = apply_audio_pattern_filter(metadata, "RPI.*")
        assert out["sources"]["RPI_Cam"]["has_audio"] is False


class TestFindMetadataFile:
    def test_legacy_pattern_match(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            video = Path(temp_dir) / "clip.mp4"
            video.write_text("v")
            meta = Path(temp_dir) / "clip.json"
            meta.write_text("{}")
            found = find_metadata_file(video)
            assert found == meta

    def test_no_metadata_returns_none(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            video = Path(temp_dir) / "clip.mp4"
            video.write_text("v")
            assert find_metadata_file(video) is None

    def test_timestamp_heuristic_match(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            video = Path(temp_dir) / "clip.mp4"
            video.write_text("v")
            # A JSON with an unrelated name but a close mtime is picked up.
            other = Path(temp_dir) / "unrelated.json"
            other.write_text("{}")
            found = find_metadata_file(video)
            assert found == other


class TestWaitForFileReady:
    def test_missing_file_times_out(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "nope.mp4"
            with patch("obsession.cli.extract.time.sleep"):
                assert wait_for_file_ready(missing, max_wait=2) is False

    def test_stable_file_ready(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            video = Path(temp_dir) / "clip.mp4"
            video.write_bytes(b"x" * 4096)
            with patch("obsession.cli.extract.time.sleep"):
                assert wait_for_file_ready(video, max_wait=3) is True


class TestParseArgsDefaults:
    def test_skip_audio_pattern_default(self):
        args = parse_args(["v.mp4", "m.json"])
        assert args.skip_audio_pattern == "RPI.*"
        assert args.delay == 3

    def test_auto_flag(self):
        args = parse_args(["v.mp4", "--auto", "--delay", "0"])
        assert args.auto is True
        assert args.metadata_file is None
        assert args.delay == 0


class TestMainBranches:
    def test_verbose_and_pattern_filter_success(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            video = Path(temp_dir) / "clip.mp4"
            video.write_text("v")
            meta = Path(temp_dir) / "clip.json"
            meta.write_text(
                json.dumps(
                    {
                        "canvas_size": [1920, 1080],
                        "sources": {"RPI_Cam": {"has_audio": True}},
                    }
                )
            )

            ok = ExtractionResult(success=True, extracted_files=["a.mp4"])
            with patch(
                "obsession.cli.extract.extract_sources", return_value=ok
            ):
                with patch(
                    "sys.argv",
                    [
                        "extract.py",
                        str(video),
                        str(meta),
                        "--verbose",
                        "--skip-audio-pattern",
                        "RPI.*",
                    ],
                ):
                    assert main() == 0

    def test_auto_mode_autodetects_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            video = Path(temp_dir) / "clip.mp4"
            video.write_bytes(b"x" * 4096)
            meta = Path(temp_dir) / "clip.json"
            meta.write_text(json.dumps({"canvas_size": [1920, 1080], "sources": {}}))

            ok = ExtractionResult(success=True, extracted_files=[])
            with patch("obsession.cli.extract.time.sleep"):
                with patch(
                    "obsession.cli.extract.extract_sources", return_value=ok
                ):
                    with patch(
                        "sys.argv",
                        ["extract.py", str(video), "--auto", "--delay", "0"],
                    ):
                        assert main() == 0

    def test_auto_mode_no_metadata_found_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            video = Path(temp_dir) / "clip.mp4"
            video.write_bytes(b"x" * 4096)
            with patch("obsession.cli.extract.time.sleep"):
                with patch(
                    "sys.argv",
                    ["extract.py", str(video), "--auto", "--delay", "0"],
                ):
                    assert main() == 1

    def test_normal_mode_missing_metadata_arg_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            video = Path(temp_dir) / "clip.mp4"
            video.write_text("v")
            with patch("sys.argv", ["extract.py", str(video)]):
                assert main() == 1
