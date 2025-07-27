"""
ABOUTME: Custom exceptions for Beatrix audio analysis
ABOUTME: Contains specialized exception classes for audio processing errors
"""


class BeatrixError(Exception):
    """Base exception for Beatrix audio analysis errors"""

    pass


class AudioValidationError(BeatrixError):
    """Raised when audio file validation fails"""

    pass


class NoAudioFileError(AudioValidationError):
    """Raised when no audio file is found in the directory"""

    pass


class MultipleAudioFilesError(AudioValidationError):
    """Raised when multiple audio files are found and no main file is specified"""

    pass


class AudioAnalysisError(BeatrixError):
    """Raised when audio analysis fails"""

    pass
