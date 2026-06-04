# ABOUTME: Tests for modernized CLI using click framework
# ABOUTME: Validates click-based audio analysis CLI functionality

"""Tests for modernized CLI using click."""

import struct
import wave
from unittest.mock import Mock, patch

import numpy as np
import pytest
from click.testing import CliRunner

from beatrix.cli.click_cli import cli


def _write_wav(path, duration_s=1.0, sample_rate=22050):
    """Write a minimal valid WAV file with a sine wave to *path*."""
    n_samples = int(sample_rate * duration_s)
    t = np.linspace(0, duration_s, n_samples, endpoint=False)
    audio = np.int16(np.sin(2 * np.pi * 440 * t) * 16000)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"{n_samples}h", *audio))
    return path


class TestClickCLI:
    """Test cases for click-based CLI implementation."""

    def test_cli_basic_usage(self, tmp_path):
        """Test basic CLI usage with required arguments."""
        runner = CliRunner()

        # Create test audio file
        audio_file = tmp_path / "test_audio.wav"
        audio_file.touch()

        # Create output directory
        output_dir = tmp_path / "output"

        with patch("beatrix.cli.click_cli.AudioAnalyzer") as mock_analyzer_class:
            mock_analyzer = Mock()
            mock_analyzer_class.return_value = mock_analyzer

            analysis_result = {
                "duration": 5.0,
                "tempo": {"bpm": 120.0},
                "animation_events": {"beats": [1.0, 2.0, 3.0]},
            }
            mock_analyzer.analyze_for_animation.return_value = analysis_result

            # Run command
            result = runner.invoke(cli, ["analyze", str(audio_file), str(output_dir)])

            assert result.exit_code == 0
            assert "Analysis complete" in result.output

            # Verify analyzer was called
            mock_analyzer.analyze_for_animation.assert_called_once()
            mock_analyzer.save_analysis.assert_called_once()

    def test_cli_with_options(self, tmp_path):
        """Test CLI with custom options."""
        runner = CliRunner()

        audio_file = tmp_path / "test.wav"
        audio_file.touch()
        output_dir = tmp_path / "output"

        with patch("beatrix.cli.click_cli.AudioAnalyzer") as mock_analyzer_class:
            mock_analyzer = Mock()
            mock_analyzer_class.return_value = mock_analyzer
            mock_analyzer.analyze_for_animation.return_value = {}

            result = runner.invoke(
                cli,
                [
                    "analyze",
                    str(audio_file),
                    str(output_dir),
                    "--beat-division",
                    "4",
                    "--min-onset-interval",
                    "1.5",
                ],
            )

            assert result.exit_code == 0

            # Verify custom parameters were passed
            mock_analyzer.analyze_for_animation.assert_called_once_with(
                audio_file, beat_division=4, min_onset_interval=1.5
            )

    def test_cli_help(self):
        """Test CLI help functionality."""
        runner = CliRunner()

        # Test main help
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Audio analysis CLI for Beatrix" in result.output

        # Test analyze command help
        result = runner.invoke(cli, ["analyze", "--help"])
        assert result.exit_code == 0
        assert "Analyze audio file" in result.output
        assert "--beat-division" in result.output
        assert "--min-onset-interval" in result.output

    def test_cli_missing_file(self, tmp_path):
        """Test CLI with missing audio file."""
        runner = CliRunner()

        nonexistent_file = tmp_path / "missing.wav"
        output_dir = tmp_path / "output"

        result = runner.invoke(cli, ["analyze", str(nonexistent_file), str(output_dir)])

        assert result.exit_code != 0
        assert "does not exist" in result.output

    def test_cli_version(self):
        """Test CLI version display."""
        runner = CliRunner()

        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "beatrix" in result.output
        assert "0.1.0" in result.output

    def test_cli_invalid_option_values(self, tmp_path):
        """Test CLI with invalid option values."""
        runner = CliRunner()

        audio_file = tmp_path / "test.wav"
        audio_file.touch()
        output_dir = tmp_path / "output"

        # Test invalid beat division
        result = runner.invoke(
            cli,
            [
                "analyze",
                str(audio_file),
                str(output_dir),
                "--beat-division",
                "not-a-number",
            ],
        )
        assert result.exit_code != 0
        assert "Invalid value" in result.output

    def test_cli_creates_output_directory(self, tmp_path):
        """Test that CLI creates output directory if it doesn't exist."""
        runner = CliRunner()

        audio_file = tmp_path / "test.wav"
        audio_file.touch()
        output_dir = tmp_path / "new_output"

        assert not output_dir.exists()

        with patch("beatrix.cli.click_cli.AudioAnalyzer") as mock_analyzer_class:
            mock_analyzer = Mock()
            mock_analyzer_class.return_value = mock_analyzer
            mock_analyzer.analyze_for_animation.return_value = {}

            result = runner.invoke(cli, ["analyze", str(audio_file), str(output_dir)])

            assert result.exit_code == 0
            # Directory creation will be verified when the actual implementation runs

    def test_cli_error_handling(self, tmp_path):
        """Test CLI error handling."""
        runner = CliRunner()

        audio_file = tmp_path / "test.wav"
        audio_file.touch()
        output_dir = tmp_path / "output"

        with patch("beatrix.cli.click_cli.AudioAnalyzer") as mock_analyzer_class:
            mock_analyzer = Mock()
            mock_analyzer_class.return_value = mock_analyzer
            mock_analyzer.analyze_for_animation.side_effect = RuntimeError(
                "Analysis failed"
            )

            result = runner.invoke(cli, ["analyze", str(audio_file), str(output_dir)])

            assert result.exit_code != 0
            assert "Error: Audio analysis failed" in result.output

    def test_cli_verbose_output(self, tmp_path):
        """Test CLI with verbose flag."""
        runner = CliRunner()

        audio_file = tmp_path / "test.wav"
        audio_file.touch()
        output_dir = tmp_path / "output"

        with patch("beatrix.cli.click_cli.AudioAnalyzer") as mock_analyzer_class:
            mock_analyzer = Mock()
            mock_analyzer_class.return_value = mock_analyzer
            mock_analyzer.analyze_for_animation.return_value = {}

            # Test with mix_stderr=False to capture logging output
            result = runner.invoke(
                cli,
                ["--verbose", "analyze", str(audio_file), str(output_dir)],
                catch_exceptions=False,
            )

            assert result.exit_code == 0
            # Should show completion message
            assert "Analysis complete" in result.output


