"""
ABOUTME: Recording-specific file structure for obsession
ABOUTME: Extends base structure with recording-specific directories
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..base import MediaStructure, StructureManager


@dataclass
class RecordingStructure(MediaStructure):
    """Structure for OBS recording projects."""
    extracted_dir: Path
    analysis_dir: Optional[Path] = None
    blender_dir: Optional[Path] = None


class RecordingStructureManager(StructureManager):
    """Manager for recording-specific structures."""
    
    EXTRACTED_DIRNAME = "extracted"
    
    @staticmethod
    def get_structure(video_path: Path) -> RecordingStructure:
        """Get recording structure."""
        base = StructureManager.get_structure(video_path)
        extracted_dir = base.project_dir / RecordingStructureManager.EXTRACTED_DIRNAME
        
        return RecordingStructure(
            project_dir=base.project_dir,
            media_file=base.media_file,
            metadata_file=base.metadata_file,
            processed_dir=base.processed_dir,
            extracted_dir=extracted_dir,
        )
    
    @staticmethod
    def create_structure(video_path: Path) -> RecordingStructure:
        """Create recording structure."""
        structure = RecordingStructureManager.get_structure(video_path)
        
        # Create all directories
        structure.processed_dir.mkdir(parents=True, exist_ok=True)
        structure.extracted_dir.mkdir(parents=True, exist_ok=True)
        
        return structure
