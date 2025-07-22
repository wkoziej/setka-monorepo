# ABOUTME: Animation applicators using events-based approach with moved VSE animations
# ABOUTME: Uses ScaleAnimation and ShakeAnimation from addon with audio timing events

"""Animation applicators using events-based approach for Cinemon VSE strips."""

from typing import Dict, Any, List
import traceback
import sys
from pathlib import Path

# Ensure addon path is available for imports
addon_path = Path(__file__).parent
if str(addon_path) not in sys.path:
    sys.path.insert(0, str(addon_path))

# Initialize animation classes to None first
ScaleAnimation = None
ShakeAnimation = None
VisibilityAnimation = None
RotationWobbleAnimation = None
JitterAnimation = None
BrightnessFlickerAnimation = None

# Try relative imports first (addon/GUI mode)
try:
    from .scale_animation import ScaleAnimation
    from .shake_animation import ShakeAnimation
    from .visibility_animation import VisibilityAnimation
    from .rotation_wobble_animation import RotationWobbleAnimation
    from .jitter_animation import JitterAnimation
    from .brightness_flicker_animation import BrightnessFlickerAnimation
    print(f"DEBUG: Successfully imported animation classes from relative imports")
    print(f"DEBUG: ScaleAnimation = {ScaleAnimation}")
    print(f"DEBUG: BrightnessFlickerAnimation = {BrightnessFlickerAnimation}")
except ImportError as e:
    print(f"DEBUG: Relative imports failed: {e}")
    
    # Try direct imports (background mode)
    try:
        import scale_animation
        import shake_animation
        import visibility_animation
        import rotation_wobble_animation
        import jitter_animation
        import brightness_flicker_animation
        
        ScaleAnimation = scale_animation.ScaleAnimation
        ShakeAnimation = shake_animation.ShakeAnimation
        VisibilityAnimation = visibility_animation.VisibilityAnimation
        RotationWobbleAnimation = rotation_wobble_animation.RotationWobbleAnimation
        JitterAnimation = jitter_animation.JitterAnimation
        BrightnessFlickerAnimation = brightness_flicker_animation.BrightnessFlickerAnimation
        
        print(f"DEBUG: Successfully imported animation classes from direct imports")
        print(f"DEBUG: ScaleAnimation = {ScaleAnimation}")
        print(f"DEBUG: BrightnessFlickerAnimation = {BrightnessFlickerAnimation}")
    except ImportError as e2:
        print(f"DEBUG: Direct imports also failed: {e2}")
        print(f"DEBUG: Current sys.path includes: {[p for p in sys.path if 'cinemon' in p]}")
        print(f"DEBUG: Addon path: {addon_path}")
        print(f"DEBUG: Files in addon path: {list(addon_path.glob('*_animation.py'))}")
        # Animation classes remain None


def apply_animation_to_strip(strip, animations: List[Dict[str, Any]], audio_events: Dict[str, Any], fps: int = 30) -> None:
    """Apply list of animations to a single strip using events-based approach.
    
    Args:
        strip: Blender video strip object
        animations: List of animation configurations
        audio_events: Dictionary containing animation events from audio analysis
        fps: Frames per second for timing conversion
    """
    try:
        print(f"\n=== Applying {len(animations)} animations to strip '{strip.name}' ===")
        
        # STEP 1: Clear existing animations
        print(f"Step 1: Clearing existing animations for '{strip.name}'...")
        clear_strip_animations(strip)
        
        # STEP 2: Apply new animations using events-based approach
        print(f"Step 2: Applying {len(animations)} new animations with events...")
        for i, animation in enumerate(animations, 1):
            anim_type = animation.get('type')
            trigger = animation.get('trigger', 'beat')
            
            print(f"  {i}/{len(animations)}: {anim_type} (trigger: {trigger})")
            
            # Get events for this trigger
            events = extract_events_for_trigger(audio_events, trigger)
            if not events:
                print(f"    ⚠ No events found for trigger '{trigger}', skipping")
                continue
                
            print(f"    ✓ Found {len(events)} events for trigger '{trigger}'")
            
            # Apply animation based on type
            success = False
            if anim_type == 'scale':
                success = apply_scale_animation(strip, animation, events, fps)
            elif anim_type == 'shake':
                success = apply_shake_animation(strip, animation, events, fps)
            elif anim_type == 'visibility':
                success = apply_visibility_animation(strip, animation, events, fps)
            elif anim_type == 'rotation':
                success = apply_rotation_wobble_animation(strip, animation, events, fps)
            elif anim_type == 'jitter':
                success = apply_jitter_animation(strip, animation, events, fps)
            elif anim_type == 'brightness_flicker':
                success = apply_brightness_flicker_animation(strip, animation, events, fps)
            elif anim_type == 'contrast_flash':
                success = apply_contrast_flash_animation(strip, animation, events, fps)
            elif anim_type == 'desaturate_pulse':
                success = apply_desaturate_pulse_animation(strip, animation, events, fps)
            else:
                print(f"    ❌ Unknown animation type: {anim_type}")
            
            if success:
                print(f"    ✓ Applied {anim_type} animation successfully")
            else:
                print(f"    ❌ Failed to apply {anim_type} animation")
        
        print(f"=== Completed animations for strip '{strip.name}' ===\n")
                
    except Exception as e:
        print(f"❌ Error applying animations to strip '{strip.name}': {e}")
        traceback.print_exc()


