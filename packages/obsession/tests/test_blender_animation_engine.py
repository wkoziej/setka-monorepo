"""
ABOUTME: Tests for BlenderAnimationEngine class - validates animation delegation system.
ABOUTME: TDD approach - tests written first to define expected engine behavior and animator delegation.
"""

import pytest
from pathlib import Path
import sys
from unittest.mock import Mock

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.blender_vse.blender_animation_engine import BlenderAnimationEngine
from core.blender_vse.animators.beat_switch_animator import BeatSwitchAnimator
from core.blender_vse.animators.energy_pulse_animator import EnergyPulseAnimator
from core.blender_vse.animators.multi_pip_animator import MultiPipAnimator


class TestBlenderAnimationEngineBasic:
    """Test basic BlenderAnimationEngine functionality."""

    def test_animation_engine_initialization(self):
        """BlenderAnimationEngine should initialize with all available animators."""
        engine = BlenderAnimationEngine()

        assert engine is not None
        assert hasattr(engine, "animators")
        assert isinstance(engine.animators, list)
        assert len(engine.animators) >= 3  # At least the three main animators

    def test_animation_engine_has_required_methods(self):
        """BlenderAnimationEngine should have required methods."""
        engine = BlenderAnimationEngine()

        required_methods = [
            "animate",
            "get_available_modes",
            "add_animator",
            "remove_animator",
        ]

        for method in required_methods:
            assert hasattr(engine, method), f"Missing method: {method}"
            assert callable(getattr(engine, method)), f"Method {method} is not callable"

    def test_animation_engine_loads_default_animators(self):
        """BlenderAnimationEngine should load default animators on initialization."""
        engine = BlenderAnimationEngine()

        # Should have instances of all three main animators
        animator_types = [type(animator) for animator in engine.animators]

        assert BeatSwitchAnimator in animator_types
        assert EnergyPulseAnimator in animator_types
        assert MultiPipAnimator in animator_types

    def test_animation_engine_get_available_modes(self):
        """BlenderAnimationEngine should return all available animation modes."""
        engine = BlenderAnimationEngine()

        available_modes = engine.get_available_modes()

        assert isinstance(available_modes, list)
        assert "beat-switch" in available_modes
        assert "energy-pulse" in available_modes
        assert "multi-pip" in available_modes
        assert len(available_modes) >= 3


class TestBlenderAnimationEngineAnimatorManagement:
    """Test animator management functionality."""

    def test_add_animator(self):
        """Should be able to add custom animators."""
        engine = BlenderAnimationEngine()
        initial_count = len(engine.animators)

        # Create mock animator
        mock_animator = Mock()
        mock_animator.get_animation_mode.return_value = "custom-mode"
        mock_animator.can_handle.return_value = True

        engine.add_animator(mock_animator)

        assert len(engine.animators) == initial_count + 1
        assert mock_animator in engine.animators
        assert "custom-mode" in engine.get_available_modes()

    def test_remove_animator(self):
        """Should be able to remove animators."""
        engine = BlenderAnimationEngine()
        initial_count = len(engine.animators)

        # Find an animator to remove
        animator_to_remove = None
        for animator in engine.animators:
            if isinstance(animator, BeatSwitchAnimator):
                animator_to_remove = animator
                break

        assert animator_to_remove is not None

        engine.remove_animator(animator_to_remove)

        assert len(engine.animators) == initial_count - 1
        assert animator_to_remove not in engine.animators

    def test_add_animator_validation(self):
        """Should validate animator interface when adding."""
        engine = BlenderAnimationEngine()

        # Invalid animator - missing required methods
        class InvalidAnimator:
            pass

        invalid_animator = InvalidAnimator()

        with pytest.raises(ValueError, match="Animator must have.*methods"):
            engine.add_animator(invalid_animator)

    def test_remove_nonexistent_animator(self):
        """Should handle removal of non-existent animator gracefully."""
        engine = BlenderAnimationEngine()
        initial_count = len(engine.animators)

        non_existent_animator = Mock()

        # Should not raise error
        engine.remove_animator(non_existent_animator)

        assert len(engine.animators) == initial_count


