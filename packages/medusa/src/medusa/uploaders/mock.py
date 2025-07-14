"""
Mock uploader implementation for testing purposes.
Provides configurable success/failure scenarios and realistic behavior simulation.
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable, List

from .base import BaseUploader, UploadProgress, UploadResult
from ..models import MediaMetadata, PlatformConfig
from ..exceptions import (
    UploadError,
    AuthenticationError,
    ValidationError,
    NetworkError,
    RateLimitError
)


@dataclass
class MockConfig:
    """Configuration for MockUploader behavior."""
    auth_success: bool = True
    upload_success: bool = True
    upload_delay: float = 0.1  # Seconds
    auth_delay: float = 0.05  # Seconds
    simulate_progress: bool = True
    progress_steps: int = 5
    auth_error: Optional[str] = None
    upload_error: Optional[str] = None
    error_type: str = "upload"  # "upload", "network", "rate_limit", "auth", "validation"
    metadata_requirements: List[str] = field(default_factory=list)


class MockUploader(BaseUploader):
    """
    Mock uploader for testing purposes.
    
    Provides configurable scenarios for:
    - Authentication success/failure
    - Upload success/failure
    - Progress reporting simulation
    - Realistic timing delays
    - Various error types
    - Call verification
    """
    
    def __init__(
        self,
        platform_name: str = "mock",
        config: Optional[PlatformConfig] = None,
        mock_config: Optional[MockConfig] = None
    ):
        """
        Initialize MockUploader.
        
        Args:
            platform_name: Platform name for the mock
            config: Platform configuration
            mock_config: Mock-specific configuration
        """
        super().__init__(platform_name, config)
        self.mock_config = mock_config or MockConfig()
        self.call_log: List[Dict[str, Any]] = []
    
    async def authenticate(self) -> bool:
        """
        Mock authentication with configurable success/failure.
        
        Returns:
            True if authentication successful, False otherwise
            
        Raises:
            AuthenticationError: If authentication fails
        """
        # Simulate authentication delay
        if self.mock_config.auth_delay > 0:
            await asyncio.sleep(self.mock_config.auth_delay)
        
        # Log the call
        call_info = {
            "method": "authenticate",
            "timestamp": datetime.now(timezone.utc),
            "success": self.mock_config.auth_success
        }
        self.call_log.append(call_info)
        
        if not self.mock_config.auth_success:
            error_message = self.mock_config.auth_error or "Mock authentication failed"
            raise AuthenticationError(error_message, platform=self.platform_name)
        
        self.is_authenticated = True
        return True
    
    def _validate_metadata(self, metadata: MediaMetadata) -> None:
        """
        Validate metadata according to mock requirements.
        
        Args:
            metadata: Media metadata to validate
            
        Raises:
            ValidationError: If metadata validation fails
        """
        # Check required fields
        for required_field in self.mock_config.metadata_requirements:
            value = getattr(metadata, required_field, None)
            if not value:
                raise ValidationError(
                    f"Missing required metadata field: {required_field}",
                    platform=self.platform_name
                )
    
    async def _upload_media(
        self,
        file_path: str,
        metadata: MediaMetadata,
        progress_callback: Optional[Callable[[UploadProgress], None]] = None
    ) -> UploadResult:
        """
        Mock media upload with configurable behavior.
        
        Args:
            file_path: Path to the media file
            metadata: Media metadata
            progress_callback: Optional callback for progress updates
            
        Returns:
            UploadResult with mock upload information
            
        Raises:
            UploadError: If upload fails
            NetworkError: If network error is simulated
            RateLimitError: If rate limit error is simulated
        """
        # Log the call
        call_info = {
            "method": "_upload_media",
            "file_path": file_path,
            "metadata": metadata.to_dict(),
            "timestamp": datetime.now(timezone.utc),
            "success": self.mock_config.upload_success
        }
        self.call_log.append(call_info)
        
        # Check if upload should fail
        if not self.mock_config.upload_success:
            error_message = self.mock_config.upload_error or "Mock upload failed"
            
            # Raise specific error type based on configuration
            if self.mock_config.error_type == "network":
                raise NetworkError(error_message, platform=self.platform_name)
            elif self.mock_config.error_type == "rate_limit":
                raise RateLimitError(error_message, platform=self.platform_name)
            elif self.mock_config.error_type == "auth":
                raise AuthenticationError(error_message, platform=self.platform_name)
            elif self.mock_config.error_type == "validation":
                raise ValidationError(error_message, platform=self.platform_name)
            else:
                raise UploadError(error_message, platform=self.platform_name)
        
        # Simulate progress reporting
        if self.mock_config.simulate_progress and progress_callback:
            total_bytes = 1000000  # Mock file size
            
            for step in range(self.mock_config.progress_steps + 1):
                bytes_uploaded = int((step / self.mock_config.progress_steps) * total_bytes)
                progress = UploadProgress(
                    bytes_uploaded=bytes_uploaded,
                    total_bytes=total_bytes,
                    status="uploading" if step < self.mock_config.progress_steps else "completed"
                )
                progress_callback(progress)
                
                # Small delay between progress updates
                if step < self.mock_config.progress_steps:
                    await asyncio.sleep(self.mock_config.upload_delay / self.mock_config.progress_steps)
        else:
            # Simple delay without progress
            if self.mock_config.upload_delay > 0:
                await asyncio.sleep(self.mock_config.upload_delay)
        
        # Generate mock result
        upload_id = f"mock_upload_{uuid.uuid4().hex[:8]}"
        media_url = f"https://mock-platform.com/video/{upload_id}"
        
        return UploadResult(
            platform=self.platform_name,
            upload_id=upload_id,
            success=True,
            media_url=media_url,
            metadata={
                "title": metadata.title,
                "description": metadata.description,
                "tags": metadata.tags,
                "mock_upload_time": datetime.now(timezone.utc).isoformat()
            }
        )
    
    async def cleanup(self) -> None:
        """Mock cleanup with call logging."""
        call_info = {
            "method": "cleanup",
            "timestamp": datetime.now(timezone.utc)
        }
        self.call_log.append(call_info)
        
        await super().cleanup()
    
    # Verification helper methods for testing
    
    def clear_call_log(self) -> None:
        """Clear the call log."""
        self.call_log.clear()
    
    def was_called(self, method_name: str) -> bool:
        """
        Check if a method was called.
        
        Args:
            method_name: Name of the method to check
            
        Returns:
            True if method was called, False otherwise
        """
        return any(call["method"] == method_name for call in self.call_log)
    
    def get_call_count(self, method_name: str) -> int:
        """
        Get the number of times a method was called.
        
        Args:
            method_name: Name of the method to check
            
        Returns:
            Number of calls to the method
        """
        return sum(1 for call in self.call_log if call["method"] == method_name)
    
    def get_calls(self, method_name: str) -> List[Dict[str, Any]]:
        """
        Get all calls to a specific method.
        
        Args:
            method_name: Name of the method to get calls for
            
        Returns:
            List of call information dictionaries
        """
        return [call for call in self.call_log if call["method"] == method_name] 