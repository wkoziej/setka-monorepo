# ABOUTME: Integration test for vendored YAML library
# ABOUTME: Tests loading and parsing of Cinemon preset files

"""Integration tests for YAML functionality in Blender addon."""

import sys
from pathlib import Path

import pytest

# Add blender_addon to path
addon_path = Path(__file__).parent.parent.parent / "blender_addon"
if str(addon_path) not in sys.path:
    sys.path.insert(0, str(addon_path))


class TestYAMLIntegration:
    """Test YAML loading and parsing integration."""

    def test_import_vendored_yaml(self):
        """Test that vendored yaml can be imported."""
        from vendor import yaml
        assert yaml is not None

    def test_load_preset_yaml(self):
        """Test loading a preset YAML file."""
        from vendor import yaml

        # Sample preset YAML matching new format
        preset_content = """
project:
  video_files: [Camera1.mp4, Camera2.mp4]
  main_audio: "main_audio.m4a"
  fps: 30
  resolution: {width: 1920, height: 1080}

layout:
  type: "random"
  config:
    seed: 42
    margin: 0.1
    overlap_allowed: false

strip_animations:
  Camera1:
    - type: "scale"
      trigger: "beat"
      intensity: 0.3
    - type: "shake"
      trigger: "energy_peaks"
      intensity: 2.0
      return_frames: 2
  
  Camera2:
    - type: "vintage_color"
      trigger: "one_time"
      sepia_amount: 0.4
      contrast_boost: 0.3

audio_analysis:
  file: "./analysis/main_audio_analysis.json"
"""

        # Parse YAML
        data = yaml.safe_load(preset_content)

        # Verify structure
        assert 'project' in data
        assert 'layout' in data
        assert 'strip_animations' in data
        assert 'audio_analysis' in data

        # Verify project settings
        assert data['project']['fps'] == 30
        assert len(data['project']['video_files']) == 2

        # Verify layout
        assert data['layout']['type'] == 'random'
        assert data['layout']['config']['seed'] == 42

        # Verify strip animations
        assert 'Camera1' in data['strip_animations']
        assert 'Camera2' in data['strip_animations']
        assert len(data['strip_animations']['Camera1']) == 2
        assert data['strip_animations']['Camera1'][0]['type'] == 'scale'

    def test_dump_preset_yaml(self):
        """Test dumping Python dict to YAML."""
        from vendor import yaml

        # Create preset data
        preset_data = {
            'project': {
                'video_files': ['test1.mp4', 'test2.mp4'],
                'fps': 60
            },
            'layout': {
                'type': 'grid',
                'config': {'rows': 2, 'cols': 2}
            },
            'strip_animations': {
                'test1': [
                    {'type': 'scale', 'trigger': 'beat', 'intensity': 0.5}
                ]
            }
        }

        # Dump to YAML
        yaml_output = yaml.dump(preset_data, default_flow_style=False)

        # Verify output contains expected content
        assert 'project:' in yaml_output
        assert 'video_files:' in yaml_output
        assert 'test1.mp4' in yaml_output
        assert 'fps: 60' in yaml_output

        # Parse it back
        parsed = yaml.safe_load(yaml_output)
        assert parsed == preset_data

    def test_yaml_unicode_support(self):
        """Test YAML handles Polish characters correctly."""
        from vendor import yaml

        # Polish filename
        data = {
            'project': {
                'main_audio': 'Przechwytywanie wejścia dźwięku.m4a'
            }
        }

        # Dump and load
        yaml_str = yaml.dump(data, default_flow_style=False, allow_unicode=True)
        loaded = yaml.safe_load(yaml_str)

        assert loaded['project']['main_audio'] == 'Przechwytywanie wejścia dźwięku.m4a'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
