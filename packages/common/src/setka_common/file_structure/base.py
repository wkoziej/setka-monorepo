"""
ABOUTME: Core file structure management for media projects
ABOUTME: Provides base classes for organizing media files and directories
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class MediaStructure:
    """Universal structure for media projects."""
    
    project_dir: Path
    media_file: Path
    metadata_file: Path
    processed_dir: Path
    
    def exists(self) -> bool:
        """Check if structure exists in filesystem."""
        return (
            self.project_dir.exists()
            and self.media_file.exists()
            and self.processed_dir.exists()
        )
    
    def is_valid(self) -> bool:
        """Validate structure including metadata."""
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


class StructureManager:
    """Base manager for media file structures."""
    
    METADATA_FILENAME = "metadata.json"
    PROCESSED_DIRNAME = "processed"
    
    @staticmethod
    def get_structure(media_path: Path, structure_type: str = "generic") -> MediaStructure:
        """Get structure for media file."""
        media_path = Path(media_path)
        project_dir = media_path.parent
        
        metadata_file = project_dir / StructureManager.METADATA_FILENAME
        processed_dir = project_dir / StructureManager.PROCESSED_DIRNAME
        
        return MediaStructure(
            project_dir=project_dir,
            media_file=media_path,
            metadata_file=metadata_file,
            processed_dir=processed_dir,
        )
    
    @staticmethod
    def create_structure(media_path: Path) -> MediaStructure:
        """Create structure in filesystem."""
        structure = StructureManager.get_structure(media_path)
        
        structure.processed_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created structure: {structure.project_dir}")
        
        return structure
    
    @staticmethod
    def ensure_directory(base_path: Path, dirname: str) -> Path:
        """Ensure directory exists."""
        dir_path = base_path / dirname
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path
