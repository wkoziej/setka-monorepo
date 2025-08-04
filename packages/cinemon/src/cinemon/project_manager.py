"""
Blender Project Manager for OBS Canvas Recording VSE projects.

This module handles the creation and configuration of Blender VSE projects
from extracted OBS recordings using a parametric script approach.
"""

import logging
import os
import subprocess
from pathlib import Path
from typing import List

from setka_common.config import BlenderYAMLConfig
from setka_common.file_structure.types import MediaType
from setka_common.utils.files import find_files_by_type

logger = logging.getLogger(__name__)


class BlenderProjectManager:
    """
    Manager for creating and configuring Blender VSE projects.

    This class handles the creation of Blender projects with Video Sequence Editor
    configured for extracted OBS Canvas recordings using a parametric script.
    """

    def __init__(self, blender_executable: str = "blender"):
        """
        Initialize BlenderProjectManager.

        Args:
            blender_executable: Path or command to Blender executable
        """
        self.blender_executable = blender_executable
        self.script_path = (
            Path(__file__).parent.parent.parent / "blender_addon" / "vse_script.py"
        )

    def create_vse_project_with_yaml_file(
        self,
        recording_path: Path,
        yaml_config_path: Path,
    ) -> Path:
        """
        Create a Blender VSE project using existing YAML configuration file.

        Args:
            recording_path: Path to the recording directory
            yaml_config_path: Path to existing YAML configuration file

        Returns:
            Path: Path to the created .blend file

        Raises:
            ValueError: If configuration is invalid
            RuntimeError: If Blender execution fails
        """
        from setka_common.file_structure.specialized import RecordingStructureManager

        logger.info(
            f"Creating Blender VSE project with YAML file for: {recording_path}"
        )

        # 1. Validate recording structure
        structure = RecordingStructureManager.find_recording_structure(recording_path)
        if not structure:
            raise ValueError(f"Invalid recording structure in: {recording_path}")

        # 2. Ensure blender directory exists
        RecordingStructureManager.ensure_blender_dir(recording_path)

        # 3. Validate YAML config file exists
        if not yaml_config_path.exists():
            raise ValueError(f"YAML config file not found: {yaml_config_path}")
        
        # 3a. Load config with path resolution enabled and validate base_directory
        from setka_common.config import YAMLConfigLoader
        loader = YAMLConfigLoader(resolve_paths=True)
        config = loader.load_config(yaml_config_path)
        
        # Validate base_directory exists (fail fast)
        if not config.project.base_directory:
            raise ValueError("base_directory required for Blender execution")
        
        # Validate base_directory matches recording_path
        config_base = Path(config.project.base_directory)
        if config_base.resolve() != recording_path.resolve():
            raise ValueError(f"Config base_directory {config_base} doesn't match recording_path {recording_path}")

        # 4. Determine output blend file path
        project_name = recording_path.name
        blender_dir = (
            structure.blender_dir
            if hasattr(structure, "blender_dir")
            else recording_path / "blender"
        )
        output_blend = blender_dir / f"{project_name}.blend"

        try:
            # 5. Execute Blender with existing YAML config file
            self._execute_blender_with_config(str(yaml_config_path))

            logger.info(
                f"Blender project created successfully with YAML file: {output_blend}"
            )
            return output_blend

        except Exception as e:
            logger.error(f"Failed to create Blender project with YAML file: {e}")
            raise RuntimeError(f"Blender execution failed: {e}")

    def _execute_blender_with_config(self, config_path: str) -> None:
        """
        Execute Blender with the parametric script and configuration file path.

        Args:
            config_path: Path to the configuration file (YAML or JSON)

        Raises:
            RuntimeError: If Blender execution fails
        """
        # Check if script exists
        if not self.script_path.exists():
            raise RuntimeError(f"Blender VSE script not found: {self.script_path}")

        # Use snap run blender if blender_executable is default
        if self.blender_executable == "blender":
            cmd = [
                "snap",
                "run",
                "blender",
                "--background",
                "--python",
                str(self.script_path),
                "--",  # Separator for Blender arguments vs script arguments
                "--config",
                config_path,
            ]
        else:
            cmd = [
                self.blender_executable,
                "--background",
                "--python",
                str(self.script_path),
                "--",  # Separator for Blender arguments vs script arguments
                "--config",
                config_path,
            ]

        try:
            logger.debug(f"Executing command: {' '.join(cmd)}")
            logger.debug(f"Working directory: {os.getcwd()}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            # Show any output for debugging
            if result.stdout.strip():
                logger.debug(f"Blender stdout: {result.stdout}")
            if result.stderr.strip():
                logger.debug(f"Blender stderr: {result.stderr}")
            logger.info("Blender script executed successfully with YAML config")
            logger.debug(f"Blender stdout: {result.stdout}")
            logger.debug(f"Blender stderr: {result.stderr}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Blender execution failed with return code {e.returncode}")
            logger.error(f"Blender stdout: {e.stdout}")
            logger.error(f"Blender stderr: {e.stderr}")
            raise RuntimeError(f"Blender execution failed: {e.stderr}")

    def _read_fps_from_metadata(self, metadata_file: Path) -> int:
        """
        Read FPS value from metadata.json file.

        Args:
            metadata_file: Path to metadata.json file

        Returns:
            int: FPS value (default: 30)
        """
        try:
            import json

            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)

            # Try to extract FPS from various possible fields
            fps = metadata.get("fps", 30)
            if isinstance(fps, str):
                fps = int(float(fps))

            logger.debug(f"Read FPS from metadata: {fps}")
            return fps
        except Exception as e:
            logger.warning(f"Could not read FPS from metadata: {e}, using default 30")
            return 30

    def find_video_files(self, extracted_dir: Path) -> List[Path]:
        """
        Find all video files in extracted directory.

        Args:
            extracted_dir: Path to extracted files directory

        Returns:
            List[Path]: List of video file paths
        """
        return find_files_by_type(extracted_dir, MediaType.VIDEO)

    def _validate_animation_mode(self, mode: str) -> None:
        """
        Validate animation mode parameter.

        Args:
            mode: Animation mode string

        Raises:
            ValueError: If mode is not valid
        """
        valid_modes = {
            "none",
            "beat-switch",
            "energy-pulse",
            "section-transition",
            "multi-pip",
            "compositional",
        }

        if mode not in valid_modes:
            raise ValueError(
                f"Invalid animation mode: {mode}. "
                f"Valid modes: {', '.join(sorted(valid_modes))}"
            )

    def _validate_beat_division(self, division: int) -> None:
        """
        Validate beat division parameter.

        Args:
            division: Beat division value

        Raises:
            ValueError: If division is not valid
        """
        valid_divisions = {1, 2, 4, 8, 16}

        if division not in valid_divisions:
            raise ValueError(
                f"Invalid beat division: {division}. "
                f"Valid divisions: {', '.join(map(str, sorted(valid_divisions)))}"
            )

