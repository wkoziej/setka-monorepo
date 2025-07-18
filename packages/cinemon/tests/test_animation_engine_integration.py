"""Integration tests for AnimationEngine with CompositionalAnimator."""

import pytest
import os
from unittest.mock import Mock, patch
from blender.vse.animation_engine import BlenderAnimationEngine
from blender.vse.animators.compositional_animator import CompositionalAnimator


class TestAnimationEngineIntegration:
    """Test suite for AnimationEngine integration with CompositionalAnimator."""
    
    @pytest.fixture
    def mock_video_strips(self):
        """Create mock video strips with transform property."""
        strips = []
        for i in range(2):
            strip = Mock()
            strip.name = f"strip_{i}"
            strip.transform = Mock()
            strip.transform.offset_x = 0
            strip.transform.offset_y = 0
            strip.transform.scale_x = 1.0
            strip.transform.scale_y = 1.0
            strips.append(strip)
        return strips
    
    @pytest.fixture
    def mock_audio_analysis(self):
        """Create mock audio analysis data."""
        return {
            "duration": 5.0,
            "tempo": {"bpm": 120.0},
            "animation_events": {
                "beats": [1.0, 2.0, 3.0],
                "energy_peaks": [1.5, 2.5]
            }
        }
    
    def test_animation_engine_includes_compositional_animator(self):
        """Test że AnimationEngine zawiera CompositionalAnimator."""
        engine = BlenderAnimationEngine()
        
        # Check that compositional animator is loaded
        compositional_animators = [
            animator for animator in engine.animators 
            if isinstance(animator, CompositionalAnimator)
        ]
        assert len(compositional_animators) == 1
        
        # Check that 'compositional' mode is available
        available_modes = engine.get_available_modes()
        assert "compositional" in available_modes
    
    def test_animation_engine_can_handle_compositional_mode(self):
        """Test że AnimationEngine może obsłużyć tryb 'compositional'."""
        engine = BlenderAnimationEngine()
        
        # Find compositor animator
        compositor_animator = None
        for animator in engine.animators:
            if animator.can_handle("compositional"):
                compositor_animator = animator
                break
        
        assert compositor_animator is not None
        assert isinstance(compositor_animator, CompositionalAnimator)
        assert compositor_animator.get_animation_mode() == "compositional"
    
    @patch.dict(os.environ, {
        'BLENDER_VSE_LAYOUT_TYPE': 'random',
        'BLENDER_VSE_LAYOUT_CONFIG': 'seed=42',
        'BLENDER_VSE_ANIMATION_CONFIG': 'scale:bass:0.3'
    })
    def test_animation_engine_delegates_to_compositional_animator(self, mock_video_strips, mock_audio_analysis):
        """Test że AnimationEngine deleguje do CompositionalAnimator."""
        engine = BlenderAnimationEngine()
        
        # Mock the compositional animator's animate method
        for animator in engine.animators:
            if isinstance(animator, CompositionalAnimator):
                animator.animate = Mock(return_value=True)
        
        success = engine.animate(mock_video_strips, mock_audio_analysis, 30, "compositional")
        
        assert success
        
        # Verify that compositional animator was called
        for animator in engine.animators:
            if isinstance(animator, CompositionalAnimator):
                animator.animate.assert_called_once_with(mock_video_strips, mock_audio_analysis, 30)
    
    def test_animation_engine_backward_compatibility(self, mock_video_strips, mock_audio_analysis):
        """Test że stare animatory nadal działają."""
        engine = BlenderAnimationEngine()
        
        # Mock existing animators
        for animator in engine.animators:
            if not isinstance(animator, CompositionalAnimator):
                animator.animate = Mock(return_value=True)
        
        # Test that old animation modes still work
        old_modes = ["beat-switch", "energy-pulse", "multi-pip"]
        
        for mode in old_modes:
            success = engine.animate(mock_video_strips, mock_audio_analysis, 30, mode)
            assert success, f"Mode {mode} should still work"
    
    def test_animation_engine_add_remove_animator(self):
        """Test dodawania i usuwania animatorów."""
        engine = BlenderAnimationEngine()
        initial_count = len(engine.animators)
        
        # Create a mock animator
        mock_animator = Mock()
        mock_animator.animate = Mock(return_value=True)
        mock_animator.can_handle = Mock(return_value=True)
        mock_animator.get_animation_mode = Mock(return_value="test_mode")
        
        # Add animator
        engine.add_animator(mock_animator)
        assert len(engine.animators) == initial_count + 1
        assert "test_mode" in engine.get_available_modes()
        
        # Remove animator
        engine.remove_animator(mock_animator)
        assert len(engine.animators) == initial_count
        assert "test_mode" not in engine.get_available_modes()
    
    def test_animation_engine_invalid_animator(self):
        """Test że błędne animatory są odrzucane."""
        engine = BlenderAnimationEngine()
        
        # Create invalid animator (missing required methods)
        class InvalidAnimator:
            def animate(self):
                return True
            # Missing can_handle and get_animation_mode
        
        invalid_animator = InvalidAnimator()
        
        with pytest.raises(ValueError, match="Animator must have"):
            engine.add_animator(invalid_animator)
    
    def test_animation_engine_no_matching_animator(self, mock_video_strips, mock_audio_analysis):
        """Test obsługi trybu bez odpowiadającego animatora."""
        engine = BlenderAnimationEngine()
        
        success = engine.animate(mock_video_strips, mock_audio_analysis, 30, "non_existent_mode")
        
        assert not success
    
    def test_animation_engine_invalid_parameters(self, mock_video_strips, mock_audio_analysis):
        """Test walidacji parametrów."""
        engine = BlenderAnimationEngine()
        
        # Invalid fps
        success = engine.animate(mock_video_strips, mock_audio_analysis, 0, "compositional")
        assert not success
        
        # Empty animation mode
        success = engine.animate(mock_video_strips, mock_audio_analysis, 30, "")
        assert not success
    
    @patch.dict(os.environ, {
        'BLENDER_VSE_LAYOUT_TYPE': 'random',
        'BLENDER_VSE_ANIMATION_CONFIG': 'scale:bass:0.5,shake:beat:5.0'
    })
    def test_full_integration_pipeline(self, mock_video_strips, mock_audio_analysis):
        """Test pełnego pipeline integracji."""
        engine = BlenderAnimationEngine()
        
        # Mock keyframe helpers for all animations
        for animator in engine.animators:
            if isinstance(animator, CompositionalAnimator):
                # Mock compositor creation
                mock_compositor = Mock()
                mock_compositor.apply = Mock(return_value=True)
                animator._create_compositor = Mock(return_value=mock_compositor)
        
        success = engine.animate(mock_video_strips, mock_audio_analysis, 30, "compositional")
        
        assert success
        
        # Verify compositor was created and applied
        compositor_animator = None
        for animator in engine.animators:
            if isinstance(animator, CompositionalAnimator):
                compositor_animator = animator
                break
        
        assert compositor_animator._create_compositor.called
        mock_compositor.apply.assert_called_once_with(mock_video_strips, mock_audio_analysis, 30)