"""
ABOUTME: YAML configuration classes for Blender VSE project configuration.
ABOUTME: Provides dataclasses for project, audio analysis, layout, and animation specifications.

Example YAML configuration structure:

```yaml
project:
  video_files: [Camera1.mp4, Camera2.mp4]
  main_audio: main_audio.m4a
  fps: 30
  resolution:
    width: 1920
    height: 1080

audio_analysis:
  file: analysis/audio_analysis.json

layout:
  type: random
  config:
    seed: 42
    margin: 0.1

strip_animations:
  Camera1:
    - type: scale
      trigger: bass
      intensity: 0.3
    - type: vintage_color
      trigger: one_time
      sepia_amount: 0.4
  Camera2:
    - type: shake
      trigger: beat
      intensity: 2.0
  all:  # Special key for applying to all strips
    - type: film_grain
      trigger: one_time
      intensity: 0.15
```

The `strip_animations` format groups animations by strip name, providing precise control
over which video strips receive which effects. Each strip can have multiple animations.
"""

from dataclasses import dataclass, field
from typing import (
    List,
    Optional,
    Dict,
    Any,
    Tuple,
    Union,
    TypedDict,
    Literal,
    NotRequired,
)
from pathlib import Path
import yaml


class ConfigValidationError(Exception):
    """Raised when YAML configuration validation fails."""

    pass


class AnimationSpec(TypedDict):
    """Type specification for individual animation configuration."""

    type: Literal[
        "scale",
        "shake",
        "rotation",
        "jitter",
        "brightness_flicker",
        "black_white",
        "film_grain",
        "vintage_color",
        "visibility",
        "pip_switch",
    ]
    trigger: Literal[
        "bass", "beat", "energy_peaks", "one_time", "continuous", "sections", "treble"
    ]
    # Optional parameters (use NotRequired for backward compatibility)
    intensity: NotRequired[float]
    duration_frames: NotRequired[int]
    degrees: NotRequired[float]
    sepia_amount: NotRequired[float]
    contrast_boost: NotRequired[float]
    grain_intensity: NotRequired[float]
    easing: NotRequired[str]


# Type alias for strip animations
StripAnimations = Dict[str, List[AnimationSpec]]


@dataclass
class Resolution:
    """Video resolution configuration."""

    width: int
    height: int


@dataclass
class ProjectConfig:
    """Configuration for Blender VSE project parameters."""

    video_files: List[str]
    main_audio: Optional[str] = None
    output_blend: Optional[str] = None
    render_output: Optional[str] = None
    fps: int = 30
    resolution: Optional[Resolution] = None
    beat_division: int = 8
    # Path resolution (only in generated configs, not presets)
    base_directory: Optional[str] = None  # Optional for presets compatibility


@dataclass
class AudioAnalysisConfig:
    """Configuration for audio analysis data."""

    file: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    beat_division: Optional[int] = None
    min_onset_interval: Optional[float] = None


@dataclass
class LayoutConfig:
    """Configuration for video layout parameters."""

    type: str = "random"
    config: Optional[Dict[str, Any]] = None


@dataclass
class BlenderYAMLConfig:
    """Complete YAML configuration for Blender VSE project."""

    project: ProjectConfig
    audio_analysis: AudioAnalysisConfig
    layout: LayoutConfig
    strip_animations: StripAnimations = field(default_factory=dict)


