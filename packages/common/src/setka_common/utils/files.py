"""
ABOUTME: File discovery and manipulation utilities
ABOUTME: Provides functions for finding and organizing media files
"""

from pathlib import Path
from typing import List
import logging

from ..file_structure.types import MediaType, FileExtensions
from ..exceptions import InvalidPathError

logger = logging.getLogger(__name__)


def find_files_by_type(directory: Path, media_type: MediaType) -> List[Path]:
    """Find all files of given media type in directory.

    Args:
        directory: Directory to search in
        media_type: Type of media files to find

    Returns:
        List of paths to files of the specified type

    Raises:
        InvalidPathError: When directory is invalid
        ValueError: When media_type is invalid
    """
    if not directory:
        raise InvalidPathError("Directory cannot be empty")

    directory = Path(directory)

    if not isinstance(media_type, MediaType):
        raise ValueError(f"Invalid media type: {media_type}")

    extensions = FileExtensions.get_for_type(media_type)
    files = []

    if not directory.exists():
        logger.warning(f"Directory does not exist: {directory}")
        return files

    if not directory.is_dir():
        logger.warning(f"Path is not a directory: {directory}")
        return files

    try:
        for file_path in directory.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in extensions:
                files.append(file_path)
    except (OSError, PermissionError) as e:
        logger.error(f"Error accessing directory {directory}: {e}")
        return files

    # Sort for consistency
    files.sort(key=lambda x: x.name)
    logger.debug(f"Found {len(files)} {media_type.value} files in {directory}")
    return files


def find_media_files(directory: Path) -> dict[MediaType, List[Path]]:
    """Find all media files grouped by type.

    Args:
        directory: Directory to search in

    Returns:
        Dictionary mapping media types to lists of file paths

    Raises:
        InvalidPathError: When directory is invalid
    """
    if not directory:
        raise InvalidPathError("Directory cannot be empty")

    directory = Path(directory)
    result = {}

    for media_type in MediaType:
        try:
            files = find_files_by_type(directory, media_type)
            if files:
                result[media_type] = files
        except (ValueError, InvalidPathError) as e:
            logger.error(f"Error finding {media_type.value} files: {e}")
            continue

    return result


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for cross-platform compatibility.

    Args:
        filename: Filename to sanitize

    Returns:
        Sanitized filename safe for cross-platform use

    Raises:
        ValueError: When filename is not a string
    """
    if not isinstance(filename, str):
        raise ValueError(f"Filename must be a string, got {type(filename)}")

    # Handle empty filename
    if not filename:
        return filename

    # Remove invalid characters
    invalid_chars = '<>:"|?*'
    for char in invalid_chars:
        filename = filename.replace(char, "_")

    # Remove leading/trailing spaces and dots
    filename = filename.strip(". ")

    # Limit length
    max_length = 255
    if len(filename) > max_length:
        name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
        filename = (
            name[: max_length - len(ext) - 1] + "." + ext if ext else name[:max_length]
        )

    return filename
