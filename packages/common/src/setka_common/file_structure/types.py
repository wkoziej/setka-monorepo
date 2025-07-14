"""
ABOUTME: Media type definitions and file extensions
ABOUTME: Provides enums and constants for different media types
"""

from enum import Enum
from typing import List


class MediaType(Enum):
    """Types of media files."""
    AUDIO = "audio"
    VIDEO = "video"
    IMAGE = "image"
    DOCUMENT = "document"


class FileExtensions:
    """Common file extensions by type."""
    AUDIO = [".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg", ".wma"]
    VIDEO = [".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".webm"]
    IMAGE = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp"]
    DOCUMENT = [".pdf", ".doc", ".docx", ".txt", ".md", ".odt"]
    
    @classmethod
    def get_for_type(cls, media_type: MediaType) -> List[str]:
        """Get extensions for media type."""
        return {
            MediaType.AUDIO: cls.AUDIO,
            MediaType.VIDEO: cls.VIDEO,
            MediaType.IMAGE: cls.IMAGE,
            MediaType.DOCUMENT: cls.DOCUMENT,
        }[media_type]
