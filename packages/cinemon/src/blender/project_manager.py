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

    def create_vse_project(
        self,
        recording_path: Path,
        main_audio_name: Optional[str] = None,
        animation_mode: str = "none",
        beat_division: int = 8,
    ) -> Path:
        """
        Create a Blender VSE project from extracted OBS recording.

        Args:
            recording_path: Path to the recording directory
            main_audio_name: Optional name of main audio file
            animation_mode: Animation mode for VSE ("none", "beat-switch", etc.)
            beat_division: Beat division for animation timing

        Returns:
            Path: Path to the created .blend file

        Raises:
            ValueError: If recording structure is invalid
            RuntimeError: If Blender execution fails
        """
        from setka_common.file_structure.specialized import RecordingStructureManager
        from beatrix import AudioValidator

        logger.info(f"Creating Blender VSE project for: {recording_path}")

        # 0. Validate input parameters
        self._validate_animation_mode(animation_mode)
        self._validate_beat_division(beat_division)

        # 1. Validate recording structure
        structure = RecordingStructureManager.find_recording_structure(recording_path)
        if not structure:
            raise ValueError(f"Invalid recording structure in: {recording_path}")

        # 2. Detect main audio file
        audio_validator = AudioValidator()
        main_audio = audio_validator.detect_main_audio(
            structure.extracted_dir, main_audio_name
        )
        logger.info(f"Main audio file: {main_audio.name}")

        # 3. Find video files
        video_files = self.find_video_files(structure.extracted_dir)
        if not video_files:
            raise ValueError(f"No video files found in: {structure.extracted_dir}")
        logger.info(f"Found {len(video_files)} video files")

        # 4. Ensure blender directory exists
        blender_dir = RecordingStructureManager.ensure_blender_dir(recording_path)

        # 5. Create output paths
        project_name = recording_path.name
        output_blend = blender_dir / f"{project_name}.blend"
        render_output = blender_dir / "render" / f"{project_name}_final.mp4"

        # 6. Read FPS from metadata
        fps = self._read_fps_from_metadata(structure.metadata_file)

        # 7. Find audio analysis file path if available and requested
        analysis_file_path = None
        if animation_mode != "none":
            # Build analysis file path based on audio file name
            analysis_dir = RecordingStructureManager.ensure_analysis_dir(recording_path)
            analysis_filename = f"{main_audio.stem}_analysis.json"
            analysis_file_path = analysis_dir / analysis_filename

            if analysis_file_path.exists():
                logger.info(
                    f"Found audio analysis file for animation mode: {animation_mode}"
                )
            else:
                logger.warning(
                    f"No audio analysis found for animation mode {animation_mode}"
                )

        # 8. Set up environment variables for the parametric script
        env_vars = self._prepare_environment_variables_with_analysis(
            video_files,
            main_audio,
            output_blend,
            render_output,
            fps,
            analysis_file_path,
            animation_mode,
            beat_division,
        )

        # 9. Execute Blender with the parametric script
        try:
            self._execute_blender_with_params(env_vars)
            logger.info(f"Blender project created successfully: {output_blend}")
            return output_blend
        except Exception as e:
            logger.error(f"Failed to create Blender project: {e}")
            raise RuntimeError(f"Blender execution failed: {e}")

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
            temp_config_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8')
            config_dict = self._convert_config_to_dict(resolved_config)
            yaml_module.dump(config_dict, temp_config_file, default_flow_style=False, allow_unicode=True)
            temp_config_file.close()
            
            logger.info(f"Created temporary config file: {temp_config_file.name}")
            logger.info(f"Video files: {resolved_config.project.video_files}")
            if resolved_config.project.main_audio:
                logger.info(f"Main audio: {resolved_config.project.main_audio}")
            logger.info(f"Animation mode: compositional with {len(resolved_config.animations)} animations")

            # 5. Execute Blender with YAML config path
            output_blend = resolved_config.project.output_blend
            self._execute_blender_with_yaml_config(temp_config_file.name)
            
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

    def _prepare_environment_variables(
        self,
        video_files: List[Path],
        main_audio: Path,
        output_blend: Path,
        render_output: Path,
        fps: int = 30,
    ) -> dict:
        """
        Prepare environment variables for the parametric Blender script.

        Args:
            video_files: List of video files to add to VSE
            main_audio: Main audio file path
            output_blend: Output .blend file path
            render_output: Render output path
            fps: Frames per second

        Returns:
            dict: Environment variables for the script
        """
        # Convert video files to comma-separated string
        video_files_str = ",".join(str(vf.resolve()) for vf in video_files)

        # Ensure render output directory exists
        render_output.parent.mkdir(parents=True, exist_ok=True)

        env_vars = {
            "BLENDER_VSE_VIDEO_FILES": video_files_str,
            "BLENDER_VSE_MAIN_AUDIO": str(main_audio.resolve()),
            "BLENDER_VSE_OUTPUT_BLEND": str(output_blend.resolve()),
            "BLENDER_VSE_RENDER_OUTPUT": str(render_output.resolve()),
            "BLENDER_VSE_FPS": str(fps),
            "BLENDER_VSE_RESOLUTION_X": "740",
            "BLENDER_VSE_RESOLUTION_Y": "554",
        }

        logger.debug(f"Prepared environment variables: {env_vars}")
        return env_vars

    def _execute_blender_with_params(self, env_vars: dict) -> None:
        """
        Execute Blender with the parametric script and environment variables.

        Args:
            env_vars: Environment variables for the script

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
            ]
        else:
            cmd = [
                self.blender_executable,
                "--background",
                "--python",
                str(self.script_path),
            ]

        # Prepare environment with script parameters
        env = os.environ.copy()
        env.update(env_vars)

        try:
            logger.debug(f"Executing command: {' '.join(cmd)}")
            logger.debug(f"Working directory: {os.getcwd()}")
            result = subprocess.run(
                cmd, env=env, capture_output=True, text=True, check=True
            )
            logger.info("Blender script executed successfully")
            logger.debug(f"Blender stdout: {result.stdout}")
            logger.debug(f"Blender stderr: {result.stderr}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Blender execution failed with return code {e.returncode}")
            logger.error(f"Blender stdout: {e.stdout}")
            logger.error(f"Blender stderr: {e.stderr}")
            raise RuntimeError(f"Blender execution failed: {e.stderr}")

    def _execute_blender_with_yaml_config(self, config_path: str) -> None:
        """
        Execute Blender with the parametric script and YAML config file path.

        Args:
            config_path: Path to the YAML configuration file

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

    def _prepare_environment_variables_with_analysis(
        self,
        video_files: List[Path],
        main_audio: Path,
        output_blend: Path,
        render_output: Path,
        fps: int = 30,
        analysis_file_path: Optional[Path] = None,
        animation_mode: str = "none",
        beat_division: int = 8,
    ) -> dict:
        """
        Prepare environment variables for the parametric Blender script with audio analysis.

        Args:
            video_files: List of video files to add to VSE
            main_audio: Main audio file path
            output_blend: Output .blend file path
            render_output: Render output path
            fps: Frames per second
            analysis_file_path: Optional path to audio analysis file
            animation_mode: Animation mode for VSE
            beat_division: Beat division for animation timing

        Returns:
            dict: Environment variables for the script
        """
        # Start with basic environment variables
        env_vars = self._prepare_environment_variables(
            video_files, main_audio, output_blend, render_output, fps
        )

        # Add audio analysis specific variables
        env_vars.update(
            {
                "BLENDER_VSE_ANIMATION_MODE": animation_mode,
                "BLENDER_VSE_BEAT_DIVISION": str(beat_division),
                "BLENDER_VSE_AUDIO_ANALYSIS_FILE": str(analysis_file_path)
                if analysis_file_path
                else "",
            }
        )

        logger.debug(
            f"Prepared environment variables with analysis: {list(env_vars.keys())}"
        )
        return env_vars

    def _serialize_analysis_data(self, analysis_data: Optional[dict]) -> str:
        """
        Serialize audio analysis data to JSON string for environment variable.

        Args:
            analysis_data: Audio analysis data or None

        Returns:
            str: JSON string of analysis data or empty string
        """
        if not analysis_data:
            return ""

        try:
            import json

            return json.dumps(analysis_data)
        except Exception as e:
            logger.warning(f"Failed to serialize analysis data: {e}")
            return ""

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
            data=yaml_config.audio_analysis.data
        )
        
        resolved_layout = LayoutConfig(
            type=yaml_config.layout.type,
            config=yaml_config.layout.config
        )
        
        return BlenderYAMLConfig(
            project=resolved_project,
            audio_analysis=resolved_audio_analysis,
            layout=resolved_layout,
            animations=yaml_config.animations
        )
    
    def _convert_config_to_dict(self, config: BlenderYAMLConfig) -> dict:
        """
        Convert BlenderYAMLConfig object to dictionary for YAML serialization.
        
        Args:
            config: YAML configuration object
            
        Returns:
            dict: Configuration as dictionary
        """
        config_dict = {
            "project": {
                "video_files": config.project.video_files,
                "main_audio": config.project.main_audio,
                "output_blend": config.project.output_blend,
                "render_output": config.project.render_output,
                "fps": config.project.fps,
                "beat_division": config.project.beat_division
            },
            "audio_analysis": {
                "file": config.audio_analysis.file,
                "data": config.audio_analysis.data
            },
            "layout": {
                "type": config.layout.type,
                "config": config.layout.config
            },
            "animations": []
        }
        
        # Add resolution if present
        if config.project.resolution:
            config_dict["project"]["resolution"] = config.project.resolution
        
        # Convert animations
        for animation in config.animations:
            anim_dict = {
                "type": animation.type,
                "trigger": animation.trigger,
                "target_strips": animation.target_strips
            }
            
            # Add dynamic parameters
            for attr_name in dir(animation):
                if not attr_name.startswith('_') and attr_name not in ['type', 'trigger', 'target_strips']:
                    value = getattr(animation, attr_name)
                    if not callable(value):
                        anim_dict[attr_name] = value
            
            config_dict["animations"].append(anim_dict)
        
        return config_dict
