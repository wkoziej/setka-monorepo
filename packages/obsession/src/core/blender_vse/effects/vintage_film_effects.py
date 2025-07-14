"""
ABOUTME: Vintage film effects module for Blender VSE - adds old film style animations.
ABOUTME: Provides camera shake, jitter, flicker and wobble effects synchronized to audio beats.
"""

import random
import math
from typing import List, Dict

from ..keyframe_helper import KeyframeHelper


class VintageFilmEffects:
    """Applies vintage film effects to video strips in Blender VSE."""

    def __init__(self):
        """Initialize VintageFilmEffects with keyframe helper."""
        self.keyframe_helper = KeyframeHelper()

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
        if not hasattr(strip, "transform"):
            return False

        print(f"  Applying camera shake to {strip.name} (intensity: {intensity})")

        # Set initial position keyframe
        self.keyframe_helper.insert_transform_position_keyframes(strip.name, 1)

        for beat_time in beats:
            frame = int(beat_time * fps)

            # Random shake offsets
            shake_x = random.uniform(-intensity, intensity)
            shake_y = random.uniform(-intensity, intensity)

            # Apply shake at beat frame
            original_x = strip.transform.offset_x
            original_y = strip.transform.offset_y

            strip.transform.offset_x = original_x + shake_x
            strip.transform.offset_y = original_y + shake_y
            self.keyframe_helper.insert_transform_position_keyframes(strip.name, frame)

            # Return to original position (2 frames later)
            return_frame = frame + 2
            strip.transform.offset_x = original_x
            strip.transform.offset_y = original_y
            self.keyframe_helper.insert_transform_position_keyframes(
                strip.name, return_frame
            )

        return True

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
        if not hasattr(strip, "transform"):
            return False

        print(f"  Applying film jitter to {strip.name} (intensity: {jitter_intensity})")

        # Apply jitter every 3-8 frames (irregular timing like old film)
        current_frame = 1
        while current_frame < duration_frames:
            # Random small offsets
            jitter_x = random.uniform(-jitter_intensity, jitter_intensity)
            jitter_y = random.uniform(-jitter_intensity, jitter_intensity)

            # Apply jitter
            base_x = strip.transform.offset_x
            base_y = strip.transform.offset_y

            strip.transform.offset_x = base_x + jitter_x
            strip.transform.offset_y = base_y + jitter_y
            self.keyframe_helper.insert_transform_position_keyframes(
                strip.name, current_frame
            )

            # Next jitter in random interval (3-8 frames)
            current_frame += random.randint(3, 8)

        return True

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

        # Set initial brightness keyframe
        strip.blend_alpha = 1.0
        self.keyframe_helper.insert_blend_alpha_keyframe(strip.name, 1, 1.0)

        for beat_time in beats:
            frame = int(beat_time * fps)

            # Random flicker (dimmer)
            flicker_alpha = 1.0 - random.uniform(0, flicker_amount)

            # Apply flicker at beat
            strip.blend_alpha = flicker_alpha
            self.keyframe_helper.insert_blend_alpha_keyframe(
                strip.name, frame, flicker_alpha
            )

            # Return to normal brightness (1 frame later)
            return_frame = frame + 1
            strip.blend_alpha = 1.0
            self.keyframe_helper.insert_blend_alpha_keyframe(
                strip.name, return_frame, 1.0
            )

        return True

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
        if not hasattr(strip, "transform"):
            return False

        print(f"  Applying rotation wobble to {strip.name} (degrees: {wobble_degrees})")

        # Set initial rotation keyframe
        self.keyframe_helper.insert_transform_rotation_keyframe(strip.name, 1, 0.0)

        for beat_time in beats:
            frame = int(beat_time * fps)

            # Random wobble rotation
            wobble_rotation = random.uniform(-wobble_degrees, wobble_degrees)
            wobble_radians = math.radians(wobble_rotation)

            # Apply wobble
            strip.transform.rotation = wobble_radians
            self.keyframe_helper.insert_transform_rotation_keyframe(
                strip.name, frame, wobble_radians
            )

            # Return to normal rotation (3 frames later)
            return_frame = frame + 3
            strip.transform.rotation = 0.0
            self.keyframe_helper.insert_transform_rotation_keyframe(
                strip.name, return_frame, 0.0
            )

        return True

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
        try:
            print(f"  Applying B&W effect to {strip.name} (intensity: {intensity})")

            # Use strip's built-in color_saturation property for B&W effect
            # Setting saturation with controlled intensity for pure B&W at high values
            saturation = max(0.0, 1.0 - intensity * 1.2)
            strip.color_saturation = saturation

            return True

        except Exception as e:
            print(f"    Warning: Could not apply B&W effect to {strip.name}: {e}")
            return False

    def apply_film_grain_noise(self, strip, noise_intensity: float = 0.1) -> bool:
        """
        Apply film grain noise effect.

        Args:
            strip: Blender video strip object
            noise_intensity: Noise intensity (0.0 to 1.0)

        Returns:
            bool: True if effect was applied successfully
        """
        try:
            print(
                f"  Applying film grain to {strip.name} (intensity: {noise_intensity})"
            )

            # Add Gaussian Blur modifier with noise-like settings
            # Note: Blender VSE doesn't have direct noise modifier,
            # but we can simulate grain with subtle blur + contrast adjustments

            # First add a slight blur to soften the image (film-like)
            blur_modifier = strip.modifiers.new(
                name="Vintage_Grain_Blur", type="GAUSSIAN_BLUR"
            )
            blur_modifier.sigma_x = noise_intensity * 0.5
            blur_modifier.sigma_y = noise_intensity * 0.5

            # Add contrast/brightness adjustment for grain effect
            color_modifier = strip.modifiers.new(
                name="Vintage_Grain_Color", type="COLOR_BALANCE"
            )
            color_modifier.color_balance.gain = (
                1.0 + noise_intensity * 0.2,  # R
                1.0 + noise_intensity * 0.2,  # G
                1.0 + noise_intensity * 0.2,  # B
            )
            color_modifier.color_balance.gamma = (
                1.0 + noise_intensity * 0.1,  # R
                1.0 + noise_intensity * 0.1,  # G
                1.0 + noise_intensity * 0.1,  # B
            )

            return True

        except Exception as e:
            print(f"    Warning: Could not apply film grain to {strip.name}: {e}")
            return False

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
        try:
            print(
                f"  Applying vintage color grade to {strip.name} (sepia: {sepia_amount}, contrast: {contrast_boost})"
            )

            # Add color balance modifier for vintage look
            color_modifier = strip.modifiers.new(
                name="Vintage_Grade", type="COLOR_BALANCE"
            )

            # Sepia effect: warm highlights, cool shadows
            color_modifier.color_balance.lift = (
                1.0 - sepia_amount * 0.1,  # R (shadows slightly cooler)
                1.0 - sepia_amount * 0.05,  # G
                1.0 - sepia_amount * 0.2,  # B (remove blue from shadows)
            )

            color_modifier.color_balance.gamma = (
                1.0 + sepia_amount * 0.1,  # R (midtones warmer)
                1.0 + sepia_amount * 0.05,  # G
                1.0 - sepia_amount * 0.1,  # B (reduce blue in midtones)
            )

            color_modifier.color_balance.gain = (
                1.0 + sepia_amount * 0.2,  # R (highlights warm)
                1.0 + sepia_amount * 0.15,  # G
                1.0 - sepia_amount * 0.1,  # B (reduce blue in highlights)
            )

            # Increase contrast for vintage look
            color_modifier.color_balance.gamma = tuple(
                g * (1.0 + contrast_boost * 0.3)
                for g in color_modifier.color_balance.gamma
            )

            return True

        except Exception as e:
            print(
                f"    Warning: Could not apply vintage color grade to {strip.name}: {e}"
            )
            return False