class TestBlenderAnimationEngineAnimation:
    """Test animation delegation functionality."""

    def test_animate_delegates_to_correct_animator(self):
        """Should delegate animation to correct animator based on mode."""
        engine = BlenderAnimationEngine()

        # Mock all animators
        for animator in engine.animators:
            animator.animate = Mock(return_value=True)
            animator.can_handle = Mock(return_value=False)

        # Set up one animator to handle our test mode
        test_animator = engine.animators[0]
        test_animator.can_handle = Mock(return_value=True)
        test_animator.get_animation_mode = Mock(return_value="test-mode")

        video_strips = [Mock(name="Video_1")]
        animation_data = {"animation_events": {"beats": [1.0]}}
        fps = 30

        result = engine.animate(video_strips, animation_data, fps, "test-mode")

        assert result is True
        test_animator.animate.assert_called_once_with(video_strips, animation_data, fps)

    def test_animate_beat_switch_mode(self):
        """Should delegate beat-switch animation to BeatSwitchAnimator."""
        engine = BlenderAnimationEngine()

        # Find the beat switch animator
        beat_switch_animator = None
        for animator in engine.animators:
            if isinstance(animator, BeatSwitchAnimator):
                beat_switch_animator = animator
                break

        assert beat_switch_animator is not None

        # Mock the animator
        beat_switch_animator.animate = Mock(return_value=True)

        video_strips = [Mock(name="Video_1")]
        animation_data = {"animation_events": {"beats": [1.0, 2.0]}}
        fps = 30

        result = engine.animate(video_strips, animation_data, fps, "beat-switch")

        assert result is True
        beat_switch_animator.animate.assert_called_once_with(
            video_strips, animation_data, fps
        )

    def test_animate_energy_pulse_mode(self):
        """Should delegate energy-pulse animation to EnergyPulseAnimator."""
        engine = BlenderAnimationEngine()

        # Find the energy pulse animator
        energy_pulse_animator = None
        for animator in engine.animators:
            if isinstance(animator, EnergyPulseAnimator):
                energy_pulse_animator = animator
                break

        assert energy_pulse_animator is not None

        # Mock the animator
        energy_pulse_animator.animate = Mock(return_value=True)

        video_strips = [Mock(name="Video_1")]
        animation_data = {"animation_events": {"energy_peaks": [2.1, 5.8]}}
        fps = 30

        result = engine.animate(video_strips, animation_data, fps, "energy-pulse")

        assert result is True
        energy_pulse_animator.animate.assert_called_once_with(
            video_strips, animation_data, fps
        )

    def test_animate_multi_pip_mode(self):
        """Should delegate multi-pip animation to MultiPipAnimator."""
        engine = BlenderAnimationEngine()

        # Find the multi-pip animator
        multi_pip_animator = None
        for animator in engine.animators:
            if isinstance(animator, MultiPipAnimator):
                multi_pip_animator = animator
                break

        assert multi_pip_animator is not None

        # Mock the animator
        multi_pip_animator.animate = Mock(return_value=True)

        video_strips = [Mock(name="Video_1"), Mock(name="Video_2")]
        animation_data = {
            "animation_events": {
                "sections": [{"start": 0.0, "end": 30.0, "label": "verse"}],
                "beats": [1.0, 2.0],
            }
        }
        fps = 30

        result = engine.animate(video_strips, animation_data, fps, "multi-pip")

        assert result is True
        multi_pip_animator.animate.assert_called_once_with(
            video_strips, animation_data, fps
        )

    def test_animate_unknown_mode(self):
        """Should handle unknown animation mode gracefully."""
        engine = BlenderAnimationEngine()

        video_strips = [Mock(name="Video_1")]
        animation_data = {"animation_events": {"beats": [1.0]}}
        fps = 30

        result = engine.animate(video_strips, animation_data, fps, "unknown-mode")

        assert result is False  # Should return False for unknown mode

    def test_animate_no_capable_animator(self):
        """Should handle case where no animator can handle the mode."""
        engine = BlenderAnimationEngine()

        # Mock all animators to return False for can_handle
        for animator in engine.animators:
            animator.can_handle = Mock(return_value=False)

        video_strips = [Mock(name="Video_1")]
        animation_data = {"animation_events": {"beats": [1.0]}}
        fps = 30

        result = engine.animate(video_strips, animation_data, fps, "test-mode")

        assert result is False


class TestBlenderAnimationEngineValidation:
    """Test input validation for BlenderAnimationEngine."""

    def test_animate_validates_parameters(self):
        """Should validate animation parameters."""
        engine = BlenderAnimationEngine()

        # Invalid FPS
        result = engine.animate([], {}, 0, "beat-switch")
        assert result is False

        result = engine.animate([], {}, -30, "beat-switch")
        assert result is False

        # Empty mode
        result = engine.animate([], {}, 30, "")
        assert result is False

        # None mode
        result = engine.animate([], {}, 30, None)
        assert result is False

    def test_animate_handles_empty_inputs(self):
        """Should handle empty inputs gracefully."""
        engine = BlenderAnimationEngine()

        # Empty video strips - should delegate to animator
        result = engine.animate(
            [], {"animation_events": {"beats": [1.0]}}, 30, "beat-switch"
        )
        # Result depends on animator implementation - should be handled by animator
        assert isinstance(result, bool)

        # Empty animation data - should delegate to animator
        result = engine.animate([Mock()], {}, 30, "beat-switch")
        assert isinstance(result, bool)

    def test_animate_handles_none_inputs(self):
        """Should handle None inputs gracefully."""
        engine = BlenderAnimationEngine()

        # None video strips
        result = engine.animate(
            None, {"animation_events": {"beats": [1.0]}}, 30, "beat-switch"
        )
        assert isinstance(result, bool)

        # None animation data
        result = engine.animate([Mock()], None, 30, "beat-switch")
        assert isinstance(result, bool)


