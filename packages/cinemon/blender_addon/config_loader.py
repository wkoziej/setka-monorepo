# ABOUTME: Wrapper for YAMLConfigLoader to provide backward compatibility
# ABOUTME: Adds load_from_string and convert_to_internal methods for tests

"""Wrapper for YAMLConfigLoader to maintain backward compatibility."""

import sys
from pathlib import Path
from typing import Any, Dict, Union

# Add vendor path for yaml
vendor_path = Path(__file__).parent / "vendor"
if str(vendor_path) not in sys.path:
    sys.path.insert(0, str(vendor_path))

import yaml
from setka_common.config.yaml_config import (
    AudioAnalysisConfig,
    BlenderYAMLConfig,
    LayoutConfig,
    ProjectConfig,
    Resolution,
)

# Import base config loader
from setka_common.config.yaml_config import YAMLConfigLoader as BaseYAMLConfigLoader

# Aliases for backward compatibility
CinemonConfig = BlenderYAMLConfig
ValidationError = ValueError


class YAMLConfigLoader(BaseYAMLConfigLoader):
    """Extended YAML configuration loader with additional methods."""

    def load_from_string(self, content: str) -> BlenderYAMLConfig:
        """Load configuration from YAML string.

        Args:
            content: YAML configuration as string

        Returns:
            Parsed and validated configuration

        Raises:
            ValueError: If validation fails
        """
        if not content or not content.strip():
            raise ValueError("Empty YAML configuration")

        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format: {e}")

        if data is None:
            raise ValueError("Empty YAML configuration")

        # Validate required sections
        if "project" not in data:
            raise ValueError("Missing required section: project")

        # Parse sections
        project_data = data.get("project", {})
        audio_analysis_data = data.get("audio_analysis", {})
        layout_data = data.get("layout", {})
        strip_animations_data = data.get("strip_animations", {})

        # Validate project section
        if "video_files" not in project_data:
            raise ValueError("Missing required field: project.video_files")
        if "fps" not in project_data:
            raise ValueError("Missing required field: project.fps")

        # Validate FPS
        fps = project_data.get("fps", 30)
        if not isinstance(fps, int) or fps <= 0:
            raise ValueError("fps must be a positive integer")

        # Validate resolution if provided
        resolution_data = project_data.get("resolution")
        resolution = None
        if resolution_data:
            if isinstance(resolution_data, dict):
                if "width" in resolution_data and "height" not in resolution_data:
                    raise ValueError("Resolution must have width and height")
                if "height" in resolution_data and "width" not in resolution_data:
                    raise ValueError("Resolution must have width and height")
                resolution = Resolution(
                    width=resolution_data.get("width", 1920),
                    height=resolution_data.get("height", 1080),
                )

        # Validate strip animations format
        for strip_name, animations in strip_animations_data.items():
            if not isinstance(animations, list):
                raise ValueError(f"Animations for strip '{strip_name}' must be a list")

            for i, anim in enumerate(animations):
                if not isinstance(anim, dict):
                    raise ValueError(
                        f"Animation {i} for strip '{strip_name}' must be a dictionary"
                    )

                # Check required fields
                if "type" not in anim:
                    raise ValueError(
                        f"Animation for strip '{strip_name}' missing required field: type"
                    )
                if "trigger" not in anim:
                    raise ValueError(
                        f"Animation for strip '{strip_name}' missing required field: trigger"
                    )

                # Validate animation type
                if anim["type"] not in self.VALID_ANIMATION_TYPES:
                    raise ValueError(f"Unknown animation type: {anim['type']}")

                # Validate trigger type
                if anim["trigger"] not in self.VALID_TRIGGERS:
                    raise ValueError(f"Unknown trigger type: {anim['trigger']}")

        # Create configuration objects
        project = ProjectConfig(
            video_files=project_data.get("video_files", []),
            main_audio=project_data.get("main_audio"),
            fps=fps,
            resolution=resolution,
        )

        audio_analysis = AudioAnalysisConfig(
            file=audio_analysis_data.get("file", "./analysis/audio.json"),
            beat_division=audio_analysis_data.get("beat_division"),
            min_onset_interval=audio_analysis_data.get("min_onset_interval"),
        )

        layout = LayoutConfig(
            type=layout_data.get("type", "random"), config=layout_data.get("config")
        )

        return BlenderYAMLConfig(
            project=project,
            audio_analysis=audio_analysis,
            layout=layout,
            strip_animations=strip_animations_data,
        )

    def load_from_file(self, file_path: Union[str, Path]) -> BlenderYAMLConfig:
        """Load configuration from YAML file.

        Args:
            file_path: Path to YAML configuration file

        Returns:
            Parsed and validated configuration

        Raises:
            ValueError: If file doesn't exist or validation fails
        """
        path = Path(file_path)
        if not path.exists():
            raise ValueError(f"Configuration file not found: {file_path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            return self.load_from_string(content)
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"Failed to load configuration: {e}")

    def convert_to_internal(self, config: BlenderYAMLConfig) -> Dict[str, Any]:
        """Convert configuration to internal format expected by VSE script.

        Args:
            config: Parsed configuration object

        Returns:
            Dictionary in internal format with flattened animations
        """
        # Flatten strip_animations into a list with target_strips
        animations = []
        for strip_name, strip_anims in config.strip_animations.items():
            for anim in strip_anims:
                animation_entry = anim.copy()
                animation_entry["target_strips"] = [strip_name]
                animations.append(animation_entry)

        return {
            "project": {
                "video_files": config.project.video_files,
                "main_audio": config.project.main_audio,
                "fps": config.project.fps,
                "resolution": config.project.resolution.__dict__
                if config.project.resolution
                else None,
            },
            "layout": {
                "type": config.layout.type,
                "config": config.layout.config or {},
            },
            "animations": animations,
            "audio_analysis": {
                "file": config.audio_analysis.file,
                "beat_division": config.audio_analysis.beat_division,
                "min_onset_interval": config.audio_analysis.min_onset_interval,
            },
        }
