"""
Parametryczny skrypt Blender do konfiguracji VSE.

Ten skrypt może być uruchomiony w Blenderze i konfiguruje VSE project
na podstawie konfiguracji YAML przekazanej jako argument.

Użycie z CLI:
blender --background --python blender_vse_script.py -- --config config.yaml

Użycie w Blenderze:
1. Otwórz Blender
2. Przejdź do workspace Scripting
3. Wklej ten skrypt
4. Zmodyfikuj CONFIG_PATH na ścieżkę do pliku konfiguracyjnego
5. Uruchom skrypt (Alt+P)
"""

import bpy
import os
import sys
import json
from pathlib import Path
from typing import List, Optional, Tuple, Dict

# Import refactored modules
try:
    from .vse.yaml_config import BlenderYAMLConfigReader
    from .vse.constants import AnimationConstants
    from .vse.keyframe_helper import KeyframeHelper
    from .vse.layout_manager import BlenderLayoutManager
    from .vse.animation_engine import BlenderAnimationEngine
    from .vse.project_setup import BlenderProjectSetup
    from .vse.animators.compositional_animator import CompositionalAnimator
except ImportError:
    # Fallback for when script is run standalone in Blender
    sys.path.append(str(Path(__file__).parent))
    from vse.yaml_config import BlenderYAMLConfigReader
    from vse.constants import AnimationConstants
    from vse.keyframe_helper import KeyframeHelper
    from vse.layout_manager import BlenderLayoutManager
    from vse.animation_engine import BlenderAnimationEngine
    from vse.project_setup import BlenderProjectSetup
    from vse.animators.compositional_animator import CompositionalAnimator


