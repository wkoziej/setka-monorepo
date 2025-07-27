# ABOUTME: YAML configuration loader for new strip_animations format
# ABOUTME: Validates and converts YAML presets to internal representation

"""YAML Configuration Loader for Cinemon Blender Addon."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    from .vendor import yaml
except ImportError:
    from vendor import yaml


class ValidationError(Exception):
    """Raised when YAML configuration validation fails."""

    pass


@dataclass
class Resolution:
    """Video resolution configuration."""

    width: int
    height: int


@dataclass
class ProjectConfig:
    """Project-level configuration."""

    video_files: List[str]
    fps: int
    main_audio: Optional[str] = None
    resolution: Optional[Resolution] = None


@dataclass
class LayoutConfig:
    """Layout configuration."""

    type: str
    config: Optional[Dict[str, Any]] = None


@dataclass
class AudioAnalysisConfig:
    """Audio analysis configuration."""

    file: str
    beat_division: Optional[int] = None
    min_onset_interval: Optional[float] = None


@dataclass
class CinemonConfig:
    """Complete Cinemon configuration."""

    project: ProjectConfig
    layout: LayoutConfig
    strip_animations: Dict[str, List[Dict[str, Any]]]
    audio_analysis: AudioAnalysisConfig


class YAMLConfigLoader:
    """Loads and validates YAML configuration files in new format."""

    # Valid animation types (synchronized with setka-common AnimationSpec)
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

    # Valid trigger types
    VALID_TRIGGER_TYPES = {"beat", "energy_peaks", "one_time", "bass", "treble"}

    # Valid layout types
    VALID_LAYOUT_TYPES = {"random", "grid", "cascade", "manual"}

    def load_from_file(self, file_path: Union[str, Path]) -> CinemonConfig:
        """Load configuration from YAML file.

        Args:
            file_path: Path to YAML configuration file

        Returns:
            Parsed and validated configuration

        Raises:
            ValidationError: If file doesn't exist or validation fails
        """
        path = Path(file_path)
        if not path.exists():
            raise ValidationError(f"Configuration file not found: {file_path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            return self.load_from_string(content)
        except Exception as e:
            raise ValidationError(f"Error reading file {file_path}: {e}")

    def load_from_string(self, yaml_content: str) -> CinemonConfig:
        """Load configuration from YAML string.

        Args:
            yaml_content: YAML configuration as string

        Returns:
            Parsed and validated configuration

        Raises:
            ValidationError: If YAML is invalid or validation fails
        """
        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise ValidationError(f"Invalid YAML format: {e}")

        if data is None:
            raise ValidationError("Empty YAML configuration")

        return self._validate_and_parse(data)

    def _validate_and_parse(self, data: Dict[str, Any]) -> CinemonConfig:
        """Validate YAML data and parse into configuration object.

        Args:
            data: Parsed YAML data

        Returns:
            Validated configuration object

        Raises:
            ValidationError: If validation fails
        """
        # Check required top-level sections
        required_sections = ["project", "layout", "strip_animations"]
        for section in required_sections:
            if section not in data:
                raise ValidationError(f"Missing required section: {section}")

        # Validate and parse project section
        project = self._parse_project(data["project"])

        # Validate and parse layout section
        layout = self._parse_layout(data["layout"])

        # Validate and parse strip animations
        strip_animations = self._parse_strip_animations(data["strip_animations"])

        # Validate and parse audio analysis (optional)
        audio_analysis = None
        if "audio_analysis" in data:
            audio_analysis = self._parse_audio_analysis(data["audio_analysis"])
        else:
            # Create default audio analysis config
            audio_analysis = AudioAnalysisConfig(file="./analysis/audio.json")

        return CinemonConfig(
            project=project,
            layout=layout,
            strip_animations=strip_animations,
            audio_analysis=audio_analysis,
        )

    def _parse_project(self, project_data: Dict[str, Any]) -> ProjectConfig:
        """Parse project configuration section."""
        if "video_files" not in project_data:
            raise ValidationError("Project section missing required field: video_files")

        if "fps" not in project_data:
            raise ValidationError("Project section missing required field: fps")

        video_files = project_data["video_files"]
        if not isinstance(video_files, list):
            raise ValidationError("video_files must be a list")
        # Empty list is allowed for auto-discovery in presets

        fps = project_data["fps"]
        if not isinstance(fps, int) or fps <= 0:
            raise ValidationError("fps must be a positive integer")

        main_audio = project_data.get("main_audio")

        resolution = None
        if "resolution" in project_data:
            res_data = project_data["resolution"]
            if "width" not in res_data or "height" not in res_data:
                raise ValidationError("Resolution must have width and height")
            resolution = Resolution(width=res_data["width"], height=res_data["height"])

        return ProjectConfig(
            video_files=video_files,
            fps=fps,
            main_audio=main_audio,
            resolution=resolution,
        )

    def _parse_layout(self, layout_data: Dict[str, Any]) -> LayoutConfig:
        """Parse layout configuration section."""
        if "type" not in layout_data:
            raise ValidationError("Layout section missing required field: type")

        layout_type = layout_data["type"]
        if layout_type not in self.VALID_LAYOUT_TYPES:
            raise ValidationError(f"Unknown layout type: {layout_type}")

        config = layout_data.get("config", {})

        return LayoutConfig(type=layout_type, config=config)

    def _parse_strip_animations(
        self, animations_data: Dict[str, Any]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Parse strip animations section."""
        if not isinstance(animations_data, dict):
            raise ValidationError("strip_animations must be a dictionary")

        validated_animations = {}

        for strip_name, animations in animations_data.items():
            if not isinstance(animations, list):
                raise ValidationError(
                    f"Animations for strip '{strip_name}' must be a list"
                )

            validated_strip_animations = []
            for animation in animations:
                validated_animation = self._validate_animation(animation, strip_name)
                validated_strip_animations.append(validated_animation)

            validated_animations[strip_name] = validated_strip_animations

        return validated_animations

    def _validate_animation(
        self, animation: Dict[str, Any], strip_name: str
    ) -> Dict[str, Any]:
        """Validate single animation configuration."""
        if "type" not in animation:
            raise ValidationError(
                f"Animation for strip '{strip_name}' missing required field: type"
            )

        animation_type = animation["type"]
        if animation_type not in self.VALID_ANIMATION_TYPES:
            raise ValidationError(f"Unknown animation type: {animation_type}")

        if "trigger" not in animation:
            raise ValidationError(
                f"Animation for strip '{strip_name}' missing required field: trigger"
            )

        trigger = animation["trigger"]
        if trigger not in self.VALID_TRIGGER_TYPES:
            raise ValidationError(f"Unknown trigger type: {trigger}")

        return animation.copy()

    def _parse_audio_analysis(self, audio_data: Dict[str, Any]) -> AudioAnalysisConfig:
        """Parse audio analysis configuration section."""
        if "file" not in audio_data:
            raise ValidationError("Audio analysis section missing required field: file")

        return AudioAnalysisConfig(
            file=audio_data["file"],
            beat_division=audio_data.get("beat_division"),
            min_onset_interval=audio_data.get("min_onset_interval"),
        )
