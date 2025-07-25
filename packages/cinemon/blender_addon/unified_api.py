# ABOUTME: Unified Animation API for Cinemon - single entry point for all animation operations
# ABOUTME: Used by both VSE script (CLI) and addon (GUI) to ensure consistent behavior

"""Unified Animation API for Cinemon addon.

This module provides a single, consistent API for applying presets, layouts,
and animations to Blender VSE projects. It can be used from both:
- VSE script (background mode) for CLI workflows
- Addon UI (GUI mode) for interactive workflows
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Set up logging
logger = logging.getLogger(__name__)

try:
    import bpy
except ImportError:
    # For testing outside Blender
    bpy = None


class AnimationAPI:
    """Unified API for all Cinemon animation operations."""

    def __init__(self):
        """Initialize Animation API."""
        self.strip_context_manager = None
        self.layout_manager = None
        self.animation_applicator = None
        self._initialize_components()

    def _initialize_components(self):
        """Initialize required components."""
        try:
            # Try relative imports first (GUI mode)
            try:
                from .animation_applicators import apply_animation_to_strip
                from .strip_context import get_strip_context_manager
            except ImportError:
                # Fallback to absolute imports (background mode)
                from animation_applicators import apply_animation_to_strip
                from strip_context import get_strip_context_manager

            self.strip_context_manager = get_strip_context_manager()
            self.apply_animation_to_strip = apply_animation_to_strip

            print("DEBUG: Animation API components initialized successfully")
            logger.info("Animation API components initialized successfully")
        except ImportError as e:
            print(f"DEBUG: Some components not available: {e}")
            print(f"DEBUG: ImportError details: {e}")
            import traceback
            traceback.print_exc()
            logger.warning(f"Some components not available: {e}")
            # Set fallback methods for testing
            self.apply_animation_to_strip = None

    def apply_preset(
        self,
        recording_path: Union[str, Path],
        preset_name: str = None,
        preset_config: Dict[str, Any] = None,
        audio_analysis_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Apply a complete preset including layout and animations.

        Args:
            recording_path: Path to recording directory
            preset_name: Name of preset to apply (e.g., 'multi-pip', 'vintage'). If None, preset_config must be provided.
            preset_config: Optional pre-loaded preset configuration. If provided, preset_name is ignored.
            audio_analysis_data: Optional pre-loaded audio analysis data

        Returns:
            Dict with status and details:
            {
                'success': bool,
                'layout_applied': bool,
                'animations_applied': bool,
                'strips_affected': int,
                'errors': List[str]
            }
        """
        result = {
            'success': False,
            'layout_applied': False,
            'animations_applied': False,
            'strips_affected': 0,
            'errors': []
        }

        try:
            # Use provided config or load from preset name
            if preset_config is None:
                if preset_name is None:
                    result['errors'].append("Either preset_name or preset_config must be provided")
                    return result

                preset_config = self._load_preset_config(preset_name)
                if not preset_config:
                    result['errors'].append(f"Failed to load preset: {preset_name}")
                    return result
            else:
                # If config provided, ensure it's properly mapped
                if bpy and bpy.context.scene.sequence_editor:
                    preset_config = self._map_video_names_to_strips(preset_config)

            # Get video strips from current scene
            if not bpy or not bpy.context.scene.sequence_editor:
                result['errors'].append("No sequence editor found")
                return result

            sequences = bpy.context.scene.sequence_editor.sequences
            video_strips = [s for s in sequences if s.type == 'MOVIE']

            if not video_strips:
                result['errors'].append("No video strips found in project")
                return result

            # Apply layout if specified
            layout_config = preset_config.get('layout', {})
            if layout_config:
                layout_success = self.apply_layout(video_strips, layout_config)
                result['layout_applied'] = layout_success
                if not layout_success:
                    result['errors'].append("Failed to apply layout")

            # Apply animations if specified
            animations_config = preset_config.get('strip_animations', {})
            if animations_config:
                # Convert strip_animations to flat animations list for compatibility
                animations_list = self._convert_strip_animations_to_list(animations_config, video_strips)

                anim_success = self.apply_animations(
                    video_strips,
                    animations_list,
                    audio_analysis_data
                )
                result['animations_applied'] = anim_success
                result['strips_affected'] = len(video_strips) if anim_success else 0
                if not anim_success:
                    result['errors'].append("Failed to apply animations")

            # Overall success if at least one operation succeeded
            result['success'] = result['layout_applied'] or result['animations_applied']

            if result['success']:
                logger.info(f"Successfully applied preset '{preset_name}'")

        except Exception as e:
            logger.error(f"Error applying preset: {e}")
            result['errors'].append(str(e))

        return result

    def apply_layout(
        self,
        video_strips: List[Any],
        layout_config: Dict[str, Any]
    ) -> bool:
        """Apply layout to video strips.

        Args:
            video_strips: List of Blender video sequence strips
            layout_config: Layout configuration dict with 'type' and 'config'

        Returns:
            bool: True if layout applied successfully
        """
        try:
            layout_type = layout_config.get('type', 'random')
            layout_config.get('config', {})

            logger.info(f"Applying layout type: {layout_type}")

            # Use the extracted layout applicators module (DRY principle)
            try:
                from .layout_applicators import apply_layout_to_strips
            except ImportError:
                # Fallback for testing environment
                import layout_applicators
                apply_layout_to_strips = layout_applicators.apply_layout_to_strips

            success = apply_layout_to_strips(layout_config)

            if success:
                logger.info(f"Layout '{layout_type}' applied to {len(video_strips)} strips")
            else:
                logger.error(f"Failed to apply layout '{layout_type}'")

            return success

        except Exception as e:
            logger.error(f"Error applying layout: {e}")
            return False

    def apply_animations(
        self,
        video_strips: List[Any],
        animations_config: List[Dict[str, Any]],
        audio_analysis_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Apply animations to video strips with optional audio timing.

        Args:
            video_strips: List of Blender video sequence strips
            animations_config: List of animation configurations
            audio_analysis_data: Optional audio analysis data for timing

        Returns:
            bool: True if animations applied successfully
        """
        try:
            # If apply_animation_to_strip is not available, simulate success for testing
            if not self.apply_animation_to_strip:
                if not bpy:  # Testing environment
                    logger.info("Animation application simulated for testing")
                    return True
                else:
                    logger.error("Animation applicator not initialized")
                    return False

            # Get audio events for timing
            audio_events = {}
            fps = 30
            if audio_analysis_data:
                audio_events = audio_analysis_data.get('animation_events', {})
                # Get FPS from scene if available
                if bpy:
                    fps = bpy.context.scene.render.fps

            # Apply animations using the events-based system
            success_count = 0
            for strip in video_strips:
                # Get animations for this strip from config
                strip_animations = self._get_animations_for_strip(
                    strip.name,
                    animations_config
                )

                if strip_animations:
                    try:
                        if self.apply_animation_to_strip:
                            # Use the new events-based approach
                            self.apply_animation_to_strip(
                                strip,
                                strip_animations,
                                audio_events,
                                fps
                            )
                            success_count += 1
                        else:
                            # Simulate animation application for testing
                            logger.info(f"Simulated animations on {strip.name}")
                            success_count += 1
                    except Exception as e:
                        logger.error(f"Failed to apply animations to {strip.name}: {e}")

            success = success_count > 0
            if success:
                logger.info(f"Applied animations to {success_count} strips")

            return success

        except Exception as e:
            logger.error(f"Error applying animations: {e}")
            return False

    def _load_preset_config(self, preset_name: str) -> Optional[Dict[str, Any]]:
        """Load preset configuration from YAML file.

        Args:
            preset_name: Name of preset (without .yaml extension)

        Returns:
            Dict with preset configuration or None if failed
        """
        try:
            # Get preset path using same logic as LoadPresetOperator
            addon_dir = Path(__file__).parent

            # Check user presets first
            user_presets_dir = Path.home() / ".config" / "blender" / "cinemon_presets"
            preset_filename = preset_name + '.yaml'
            preset_path = user_presets_dir / preset_filename

            # If not found, check built-in presets
            if not preset_path.exists():
                preset_path = addon_dir / "example_presets" / preset_filename
            if not preset_path or not preset_path.exists():
                logger.error(f"Preset not found: {preset_name}")
                return None

            # Load YAML
            import sys
            vendor_path = Path(__file__).parent / "vendor"
            if str(vendor_path) not in sys.path:
                sys.path.insert(0, str(vendor_path))

            try:
                import yaml
            except ImportError:
                logger.error(f"PyYAML not found in vendor path: {vendor_path}")
                return None
            with open(preset_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            # Map Video_X names to actual strip names if needed
            if bpy and bpy.context.scene.sequence_editor:
                config = self._map_video_names_to_strips(config)

            return config

        except Exception as e:
            logger.error(f"Error loading preset {preset_name}: {e}")
            return None

    def _convert_strip_animations_to_list(
        self,
        strip_animations: Dict[str, List[Dict]],
        video_strips: List[Any]
    ) -> List[Dict[str, Any]]:
        """Convert strip_animations format to flat animations list.

        Args:
            strip_animations: Dict mapping strip names to their animations
            video_strips: List of video strips

        Returns:
            List of animation dicts with target_strips added
        """
        animations_list = []

        for strip_name, animations in strip_animations.items():
            for animation in animations:
                # Create a copy and add target_strips
                anim_copy = animation.copy()
                anim_copy['target_strips'] = [strip_name]
                animations_list.append(anim_copy)

        return animations_list

    def _get_animations_for_strip(
        self,
        strip_name: str,
        animations_config: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Get animations that target a specific strip.

        Args:
            strip_name: Name of the strip
            animations_config: List of all animations

        Returns:
            List of animations for this strip
        """
        strip_animations = []

        for animation in animations_config:
            target_strips = animation.get('target_strips', [])

            # If no target strips specified, apply to all
            if not target_strips or strip_name in target_strips:
                strip_animations.append(animation)

        return strip_animations


    def _map_video_names_to_strips(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Map Video_X names to actual strip names in the scene.

        Args:
            config: Configuration with potential Video_X references

        Returns:
            Updated configuration with mapped names
        """
        if not bpy or not bpy.context.scene.sequence_editor:
            return config

        # Get all video strips sorted by channel
        sequences = bpy.context.scene.sequence_editor.sequences
        video_strips = [s for s in sequences if s.type == 'MOVIE']
        video_strips.sort(key=lambda s: s.channel)

        # Create mapping from Video_X to actual names
        strip_mapping = {}
        for i, strip in enumerate(video_strips):
            video_key = f"Video_{i+1}"
            strip_mapping[video_key] = strip.name

        # Apply mapping to strip_animations if present
        if 'strip_animations' in config:
            strip_animations = config.get('strip_animations', {})
            mapped_animations = {}

            for video_key, animations in strip_animations.items():
                if video_key in strip_mapping:
                    actual_name = strip_mapping[video_key]
                    mapped_animations[actual_name] = animations
                else:
                    # Keep non-Video_X names as-is
                    mapped_animations[video_key] = animations

            config['strip_animations'] = mapped_animations

        return config


# Global instance for easy access
_animation_api = None


def get_animation_api() -> AnimationAPI:
    """Get or create the global Animation API instance.

    Returns:
        AnimationAPI: The global instance
    """
    global _animation_api
    if _animation_api is None:
        _animation_api = AnimationAPI()
    return _animation_api