class BlenderVSEConfigurator:
    """Konfigurator Blender VSE z konfiguracji YAML."""

    def __init__(self, config_path: Optional[str] = None):
        """Inicjalizuj konfigurator z konfiguracji YAML.
        
        Args:
            config_path: Ścieżka do pliku konfiguracyjnego YAML
        """
        # Parse command line arguments if no config path provided
        if config_path is None:
            config_path = self._parse_command_line_args()
        
        # Load YAML configuration
        self.yaml_config = BlenderYAMLConfigReader(config_path)
        
        # Set attributes from config (maintaining compatibility)
        self.video_files = [Path(f) for f in self.yaml_config.video_files]
        self.main_audio = Path(self.yaml_config.main_audio) if self.yaml_config.main_audio else None
        self.output_blend = Path(self.yaml_config.output_blend) if self.yaml_config.output_blend else None
        self.render_output = Path(self.yaml_config.render_output) if self.yaml_config.render_output else None
        self.fps = self.yaml_config.fps
        self.resolution_x = self.yaml_config.resolution_x
        self.resolution_y = self.yaml_config.resolution_y
        self.beat_division = self.yaml_config.beat_division
        
        # Animation mode is always compositional with YAML config
        self.animation_mode = "compositional"
        
        # Initialize compositional animator
        self.compositional_animator = CompositionalAnimator()

        # Initialize project setup with config
        self.project_setup = BlenderProjectSetup(
            {
                "fps": self.fps,
                "resolution_x": self.resolution_x,
                "resolution_y": self.resolution_y,
                "video_files": self.video_files,
                "main_audio": self.main_audio,
                "output_blend": self.output_blend,
                "render_output": self.render_output,
            }
        )
    
    def _parse_command_line_args(self) -> Optional[str]:
        """Parse command line arguments to find config file.
        
        Returns:
            Optional[str]: Path to config file or None
        """
        # Look for --config argument in sys.argv
        for i, arg in enumerate(sys.argv):
            if arg == '--config' and i + 1 < len(sys.argv):
                return sys.argv[i + 1]
        
        # Fallback - look for CONFIG_PATH constant (for Blender GUI usage)
        if 'CONFIG_PATH' in globals():
            return CONFIG_PATH
        
        raise ValueError("No config file specified. Use --config argument or set CONFIG_PATH variable.")

    def validate_parameters(self) -> Tuple[bool, List[str]]:
        """
        Waliduj parametry konfiguracji.

        Returns:
            Tuple[bool, List[str]]: (czy_valid, lista_błędów)
        """
        return self.yaml_config.validate()

    def setup_vse_project(self) -> bool:
        """
        Skonfiguruj projekt Blender VSE.

        Returns:
            bool: True jeśli sukces
        """
        print("=== Konfiguracja projektu Blender VSE ===")

        # Walidacja parametrów
        is_valid, errors = self.validate_parameters()
        if not is_valid:
            print("✗ Błędy walidacji parametrów:")
            for error in errors:
                print(f"  - {error}")
            return False

        # Use BlenderProjectSetup for basic project setup
        success = self.project_setup.setup_project()
        if not success:
            print("✗ Błąd konfiguracji podstawowego projektu")
            return False

        # Apply compositional animations if configured
        if self.yaml_config.animations:
            sequencer = bpy.context.scene.sequence_editor
            animation_success = self._apply_compositional_animations(sequencer)
            if not animation_success:
                print(
                    "⚠ Animacje nie zostały zastosowane, ale projekt został utworzony"
                )
            else:
                # Save file again after adding animations
                if self.output_blend:
                    try:
                        bpy.ops.wm.save_as_mainfile(filepath=str(self.output_blend))
                        print(f"✓ Zapisano projekt z animacjami: {self.output_blend}")
                    except Exception as e:
                        print(f"✗ Błąd zapisywania projektu z animacjami: {e}")
                        return False

        print("=== Konfiguracja projektu VSE zakończona sukcesem ===")
        return True

    def _apply_compositional_animations(self, sequencer) -> bool:
        """
        Apply compositional animations to video strips using YAML configuration.

        Args:
            sequencer: Blender sequence editor

        Returns:
            bool: True if animations were applied successfully
        """
        print("=== Applying compositional animations from YAML config ===")

        # Load animation data
        animation_data = self._load_animation_data()
        if not animation_data:
            print("✗ No animation data available")
            return False

        # Get video strips (exclude audio strips)
        video_strips = [
            seq
            for seq in sequencer.sequences
            if hasattr(seq, "blend_alpha") and hasattr(seq, "transform")
        ]
        if not video_strips:
            print("✗ No video strips found for animation")
            return False

        print(f"✓ Found {len(video_strips)} video strips for animation")
        print(f"✓ Layout type: {self.yaml_config.layout_type}")
        print(f"✓ Animations configured: {len(self.yaml_config.animations)}")
        
        # Apply layout using YAML config
        success = self._apply_yaml_layout_and_animations(video_strips, animation_data)
        
        if success:
            print("✓ Compositional animations applied successfully")
        else:
            print("✗ Compositional animations failed")

        return success

    def _load_animation_data(self) -> Optional[Dict]:
        """
        Load animation data from YAML configuration.

        Returns:
            Optional[Dict]: Animation data with events or None if not available
        """
        # Load animation data using YAML config
        full_data = self.yaml_config.load_audio_analysis_data()
        
        if not full_data:
            print("No audio analysis data found in YAML config")
            return None

        try:
            # Extract beat events and energy peaks
            if "animation_events" not in full_data:
                print("No animation_events found in analysis data")
                return None

            animation_events = full_data["animation_events"]

            # Support beats, energy_peaks, and sections
            events_data = {}
            if "beats" in animation_events:
                events_data["beats"] = animation_events["beats"]
                print(f"✓ Loaded {len(events_data['beats'])} beat events")

            if "energy_peaks" in animation_events:
                events_data["energy_peaks"] = animation_events["energy_peaks"]
                print(f"✓ Loaded {len(events_data['energy_peaks'])} energy peak events")

            if "sections" in animation_events:
                events_data["sections"] = animation_events["sections"]
                print(
                    f"✓ Loaded {len(events_data['sections'])} section boundary events"
                )

            if not events_data:
                print(
                    "No supported animation events found (beats, energy_peaks, or sections)"
                )
                return None

            # Return expanded data
            expanded_data = {
                "duration": full_data.get("duration", 0.0),
                "tempo": full_data.get("tempo", {"bpm": 120.0}),
                "animation_events": events_data,
            }

            return expanded_data

        except Exception as e:
            print(f"Error processing animation data: {e}")
            return None

    def _calculate_pip_positions(
        self, resolution_x: int = 1280, resolution_y: int = 720
    ) -> List[Dict]:
        """
        Calculate PiP positions for 2x2 grid layout.

        MVP version: Hardcoded 2x2 grid for maximum 4 video sources.

        Args:
            resolution_x: Canvas width in pixels
            resolution_y: Canvas height in pixels

        Returns:
            List[Dict]: List of position dictionaries with x, y, width, height
        """
        # MVP: Hardcoded 2x2 grid
        pip_width = resolution_x // 2
        pip_height = resolution_y // 2

        positions = [
            # Top-left
            {"x": 0, "y": pip_height, "width": pip_width, "height": pip_height},
            # Top-right
            {"x": pip_width, "y": pip_height, "width": pip_width, "height": pip_height},
            # Bottom-left
            {"x": 0, "y": 0, "width": pip_width, "height": pip_height},
            # Bottom-right
            {"x": pip_width, "y": 0, "width": pip_width, "height": pip_height},
        ]

        print(
            f"✓ Calculated 2x2 PiP positions for {resolution_x}x{resolution_y} canvas"
        )
        return positions

    def _animate_beat_switch(self, video_strips: List, animation_data: Dict) -> bool:
        """
        Animate beat switch by alternating strip visibility using blend_alpha.

        MVP version: Simple alternating visibility on beat events.

        Args:
            video_strips: List of video strips from Blender VSE
            animation_data: Animation data containing beat events

        Returns:
            bool: True if animation was applied successfully
        """
        if not animation_data or "animation_events" not in animation_data:
            print("No animation data available")
            return True

        beats = animation_data["animation_events"].get("beats", [])
        if not beats:
            print("No beat events found - skipping animation")
            return True

        if not video_strips:
            print("No video strips found - skipping animation")
            return True

        # Get FPS from scene
        fps = bpy.context.scene.render.fps
        print(
            f"✓ Animating {len(video_strips)} strips on {len(beats)} beats at {fps} FPS"
        )

        # Set initial visibility - first strip visible, others hidden
        keyframe_helper = KeyframeHelper()
        for i, strip in enumerate(video_strips):
            alpha_value = 1.0 if i == 0 else 0.0
            strip.blend_alpha = alpha_value
            keyframe_helper.insert_blend_alpha_keyframe(strip.name, 1, alpha_value)

        # Animate on beat events
        for beat_index, beat_time in enumerate(beats):
            frame = int(beat_time * fps)
            active_strip_index = beat_index % len(video_strips)

            print(
                f"  Beat {beat_index + 1}: frame {frame}, active strip {active_strip_index}"
            )

            # Set visibility for all strips
            for strip_index, strip in enumerate(video_strips):
                alpha_value = 1.0 if strip_index == active_strip_index else 0.0
                strip.blend_alpha = alpha_value
                keyframe_helper.insert_blend_alpha_keyframe(
                    strip.name, frame, alpha_value
                )

        print("✓ Beat switch animation applied successfully")
        return True

    def _animate_energy_pulse(self, video_strips: List, animation_data: Dict) -> bool:
        """
        Animate energy pulse by scaling strips on energy peaks.

        Args:
            video_strips: List of video strips from Blender VSE
            animation_data: Animation data containing energy_peaks events

        Returns:
            bool: True if animation was applied successfully
        """
        if not animation_data or "animation_events" not in animation_data:
            print("No animation data available")
            return True

        energy_peaks = animation_data["animation_events"].get("energy_peaks", [])
        if not energy_peaks:
            print("No energy peaks found - skipping animation")
            return True

        if not video_strips:
            print("No video strips found - skipping animation")
            return True

        # Get FPS from scene
        fps = bpy.context.scene.render.fps
        print(
            f"✓ Animating {len(video_strips)} strips on {len(energy_peaks)} energy peaks at {fps} FPS"
        )

        # Set initial scale to normal
        keyframe_helper = KeyframeHelper()
        for strip in video_strips:
            if hasattr(strip, "transform"):
                strip.transform.scale_x = 1.0
                strip.transform.scale_y = 1.0
                keyframe_helper.insert_transform_scale_keyframes(
                    strip.name, 1, 1.0, 1.0
                )

        # Animate on energy peak events
        for peak_index, peak_time in enumerate(energy_peaks):
            frame = int(peak_time * fps)

            print(f"  Energy peak {peak_index + 1}: frame {frame}")

            # Scale up on energy peak
            for strip in video_strips:
                if hasattr(strip, "transform"):
                    scale_factor = AnimationConstants.ENERGY_SCALE_FACTOR
                    strip.transform.scale_x = scale_factor
                    strip.transform.scale_y = scale_factor
                    keyframe_helper.insert_transform_scale_keyframes(
                        strip.name, frame, scale_factor
                    )

            # Scale back down after peak (1 frame later)
            return_frame = frame + 1
            for strip in video_strips:
                if hasattr(strip, "transform"):
                    strip.transform.scale_x = 1.0  # Back to normal
                    strip.transform.scale_y = 1.0
                    keyframe_helper.insert_transform_scale_keyframes(
                        strip.name, return_frame, 1.0
                    )

        print("✓ Energy pulse animation applied successfully")
        return True

    def _animate_multi_pip(self, video_strips: List, animation_data: Dict) -> bool:
        """
        Apply Multi-PiP animation mode.

        Layout: Main cameras (video1/video2) switch on section boundaries,
               Corner PiPs (video3/video4+) always visible with beat/energy effects.

        Args:
            video_strips: List of video strips
            animation_data: Animation data with sections, beats, and energy_peaks

        Returns:
            bool: True if animation applied successfully
        """
        print("=== Applying Multi-PiP animation mode ===")

        # Get required data
        # Get sections from animation data (already converted to objects)
        sections = animation_data.get("animation_events", {}).get("sections", [])
        beats = animation_data.get("animation_events", {}).get("beats", [])
        energy_peaks = animation_data.get("animation_events", {}).get(
            "energy_peaks", []
        )

        print(
            f"Found {len(sections)} sections, {len(beats)} beats, {len(energy_peaks)} energy peaks"
        )

        if not sections:
            print("✗ No sections found for Multi-PiP mode")
            return False

        # Setup multi-pip layout positions
        layout = self._calculate_multi_pip_layout(len(video_strips))

        # Apply layout positions to all strips
        for i, strip in enumerate(video_strips):
            if i < len(layout):
                pos_x, pos_y, base_scale = layout[i]
                strip.transform.offset_x = pos_x
                strip.transform.offset_y = pos_y
                strip.transform.scale_x = base_scale
                strip.transform.scale_y = base_scale
                print(
                    f"  {strip.name}: position ({pos_x}, {pos_y}), scale {base_scale}"
                )

        # Separate main cameras from corner PiPs
        main_cameras = {}
        corner_pips = {}

        for i, strip in enumerate(video_strips):
            if i < 2:  # First two strips are main cameras
                main_cameras[strip.name] = strip
            else:  # Rest are corner PiPs
                corner_pips[strip.name] = strip

        print(f"Main cameras: {list(main_cameras.keys())}")
        print(f"Corner PiPs: {list(corner_pips.keys())}")

        # Setup main camera section switching (pass converted sections)
        success1 = self._setup_main_camera_sections(
            main_cameras, {"sections": sections}
        )

        # Setup corner PiP effects
        success2 = self._setup_corner_pip_effects(corner_pips, animation_data)

        return success1 and success2

    def _calculate_multi_pip_layout(
        self, strip_count: int
    ) -> List[Tuple[int, int, float]]:
        """
        Calculate Multi-PiP layout positions based on scene resolution.

        Args:
            strip_count: Number of video strips

        Returns:
            List of (pos_x, pos_y, scale) tuples for each strip
        """
        # Use LayoutManager for centralized layout calculation
        width = bpy.context.scene.render.resolution_x
        height = bpy.context.scene.render.resolution_y
        layout_manager = BlenderLayoutManager(width, height)

        return layout_manager.calculate_multi_pip_layout(strip_count)

    def _setup_main_camera_sections(
        self, main_cameras: Dict, animation_data: Dict
    ) -> bool:
        """
        Setup main camera section switching.

        Main cameras (video1/video2) alternate on section boundaries.

        Args:
            main_cameras: Dictionary of main camera strips
            animation_data: Animation data with sections

        Returns:
            bool: True if setup successful
        """
        sections = animation_data.get("sections", [])
        fps = bpy.context.scene.render.fps

        print("=== Setting up main camera section switching ===")

        strip_names = list(main_cameras.keys())
        if len(strip_names) < 2:
            print("✗ Need at least 2 main cameras for section switching")
            return False

        # Initially hide all main cameras
        keyframe_helper = KeyframeHelper()
        for strip in main_cameras.values():
            strip.blend_alpha = 0.0

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
                keyframe_helper.insert_blend_alpha_keyframe(
                    strip.name, start_frame, 0.0
                )

            # Show active camera
            active_strip.blend_alpha = 1.0
            keyframe_helper.insert_blend_alpha_keyframe(
                active_strip.name, start_frame, 1.0
            )

        return True

    def _setup_corner_pip_effects(
        self, corner_pips: Dict, animation_data: Dict
    ) -> bool:
        """
        Setup corner PiP effects (beat/energy animations).

        Corner PiPs are always visible and react to beats/energy.

        Args:
            corner_pips: Dictionary of corner PiP strips
            animation_data: Animation data with beats and energy_peaks

        Returns:
            bool: True if setup successful
        """
        energy_peaks = animation_data.get("animation_events", {}).get(
            "energy_peaks", []
        )
        fps = bpy.context.scene.render.fps

        print("=== Setting up corner PiP effects ===")

        if not corner_pips:
            print("✓ No corner PiPs to animate")
            return True

        # Make all corner PiPs visible
        keyframe_helper = KeyframeHelper()
        for strip in corner_pips.values():
            strip.blend_alpha = 1.0

        # Add beat-based scale pulsing (like energy-pulse mode)
        for strip in corner_pips.values():
            # Set initial scale keyframes at frame 1
            keyframe_helper.insert_transform_scale_keyframes(strip, 1)

        # Animate on energy peaks (bass response)
        for peak_index, peak_time in enumerate(energy_peaks):
            frame = int(peak_time * fps)

            for strip in corner_pips.values():
                # Get current base scale from layout
                current_scale = strip.transform.scale_x
                pulse_scale = current_scale * AnimationConstants.PIP_SCALE_FACTOR

                # Scale up on energy peak
                strip.transform.scale_x = pulse_scale
                strip.transform.scale_y = pulse_scale
                keyframe_helper.insert_transform_scale_keyframes(
                    strip.name, frame, pulse_scale
                )

                # Scale back down (1 frame later)
                return_frame = frame + 1
                strip.transform.scale_x = current_scale
                strip.transform.scale_y = current_scale
                keyframe_helper.insert_transform_scale_keyframes(
                    strip.name, return_frame, current_scale
                )

        print(f"✓ Corner PiP effects applied to {len(corner_pips)} strips")
        return True

    def _apply_yaml_layout_and_animations(self, video_strips: List, animation_data: Dict) -> bool:
        """
        Apply layout and animations using YAML configuration.
        
        Args:
            video_strips: List of video strips from Blender VSE
            animation_data: Animation data containing events
            
        Returns:
            bool: True if layout and animations were applied successfully
        """
        from .vse.animation_compositor import AnimationCompositor
        from .vse.layouts import RandomLayout
        from .vse.animations import (
            ScaleAnimation, ShakeAnimation, RotationWobbleAnimation,
            JitterAnimation, BrightnessFlickerAnimation,
            BlackWhiteAnimation, FilmGrainAnimation, VintageColorGradeAnimation
        )
        
        print("=== Applying YAML layout and animations ===")
        
        # Create layout from YAML config
        layout = self._create_layout_from_yaml()
        
        # Create animations from YAML config
        animations = self._create_animations_from_yaml()
        
        # Create and apply compositor
        compositor = AnimationCompositor(layout, animations)
        success = compositor.apply(video_strips, animation_data, self.fps)
        
        if success:
            print("✓ YAML layout and animations applied successfully")
        else:
            print("✗ Failed to apply YAML layout and animations")
        
        return success
    
    def _create_layout_from_yaml(self):
        """Create layout instance from YAML configuration."""
        from .vse.layouts import RandomLayout
        
        layout_type = self.yaml_config.layout_type
        layout_config = self.yaml_config.layout_config or {}
        
        if layout_type == "random":
            return RandomLayout(
                overlap_allowed=layout_config.get('overlap_allowed', True),
                margin=layout_config.get('margin', 0.05),
                min_scale=layout_config.get('min_scale', 0.3),
                max_scale=layout_config.get('max_scale', 0.8),
                seed=layout_config.get('seed', None)
            )
        else:
            # Default to random layout
            return RandomLayout()
    
    def _create_animations_from_yaml(self) -> List:
        """Create animation instances from YAML configuration."""
        from .vse.animations import (
            ScaleAnimation, ShakeAnimation, RotationWobbleAnimation,
            JitterAnimation, BrightnessFlickerAnimation,
            BlackWhiteAnimation, FilmGrainAnimation, VintageColorGradeAnimation
        )
        
        animations = []
        
        for anim_spec in self.yaml_config.animations:
            anim_type = anim_spec.type
            trigger = anim_spec.trigger
            
            # Create animation based on type
            if anim_type == "scale":
                intensity = getattr(anim_spec, 'intensity', 0.3)
                duration_frames = getattr(anim_spec, 'duration_frames', 2)
                animation = ScaleAnimation(
                    trigger=trigger,
                    intensity=intensity,
                    duration_frames=duration_frames
                )
                animations.append(animation)
                
            elif anim_type == "shake":
                intensity = getattr(anim_spec, 'intensity', 10.0)
                return_frames = getattr(anim_spec, 'return_frames', 2)
                animation = ShakeAnimation(
                    trigger=trigger,
                    intensity=intensity,
                    return_frames=return_frames
                )
                animations.append(animation)
                
            elif anim_type == "rotation":
                wobble_degrees = getattr(anim_spec, 'wobble_degrees', 1.0)
                return_frames = getattr(anim_spec, 'return_frames', 3)
                animation = RotationWobbleAnimation(
                    trigger=trigger,
                    wobble_degrees=wobble_degrees,
                    return_frames=return_frames
                )
                animations.append(animation)
                
            elif anim_type == "jitter":
                intensity = getattr(anim_spec, 'intensity', 2.0)
                min_interval = getattr(anim_spec, 'min_interval', 3)
                max_interval = getattr(anim_spec, 'max_interval', 8)
                animation = JitterAnimation(
                    trigger=trigger,
                    intensity=intensity,
                    min_interval=min_interval,
                    max_interval=max_interval
                )
                animations.append(animation)
                
            elif anim_type == "brightness_flicker":
                intensity = getattr(anim_spec, 'intensity', 0.15)
                return_frames = getattr(anim_spec, 'return_frames', 1)
                animation = BrightnessFlickerAnimation(
                    trigger=trigger,
                    intensity=intensity,
                    return_frames=return_frames
                )
                animations.append(animation)
                
            elif anim_type == "black_white":
                intensity = getattr(anim_spec, 'intensity', 0.8)
                animation = BlackWhiteAnimation(
                    trigger=trigger,
                    intensity=intensity
                )
                animations.append(animation)
                
            elif anim_type == "film_grain":
                intensity = getattr(anim_spec, 'intensity', 0.1)
                animation = FilmGrainAnimation(
                    trigger=trigger,
                    intensity=intensity
                )
                animations.append(animation)
                
            elif anim_type == "vintage_color":
                sepia_amount = getattr(anim_spec, 'sepia_amount', 0.3)
                contrast_boost = getattr(anim_spec, 'contrast_boost', 0.2)
                animation = VintageColorGradeAnimation(
                    trigger=trigger,
                    sepia_amount=sepia_amount,
                    contrast_boost=contrast_boost
                )
                animations.append(animation)
        
        return animations


