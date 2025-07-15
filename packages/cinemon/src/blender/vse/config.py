"""
ABOUTME: Configuration module for Blender VSE - handles parameter parsing and validation.
ABOUTME: Centralizes environment variable parsing and provides consistent validation interface.
"""

import os
from pathlib import Path
from typing import List, Optional, Tuple

from .constants import BlenderConstants


class BlenderVSEConfig:
    """Configuration class for Blender VSE project parameters."""

    def __init__(self):
        """Initialize configuration from environment variables."""
        self.video_files = self._parse_video_files()
        self.main_audio = self._get_env_path("BLENDER_VSE_MAIN_AUDIO")
        self.output_blend = self._get_env_path("BLENDER_VSE_OUTPUT_BLEND")
        self.render_output = self._get_env_path("BLENDER_VSE_RENDER_OUTPUT")
        self.fps = self._get_env_int("BLENDER_VSE_FPS", BlenderConstants.DEFAULT_FPS)
        self.resolution_x = self._get_env_int(
            "BLENDER_VSE_RESOLUTION_X", BlenderConstants.DEFAULT_RESOLUTION_X
        )
        self.resolution_y = self._get_env_int(
            "BLENDER_VSE_RESOLUTION_Y", BlenderConstants.DEFAULT_RESOLUTION_Y
        )

        # Animation parameters
        self.animation_mode = os.getenv("BLENDER_VSE_ANIMATION_MODE", "none")
        self.beat_division = self._get_env_int("BLENDER_VSE_BEAT_DIVISION", 8)

    def _parse_video_files(self) -> List[Path]:
        """Parse list of video files from environment variable."""
        video_files_str = os.getenv("BLENDER_VSE_VIDEO_FILES", "")
        if not video_files_str:
            return []

        paths = []
        for path_str in video_files_str.split(","):
            path_str = path_str.strip()
            if path_str:
                paths.append(Path(path_str))
        return paths

    def _get_env_path(self, env_var: str) -> Optional[Path]:
        """Get path from environment variable."""
        path_str = os.getenv(env_var)
        return Path(path_str) if path_str else None

    def _get_env_int(self, env_var: str, default: int) -> int:
        """Get integer from environment variable with fallback to default."""
        try:
            value_str = os.getenv(env_var)
            if value_str is None:
                return default
            return int(float(value_str))
        except (ValueError, TypeError):
            return default

    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate configuration parameters.

        Returns:
            Tuple[bool, List[str]]: (is_valid, list_of_errors)
        """
        errors = []

        if not self.video_files:
            errors.append("Brak plików wideo (BLENDER_VSE_VIDEO_FILES)")

        for i, video_file in enumerate(self.video_files):
            if not video_file.exists():
                errors.append(f"Plik wideo {i + 1} nie istnieje: {video_file}")

        if self.main_audio and not self.main_audio.exists():
            errors.append(f"Główny plik audio nie istnieje: {self.main_audio}")

        if not self.output_blend:
            errors.append("Brak ścieżki wyjściowej .blend (BLENDER_VSE_OUTPUT_BLEND)")

        if not self.render_output:
            errors.append("Brak ścieżki renderowania (BLENDER_VSE_RENDER_OUTPUT)")

        if self.fps <= 0:
            errors.append(f"Nieprawidłowa wartość FPS: {self.fps}")

        if self.resolution_x <= 0 or self.resolution_y <= 0:
            errors.append(
                f"Nieprawidłowa rozdzielczość: {self.resolution_x}x{self.resolution_y}"
            )

        return len(errors) == 0, errors
