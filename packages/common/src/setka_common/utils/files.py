"""
ABOUTME: File discovery and manipulation utilities
ABOUTME: Provides functions for finding and organizing media files
"""

from pathlib import Path
from typing import List
import logging
import re

from dataclasses import dataclass
from typing import Optional

from ..file_structure.types import MediaType, FileExtensions
from ..exceptions import InvalidPathError

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of directory structure validation."""

    is_valid: bool
    errors: List[str]
    has_video_files: bool
    has_audio_files: bool
    has_analysis_files: bool


class MediaDiscovery:
    """
    Auto-discovery of media files in recording directory.

    Discovers video files, audio files, analysis files, and validates
    the recording directory structure for media processing.

    Example:
        discovery = MediaDiscovery(Path("./recording_20250105_143022"))
        video_files = discovery.discover_video_files()
        main_audio = discovery.detect_main_audio()
        validation = discovery.validate_structure()
    """

    ANALYSIS_EXTENSIONS = {".json"}

    def __init__(self, recording_dir: Path):
        """
        Initialize MediaDiscovery with recording directory.

        Args:
            recording_dir: Path to recording directory

        Raises:
            FileNotFoundError: If recording directory or extracted directory doesn't exist
        """
        # Local import avoids a module-level cycle: recording.py imports from
        # this module, so the dir-name constants are pulled in lazily here.
        from ..file_structure.specialized import RecordingStructureManager

        self.recording_dir = Path(recording_dir)

        if not self.recording_dir.exists():
            raise FileNotFoundError(f"Recording directory not found: {recording_dir}")

        self.extracted_dir = (
            self.recording_dir / RecordingStructureManager.EXTRACTED_DIRNAME
        )
        if not self.extracted_dir.exists():
            raise FileNotFoundError(
                f"Extracted directory not found: {self.extracted_dir}"
            )

        self.analysis_dir = (
            self.recording_dir / RecordingStructureManager.ANALYSIS_DIRNAME
        )

    def discover_video_files(self) -> List[str]:
        """
        Discover video files in extracted directory.

        Returns:
            List of video filenames (not full paths)
        """
        video_paths = find_files_by_type(self.extracted_dir, MediaType.VIDEO)
        return sorted([path.name for path in video_paths])

    def discover_audio_files(self) -> List[str]:
        """
        Discover audio files in extracted directory.

        Returns:
            List of audio filenames (not full paths)
        """
        audio_paths = find_files_by_type(self.extracted_dir, MediaType.AUDIO)
        return sorted([path.name for path in audio_paths])

    def discover_analysis_files(self) -> List[str]:
        """
        Discover analysis files in analysis directory.

        Returns:
            List of analysis filenames (not full paths)
        """
        if not self.analysis_dir.exists():
            return []

        analysis_files = []

        for file_path in self.analysis_dir.iterdir():
            if file_path.is_file():
                extension = file_path.suffix.lower()
                if extension in self.ANALYSIS_EXTENSIONS:
                    analysis_files.append(file_path.name)

        return sorted(analysis_files)

    def detect_main_audio(self) -> Optional[str]:
        """
        Detect main audio file from available audio files.

        Logic:
        1. If "main_audio.*" exists, use it
        2. If only one audio file exists, use it
        3. If multiple files exist without main_audio, return None

        Returns:
            Main audio filename or None if ambiguous
        """
        audio_files = self.discover_audio_files()

        if not audio_files:
            return None

        # Check for main_audio file
        for audio_file in audio_files:
            file_stem = Path(audio_file).stem.lower()
            if file_stem == "main_audio":
                return audio_file

        # If only one audio file, use it
        if len(audio_files) == 1:
            return audio_files[0]

        # Multiple files without main_audio - ambiguous
        return None

    def validate_structure(self) -> ValidationResult:
        """
        Validate recording directory structure.

        Returns:
            ValidationResult with validation status and details
        """
        errors = []

        # Check for video files
        video_files = self.discover_video_files()
        has_video_files = len(video_files) > 0
        if not has_video_files:
            errors.append("No video files found in extracted directory")

        # Check for audio files
        audio_files = self.discover_audio_files()
        has_audio_files = len(audio_files) > 0
        if not has_audio_files:
            errors.append("No audio files found in extracted directory")

        # Check for analysis files (optional)
        analysis_files = self.discover_analysis_files()
        has_analysis_files = len(analysis_files) > 0

        # Check for metadata.json (optional)
        metadata_file = self.recording_dir / "metadata.json"
        if not metadata_file.exists():
            # This is a warning, not an error
            pass

        is_valid = len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            has_video_files=has_video_files,
            has_audio_files=has_audio_files,
            has_analysis_files=has_analysis_files,
        )


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

    This is the single canonical sanitizer for the monorepo. It is a *superset*
    of obsession's ``core/extractor.py`` rules and is guaranteed (by the
    ``test_sanitize_superset`` regression test) to produce byte-identical output
    to that implementation on real OBS source names — so adopting it in
    obsession renames no already-extracted files.

    Rules applied in order:
    1. Replace path separators and reserved characters ``/ \\ : * ? " < > |``
       with ``_``.
    2. Collapse runs of consecutive underscores into a single ``_``.
    3. Strip leading/trailing spaces and dots.
    4. Strip leading/trailing underscores.
    5. Fall back to ``"source"`` when nothing usable remains.
    6. Truncate to 255 chars, preserving the extension when present.

    Args:
        filename: Filename to sanitize

    Returns:
        Sanitized filename safe for cross-platform use

    Raises:
        ValueError: When filename is not a string
    """
    if not isinstance(filename, str):
        raise ValueError(f"Filename must be a string, got {type(filename)}")

    # 1. Replace path separators and reserved characters with underscores.
    sanitized = re.sub(r'[/\\:*?"<>|]', "_", filename)

    # 2. Collapse repeated underscores into one.
    sanitized = re.sub(r"_+", "_", sanitized)

    # 3. Strip leading/trailing spaces and dots.
    sanitized = sanitized.strip(". ")

    # 4. Strip leading/trailing underscores.
    sanitized = sanitized.strip("_")

    # 5. Non-empty fallback so a source never maps to an empty path.
    if not sanitized:
        return "source"

    # 6. Limit length, preserving the extension when present.
    max_length = 255
    if len(sanitized) > max_length:
        name, ext = (
            sanitized.rsplit(".", 1) if "." in sanitized else (sanitized, "")
        )
        sanitized = (
            name[: max_length - len(ext) - 1] + "." + ext
            if ext
            else name[:max_length]
        )

    return sanitized
