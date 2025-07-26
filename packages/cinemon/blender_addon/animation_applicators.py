# ABOUTME: Animation applicators using events-based approach with moved VSE animations
# ABOUTME: Uses ScaleAnimation and ShakeAnimation from addon with audio timing events

"""Animation applicators using events-based approach for Cinemon VSE strips."""

import importlib
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List

# Ensure addon path is available for imports
addon_path = Path(__file__).parent
if str(addon_path) not in sys.path:
    sys.path.insert(0, str(addon_path))

# Initialize animation classes to None first (used only for debug import verification)
ScaleAnimation = None
ShakeAnimation = None
VisibilityAnimation = None
RotationWobbleAnimation = None
JitterAnimation = None
BrightnessFlickerAnimation = None

# Try relative imports first (addon/GUI mode)
try:
    from .brightness_flicker_animation import BrightnessFlickerAnimation
    from .jitter_animation import JitterAnimation
    from .rotation_wobble_animation import RotationWobbleAnimation
    from .scale_animation import ScaleAnimation
    from .shake_animation import ShakeAnimation
    from .visibility_animation import VisibilityAnimation

    print("DEBUG: Successfully imported animation classes from relative imports")
    print(f"DEBUG: ScaleAnimation = {ScaleAnimation}")
    print(f"DEBUG: BrightnessFlickerAnimation = {BrightnessFlickerAnimation}")
except ImportError as e:
    print(f"DEBUG: Relative imports failed: {e}")

    # Try direct imports (background mode)
    try:
        import brightness_flicker_animation
        import jitter_animation
        import rotation_wobble_animation
        import scale_animation
        import shake_animation
        import visibility_animation

        ScaleAnimation = scale_animation.ScaleAnimation
        ShakeAnimation = shake_animation.ShakeAnimation
        VisibilityAnimation = visibility_animation.VisibilityAnimation
        RotationWobbleAnimation = rotation_wobble_animation.RotationWobbleAnimation
        JitterAnimation = jitter_animation.JitterAnimation
        BrightnessFlickerAnimation = (
            brightness_flicker_animation.BrightnessFlickerAnimation
        )

        print("DEBUG: Successfully imported animation classes from direct imports")
        print(f"DEBUG: ScaleAnimation = {ScaleAnimation}")
        print(f"DEBUG: BrightnessFlickerAnimation = {BrightnessFlickerAnimation}")
    except ImportError as e2:
        print(f"DEBUG: Direct imports also failed: {e2}")
        print(
            f"DEBUG: Current sys.path includes: {[p for p in sys.path if 'cinemon' in p]}"
        )
        print(f"DEBUG: Addon path: {addon_path}")
        print(f"DEBUG: Files in addon path: {list(addon_path.glob('*_animation.py'))}")
        # Animation classes remain None


def safe_import_animation(animation_module_name: str, animation_class_name: str):
    """Try to import animation class with fallback patterns.

    Args:
        animation_module_name: Module name (e.g., 'visibility_animation')
        animation_class_name: Class name (e.g., 'VisibilityAnimation')

    Returns:
        Animation class or None if import failed
    """
    try:
        # Try relative import first (addon/GUI mode)
        module = importlib.import_module(f".{animation_module_name}", package=__name__)
        return getattr(module, animation_class_name)
    except ImportError:
        try:
            # Try direct import (background mode)
            module = importlib.import_module(animation_module_name)
            return getattr(module, animation_class_name)
        except ImportError:
            return None


