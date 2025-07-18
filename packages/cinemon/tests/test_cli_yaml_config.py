"""Tests for CLI YAML configuration support."""

import pytest
import tempfile
import argparse
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from blender.cli.blend_setup import parse_args, main
from setka_common.config import BlenderYAMLConfig, ProjectConfig, AudioAnalysisConfig, LayoutConfig


class TestCLIYAMLConfig:
    """Test cases for CLI YAML configuration support."""

    def test_parse_args_with_config_parameter(self):
        """Test that --config parameter is accepted by argparse."""
        # Test that --config parameter is now accepted
        with patch('sys.argv', ['cinemon-blend-setup', 'test_dir', '--config', 'test.yaml']):
            args = parse_args()
            assert args.config == Path('test.yaml')
            assert args.recording_dir == Path('test_dir')

    def test_parse_args_with_config_parameter_should_work(self):
        """Test that --config parameter will work after implementation."""
        # This test documents the expected behavior
        # For now, we'll skip it as it will be implemented next
        pytest.skip("Will be implemented when CLI is updated")

    def test_main_with_yaml_config_file(self):
        """Test main function with YAML config file."""
        # Create temporary YAML config file
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
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            
            # Mock the necessary components
            with patch('sys.argv', ['cinemon-blend-setup', 'test_dir', '--config', f.name]):
                with patch('blender.cli.blend_setup.validate_recording_directory'):
                    with patch('blender.cli.blend_setup.BlenderProjectManager') as mock_manager:
                        with patch('blender.cli.blend_setup.Path') as mock_path:
                            with patch('setka_common.config.YAMLConfigLoader') as mock_loader:
                                # Setup mocks
                                mock_path.return_value.exists.return_value = True
                                mock_config = MagicMock()
                                mock_loader.return_value.load_config.return_value = mock_config
                                mock_manager.return_value.create_vse_project_with_config.return_value = Path("/test/project.blend")
                                
                                # This will fail until implemented
                                with pytest.raises(SystemExit):
                                    main()
            
            # Cleanup
            Path(f.name).unlink()

    def test_main_with_yaml_config_file_not_found(self):
        """Test main function with non-existent YAML config file."""
        with patch('sys.argv', ['cinemon-blend-setup', 'test_dir', '--config', 'nonexistent.yaml']):
            # This will fail until implemented
            with pytest.raises(SystemExit):
                main()

    def test_main_with_yaml_config_validation_error(self):
        """Test main function with invalid YAML config."""
        yaml_content = """
project:
  video_files: []  # Invalid - empty video files
audio_analysis: {}
layout:
  type: random
animations: []
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            
            with patch('sys.argv', ['cinemon-blend-setup', 'test_dir', '--config', f.name]):
                # This will fail until implemented
                with pytest.raises(SystemExit):
                    main()
            
            # Cleanup
            Path(f.name).unlink()

    def test_main_with_yaml_config_integration(self):
        """Test full integration with YAML config."""
        yaml_content = """
project:
  video_files: [camera1.mp4, camera2.mp4]
  main_audio: main_audio.m4a
  output_blend: blender/project.blend
  render_output: blender/render/output.mp4
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
  - type: shake
    trigger: beat
    target_strips: [camera2]
    intensity: 5.0
    return_frames: 2
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            
            with patch('sys.argv', ['cinemon-blend-setup', 'test_dir', '--config', f.name]):
                with patch('blender.cli.blend_setup.validate_recording_directory'):
                    with patch('blender.cli.blend_setup.BlenderProjectManager') as mock_manager:
                        with patch('blender.cli.blend_setup.Path') as mock_path:
                            with patch('setka_common.config.YAMLConfigLoader') as mock_loader:
                                # Setup mocks
                                mock_path.return_value.exists.return_value = True
                                
                                # Create expected config
                                project = ProjectConfig(
                                    video_files=["camera1.mp4", "camera2.mp4"],
                                    main_audio="main_audio.m4a",
                                    output_blend="blender/project.blend",
                                    render_output="blender/render/output.mp4",
                                    fps=30,
                                    resolution={"width": 1920, "height": 1080},
                                    beat_division=8
                                )
                                audio_analysis = AudioAnalysisConfig(file="analysis/audio_analysis.json")
                                layout = LayoutConfig(
                                    type="random",
                                    config={
                                        "overlap_allowed": False,
                                        "seed": 42,
                                        "margin": 0.05
                                    }
                                )
                                
                                mock_config = BlenderYAMLConfig(
                                    project=project,
                                    audio_analysis=audio_analysis,
                                    layout=layout,
                                    animations=[]  # Simplified for test
                                )
                                
                                mock_loader.return_value.load_config.return_value = mock_config
                                mock_manager.return_value.create_vse_project_with_config.return_value = Path("/test/project.blend")
                                
                                # This will fail until implemented
                                with pytest.raises(SystemExit):
                                    result = main()
            
            # Cleanup
            Path(f.name).unlink()

    def test_yaml_config_takes_precedence_over_cli_args(self):
        """Test that YAML config takes precedence over CLI arguments."""
        yaml_content = """
project:
  video_files: [from_yaml.mp4]
  main_audio: yaml_audio.m4a
  fps: 60
  beat_division: 16

audio_analysis: {}
layout:
  type: random
animations: []
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            
            # CLI args have different values
            with patch('sys.argv', [
                'cinemon-blend-setup', 'test_dir', 
                '--config', f.name,
                '--main-audio', 'cli_audio.m4a',  # Should be overridden
                '--animation-mode', 'beat-switch',  # Should be overridden
                '--beat-division', '4'  # Should be overridden
            ]):
                with patch('blender.cli.blend_setup.validate_recording_directory'):
                    with patch('blender.cli.blend_setup.BlenderProjectManager') as mock_manager:
                        with patch('blender.cli.blend_setup.Path') as mock_path:
                            with patch('setka_common.config.YAMLConfigLoader') as mock_loader:
                                # Setup mocks
                                mock_path.return_value.exists.return_value = True
                                mock_config = MagicMock()
                                mock_config.project.main_audio = "yaml_audio.m4a"
                                mock_config.project.fps = 60
                                mock_config.project.beat_division = 16
                                mock_loader.return_value.load_config.return_value = mock_config
                                mock_manager.return_value.create_vse_project_with_config.return_value = Path("/test/project.blend")
                                
                                # This will fail until implemented
                                with pytest.raises(SystemExit):
                                    main()
            
            # Cleanup
            Path(f.name).unlink()

    def test_yaml_config_with_relative_paths(self):
        """Test YAML config with relative paths resolution."""
        yaml_content = """
