"""
ABOUTME: Core file structure management for media projects
ABOUTME: Provides base classes for organizing media files and directories
"""

from dataclasses import dataclass
from pathlib import Path
import json
import logging

from ..exceptions import InvalidPathError, DirectoryCreationError

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
    def get_structure(
        media_path: Path, structure_type: str = "generic"
    ) -> MediaStructure:
        """Get structure for media file.

        Args:
            media_path: Path to the media file
            structure_type: Type of structure (for future use)

        Returns:
            MediaStructure instance

        Raises:
            InvalidPathError: When media_path is invalid
        """
        if not media_path:
            raise InvalidPathError("Media path cannot be empty")

        media_path = Path(media_path)

        if not media_path.name:
            raise InvalidPathError(f"Invalid media path: {media_path}")

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
        """Create structure in filesystem.

        Args:
            media_path: Path to the media file

        Returns:
            MediaStructure instance with created directories

        Raises:
            InvalidPathError: When media_path is invalid
            DirectoryCreationError: When directory creation fails
        """
        structure = StructureManager.get_structure(media_path)

        try:
            structure.processed_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created structure: {structure.project_dir}")
        except (OSError, PermissionError) as e:
            raise DirectoryCreationError(
                f"Failed to create structure at {structure.project_dir}: {e}"
            )

        return structure

    @staticmethod
    def ensure_directory(base_path: Path, dirname: str) -> Path:
        """Ensure directory exists.

        Args:
            base_path: Base directory path
            dirname: Name of directory to create

        Returns:
            Path to the created directory

        Raises:
            InvalidPathError: When base_path is invalid
            DirectoryCreationError: When directory creation fails
        """
        if not base_path:
            raise InvalidPathError("Base path cannot be empty")

        if not dirname:
            raise InvalidPathError("Directory name cannot be empty")

        base_path = Path(base_path)

        if not base_path.exists():
            raise InvalidPathError(f"Base path does not exist: {base_path}")

        if not base_path.is_dir():
            raise InvalidPathError(f"Base path is not a directory: {base_path}")

        dir_path = base_path / dirname

        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            return dir_path
        except (OSError, PermissionError) as e:
            raise DirectoryCreationError(f"Failed to create directory {dir_path}: {e}")