def apply_animation_to_strip(
    strip, animations: List[Dict[str, Any]], audio_events: Dict[str, Any], fps: int = 30
) -> None:
    """Apply list of animations to a single strip using events-based approach.

    Args:
        strip: Blender video strip object
        animations: List of animation configurations
        audio_events: Dictionary containing animation events from audio analysis
        fps: Frames per second for timing conversion
    """
    try:
        print(
            f"\n=== Applying {len(animations)} animations to strip '{strip.name}' ==="
        )

        # STEP 1: Clear existing animations
        print(f"Step 1: Clearing existing animations for '{strip.name}'...")
        clear_strip_animations(strip)

        # STEP 2: Apply new animations using events-based approach
        print(f"Step 2: Applying {len(animations)} new animations with events...")
        for i, animation in enumerate(animations, 1):
            anim_type = animation.get("type")
            trigger = animation.get("trigger", "beat")

            print(f"  {i}/{len(animations)}: {anim_type} (trigger: {trigger})")

            # Get events for this trigger
            events = extract_events_for_trigger(audio_events, trigger)
            if not events:
                print(f"    ⚠ No events found for trigger '{trigger}', skipping")
                continue

            print(f"    ✓ Found {len(events)} events for trigger '{trigger}'")

            # Apply animation based on type
            success = False
            print(
                f"    DEBUG: Applying {anim_type} animation with {len(events)} events..."
            )
            if anim_type == "scale":
                success = apply_scale_animation(strip, animation, events, fps)
            elif anim_type == "shake":
                success = apply_shake_animation(strip, animation, events, fps)
            elif anim_type == "visibility":
                success = apply_visibility_animation(strip, animation, events, fps)
            elif anim_type == "rotation_wobble":
                success = apply_rotation_wobble_animation(strip, animation, events, fps)
            elif anim_type == "jitter":
                success = apply_jitter_animation(strip, animation, events, fps)
            elif anim_type == "brightness_flicker":
                success = apply_brightness_flicker_animation(
                    strip, animation, events, fps
                )
            elif anim_type == "contrast_flash":
                success = apply_contrast_flash_animation(strip, animation, events, fps)
            elif anim_type == "desaturate_pulse":
                success = apply_desaturate_pulse_animation(
                    strip, animation, events, fps
                )
            else:
                print(f"    ERROR: Unknown animation type '{anim_type}'")
                continue

            if success:
                print(f"    ✓ {anim_type} animation applied successfully")
            else:
                print(f"    ✗ {anim_type} animation FAILED to apply")

        print(f"=== Completed animations for strip '{strip.name}' ===\n")

    except Exception as e:
        print(f"❌ Error applying animations to strip '{strip.name}': {e}")
        traceback.print_exc()


def extract_events_for_trigger(
    audio_events: Dict[str, Any], trigger: str
) -> List[float]:
    """Extract event times from audio analysis for given trigger.

    Args:
        audio_events: Dictionary containing animation events from audio analysis
        trigger: Event type ("beat", "bass", "energy_peaks", etc.)

    Returns:
        List of event times in seconds
    """
    if not isinstance(audio_events, dict):
        return []

    # Map triggers to audio event types
    trigger_mapping = {
        "beat": "beats",
        "bass": "energy_peaks",  # Map bass to energy_peaks
        "energy_peaks": "energy_peaks",
        "sections": "sections",
    }

    event_key = trigger_mapping.get(trigger, trigger)
    events = audio_events.get(event_key, [])

    # Handle sections format (list of dicts with start/end)
    if event_key == "sections" and isinstance(events, list) and events:
        if isinstance(events[0], dict):
            return [section.get("start", 0.0) for section in events]

    # Handle regular event lists (list of floats)
    if isinstance(events, list):
        return [float(event) for event in events if isinstance(event, (int, float))]

    return []