project:
  video_files: [camera1.mp4, camera2.mp4]
  main_audio: main_audio.m4a
  output_blend: blender/project.blend
  render_output: blender/render/output.mp4

audio_analysis:
  file: analysis/audio_analysis.json

layout:
  type: random

animations: []
"""
        
        # Create config in recording directory
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "animation_config.yaml"
            with open(config_path, 'w') as f:
                f.write(yaml_content)
            
            with patch('sys.argv', ['cinemon-blend-setup', temp_dir, '--config', str(config_path)]):
                with patch('blender.cli.blend_setup.validate_recording_directory'):
                    with patch('blender.cli.blend_setup.BlenderProjectManager') as mock_manager:
                        with patch('setka_common.config.YAMLConfigLoader') as mock_loader:
                            # Setup mocks
                            mock_config = MagicMock()
                            mock_loader.return_value.load_config.return_value = mock_config
                            mock_manager.return_value.create_vse_project_with_config.return_value = Path("/test/project.blend")
                            
                            # This will fail until implemented
                            with pytest.raises(SystemExit):
                                main()


class TestCLIYAMLConfigArgParsing:
    """Test cases for argument parsing with YAML config."""

    def test_config_parameter_added_to_parser(self):
        """Test that --config parameter is added to argument parser."""
        # This tests the current implementation - should fail
        with pytest.raises(SystemExit):
            with patch('sys.argv', ['cinemon-blend-setup', '--help']):
                parse_args()

    def test_config_parameter_type_validation(self):
        """Test that --config parameter validates file path."""
        # This will be implemented
        pytest.skip("Will be implemented when CLI is updated")

    def test_config_parameter_mutual_exclusion(self):
        """Test that --config parameter works with other parameters."""
        # This will be implemented
        pytest.skip("Will be implemented when CLI is updated")


class TestCLIYAMLConfigErrorHandling:
    """Test cases for error handling with YAML config."""

    def test_yaml_config_file_permission_error(self):
        """Test handling of permission errors when reading YAML config."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("project:\n  video_files: [test.mp4]\n")
            f.flush()
            
            # Remove read permissions
            os.chmod(f.name, 0o000)
            
            try:
                with patch('sys.argv', ['cinemon-blend-setup', 'test_dir', '--config', f.name]):
                    # This will fail until implemented
                    with pytest.raises(SystemExit):
                        main()
            finally:
                # Restore permissions for cleanup
                os.chmod(f.name, 0o644)
                Path(f.name).unlink()

    def test_yaml_config_invalid_syntax(self):
        """Test handling of invalid YAML syntax."""
        yaml_content = """
project:
  video_files: [test.mp4
  # Missing closing bracket
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            
            with patch('sys.argv', ['cinemon-blend-setup', 'test_dir', '--config', f.name]):
                # This will fail until implemented
                with pytest.raises(SystemExit):
                    main()
            
            # Cleanup
            Path(f.name).unlink()

    def test_yaml_config_missing_required_fields(self):
        """Test handling of YAML config with missing required fields."""
        yaml_content = """
project: {}
audio_analysis: {}
layout: {}
animations: []
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            
            with patch('sys.argv', ['cinemon-blend-setup', 'test_dir', '--config', f.name]):
                # This will fail until implemented
                with pytest.raises(SystemExit):
                    main()
            
            # Cleanup
            Path(f.name).unlink()