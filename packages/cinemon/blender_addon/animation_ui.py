# ABOUTME: UI management for animation controls and property groups in Blender addon
# ABOUTME: Handles dynamic animation parameter UI generation and validation

"""Animation UI controls and property management for Cinemon addon."""

from typing import List, Dict, Any, Optional
import copy

try:
    import bpy
    from bpy.types import PropertyGroup
    from bpy.props import StringProperty, FloatProperty, BoolProperty, EnumProperty
    
    # Make sure we can register the property group
    class MockBpy:
        class Utils:
            @staticmethod
            def register_class(cls):
                pass
            @staticmethod
            def unregister_class(cls):
                pass
        utils = Utils()
    
    # Ensure bpy.utils exists for registration
    if not hasattr(bpy, 'utils'):
        bpy.utils = MockBpy.Utils()
        
except ImportError:
    # For testing without Blender
    class PropertyGroup:
        pass
    
    def StringProperty(**kwargs):
        return kwargs.get('default', '')
    
    def FloatProperty(**kwargs):
        return kwargs.get('default', 0.0)
    
    def BoolProperty(**kwargs):
        return kwargs.get('default', False)
    
    def EnumProperty(**kwargs):
        return kwargs.get('default', '')
    
    class MockBpy:
        class Utils:
            @staticmethod
            def register_class(cls):
                pass
            @staticmethod
            def unregister_class(cls):
                pass
        utils = Utils()
    
    bpy = MockBpy()

try:
    from .strip_context import StripContextManager
except ImportError:
    # For direct module execution/testing
    from strip_context import StripContextManager


class AnimationPropertyGroup(PropertyGroup):
    """Property group for single animation configuration."""
    
    # Animation type dropdown
    animation_type: EnumProperty(
        name="Type",
        description="Type of animation",
        items=[
            ('scale', 'Scale', 'Scale animation on beats/bass'),
            ('shake', 'Shake', 'Position shake on energy peaks'),
            ('rotation', 'Rotation', 'Rotation animation on beats'),
            ('jitter', 'Jitter', 'Continuous random position changes'),
            ('brightness_flicker', 'Brightness Flicker', 'Brightness modulation'),
            ('vintage_color', 'Vintage Color', 'Sepia and vintage effects'),
            ('black_white', 'Black & White', 'Desaturation effects'),
            ('film_grain', 'Film Grain', 'Grain overlay effects')
        ],
        default='scale'
    )
    
    # Trigger dropdown
    trigger: EnumProperty(
        name="Trigger",
        description="What triggers this animation",
        items=[
            ('beat', 'Beat', 'Trigger on beat events'),
            ('bass', 'Bass', 'Trigger on bass events'),
            ('energy_peaks', 'Energy Peaks', 'Trigger on energy peak events'),
            ('one_time', 'One Time', 'Apply once at start'),
            ('continuous', 'Continuous', 'Apply continuously')
        ],
        default='beat'
    )
    
    # Common parameters
    enabled: BoolProperty(
        name="Enabled",
        description="Enable this animation",
        default=True
    )
    
    intensity: FloatProperty(
        name="Intensity",
        description="Animation intensity",
        default=0.3,
        min=0.0,
        max=10.0
    )
    
    duration_frames: FloatProperty(
        name="Duration",
        description="Animation duration in frames",
        default=3.0,
        min=1.0,
        max=30.0
    )
    
    # Specific parameters for different animation types
    degrees: FloatProperty(
        name="Degrees",
        description="Rotation degrees (for rotation animation)",
        default=5.0,
        min=0.0,
        max=360.0
    )
    
    return_frames: FloatProperty(
        name="Return Frames",
        description="Frames to return to original position (for shake)",
        default=2.0,
        min=1.0,
        max=10.0
    )
    
    sepia_amount: FloatProperty(
        name="Sepia Amount",
        description="Amount of sepia effect (for vintage_color)",
        default=0.4,
        min=0.0,
        max=1.0
    )
    
    contrast_boost: FloatProperty(
        name="Contrast Boost",
        description="Contrast boost amount (for vintage_color)",
        default=0.3,
        min=0.0,
        max=2.0
    )
    
    grain_intensity: FloatProperty(
        name="Grain Intensity",
        description="Film grain intensity (for vintage_color/film_grain)",
        default=0.2,
        min=0.0,
        max=1.0
    )


