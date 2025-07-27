"""
ABOUTME: YAML configuration module for Blender VSE - reads YAML config directly instead of environment variables.
ABOUTME: Provides native YAML reading capabilities for Blender scripts with validation and path resolution.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Import shared config classes
try:
    from setka_common.config.yaml_config import (
        BlenderYAMLConfig,
        YAMLConfigLoader,
    )
except ImportError:
    # Fallback when running in Blender environment
    sys.path.append('/home/wojtas/dev/setka-monorepo/packages/common/src')
    from setka_common.config.yaml_config import (
        BlenderYAMLConfig,
        YAMLConfigLoader,
    )


class BlenderYAMLConfigReader:
    """YAML configuration reader for Blender VSE scripts."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize YAML config reader.
        
        Args:
            config_path: Optional path to YAML config file
        """
        self.config_path = config_path
        self.config = None

        if config_path:
            self.load_config(config_path)

    def load_config(self, config_path: str) -> BlenderYAMLConfig:
        """
        Load YAML configuration from file.
        
        Args:
            config_path: Path to YAML configuration file
            
        Returns:
            BlenderYAMLConfig: Loaded configuration object
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid
        """
        config_file = Path(config_path)

        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        loader = YAMLConfigLoader()
        self.config = loader.load_config(config_file)

        return self.config

    @property
    def video_files(self) -> List[str]:
        """Get list of video files."""
        if not self.config:
            return []
        return self.config.project.video_files

    @property
    def main_audio(self) -> Optional[str]:
        """Get main audio file path."""
        if not self.config:
            return None
        return self.config.project.main_audio

    @property
    def output_blend(self) -> Optional[str]:
        """Get output blend file path."""
        if not self.config:
            return None
        return self.config.project.output_blend

    @property
    def render_output(self) -> Optional[str]:
        """Get render output path."""
        if not self.config:
            return None
        return self.config.project.render_output

    @property
    def fps(self) -> int:
        """Get FPS value."""
        if not self.config:
            return 30
        return self.config.project.fps

    @property
    def resolution_x(self) -> int:
        """Get resolution width."""
        if not self.config or not self.config.project.resolution:
            return 1920
        if hasattr(self.config.project.resolution, 'width'):
            return self.config.project.resolution.width
        return self.config.project.resolution.get("width", 1920)

    @property
    def resolution_y(self) -> int:
        """Get resolution height."""
        if not self.config or not self.config.project.resolution:
            return 1080
        if hasattr(self.config.project.resolution, 'height'):
            return self.config.project.resolution.height
        return self.config.project.resolution.get("height", 1080)

    @property
    def beat_division(self) -> int:
        """Get beat division value."""
        if not self.config:
            return 8
        return self.config.project.beat_division

    @property
    def layout_type(self) -> str:
        """Get layout type."""
        if not self.config:
            return "random"
        return self.config.layout.type

    @property
    def layout_config(self) -> Optional[Dict[str, Any]]:
        """Get layout configuration."""
        if not self.config:
            return None
        return self.config.layout.config

    @property
    def animations(self) -> List[Dict[str, Any]]:
        """Get list of animations (converted from strip_animations to flat format)."""
        if not self.config:
            return []
        
        # Convert strip_animations to flat animations list
        flat_animations = []
        for strip_name, animations in self.config.strip_animations.items():
            if animations:
                for animation in animations:
                    flat_animation = animation.copy()
                    flat_animation["target_strips"] = [strip_name]
                    flat_animations.append(flat_animation)
        
        return flat_animations

    @property
    def audio_analysis_file(self) -> Optional[str]:
        """Get audio analysis file path."""
        if not self.config:
            return None
        return self.config.audio_analysis.file

    @property
    def audio_analysis_data(self) -> Optional[Dict[str, Any]]:
        """Get audio analysis data."""
        if not self.config:
            return None
        return self.config.audio_analysis.data

    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate configuration.
        
        Returns:
            Tuple[bool, List[str]]: (is_valid, list_of_errors)
        """
        if not self.config:
            return False, ["No configuration loaded"]

        errors = []

        # Validate video files exist
        for video_file in self.config.project.video_files:
            video_path = Path(video_file)
            if not video_path.exists():
                errors.append(f"Video file not found: {video_file}")

        # Validate main audio exists
        if self.config.project.main_audio:
            audio_path = Path(self.config.project.main_audio)
            if not audio_path.exists():
                errors.append(f"Main audio file not found: {self.config.project.main_audio}")

        # Validate audio analysis file exists if specified
        if self.config.audio_analysis.file:
            analysis_path = Path(self.config.audio_analysis.file)
            if not analysis_path.exists():
                errors.append(f"Audio analysis file not found: {self.config.audio_analysis.file}")

        return len(errors) == 0, errors

    def load_audio_analysis_data(self) -> Optional[Dict[str, Any]]:
        """
        Load audio analysis data from file or embedded data.
        
        Returns:
            Optional[Dict]: Animation data with events or None if not available
        """
        if not self.config:
            return None

        # Try loading from file first
        if self.config.audio_analysis.file:
            analysis_path = Path(self.config.audio_analysis.file)
            if analysis_path.exists():
                try:
                    with open(analysis_path, 'r', encoding='utf-8') as f:
                        import json
                        return json.load(f)
                except Exception as e:
                    print(f"Error loading analysis file {analysis_path}: {e}")

        # Fallback to embedded data
        return self.config.audio_analysis.data
