# ABOUTME: Tests for unified Animation API that handles both VSE and addon workflows
# ABOUTME: Tests preset application, layout management, and animation coordination

"""Tests for unified Animation API."""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, mock_open
import sys

# Add blender_addon to path for testing
addon_path = Path(__file__).parent.parent / "blender_addon"
if str(addon_path) not in sys.path:
    sys.path.insert(0, str(addon_path))

from unified_api import AnimationAPI, get_animation_api


@pytest.fixture
def mock_bpy():
    """Mock bpy module for testing."""
    mock_bpy_module = MagicMock()
    
    # Mock scene and sequence editor
    mock_scene = MagicMock()
    mock_sequence_editor = MagicMock()
    
    # Mock video strips
    mock_strip1 = MagicMock()
    mock_strip1.type = 'MOVIE'
    mock_strip1.name = 'Camera1'
    mock_strip1.channel = 1
    
    mock_strip2 = MagicMock()
    mock_strip2.type = 'MOVIE'
    mock_strip2.name = 'Camera2'  
    mock_strip2.channel = 2
    
    mock_sequence_editor.sequences = [mock_strip1, mock_strip2]
    mock_scene.sequence_editor = mock_sequence_editor
    mock_scene.frame_start = 1
    mock_scene.frame_end = 1000
    
    mock_bpy_module.context.scene = mock_scene
    
    # Patch the bpy import in unified_api module
    with patch.dict('sys.modules', {'bpy': mock_bpy_module}):
        yield mock_bpy_module


@pytest.fixture
def sample_preset_config():
    """Sample preset configuration for testing."""
    return {
        'layout': {
            'type': 'main-pip',
            'config': {
                'pip_scale': 0.25,
                'margin_percent': 0.08
            }
        },
        'strip_animations': {
            'Video_1': [
                {
                    'type': 'scale',
                    'trigger': 'beat',
                    'intensity': 0.2,
                    'duration_frames': 3
                }
            ],
            'Video_2': [
                {
                    'type': 'shake',
                    'trigger': 'energy_peaks',
                    'intensity': 0.8,
                    'return_frames': 2
                }
            ]
        }
    }


@pytest.fixture
def sample_audio_data():
    """Sample audio analysis data for testing."""
    return {
        'duration': 180.0,
        'tempo': {'bpm': 120.0},
        'animation_events': {
            'beats': [1.0, 1.5, 2.0, 2.5, 3.0],
            'energy_peaks': [1.2, 2.3, 3.1],
            'sections': [0.0, 60.0, 120.0, 180.0]
        }
    }