class AnimationUIManager:
    """Manages animation UI controls and property groups."""
    
    def __init__(self):
        """Initialize animation UI manager."""
        self.context_manager = StripContextManager()
        
        # Map animation types to their specific parameters
        self.type_parameters = {
            'scale': ['intensity', 'duration_frames'],
            'shake': ['intensity', 'return_frames'],
            'rotation': ['degrees', 'duration_frames'],
            'jitter': ['intensity'],
            'brightness_flicker': ['intensity', 'duration_frames'],
            'vintage_color': ['sepia_amount', 'contrast_boost', 'grain_intensity'],
            'black_white': ['intensity'],
            'film_grain': ['grain_intensity']
        }
    
    def populate_from_animations(self, scene, animations: List[Dict[str, Any]]) -> None:
        """Populate UI property groups from animations list."""
        try:
            # Clear existing animations
            scene.cinemon_animations.clear()
            
            # Add each animation as property group
            for anim_data in animations:
                anim_prop = scene.cinemon_animations.add()
                
                # Set basic properties
                anim_prop.animation_type = anim_data.get('type', 'scale')
                anim_prop.trigger = anim_data.get('trigger', 'beat')
                anim_prop.enabled = anim_data.get('enabled', True)
                
                # Set parameters based on animation type
                self._set_animation_parameters(anim_prop, anim_data)
                
        except AttributeError:
            # For testing when scene properties don't exist
            pass
    
    def _set_animation_parameters(self, anim_prop, anim_data: Dict[str, Any]) -> None:
        """Set animation-specific parameters on property group."""
        # Common parameters
        if 'intensity' in anim_data:
            anim_prop.intensity = anim_data['intensity']
        if 'duration_frames' in anim_data:
            anim_prop.duration_frames = anim_data['duration_frames']
        
        # Type-specific parameters
        if 'degrees' in anim_data:
            anim_prop.degrees = anim_data['degrees']
        if 'return_frames' in anim_data:
            anim_prop.return_frames = anim_data['return_frames']
        if 'sepia_amount' in anim_data:
            anim_prop.sepia_amount = anim_data['sepia_amount']
        if 'contrast_boost' in anim_data:
            anim_prop.contrast_boost = anim_data['contrast_boost']
        if 'grain_intensity' in anim_data:
            anim_prop.grain_intensity = anim_data['grain_intensity']
    
    def extract_animations_from_ui(self, scene) -> List[Dict[str, Any]]:
        """Extract animations from UI property groups."""
        animations = []
        
        try:
            for anim_prop in scene.cinemon_animations:
                if not anim_prop.enabled:
                    continue  # Skip disabled animations
                
                anim_dict = {
                    'type': anim_prop.animation_type,
                    'trigger': anim_prop.trigger
                }
                
                # Add relevant parameters based on animation type
                self._extract_animation_parameters(anim_dict, anim_prop)
                
                animations.append(anim_dict)
                
        except AttributeError:
            # For testing when scene properties don't exist
            pass
        
        return animations
    
    def _extract_animation_parameters(self, anim_dict: Dict[str, Any], anim_prop) -> None:
        """Extract animation-specific parameters from property group."""
        anim_type = anim_dict['type']
        
        # Get relevant parameters for this animation type
        relevant_params = self.type_parameters.get(anim_type, [])
        
        # Always include intensity if it's used by this type
        if 'intensity' in relevant_params:
            anim_dict['intensity'] = anim_prop.intensity
        
        # Include other relevant parameters
        for param in relevant_params:
            if param != 'intensity':  # Already handled above
                if hasattr(anim_prop, param):
                    anim_dict[param] = getattr(anim_prop, param)
    
    def add_new_animation(self, scene, animation_type: str, trigger: str):
        """Add new animation to UI."""
        try:
            anim_prop = scene.cinemon_animations.add()
            anim_prop.animation_type = animation_type
            anim_prop.trigger = trigger
            anim_prop.enabled = True
            
            # Set default parameters
            defaults = self.context_manager.get_default_animation_parameters(animation_type)
            self._set_animation_parameters(anim_prop, defaults)
            
            return anim_prop
        except AttributeError:
            # For testing
            return None
    
    def remove_animation(self, scene, index: int) -> None:
        """Remove animation from UI."""
        try:
            scene.cinemon_animations.remove(index)
        except (AttributeError, IndexError):
            # For testing or invalid index
            pass
    
    def validate_animation_params(self, params: Dict[str, Any]) -> bool:
        """Validate animation parameters."""
        # Check required fields
        if 'type' not in params or 'trigger' not in params:
            return False
        
        # Check valid animation type
        valid_types = self.get_available_animation_types()
        if params['type'] not in valid_types:
            return False
        
        # Check valid trigger
        valid_triggers = self.get_available_triggers()
        if params['trigger'] not in valid_triggers:
            return False
        
        return True
    
    def get_parameter_defaults(self, animation_type: str) -> Dict[str, Any]:
        """Get default parameters for animation type."""
        return self.context_manager.get_default_animation_parameters(animation_type)
    
    def get_available_animation_types(self) -> List[str]:
        """Get available animation types."""
        return self.context_manager.get_available_animation_types()
    
    def get_available_triggers(self) -> List[str]:
        """Get available triggers."""
        return self.context_manager.get_available_triggers()
    
    def draw_animation_parameters(self, layout, anim_prop) -> None:
        """Draw animation parameters in UI layout."""
        try:
            # Get relevant parameters for this animation type
            anim_type = anim_prop.animation_type
            relevant_params = self.type_parameters.get(anim_type, [])
            
            # Draw relevant parameter controls
            for param in relevant_params:
                if hasattr(anim_prop, param):
                    layout.prop(anim_prop, param)
        except AttributeError:
            # For testing when layout doesn't exist
            pass


# Registration
classes = [
    AnimationPropertyGroup
]


def register():
    """Register animation UI classes."""
    try:
        for cls in classes:
            bpy.utils.register_class(cls)
        print("Animation UI registered successfully")
    except Exception as e:
        print(f"Animation UI registration error: {e}")


def unregister():
    """Unregister animation UI classes."""
    try:
        for cls in reversed(classes):
            bpy.utils.unregister_class(cls)
        print("Animation UI unregistered")
    except Exception as e:
        print(f"Animation UI unregistration error: {e}")


if __name__ == "__main__":
    register()