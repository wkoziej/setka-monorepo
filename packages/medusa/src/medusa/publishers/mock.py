"""
Mock publisher implementation for testing purposes.
Provides configurable success/failure scenarios and template processing simulation.
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable, List

from .base import BasePublisher, PublishProgress, PublishResult
from ..models import PlatformConfig
from ..exceptions import (
    PublishError,
    AuthenticationError,
    ValidationError,
    TemplateError,
    NetworkError,
    RateLimitError
)


@dataclass
class MockPublishConfig:
    """Configuration for MockPublisher behavior."""
    auth_success: bool = True
    publish_success: bool = True
    publish_delay: float = 0.1  # Seconds
    auth_delay: float = 0.05  # Seconds
    simulate_progress: bool = True
    progress_steps: int = 3
    auth_error: Optional[str] = None
    publish_error: Optional[str] = None
    error_type: str = "publish"  # "publish", "network", "rate_limit", "auth", "validation", "template"
    content_requirements: List[str] = field(default_factory=list)
    max_content_length: int = 5000


class MockPublisher(BasePublisher):
    """
    Mock publisher for testing purposes.
    
    Provides configurable scenarios for:
    - Authentication success/failure
    - Publishing success/failure
    - Progress reporting simulation
    - Realistic timing delays
    - Various error types
    - Template processing simulation
    - Call verification
    """
    
    def __init__(
        self,
        platform_name: str = "mock",
        config: Optional[PlatformConfig] = None,
        mock_config: Optional[MockPublishConfig] = None
    ):
        """
        Initialize MockPublisher.
        
        Args:
            platform_name: Platform name for the mock
            config: Platform configuration
            mock_config: Mock-specific configuration
        """
        super().__init__(platform_name, config)
        self.mock_config = mock_config or MockPublishConfig()
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
    
    def _validate_content(self, content: str, metadata: Dict[str, Any]) -> None:
        """
        Validate content and metadata according to mock requirements.
        
        Args:
            content: Post content to validate
            metadata: Platform-specific metadata to validate
            
        Raises:
            ValidationError: If content or metadata validation fails
        """
        # Check content length
        if len(content) > self.mock_config.max_content_length:
            raise ValidationError(
                f"Content too long: {len(content)} characters (max {self.mock_config.max_content_length})",
                platform=self.platform_name
            )
        
        # Check required metadata fields
        for required_field in self.mock_config.content_requirements:
            if required_field not in metadata or not metadata[required_field]:
                raise ValidationError(
                    f"Missing required content field: {required_field}",
                    platform=self.platform_name
                )
    
    async def _publish_post(
        self,
        content: str,
        metadata: Dict[str, Any],
        progress_callback: Optional[Callable[[PublishProgress], None]] = None
    ) -> PublishResult:
        """
        Mock post publishing with configurable behavior.
        
        Args:
            content: Post content (with variables already substituted)
            metadata: Platform-specific metadata
            progress_callback: Optional callback for progress updates
            
        Returns:
            PublishResult with mock publishing information
            
        Raises:
            PublishError: If publishing fails
            NetworkError: If network error is simulated
            RateLimitError: If rate limit error is simulated
            TemplateError: If template error is simulated
        """
        # Log the call
        call_info = {
            "method": "_publish_post",
            "content": content,
            "metadata": metadata,
            "timestamp": datetime.now(timezone.utc),
            "success": self.mock_config.publish_success
        }
        self.call_log.append(call_info)
        
        # Check if publishing should fail
        if not self.mock_config.publish_success:
            error_message = self.mock_config.publish_error or "Mock publishing failed"
            
            # Raise specific error type based on configuration
            if self.mock_config.error_type == "network":
                raise NetworkError(error_message, platform=self.platform_name)
            elif self.mock_config.error_type == "rate_limit":
                raise RateLimitError(error_message, platform=self.platform_name)
            elif self.mock_config.error_type == "auth":
                raise AuthenticationError(error_message, platform=self.platform_name)
            elif self.mock_config.error_type == "validation":
                raise ValidationError(error_message, platform=self.platform_name)
            elif self.mock_config.error_type == "template":
                raise TemplateError(error_message, platform=self.platform_name)
            else:
                raise PublishError(error_message, platform=self.platform_name)
        
        # Simulate progress reporting
        if self.mock_config.simulate_progress and progress_callback:
            progress_steps = [
                ("validating", "Validating post content"),
                ("processing", "Processing post data"),
                ("publishing", "Publishing to platform")
            ]
            
            for step_num, (step_name, message) in enumerate(progress_steps):
                progress = PublishProgress(
                    step=step_name,
                    current_step=step_num,
                    total_steps=len(progress_steps),
                    message=message
                )
                progress_callback(progress)
                
                # Small delay between progress updates
                if step_num < len(progress_steps) - 1:
                    await asyncio.sleep(self.mock_config.publish_delay / len(progress_steps))
            
            # Final completion progress
            final_progress = PublishProgress(
                step="completed",
                current_step=len(progress_steps),
                total_steps=len(progress_steps),
                message="Post published successfully",
                status="completed"
            )
            progress_callback(final_progress)
        else:
            # Simple delay without progress
            if self.mock_config.publish_delay > 0:
                await asyncio.sleep(self.mock_config.publish_delay)
        
        # Generate mock result
        post_id = f"mock_post_{uuid.uuid4().hex[:8]}"
        post_url = f"https://mock-platform.com/post/{post_id}"
        
        return PublishResult(
            platform=self.platform_name,
            post_id=post_id,
            success=True,
            post_url=post_url,
            metadata={
                "content_length": len(content),
                "published_at": datetime.now(timezone.utc).isoformat(),
                "mock_metadata": metadata
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