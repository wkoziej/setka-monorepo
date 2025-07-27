"""
ABOUTME: Vintage film effects module for Blender VSE - adds old film style animations.
ABOUTME: Refactored to use compositional animation system - delegates to individual animation classes.
"""

from typing import Dict, List

from ..animations import (
    BlackWhiteAnimation,
    BrightnessFlickerAnimation,
    FilmGrainAnimation,
    JitterAnimation,
    RotationWobbleAnimation,
    ShakeAnimation,
    VintageColorGradeAnimation,
)


class VintageFilmEffects:
    """
    Applies vintage film effects to video strips in Blender VSE.

    Refactored to use compositional animation system for better maintainability
    and to enable use of vintage effects in compositional mode.
    """

    def __init__(self):
        """Initialize VintageFilmEffects with animation instances."""
        # Create animation instances for each effect
        self.shake_animation = ShakeAnimation()
        self.jitter_animation = JitterAnimation()
        self.brightness_flicker_animation = BrightnessFlickerAnimation()
        self.rotation_wobble_animation = RotationWobbleAnimation()
        self.black_white_animation = BlackWhiteAnimation()
        self.film_grain_animation = FilmGrainAnimation()
        self.vintage_color_grade_animation = VintageColorGradeAnimation()

    def apply_camera_shake(
        self, strip, beats: List[float], fps: int, intensity: float = 10.0
    ) -> bool:
        """
        Apply camera shake effect synchronized to beats.

        Args:
            strip: Blender video strip object
            beats: List of beat times in seconds
            fps: Frames per second
            intensity: Shake intensity in pixels

        Returns:
            bool: True if effect was applied successfully
        """
        print(f"  Applying camera shake to {strip.name} (intensity: {intensity})")

        # Configure shake animation with specified intensity
        self.shake_animation.intensity = intensity
        self.shake_animation.return_frames = 2
        self.shake_animation.random_direction = True

        # Delegate to ShakeAnimation
        return self.shake_animation.apply_to_strip(strip, beats, fps)

    def apply_film_jitter(
        self, strip, duration_frames: int, fps: int, jitter_intensity: float = 2.0
    ) -> bool:
        """
        Apply continuous film jitter effect.

        Args:
            strip: Blender video strip object
            duration_frames: Total duration in frames
            fps: Frames per second
            jitter_intensity: Jitter intensity in pixels

        Returns:
            bool: True if effect was applied successfully
        """
        print(f"  Applying film jitter to {strip.name} (intensity: {jitter_intensity})")

        # Configure jitter animation with specified intensity
        self.jitter_animation.intensity = jitter_intensity
        self.jitter_animation.min_interval = 3
        self.jitter_animation.max_interval = 8

        # Delegate to JitterAnimation (pass duration_frames via kwargs)
        return self.jitter_animation.apply_to_strip(
            strip, [], fps, duration_frames=duration_frames
        )

    def apply_brightness_flicker(
        self, strip, beats: List[float], fps: int, flicker_amount: float = 0.15
    ) -> bool:
        """
        Apply brightness flicker effect synchronized to beats.

        Args:
            strip: Blender video strip object
            beats: List of beat times in seconds
            fps: Frames per second
            flicker_amount: Flicker intensity (0.0 to 1.0)

        Returns:
            bool: True if effect was applied successfully
        """
        print(
            f"  Applying brightness flicker to {strip.name} (amount: {flicker_amount})"
        )

        # Configure brightness flicker animation with specified intensity
        self.brightness_flicker_animation.intensity = flicker_amount
        self.brightness_flicker_animation.return_frames = 1

        # Delegate to BrightnessFlickerAnimation
        return self.brightness_flicker_animation.apply_to_strip(strip, beats, fps)

    def apply_rotation_wobble(
        self, strip, beats: List[float], fps: int, wobble_degrees: float = 1.0
    ) -> bool:
        """
        Apply subtle rotation wobble effect.

        Args:
            strip: Blender video strip object
            beats: List of beat times in seconds
            fps: Frames per second
            wobble_degrees: Maximum wobble in degrees

        Returns:
            bool: True if effect was applied successfully
        """
        print(f"  Applying rotation wobble to {strip.name} (degrees: {wobble_degrees})")

        # Configure rotation wobble animation with specified parameters
        self.rotation_wobble_animation.wobble_degrees = wobble_degrees
        self.rotation_wobble_animation.return_frames = 3
        self.rotation_wobble_animation.oscillate = (
            False  # Original VintageFilmEffects behavior
        )

        # Delegate to RotationWobbleAnimation
        return self.rotation_wobble_animation.apply_to_strip(strip, beats, fps)

    def apply_vintage_film_combo(
        self,
        strip,
        beats: List[float],
        duration_frames: int,
        fps: int,
        effects_config: Dict = None,
    ) -> bool:
        """
        Apply combination of vintage film effects.

        Args:
            strip: Blender video strip object
            beats: List of beat times in seconds
            duration_frames: Total duration in frames
            fps: Frames per second
            effects_config: Configuration for effects intensity

        Returns:
            bool: True if effects were applied successfully
        """
        if not effects_config:
            effects_config = {
                "camera_shake": {"enabled": True, "intensity": 2.0},
                "film_jitter": {"enabled": True, "intensity": 0.5},
                "brightness_flicker": {"enabled": True, "amount": 0.1},
                "rotation_wobble": {"enabled": True, "degrees": 0.5},
                "black_white": {"enabled": True, "intensity": 0.6},
                "film_grain": {"enabled": True, "intensity": 0.15},
                "vintage_grade": {"enabled": True, "sepia": 0.01, "contrast": 0.5},
            }

        print(f"=== Applying vintage film effects to {strip.name} ===")

        success = True

        # Apply camera shake on beats
        if effects_config.get("camera_shake", {}).get("enabled", False):
            success &= self.apply_camera_shake(
                strip, beats, fps, effects_config["camera_shake"]["intensity"]
            )

        # Apply continuous film jitter
        if effects_config.get("film_jitter", {}).get("enabled", False):
            success &= self.apply_film_jitter(
                strip, duration_frames, fps, effects_config["film_jitter"]["intensity"]
            )

        # Apply brightness flicker on beats
        if effects_config.get("brightness_flicker", {}).get("enabled", False):
            success &= self.apply_brightness_flicker(
                strip, beats, fps, effects_config["brightness_flicker"]["amount"]
            )

        # Apply rotation wobble on beats
        if effects_config.get("rotation_wobble", {}).get("enabled", False):
            success &= self.apply_rotation_wobble(
                strip, beats, fps, effects_config["rotation_wobble"]["degrees"]
            )

        # Apply black and white effect
        if effects_config.get("black_white", {}).get("enabled", False):
            success &= self.apply_black_white_effect(
                strip, effects_config["black_white"]["intensity"]
            )

        # Apply film grain noise
        if effects_config.get("film_grain", {}).get("enabled", False):
            success &= self.apply_film_grain_noise(
                strip, effects_config["film_grain"]["intensity"]
            )

        # Apply vintage color grading
        if effects_config.get("vintage_grade", {}).get("enabled", False):
            success &= self.apply_vintage_color_grade(
                strip,
                effects_config["vintage_grade"]["sepia"],
                effects_config["vintage_grade"]["contrast"],
            )

        if success:
            print(f"✓ Vintage film effects applied successfully to {strip.name}")
        else:
            print(f"✗ Some vintage film effects failed for {strip.name}")

        return success

    def apply_black_white_effect(self, strip, intensity: float = 0.8) -> bool:
        """
        Apply black and white desaturation effect.

        Args:
            strip: Blender video strip object
            intensity: Desaturation intensity (0.0 = color, 1.0 = full B&W)

        Returns:
            bool: True if effect was applied successfully
        """
        print(f"  Applying B&W effect to {strip.name} (intensity: {intensity})")

        # Configure black white animation with specified intensity
        self.black_white_animation.intensity = intensity

        # Delegate to BlackWhiteAnimation
        return self.black_white_animation.apply_to_strip(strip, [], 0)

    def apply_film_grain_noise(self, strip, noise_intensity: float = 0.1) -> bool:
        """
        Apply film grain noise effect.

        Args:
            strip: Blender video strip object
            noise_intensity: Noise intensity (0.0 to 1.0)

        Returns:
            bool: True if effect was applied successfully
        """
        print(f"  Applying film grain to {strip.name} (intensity: {noise_intensity})")

        # Configure film grain animation with specified intensity
        self.film_grain_animation.intensity = noise_intensity

        # Delegate to FilmGrainAnimation
        return self.film_grain_animation.apply_to_strip(strip, [], 0)

    def apply_vintage_color_grade(
        self, strip, sepia_amount: float = 0.3, contrast_boost: float = 0.2
    ) -> bool:
        """
        Apply vintage color grading (sepia tint, contrast).

        Args:
            strip: Blender video strip object
            sepia_amount: Sepia tint intensity (0.0 to 1.0)
            contrast_boost: Contrast boost amount (0.0 to 1.0)

        Returns:
            bool: True if effect was applied successfully
        """
        print(
            f"  Applying vintage color grade to {strip.name} (sepia: {sepia_amount}, contrast: {contrast_boost})"
        )

        # Configure vintage color grade animation with specified parameters
        self.vintage_color_grade_animation.sepia_amount = sepia_amount
        self.vintage_color_grade_animation.contrast_boost = contrast_boost

        # Delegate to VintageColorGradeAnimation
        return self.vintage_color_grade_animation.apply_to_strip(strip, [], 0)
