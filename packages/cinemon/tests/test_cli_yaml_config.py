"""Tests for CLI YAML configuration support after migration."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from blender.cli.blend_setup import load_yaml_config, main, parse_args


class TestCLIYAMLConfig:
    """Test cases for CLI YAML configuration support."""

    def test_parse_args_with_config_parameter(self):
        """Test that --config parameter is accepted by argparse."""
        with patch('sys.argv', ['cinemon-blend-setup', 'test_dir', '--config', 'test.yaml']):
            args = parse_args()
            assert args.config == Path('test.yaml')
            assert args.recording_dir == Path('test_dir')
            assert args.preset is None

    @patch("blender.cli.blend_setup.BlenderProjectManager")
    @patch("blender.cli.blend_setup.load_yaml_config")
    def test_main_with_yaml_config_file_success(self, mock_load_yaml, mock_manager_class):
        """Test successful main function with YAML config file."""
        # Setup mocks
        mock_yaml_config = MagicMock()
        mock_load_yaml.return_value = mock_yaml_config

        mock_manager = MagicMock()
        mock_project_path = Path("/test/recording/blender/project.blend")
        mock_manager.create_vse_project_with_config.return_value = mock_project_path
        mock_manager_class.return_value = mock_manager

        with patch('sys.argv', ['cinemon-blend-setup', 'test_dir', '--config', 'test.yaml']):
            result = main()

        assert result == 0
        mock_load_yaml.assert_called_once_with(Path('test.yaml'))
        mock_manager.create_vse_project_with_config.assert_called_once_with(
            Path('test_dir'),
            mock_yaml_config
        )

    def test_main_with_yaml_config_file_not_found(self):
        """Test main function with non-existent YAML config file."""
        with patch('sys.argv', ['cinemon-blend-setup', 'test_dir', '--config', 'nonexistent.yaml']):
            result = main()

        assert result == 1  # Should return error code, not raise SystemExit

    def test_main_with_yaml_config_validation_error(self):
        """Test main function with invalid YAML config."""
        # Create temporary invalid YAML config file
        yaml_content = """
project:
  video_files: []  # Invalid - empty video files
  fps: 30
audio_analysis:
  file: null
layout:
  type: random
  config: {}
animations: []
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()

            try:
                with patch('sys.argv', ['cinemon-blend-setup', 'test_dir', '--config', f.name]):
                    result = main()

                assert result == 1  # Should return error code for validation failure
            finally:
                Path(f.name).unlink()

    @patch("blender.cli.blend_setup.BlenderProjectManager")
    @patch("blender.cli.blend_setup.load_yaml_config")
    def test_main_with_yaml_config_integration(self, mock_load_yaml, mock_manager_class):
        """Test integration with valid YAML config file."""
        yaml_content = """
project:
  video_files: [camera1.mp4, camera2.mp4]
  main_audio: main_audio.m4a
  fps: 30
  resolution:
    width: 1920
    height: 1080
  beat_division: 8

audio_analysis:
  file: analysis/audio_analysis.json

layout:
  type: random
  config:
    overlap_allowed: false
    seed: 42
    margin: 0.05

animations:
  - type: scale
    trigger: bass
    target_strips: [camera1]
    intensity: 0.3
    duration_frames: 2
"""

        # Setup mocks
        mock_yaml_config = MagicMock()
        mock_load_yaml.return_value = mock_yaml_config

        mock_manager = MagicMock()
        mock_project_path = Path("/test/recording/blender/project.blend")
        mock_manager.create_vse_project_with_config.return_value = mock_project_path
        mock_manager_class.return_value = mock_manager

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()

            try:
                with patch('sys.argv', ['cinemon-blend-setup', 'test_dir', '--config', f.name]):
                    result = main()

                assert result == 0
                mock_load_yaml.assert_called_once_with(Path(f.name))
                mock_manager.create_vse_project_with_config.assert_called_once()
            finally:
                Path(f.name).unlink()

    def test_yaml_config_with_relative_paths(self):
        """Test YAML config handling with relative paths."""
        # This tests the path resolution in load_yaml_config
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml_content = """
project:
  video_files: [video1.mp4]
  fps: 30
audio_analysis:
  file: null
layout:
  type: random
  config: {}
animations: []
"""
            f.write(yaml_content)
            f.flush()

            try:
                # Test that load_yaml_config can handle Path objects
                config_path = Path(f.name)
                config = load_yaml_config(config_path)

                assert config is not None
                # The function should not raise exceptions for valid files
            finally:
                Path(f.name).unlink()


class TestCLIYAMLConfigErrorHandling:
    """Test error handling in CLI YAML configuration."""

    @patch("blender.cli.blend_setup.BlenderProjectManager")
    def test_yaml_config_file_permission_error(self, mock_manager_class):
        """Test handling of file permission errors."""
        with patch('sys.argv', ['cinemon-blend-setup', 'test_dir', '--config', '/root/no_permission.yaml']):
            # This should handle FileNotFoundError or PermissionError gracefully
            result = main()
            assert result == 1

    def test_yaml_config_invalid_syntax(self):
        """Test handling of invalid YAML syntax."""
        yaml_content = "invalid: yaml: syntax: [unclosed"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()

            try:
                with patch('sys.argv', ['cinemon-blend-setup', 'test_dir', '--config', f.name]):
                    result = main()

                assert result == 1  # Should handle YAML syntax errors
            finally:
                Path(f.name).unlink()

    def test_yaml_config_missing_required_fields(self):
        """Test handling of YAML with missing required fields."""
        yaml_content = """
# Missing project section
audio_analysis:
  file: null
layout:
  type: random
animations: []
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()

            try:
                with patch('sys.argv', ['cinemon-blend-setup', 'test_dir', '--config', f.name]):
                    result = main()

                assert result == 1  # Should handle missing required fields
            finally:
                Path(f.name).unlink()


class TestLoadYAMLConfig:
    """Test load_yaml_config function directly."""

    def test_load_yaml_config_success(self):
        """Test successful YAML config loading."""
        yaml_content = """
project:
  video_files: [video1.mp4]
  fps: 30
  resolution:
    width: 1920
    height: 1080
audio_analysis:
  file: null
layout:
  type: random
  config: {}
animations: []
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()

            try:
                config = load_yaml_config(Path(f.name))

                assert config is not None
                assert hasattr(config, 'project')
                assert hasattr(config, 'layout')
                assert hasattr(config, 'animations')
            finally:
                Path(f.name).unlink()

    def test_load_yaml_config_file_not_found(self):
        """Test YAML config loading with missing file."""
        with pytest.raises(FileNotFoundError):
            load_yaml_config(Path("nonexistent.yaml"))

    def test_load_yaml_config_validation_error(self):
        """Test YAML config loading with validation error."""
        yaml_content = "invalid_yaml_structure: yes"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()

            try:
                with pytest.raises(ValueError):
                    load_yaml_config(Path(f.name))
            finally:
                Path(f.name).unlink()
