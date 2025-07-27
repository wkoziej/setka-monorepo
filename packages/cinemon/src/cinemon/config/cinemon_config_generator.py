# ABOUTME: CinemonConfigGenerator main class for simplified YAML configuration generation
# ABOUTME: Provides high-level APIs for preset-based and custom configuration creation

"""Main configuration generator for cinemon."""

import copy
from pathlib import Path
from typing import Any, Dict, Union

import yaml
from setka_common.config.yaml_config import (
    BlenderYAMLConfig,
    Resolution,
)
from setka_common.utils import MediaDiscovery

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

        # Generate preset with overrides
        config_path = generator.generate_preset(
            "./recording",
            "vintage",
            seed=42,
            main_audio="main_audio.m4a"
        )
    """

    def __init__(self):
        """Initialize CinemonConfigGenerator."""
        self.preset_manager = PresetManager()

    def generate_preset(
        self, recording_dir: Union[str, Path], preset_name: str, **overrides
    ) -> Path:
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
        config = self._build_config_from_preset(
            preset_config, main_audio, overrides, discovery
        )

        # Generate output file path
        output_file = recording_dir / f"animation_config_{preset_name}.yaml"

        # Write YAML configuration
        self._write_yaml_config(config, output_file)

        return output_file

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

    def _build_config_from_preset(
        self,
        preset_config,
        main_audio: str,
        overrides: Dict[str, Any],
        discovery: "MediaDiscovery",
    ) -> Dict[str, Any]:
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
        # Deep copy the entire config to avoid modifying original
        config = copy.deepcopy(preset_config)

        # Apply overrides to layout
        if "seed" in overrides:
            if not config.layout.config:
                config.layout.config = {}
            config.layout.config["seed"] = overrides["seed"]

        # Apply other layout overrides
        layout_overrides = overrides.get("layout_config", {})
        if layout_overrides:
            if not config.layout.config:
                config.layout.config = {}
            config.layout.config.update(layout_overrides)

        # Get video files from the discovery instance
        video_files = discovery.discover_video_files()

        # Auto-detect audio analysis file
        analysis_files = discovery.discover_analysis_files()
        analysis_file = None
        if analysis_files:
            # Use the first analysis file found
            analysis_file = f"analysis/{analysis_files[0]}"

        # Update project settings
        config.project.video_files = video_files
        config.project.main_audio = main_audio

        if "fps" in overrides:
            config.project.fps = overrides["fps"]

        # Update resolution if provided
        if "width" in overrides or "height" in overrides:
            if not config.project.resolution:
                config.project.resolution = Resolution(width=1920, height=1080)
            if "width" in overrides:
                config.project.resolution.width = overrides["width"]
            if "height" in overrides:
                config.project.resolution.height = overrides["height"]

        # Update audio analysis settings
        if "beat_division" in overrides:
            config.audio_analysis.beat_division = overrides["beat_division"]
        if "min_onset_interval" in overrides:
            config.audio_analysis.min_onset_interval = overrides["min_onset_interval"]
        if analysis_file:
            config.audio_analysis.file = analysis_file

        return config

    def _write_yaml_config(self, config: BlenderYAMLConfig, output_file: Path) -> None:
        """
        Write configuration to YAML file.

        Args:
            config: BlenderYAMLConfig object
            output_file: Output file path
        """
        # Convert BlenderYAMLConfig to dict for YAML serialization
        config_dict = {
            "project": {
                "video_files": config.project.video_files,
                "main_audio": config.project.main_audio,
                "fps": config.project.fps,
                "resolution": {
                    "width": config.project.resolution.width
                    if config.project.resolution
                    else 1920,
                    "height": config.project.resolution.height
                    if config.project.resolution
                    else 1080,
                },
                "beat_division": config.project.beat_division,
            },
            "audio_analysis": {
                "file": config.audio_analysis.file,
                "beat_division": config.audio_analysis.beat_division,
                "min_onset_interval": config.audio_analysis.min_onset_interval,
            },
            "layout": {
                "type": config.layout.type,
                "config": config.layout.config or {},
            },
            "strip_animations": config.strip_animations,
        }

        # Remove None values for cleaner YAML
        if not config.project.main_audio:
            del config_dict["project"]["main_audio"]
        if not config.audio_analysis.file:
            del config_dict["audio_analysis"]["file"]
        if config.audio_analysis.beat_division is None:
            del config_dict["audio_analysis"]["beat_division"]
        if config.audio_analysis.min_onset_interval is None:
            del config_dict["audio_analysis"]["min_onset_interval"]

        # Remove empty audio_analysis if all fields are None
        if not any(config_dict["audio_analysis"].values()):
            del config_dict["audio_analysis"]

        with output_file.open("w", encoding="utf-8") as f:
            yaml.dump(
                config_dict,
                f,
                default_flow_style=False,
                allow_unicode=True,
                indent=2,
                sort_keys=False,
            )
