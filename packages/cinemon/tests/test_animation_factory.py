# ABOUTME: Tests for AnimationFactory - verifies factory pattern implementation and animation creation
# ABOUTME: Ensures all animation types can be created with correct parameters and defaults

"""Tests for AnimationFactory."""

import pytest
from vse.animations import AnimationFactory
from vse.animations.scale_animation import ScaleAnimation
from vse.animations.shake_animation import ShakeAnimation
from vse.animations.vintage_color_grade_animation import VintageColorGradeAnimation
from vse.animations.visibility_animation import VisibilityAnimation


class TestAnimationFactory:
    """Tests for AnimationFactory class."""

    def test_create_scale_animation(self):
        """Test creating scale animation with factory."""
        spec = {
            "type": "scale",
            "trigger": "bass",
            "intensity": 0.5,
            "duration_frames": 4,
            "target_strips": ["Camera1", "Camera2"],
        }

        animation = AnimationFactory.create(spec)

        assert isinstance(animation, ScaleAnimation)
        assert animation.trigger == "bass"
        assert animation.intensity == 0.5
        assert animation.duration_frames == 4
        assert animation.target_strips == ["Camera1", "Camera2"]

    def test_create_animation_with_defaults(self):
        """Test creating animation with default parameters."""
        spec = {"type": "shake", "trigger": "beat"}

        animation = AnimationFactory.create(spec)

        assert isinstance(animation, ShakeAnimation)
        assert animation.trigger == "beat"
        assert animation.intensity == 10.0  # default
        assert animation.return_frames == 2  # default
        assert animation.target_strips == []  # default

    def test_create_vintage_color_animation(self):
        """Test creating vintage color animation."""
        spec = {
            "type": "vintage_color",
            "trigger": "one_time",
            "sepia_amount": 0.6,
            "contrast_boost": 0.3,
        }

        animation = AnimationFactory.create(spec)

        assert isinstance(animation, VintageColorGradeAnimation)
        assert animation.trigger == "one_time"
        assert animation.sepia_amount == 0.6
        assert animation.contrast_boost == 0.3

    def test_create_unknown_animation_type(self):
        """Test handling unknown animation type."""
        spec = {"type": "unknown_animation", "trigger": "bass"}

        animation = AnimationFactory.create(spec)

        assert animation is None

    def test_create_multiple_animations(self):
        """Test creating multiple animations at once."""
        specs = [
            {"type": "scale", "trigger": "bass", "intensity": 0.3},
            {"type": "shake", "trigger": "beat", "intensity": 5.0},
            {
                "type": "visibility",
                "trigger": "sections",
                "pattern": "cycle",
                "target_strips": ["Camera1"],
            },
        ]

        animations = AnimationFactory.create_multiple(specs)

        assert len(animations) == 3
        assert isinstance(animations[0], ScaleAnimation)
        assert isinstance(animations[1], ShakeAnimation)
        assert isinstance(animations[2], VisibilityAnimation)

        # Verify specific properties
        assert animations[0].intensity == 0.3
        assert animations[1].intensity == 5.0
        assert animations[2].pattern == "cycle"
        assert animations[2].target_strips == ["Camera1"]

    def test_create_multiple_with_invalid_specs(self):
        """Test creating multiple animations with some invalid specs."""
        specs = [
            {"type": "scale", "trigger": "bass"},
            {"type": "invalid_type", "trigger": "beat"},
            {"type": "shake", "trigger": "energy_peaks"},
        ]

        animations = AnimationFactory.create_multiple(specs)

        # Should skip invalid animation
        assert len(animations) == 2
        assert isinstance(animations[0], ScaleAnimation)
        assert isinstance(animations[1], ShakeAnimation)

    def test_get_registered_types(self):
        """Test getting list of registered animation types."""
        registered_types = AnimationFactory.get_registered_types()

        expected_types = [
            "scale",
            "shake",
            "rotation",
            "jitter",
            "brightness_flicker",
            "black_white",
            "film_grain",
            "vintage_color",
            "visibility",
        ]

        assert set(registered_types) == set(expected_types)

    def test_all_registered_animations_can_be_created(self):
        """Test that all registered animation types can be created."""
        registered_types = AnimationFactory.get_registered_types()

        for anim_type in registered_types:
            spec = {"type": anim_type, "trigger": "bass"}

            animation = AnimationFactory.create(spec)
            assert animation is not None, f"Failed to create {anim_type} animation"

    def test_empty_spec(self):
        """Test handling empty specification."""
        animation = AnimationFactory.create({})
        assert animation is None

    def test_none_spec(self):
        """Test handling None specification."""
        with pytest.raises(AttributeError):
            AnimationFactory.create(None)
