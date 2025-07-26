"""
ABOUTME: Beatrix - Audio analysis for Setka media processing pipeline
ABOUTME: Provides audio analysis capabilities including beat detection, energy analysis, and structural segmentation
"""

from .core.audio_analyzer import AudioAnalyzer
from .core.audio_validator import (
    AudioValidator,
    AudioValidationError,
    NoAudioFileError,
    MultipleAudioFilesError,
)
from .cli.analyze_audio import analyze_audio_command

__version__ = "0.1.0"
__all__ = [
    "AudioAnalyzer",
    "AudioValidator",
    "AudioValidationError",
    "NoAudioFileError",
    "MultipleAudioFilesError",
    "analyze_audio_command",
]
