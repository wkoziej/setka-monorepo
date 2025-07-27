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
    return_frames: NotRequired[int]
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
    """Loader and validator for YAML configuration files."""

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
            return self.load_from_string(content)
        except Exception as e:
            raise ValueError(f"Error reading file {file_path}: {e}")

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
            raise ValueError(f"Invalid YAML format: {e}")

        if data is None:
            raise ValueError("Empty YAML configuration")

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
                raise ValueError(f"Missing required section: {section}")

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
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")

        return config

    def load_config(self, config_path: Path) -> BlenderYAMLConfig:
        """Load and validate YAML configuration.

        This method is kept for backward compatibility.
        It delegates to load_from_file for consistency.
        """
        return self.load_from_file(config_path)

    def _parse_project_config(self, data: Dict[str, Any]) -> ProjectConfig:
        """Parse project configuration section."""
        video_files = data.get("video_files", [])
        if not isinstance(video_files, list):
            raise ValueError("video_files must be a list")

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

        # Validate project
        if not config.project.video_files:
            errors.append("Project must have at least one video file")

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
