# ABOUTME: Tests for CLI --preset parameter integration
# ABOUTME: Tests CLI argument parsing, preset usage, and config generation in blend_setup.py

"""Tests for CLI --preset parameter functionality."""

import pytest
import argparse
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import sys

from blender.cli.blend_setup import parse_args, main


class TestCLIPresetParameter:
    """Test cases for CLI --preset parameter integration."""

    def test_parse_args_with_preset_parameter(self):
        """Test that --preset parameter is properly parsed."""
        test_args = ["recording_dir", "--preset", "vintage"]
        
        with patch.object(sys, 'argv', ["blend_setup.py"] + test_args):
            args = parse_args()
            
        assert hasattr(args, 'preset')
        assert args.preset == "vintage"
        assert args.recording_dir == Path("recording_dir")

    def test_parse_args_preset_parameter_optional(self):
        """Test that --preset parameter is optional."""
        test_args = ["recording_dir"]
        
        with patch.object(sys, 'argv', ["blend_setup.py"] + test_args):
            args = parse_args()
            
        assert hasattr(args, 'preset')
        assert args.preset is None

    def test_parse_args_preset_and_config_mutually_exclusive(self):
        """Test that --preset and --config are mutually exclusive."""
        test_args = ["recording_dir", "--preset", "vintage", "--config", "config.yaml"]
        
        with patch.object(sys, 'argv', ["blend_setup.py"] + test_args):
            with pytest.raises(SystemExit):  # argparse exits on mutually exclusive args
                parse_args()

    def test_parse_args_preset_with_other_parameters(self):
        """Test that --preset works with other CLI parameters."""
        test_args = [
            "recording_dir", 
            "--preset", "music-video", 
            "--verbose", 
            "--force",
            "--main-audio", "audio.m4a"
        ]
        
        with patch.object(sys, 'argv', ["blend_setup.py"] + test_args):
            args = parse_args()
            
        assert args.preset == "music-video"
        assert args.verbose is True
        assert args.force is True
        assert args.main_audio == "audio.m4a"

    @patch('blender.cli.blend_setup.CinemonConfigGenerator')
    @patch('blender.cli.blend_setup.BlenderProjectManager')
    @patch('blender.cli.blend_setup.validate_recording_directory')
    def test_main_with_preset_generates_config(self, mock_validate, mock_project_manager, mock_generator_class):
        """Test that main() uses CinemonConfigGenerator when --preset is specified."""
        # Setup mocks
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator
        mock_config_path = Path("/tmp/test_config.yaml")
        mock_generator.generate_preset.return_value = mock_config_path
        
        mock_manager = MagicMock()
        mock_project_manager.return_value = mock_manager
        
        test_args = ["recording_dir", "--preset", "vintage"]
        
        with patch.object(sys, 'argv', ["blend_setup.py"] + test_args):
            main()
        
        # Verify CinemonConfigGenerator was used
        mock_generator_class.assert_called_once()
        mock_generator.generate_preset.assert_called_once_with(
            Path("recording_dir"), 
            "vintage"
        )
        
        # Verify project manager was called with generated config
        mock_manager.create_vse_project_with_config.assert_called_once_with(
            Path("recording_dir"),
            mock_config_path,
            force=False
        )

    @patch('blender.cli.blend_setup.CinemonConfigGenerator')
    @patch('blender.cli.blend_setup.BlenderProjectManager')
    @patch('blender.cli.blend_setup.validate_recording_directory')
    def test_main_with_preset_and_overrides(self, mock_validate, mock_project_manager, mock_generator_class):
        """Test that main() passes parameter overrides to preset generation."""
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator
        mock_config_path = Path("/tmp/test_config.yaml")
        mock_generator.generate_preset.return_value = mock_config_path
        
        mock_manager = MagicMock()
        mock_project_manager.return_value = mock_manager
        
        test_args = [
            "recording_dir", 
            "--preset", "music-video",
            "--main-audio", "custom_audio.m4a",
            "--beat-division", "4"
        ]
        
        with patch.object(sys, 'argv', ["blend_setup.py"] + test_args):
            main()
        
        # Verify overrides were passed to generate_preset
        mock_generator.generate_preset.assert_called_once_with(
            Path("recording_dir"), 
            "music-video",
            main_audio="custom_audio.m4a",
            beat_division=4
        )

    @patch('blender.cli.blend_setup.CinemonConfigGenerator')
    @patch('blender.cli.blend_setup.BlenderProjectManager')
    @patch('blender.cli.blend_setup.validate_recording_directory')
    def test_main_without_preset_uses_legacy_mode(self, mock_validate, mock_project_manager, mock_generator_class):
        """Test that main() uses legacy mode when --preset is not specified."""
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator
        
        mock_manager = MagicMock()
        mock_project_manager.return_value = mock_manager
        
        test_args = ["recording_dir", "--animation-mode", "beat-switch"]
        
        with patch.object(sys, 'argv', ["blend_setup.py"] + test_args):
            main()
        
        # Verify CinemonConfigGenerator was NOT used for legacy mode
        mock_generator_class.assert_not_called()
        
        # Verify legacy create_vse_project was called
        mock_manager.create_vse_project.assert_called_once()

    @patch('blender.cli.blend_setup.CinemonConfigGenerator')
    @patch('blender.cli.blend_setup.BlenderProjectManager')
    @patch('blender.cli.blend_setup.validate_recording_directory')
    def test_main_with_config_file_skips_preset_generation(self, mock_validate, mock_project_manager, mock_generator_class):
        """Test that main() skips preset generation when --config is specified."""
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator
        
        mock_manager = MagicMock()
        mock_project_manager.return_value = mock_manager
        
        test_args = ["recording_dir", "--config", "existing_config.yaml"]
        
        with patch.object(sys, 'argv', ["blend_setup.py"] + test_args):
            main()
        
        # Verify CinemonConfigGenerator was NOT used
        mock_generator_class.assert_not_called()
        
        # Verify project manager was called with existing config
        mock_manager.create_vse_project_with_config.assert_called_once_with(
            Path("recording_dir"),
            Path("existing_config.yaml"),
            force=False
        )

    @patch('blender.cli.blend_setup.CinemonConfigGenerator')
    @patch('blender.cli.blend_setup.logging')
    def test_main_preset_generation_error_handling(self, mock_logging, mock_generator_class):
        """Test error handling when preset generation fails."""
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate_preset.side_effect = ValueError("Preset 'invalid' not found")
        
        test_args = ["recording_dir", "--preset", "invalid"]
        
        with patch.object(sys, 'argv', ["blend_setup.py"] + test_args):
            result = main()
        
        # Should return error code 1
        assert result == 1
        
        # Verify error was logged
        mock_logging.getLogger().error.assert_called()

    def test_preset_parameter_validation_valid_preset_names(self):
        """Test that valid preset names are accepted."""
        valid_presets = ["vintage", "music-video", "minimal", "beat-switch"]
        
        for preset in valid_presets:
            test_args = ["recording_dir", "--preset", preset]
            
            with patch.object(sys, 'argv', ["blend_setup.py"] + test_args):
                args = parse_args()
                assert args.preset == preset

    @patch('blender.cli.blend_setup.CinemonConfigGenerator')
    @patch('blender.cli.blend_setup.BlenderProjectManager')
    @patch('blender.cli.blend_setup.validate_recording_directory')
    def test_main_preset_with_force_flag(self, mock_validate, mock_project_manager, mock_generator_class):
        """Test that --force flag is properly passed through with preset mode."""
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator
        mock_config_path = Path("/tmp/test_config.yaml")
        mock_generator.generate_preset.return_value = mock_config_path
        
        mock_manager = MagicMock()
        mock_project_manager.return_value = mock_manager
        
        test_args = ["recording_dir", "--preset", "vintage", "--force"]
        
        with patch.object(sys, 'argv', ["blend_setup.py"] + test_args):
            main()
        
        # Verify force flag was passed to project manager
        mock_manager.create_vse_project_with_config.assert_called_once_with(
            Path("recording_dir"),
            mock_config_path,
            force=True
        )

    @patch('blender.cli.blend_setup.CinemonConfigGenerator')
    @patch('blender.cli.blend_setup.BlenderProjectManager')
    @patch('blender.cli.blend_setup.validate_recording_directory')
    @patch('blender.cli.blend_setup.logging')
    def test_main_preset_mode_logging(self, mock_logging, mock_validate, mock_project_manager, mock_generator_class):
        """Test that preset mode produces appropriate log messages."""
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator
        mock_config_path = Path("/tmp/test_config.yaml")
        mock_generator.generate_preset.return_value = mock_config_path
        
        mock_manager = MagicMock()
        mock_project_manager.return_value = mock_manager
        
        test_args = ["recording_dir", "--preset", "vintage"]
        
        with patch.object(sys, 'argv', ["blend_setup.py"] + test_args):
            main()
        
        # Verify appropriate logging occurred
        mock_logging.info.assert_any_call("Generating configuration from preset: vintage")
        mock_logging.info.assert_any_call(f"Generated configuration: {mock_config_path}")

    def test_help_text_includes_preset_parameter(self, capsys):
        """Test that help text includes --preset parameter documentation."""
        test_args = ["--help"]
        
        with patch.object(sys, 'argv', ["blend_setup.py"] + test_args):
            with pytest.raises(SystemExit):  # --help causes SystemExit
                parse_args()
        
        # Check that help text was printed and includes preset info
        captured = capsys.readouterr()
        help_text = captured.out
        assert "--preset" in help_text
        assert "preset" in help_text.lower()

    @patch('blender.cli.blend_setup.CinemonConfigGenerator')
    def test_preset_parameter_integration_with_validation(self, mock_generator_class):
        """Test that preset parameter integrates properly with existing validation."""
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate_preset.side_effect = FileNotFoundError("Recording directory not found")
        
        test_args = ["nonexistent_dir", "--preset", "vintage"]
        
        with patch.object(sys, 'argv', ["blend_setup.py"] + test_args):
            result = main()
        
        # Should return error code 1
        assert result == 1
        
        # Verify validation still occurs even in preset mode
        mock_generator.generate_preset.assert_called_once()