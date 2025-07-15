"""
ABOUTME: MultiPipAnimator class - handles main camera switching with PiP corner effects.
ABOUTME: Extracts multi-pip logic from BlenderVSEConfigurator for better modularity and testability.
"""

from typing import List, Dict

from ..keyframe_helper import KeyframeHelper
from ..layout_manager import BlenderLayoutManager
from ..effects.vintage_film_effects import VintageFilmEffects


class MultiPipAnimator:
    """Animator for main camera switching with PiP corner effects."""

    def __init__(self):
        """Initialize MultiPipAnimator with required components."""
        self.keyframe_helper = KeyframeHelper()
        # Layout manager will be initialized with actual scene resolution in animate()
        self.layout_manager = None
        self.vintage_effects = VintageFilmEffects()

    def get_animation_mode(self) -> str:
        """
        Get the animation mode this animator handles.

        Returns:
            str: Animation mode identifier
        """
        return "multi-pip"

    def can_handle(self, animation_mode: str) -> bool:
        """
        Check if this animator can handle the specified animation mode.

        Args:
            animation_mode: Animation mode to check

        Returns:
            bool: True if this animator can handle the mode
        """
        return animation_mode == "multi-pip"

    def animate(self, video_strips: List, animation_data: Dict, fps: int) -> bool:
        """
        Apply multi-pip animation with main camera switching and corner PiPs.

        Args:
            video_strips: List of video strips from Blender VSE
            animation_data: Animation data containing sections and beats events
            fps: Frames per second for frame calculation

        Returns:
            bool: True if animation was applied successfully
        """
        # Validate inputs
        if fps <= 0:
            return False

        if not video_strips:
            return True  # Nothing to animate

        if not animation_data or "animation_events" not in animation_data:
            return True  # No animation data

        sections = animation_data["animation_events"].get("sections", [])
        beats = animation_data["animation_events"].get("beats", [])

        if not sections and not beats:
            return True  # No animation events

        print(
            f"✓ Multi-PiP animation: {len(video_strips)} strips, {len(sections)} sections, {len(beats)} beats at {fps} FPS"
        )

        # Initialize layout manager with actual scene resolution
        import bpy

        scene_width = bpy.context.scene.render.resolution_x
        scene_height = bpy.context.scene.render.resolution_y
        self.layout_manager = BlenderLayoutManager(scene_width, scene_height)

        print(
            f"✓ Initialized layout manager with scene resolution: {scene_width}x{scene_height}"
        )

        # First: Apply layout positions to ALL strips (like original implementation)
        layout = self.layout_manager.calculate_multi_pip_layout(len(video_strips))
        for i, strip in enumerate(video_strips):
            if i < len(layout):
                pos_x, pos_y, base_scale = layout[i]
                if hasattr(strip, "transform"):
                    # For main cameras (first 2 strips): use base scale to fill canvas
                    # For PiP (other strips): use resolution-aware scaling
                    if i < 2:  # Main cameras - force fill canvas
                        adjusted_scale = (
                            base_scale  # Use base scale (1.0) to fill canvas
                        )
                    else:  # PiP strips - use resolution-aware scaling
                        adjusted_scale = self._calculate_resolution_aware_scale(
                            strip, base_scale
                        )

                    strip.transform.offset_x = pos_x
                    strip.transform.offset_y = pos_y
                    strip.transform.scale_x = adjusted_scale
                    strip.transform.scale_y = adjusted_scale
                    print(
                        f"  {strip.name}: position ({pos_x}, {pos_y}), base_scale {base_scale}, adjusted_scale {adjusted_scale:.3f}"
                    )

        # Separate main cameras from corner PiPs (like original implementation)
        main_cameras = {}
        corner_pips = {}

        for i, strip in enumerate(video_strips):
            if i < 2:  # First two strips are main cameras
                main_cameras[strip.name] = strip
            else:  # Rest are corner PiPs
                corner_pips[strip.name] = strip

        print(f"Main cameras: {list(main_cameras.keys())}")
        print(f"Corner PiPs: {list(corner_pips.keys())}")

        # Apply main camera switching based on sections
        if sections:
            self._setup_main_camera_sections(main_cameras, sections, fps)

        # Apply vintage film effects to main cameras
        beats = animation_data["animation_events"].get("beats", [])
        if beats and main_cameras:
            self._apply_vintage_effects_to_main_cameras(main_cameras, beats, fps)

        # Apply corner PiP effects based on energy peaks (like original)
        energy_peaks = animation_data["animation_events"].get("energy_peaks", [])
        if energy_peaks and corner_pips:
            self._setup_corner_pip_effects(corner_pips, energy_peaks, fps)

        print("✓ Multi-PiP animation applied successfully")
        return True

    def _setup_main_camera_sections(
        self, main_cameras: Dict, sections: List[Dict], fps: int
    ):
        """
        Setup main camera section switching (restored original logic).

        Main cameras (video1/video2) alternate on section boundaries.

        Args:
            main_cameras: Dictionary of main camera strips
            sections: List of section dictionaries with start/end times
            fps: Frames per second
        """
        print("=== Setting up main camera section switching ===")

        strip_names = list(main_cameras.keys())
        if len(strip_names) < 2:
            print("✗ Need at least 2 main cameras for section switching")
            return False

        # Initially show first main camera at frame 1
        first_strip = list(main_cameras.values())[0]
        for strip in main_cameras.values():
            if strip == first_strip:
                strip.blend_alpha = 1.0
                self.keyframe_helper.insert_blend_alpha_keyframe(strip.name, 1, 1.0)
            else:
                strip.blend_alpha = 0.0
                self.keyframe_helper.insert_blend_alpha_keyframe(strip.name, 1, 0.0)

        # Setup section switching (alternating between video1 and video2)
        for section_index, section in enumerate(sections):
            start_frame = int(section["start"] * fps)
            end_frame = int(section["end"] * fps)

            # Determine which camera should be active
            active_index = section_index % len(strip_names)
            active_strip_name = strip_names[active_index]
            active_strip = main_cameras[active_strip_name]

            print(
                f"  Section {section_index + 1} ({section['label']}): frames {start_frame}-{end_frame}, camera {active_strip_name}"
            )

            # Hide all cameras at section start
            for strip in main_cameras.values():
                strip.blend_alpha = 0.0
                self.keyframe_helper.insert_blend_alpha_keyframe(
                    strip.name, start_frame, 0.0
                )

            # Show active camera for the entire section duration
            active_strip.blend_alpha = 1.0
            self.keyframe_helper.insert_blend_alpha_keyframe(
                active_strip.name, start_frame, 1.0
            )

            # Keep active camera visible until end of section
            self.keyframe_helper.insert_blend_alpha_keyframe(
                active_strip.name, end_frame, 1.0
            )

    def _animate_pip_corner_effects(
        self, video_strips: List, energy_peaks: List[float], fps: int
    ):
        """
        Animate PiP corner effects on energy peaks (like original implementation).

        Args:
            video_strips: List of video strips
            energy_peaks: List of energy peak times in seconds
            fps: Frames per second
        """
        print(f"  PiP corner effects on {len(energy_peaks)} energy peaks")

        # Set up PiP strips (non-main cameras) - positions already set above
        pip_strips = video_strips[2:]  # Corner PiPs start from index 2 (like original)

        # Make all corner PiPs visible and set initial keyframes
        for strip in pip_strips:
            if hasattr(strip, "transform"):
                strip.blend_alpha = 1.0
                # Set initial scale keyframes at frame 1
                self.keyframe_helper.insert_transform_scale_keyframes(strip.name, 1)
                print(f"    PiP strip {strip.name}: visible with initial keyframes")

    def _calculate_resolution_aware_scale(self, strip, base_scale: float) -> float:
        """
        Calculate resolution-aware scale factor for video strip.

        This adjusts the base scale to account for the difference between
        the strip's resolution and the project's resolution.

        Args:
            strip: Blender video strip object
            base_scale: Base scale factor from layout calculation

        Returns:
            float: Adjusted scale factor
        """
        try:
            # Get scene resolution
            import bpy

            scene = bpy.context.scene
            project_width = scene.render.resolution_x
            project_height = scene.render.resolution_y

            # Get strip resolution from elements (if available)
            if hasattr(strip, "elements") and strip.elements:
                # For movie strips, get resolution from first element
                strip_width = strip.elements[0].orig_width
                strip_height = strip.elements[0].orig_height
            else:
                # Fallback: use project resolution
                return base_scale

            # Calculate scale factors to fit strip to project resolution
            width_scale = project_width / strip_width
            height_scale = project_height / strip_height

            # Use the smaller scale to maintain aspect ratio (fit within bounds)
            fit_scale = min(width_scale, height_scale)

            # Apply the fit scale to the base layout scale
            adjusted_scale = base_scale * fit_scale

            print(
                f"    Resolution adjustment: {strip_width}x{strip_height} -> {project_width}x{project_height}, "
                f"fit_scale: {fit_scale:.3f}, base: {base_scale}, adjusted: {adjusted_scale:.3f}"
            )

            return adjusted_scale

        except Exception as e:
            print(
                f"    Warning: Could not calculate resolution-aware scale for {strip.name}: {e}"
            )
            return base_scale

    def _setup_corner_pip_effects(
        self, corner_pips: Dict, energy_peaks: List[float], fps: int
    ):
        """
        Setup corner PiP effects (restored original logic).

        Corner PiPs are always visible (blend_alpha = 1.0) and react to energy peaks.

        Args:
            corner_pips: Dictionary of corner PiP strips
            energy_peaks: List of energy peak times in seconds
            fps: Frames per second
        """
        print("=== Setting up corner PiP effects ===")

        if not corner_pips:
            print("✓ No corner PiPs to animate")
            return True

        # Make all corner PiPs FULLY VISIBLE (original logic)
        for strip in corner_pips.values():
            strip.blend_alpha = 1.0  # FULL VISIBILITY (not 0.3!)

        # Add beat-based scale pulsing (like energy-pulse mode)
        for strip in corner_pips.values():
            # Set initial scale keyframes at frame 1
            self.keyframe_helper.insert_transform_scale_keyframes(strip.name, 1)

        # Animate on energy peaks (bass response)
        for peak_index, peak_time in enumerate(energy_peaks):
            frame = int(peak_time * fps)

            for strip in corner_pips.values():
                # Get current base scale from layout
                current_scale = strip.transform.scale_x
                pulse_scale = current_scale * 1.1  # 10% pulse for corner PiPs

                # Scale up on energy peak
                strip.transform.scale_x = pulse_scale
                strip.transform.scale_y = pulse_scale
                self.keyframe_helper.insert_transform_scale_keyframes(
                    strip.name, frame, pulse_scale
                )

                # Scale back down (1 frame later)
                return_frame = frame + 1
                strip.transform.scale_x = current_scale
                strip.transform.scale_y = current_scale
                self.keyframe_helper.insert_transform_scale_keyframes(
                    strip.name, return_frame, current_scale
                )

        print(f"✓ Corner PiP effects applied to {len(corner_pips)} strips")
        return True

    def _apply_vintage_effects_to_main_cameras(
        self, main_cameras: Dict, beats: List[float], fps: int
    ) -> bool:
        """
        Apply vintage film effects to main cameras.

        Args:
            main_cameras: Dictionary of main camera strips
            beats: List of beat times in seconds
            fps: Frames per second

        Returns:
            bool: True if effects were applied successfully
        """
        print("=== Applying vintage film effects to main cameras ===")

        # Calculate timeline duration for jitter effect
        import bpy

        timeline_duration = bpy.context.scene.frame_end

        # Vintage effects configuration (subtle for main cameras)
        vintage_config = {
            "camera_shake": {"enabled": True, "intensity": 2.0},
            "film_jitter": {"enabled": True, "intensity": 1.0},
            "brightness_flicker": {
                "enabled": False,
                "amount": 0.28,
            },  # DISABLED - conflicts with blend_alpha camera switching
            "rotation_wobble": {"enabled": True, "degrees": 0.5},
            "black_white": {"enabled": True, "intensity": 0.8},
            "film_grain": {"enabled": True, "intensity": 0.12},
            "vintage_grade": {"enabled": True, "sepia": -0.35, "contrast": 0.2},
        }

        success = True
        for strip in main_cameras.values():
            print(f"  Applying vintage effects to main camera: {strip.name}")
            success &= self.vintage_effects.apply_vintage_film_combo(
                strip, beats, timeline_duration, fps, vintage_config
            )

        if success:
            print(f"✓ Vintage film effects applied to {len(main_cameras)} main cameras")
        else:
            print("✗ Some vintage effects failed for main cameras")

        return success
