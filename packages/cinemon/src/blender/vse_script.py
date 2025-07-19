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
    from .vse.constants import AnimationConstants
    from .vse.keyframe_helper import KeyframeHelper
    from .vse.layout_manager import BlenderLayoutManager
    from .vse.project_setup import BlenderProjectSetup
except ImportError:
    # Fallback for when script is run standalone in Blender
    sys.path.append(str(Path(__file__).parent))
    from vse.constants import AnimationConstants
    from vse.keyframe_helper import KeyframeHelper
    from vse.layout_manager import BlenderLayoutManager
    from vse.project_setup import BlenderProjectSetup


class BlenderVSEConfigurator:
    """Konfigurator Blender VSE z konfiguracji YAML."""

    def __init__(self, config_path: Optional[str] = None):
        """Inicjalizuj konfigurator z konfiguracji JSON.
        
        Args:
            config_path: Ścieżka do pliku konfiguracyjnego JSON
        """
        # Parse command line arguments if no config path provided
        if config_path is None:
            config_path = self._parse_command_line_args()
        
        # Load JSON configuration
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config_data = json.load(f)
        
        # Set attributes from config (maintaining compatibility)
        project = self.config_data['project']
        self.video_files = [Path(f) for f in project['video_files']]
        self.main_audio = Path(project['main_audio']) if project.get('main_audio') else None
        self.output_blend = Path(project['output_blend']) if project.get('output_blend') else None
        self.render_output = Path(project['render_output']) if project.get('render_output') else None
        self.fps = project.get('fps', 30)
        resolution = project.get('resolution', {})
        self.resolution_x = resolution.get('width', 1920)
        self.resolution_y = resolution.get('height', 1080)
        self.beat_division = project.get('beat_division', 8)
        
        # Animation mode is always compositional with JSON config
        self.animation_mode = "compositional"

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
        # Basic validation for JSON config
        errors = []
        required_keys = ['project', 'audio_analysis', 'layout', 'animations']
        for key in required_keys:
            if key not in self.config_data:
                errors.append(f"Missing required key: {key}")
        
        return len(errors) == 0, errors

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
        print(f"🎭 Checking animations: config has {len(self.config_data.get('animations', []))} animations")
        if self.config_data['animations']:
            print(f"🎭 Applying compositional animations...")
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
        print("🎵 Loading animation data...")
        try:
            animation_data = self._load_animation_data()
            print(f"🎵 Animation data loaded: {type(animation_data)}")
        except Exception as e:
            print(f"❌ Failed to load animation data: {e}")
            return False
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
        layout = self.config_data.get('layout', {})
        animations = self.config_data.get('animations', [])
        print(f"✓ Layout type: {layout.get('type', 'unknown')}")
        print(f"✓ Animations configured: {len(animations)}")
        
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
        # Load audio analysis data from JSON config
        audio_analysis = self.config_data.get('audio_analysis', {})
        print(f"🎵 Audio analysis section: {audio_analysis.keys() if audio_analysis else 'None'}")
        
        full_data = audio_analysis.get('data', {})
        print(f"🎵 Full data type: {type(full_data)}, empty: {not full_data}")
        
        if not full_data:
            # Try loading from file
            analysis_file = audio_analysis.get('file')
            print(f"🎵 Trying to load from file: {analysis_file}")
            if analysis_file:
                try:
                    with open(analysis_file, 'r', encoding='utf-8') as f:
                        import json
                        full_data = json.load(f)
                        print(f"🎵 Loaded from file successfully: {len(full_data)} keys")
                except Exception as e:
                    print(f"❌ Failed to load from file {analysis_file}: {e}")
                    return None
            else:
                print("❌ No audio analysis data found in config and no file specified")
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


    def _apply_yaml_layout_and_animations(self, video_strips: List, animation_data: Dict) -> bool:
        """
        Apply layout and animations using YAML configuration.
        
        Args:
            video_strips: List of video strips from Blender VSE
            animation_data: Animation data containing events
            
        Returns:
            bool: True if layout and animations were applied successfully
        """
        try:
            from .vse.animation_compositor import AnimationCompositor
            from .vse.layouts import RandomLayout
            from .vse.animations import (
                ScaleAnimation, ShakeAnimation, RotationWobbleAnimation,
                JitterAnimation, BrightnessFlickerAnimation,
                BlackWhiteAnimation, FilmGrainAnimation, VintageColorGradeAnimation
            )
        except ImportError:
            # Fallback for when script is run standalone in Blender
            sys.path.append(str(Path(__file__).parent))
            from vse.animation_compositor import AnimationCompositor
            from vse.layouts import RandomLayout
            from vse.animations import (
                ScaleAnimation, ShakeAnimation, RotationWobbleAnimation,
                JitterAnimation, BrightnessFlickerAnimation,
                BlackWhiteAnimation, FilmGrainAnimation, VintageColorGradeAnimation,
                VisibilityAnimation
            )
        
        print("=== Applying YAML layout and animations ===")
        
        # Create layout from YAML config
        layout = self._create_layout_from_yaml()
        
        # Create animations from YAML config
        animations = self._create_animations_from_yaml()
        print(f"🎨 Created {len(animations)} animations total")
        
        # Create and apply compositor
        print(f"🎭 Creating compositor with {len(animations)} animations and {len(video_strips)} strips")
        compositor = AnimationCompositor(layout, animations)
        success = compositor.apply(video_strips, animation_data, self.fps)
        print(f"🎭 Compositor apply result: {success}")
        
        if success:
            print("✓ YAML layout and animations applied successfully")
        else:
            print("✗ Failed to apply YAML layout and animations")
        
        return success
    
    def _create_layout_from_yaml(self):
        """Create layout instance from YAML configuration."""
        try:
            from .vse.layouts import RandomLayout, MainPipLayout
        except ImportError:
            # Fallback for when script is run standalone in Blender
            sys.path.append(str(Path(__file__).parent))
            from vse.layouts import RandomLayout, MainPipLayout
        
        layout = self.config_data.get('layout', {})
        layout_type = layout.get('type', 'random')
        layout_config = layout.get('config', {})
        
        if layout_type == "random":
            return RandomLayout(
                overlap_allowed=layout_config.get('overlap_allowed', True),
                margin=layout_config.get('margin', 0.05),
                min_scale=layout_config.get('min_scale', 0.3),
                max_scale=layout_config.get('max_scale', 0.8),
                seed=layout_config.get('seed', None)
            )
        elif layout_type == "main-pip":
            return MainPipLayout(
                pip_scale=layout_config.get('pip_scale', 0.25),
                margin_percent=layout_config.get('margin_percent', 0.1)
            )
        else:
            # Default to random layout
            return RandomLayout()
    
    def _create_animations_from_yaml(self) -> List:
        """Create animation instances from YAML configuration."""
        try:
            from .vse.animations import (
                ScaleAnimation, ShakeAnimation, RotationWobbleAnimation,
                JitterAnimation, BrightnessFlickerAnimation,
                BlackWhiteAnimation, FilmGrainAnimation, VintageColorGradeAnimation
            )
        except ImportError:
            # Fallback for when script is run standalone in Blender
            sys.path.append(str(Path(__file__).parent))
            from vse.animations import (
                ScaleAnimation, ShakeAnimation, RotationWobbleAnimation,
                JitterAnimation, BrightnessFlickerAnimation,
                BlackWhiteAnimation, FilmGrainAnimation, VintageColorGradeAnimation,
                VisibilityAnimation
            )
        
        animations = []
        
        print(f"🎨 _create_animations_from_yaml: Found {len(self.config_data.get('animations', []))} animation specs")
        for anim_spec in self.config_data.get('animations', []):
            anim_type = anim_spec.get('type')
            trigger = anim_spec.get('trigger')
            
            # Create animation based on type
            if anim_type == "scale":
                intensity = anim_spec.get('intensity', 0.3)
                duration_frames = anim_spec.get('duration_frames', 2)
                target_strips = anim_spec.get('target_strips', [])
                animation = ScaleAnimation(
                    trigger=trigger,
                    intensity=intensity,
                    duration_frames=duration_frames,
                    target_strips=target_strips
                )
                print(f"🎨 Created ScaleAnimation: trigger={trigger}, intensity={intensity}, target_strips={target_strips}")
                animations.append(animation)
                
            elif anim_type == "shake":
                intensity = anim_spec.get('intensity', 10.0)
                return_frames = anim_spec.get('return_frames', 2)
                animation = ShakeAnimation(
                    trigger=trigger,
                    intensity=intensity,
                    return_frames=return_frames
                )
                animations.append(animation)
                
            elif anim_type == "rotation":
                wobble_degrees = anim_spec.get('wobble_degrees', 1.0)
                return_frames = anim_spec.get('return_frames', 3)
                animation = RotationWobbleAnimation(
                    trigger=trigger,
                    wobble_degrees=wobble_degrees,
                    return_frames=return_frames
                )
                animations.append(animation)
                
            elif anim_type == "jitter":
                intensity = anim_spec.get('intensity', 2.0)
                min_interval = anim_spec.get('min_interval', 3)
                max_interval = anim_spec.get('max_interval', 8)
                animation = JitterAnimation(
                    trigger=trigger,
                    intensity=intensity,
                    min_interval=min_interval,
                    max_interval=max_interval
                )
                animations.append(animation)
                
            elif anim_type == "brightness_flicker":
                intensity = anim_spec.get('intensity', 0.15)
                return_frames = anim_spec.get('return_frames', 1)
                animation = BrightnessFlickerAnimation(
                    trigger=trigger,
                    intensity=intensity,
                    return_frames=return_frames
                )
                animations.append(animation)
                
            elif anim_type == "black_white":
                intensity = anim_spec.get('intensity', 0.8)
                animation = BlackWhiteAnimation(
                    trigger=trigger,
                    intensity=intensity
                )
                animations.append(animation)
                
            elif anim_type == "film_grain":
                intensity = anim_spec.get('intensity', 0.1)
                animation = FilmGrainAnimation(
                    trigger=trigger,
                    intensity=intensity
                )
                animations.append(animation)
                
            elif anim_type == "vintage_color":
                sepia_amount = anim_spec.get('sepia_amount', 0.3)
                contrast_boost = anim_spec.get('contrast_boost', 0.2)
                animation = VintageColorGradeAnimation(
                    trigger=trigger,
                    sepia_amount=sepia_amount,
                    contrast_boost=contrast_boost
                )
                animations.append(animation)
                
            elif anim_type == "visibility":
                pattern = anim_spec.get('pattern', 'alternate')
                duration_frames = anim_spec.get('duration_frames', 10)
                target_strips = anim_spec.get('target_strips', [])
                animation = VisibilityAnimation(
                    trigger=trigger,
                    pattern=pattern,
                    duration_frames=duration_frames,
                    target_strips=target_strips
                )
                print(f"🎨 Created VisibilityAnimation: trigger={trigger}, pattern={pattern}, target_strips={target_strips}")
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
        print(f"Layout: {configurator.config_data.get('layout', {}).get('type', 'unknown')}")
        print(f"Animations: {len(configurator.config_data.get('animations', []))}")
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
