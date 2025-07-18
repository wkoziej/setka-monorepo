# ABOUTME: CompositionalAnimator - integrates compositional animation system with AnimationEngine
# ABOUTME: Parses environment variables to configure layouts and animations dynamically

"""Compositional animator for AnimationEngine integration."""

import os
from typing import List, Dict

from ..animation_compositor import AnimationCompositor
from ..layouts import RandomLayout
from ..animations import (
    ScaleAnimation, ShakeAnimation, RotationWobbleAnimation,
    JitterAnimation, BrightnessFlickerAnimation,
    BlackWhiteAnimation, FilmGrainAnimation, VintageColorGradeAnimation
)


class CompositionalAnimator:
    """
    Animator that uses the compositional animation system.
    
    This animator integrates the new layout + animation architecture
    with the existing AnimationEngine system. It reads configuration
    from environment variables and creates appropriate composers.
    
    Environment variables:
    - BLENDER_VSE_LAYOUT_TYPE: "random" (more types can be added)
    - BLENDER_VSE_LAYOUT_CONFIG: "overlap_allowed=false,seed=42,margin=0.1"
    - BLENDER_VSE_ANIMATION_CONFIG: "scale:bass:0.3:2,shake:beat:10.0:2"
    """
    
    def __init__(self):
        """Initialize CompositionalAnimator."""
        self.compositor = None
    
    def get_animation_mode(self) -> str:
        """
        Get the animation mode this animator handles.
        
        Returns:
            Animation mode identifier
        """
        return "compositional"
    
    def can_handle(self, animation_mode: str) -> bool:
        """
        Check if this animator can handle the specified animation mode.
        
        Args:
            animation_mode: Animation mode to check
            
        Returns:
            True if this animator can handle the mode
        """
        return animation_mode == "compositional"
    
    def animate(self, video_strips: List, animation_data: Dict, fps: int) -> bool:
        """
        Apply compositional animation to video strips.
        
        Args:
            video_strips: List of video strips from Blender VSE
            animation_data: Animation data containing events
            fps: Frames per second for frame calculation
            
        Returns:
            True if animation was applied successfully
        """
        if not video_strips:
            return True  # Nothing to animate
        
        # Create or get compositor
        if self.compositor is None:
            self.compositor = self._create_compositor()
        
        # Apply layout and animations
        return self.compositor.apply(video_strips, animation_data, fps)
    
    def _create_compositor(self) -> AnimationCompositor:
        """
        Create AnimationCompositor from environment variables.
        
        Returns:
            Configured AnimationCompositor instance
        """
        # Parse layout configuration
        layout_type = os.getenv("BLENDER_VSE_LAYOUT_TYPE", "random")
        layout_config = os.getenv("BLENDER_VSE_LAYOUT_CONFIG", "")
        layout = self._parse_layout_config(layout_type, layout_config)
        
        # Parse animation configuration
        animation_config = os.getenv("BLENDER_VSE_ANIMATION_CONFIG", "")
        animations = self._parse_animation_config(animation_config)
        
        return AnimationCompositor(layout, animations)
    
    def _parse_layout_config(self, layout_type: str, config: str):
        """
        Parse layout configuration from string.
        
        Args:
            layout_type: Type of layout ("random", etc.)
            config: Configuration string (key=value,key=value)
            
        Returns:
            Layout instance
        """
        # Parse config string into dict
        config_dict = {}
        if config:
            for pair in config.split(','):
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Convert value to appropriate type
                    if value.lower() == 'true':
                        config_dict[key] = True
                    elif value.lower() == 'false':
                        config_dict[key] = False
                    elif value.replace('.', '').replace('-', '').isdigit():
                        config_dict[key] = float(value) if '.' in value else int(value)
                    else:
                        config_dict[key] = value
        
        # Create layout based on type
        if layout_type == "random":
            return RandomLayout(
                overlap_allowed=config_dict.get('overlap_allowed', True),
                margin=config_dict.get('margin', 0.05),
                min_scale=config_dict.get('min_scale', 0.3),
                max_scale=config_dict.get('max_scale', 0.8),
                seed=config_dict.get('seed', None)
            )
        else:
            # Default to random layout
            return RandomLayout()
    
    def _parse_animation_config(self, config: str) -> List:
        """
        Parse animation configuration from string.
        
        Args:
            config: Configuration string (type:trigger:param1:param2,...)
            
        Returns:
            List of animation instances
        """
        animations = []
        
        if not config:
            return animations
        
        for anim_config in config.split(','):
            anim_config = anim_config.strip()
            if not anim_config:
                continue
                
            parts = anim_config.split(':')
            if len(parts) < 2:
                continue  # Invalid format
            
            anim_type = parts[0].strip()
            trigger = parts[1].strip()
            
            # Parse parameters
            params = []
            for i in range(2, len(parts)):
                param = parts[i].strip()
                if param.replace('.', '').replace('-', '').isdigit():
                    params.append(float(param) if '.' in param else int(param))
                else:
                    params.append(param)
            
            # Create animation based on type
            if anim_type == "scale":
                intensity = params[0] if len(params) > 0 else 0.3
                duration_frames = params[1] if len(params) > 1 else 2
                animation = ScaleAnimation(
                    trigger=trigger,
                    intensity=intensity,
                    duration_frames=duration_frames
                )
                animations.append(animation)
                
            elif anim_type == "shake":
                intensity = params[0] if len(params) > 0 else 10.0
                return_frames = params[1] if len(params) > 1 else 2
                animation = ShakeAnimation(
                    trigger=trigger,
                    intensity=intensity,
                    return_frames=return_frames
                )
                animations.append(animation)
                
            elif anim_type == "rotation":
                wobble_degrees = params[0] if len(params) > 0 else 1.0
                return_frames = params[1] if len(params) > 1 else 3
                animation = RotationWobbleAnimation(
                    trigger=trigger,
                    wobble_degrees=wobble_degrees,
                    return_frames=return_frames
                )
                animations.append(animation)
                
            elif anim_type == "jitter":
                intensity = params[0] if len(params) > 0 else 2.0
                min_interval = params[1] if len(params) > 1 else 3
                max_interval = params[2] if len(params) > 2 else 8
                animation = JitterAnimation(
                    trigger=trigger,
                    intensity=intensity,
                    min_interval=min_interval,
                    max_interval=max_interval
                )
                animations.append(animation)
                
            elif anim_type == "brightness_flicker":
                intensity = params[0] if len(params) > 0 else 0.15
                return_frames = params[1] if len(params) > 1 else 1
                animation = BrightnessFlickerAnimation(
                    trigger=trigger,
                    intensity=intensity,
                    return_frames=return_frames
                )
                animations.append(animation)
                
            elif anim_type == "black_white":
                intensity = params[0] if len(params) > 0 else 0.8
                animation = BlackWhiteAnimation(
                    trigger=trigger,
                    intensity=intensity
                )
                animations.append(animation)
                
            elif anim_type == "film_grain":
                intensity = params[0] if len(params) > 0 else 0.1
                animation = FilmGrainAnimation(
                    trigger=trigger,
                    intensity=intensity
                )
                animations.append(animation)
                
            elif anim_type == "vintage_color":
                sepia_amount = params[0] if len(params) > 0 else 0.3
                contrast_boost = params[1] if len(params) > 1 else 0.2
                animation = VintageColorGradeAnimation(
                    trigger=trigger,
                    sepia_amount=sepia_amount,
                    contrast_boost=contrast_boost
                )
                animations.append(animation)
        
        return animations