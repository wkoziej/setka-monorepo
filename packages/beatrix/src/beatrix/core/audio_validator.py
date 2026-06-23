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
from ..exceptions import (
    AudioValidationError,
    NoAudioFileError,
    MultipleAudioFilesError,
)

logger = logging.getLogger(__name__)


class AudioValidator:
    """
    Validator for audio files in extracted OBS recordings.

    This class handles detection and validation of audio files,
    with support for multiple audio file scenarios.
    """

    def __init__(self):
        """Initialize AudioValidator."""
        self._librosa = None

    @property
    def librosa(self):
        """Lazy-load librosa for the decode probe."""
        if self._librosa is None:
            try:
                import librosa

                self._librosa = librosa
            except ImportError:
                raise ImportError(
                    "librosa jest wymagana do walidacji audio. "
                    "Zainstaluj: pip install librosa"
                )
        return self._librosa

    def validate_audio_file(self, audio_path: Path) -> Path:
        """
        Fail fast: confirm an audio file is actually decodable.

        Existence and extension checks pass for a file that is corrupt or
        truncated; this probe decodes just enough (``librosa.get_duration``)
        to reject such a file before any expensive analysis begins.

        Args:
            audio_path: Path to the audio file to probe

        Returns:
            Path: The validated path (unchanged)

        Raises:
            AudioValidationError: When the file cannot be decoded
        """
        try:
            self.librosa.get_duration(path=str(audio_path))
        except Exception as exc:
            raise AudioValidationError(
                f"Nie można zdekodować pliku audio: {audio_path.name} ({exc})"
            ) from exc
        return audio_path

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
            AudioValidationError: When the selected file cannot be decoded
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
        return self.validate_audio_file(audio_files[0])

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
            AudioValidationError: When the file cannot be decoded
        """
        audio_path = extracted_dir / specified_audio

        if not audio_path.exists():
            raise ValueError(f"Nie znaleziono wskazanego pliku audio: {specified_audio}")

        if not audio_path.is_file():
            raise ValueError(
                f"Wskazana ścieżka audio nie jest plikiem: {specified_audio}"
            )

        if audio_path.suffix.lower() not in FileExtensions.AUDIO:
            raise ValueError(
                f"Wskazany plik jest nieprawidłowym plikiem audio: {specified_audio}. "
                f"Obsługiwane formaty: {', '.join(FileExtensions.AUDIO)}"
            )

        logger.info(f"Validated specified audio file: {specified_audio}")
        return self.validate_audio_file(audio_path)
