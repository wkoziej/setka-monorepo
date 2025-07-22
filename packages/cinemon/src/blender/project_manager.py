"""
Blender Project Manager for OBS Canvas Recording VSE projects.

This module handles the creation and configuration of Blender VSE projects
from extracted OBS recordings using a parametric script approach.
"""

import subprocess
import os
from pathlib import Path
from typing import List, Optional
import logging

from setka_common.file_structure.types import MediaType
from setka_common.utils.files import find_files_by_type
from setka_common.config import BlenderYAMLConfig, YAMLConfigLoader

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
        self.script_path = Path(__file__).parent / "vse_script.py"


    def create_vse_project_with_config(
        self,
        recording_path: Path,
        yaml_config: BlenderYAMLConfig,
    ) -> Path:
        """
        Create a Blender VSE project using YAML configuration.

        Args:
            recording_path: Path to the recording directory
            yaml_config: YAML configuration object

        Returns:
            Path: Path to the created .blend file

        Raises:
            ValueError: If configuration is invalid
            RuntimeError: If Blender execution fails
        """
        from setka_common.file_structure.specialized import RecordingStructureManager
        import tempfile
        import yaml as yaml_module

        logger.info(f"Creating Blender VSE project with YAML config for: {recording_path}")

        # 1. Validate recording structure
        structure = RecordingStructureManager.find_recording_structure(recording_path)
        if not structure:
            raise ValueError(f"Invalid recording structure in: {recording_path}")

        # 2. Ensure blender directory exists
        blender_dir = RecordingStructureManager.ensure_blender_dir(recording_path)

        # 3. Resolve paths relative to recording directory and create resolved config
        resolved_config = self._create_resolved_config(yaml_config, recording_path, structure)
        
        # 4. Create temporary YAML file with resolved paths
        temp_config_file = None
        try:
            # Write resolved config to temporary YAML file
            import yaml
            temp_config_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8')
            
            # Convert to internal format for vse_script.py compatibility
            loader = YAMLConfigLoader()
            internal_config = loader.convert_to_internal(resolved_config)
            
            yaml.dump(internal_config, temp_config_file, indent=2, allow_unicode=True, default_flow_style=False)
            temp_config_file.close()
            
            logger.info(f"Created temporary config file: {temp_config_file.name}")
            logger.info(f"Video files: {resolved_config.project.video_files}")
            if resolved_config.project.main_audio:
                logger.info(f"Main audio: {resolved_config.project.main_audio}")
            logger.info(f"Animation mode: compositional with {len(internal_config.get('animations', []))} animations")

            # 5. Execute Blender with JSON config path
            output_blend = resolved_config.project.output_blend
            self._execute_blender_with_json_config(temp_config_file.name)
            
            logger.info(f"Blender project created successfully with YAML config: {output_blend}")
            return Path(output_blend)
            
        except Exception as e:
            logger.error(f"Failed to create Blender project with YAML config: {e}")
            raise RuntimeError(f"Blender execution failed: {e}")
        finally:
            # Clean up temporary file
            if temp_config_file:
                try:
                    import os
                    os.unlink(temp_config_file.name)
                    logger.debug(f"Cleaned up temporary config file: {temp_config_file.name}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary config file: {e}")



    def _execute_blender_with_json_config(self, config_path: str) -> None:
        """
        Execute Blender with the parametric script and JSON config file path.

        Args:
            config_path: Path to the JSON configuration file

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
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True
            )
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
    
    def _create_resolved_config(self, yaml_config: BlenderYAMLConfig, recording_path: Path, structure) -> BlenderYAMLConfig:
        """
        Create a new config with all paths resolved to absolute paths.
        
        Args:
            yaml_config: Original YAML configuration
            recording_path: Path to the recording directory
            structure: Recording structure manager
            
        Returns:
            BlenderYAMLConfig: New config with resolved paths
        """
        from setka_common.config.yaml_config import ProjectConfig, AudioAnalysisConfig, LayoutConfig
        
        # Resolve video files
        resolved_video_files = []
        for video_file in yaml_config.project.video_files:
            video_path = structure.extracted_dir / video_file
            if not video_path.exists():
                raise ValueError(f"Video file not found: {video_path}")
            resolved_video_files.append(str(video_path.resolve()))
        
        # Resolve main audio
        resolved_main_audio = None
        if yaml_config.project.main_audio:
            main_audio_path = structure.extracted_dir / yaml_config.project.main_audio
            if not main_audio_path.exists():
                raise ValueError(f"Main audio file not found: {main_audio_path}")
            resolved_main_audio = str(main_audio_path.resolve())
        
        # Resolve output paths
        project_name = recording_path.name
        blender_dir = structure.blender_dir if hasattr(structure, 'blender_dir') else recording_path / "blender"
        
        if yaml_config.project.output_blend:
            output_blend = recording_path / yaml_config.project.output_blend
        else:
            output_blend = blender_dir / f"{project_name}.blend"
        
        if yaml_config.project.render_output:
            render_output = recording_path / yaml_config.project.render_output
        else:
            render_output = blender_dir / "render" / f"{project_name}_final.mp4"
        
        # Ensure render output directory exists
        render_output.parent.mkdir(parents=True, exist_ok=True)
        
        # Resolve audio analysis file
        resolved_analysis_file = None
        if yaml_config.audio_analysis.file:
            analysis_file_path = recording_path / yaml_config.audio_analysis.file
            if analysis_file_path.exists():
                resolved_analysis_file = str(analysis_file_path.resolve())
        
        # Create resolved config objects
        resolved_project = ProjectConfig(
            video_files=resolved_video_files,
            main_audio=resolved_main_audio,
            output_blend=str(output_blend.resolve()),
            render_output=str(render_output.resolve()),
            fps=yaml_config.project.fps,
            resolution=yaml_config.project.resolution,
            beat_division=yaml_config.project.beat_division
        )
        
        resolved_audio_analysis = AudioAnalysisConfig(
            file=resolved_analysis_file,
            data=yaml_config.audio_analysis.data,
            beat_division=yaml_config.audio_analysis.beat_division,
            min_onset_interval=yaml_config.audio_analysis.min_onset_interval
        )
        
        resolved_layout = LayoutConfig(
            type=yaml_config.layout.type,
            config=yaml_config.layout.config
        )
        
        return BlenderYAMLConfig(
            project=resolved_project,
            audio_analysis=resolved_audio_analysis,
            layout=resolved_layout,
            animations=yaml_config.animations,
            strip_animations=yaml_config.strip_animations
        )
    