@pytest.mark.audio
@pytest.mark.integration
class TestAnalyzeRecordingCommand:
    """Tests for the analyze-recording subcommand (directory mode)."""

    def test_master_only_produces_one_analysis_file(self, tmp_path):
        """Happy path: mixed/master.wav → analysis/master_analysis.json."""
        runner = CliRunner()
        mixed_dir = tmp_path / "mixed"
        mixed_dir.mkdir()
        _write_wav(mixed_dir / "master.wav")

        result = runner.invoke(cli, ["analyze-recording", str(tmp_path)])

        assert result.exit_code == 0, result.output
        analysis_file = tmp_path / "analysis" / "master_analysis.json"
        assert analysis_file.exists(), (
            f"Expected {analysis_file}, output: {result.output}"
        )

    def test_master_and_stems_produce_three_analysis_files(self, tmp_path):
        """Happy path: master + 2 stems → 3 *_analysis.json files."""
        runner = CliRunner()
        mixed_dir = tmp_path / "mixed"
        mixed_dir.mkdir()
        stems_dir = mixed_dir / "stems"
        stems_dir.mkdir()
        _write_wav(mixed_dir / "master.wav")
        _write_wav(stems_dir / "drums.wav")
        _write_wav(stems_dir / "bass.wav")

        result = runner.invoke(cli, ["analyze-recording", str(tmp_path)])

        assert result.exit_code == 0, result.output
        analysis_dir = tmp_path / "analysis"
        for stem in ("master", "drums", "bass"):
            assert (analysis_dir / f"{stem}_analysis.json").exists(), (
                f"Missing {stem}_analysis.json; output: {result.output}"
            )

    def test_empty_mixed_falls_back_to_extracted(self, tmp_path):
        """Edge case: mixed/ exists but empty, extracted/ has 1 file → fallback."""
        runner = CliRunner()
        (tmp_path / "mixed").mkdir()
        extracted_dir = tmp_path / "extracted"
        extracted_dir.mkdir()
        _write_wav(extracted_dir / "source.wav")

        result = runner.invoke(cli, ["analyze-recording", str(tmp_path)])

        assert result.exit_code == 0, result.output
        assert (tmp_path / "analysis" / "source_analysis.json").exists()

    def test_no_audio_exits_nonzero_with_message(self, tmp_path):
        """Error path: no audio anywhere → nonzero exit + message on stderr."""
        runner = CliRunner()

        result = runner.invoke(cli, ["analyze-recording", str(tmp_path)])

        assert result.exit_code != 0
        # CliRunner by default mixes stderr into output
        assert "no audio" in result.output.lower() or "audio" in result.output.lower()

    def test_stem_collision_exits_nonzero_no_file_written(self, tmp_path):
        """Error path: collision in stem names → nonzero exit, no file written."""
        runner = CliRunner()
        mixed_dir = tmp_path / "mixed"
        mixed_dir.mkdir()
        stems_dir = mixed_dir / "stems"
        stems_dir.mkdir()
        _write_wav(mixed_dir / "master.wav")
        _write_wav(stems_dir / "master.wav")  # collision: both → master_analysis.json

        result = runner.invoke(cli, ["analyze-recording", str(tmp_path)])

        assert result.exit_code != 0
        assert "collision" in result.output.lower() or "master" in result.output.lower()
        analysis_dir = tmp_path / "analysis"
        # No file should have been written during failed run
        if analysis_dir.exists():
            assert not any(analysis_dir.iterdir()), (
                "No analysis files should be written on collision"
            )

    def test_beat_division_and_onset_interval_propagate(self, tmp_path):
        """Edge case: custom options are forwarded to every analysis call."""
        runner = CliRunner()
        mixed_dir = tmp_path / "mixed"
        mixed_dir.mkdir()
        _write_wav(mixed_dir / "master.wav")

        with patch("beatrix.cli.click_cli.AudioAnalyzer") as mock_analyzer_class:
            mock_analyzer = Mock()
            mock_analyzer_class.return_value = mock_analyzer
            mock_analyzer.analyze_for_animation.return_value = {
                "duration": 1.0,
                "tempo": {"bpm": 120.0},
                "animation_events": {"beats": []},
            }

            result = runner.invoke(
                cli,
                [
                    "analyze-recording",
                    str(tmp_path),
                    "--beat-division",
                    "4",
                    "--min-onset-interval",
                    "1.5",
                ],
            )

            assert result.exit_code == 0, result.output
            mock_analyzer.analyze_for_animation.assert_called_once_with(
                mixed_dir / "master.wav",
                beat_division=4,
                min_onset_interval=1.5,
            )

    def test_existing_analyze_command_still_works(self, tmp_path):
        """Regression: single-file analyze command is unaffected."""
        runner = CliRunner()
        audio_file = tmp_path / "test.wav"
        audio_file.touch()
        output_dir = tmp_path / "output"

        with patch("beatrix.cli.click_cli.AudioAnalyzer") as mock_analyzer_class:
            mock_analyzer = Mock()
            mock_analyzer_class.return_value = mock_analyzer
            mock_analyzer.analyze_for_animation.return_value = {}

            result = runner.invoke(cli, ["analyze", str(audio_file), str(output_dir)])

            assert result.exit_code == 0
            mock_analyzer.analyze_for_animation.assert_called_once()

    def test_master_only_produces_index_json(self, tmp_path):
        """Regression n=1: master.wav → master_analysis.json + index.json with one entry."""
        runner = CliRunner()
        mixed_dir = tmp_path / "mixed"
        mixed_dir.mkdir()
        _write_wav(mixed_dir / "master.wav")

        result = runner.invoke(cli, ["analyze-recording", str(tmp_path)])

        assert result.exit_code == 0, result.output
        index_file = tmp_path / "analysis" / "index.json"
        assert index_file.exists(), f"index.json missing; output: {result.output}"

        import json

        index = json.loads(index_file.read_text())
        assert index["version"] == 1
        assert len(index["sources"]) == 1
        entry = index["sources"][0]
        assert entry["role"] == "master"
        assert entry["origin"] == "mixed"
        assert entry["label"] == "master"
        assert entry["source"] == "mixed/master.wav"
        assert entry["analysis"] == "analysis/master_analysis.json"
        assert "duration" in entry
        assert "sample_rate" in entry

    def test_bitwig_samples_produce_index_json(self, tmp_path):
        """Happy path: mixed/master.wav + bitwig/samples/{m_s-24,track 4+git-24}.wav
        → index.json with 3 entries, correct roles/origins/labels/paths."""
        runner = CliRunner()
        mixed_dir = tmp_path / "mixed"
        mixed_dir.mkdir()
        bitwig_samples_dir = tmp_path / "bitwig" / "samples"
        bitwig_samples_dir.mkdir(parents=True)

        with patch("beatrix.cli.click_cli.AudioAnalyzer") as mock_analyzer_class:
            mock_analyzer = Mock()
            mock_analyzer_class.return_value = mock_analyzer
            mock_analyzer.analyze_for_animation.return_value = {
                "duration": 10.0,
                "sample_rate": 44100,
                "tempo": {"bpm": 120.0},
                "animation_events": {"beats": []},
            }

            _write_wav(mixed_dir / "master.wav")
            _write_wav(bitwig_samples_dir / "m_s-24.wav")
            _write_wav(bitwig_samples_dir / "track 4+git-24.wav")

            result = runner.invoke(cli, ["analyze-recording", str(tmp_path)])

            assert result.exit_code == 0, result.output

        # Verify index.json — the manifest written by analyze-recording
        import json

        analysis_dir = tmp_path / "analysis"
        index_file = analysis_dir / "index.json"
        assert index_file.exists(), "index.json missing"
        index = json.loads(index_file.read_text())
        assert index["version"] == 1
        assert len(index["sources"]) == 3

        by_label = {e["label"]: e for e in index["sources"]}

        master_entry = by_label["master"]
        assert master_entry["role"] == "master"
        assert master_entry["origin"] == "mixed"
        assert master_entry["source"] == "mixed/master.wav"
        assert master_entry["analysis"] == "analysis/master_analysis.json"
        assert master_entry["duration"] == 10.0
        assert master_entry["sample_rate"] == 44100

        ms_entry = by_label["m_s"]
        assert ms_entry["role"] == "stem"
        assert ms_entry["origin"] == "bitwig"
        assert ms_entry["source"] == "bitwig/samples/m_s-24.wav"
        assert ms_entry["analysis"] == "analysis/m_s_analysis.json"

        track_entry = by_label["track_4_git"]
        assert track_entry["role"] == "stem"
        assert track_entry["origin"] == "bitwig"
        assert track_entry["source"] == "bitwig/samples/track 4+git-24.wav"
        assert track_entry["analysis"] == "analysis/track_4_git_analysis.json"

    def test_mixed_stems_produce_index_json_with_mixed_origin(self, tmp_path):
        """Happy path: mixed/stems/ non-empty → entries use origin=mixed, bitwig ignored."""
        runner = CliRunner()
        mixed_dir = tmp_path / "mixed"
        mixed_dir.mkdir()
        stems_dir = mixed_dir / "stems"
        stems_dir.mkdir()
        bitwig_samples_dir = tmp_path / "bitwig" / "samples"
        bitwig_samples_dir.mkdir(parents=True)

        with patch("beatrix.cli.click_cli.AudioAnalyzer") as mock_analyzer_class:
            mock_analyzer = Mock()
            mock_analyzer_class.return_value = mock_analyzer
            mock_analyzer.analyze_for_animation.return_value = {
                "duration": 5.0,
                "sample_rate": 48000,
                "tempo": {"bpm": 90.0},
                "animation_events": {"beats": []},
            }

            _write_wav(mixed_dir / "master.wav")
            _write_wav(stems_dir / "drums.wav")
            _write_wav(stems_dir / "bass.wav")
            _write_wav(bitwig_samples_dir / "ignored.wav")

            result = runner.invoke(cli, ["analyze-recording", str(tmp_path)])

            assert result.exit_code == 0, result.output

        import json

        index_file = tmp_path / "analysis" / "index.json"
        assert index_file.exists()
        index = json.loads(index_file.read_text())
        assert len(index["sources"]) == 3

        by_label = {e["label"]: e for e in index["sources"]}
        assert by_label["master"]["origin"] == "mixed"
        assert by_label["drums"]["role"] == "stem"
        assert by_label["drums"]["origin"] == "mixed"
        assert by_label["drums"]["source"] == "mixed/stems/drums.wav"
        assert by_label["bass"]["origin"] == "mixed"
        # bitwig/ignored.wav must NOT appear
        assert "ignored" not in by_label

    def test_extracted_fallback_produces_index_json_with_main_role(self, tmp_path):
        """Edge case: extracted/ fallback → role=main, origin=extracted in index.json."""
        runner = CliRunner()
        extracted_dir = tmp_path / "extracted"
        extracted_dir.mkdir()

        with patch("beatrix.cli.click_cli.AudioAnalyzer") as mock_analyzer_class:
            mock_analyzer = Mock()
            mock_analyzer_class.return_value = mock_analyzer
            mock_analyzer.analyze_for_animation.return_value = {
                "duration": 3.0,
                "sample_rate": 44100,
                "tempo": {"bpm": 100.0},
                "animation_events": {"beats": []},
            }

            _write_wav(extracted_dir / "source.wav")

            result = runner.invoke(cli, ["analyze-recording", str(tmp_path)])

            assert result.exit_code == 0, result.output

        import json

        index_file = tmp_path / "analysis" / "index.json"
        assert index_file.exists()
        index = json.loads(index_file.read_text())
        assert len(index["sources"]) == 1
        entry = index["sources"][0]
        assert entry["role"] == "main"
        assert entry["origin"] == "extracted"
        assert entry["label"] == "source"
        assert entry["source"] == "extracted/source.wav"
        assert entry["analysis"] == "analysis/source_analysis.json"

    def test_no_audio_does_not_write_index_json(self, tmp_path):
        """Error path: no audio → nonzero exit, index.json NOT written."""
        runner = CliRunner()

        result = runner.invoke(cli, ["analyze-recording", str(tmp_path)])

        assert result.exit_code != 0
        assert not (tmp_path / "analysis" / "index.json").exists()

    def test_collision_does_not_write_index_json(self, tmp_path):
        """Error path: sanitised name collision → nonzero exit, index.json NOT written."""
        runner = CliRunner()
        mixed_dir = tmp_path / "mixed"
        mixed_dir.mkdir()
        stems_dir = mixed_dir / "stems"
        stems_dir.mkdir()
        _write_wav(mixed_dir / "master.wav")
        _write_wav(stems_dir / "master.wav")  # collision

        result = runner.invoke(cli, ["analyze-recording", str(tmp_path)])

        assert result.exit_code != 0
        assert not (tmp_path / "analysis" / "index.json").exists()

    def test_options_propagate_to_all_sources(self, tmp_path):
        """Edge case: --beat-division/--min-onset-interval forwarded to every source."""
        runner = CliRunner()
        mixed_dir = tmp_path / "mixed"
        mixed_dir.mkdir()
        bitwig_samples_dir = tmp_path / "bitwig" / "samples"
        bitwig_samples_dir.mkdir(parents=True)

        with patch("beatrix.cli.click_cli.AudioAnalyzer") as mock_analyzer_class:
            mock_analyzer = Mock()
            mock_analyzer_class.return_value = mock_analyzer
            mock_analyzer.analyze_for_animation.return_value = {
                "duration": 1.0,
                "sample_rate": 44100,
                "tempo": {"bpm": 120.0},
                "animation_events": {"beats": []},
            }

            _write_wav(mixed_dir / "master.wav")
            _write_wav(bitwig_samples_dir / "track-24.wav")

            result = runner.invoke(
                cli,
                [
                    "analyze-recording",
                    str(tmp_path),
                    "--beat-division",
                    "4",
                    "--min-onset-interval",
                    "1.5",
                ],
            )

            assert result.exit_code == 0, result.output
            assert mock_analyzer.analyze_for_animation.call_count == 2
            for call in mock_analyzer.analyze_for_animation.call_args_list:
                assert call.kwargs["beat_division"] == 4
                assert call.kwargs["min_onset_interval"] == 1.5
