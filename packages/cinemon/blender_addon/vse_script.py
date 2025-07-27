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

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import bpy

# Import refactored modules - absolute imports after sys.path setup
from vse.constants import AnimationConstants
from vse.keyframe_helper import KeyframeHelper
from vse.layout_manager import BlenderLayoutManager
from vse.project_setup import BlenderProjectSetup
from vse.yaml_config import BlenderYAMLConfigReader


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

        # Load YAML configuration using BlenderYAMLConfigReader
        self.config_path = Path(config_path)
        self.reader = BlenderYAMLConfigReader(config_path)
        self.config = self.reader.config
        
        # Add config_data property for test compatibility
        self.config_data = self.config

        # Use reader properties for all attributes
        self.video_files = [Path(f) for f in self.reader.video_files]
        self.main_audio = Path(self.reader.main_audio) if self.reader.main_audio else None
        self.output_blend = Path(self.reader.output_blend) if self.reader.output_blend else None
        self.render_output = Path(self.reader.render_output) if self.reader.render_output else None
        self.fps = self.reader.fps
        self.resolution_x = self.reader.resolution_x
        self.resolution_y = self.reader.resolution_y
        self.beat_division = self.reader.beat_division

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

        raise ValueError("No YAML config file specified. Use --config argument or set CONFIG_PATH variable.")

    def validate_parameters(self) -> Tuple[bool, List[str]]:
        """
        Waliduj parametry konfiguracji.

        Returns:
            Tuple[bool, List[str]]: (czy_valid, lista_błędów)
        """
        # Use BlenderYAMLConfigReader's validation method
        return self.reader.validate()

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
        strip_animations = self.config.strip_animations
        total_animations = sum(len(anims) for anims in strip_animations.values())
        print(f"🎭 Checking animations: config has {total_animations} animations across {len(strip_animations)} strips")
        if strip_animations:
            print("🎭 Applying compositional animations...")
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
        layout = self.config.layout
        strip_animations = self.config.strip_animations
        total_animations = sum(len(anims) for anims in strip_animations.values())
        print(f"✓ Layout type: {layout.type}")
        print(f"✓ Animations configured: {total_animations} animations across {len(strip_animations)} strips")

        # Apply layout using YAML config
        success = self._apply_yaml_layout_and_animations(video_strips, animation_data)

        if success:
            print("✓ Compositional animations applied successfully")
        else:
            print("✗ Compositional animations failed")

        return success

    def _load_animation_data(self) -> Optional[Dict]:
        """
        Load animation data from audio analysis file specified in YAML config.

        Returns:
            Optional[Dict]: Animation data with events or None if not available
        """
        # Load audio analysis data from file specified in YAML config
        audio_analysis = self.config.audio_analysis
        print(f"🎵 Audio analysis file: {audio_analysis.file if audio_analysis.file else 'None'}")

        analysis_file = audio_analysis.file
        print(f"🎵 Loading from file: {analysis_file}")

        if not analysis_file:
            print("❌ No audio analysis file specified in YAML config")
            return None

        try:
            import json
            with open(analysis_file, 'r', encoding='utf-8') as f:
                full_data = json.load(f)
                print(f"🎵 Loaded from file successfully: {len(full_data)} keys")
        except Exception as e:
            print(f"❌ Failed to load from file {analysis_file}: {e}")
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
        from .vse.animation_compositor import AnimationCompositor

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
        from .vse.layouts import MainPipLayout, RandomLayout

        layout = self.config.layout
        layout_type = layout.type
        layout_config = layout.config if layout.config else {}

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
        from .vse.animations import AnimationFactory

        # Use reader.animations which automatically converts strip_animations to flat format
        animation_specs = self.reader.animations
        print(f"🎨 _create_animations_from_yaml: Found {len(animation_specs)} animation specs")
        
        # Use factory to create all animations
        animations = AnimationFactory.create_multiple(animation_specs)
        
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
        print(f"Layout: {configurator.config.layout.type}")
        print(f"Animations: {len(configurator.reader.animations)}")
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
