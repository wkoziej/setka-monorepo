"""
Audio Validator for OBS Canvas Recording audio files.

This module handles detection and validation of audio files in extracted
OBS recordings, with support for multiple audio file scenarios.
"""

from pathlib import Path
from typing import List, Optional
import logging

from setka_common.file_structure.types import FileExtensions, MediaType
from setka_common.utils.files import find_files_by_type

logger = logging.getLogger(__name__)


class AudioValidationError(Exception):
    """Base exception for audio validation errors."""

    pass


class NoAudioFileError(AudioValidationError):
    """Raised when no audio files are found in extracted directory."""

    pass


class MultipleAudioFilesError(AudioValidationError):
    """Raised when multiple audio files are found without specification."""

    pass


class AudioValidator:
    """
    Validator for audio files in extracted OBS recordings.

    This class handles detection and validation of audio files,
    with support for multiple audio file scenarios.
    """

    def __init__(self):
        """Initialize AudioValidator."""
        pass

    def detect_main_audio(
        self, extracted_dir: Path, specified_audio: Optional[str] = None
    ) -> Path:
        """
        Detect main audio file or validate specified audio.

        Args:
            extracted_dir: Path to extracted files directory
            specified_audio: Optional name of specific audio file to use

        Returns:
            Path: Path to the main audio file

        Raises:
            NoAudioFileError: When no audio files are found
            MultipleAudioFilesError: When multiple audio files found without specification
            ValueError: When specified audio file is not found or invalid
        """
        audio_files = self.find_audio_files(extracted_dir)

        if specified_audio:
            return self._validate_specified_audio(extracted_dir, specified_audio)

        if len(audio_files) == 0:
            raise NoAudioFileError("Brak plików audio w katalogu extracted/")
        elif len(audio_files) > 1:
            audio_names = [f.name for f in audio_files]
            raise MultipleAudioFilesError(
                f"Znaleziono {len(audio_files)} plików audio: {', '.join(audio_names)}. "
                f"Użyj --main-audio aby wskazać właściwy."
            )

        logger.info(f"Detected main audio file: {audio_files[0].name}")
        return audio_files[0]

    def find_audio_files(self, extracted_dir: Path) -> List[Path]:
        """
        Find all audio files in extracted directory.

        Args:
            extracted_dir: Path to extracted files directory

        Returns:
            List[Path]: List of audio file paths
        """
        if not extracted_dir.exists():
            logger.warning(f"Extracted directory does not exist: {extracted_dir}")
            return []

        audio_files = find_files_by_type(extracted_dir, MediaType.AUDIO)
        logger.debug(f"Found {len(audio_files)} audio files in {extracted_dir}")
        return audio_files

    def _validate_specified_audio(
        self, extracted_dir: Path, specified_audio: str
    ) -> Path:
        """
        Validate specified audio file exists and is valid.

        Args:
            extracted_dir: Path to extracted files directory
            specified_audio: Name of specified audio file

        Returns:
            Path: Path to validated audio file

        Raises:
            ValueError: When specified audio file is not found or invalid
        """
        audio_path = extracted_dir / specified_audio

        if not audio_path.exists():
            raise ValueError(f"Specified audio file not found: {specified_audio}")

        if not audio_path.is_file():
            raise ValueError(f"Specified audio path is not a file: {specified_audio}")

        if audio_path.suffix.lower() not in FileExtensions.AUDIO:
            raise ValueError(
                f"Specified file is not a valid audio file: {specified_audio}. "
                f"Supported formats: {', '.join(FileExtensions.AUDIO)}"
            )

        logger.info(f"Validated specified audio file: {specified_audio}")
        return audio_path