class YAMLConfigLoader:
    """Loader and validator for YAML configuration files.

    This class provides a centralized way to load and validate YAML configuration
    files for Blender VSE projects. It ensures all configurations conform to the
    expected structure and valid types.

    Example usage:
        loader = YAMLConfigLoader()

        # Load from file
        config = loader.load_from_file("animation_config.yaml")

        # Load from string
        yaml_str = '''
        project:
          video_files: [cam1.mp4, cam2.mp4]
          fps: 30
        layout:
          type: random
        strip_animations:
          cam1:
            - type: scale
              trigger: bass
              intensity: 0.5
        '''
        config = loader.load_from_string(yaml_str)

        # Validate existing config
        is_valid, errors = loader.validate_config(config)
    """

    def __init__(self, resolve_paths: bool = True):
        """Initialize loader with optional path resolution.

        Args:
            resolve_paths: If True, resolve relative paths using base_directory
        """
        self.resolve_paths = resolve_paths

    VALID_ANIMATION_TYPES = {
        "scale",
        "shake",
        "rotation",
        "jitter",
        "brightness_flicker",
        "black_white",
        "film_grain",
        "vintage_color",
        "visibility",
        "pip_switch",
    }

    VALID_TRIGGERS = {
        "bass",
        "beat",
        "energy_peaks",
        "one_time",
        "continuous",
        "sections",
        "treble",
    }

    VALID_LAYOUT_TYPES = {
        "random",
        "grid",
        "center",
        "fill",
        "main-pip",
        "cascade",
        "manual",
    }

    def load_from_file(self, file_path: Union[str, Path]) -> BlenderYAMLConfig:
        """Load configuration from YAML file.

        Args:
            file_path: Path to YAML configuration file

        Returns:
            Parsed and validated configuration

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If YAML is invalid or validation fails
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            config = self.load_from_string(content)

            # Resolve relative paths using base_directory (only if enabled and base_directory exists)
            if self.resolve_paths and config.project.base_directory:
                config = self._resolve_relative_paths(config)

            return config
        except Exception as e:
            raise ConfigValidationError(f"Error reading file {file_path}: {e}")

    def load_from_string(self, yaml_content: str) -> BlenderYAMLConfig:
        """Load configuration from YAML string.

        Args:
            yaml_content: YAML configuration as string

        Returns:
            Parsed and validated configuration

        Raises:
            ValueError: If YAML is invalid or validation fails
        """
        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise ConfigValidationError(f"Invalid YAML format: {e}")

        if data is None:
            raise ConfigValidationError("Empty YAML configuration")

        return self._parse_and_validate(data)

    def _parse_and_validate(self, data: Dict[str, Any]) -> BlenderYAMLConfig:
        """Parse YAML data and validate configuration.

        Args:
            data: Parsed YAML data

        Returns:
            Validated configuration object

        Raises:
            ValueError: If validation fails
        """
        # Check required top-level sections
        required_sections = ["project", "layout", "strip_animations"]
        for section in required_sections:
            if section not in data:
                raise ConfigValidationError(f"Missing required section: {section}")

        # Parse sections
        project_data = data.get("project", {})
        audio_analysis_data = data.get("audio_analysis", {})
        layout_data = data.get("layout", {})
        strip_animations_data = data.get("strip_animations", {})

        # Create configuration objects
        project = self._parse_project_config(project_data)
        audio_analysis = self._parse_audio_analysis_config(audio_analysis_data)
        layout = self._parse_layout_config(layout_data)

        config = BlenderYAMLConfig(
            project=project,
            audio_analysis=audio_analysis,
            layout=layout,
            strip_animations=strip_animations_data,
        )

        # Validate configuration
        is_valid, errors = self.validate_config(config)
        if not is_valid:
            raise ConfigValidationError(
                f"Configuration validation failed: {'; '.join(errors)}"
            )

        return config

    def load_config(self, config_path: Path) -> BlenderYAMLConfig:
        """Load and validate YAML configuration.

        This method is kept for backward compatibility.
        It delegates to load_from_file for consistency.
        """
        config = self.load_from_file(config_path)

        # Resolve relative paths using base_directory (only if enabled and base_directory exists)
        if self.resolve_paths and config.project.base_directory:
            config = self._resolve_relative_paths(config)

        return config

    def _parse_project_config(self, data: Dict[str, Any]) -> ProjectConfig:
        """Parse project configuration section."""
        video_files = data.get("video_files", [])
        if not isinstance(video_files, list):
            raise ConfigValidationError("video_files must be a list")

        # Parse resolution
        resolution_data = data.get("resolution")
        resolution = None
        if resolution_data:
            if isinstance(resolution_data, dict):
                resolution = Resolution(
                    width=resolution_data.get("width", 1920),
                    height=resolution_data.get("height", 1080),
                )
            else:
                resolution = resolution_data  # Backwards compatibility

        return ProjectConfig(
            video_files=video_files,
            main_audio=data.get("main_audio"),
            output_blend=data.get("output_blend"),
            render_output=data.get("render_output"),
            fps=data.get("fps", 30),
            resolution=resolution,
            beat_division=data.get("beat_division", 8),
            base_directory=data.get("base_directory"),
        )

    def _parse_audio_analysis_config(self, data: Dict[str, Any]) -> AudioAnalysisConfig:
        """Parse audio analysis configuration section."""
        return AudioAnalysisConfig(
            file=data.get("file"),
            data=data.get("data"),
            beat_division=data.get("beat_division"),
            min_onset_interval=data.get("min_onset_interval"),
        )

    def _parse_layout_config(self, data: Dict[str, Any]) -> LayoutConfig:
        """Parse layout configuration section."""
        return LayoutConfig(type=data.get("type", "random"), config=data.get("config"))

    def validate_config(self, config: BlenderYAMLConfig) -> Tuple[bool, List[str]]:
        """Validate configuration with fail-fast approach."""
        errors = []

        # Validate project - empty video_files allowed for auto-discovery
        # if not config.project.video_files:
        #     errors.append("Project must have at least one video file")

        if config.project.fps <= 0:
            errors.append("FPS must be greater than 0")

        if config.project.resolution:
            if isinstance(config.project.resolution, Resolution):
                width = config.project.resolution.width
                height = config.project.resolution.height
            else:
                # Backwards compatibility with dict
                width = config.project.resolution.get("width", 0)
                height = config.project.resolution.get("height", 0)

            if width <= 0 or height <= 0:
                errors.append("Resolution width and height must be greater than 0")

        # Validate layout
        if config.layout.type not in self.VALID_LAYOUT_TYPES:
            errors.append(
                f"Invalid layout type: {config.layout.type}. Must be one of {self.VALID_LAYOUT_TYPES}"
            )

        # Validate strip_animations
        for strip_name, animations in config.strip_animations.items():
            if not isinstance(animations, list):
                errors.append(f"Animations for strip '{strip_name}' must be a list")
                continue

            for j, animation in enumerate(animations):
                if not isinstance(animation, dict):
                    errors.append(
                        f"Strip '{strip_name}' animation {j}: Must be a dictionary"
                    )
                    continue

                if "type" not in animation:
                    errors.append(
                        f"Strip '{strip_name}' animation {j}: Missing required field 'type'"
                    )
                elif animation["type"] not in self.VALID_ANIMATION_TYPES:
                    errors.append(
                        f"Strip '{strip_name}' animation {j}: Invalid type '{animation['type']}'. Must be one of {self.VALID_ANIMATION_TYPES}"
                    )

                if "trigger" not in animation:
                    errors.append(
                        f"Strip '{strip_name}' animation {j}: Missing required field 'trigger'"
                    )
                elif animation["trigger"] not in self.VALID_TRIGGERS:
                    errors.append(
                        f"Strip '{strip_name}' animation {j}: Invalid trigger '{animation['trigger']}'. Must be one of {self.VALID_TRIGGERS}"
                    )

        return len(errors) == 0, errors

    def _resolve_relative_paths(self, config: BlenderYAMLConfig) -> BlenderYAMLConfig:
        """Resolve relative paths using base_directory.

        Args:
            config: Configuration with potential relative paths

        Returns:
            Configuration with resolved absolute paths
        """
        base_path = Path(config.project.base_directory)
        extracted_dir = base_path / "extracted"

        # Resolve video files to absolute paths
        resolved_video_files = []
        for video_file in config.project.video_files:
            if Path(video_file).is_absolute():
                resolved_video_files.append(video_file)
            else:
                resolved_video_files.append(str(extracted_dir / video_file))

        # Resolve main audio
        resolved_main_audio = None
        if config.project.main_audio:
            if Path(config.project.main_audio).is_absolute():
                resolved_main_audio = config.project.main_audio
            else:
                resolved_main_audio = str(extracted_dir / config.project.main_audio)

        # Resolve analysis file
        resolved_analysis_file = None
        if config.audio_analysis.file:
            if Path(config.audio_analysis.file).is_absolute():
                resolved_analysis_file = config.audio_analysis.file
            else:
                resolved_analysis_file = str(base_path / config.audio_analysis.file)

        # Resolve output_blend
        resolved_output_blend = None
        if config.project.output_blend:
            if Path(config.project.output_blend).is_absolute():
                resolved_output_blend = config.project.output_blend
            else:
                resolved_output_blend = str(base_path / config.project.output_blend)

        # Create new config with resolved paths
        return BlenderYAMLConfig(
            project=ProjectConfig(
                base_directory=config.project.base_directory,
                video_files=resolved_video_files,
                main_audio=resolved_main_audio,
                output_blend=resolved_output_blend,
                render_output=config.project.render_output,
                fps=config.project.fps,
                resolution=config.project.resolution,
                beat_division=config.project.beat_division,
            ),
            audio_analysis=AudioAnalysisConfig(
                file=resolved_analysis_file,
                data=config.audio_analysis.data,
                beat_division=config.audio_analysis.beat_division,
                min_onset_interval=config.audio_analysis.min_onset_interval,
            ),
            layout=config.layout,
            strip_animations=config.strip_animations,
        )

    def _validate_for_blender_execution(self, config: BlenderYAMLConfig):
        """Validate config is ready for Blender execution.

        Args:
            config: Configuration to validate

        Raises:
            ConfigValidationError: If validation fails
        """
        if not config.project.base_directory:
            raise ConfigValidationError("base_directory required for Blender execution")

        if not config.project.video_files:
            raise ConfigValidationError("video_files required for Blender execution")

        base_dir = Path(config.project.base_directory)
        if not base_dir.exists():
            raise ConfigValidationError(f"Base directory does not exist: {base_dir}")