def apply_scale_animation(
    strip, animation: Dict[str, Any], events: List[float], fps: int
) -> bool:
    """Apply scale animation using events-based approach.

    Args:
        strip: Blender video strip object
        animation: Animation configuration
        events: List of event times in seconds
        fps: Frames per second

    Returns:
        True if animation was applied successfully
    """
    try:
        # Import ScaleAnimation using helper function
        ScaleAnimation = safe_import_animation("scale_animation", "ScaleAnimation")
        if ScaleAnimation is None:
            print("    ScaleAnimation not available - skipping")
            return False

        print(f"    DEBUG: In apply_scale_animation, ScaleAnimation = {ScaleAnimation}")

        # Create ScaleAnimation instance from configuration
        scale_anim = ScaleAnimation(
            trigger=animation.get("trigger", "bass"),
            intensity=animation.get("intensity", 0.3),
            duration_frames=animation.get("duration_frames", 2),
            target_strips=animation.get("target_strips", []),
        )

        # Check if animation should be applied to this strip
        if not scale_anim.should_apply_to_strip(strip):
            print("    Skipping scale animation - strip not in target list")
            return False

        # Apply animation with events
        return scale_anim.apply_to_strip(strip, events, fps)

    except Exception as e:
        print(f"Error in apply_scale_animation: {e}")
        traceback.print_exc()
        return False


def apply_shake_animation(
    strip, animation: Dict[str, Any], events: List[float], fps: int
) -> bool:
    """Apply shake animation using events-based approach.

    Args:
        strip: Blender video strip object
        animation: Animation configuration
        events: List of event times in seconds
        fps: Frames per second

    Returns:
        True if animation was applied successfully
    """
    try:
        # Import ShakeAnimation using helper function
        ShakeAnimation = safe_import_animation("shake_animation", "ShakeAnimation")
        if ShakeAnimation is None:
            print("    ShakeAnimation not available - skipping")
            return False

        # Create ShakeAnimation instance from configuration
        shake_anim = ShakeAnimation(
            trigger=animation.get("trigger", "beat"),
            intensity=animation.get("intensity", 5.0),
            return_frames=animation.get("return_frames", 2),
            random_direction=animation.get("random_direction", True),
            target_strips=animation.get("target_strips", []),
        )

        # Check if animation should be applied to this strip
        if not shake_anim.should_apply_to_strip(strip):
            print("    Skipping shake animation - strip not in target list")
            return False

        # Apply animation with events
        return shake_anim.apply_to_strip(strip, events, fps)

    except Exception as e:
        print(f"Error in apply_shake_animation: {e}")
        traceback.print_exc()
        return False


def apply_visibility_animation(
    strip, animation: Dict[str, Any], events: List[float], fps: int
) -> bool:
    """Apply visibility animation using events-based approach.

    Args:
        strip: Blender video strip object
        animation: Animation configuration
        events: List of event times in seconds
        fps: Frames per second

    Returns:
        True if animation was applied successfully
    """
    try:
        # Import VisibilityAnimation using helper function
        VisibilityAnimation = safe_import_animation(
            "visibility_animation", "VisibilityAnimation"
        )
        if VisibilityAnimation is None:
            print("    VisibilityAnimation not available - skipping")
            return False

        # Create VisibilityAnimation instance from configuration
        visibility_anim = VisibilityAnimation(
            trigger=animation.get("trigger", "beat"),
            pattern=animation.get("pattern", "alternate"),
            duration_frames=animation.get("duration_frames", 10),
            target_strips=animation.get("target_strips", []),
        )

        # Check if animation should be applied to this strip
        if not visibility_anim.should_apply_to_strip(strip):
            print("    Skipping visibility animation - strip not in target list")
            return False

        # Apply animation with events
        return visibility_anim.apply_to_strip(strip, events, fps)

    except Exception as e:
        print(f"Error in apply_visibility_animation: {e}")
        traceback.print_exc()
        return False