def extract_events_for_trigger(audio_events: Dict[str, Any], trigger: str) -> List[float]:
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
        'beat': 'beats',
        'bass': 'energy_peaks',  # Map bass to energy_peaks 
        'energy_peaks': 'energy_peaks',
        'sections': 'sections'
    }
    
    event_key = trigger_mapping.get(trigger, trigger)
    events = audio_events.get(event_key, [])
    
    # Handle sections format (list of dicts with start/end)
    if event_key == 'sections' and isinstance(events, list) and events:
        if isinstance(events[0], dict):
            return [section.get('start', 0.0) for section in events]
    
    # Handle regular event lists (list of floats)
    if isinstance(events, list):
        return [float(event) for event in events if isinstance(event, (int, float))]
    
    return []


def apply_scale_animation(strip, animation: Dict[str, Any], events: List[float], fps: int) -> bool:
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
        # Import ScaleAnimation directly in function
        try:
            from .scale_animation import ScaleAnimation
        except ImportError:
            try:
                import scale_animation
                ScaleAnimation = scale_animation.ScaleAnimation
            except ImportError:
                print(f"    ScaleAnimation not available - skipping")
                return False
        
        print(f"    DEBUG: In apply_scale_animation, ScaleAnimation = {ScaleAnimation}")
        
        # Create ScaleAnimation instance from configuration
        scale_anim = ScaleAnimation(
            trigger=animation.get('trigger', 'bass'),
            intensity=animation.get('intensity', 0.3),
            duration_frames=animation.get('duration_frames', 2),
            target_strips=animation.get('target_strips', [])
        )
        
        # Check if animation should be applied to this strip
        if not scale_anim.should_apply_to_strip(strip):
            print(f"    Skipping scale animation - strip not in target list")
            return False
        
        # Apply animation with events
        return scale_anim.apply_to_strip(strip, events, fps)
        
    except Exception as e:
        print(f"Error in apply_scale_animation: {e}")
        traceback.print_exc()
        return False


def apply_shake_animation(strip, animation: Dict[str, Any], events: List[float], fps: int) -> bool:
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
        # Import ShakeAnimation directly in function
        try:
            from .shake_animation import ShakeAnimation
        except ImportError:
            try:
                import shake_animation
                ShakeAnimation = shake_animation.ShakeAnimation
            except ImportError:
                print(f"    ShakeAnimation not available - skipping")
                return False
        
        # Create ShakeAnimation instance from configuration
        shake_anim = ShakeAnimation(
            trigger=animation.get('trigger', 'beat'),
            intensity=animation.get('intensity', 5.0),
            return_frames=animation.get('return_frames', 2),
            random_direction=animation.get('random_direction', True),
            target_strips=animation.get('target_strips', [])
        )
        
        # Check if animation should be applied to this strip
        if not shake_anim.should_apply_to_strip(strip):
            print(f"    Skipping shake animation - strip not in target list")
            return False
        
        # Apply animation with events
        return shake_anim.apply_to_strip(strip, events, fps)
        
    except Exception as e:
        print(f"Error in apply_shake_animation: {e}")
        traceback.print_exc()
        return False


