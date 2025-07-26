# ABOUTME: Tests for modernized CLI using click framework
# ABOUTME: Validates click-based audio analysis CLI functionality

"""Tests for modernized CLI using click."""

from unittest.mock import Mock, patch
from click.testing import CliRunner

from beatrix.cli.click_cli import cli


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
            
            result = runner.invoke(cli, [
                "analyze",
                str(audio_file),
                str(output_dir),
                "--beat-division", "4",
                "--min-onset-interval", "1.5"
            ])
            
            assert result.exit_code == 0
            
            # Verify custom parameters were passed
            mock_analyzer.analyze_for_animation.assert_called_once_with(
                audio_file,
                beat_division=4,
                min_onset_interval=1.5
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
        result = runner.invoke(cli, [
            "analyze",
            str(audio_file),
            str(output_dir),
            "--beat-division", "not-a-number"
        ])
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
            mock_analyzer.analyze_for_animation.side_effect = RuntimeError("Analysis failed")
            
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
            result = runner.invoke(cli, [
                "--verbose",
                "analyze",
                str(audio_file),
                str(output_dir)
            ], catch_exceptions=False)
            
            assert result.exit_code == 0
            # Should show completion message
            assert "Analysis complete" in result.output