class TestAnimationAPI:
    """Test cases for AnimationAPI class."""
    
    def test_initialization(self, mock_bpy):
        """Test that AnimationAPI initializes correctly."""
        # Test basic initialization without mocking imports
        api = AnimationAPI()
        
        # Should have initialized without error
        assert api is not None
        assert hasattr(api, 'strip_context_manager')
        assert hasattr(api, 'apply_animation_to_strip')
    
    def test_apply_preset_with_config(self, mock_bpy, sample_preset_config, sample_audio_data):
        """Test applying preset with pre-loaded configuration."""
        with patch.object(AnimationAPI, 'apply_layout', return_value=True) as mock_layout, \
             patch.object(AnimationAPI, 'apply_animations', return_value=True) as mock_animations, \
             patch('unified_api.bpy', mock_bpy):
            
            api = AnimationAPI()
            
            result = api.apply_preset(
                recording_path="/test/recording",
                preset_config=sample_preset_config,
                audio_analysis_data=sample_audio_data
            )
            
            # Should succeed
            assert result['success'] is True
            assert result['layout_applied'] is True
            assert result['animations_applied'] is True
            assert result['strips_affected'] == 2
            assert len(result['errors']) == 0
            
            # Should call layout and animations methods
            mock_layout.assert_called_once()
            mock_animations.assert_called_once()
    
    def test_apply_preset_with_preset_name(self, mock_bpy):
        """Test applying preset by name."""
        mock_config = {
            'layout': {'type': 'random', 'config': {'seed': 42}},
            'strip_animations': {
                'Camera1': [{'type': 'scale', 'trigger': 'beat', 'intensity': 0.1}]
            }
        }
        
        with patch.object(AnimationAPI, '_load_preset_config', return_value=mock_config) as mock_load, \
             patch.object(AnimationAPI, 'apply_layout', return_value=True) as mock_layout, \
             patch.object(AnimationAPI, 'apply_animations', return_value=True) as mock_animations, \
             patch('unified_api.bpy', mock_bpy):
            
            api = AnimationAPI()
            
            result = api.apply_preset(
                recording_path="/test/recording",
                preset_name="multi-pip"
            )
            
            # Should load preset config
            mock_load.assert_called_once_with("multi-pip")
            
            # Should succeed
            assert result['success'] is True
    
    def test_apply_preset_missing_parameters(self, mock_bpy):
        """Test that missing preset name and config raises error."""
        api = AnimationAPI()
        
        result = api.apply_preset(recording_path="/test/recording")
        
        assert result['success'] is False
        assert "Either preset_name or preset_config must be provided" in result['errors']
    
    def test_apply_preset_no_strips(self, mock_bpy, sample_preset_config):
        """Test applying preset when no video strips found."""
        # Mock empty sequence editor
        mock_bpy.context.scene.sequence_editor.sequences = []
        
        with patch('unified_api.bpy', mock_bpy):
            api = AnimationAPI()
            
            result = api.apply_preset(
                recording_path="/test/recording",
                preset_config=sample_preset_config
            )
            
            assert result['success'] is False
            assert "No video strips found in project" in result['errors']
    
    def test_apply_layout_success(self, mock_bpy):
        """Test successful layout application."""
        layout_config = {
            'type': 'main-pip',
            'config': {'pip_scale': 0.25}
        }
        
        with patch('layout_applicators.apply_layout_to_strips', return_value=True) as mock_apply:
            api = AnimationAPI()
            video_strips = [MagicMock(), MagicMock()]
            
            result = api.apply_layout(video_strips, layout_config)
            
            assert result is True
            mock_apply.assert_called_once_with(layout_config)
    
    def test_apply_layout_failure(self, mock_bpy):
        """Test layout application failure."""
        layout_config = {'type': 'invalid', 'config': {}}
        
        with patch('layout_applicators.apply_layout_to_strips', return_value=False) as mock_apply:
            api = AnimationAPI()
            video_strips = [MagicMock(), MagicMock()]
            
            result = api.apply_layout(video_strips, layout_config)
            
            assert result is False
    
    def test_apply_animations_with_audio_data(self, mock_bpy, sample_audio_data):
        """Test applying animations with audio timing data."""
        animations_config = [
            {
                'type': 'scale',
                'trigger': 'beat',
                'intensity': 0.3,
                'target_strips': ['Camera1']
            }
        ]
        
        mock_apply_anim = Mock()
        api = AnimationAPI()
        api.apply_animation_to_strip = mock_apply_anim
        
        # Mock bpy.context.scene with frame attributes
        mock_bpy.context.scene.frame_start = 1
        mock_bpy.context.scene.frame_end = 1000
        
        with patch('unified_api.bpy', mock_bpy):
            # Set scene FPS for timing
            mock_bpy.context.scene.render.fps = 30
            
            # Create video strips with proper .name attributes
            strip1 = MagicMock()
            strip1.name = 'Camera1'
            strip2 = MagicMock()
            strip2.name = 'Camera2'
            video_strips = [strip1, strip2]
            
            result = api.apply_animations(video_strips, animations_config, sample_audio_data)
            
            # Should apply animations to targeted strip (Camera1 should match)
            assert mock_apply_anim.call_count >= 1
            assert result is True
    
    def test_convert_strip_animations_to_list(self, mock_bpy):
        """Test converting strip_animations format to flat list."""
        strip_animations = {
            'Camera1': [
                {'type': 'scale', 'trigger': 'beat', 'intensity': 0.2},
                {'type': 'shake', 'trigger': 'energy', 'intensity': 1.0}
            ],
            'Camera2': [
                {'type': 'rotation', 'trigger': 'beat', 'intensity': 0.5}
            ]
        }
        
        api = AnimationAPI()
        video_strips = [MagicMock(), MagicMock()]
        
        result = api._convert_strip_animations_to_list(strip_animations, video_strips)
        
        # Should create flat list with target_strips added
        assert len(result) == 3
        
        # Check first animation
        assert result[0]['type'] == 'scale'
        assert result[0]['target_strips'] == ['Camera1']
        
        # Check second animation 
        assert result[1]['type'] == 'shake'
        assert result[1]['target_strips'] == ['Camera1']
        
        # Check third animation
        assert result[2]['type'] == 'rotation'
        assert result[2]['target_strips'] == ['Camera2']
    
    def test_get_animations_for_strip(self, mock_bpy):
        """Test getting animations that target specific strip."""
        animations_config = [
            {'type': 'scale', 'trigger': 'beat', 'target_strips': ['Camera1']},
            {'type': 'shake', 'trigger': 'energy', 'target_strips': ['Camera2']},
            {'type': 'brightness', 'trigger': 'beat', 'target_strips': []},  # All strips
        ]
        
        api = AnimationAPI()
        
        # Get animations for Camera1
        camera1_animations = api._get_animations_for_strip('Camera1', animations_config)
        assert len(camera1_animations) == 2  # scale + brightness (empty target_strips)
        assert camera1_animations[0]['type'] == 'scale'
        assert camera1_animations[1]['type'] == 'brightness'
        
        # Get animations for Camera2
        camera2_animations = api._get_animations_for_strip('Camera2', animations_config)
        assert len(camera2_animations) == 2  # shake + brightness
        assert camera2_animations[0]['type'] == 'shake'
    
    def test_load_preset_config_builtin(self, mock_bpy):
        """Test loading built-in preset configuration."""
        mock_preset_content = """
layout:
  type: main-pip
  config:
    pip_scale: 0.25
strip_animations:
  Video_1:
    - type: scale
      trigger: beat
      intensity: 0.2
"""
        
        mock_config = {
            'layout': {'type': 'main-pip', 'config': {'pip_scale': 0.25}},
            'strip_animations': {
                'Video_1': [{'type': 'scale', 'trigger': 'beat', 'intensity': 0.2}]
            }
        }
        
        with patch('builtins.open', mock_open(read_data=mock_preset_content)), \
             patch('pathlib.Path.exists', return_value=True), \
             patch('yaml.safe_load', return_value=mock_config), \
             patch('unified_api.bpy', mock_bpy):
            
            api = AnimationAPI()
            config = api._load_preset_config('multi-pip')
            
            assert config is not None
            assert config['layout']['type'] == 'main-pip'
            # Video_1 should be mapped to Camera1 by _map_video_names_to_strips
            assert 'Camera1' in config['strip_animations']
    
    def test_load_preset_config_not_found(self, mock_bpy):
        """Test handling of missing preset file."""
        with patch('pathlib.Path.exists', return_value=False):
            api = AnimationAPI()
            config = api._load_preset_config('nonexistent')
            
            assert config is None
    
    def test_map_video_names_to_strips(self, mock_bpy):
        """Test mapping Video_X names to actual strip names."""
        config = {
            'strip_animations': {
                'Video_1': [{'type': 'scale', 'trigger': 'beat'}],
                'Video_2': [{'type': 'shake', 'trigger': 'energy'}],
                'CustomName': [{'type': 'rotation', 'trigger': 'beat'}]
            }
        }
        
        with patch('unified_api.bpy', mock_bpy):
            api = AnimationAPI()
            mapped_config = api._map_video_names_to_strips(config)
            
            # Video_X names should be mapped to actual strip names
            strip_animations = mapped_config['strip_animations']
            assert 'Camera1' in strip_animations  # Video_1 -> Camera1
            assert 'Camera2' in strip_animations  # Video_2 -> Camera2
            assert 'CustomName' in strip_animations  # Non-Video_X names kept as-is
            
            # Original Video_X keys should be replaced
            assert 'Video_1' not in strip_animations
            assert 'Video_2' not in strip_animations
    
    def test_events_based_animation_timing(self, mock_bpy, sample_audio_data):
        """Test that animations now use events-based timing."""
        api = AnimationAPI()
        
        # Mock animation applicator
        mock_apply = MagicMock()
        api.apply_animation_to_strip = mock_apply
        
        # Apply animations with audio data
        animations_config = [{'type': 'scale', 'trigger': 'beat', 'intensity': 0.3}]
        strip = MagicMock()
        strip.name = 'test_strip'
        
        mock_bpy.context.scene.render.fps = 30
        with patch('unified_api.bpy', mock_bpy):
            api.apply_animations([strip], animations_config, sample_audio_data)
        
        # Should have called with events-based approach
        mock_apply.assert_called_once()
        call_args = mock_apply.call_args
        assert call_args[0][2] == {'beats': [1.0, 1.5, 2.0, 2.5, 3.0], 'energy_peaks': [1.2, 2.3, 3.1], 'sections': [0.0, 60.0, 120.0, 180.0]}  # audio_events
        assert call_args[0][3] == 30  # fps


class TestGlobalAPI:
    """Test cases for global API functions."""
    
    def test_get_animation_api_singleton(self, mock_bpy):
        """Test that get_animation_api returns singleton instance."""
        # Clear the global instance first
        import unified_api
        unified_api._animation_api = None
        
        # Mock the initialization to avoid import errors
        with patch.object(AnimationAPI, '_initialize_components'):
            api1 = get_animation_api()
            api2 = get_animation_api()
            
            # Should return same instance
            assert api1 is api2
            assert isinstance(api1, AnimationAPI)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])