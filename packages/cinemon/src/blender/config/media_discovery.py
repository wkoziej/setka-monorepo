# ABOUTME: MediaDiscovery class for auto-discovery of media files in recording directories
# ABOUTME: Provides file discovery, validation, and main audio detection functionality

"""Media discovery for recording directories."""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


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
    the recording directory structure for cinemon processing.

    Example:
        discovery = MediaDiscovery(Path("./recording_20250105_143022"))
        video_files = discovery.discover_video_files()
        main_audio = discovery.detect_main_audio()
        validation = discovery.validate_structure()
    """

    VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.webm'}
    AUDIO_EXTENSIONS = {'.m4a', '.wav', '.mp3', '.aac', '.flac'}
    ANALYSIS_EXTENSIONS = {'.json'}

    def __init__(self, recording_dir: Path):
        """
        Initialize MediaDiscovery with recording directory.

        Args:
            recording_dir: Path to recording directory

        Raises:
            FileNotFoundError: If recording directory or extracted directory doesn't exist
        """
        self.recording_dir = Path(recording_dir)

        if not self.recording_dir.exists():
            raise FileNotFoundError(f"Recording directory not found: {recording_dir}")

        self.extracted_dir = self.recording_dir / "extracted"
        if not self.extracted_dir.exists():
            raise FileNotFoundError(f"Extracted directory not found: {self.extracted_dir}")

        self.analysis_dir = self.recording_dir / "analysis"

    def discover_video_files(self) -> List[str]:
        """
        Discover video files in extracted directory.

        Returns:
            List of video filenames (not full paths)
        """
        video_files = []

        for file_path in self.extracted_dir.iterdir():
            if file_path.is_file():
                extension = file_path.suffix.lower()
                if extension in self.VIDEO_EXTENSIONS:
                    video_files.append(file_path.name)

        return sorted(video_files)

    def discover_audio_files(self) -> List[str]:
        """
        Discover audio files in extracted directory.

        Returns:
            List of audio filenames (not full paths)
        """
        audio_files = []

        for file_path in self.extracted_dir.iterdir():
            if file_path.is_file():
                extension = file_path.suffix.lower()
                if extension in self.AUDIO_EXTENSIONS:
                    audio_files.append(file_path.name)

        return sorted(audio_files)

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
            has_analysis_files=has_analysis_files
        )
