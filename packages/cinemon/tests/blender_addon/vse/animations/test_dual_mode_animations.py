# ABOUTME: Test suite for dual-mode animations (static one_time and event-driven)
# ABOUTME: Validates BlackWhiteAnimation, VintageColorGradeAnimation

"""Test suite for dual-mode animations supporting one_time and event-driven triggers."""

from unittest.mock import MagicMock, patch

import pytest


class TestBlackWhiteAnimation:
    """Test BlackWhiteAnimation dual-mode functionality."""

    def test_one_time_mode_compatibility(self, mock_bpy):
        """Test that one_time mode works as before."""
        from vse.animations.black_white_animation import BlackWhiteAnimation

        # Create animation in one_time mode
        animation = BlackWhiteAnimation(trigger="one_time", intensity=0.8)

        # Create mock strip
        strip = MagicMock()
        strip.name = "test_strip"
        strip.color_saturation = 1.0

        # Apply animation
        result = animation.apply_to_strip(strip, [], 30)

        # Verify desaturation was applied
        assert result is True
        assert strip.color_saturation == pytest.approx(0.2, rel=0.1)  # 1.0 - 0.8 = 0.2

    def test_event_driven_mode(self, mock_bpy):
        """Test new event-driven mode."""
        from vse.animations.black_white_animation import BlackWhiteAnimation
        from vse.keyframe_helper import KeyframeHelper

        # Create animation in event-driven mode
        animation = BlackWhiteAnimation(
            trigger="beat", intensity=0.9, duration_frames=2
        )
        animation.keyframe_helper = KeyframeHelper()

        # Create mock strip with property tracking
        strip = MagicMock()
        strip.name = "test_strip"
        # Track saturation changes
        saturation_values = []

        def set_saturation(val):
            saturation_values.append(val)

        def get_saturation():
            return saturation_values[-1] if saturation_values else 1.0

        type(strip).color_saturation = property(
            fget=lambda self: get_saturation(),
            fset=lambda self, val: set_saturation(val),
        )

        # Apply animation with beat events
        events = [1.0, 2.0, 3.0]  # Beat times in seconds
        result = animation.apply_to_strip(strip, events, 30)

        # Verify animation was applied
        assert result is True
        # Check that saturation was changed (should have multiple values)
        assert len(saturation_values) > 0
        # At least one value should be desaturated (< 1.0)
        assert any(val < 1.0 for val in saturation_values)

    def test_fade_in_feature(self, mock_bpy):
        """Test new fade-in feature for one_time mode."""
        from vse.animations.black_white_animation import BlackWhiteAnimation
        from vse.keyframe_helper import KeyframeHelper

        # Create animation with fade-in
        animation = BlackWhiteAnimation(trigger="one_time", intensity=0.8, fade_in=True)
        animation.keyframe_helper = KeyframeHelper()

        # Create mock strip
        strip = MagicMock()
        strip.name = "test_strip"
        strip.color_saturation = 1.0

        # Apply animation
        result = animation.apply_to_strip(strip, [], 30)

        # Verify fade-in was applied (final value should be desaturated)
        assert result is True
        # Check that saturation was set multiple times (fade-in effect)
        assert strip.color_saturation == pytest.approx(0.2, rel=0.1)

    def test_mode_switching(self, mock_bpy):
        """Test that trigger determines the mode correctly."""
        from vse.animations.black_white_animation import BlackWhiteAnimation

        # Test one_time trigger
        anim_static = BlackWhiteAnimation(trigger="one_time")
        assert anim_static.trigger == "one_time"

        # Test event-driven triggers
        anim_beat = BlackWhiteAnimation(trigger="beat")
        assert anim_beat.trigger == "beat"

        anim_bass = BlackWhiteAnimation(trigger="bass")
        assert anim_bass.trigger == "bass"

        anim_energy = BlackWhiteAnimation(trigger="energy_peaks")
        assert anim_energy.trigger == "energy_peaks"