def apply_rotation_wobble_animation(
    strip, animation: Dict[str, Any], events: List[float], fps: int
) -> bool:
    """Apply rotation wobble animation using events-based approach.

    Args:
        strip: Blender video strip object
        animation: Animation configuration
        events: List of event times in seconds
        fps: Frames per second

    Returns:
        True if animation was applied successfully
    """
    try:
        # Import RotationWobbleAnimation using helper function
        RotationWobbleAnimation = safe_import_animation(
            "rotation_wobble_animation", "RotationWobbleAnimation"
        )
        if RotationWobbleAnimation is None:
            print("    RotationWobbleAnimation not available - skipping")
            return False

        # Create RotationWobbleAnimation instance from configuration
        rotation_anim = RotationWobbleAnimation(
            trigger=animation.get("trigger", "beat"),
            wobble_degrees=animation.get(
                "intensity", 5.0
            ),  # Map intensity to wobble_degrees
            return_frames=animation.get("duration_frames", 3),
            oscillate=animation.get("oscillate", True),
            target_strips=animation.get("target_strips", []),
        )

        # Check if animation should be applied to this strip
        if not rotation_anim.should_apply_to_strip(strip):
            print("    Skipping rotation wobble animation - strip not in target list")
            return False

        # Apply animation with events
        return rotation_anim.apply_to_strip(strip, events, fps)

    except Exception as e:
        print(f"Error in apply_rotation_wobble_animation: {e}")
        traceback.print_exc()
        return False


def apply_jitter_animation(
    strip, animation: Dict[str, Any], events: List[float], fps: int
) -> bool:
    """Apply jitter animation using events-based approach.

    Args:
        strip: Blender video strip object
        animation: Animation configuration
        events: List of event times in seconds (ignored for continuous effect)
        fps: Frames per second

    Returns:
        True if animation was applied successfully
    """
    try:
        # Import JitterAnimation directly in function
        try:
            from .jitter_animation import JitterAnimation
        except ImportError:
            try:
                import jitter_animation

                JitterAnimation = jitter_animation.JitterAnimation
            except ImportError:
                print("    JitterAnimation not available - skipping")
                return False

        # Create JitterAnimation instance from configuration
        jitter_anim = JitterAnimation(
            trigger=animation.get("trigger", "continuous"),
            intensity=animation.get("intensity", 2.0),
            min_interval=animation.get("min_interval", 3),
            max_interval=animation.get("max_interval", 8),
            target_strips=animation.get("target_strips", []),
        )

        # Check if animation should be applied to this strip
        if not jitter_anim.should_apply_to_strip(strip):
            print("    Skipping jitter animation - strip not in target list")
            return False

        # Apply animation with events (jitter is continuous, so events are ignored)
        return jitter_anim.apply_to_strip(strip, events, fps)

    except Exception as e:
        print(f"Error in apply_jitter_animation: {e}")
        traceback.print_exc()
        return False


def apply_brightness_flicker_animation(
    strip, animation: Dict[str, Any], events: List[float], fps: int
) -> bool:
    """Apply brightness flicker animation using events-based approach.

    Args:
        strip: Blender video strip object
        animation: Animation configuration
        events: List of event times in seconds
        fps: Frames per second

    Returns:
        True if animation was applied successfully
    """
    try:
        # Import BrightnessFlickerAnimation using helper function
        BrightnessFlickerAnimation = safe_import_animation(
            "brightness_flicker_animation", "BrightnessFlickerAnimation"
        )
        if BrightnessFlickerAnimation is None:
            print("    BrightnessFlickerAnimation not available - skipping")
            return False

        print(
            f"    DEBUG: In apply_brightness_flicker_animation, BrightnessFlickerAnimation = {BrightnessFlickerAnimation}"
        )

        # Create BrightnessFlickerAnimation instance from configuration
        flicker_anim = BrightnessFlickerAnimation(
            trigger=animation.get("trigger", "beat"),
            intensity=animation.get("intensity", 0.1),
            duration_frames=animation.get("duration_frames", 2),
            target_strips=animation.get("target_strips", []),
        )

        # Check if animation should be applied to this strip
        if not flicker_anim.should_apply_to_strip(strip):
            print(
                "    Skipping brightness flicker animation - strip not in target list"
            )
            return False

        # Apply animation with events
        return flicker_anim.apply_to_strip(strip, events, fps)

    except Exception as e:
        print(f"Error in apply_brightness_flicker_animation: {e}")
        traceback.print_exc()
        return False


