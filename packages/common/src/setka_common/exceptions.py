"""
ABOUTME: Exception classes for setka-common package
ABOUTME: Provides custom exceptions for better error handling
"""


class SetkaCommonError(Exception):
    """Base exception for setka-common package."""
    pass


class InvalidPathError(SetkaCommonError):
    """Raised when path is invalid or doesn't exist."""
    pass


class StructureValidationError(SetkaCommonError):
    """Raised when structure validation fails."""
    pass


class FileNotFoundError(SetkaCommonError):
    """Raised when required file is not found."""
    pass


class InvalidFileFormatError(SetkaCommonError):
    """Raised when file format is invalid."""
    pass


class DirectoryCreationError(SetkaCommonError):
    """Raised when directory creation fails."""
    pass


class MetadataError(SetkaCommonError):
    """Raised when metadata operation fails."""
    pass