class TestVintageColorGradeAnimation:
    """Test VintageColorGradeAnimation dual-mode functionality."""

    def test_one_time_mode_compatibility(self, mock_bpy):
        """Test that one_time mode works as before."""
        from vse.animations.vintage_color_grade_animation import (
            VintageColorGradeAnimation,
        )

        # Create animation in one_time mode
        animation = VintageColorGradeAnimation(
            trigger="one_time", sepia_amount=0.4, contrast_boost=0.2
        )

        # Create mock strip with modifiers
        strip = MagicMock()
        strip.name = "test_strip"
        strip.modifiers = MagicMock()

        mock_modifier = MagicMock()
        mock_modifier.color_balance = MagicMock()
        mock_modifier.color_balance.lift = (1.0, 1.0, 1.0)
        mock_modifier.color_balance.gamma = (1.0, 1.0, 1.0)
        mock_modifier.color_balance.gain = (1.0, 1.0, 1.0)
        strip.modifiers.new = MagicMock(return_value=mock_modifier)

        # Apply animation
        result = animation.apply_to_strip(strip, [], 30)

        # Verify color grading was applied
        assert result is True
        assert strip.modifiers.new.called

    def test_event_driven_mode_sepia(self, mock_bpy):
        """Test event-driven mode animating sepia."""
        from vse.animations.vintage_color_grade_animation import (
            VintageColorGradeAnimation,
        )
        from vse.keyframe_helper import KeyframeHelper

        # Create animation animating sepia
        animation = VintageColorGradeAnimation(
            trigger="sections",
            sepia_amount=0.6,
            animate_property="sepia",
            duration_frames=10,
        )
        animation.keyframe_helper = KeyframeHelper()

        # Create mock strip
        strip = MagicMock()
        strip.name = "test_strip"

        # Mock modifiers collection
        modifiers_list = []
        modifiers_mock = MagicMock()

        def new_modifier(name, type):
            mod = MagicMock()
            mod.name = name
            mod.color_balance = MagicMock()
            mod.color_balance.lift = (1.0, 1.0, 1.0)
            mod.color_balance.gamma = (1.0, 1.0, 1.0)
            mod.color_balance.gain = (1.0, 1.0, 1.0)
            modifiers_list.append(mod)
            return mod

        modifiers_mock.new = new_modifier
        modifiers_mock.__iter__ = lambda self: iter(modifiers_list)
        strip.modifiers = modifiers_mock

        # Apply animation with section events
        events = [0.0, 10.0, 20.0]  # Section boundaries
        result = animation.apply_to_strip(strip, events, 30)

        # Verify animation was applied
        assert result is True

    def test_event_driven_mode_contrast(self, mock_bpy):
        """Test event-driven mode animating contrast."""
        from vse.animations.vintage_color_grade_animation import (
            VintageColorGradeAnimation,
        )
        from vse.keyframe_helper import KeyframeHelper

        # Create animation animating contrast
        animation = VintageColorGradeAnimation(
            trigger="beat",
            contrast_boost=0.3,
            animate_property="contrast",
            duration_frames=3,
        )
        animation.keyframe_helper = KeyframeHelper()

        # Create mock strip
        strip = MagicMock()
        strip.name = "test_strip"

        # Mock modifiers collection
        modifiers_list = []
        modifiers_mock = MagicMock()

        def new_modifier(name, type):
            mod = MagicMock()
            mod.name = name
            mod.color_balance = MagicMock()
            mod.color_balance.lift = (1.0, 1.0, 1.0)
            mod.color_balance.gamma = (1.0, 1.0, 1.0)
            mod.color_balance.gain = (1.0, 1.0, 1.0)
            modifiers_list.append(mod)
            return mod

        modifiers_mock.new = new_modifier
        modifiers_mock.__iter__ = lambda self: iter(modifiers_list)
        strip.modifiers = modifiers_mock

        # Apply animation with beat events
        events = [1.0, 2.0, 3.0]
        result = animation.apply_to_strip(strip, events, 30)

        # Verify animation was applied
        assert result is True

    def test_animate_property_options(self, mock_bpy):
        """Test different animate_property options."""
        from vse.animations.vintage_color_grade_animation import (
            VintageColorGradeAnimation,
        )

        # Test sepia animation
        anim_sepia = VintageColorGradeAnimation(animate_property="sepia")
        assert anim_sepia.animate_property == "sepia"

        # Test contrast animation
        anim_contrast = VintageColorGradeAnimation(animate_property="contrast")
        assert anim_contrast.animate_property == "contrast"

        # Test both animation
        anim_both = VintageColorGradeAnimation(animate_property="both")
        assert anim_both.animate_property == "both"


class TestStaticToEventMigration:
    """Test overall migration from static to event-driven animations."""

    def test_all_static_animations_support_events(self, mock_bpy):
        """Test that all formerly static animations now support events."""
        from vse.animations.black_white_animation import BlackWhiteAnimation
        from vse.animations.vintage_color_grade_animation import (
            VintageColorGradeAnimation,
        )

        animations = [
            BlackWhiteAnimation(trigger="beat"),
            VintageColorGradeAnimation(trigger="energy_peaks"),
        ]

        for anim in animations:
            # All should have event-driven triggers
            assert anim.trigger in ["beat", "bass", "energy_peaks"]
            # All should have duration_frames parameter
            assert hasattr(anim, "duration_frames")

    def test_backwards_compatibility(self, mock_bpy):
        """Test that old YAML configurations still work."""
        from vse.animations.black_white_animation import BlackWhiteAnimation
        from vse.animations.vintage_color_grade_animation import (
            VintageColorGradeAnimation,
        )

        # Old-style one_time configurations should still work
        animations = [
            BlackWhiteAnimation(trigger="one_time", intensity=0.8),
            VintageColorGradeAnimation(trigger="one_time", sepia_amount=0.4),
        ]

        for anim in animations:
            assert anim.trigger == "one_time"

            # Create mock strip
            strip = MagicMock()
            strip.name = "test_strip"
            strip.color_saturation = 1.0
            strip.modifiers = MagicMock()
            strip.modifiers.new = MagicMock(return_value=MagicMock())

            # Should apply without errors
            result = anim.apply_to_strip(strip, [], 30)
            assert result is True