def main() -> int:
    """
    Główna funkcja skryptu.

    Returns:
        int: Kod wyjścia (0 dla sukcesu, 1 dla błędu)
    """
    try:
        configurator = BlenderVSEConfigurator()

        print("=== Parametryczny skrypt Blender VSE z YAML ===")
        print(f"Pliki wideo: {len(configurator.video_files)}")
        print(f"Główne audio: {configurator.main_audio}")
        print(f"Plik wyjściowy: {configurator.output_blend}")
        print(f"Renderowanie: {configurator.render_output}")
        print(f"Rozdzielczość: {configurator.resolution_x}x{configurator.resolution_y}")
        print(f"FPS: {configurator.fps}")
        print(f"Layout: {configurator.yaml_config.layout_type}")
        print(f"Animations: {len(configurator.yaml_config.animations)}")
        print()

        success = configurator.setup_vse_project()

        if success:
            print("✅ Projekt VSE skonfigurowany pomyślnie z YAML!")
            return 0
        else:
            print("❌ Błąd konfiguracji projektu VSE")
            return 1
    except Exception as e:
        print(f"❌ Błąd inicjalizacji: {e}")
        return 1


# Sprawdź czy jesteśmy w Blenderze czy uruchamiamy z linii poleceń
def is_running_in_blender() -> bool:
    """Sprawdź czy skrypt jest uruchamiany w Blenderze."""
    try:
        import importlib.util

        spec = importlib.util.find_spec("bpy")
        return spec is not None
    except ImportError:
        return False


# Uruchom główną funkcję tylko gdy skrypt jest wykonywany bezpośrednio
if __name__ == "__main__":
    exit_code = main()

    # Jeśli uruchamiamy z linii poleceń (nie w Blenderze), użyj sys.exit()
    if not is_running_in_blender():
        sys.exit(exit_code)