def apply_visibility_animation(strip, animation: Dict[str, Any], events: List[float], fps: int) -> bool:
    """Apply visibility animation using events-based approach.
    
    Args:
        strip: Blender video strip object
        animation: Animation configuration
        events: List of event times in seconds
        fps: Frames per second
        
    Returns:
        True if animation was applied successfully
    """
    global VisibilityAnimation
    try:
        if VisibilityAnimation is None:
            print(f"    VisibilityAnimation not available - skipping")
            return False
            
        # Create VisibilityAnimation instance from configuration
        visibility_anim = VisibilityAnimation(
            trigger=animation.get('trigger', 'beat'),
            pattern=animation.get('pattern', 'alternate'),
            duration_frames=animation.get('duration_frames', 10),
            target_strips=animation.get('target_strips', [])
        )
        
        # Check if animation should be applied to this strip
        if not visibility_anim.should_apply_to_strip(strip):
            print(f"    Skipping visibility animation - strip not in target list")
            return False
        
        # Apply animation with events
        return visibility_anim.apply_to_strip(strip, events, fps)
        
    except Exception as e:
        print(f"Error in apply_visibility_animation: {e}")
        traceback.print_exc()
        return False


def apply_rotation_wobble_animation(strip, animation: Dict[str, Any], events: List[float], fps: int) -> bool:
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
        # Import RotationWobbleAnimation directly in function
        try:
            from .rotation_wobble_animation import RotationWobbleAnimation
        except ImportError:
            try:
                import rotation_wobble_animation
                RotationWobbleAnimation = rotation_wobble_animation.RotationWobbleAnimation
            except ImportError:
                print(f"    RotationWobbleAnimation not available - skipping")
                return False
        
        # Create RotationWobbleAnimation instance from configuration
        rotation_anim = RotationWobbleAnimation(
            trigger=animation.get('trigger', 'beat'),
            wobble_degrees=animation.get('intensity', 5.0),  # Map intensity to wobble_degrees
            return_frames=animation.get('duration_frames', 3),
            oscillate=animation.get('oscillate', True),
            target_strips=animation.get('target_strips', [])
        )
        
        # Check if animation should be applied to this strip
        if not rotation_anim.should_apply_to_strip(strip):
            print(f"    Skipping rotation wobble animation - strip not in target list")
            return False
        
        # Apply animation with events
        return rotation_anim.apply_to_strip(strip, events, fps)
        
    except Exception as e:
        print(f"Error in apply_rotation_wobble_animation: {e}")
        traceback.print_exc()
        return False


def apply_jitter_animation(strip, animation: Dict[str, Any], events: List[float], fps: int) -> bool:
    """Apply jitter animation using events-based approach.
    
    Args:
        strip: Blender video strip object
        animation: Animation configuration
        events: List of event times in seconds (ignored for continuous effect)
        fps: Frames per second
        
    Returns:
        True if animation was applied successfully
    """
    global JitterAnimation
    try:
        if JitterAnimation is None:
            print(f"    JitterAnimation not available - skipping")
            return False
            
        # Create JitterAnimation instance from configuration
        jitter_anim = JitterAnimation(
            trigger=animation.get('trigger', 'continuous'),
            intensity=animation.get('intensity', 2.0),
            min_interval=animation.get('min_interval', 3),
            max_interval=animation.get('max_interval', 8),
            target_strips=animation.get('target_strips', [])
        )
        
        # Check if animation should be applied to this strip
        if not jitter_anim.should_apply_to_strip(strip):
            print(f"    Skipping jitter animation - strip not in target list")
            return False
        
        # Apply animation with events (jitter is continuous, so events are ignored)
        return jitter_anim.apply_to_strip(strip, events, fps)
        
    except Exception as e:
        print(f"Error in apply_jitter_animation: {e}")
        traceback.print_exc()
        return False


def apply_brightness_flicker_animation(strip, animation: Dict[str, Any], events: List[float], fps: int) -> bool:
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
        # Import BrightnessFlickerAnimation directly in function
        try:
            from .brightness_flicker_animation import BrightnessFlickerAnimation
        except ImportError:
            try:
                import brightness_flicker_animation
                BrightnessFlickerAnimation = brightness_flicker_animation.BrightnessFlickerAnimation
            except ImportError:
                print(f"    BrightnessFlickerAnimation not available - skipping")
                return False
        
        print(f"    DEBUG: In apply_brightness_flicker_animation, BrightnessFlickerAnimation = {BrightnessFlickerAnimation}")
        
        # Create BrightnessFlickerAnimation instance from configuration
        flicker_anim = BrightnessFlickerAnimation(
            trigger=animation.get('trigger', 'beat'),
            intensity=animation.get('intensity', 0.1),
            duration_frames=animation.get('duration_frames', 2),
            target_strips=animation.get('target_strips', [])
        )
        
        # Check if animation should be applied to this strip
        if not flicker_anim.should_apply_to_strip(strip):
            print(f"    Skipping brightness flicker animation - strip not in target list")
            return False
        
        # Apply animation with events
        return flicker_anim.apply_to_strip(strip, events, fps)
        
    except Exception as e:
        print(f"Error in apply_brightness_flicker_animation: {e}")
        traceback.print_exc()
        return False


