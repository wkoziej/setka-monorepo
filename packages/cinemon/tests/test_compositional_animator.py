"""Tests for CompositionalAnimator implementation."""

import pytest
import os
from unittest.mock import Mock, patch
from blender.vse.animators.compositional_animator import CompositionalAnimator
from blender.vse.layouts import RandomLayout
from blender.vse.animations import ScaleAnimation, ShakeAnimation


class TestCompositionalAnimator:
    """Test suite for CompositionalAnimator."""
    
    @pytest.fixture
    def mock_video_strips(self):
        """Create mock video strips with transform property."""
        strips = []
        for i in range(3):
            strip = Mock()
            strip.name = f"strip_{i}"
            strip.transform = Mock()
            strip.transform.offset_x = 0
            strip.transform.offset_y = 0
            strip.transform.scale_x = 1.0
            strip.transform.scale_y = 1.0
            strip.transform.rotation = 0.0
            strips.append(strip)
        return strips
    
    @pytest.fixture
    def mock_audio_analysis(self):
        """Create mock audio analysis data."""
        return {
            "duration": 10.0,
            "tempo": {"bpm": 120.0},
            "animation_events": {
                "beats": [1.0, 2.0, 3.0, 4.0],
                "energy_peaks": [1.5, 2.5, 3.5],
                "sections": [
                    {"start": 0.0, "end": 5.0, "label": "intro"},
                    {"start": 5.0, "end": 10.0, "label": "main"}
                ]
            }
        }
    
    def test_get_animation_mode(self):
        """Test że animator zwraca właściwy mode."""
        animator = CompositionalAnimator()
        assert animator.get_animation_mode() == "compositional"
    
    def test_can_handle(self):
        """Test że animator obsługuje właściwy mode."""
        animator = CompositionalAnimator()
        assert animator.can_handle("compositional") is True
        assert animator.can_handle("beat-switch") is False
        assert animator.can_handle("energy-pulse") is False
    
    @patch.dict(os.environ, {
        'BLENDER_VSE_LAYOUT_TYPE': 'random',
        'BLENDER_VSE_LAYOUT_CONFIG': 'overlap_allowed=false,seed=42',
        'BLENDER_VSE_ANIMATION_CONFIG': 'scale:bass:0.3:2,shake:beat:10.0:2'
    })
    def test_animate_with_environment_config(self, mock_video_strips, mock_audio_analysis):
        """Test animacji z konfiguracją z zmiennych środowiskowych."""
        animator = CompositionalAnimator()
        
        # Mock _create_compositor to return a mock compositor
        mock_compositor = Mock()
        mock_compositor.apply = Mock(return_value=True)
        animator._create_compositor = Mock(return_value=mock_compositor)
        
        success = animator.animate(mock_video_strips, mock_audio_analysis, 30)
        
        assert success
        animator._create_compositor.assert_called_once()
        mock_compositor.apply.assert_called_once_with(mock_video_strips, mock_audio_analysis, 30)
    
    def test_parse_layout_config_random(self):
        """Test parsowania konfiguracji dla random layout."""
        animator = CompositionalAnimator()
        
        layout_type = "random"
        layout_config = "overlap_allowed=false,seed=42,margin=0.1"
        
        layout = animator._parse_layout_config(layout_type, layout_config)
        
        assert isinstance(layout, RandomLayout)
        assert layout.overlap_allowed is False
        assert layout.seed == 42
        assert layout.margin == 0.1
    
    def test_parse_layout_config_default(self):
        """Test domyślnej konfiguracji layout."""
        animator = CompositionalAnimator()
        
        layout = animator._parse_layout_config("unknown", "")
        
        assert isinstance(layout, RandomLayout)
        assert layout.overlap_allowed is True  # Default
    
    def test_parse_animation_config_basic(self):
        """Test parsowania konfiguracji animacji."""
        animator = CompositionalAnimator()
        
        config = "scale:bass:0.3:2,shake:beat:10.0:3"
        animations = animator._parse_animation_config(config)
        
        assert len(animations) == 2
        
        # Check scale animation
        scale_anim = animations[0]
        assert isinstance(scale_anim, ScaleAnimation)
        assert scale_anim.trigger == "bass"
        assert scale_anim.intensity == 0.3
        assert scale_anim.duration_frames == 2
        
        # Check shake animation
        shake_anim = animations[1]
        assert isinstance(shake_anim, ShakeAnimation)
        assert shake_anim.trigger == "beat"
        assert shake_anim.intensity == 10.0
        assert shake_anim.return_frames == 3
    
    def test_parse_animation_config_empty(self):
        """Test parsowania pustej konfiguracji animacji."""
        animator = CompositionalAnimator()
        
        animations = animator._parse_animation_config("")
        
        assert len(animations) == 0
    
    def test_parse_animation_config_invalid_format(self):
        """Test obsługi nieprawidłowego formatu konfiguracji."""
        animator = CompositionalAnimator()
        
        # Invalid format should be ignored
        config = "invalid:format,scale:bass:0.3:2"
        animations = animator._parse_animation_config(config)
        
        assert len(animations) == 1  # Only valid one should be parsed
        assert isinstance(animations[0], ScaleAnimation)
    
    def test_parse_animation_config_unknown_type(self):
        """Test parsowania nieznanego typu animacji."""
        animator = CompositionalAnimator()
        
        config = "unknown:bass:0.3:2,scale:beat:0.5:3"
        animations = animator._parse_animation_config(config)
        
        assert len(animations) == 1  # Only known type should be parsed
        assert isinstance(animations[0], ScaleAnimation)
    
    @patch.dict(os.environ, {
        'BLENDER_VSE_LAYOUT_TYPE': 'random',
        'BLENDER_VSE_LAYOUT_CONFIG': 'seed=123',
        'BLENDER_VSE_ANIMATION_CONFIG': 'scale:bass:0.5'
    })
    def test_create_compositor_from_env(self):
        """Test tworzenia kompozytora z zmiennych środowiskowych."""
        animator = CompositionalAnimator()
        
        compositor = animator._create_compositor()
        
        assert compositor is not None
        assert isinstance(compositor.layout, RandomLayout)
        assert compositor.layout.seed == 123
        assert len(compositor.animations) == 1
        assert isinstance(compositor.animations[0], ScaleAnimation)
    
    def test_create_compositor_no_env(self):
        """Test tworzenia kompozytora bez zmiennych środowiskowych."""
        animator = CompositionalAnimator()
        
        compositor = animator._create_compositor()
        
        assert compositor is not None
        assert isinstance(compositor.layout, RandomLayout)
        assert len(compositor.animations) == 0  # No animations configured
    
    def test_animate_no_strips(self):
        """Test animacji bez stripów."""
        animator = CompositionalAnimator()
        
        success = animator.animate([], {}, 30)
        
        assert success  # Should succeed but do nothing
    
    def test_animate_no_analysis(self, mock_video_strips):
        """Test animacji bez danych analizy."""
        animator = CompositionalAnimator()
        animator.compositor = Mock()
        animator.compositor.apply = Mock(return_value=True)
        animator._create_compositor = Mock(return_value=animator.compositor)
        
        success = animator.animate(mock_video_strips, {}, 30)
        
        assert success
        animator.compositor.apply.assert_called_once_with(mock_video_strips, {}, 30)
    
    def test_animate_compositor_failure(self, mock_video_strips, mock_audio_analysis):
        """Test obsługi błędu w kompozytorze."""
        animator = CompositionalAnimator()
        animator.compositor = Mock()
        animator.compositor.apply = Mock(return_value=False)
        animator._create_compositor = Mock(return_value=animator.compositor)
        
        success = animator.animate(mock_video_strips, mock_audio_analysis, 30)
        
        assert not success