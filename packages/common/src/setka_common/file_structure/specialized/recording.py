"""
ABOUTME: Recording-specific file structure for obsession
ABOUTME: Extends base structure with recording-specific directories
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import json
import logging

from ..base import MediaStructure, StructureManager
from ...utils.files import find_files_by_type, MediaType
from ...exceptions import (
    InvalidPathError,
    DirectoryCreationError,
)

logger = logging.getLogger(__name__)


@dataclass
class RecordingStructure(MediaStructure):
    """Structure for OBS recording projects."""
    extracted_dir: Path

    def exists(self) -> bool:
        """Check if recording structure exists."""
        return (
            self.project_dir.exists()
            and self.media_file.exists()
            and self.extracted_dir.exists()
        )

    def is_valid(self) -> bool:
        """Validate recording structure including metadata."""
        try:
            if not self.project_dir.exists():
                return False
            
            if not self.media_file.exists():
                return False
            
            if self.metadata_file.exists():
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    json.load(f)
            
            return True
        except (json.JSONDecodeError, IOError, OSError):
            return False


class RecordingStructureManager(StructureManager):
    """Manager for recording-specific structures."""
    
    # Directory names - single source of truth
    EXTRACTED_DIRNAME = "extracted"
    BLENDER_DIRNAME = "blender"
    ANALYSIS_DIRNAME = "analysis"
    
    @staticmethod
    def get_structure(video_path: Path) -> RecordingStructure:
        """Get recording structure.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            RecordingStructure instance
            
        Raises:
            InvalidPathError: When video_path is invalid
        """
        if not video_path:
            raise InvalidPathError("Video path cannot be empty")
        
        video_path = Path(video_path)
        
        if not video_path.name:
            raise InvalidPathError(f"Invalid video path: {video_path}")
        
        project_dir = video_path.parent
        
        metadata_file = project_dir / RecordingStructureManager.METADATA_FILENAME
        processed_dir = project_dir / RecordingStructureManager.PROCESSED_DIRNAME
        extracted_dir = project_dir / RecordingStructureManager.EXTRACTED_DIRNAME
        
        return RecordingStructure(
            project_dir=project_dir,
            media_file=video_path,
            metadata_file=metadata_file,
            processed_dir=processed_dir,
            extracted_dir=extracted_dir,
        )
    
    @staticmethod
    def create_structure(video_path: Path) -> RecordingStructure:
        """Create recording structure.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            RecordingStructure instance with created directories
            
        Raises:
            InvalidPathError: When video_path is invalid
            DirectoryCreationError: When directory creation fails
        """
        structure = RecordingStructureManager.get_structure(video_path)
        
        try:
            # Create all directories
            structure.extracted_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created recording structure: {structure.project_dir}")
        except (OSError, PermissionError) as e:
            raise DirectoryCreationError(
                f"Failed to create recording structure at {structure.project_dir}: {e}"
            )
        
        return structure

    @staticmethod
    def get_extracted_dir(video_path: Path) -> Path:
        """Get extracted directory for recording."""
        structure = RecordingStructureManager.get_structure(video_path)
        return structure.extracted_dir

    @staticmethod
    def find_recording_structure(base_path: Path) -> Optional[RecordingStructure]:
        """Find recording structure in directory.
        
        Args:
            base_path: Directory to search in
            
        Returns:
            RecordingStructure if found and valid, None otherwise
            
        Raises:
            InvalidPathError: When base_path is invalid
        """
        if not base_path:
            raise InvalidPathError("Base path cannot be empty")
        
        base_path = Path(base_path)
        
        if not base_path.exists():
            logger.debug(f"Base path does not exist: {base_path}")
            return None
        
        if not base_path.is_dir():
            logger.debug(f"Base path is not a directory: {base_path}")
            return None
        
        # Look for metadata.json
        metadata_file = base_path / RecordingStructureManager.METADATA_FILENAME
        if not metadata_file.exists():
            logger.debug(f"Metadata file not found: {metadata_file}")
            return None
        
        # Look for video files using FileExtensions
        try:
            video_files = find_files_by_type(base_path, MediaType.VIDEO)
        except Exception as e:
            logger.warning(f"Error finding video files in {base_path}: {e}")
            return None
        
        if not video_files:
            logger.debug(f"No video files found in {base_path}")
            return None
        
        # Use first video file found
        video_file = video_files[0]
        try:
            structure = RecordingStructureManager.get_structure(video_file)
            return structure if structure.is_valid() else None
        except InvalidPathError as e:
            logger.warning(f"Invalid video file path {video_file}: {e}")
            return None

    @staticmethod
    def ensure_blender_dir(recording_dir: Path) -> Path:
        """Ensure blender directory exists.
        
        Args:
            recording_dir: Recording directory path
            
        Returns:
            Path to blender directory
            
        Raises:
            InvalidPathError: When recording_dir is invalid
            DirectoryCreationError: When directory creation fails
        """
        if not recording_dir:
            raise InvalidPathError("Recording directory cannot be empty")
        
        recording_dir = Path(recording_dir)
        
        if not recording_dir.exists():
            raise InvalidPathError(f"Recording directory does not exist: {recording_dir}")
        
        if not recording_dir.is_dir():
            raise InvalidPathError(f"Recording path is not a directory: {recording_dir}")
        
        blender_dir = recording_dir / RecordingStructureManager.BLENDER_DIRNAME
        
        try:
            blender_dir.mkdir(parents=True, exist_ok=True)
            
            # Also create render subdirectory
            render_dir = blender_dir / "render"
            render_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Created blender directory: {blender_dir}")
            return blender_dir
        except (OSError, PermissionError) as e:
            raise DirectoryCreationError(
                f"Failed to create blender directory at {blender_dir}: {e}"
            )

    @staticmethod
    def ensure_analysis_dir(recording_dir: Path) -> Path:
        """Ensure analysis directory exists.
        
        Args:
            recording_dir: Recording directory path
            
        Returns:
            Path to analysis directory
            
        Raises:
            InvalidPathError: When recording_dir is invalid
            DirectoryCreationError: When directory creation fails
        """
        if not recording_dir:
            raise InvalidPathError("Recording directory cannot be empty")
        
        recording_dir = Path(recording_dir)
        
        if not recording_dir.exists():
            raise InvalidPathError(f"Recording directory does not exist: {recording_dir}")
        
        if not recording_dir.is_dir():
            raise InvalidPathError(f"Recording path is not a directory: {recording_dir}")
        
        analysis_dir = recording_dir / RecordingStructureManager.ANALYSIS_DIRNAME
        
        try:
            analysis_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created analysis directory: {analysis_dir}")
            return analysis_dir
        except (OSError, PermissionError) as e:
            raise DirectoryCreationError(
                f"Failed to create analysis directory at {analysis_dir}: {e}"
            )

    @staticmethod
    def get_analysis_file_path(video_path: Path) -> Path:
        """Get analysis file path for video.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Path to the analysis file
            
        Raises:
            InvalidPathError: When video_path is invalid
        """
        if not video_path:
            raise InvalidPathError("Video path cannot be empty")
        
        video_path = Path(video_path)
        
        if not video_path.name:
            raise InvalidPathError(f"Invalid video path: {video_path}")
        
        recording_dir = video_path.parent
        analysis_dir = recording_dir / RecordingStructureManager.ANALYSIS_DIRNAME
        
        analysis_filename = f"{video_path.stem}_analysis.json"
        return analysis_dir / analysis_filename

    @staticmethod
    def find_audio_analysis(video_path: Path) -> Optional[Path]:
        """Find existing audio analysis file.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Path to analysis file if exists, None otherwise
            
        Raises:
            InvalidPathError: When video_path is invalid
        """
        try:
            analysis_file = RecordingStructureManager.get_analysis_file_path(video_path)
            return analysis_file if analysis_file.exists() else None
        except InvalidPathError:
            logger.debug(f"Invalid video path for analysis lookup: {video_path}")
            return None