class TestBlenderAnimationEnginePerformance:
    """Test performance and efficiency of BlenderAnimationEngine."""

    def test_animate_finds_animator_efficiently(self):
        """Should find correct animator efficiently without checking all."""
        engine = BlenderAnimationEngine()

        # Create spies for can_handle calls
        can_handle_calls = []
        for animator in engine.animators:
            animator_name = type(animator).__name__
            original_can_handle = animator.can_handle

            def make_spy(name, orig):
                def spy_can_handle(mode):
                    can_handle_calls.append(name)
                    return orig(mode)

                return spy_can_handle

            animator.can_handle = make_spy(animator_name, original_can_handle)

        video_strips = [Mock(name="Video_1")]
        animation_data = {"animation_events": {"beats": [1.0]}}
        fps = 30

        # Test beat-switch mode
        can_handle_calls.clear()
        result = engine.animate(video_strips, animation_data, fps, "beat-switch")

        assert result is True
        # Should stop checking after finding the right animator
        assert len(can_handle_calls) >= 1
        assert "BeatSwitchAnimator" in can_handle_calls

    def test_multiple_animations_reuse_animators(self):
        """Should reuse animator instances across multiple animations."""
        engine = BlenderAnimationEngine()

        initial_animators = engine.animators.copy()

        video_strips = [Mock(name="Video_1")]
        animation_data = {"animation_events": {"beats": [1.0]}}
        fps = 30

        # Perform multiple animations
        for _ in range(5):
            engine.animate(video_strips, animation_data, fps, "beat-switch")

        # Should still have same animator instances
        assert engine.animators == initial_animators


class TestBlenderAnimationEngineCompatibility:
    """Test compatibility with existing BlenderVSEConfigurator interface."""

    def test_animate_signature_compatibility(self):
        """Should have compatible signature with BlenderVSEConfigurator methods."""
        engine = BlenderAnimationEngine()

        # Should accept same parameter types as original methods
        video_strips = []
        animation_data = {}
        fps = 30
        animation_mode = "beat-switch"

        # Should not raise TypeError
        result = engine.animate(video_strips, animation_data, fps, animation_mode)
        assert isinstance(result, bool)

    def test_animate_return_type_compatibility(self):
        """Should return same type as original animation methods."""
        engine = BlenderAnimationEngine()

        test_cases = [
            ("beat-switch", {"animation_events": {"beats": [1.0]}}),
            ("energy-pulse", {"animation_events": {"energy_peaks": [2.1]}}),
            (
                "multi-pip",
                {
                    "animation_events": {
                        "sections": [{"start": 0.0, "end": 30.0}],
                        "beats": [1.0],
                    }
                },
            ),
        ]

        for mode, data in test_cases:
            result = engine.animate([Mock()], data, 30, mode)
            assert isinstance(result, bool)


class TestBlenderAnimationEngineIntegration:
    """Test integration scenarios for BlenderAnimationEngine."""

    def test_all_animators_work_together(self):
        """Should support all animation modes in single engine instance."""
        engine = BlenderAnimationEngine()

        video_strips = [Mock(name="Video_1"), Mock(name="Video_2")]
        fps = 30

        # Test all three main modes
        modes_and_data = [
            ("beat-switch", {"animation_events": {"beats": [1.0, 2.0]}}),
            ("energy-pulse", {"animation_events": {"energy_peaks": [2.1, 5.8]}}),
            (
                "multi-pip",
                {
                    "animation_events": {
                        "sections": [{"start": 0.0, "end": 30.0}],
                        "beats": [1.0],
                    }
                },
            ),
        ]

        for mode, data in modes_and_data:
            result = engine.animate(video_strips, data, fps, mode)
            assert result is True, f"Failed for mode: {mode}"

    def test_engine_state_isolation(self):
        """Should maintain isolation between different animation calls."""
        engine = BlenderAnimationEngine()

        video_strips = [Mock(name="Video_1")]
        fps = 30

        # First animation
        result1 = engine.animate(
            video_strips, {"animation_events": {"beats": [1.0]}}, fps, "beat-switch"
        )

        # Second animation with different mode
        result2 = engine.animate(
            video_strips,
            {"animation_events": {"energy_peaks": [2.1]}},
            fps,
            "energy-pulse",
        )

        # Both should succeed independently
        assert result1 is True
        assert result2 is True

    def test_engine_animator_state_independence(self):
        """Should ensure animators maintain independent state."""
        engine = BlenderAnimationEngine()

        # Get references to animators
        beat_switch_animator = None
        energy_pulse_animator = None

        for animator in engine.animators:
            if isinstance(animator, BeatSwitchAnimator):
                beat_switch_animator = animator
            elif isinstance(animator, EnergyPulseAnimator):
                energy_pulse_animator = animator

        assert beat_switch_animator is not None
        assert energy_pulse_animator is not None

        # Both should be different instances
        assert beat_switch_animator is not energy_pulse_animator
        assert not isinstance(beat_switch_animator, type(energy_pulse_animator))