def apply_contrast_flash_animation(
    strip, animation: Dict[str, Any], events: List[float], fps: int
) -> bool:
    """Apply contrast flash animation using events-based approach.

    Args:
        strip: Blender video strip object
        animation: Animation configuration
        events: List of event times in seconds
        fps: Frames per second

    Returns:
        True if animation was applied successfully
    """
    try:
        # Import BrightnessFlickerAnimation using helper function (contrast flash uses BrightnessFlickerAnimation)
        BrightnessFlickerAnimation = safe_import_animation(
            "brightness_flicker_animation", "BrightnessFlickerAnimation"
        )
        if BrightnessFlickerAnimation is None:
            print("    BrightnessFlickerAnimation not available - skipping")
            return False

        # Create BrightnessFlickerAnimation instance from configuration (for contrast flash)
        flicker_anim = BrightnessFlickerAnimation(
            trigger=animation.get("trigger", "beat"),
            intensity=animation.get(
                "intensity", 0.25
            ),  # Use a default intensity for contrast flash
            duration_frames=animation.get("duration_frames", 2),
            target_strips=animation.get("target_strips", []),
        )

        # Check if animation should be applied to this strip
        if not flicker_anim.should_apply_to_strip(strip):
            print("    Skipping contrast flash animation - strip not in target list")
            return False

        # Apply animation with events
        return flicker_anim.apply_to_strip(strip, events, fps)

    except Exception as e:
        print(f"Error in apply_contrast_flash_animation: {e}")
        traceback.print_exc()
        return False


def apply_desaturate_pulse_animation(
    strip, animation: Dict[str, Any], events: List[float], fps: int
) -> bool:
    """Apply desaturate pulse animation using events-based approach.

    Args:
        strip: Blender video strip object
        animation: Animation configuration
        events: List of event times in seconds
        fps: Frames per second

    Returns:
        True if animation was applied successfully
    """
    try:
        # Import BrightnessFlickerAnimation using helper function (desaturate pulse uses BrightnessFlickerAnimation)
        BrightnessFlickerAnimation = safe_import_animation(
            "brightness_flicker_animation", "BrightnessFlickerAnimation"
        )
        if BrightnessFlickerAnimation is None:
            print("    BrightnessFlickerAnimation not available - skipping")
            return False

        # Create BrightnessFlickerAnimation instance from configuration (for desaturate pulse)
        flicker_anim = BrightnessFlickerAnimation(
            trigger=animation.get("trigger", "beat"),
            intensity=animation.get(
                "intensity", 0.3
            ),  # Use a default intensity for desaturate pulse
            duration_frames=animation.get("duration_frames", 3),
            target_strips=animation.get("target_strips", []),
        )

        # Check if animation should be applied to this strip
        if not flicker_anim.should_apply_to_strip(strip):
            print("    Skipping desaturate pulse animation - strip not in target list")
            return False

        # Apply animation with events
        return flicker_anim.apply_to_strip(strip, events, fps)

    except Exception as e:
        print(f"Error in apply_desaturate_pulse_animation: {e}")
        traceback.print_exc()
        return False


def clear_strip_animations(strip) -> None:
    """Clear ALL animation keyframes for a strip - uses KeyframeCleaner for comprehensive cleanup."""
    print(f"DEBUG: clear_strip_animations() called for strip '{strip.name}'")
    try:
        # Import KeyframeCleaner from keyframe_helper
        try:
            from .keyframe_helper import keyframe_cleaner
        except ImportError:
            # Direct import for background mode
            from keyframe_helper import keyframe_cleaner

        # Use the comprehensive cleaner that properly removes all fcurves and keyframes
        keyframe_cleaner.clear_all_strip_animations(strip)

    except Exception as e:
        print(f"Error clearing animations for strip '{strip.name}': {e}")
        traceback.print_exc()
