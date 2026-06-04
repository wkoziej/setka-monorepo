"""
ABOUTME: Recording-specific file structure for obsession
ABOUTME: Extends base structure with recording-specific directories
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import json
import logging
import re

from ..base import MediaStructure, StructureManager
from ...utils.files import find_files_by_type, MediaType
from ...exceptions import (
    InvalidPathError,
    DirectoryCreationError,
)

logger = logging.getLogger(__name__)

# Bitwig appends a numeric suffix like "-24" or "-100" to recorded track filenames.
_BITWIG_SUFFIX_RE = re.compile(r"-\d+$")

# Characters that act as separators and should become underscores.
_SEPARATOR_CHARS_RE = re.compile(r"[ +/\\]+")

# Collapse multiple underscores into one.
_MULTI_UNDERSCORE_RE = re.compile(r"_+")


def sanitize_stem_name(name: str) -> str:
    """Convert a raw Bitwig filename or stem into a stable, filesystem-safe label.

    Steps applied in order:
    1. Strip file extension (handles both bare stems and full filenames like ``foo.wav``).
    2. Remove the Bitwig numeric recording suffix ``-<digits>`` at the end
       (e.g. ``track 4+git-24`` → ``track 4+git``).
    3. Replace separator characters (space, ``+``, ``/``, ``\\``) with ``_``.
    4. Collapse consecutive underscores into one and strip leading/trailing ``_``.

    Case is preserved — no lower-casing.  The function is idempotent:
    ``sanitize_stem_name(sanitize_stem_name(x)) == sanitize_stem_name(x)``.

    Args:
        name: Raw stem name or full filename from a Bitwig ``samples/`` directory
              or any other audio source.

    Returns:
        Normalised label suitable for use in ``<label>_analysis.json`` and the
        ``analysis/index.json`` manifest.

    Raises:
        ValueError: When the resulting label is empty (e.g. input was only
                    separator characters), with a message referencing
                    ``sanitize_stem_name`` for easy grep.
    """
    # Step 1: replace path separators (/ \) with underscores BEFORE Path.stem so
    # that "my track/stem" is not interpreted as a filesystem path component.
    # Spaces and + are not path separators on Linux but are still replaced here
    # pre-emptively; they will also be caught in step 3.
    pre = name.replace("/", "_").replace("\\", "_")

    # Step 1b: strip file extension using Path.stem (handles e.g. "track-24.wav").
    stem = Path(pre).stem

    # Step 2: remove Bitwig numeric suffix "-<digits>" at the end.
    stem = _BITWIG_SUFFIX_RE.sub("", stem)

    # Step 3: replace remaining separator characters (space, +) with underscore.
    stem = _SEPARATOR_CHARS_RE.sub("_", stem)

    # Step 4: collapse and strip underscores.
    stem = _MULTI_UNDERSCORE_RE.sub("_", stem)
    stem = stem.strip("_")

    if not stem:
        raise ValueError(
            f"sanitize_stem_name: input {name!r} reduces to an empty label after "
            "removing extension, Bitwig suffix, and separator characters. "
            "Provide a name with at least one alphanumeric character."
        )

    return stem


@dataclass
class RecordingStructure(MediaStructure):
    """Structure for OBS recording projects."""

    extracted_dir: Path
    mixed_dir: Path
    bitwig_dir: Path

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
    MIXED_DIRNAME = "mixed"
    BITWIG_DIRNAME = "bitwig"

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
        mixed_dir = project_dir / RecordingStructureManager.MIXED_DIRNAME
        bitwig_dir = project_dir / RecordingStructureManager.BITWIG_DIRNAME

        return RecordingStructure(
            project_dir=project_dir,
            media_file=video_path,
            metadata_file=metadata_file,
            processed_dir=processed_dir,
            extracted_dir=extracted_dir,
            mixed_dir=mixed_dir,
            bitwig_dir=bitwig_dir,
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
            structure.mixed_dir.mkdir(parents=True, exist_ok=True)
            structure.bitwig_dir.mkdir(parents=True, exist_ok=True)
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
            raise InvalidPathError(
                f"Recording directory does not exist: {recording_dir}"
            )

        if not recording_dir.is_dir():
            raise InvalidPathError(
                f"Recording path is not a directory: {recording_dir}"
            )

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
            raise InvalidPathError(
                f"Recording directory does not exist: {recording_dir}"
            )

        if not recording_dir.is_dir():
            raise InvalidPathError(
                f"Recording path is not a directory: {recording_dir}"
            )

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
    def ensure_mixed_dir(recording_dir: Path) -> Path:
        """Ensure mixed directory exists.

        Holds the polished audio mix exported from Bitwig (master now,
        per-instrument stems later). Distinct from extracted/ which holds
        raw OBS sources.

        Args:
            recording_dir: Recording directory path

        Returns:
            Path to mixed directory

        Raises:
            InvalidPathError: When recording_dir is invalid
            DirectoryCreationError: When directory creation fails
        """
        if not recording_dir:
            raise InvalidPathError("Recording directory cannot be empty")

        recording_dir = Path(recording_dir)

        if not recording_dir.exists():
            raise InvalidPathError(
                f"Recording directory does not exist: {recording_dir}"
            )

        if not recording_dir.is_dir():
            raise InvalidPathError(
                f"Recording path is not a directory: {recording_dir}"
            )

        mixed_dir = recording_dir / RecordingStructureManager.MIXED_DIRNAME

        try:
            mixed_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created mixed directory: {mixed_dir}")
            return mixed_dir
        except (OSError, PermissionError) as e:
            raise DirectoryCreationError(
                f"Failed to create mixed directory at {mixed_dir}: {e}"
            )

    @staticmethod
    def ensure_bitwig_dir(recording_dir: Path) -> Path:
        """Ensure bitwig directory exists.

        Holds the Bitwig Studio project file (Save As target).
        Distinct from mixed/ (audio exports) and extracted/ (raw OBS sources).

        Args:
            recording_dir: Recording directory path

        Returns:
            Path to bitwig directory

        Raises:
            InvalidPathError: When recording_dir is invalid
            DirectoryCreationError: When directory creation fails
        """
        if not recording_dir:
            raise InvalidPathError("Recording directory cannot be empty")

        recording_dir = Path(recording_dir)

        if not recording_dir.exists():
            raise InvalidPathError(
                f"Recording directory does not exist: {recording_dir}"
            )

        if not recording_dir.is_dir():
            raise InvalidPathError(
                f"Recording path is not a directory: {recording_dir}"
            )

        bitwig_dir = recording_dir / RecordingStructureManager.BITWIG_DIRNAME

        try:
            bitwig_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created bitwig directory: {bitwig_dir}")
            return bitwig_dir
        except (OSError, PermissionError) as e:
            raise DirectoryCreationError(
                f"Failed to create bitwig directory at {bitwig_dir}: {e}"
            )

    @staticmethod
    def find_bitwig_sample_sources(recording_dir: Path) -> list[Path]:
        """Locate audio files in the Bitwig samples directory.

        Looks for a ``samples/`` subdirectory inside ``bitwig/``:
        - First checks ``bitwig/samples/`` (flat layout).
        - If not found, scans one level deep: ``bitwig/*/samples/`` (project-in-subfolder
          layout produced by Bitwig's Save As).
        No deeper recursion is performed to avoid pulling in unrelated audio.

        Args:
            recording_dir: Recording directory path

        Returns:
            Sorted (case-insensitive) list of audio file paths found in samples/,
            or an empty list when ``bitwig/`` or any ``samples/`` directory is absent.
        """
        recording_dir = Path(recording_dir)
        bitwig_dir = recording_dir / RecordingStructureManager.BITWIG_DIRNAME

        if not bitwig_dir.exists():
            return []

        # Prefer flat bitwig/samples/ layout first
        flat_samples = bitwig_dir / "samples"
        if flat_samples.exists() and flat_samples.is_dir():
            return sorted(
                find_files_by_type(flat_samples, MediaType.AUDIO),
                key=lambda p: p.name.lower(),
            )

        # Fallback: scan one level of subdirectories for a samples/ folder
        for child in bitwig_dir.iterdir():
            if not child.is_dir():
                continue
            nested_samples = child / "samples"
            if nested_samples.exists() and nested_samples.is_dir():
                return sorted(
                    find_files_by_type(nested_samples, MediaType.AUDIO),
                    key=lambda p: p.name.lower(),
                )

        return []

    @staticmethod
    def find_analysis_audio_sources(recording_dir: Path) -> list[Path]:
        """Resolve audio sources for analysis using a hybrid two-tier approach.

        **Tier resolution:**

        1. *master-tier* — audio files directly in ``mixed/`` (non-recursive).
           Typically a single ``master.wav`` from a Bitwig Export Audio.
        2. *stems-tier* — audio files in ``mixed/stems/`` if that directory is
           non-empty; otherwise falls back to ``find_bitwig_sample_sources``
           (``bitwig/…/samples/`` raw capture files).

        The two tiers are merged and a collision check is performed using
        ``sanitize_stem_name`` on each file's stem — two files producing the same
        sanitised label would map to the same ``<label>_analysis.json`` output,
        which is rejected with ``ValueError``.

        If both tiers are empty (no ``mixed/`` audio and no bitwig samples), the
        function falls back to ``extracted/`` for backward compatibility.

        Args:
            recording_dir: Recording directory path

        Returns:
            Sorted (case-insensitive) list of audio file paths to analyze

        Raises:
            ValueError: When two source files sanitise to the same label (collision)
        """
        recording_dir = Path(recording_dir)

        mixed_dir = recording_dir / RecordingStructureManager.MIXED_DIRNAME
        stems_dir = mixed_dir / "stems"

        # --- master-tier: audio directly in mixed/ root ---
        master_tier: list[Path] = []
        if mixed_dir.exists():
            master_tier.extend(find_files_by_type(mixed_dir, MediaType.AUDIO))

        # --- stems-tier: mixed/stems/ preferred; bitwig/samples/ as fallback ---
        stems_tier: list[Path] = []
        if stems_dir.exists():
            stems_tier.extend(find_files_by_type(stems_dir, MediaType.AUDIO))
        if not stems_tier:
            # mixed/stems/ absent or empty — try bitwig samples
            stems_tier.extend(
                RecordingStructureManager.find_bitwig_sample_sources(recording_dir)
            )

        sources = master_tier + stems_tier

        if sources:
            # Detect sanitised label collisions before returning
            seen_labels: dict[str, Path] = {}
            for audio_file in sources:
                label = sanitize_stem_name(audio_file.stem)
                if label in seen_labels:
                    raise ValueError(
                        f"Stem name collision after sanitisation: "
                        f"'{audio_file}' and '{seen_labels[label]}' "
                        f"would both produce '{label}_analysis.json'. "
                        "Use unique stem names across mixed/ and stems sources."
                    )
                seen_labels[label] = audio_file

            return sorted(sources, key=lambda p: p.name.lower())

        # Fallback: no audio in mixed/ or bitwig — use extracted/ (backward compat)
        extracted_dir = recording_dir / RecordingStructureManager.EXTRACTED_DIRNAME
        extracted_files = find_files_by_type(extracted_dir, MediaType.AUDIO)
        return sorted(extracted_files, key=lambda p: p.name.lower())

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
