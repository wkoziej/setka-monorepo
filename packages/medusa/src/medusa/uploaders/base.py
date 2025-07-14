"""
Base abstract class for media uploaders.
Provides common functionality and interface for all uploader implementations.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timezone

from ..models import MediaMetadata, PlatformConfig
from ..exceptions import (
    UploadError,
    AuthenticationError,
    ValidationError,
    RateLimitError,
    NetworkError,
    MedusaError
)


@dataclass
class UploadProgress:
    """Represents upload progress information."""
    bytes_uploaded: int
    total_bytes: int
    percentage: float = field(init=False)
    status: str = "uploading"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self):
        """Validate and calculate percentage after initialization."""
        # Validation
        if self.bytes_uploaded < 0:
            raise ValidationError("bytes_uploaded cannot be negative")
        
        if self.total_bytes < 0:
            raise ValidationError("total_bytes must be positive")
        
        if self.bytes_uploaded > self.total_bytes:
            raise ValidationError("bytes_uploaded cannot exceed total_bytes")
        
        # Calculate percentage
        if self.total_bytes == 0:
            self.percentage = 0.0
        else:
            self.percentage = (self.bytes_uploaded / self.total_bytes) * 100.0


@dataclass
class UploadResult:
    """Represents the result of a media upload operation."""
    platform: str
    upload_id: str
    success: bool = True
    media_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self):
        """Validate upload result after initialization."""
        if not self.platform or not self.platform.strip():
            raise ValidationError("Platform name cannot be empty")
        
        if not self.success and not self.error:
            raise ValidationError("Failed uploads must have error information")


class BaseUploader(ABC):
    """
    Abstract base class for all media uploaders.
    
    Provides common functionality including:
    - Authentication management
    - Progress reporting
    - Error handling and retry logic
    - Metadata validation
    - Async context manager support
    """
    
    def __init__(self, platform_name: str, config: Optional[PlatformConfig] = None):
        """
        Initialize the base uploader.
        
        Args:
            platform_name: Name of the platform (e.g., 'youtube', 'vimeo')
            config: Platform-specific configuration
            
        Raises:
            ValidationError: If platform_name is empty
        """
        if not platform_name or not platform_name.strip():
            raise ValidationError("Platform name cannot be empty")
        
        self.platform_name = platform_name.strip()
        self.config = config or PlatformConfig(platform_name=self.platform_name)
        self.is_authenticated = False
        self.logger = logging.getLogger(f"medusa.uploader.{self.platform_name}")
        
        # Configuration from config or defaults
        self.retry_attempts = getattr(self.config, 'retry_attempts', 3)
        self.timeout = getattr(self.config, 'timeout', None) or 30
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """
        Authenticate with the platform.
        
        Returns:
            True if authentication successful, False otherwise
            
        Raises:
            AuthenticationError: If authentication fails
        """
        pass
    
    @abstractmethod
    async def _upload_media(
        self,
        file_path: str,
        metadata: MediaMetadata,
        progress_callback: Optional[Callable[[UploadProgress], None]] = None
    ) -> UploadResult:
        """
        Platform-specific media upload implementation.
        
        Args:
            file_path: Path to the media file
            metadata: Media metadata
            progress_callback: Optional callback for progress updates
            
        Returns:
            UploadResult with upload information
            
        Raises:
            UploadError: If upload fails
        """
        pass
    
    @abstractmethod
    def _validate_metadata(self, metadata: MediaMetadata) -> None:
        """
        Validate metadata for platform-specific requirements.
        
        Args:
            metadata: Media metadata to validate
            
        Raises:
            ValidationError: If metadata is invalid
        """
        pass
    
    async def upload_media(
        self,
        file_path: str,
        metadata: MediaMetadata,
        progress_callback: Optional[Callable[[UploadProgress], None]] = None
    ) -> UploadResult:
        """
        Upload media file with retry logic and error handling.
        
        Args:
            file_path: Path to the media file
            metadata: Media metadata
            progress_callback: Optional callback for progress updates
            
        Returns:
            UploadResult with upload information
            
        Raises:
            AuthenticationError: If authentication is required or fails
            ValidationError: If metadata validation fails
            UploadError: If upload fails after all retries
        """
        # Check authentication
        if not self.is_authenticated:
            raise AuthenticationError(
                "Authentication required before uploading",
                platform=self.platform_name
            )
        
        # Validate metadata
        self._validate_metadata(metadata)
        
        # Attempt upload with retry logic
        last_error = None
        for attempt in range(self.retry_attempts + 1):
            try:
                if self.timeout > 0:
                    result = await asyncio.wait_for(
                        self._upload_media(file_path, metadata, progress_callback),
                        timeout=self.timeout
                    )
                else:
                    result = await self._upload_media(file_path, metadata, progress_callback)
                
                self.logger.info(f"Upload successful on attempt {attempt + 1}")
                return result
                
            except Exception as e:
                last_error = e
                
                # Don't retry certain types of errors
                if not self._is_retryable_error(e) or attempt == self.retry_attempts:
                    self.logger.error(f"Upload failed after {attempt + 1} attempts: {e}")
                    raise e
                
                # Log retry attempt
                self.logger.warning(f"Upload attempt {attempt + 1} failed, retrying: {e}")
                
                # Exponential backoff
                await asyncio.sleep(2 ** attempt)
        
        # This should not be reached, but just in case
        if last_error:
            raise last_error
        else:
            raise UploadError("Upload failed for unknown reason", platform=self.platform_name)
    
    def _is_retryable_error(self, error: Exception) -> bool:
        """
        Determine if an error is retryable.
        
        Args:
            error: The exception that occurred
            
        Returns:
            True if the error should trigger a retry, False otherwise
        """
        # Network-related errors are retryable
        if isinstance(error, (NetworkError, RateLimitError, asyncio.TimeoutError)):
            return True
        
        # Authentication and validation errors are not retryable
        if isinstance(error, (AuthenticationError, ValidationError)):
            return False
        
        # Other MedusaError types are generally not retryable
        if isinstance(error, MedusaError):
            return False
        
        # Generic exceptions are generally not retryable unless specifically network-related
        return False
    
    async def cleanup(self) -> None:
        """
        Clean up resources after upload operations.
        
        This method can be overridden by subclasses to perform
        platform-specific cleanup operations.
        """
        self.logger.debug(f"Cleanup completed for {self.platform_name}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        result = await self.authenticate()
        if result:
            self.is_authenticated = True
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()
        return False  # Don't suppress exceptions
    
    def health_check(self) -> bool:
        """
        Check if the platform is healthy and ready for operations.
        
        Returns:
            True if platform is healthy, False otherwise
        """
        try:
            # Basic health check - verify authentication status
            return self.is_authenticated
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
