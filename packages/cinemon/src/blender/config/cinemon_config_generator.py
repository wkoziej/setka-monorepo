# ABOUTME: CinemonConfigGenerator main class for simplified YAML configuration generation
# ABOUTME: Provides high-level APIs for preset-based and custom configuration creation

"""Main configuration generator for cinemon."""

import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

from .media_discovery import MediaDiscovery
from .preset_manager import PresetManager


class CinemonConfigGenerator:
    """
    Main generator class for cinemon YAML configurations.
    
    Provides high-level APIs for generating configurations from presets,
    custom parameters, and auto-discovery mechanisms.
    
    Example:
        generator = CinemonConfigGenerator()
        
        # Generate preset configuration
        config_path = generator.generate_preset("./recording", "vintage")
        
        # Generate custom configuration
        config_path = generator.generate_config(
            "./recording",
            layout={"type": "random", "config": {"seed": 42}},
            animations=[{"type": "scale", "trigger": "bass", "intensity": 0.3}]
        )
    """
    
    def __init__(self):
        """Initialize CinemonConfigGenerator."""
        self.preset_manager = PresetManager()
    
    def generate_preset(self, 
                       recording_dir: Union[str, Path], 
                       preset_name: str, 
                       **overrides) -> Path:
        """
        Generate configuration from preset template.
        
        Args:
            recording_dir: Path to recording directory
            preset_name: Name of preset to use
            **overrides: Parameter overrides (seed, main_audio, etc.)
            
        Returns:
            Path to generated configuration file
            
        Raises:
            FileNotFoundError: If recording directory invalid
            ValueError: If preset not found or validation fails
        """
        recording_dir = Path(recording_dir)
        
        # Discover and validate media files
        discovery = MediaDiscovery(recording_dir)
        validation_result = discovery.validate_structure()
        
        if not validation_result.is_valid:
            # Combine all validation errors into single message
            error_message = "; ".join(validation_result.errors)
            raise ValueError(f"Invalid recording directory: {error_message}")
        
        # Get preset configuration
        preset_config = self.preset_manager.get_preset(preset_name)
        
        # Determine main audio file
        main_audio = overrides.get("main_audio")
        if not main_audio:
            main_audio = discovery.detect_main_audio()
            if not main_audio:
                audio_files = discovery.discover_audio_files()
                if len(audio_files) > 1:
                    raise ValueError(
                        f"Multiple audio files found ({len(audio_files)}). "
                        f"Please specify main_audio parameter: {audio_files}"
                    )
        
        # Build configuration from preset
        config_data = self._build_config_from_preset(preset_config, main_audio, overrides, discovery)
        
        # Generate output file path
        output_file = recording_dir / f"animation_config_{preset_name}.yaml"
        
        # Write YAML configuration
        self._write_yaml_config(config_data, output_file)
        
        return output_file
    
    def generate_config(self, 
                       recording_dir: Union[str, Path],
                       layout: Dict[str, Any],
                       animations: List[Dict[str, Any]],
                       main_audio: Optional[str] = None,
                       project_overrides: Optional[Dict[str, Any]] = None,
                       **kwargs) -> Path:
        """
        Generate custom configuration from parameters.
        
        Args:
            recording_dir: Path to recording directory
            layout: Layout configuration
            animations: List of animation configurations
            main_audio: Main audio file (auto-detected if None)
            project_overrides: Project setting overrides
            **kwargs: Additional configuration parameters
            
        Returns:
            Path to generated configuration file
            
        Raises:
            FileNotFoundError: If recording directory invalid
            ValueError: If validation fails
        """
        recording_dir = Path(recording_dir)
        
        # Discover and validate media files
        discovery = MediaDiscovery(recording_dir)
        validation_result = discovery.validate_structure()
        
        if not validation_result.is_valid:
            error_message = "; ".join(validation_result.errors)
            raise ValueError(f"Invalid recording directory: {error_message}")
        
        # Determine main audio file if not specified
        if not main_audio:
            main_audio = discovery.detect_main_audio()
            if not main_audio:
                audio_files = discovery.discover_audio_files()
                if len(audio_files) > 1:
                    raise ValueError(
                        f"Multiple audio files found ({len(audio_files)}). "
                        f"Please specify main_audio parameter: {audio_files}"
                    )
        
        # Build custom configuration
        config_data = self._build_custom_config(
            layout, animations, main_audio, project_overrides, discovery, **kwargs
        )
        
        # Generate output file path
        output_file = recording_dir / "animation_config.yaml"
        
        # Write YAML configuration
        self._write_yaml_config(config_data, output_file)
        
        return output_file
    
    def generate_template(self, 
                         recording_dir: Union[str, Path],
                         **params) -> Path:
        """
        Generate template configuration for manual editing.
        
        Args:
            recording_dir: Path to recording directory
            **params: Template parameters
            
        Returns:
            Path to generated template file
        """
        # Use minimal preset as template base
        return self.generate_preset(recording_dir, "minimal", **params)
    
    def discover_media_files(self, recording_dir: Union[str, Path]) -> MediaDiscovery:
        """
        Discover media files in recording directory.
        
        Args:
            recording_dir: Path to recording directory
            
        Returns:
            MediaDiscovery instance with discovered files
        """
        return MediaDiscovery(Path(recording_dir))
    
    def validate_recording_structure(self, recording_dir: Union[str, Path]):
        """
        Validate recording directory structure.
        
        Args:
            recording_dir: Path to recording directory
            
        Returns:
            ValidationResult with validation status
        """
        discovery = MediaDiscovery(Path(recording_dir))
        return discovery.validate_structure()
    
    def _build_config_from_preset(self, 
                                 preset_config, 
                                 main_audio: str, 
                                 overrides: Dict[str, Any],
                                 discovery: 'MediaDiscovery') -> Dict[str, Any]:
        """
        Build configuration from preset template.
        
        Args:
            preset_config: PresetConfig object
            main_audio: Main audio filename
            overrides: Parameter overrides
            discovery: MediaDiscovery instance to use
            
        Returns:
            Complete configuration dictionary
        """
        # Start with preset base
        layout = preset_config.layout.copy()
        animations = [anim.copy() for anim in preset_config.animations]
        
        # Apply overrides to layout
        if "seed" in overrides:
            layout["config"]["seed"] = overrides["seed"]
        
        # Apply other layout overrides
        layout_overrides = overrides.get("layout_config", {})
        layout["config"].update(layout_overrides)
        
        # Get video files from the discovery instance
        video_files = discovery.discover_video_files()
        
        # Auto-detect audio analysis file
        analysis_files = discovery.discover_analysis_files()
        analysis_file = None
        if analysis_files:
            # Use the first analysis file found
            analysis_file = f"analysis/{analysis_files[0]}"
        
        # Build complete configuration
        config_data = {
            "project": {
                "video_files": video_files,
                "main_audio": main_audio,
                "fps": overrides.get("fps", 30),
                "resolution": {
                    "width": overrides.get("width", 1920),
                    "height": overrides.get("height", 1080)
                }
            },
            "audio_analysis": {
                "beat_division": overrides.get("beat_division", 4),
                "min_onset_interval": overrides.get("min_onset_interval", 0.5),
                "file": analysis_file
            },
            "layout": layout,
            "animations": animations
        }
        
        return config_data
    
    def _build_custom_config(self, 
                            layout: Dict[str, Any],
                            animations: List[Dict[str, Any]], 
                            main_audio: str,
                            project_overrides: Optional[Dict[str, Any]] = None,
                            discovery: 'MediaDiscovery' = None,
                            **kwargs) -> Dict[str, Any]:
        """
        Build custom configuration from parameters.
        
        Args:
            layout: Layout configuration
            animations: Animation configurations
            main_audio: Main audio filename
            project_overrides: Project setting overrides
            discovery: MediaDiscovery instance to use
            **kwargs: Additional parameters
            
        Returns:
            Complete configuration dictionary
        """
        # Get video files from the discovery instance
        video_files = discovery.discover_video_files()
        
        # Auto-detect audio analysis file
        analysis_files = discovery.discover_analysis_files()
        analysis_file = None
        if analysis_files:
            # Use the first analysis file found
            analysis_file = f"analysis/{analysis_files[0]}"
        
        # Default project settings
        project_settings = {
            "video_files": video_files,
            "main_audio": main_audio,
            "fps": 30,
            "resolution": {
                "width": 1920,
                "height": 1080
            }
        }
        
        # Apply project overrides
        if project_overrides:
            project_settings.update(project_overrides)
        
        # Default audio analysis settings
        audio_analysis = {
            "beat_division": kwargs.get("beat_division", 4),
            "min_onset_interval": kwargs.get("min_onset_interval", 0.5),
            "file": analysis_file
        }
        
        config_data = {
            "project": project_settings,
            "audio_analysis": audio_analysis,
            "layout": layout,
            "animations": animations
        }
        
        return config_data
    
    def _write_yaml_config(self, config_data: Dict[str, Any], output_file: Path) -> None:
        """
        Write configuration to YAML file.
        
        Args:
            config_data: Configuration data
            output_file: Output file path
        """
        with output_file.open('w', encoding='utf-8') as f:
            yaml.dump(
                config_data, 
                f, 
                default_flow_style=False, 
                allow_unicode=True,
                indent=2,
                sort_keys=False
            )