def apply_contrast_flash_animation(strip, animation: Dict[str, Any], events: List[float], fps: int) -> bool:
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
        # Import BrightnessFlickerAnimation directly in function
        try:
            from .brightness_flicker_animation import BrightnessFlickerAnimation
        except ImportError:
            try:
                import brightness_flicker_animation
                BrightnessFlickerAnimation = brightness_flicker_animation.BrightnessFlickerAnimation
            except ImportError:
                print(f"    BrightnessFlickerAnimation not available - skipping")
                return False
        
        # Create BrightnessFlickerAnimation instance from configuration (for contrast flash)
        flicker_anim = BrightnessFlickerAnimation(
            trigger=animation.get('trigger', 'beat'),
            intensity=animation.get('intensity', 0.25), # Use a default intensity for contrast flash
            duration_frames=animation.get('duration_frames', 2),
            target_strips=animation.get('target_strips', [])
        )
        
        # Check if animation should be applied to this strip
        if not flicker_anim.should_apply_to_strip(strip):
            print(f"    Skipping contrast flash animation - strip not in target list")
            return False
        
        # Apply animation with events
        return flicker_anim.apply_to_strip(strip, events, fps)
        
    except Exception as e:
        print(f"Error in apply_contrast_flash_animation: {e}")
        traceback.print_exc()
        return False


def apply_desaturate_pulse_animation(strip, animation: Dict[str, Any], events: List[float], fps: int) -> bool:
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
        # Import BrightnessFlickerAnimation directly in function
        try:
            from .brightness_flicker_animation import BrightnessFlickerAnimation
        except ImportError:
            try:
                import brightness_flicker_animation
                BrightnessFlickerAnimation = brightness_flicker_animation.BrightnessFlickerAnimation
            except ImportError:
                print(f"    BrightnessFlickerAnimation not available - skipping")
                return False
        
        # Create BrightnessFlickerAnimation instance from configuration (for desaturate pulse)
        flicker_anim = BrightnessFlickerAnimation(
            trigger=animation.get('trigger', 'beat'),
            intensity=animation.get('intensity', 0.3), # Use a default intensity for desaturate pulse
            duration_frames=animation.get('duration_frames', 3),
            target_strips=animation.get('target_strips', [])
        )
        
        # Check if animation should be applied to this strip
        if not flicker_anim.should_apply_to_strip(strip):
            print(f"    Skipping desaturate pulse animation - strip not in target list")
            return False
        
        # Apply animation with events
        return flicker_anim.apply_to_strip(strip, events, fps)
        
    except Exception as e:
        print(f"Error in apply_desaturate_pulse_animation: {e}")
        traceback.print_exc()
        return False


def clear_strip_animations(strip) -> None:
    """Clear ALL animation keyframes for a strip - aggressive approach."""
    try:
        cleared_items = []
        
        # 1. Clear keyframes for strip (if it has animation_data)
        keyframes_cleared = 0
        if hasattr(strip, 'animation_data') and strip.animation_data:
            strip.animation_data_clear()
            keyframes_cleared = 1
        
        if keyframes_cleared > 0:
            cleared_items.append("strip keyframes")
        
        # 2. Clear keyframes for strip transform (if it has animation_data)
        if hasattr(strip, 'transform'):
            try:
                if hasattr(strip.transform, 'animation_data') and strip.transform.animation_data:
                    strip.transform.animation_data_clear()
                    cleared_items.append("transform keyframes")
            except AttributeError:
                # StripTransform doesn't have animation_data in Blender 4.5
                pass
        
        # 3. Clear ALL modifiers added by Cinemon (they might have keyframes too)
        cinemon_modifier_names = [
            "Brightness Flicker", "Color Effect", "Desaturate Pulse", "Contrast Flash"
        ]
        
        modifiers_to_remove = []
        for modifier in strip.modifiers:
            if modifier.name in cinemon_modifier_names:
                modifiers_to_remove.append(modifier)
        
        for modifier in modifiers_to_remove:
            modifier_name = modifier.name  # Get name before removing
            strip.modifiers.remove(modifier)
            cleared_items.append(f"modifier '{modifier_name}'")
        
        if cleared_items:
            print(f"Cleared for strip '{strip.name}': {', '.join(cleared_items)}")
        else:
            print(f"No animations to clear for strip '{strip.name}'")
                
    except Exception as e:
        print(f"Error clearing animations for strip '{strip.name}': {e}")
        traceback.print_exc()