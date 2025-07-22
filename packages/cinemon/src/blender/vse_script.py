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
from pathlib import Path
from pathlib import Path
from typing import List, Optional, Tuple, Dict

# Import YAML configuration loader and Animation API
addon_path = Path(__file__).parent.parent.parent / "blender_addon"
if str(addon_path) not in sys.path:
    sys.path.insert(0, str(addon_path))

# Import Animation API for unified animation system
try:
    from unified_api import get_animation_api
    print("✓ Animation API imported successfully")
except ImportError as e:
    print(f"⚠ Warning: Could not import Animation API: {e}")
    get_animation_api = None

# NOTE: This import is kept for fallback compatibility but not used
# The actual config loading is done through setka-common later in the file

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
        """Inicjalizuj konfigurator z konfiguracji YAML.
        
        Args:
            config_path: Ścieżka do pliku konfiguracyjnego YAML
        """
        # Parse command line arguments if no config path provided
        if config_path is None:
            config_path = self._parse_command_line_args()
        
        # Load YAML configuration 
        self.config_path = Path(config_path)
        
        # Add vendor path for PyYAML (Blender doesn't have it)
        addon_vendor_path = Path(__file__).parent.parent.parent / "blender_addon" / "vendor"
        if str(addon_vendor_path) not in sys.path:
            sys.path.insert(0, str(addon_vendor_path))
        
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            raw_config = yaml.safe_load(f)
        
        # Detect format and convert if needed
        if "strip_animations" in raw_config:
            # This is grouped format (preset file) - need to convert to internal
            common_path = Path(__file__).parent.parent.parent.parent.parent / "common" / "src"
            if str(common_path) not in sys.path:
                sys.path.insert(0, str(common_path))
            
            from setka_common.config.yaml_config import YAMLConfigLoader
            
            loader = YAMLConfigLoader()
            # Write temp file and load through standard pipeline
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
                yaml.dump(raw_config, temp_file, default_flow_style=False, allow_unicode=True)
                temp_path = temp_file.name
            
            try:
                config_obj = loader.load_config(Path(temp_path))
                print(f"🔍 DEBUG: Loaded config has {len(getattr(config_obj, 'strip_animations', {}))} strip_animations")
                # Convert to internal format
                self.config_data = loader.convert_to_internal(config_obj)
                print(f"🔍 DEBUG: After conversion has {len(self.config_data.get('animations', []))} animations")
            finally:
                import os
                os.unlink(temp_path)
        else:
            # This is already internal format (from project_manager.py)
            self.config_data = raw_config
        
        # Set attributes from config (maintaining compatibility)
        project = self.config_data['project']
        print(f"🎬 VSE script received video_files: {project['video_files']}")
        
        # Resolve relative paths to absolute paths relative to config file directory
        config_dir = self.config_path.parent
        resolved_video_files = []
        for video_file in project['video_files']:
            video_path = Path(video_file)
            if not video_path.is_absolute():
                # Try relative to config directory first
                resolved_path = config_dir / video_path
                if not resolved_path.exists():
                    # Try relative to config_dir/extracted/ (standard structure)
                    resolved_path = config_dir / "extracted" / video_path
                if resolved_path.exists():
                    resolved_video_files.append(resolved_path.resolve())
                else:
                    print(f"❌ Video file not found: {video_path} (tried {config_dir / video_path} and {config_dir / 'extracted' / video_path})")
                    resolved_video_files.append(video_path)  # Keep original if not found
            else:
                resolved_video_files.append(Path(video_file))
        
        self.video_files = resolved_video_files
        print(f"🎬 VSE script resolved video_files: {[str(p) + ' (absolute: ' + str(p.is_absolute()) + ', exists: ' + str(p.exists()) + ')' for p in self.video_files]}")
        
        # Resolve main_audio path similar to video files
        if project.get('main_audio'):
            main_audio_path = Path(project['main_audio'])
            if not main_audio_path.is_absolute():
                # Try relative to config directory first  
                resolved_audio = config_dir / main_audio_path
                if not resolved_audio.exists():
                    # Try relative to config_dir/extracted/ (standard structure)
                    resolved_audio = config_dir / "extracted" / main_audio_path
                if resolved_audio.exists():
                    self.main_audio = resolved_audio.resolve()
                else:
                    print(f"❌ Main audio file not found: {main_audio_path}")
                    self.main_audio = main_audio_path
            else:
                self.main_audio = main_audio_path
            print(f"🎬 VSE script resolved main_audio: {self.main_audio} (absolute: {self.main_audio.is_absolute()}, exists: {self.main_audio.exists()})")
        else:
            self.main_audio = None
        # Set output_blend - if not specified, generate default path based on config location
        if project.get('output_blend'):
            self.output_blend = Path(project['output_blend'])
        else:
            # Generate default output path: config_dir/blender/{config_name}.blend
            config_name = self.config_path.stem.replace('animation_config_', '').replace('animation_config', 'project')
            self.output_blend = config_dir / "blender" / f"{config_name}.blend"
            print(f"🎬 Generated default output_blend: {self.output_blend}")
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
        
        raise ValueError("No YAML config file specified. Use --config argument or set CONFIG_PATH variable.")

    def validate_parameters(self) -> Tuple[bool, List[str]]:
        """
        Waliduj parametry konfiguracji.

        Returns:
            Tuple[bool, List[str]]: (czy_valid, lista_błędów)
        """
        # Validation for internal format (converted from YAML)
        errors = []
        required_keys = ['project', 'audio_analysis', 'layout', 'animations']
        for key in required_keys:
            if key not in self.config_data:
                errors.append(f"Missing required key: {key}")
        
        # Additional validation
        project = self.config_data.get('project', {})
        # Empty video_files is allowed for auto-discovery in presets
        
        if not project.get('fps'):
            errors.append("FPS not specified in project")
        
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
        print(f"🎭 Checking strip_animations: config has {len(self.config_data.get('strip_animations', {}))} strips with animations")
        print(f"🎭 Config keys: {list(self.config_data.keys())}")
        animation_success = True
        
        # Use unified Animation API - no fallbacks!
        if self.config_data.get('animations') or self.config_data.get('strip_animations'):
            if not get_animation_api:
                print("❌ Animation API not available - cannot apply animations")
                return False
                
            print("🎭 Using unified Animation API for animations...")
            animation_success = self._apply_animations_via_api()
            if not animation_success:
                print("❌ Failed to apply animations via Animation API")
                return False

        # Save project once at the end, after all setup and animations
        if self.output_blend:
            try:
                # Verify layout and strips before final save
                sequencer = bpy.context.scene.sequence_editor
                if sequencer:
                    strips_count = len(sequencer.sequences)
                    video_strips = [s for s in sequencer.sequences if s.type == 'MOVIE']
                    video_strips_count = len(video_strips)
                    print(f"🎬 Before final save: {strips_count} total sequences, {video_strips_count} video strips")
                    
                    # Verify layout positions for debugging
                    if video_strips_count > 0:
                        print("🎬 Layout verification:")
                        for i, strip in enumerate(video_strips):
                            if hasattr(strip, 'transform'):
                                pos_x = strip.transform.offset_x
                                pos_y = strip.transform.offset_y
                                scale = strip.transform.scale_x
                                print(f"  Strip {i+1} ({strip.name}): pos=({pos_x}, {pos_y}), scale={scale}")
                            else:
                                print(f"  Strip {i+1} ({strip.name}): No transform property")
                    
                    if video_strips_count == 0:
                        print("⚠ Warning: No video strips found before save - this indicates a problem!")
                else:
                    print("🎬 Before final save: No sequence editor found")
                    return False
                
                
                bpy.ops.wm.save_as_mainfile(filepath=str(self.output_blend))
                success_msg = "z animacjami" if animation_success and self.config_data['animations'] else "podstawowy"
                print(f"✓ Zapisano projekt {success_msg}: {self.output_blend}")
            except Exception as e:
                print(f"✗ Błąd zapisywania projektu: {e}")
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
        Load animation data from audio analysis file specified in YAML config.

        Returns:
            Optional[Dict]: Animation data with events or None if not available
        """
        # Load audio analysis data from file specified in YAML config
        audio_analysis = self.config_data.get('audio_analysis', {})
        print(f"🎵 Audio analysis section: {audio_analysis.keys() if audio_analysis else 'None'}")
        
        analysis_file = audio_analysis.get('file')
        print(f"🎵 Loading from file: {analysis_file}")
        
        if not analysis_file:
            print("❌ No audio analysis file specified in YAML config")
            return None
            
        try:
            # Resolve relative paths relative to config file directory or recording directory
            analysis_path = Path(analysis_file)
            if not analysis_path.is_absolute():
                # Try relative to config directory first
                if hasattr(self, 'config_path') and self.config_path:
                    config_dir = self.config_path.parent
                    resolved_path = config_dir / analysis_file
                    if resolved_path.exists():
                        analysis_path = resolved_path
                    else:
                        print(f"🎵 Analysis file not found relative to config: {resolved_path}")
                        # Try relative to recording directory (parent of config directory)
                        recording_dir = config_dir
                        resolved_path = recording_dir / analysis_file
                        if resolved_path.exists():
                            analysis_path = resolved_path
                        else:
                            print(f"🎵 Analysis file not found relative to recording: {resolved_path}")
                            return None
                else:
                    # Fallback: try relative to first video file directory
                    if self.video_files:
                        video_dir = self.video_files[0].parent.parent  # Go up from extracted/ to recording/
                        resolved_path = video_dir / analysis_file
                        if resolved_path.exists():
                            analysis_path = resolved_path
                        else:
                            print(f"🎵 Analysis file not found relative to video directory: {resolved_path}")
                            return None
                    else:
                        print(f"🎵 Cannot resolve relative path {analysis_file} - no config_path or video files")
                        return None
            
            print(f"🎵 Resolved analysis file path: {analysis_path}")
            
            import json
            with open(analysis_path, 'r', encoding='utf-8') as f:
                full_data = json.load(f)
                print(f"🎵 Loaded from file successfully: {len(full_data)} keys")
        except Exception as e:
            print(f"❌ Failed to load from file {analysis_path}: {e}")
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

    def _apply_animations_via_api(self) -> bool:
        """Apply animations using unified Animation API.
        
        Returns:
            bool: True if animations applied successfully
        """
        try:
            # Get Animation API instance
            api = get_animation_api()
            
            # Load audio analysis data
            audio_data = self._load_animation_data()
            
            # Extract preset name from config path
            preset_name = "custom"
            if hasattr(self, 'config_path') and self.config_path:
                config_name = self.config_path.name
                if config_name.startswith('animation_config_'):
                    preset_name = config_name.replace('animation_config_', '').replace('.yaml', '')
            
            print(f"🎭 Applying preset '{preset_name}' via Animation API")
            
            # Get recording path from the first video file or output blend path
            recording_path = None
            if self.video_files:
                recording_path = self.video_files[0].parent.parent  # Go up from extracted/video.mp4
            elif self.output_blend:
                recording_path = self.output_blend.parent.parent  # Go up from blender/project.blend
            
            if not recording_path:
                print("❌ Could not determine recording path")
                return False
            
            # Apply preset using unified API - it handles both layout and animations
            # Pass our already loaded config instead of loading preset by name
            result = api.apply_preset(
                recording_path=recording_path,
                preset_config=self.config_data,
                audio_analysis_data=audio_data
            )
            
            if result['success']:
                print(f"✅ Successfully applied preset '{preset_name}'")
                print(f"   Layout applied: {result['layout_applied']}")
                print(f"   Animations applied: {result['animations_applied']}")
                print(f"   Strips affected: {result['strips_affected']}")
                return True
            else:
                print(f"❌ Failed to apply preset '{preset_name}'")
                for error in result['errors']:
                    print(f"   Error: {error}")
                return False
            
        except Exception as e:
            print(f"❌ Error in _apply_animations_via_api: {e}")
            import traceback
            traceback.print_exc()
            return False

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
