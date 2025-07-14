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
from ..types import FileExtensions
from ...utils.files import find_files_by_type, MediaType

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
        """Get recording structure."""
        video_path = Path(video_path)
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
        """Create recording structure."""
        structure = RecordingStructureManager.get_structure(video_path)
        
        # Create all directories
        structure.extracted_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created recording structure: {structure.project_dir}")
        
        return structure

    @staticmethod
    def get_extracted_dir(video_path: Path) -> Path:
        """Get extracted directory for recording."""
        structure = RecordingStructureManager.get_structure(video_path)
        return structure.extracted_dir

    @staticmethod
    def find_recording_structure(base_path: Path) -> Optional[RecordingStructure]:
        """Find recording structure in directory."""
        base_path = Path(base_path)
        
        if not base_path.exists() or not base_path.is_dir():
            return None
        
        # Look for metadata.json
        metadata_file = base_path / RecordingStructureManager.METADATA_FILENAME
        if not metadata_file.exists():
            return None
        
        # Look for video files using FileExtensions
        video_files = find_files_by_type(base_path, MediaType.VIDEO)
        
        if not video_files:
            return None
        
        # Use first video file found
        video_file = video_files[0]
        structure = RecordingStructureManager.get_structure(video_file)
        
        return structure if structure.is_valid() else None

    @staticmethod
    def ensure_blender_dir(recording_dir: Path) -> Path:
        """Ensure blender directory exists."""
        blender_dir = recording_dir / RecordingStructureManager.BLENDER_DIRNAME
        blender_dir.mkdir(parents=True, exist_ok=True)
        
        # Also create render subdirectory
        render_dir = blender_dir / "render"
        render_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Created blender directory: {blender_dir}")
        return blender_dir

    @staticmethod
    def ensure_analysis_dir(recording_dir: Path) -> Path:
        """Ensure analysis directory exists."""
        analysis_dir = recording_dir / RecordingStructureManager.ANALYSIS_DIRNAME
        analysis_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Created analysis directory: {analysis_dir}")
        return analysis_dir

    @staticmethod
    def get_analysis_file_path(video_path: Path) -> Path:
        """Get analysis file path for video."""
        video_path = Path(video_path)
        recording_dir = video_path.parent
        analysis_dir = recording_dir / RecordingStructureManager.ANALYSIS_DIRNAME
        
        analysis_filename = f"{video_path.stem}_analysis.json"
        return analysis_dir / analysis_filename

    @staticmethod
    def find_audio_analysis(video_path: Path) -> Optional[Path]:
        """Find existing audio analysis file."""
        analysis_file = RecordingStructureManager.get_analysis_file_path(video_path)
        return analysis_file if analysis_file.exists() else None
