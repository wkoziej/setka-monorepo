"""
ABOUTME: YAML configuration classes for Blender VSE project configuration.
ABOUTME: Provides dataclasses for project, audio analysis, layout, and animation specifications.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
import yaml


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
class AnimationSpec:
    """Specification for individual animation with dynamic parameters."""

    type: str
    trigger: str
    target_strips: List[str]

    def __init__(self, type: str, trigger: str, target_strips: List[str], **kwargs):
        self.type = type
        self.trigger = trigger
        self.target_strips = target_strips

        # Store additional parameters as attributes
        for key, value in kwargs.items():
            setattr(self, key, value)


@dataclass
class BlenderYAMLConfig:
    """Complete YAML configuration for Blender VSE project."""

    project: ProjectConfig
    audio_analysis: AudioAnalysisConfig
    layout: LayoutConfig
    strip_animations: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    animations: List[AnimationSpec] = field(
        default_factory=list
    )  # Deprecated - use strip_animations

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for JSON serialization."""
        return {
            "project": {
                "video_files": self.project.video_files,
                "main_audio": self.project.main_audio,
                "output_blend": self.project.output_blend,
                "render_output": self.project.render_output,
                "fps": self.project.fps,
                "resolution": self.project.resolution,
                "beat_division": self.project.beat_division,
            },
            "audio_analysis": {
                "file": self.audio_analysis.file,
                "data": self.audio_analysis.data,
            },
            "layout": {"type": self.layout.type, "config": self.layout.config},
            "animations": [
                {
                    "type": anim.type,
                    "trigger": anim.trigger,
                    "target_strips": anim.target_strips,
                    **{
                        k: v
                        for k, v in anim.__dict__.items()
                        if k not in ("type", "trigger", "target_strips")
                    },
                }
                for anim in self.animations
            ],
        }


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
        "desaturate_pulse",
        "contrast_flash",
        "pip_switch",
        "opacity",
        "position",
    }

    VALID_TRIGGERS = {
        "bass",
        "beat",
        "energy_peaks",
        "one_time",
        "continuous",
        "sections",
    }

    VALID_LAYOUT_TYPES = {"random", "grid", "center", "fill", "main-pip"}

    def load_config(self, config_path: Path) -> BlenderYAMLConfig:
        """Load and validate YAML configuration."""
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                content = f.read()
            return self.load_from_string(content)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML syntax: {e}")

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
            raise ValueError(f"Invalid YAML syntax: {e}")

        # Parse sections
        project_data = data.get("project", {})
        audio_analysis_data = data.get("audio_analysis", {})
        layout_data = data.get("layout", {})
        animations_data = data.get("animations", [])
        strip_animations_data = data.get("strip_animations", {})

        # Create configuration objects
        project = self._parse_project_config(project_data)
        audio_analysis = self._parse_audio_analysis_config(audio_analysis_data)
        layout = self._parse_layout_config(layout_data)
        animations = self._parse_animations_config(animations_data)

        config = BlenderYAMLConfig(
            project=project,
            audio_analysis=audio_analysis,
            layout=layout,
            animations=animations,
            strip_animations=strip_animations_data,
        )

        # Validate configuration
        is_valid, errors = self.validate_config(config)
        if not is_valid:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")

        return config

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

    def _parse_animations_config(
        self, data: List[Dict[str, Any]]
    ) -> List[AnimationSpec]:
        """Parse animations configuration section."""
        animations = []
        for anim_data in data:
            anim_type = anim_data.get("type")
            trigger = anim_data.get("trigger")
            target_strips = anim_data.get("target_strips", [])

            if not anim_type or not trigger:
                raise ValueError("Animation must have 'type' and 'trigger' fields")

            # Extract additional parameters
            kwargs = {
                k: v
                for k, v in anim_data.items()
                if k not in ["type", "trigger", "target_strips"]
            }

            animation = AnimationSpec(
                type=anim_type, trigger=trigger, target_strips=target_strips, **kwargs
            )
            animations.append(animation)

        return animations

    def validate_config(self, config: BlenderYAMLConfig) -> Tuple[bool, List[str]]:
        """Validate configuration with fail-fast approach."""
        errors = []

        # Validate project
        # Empty video_files list is allowed for auto-discovery

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

        # Validate animations
        for i, animation in enumerate(config.animations):
            if animation.type not in self.VALID_ANIMATION_TYPES:
                errors.append(
                    f"Animation {i}: Invalid type '{animation.type}'. Must be one of {self.VALID_ANIMATION_TYPES}"
                )

            if animation.trigger not in self.VALID_TRIGGERS:
                errors.append(
                    f"Animation {i}: Invalid trigger '{animation.trigger}'. Must be one of {self.VALID_TRIGGERS}"
                )

        return len(errors) == 0, errors

    def convert_to_internal(self, config: BlenderYAMLConfig) -> Dict[str, Any]:
        """Convert BlenderYAMLConfig to internal format used by vse_script.py.

        Converts strip_animations (grouped format) to animations (flat format with target_strips).
        This is needed for backwards compatibility with vse_script.py.

        Args:
            config: BlenderYAMLConfig object to convert

        Returns:
            Dictionary in internal format expected by vse_script.py
        """
        # Start with project configuration
        internal_format = {
            "project": {
                "video_files": config.project.video_files,
                "main_audio": config.project.main_audio,
                "output_blend": config.project.output_blend,
                "render_output": config.project.render_output,
                "fps": config.project.fps,
                "beat_division": config.project.beat_division,
            },
            "layout": {
                "type": config.layout.type,
                "config": config.layout.config or {},
            },
            "audio_analysis": {
                "file": config.audio_analysis.file,
                "data": config.audio_analysis.data,
                "beat_division": config.audio_analysis.beat_division,
                "min_onset_interval": config.audio_analysis.min_onset_interval,
            },
        }

        # Add resolution if present
        if config.project.resolution:
            if isinstance(config.project.resolution, Resolution):
                internal_format["project"]["resolution"] = {
                    "width": config.project.resolution.width,
                    "height": config.project.resolution.height,
                }
            else:
                # Handle dict format for backwards compatibility
                internal_format["project"]["resolution"] = config.project.resolution

        # Keep original strip_animations format for unified_api
        internal_format["strip_animations"] = config.strip_animations

        # Also convert to flat animations list for backwards compatibility with vse_script.py
        flat_animations = []

        # First, convert strip_animations (new format)
        for strip_name, animations in config.strip_animations.items():
            if animations:  # Only include strips that have animations
                for animation in animations:
                    # Create copy and add target_strips
                    flat_animation = animation.copy()
                    flat_animation["target_strips"] = [strip_name]
                    flat_animations.append(flat_animation)

        # Then, add any legacy flat animations (for backwards compatibility)
        for animation in config.animations:
            flat_animation = {
                "type": animation.type,
                "trigger": animation.trigger,
                "target_strips": animation.target_strips or [],
            }
            # Add any additional properties from the animation spec
            for key, value in animation.__dict__.items():
                if (
                    key not in ["type", "trigger", "target_strips"]
                    and value is not None
                ):
                    flat_animation[key] = value

            flat_animations.append(flat_animation)

        internal_format["animations"] = flat_animations

        return internal_format
