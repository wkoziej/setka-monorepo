"""
Base abstract class for social media publishers.
Provides common functionality and interface for all publisher implementations.
"""

import asyncio
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timezone

from ..models import PlatformConfig
from ..exceptions import (
    PublishError,
    AuthenticationError,
    ValidationError,
    TemplateError,
    RateLimitError,
    NetworkError,
    MedusaError
)


@dataclass
class PublishProgress:
    """Represents publishing progress information."""
    step: str
    current_step: int
    total_steps: int
    message: Optional[str] = None
    percentage: float = field(init=False)
    status: str = "in_progress"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self):
        """Validate and calculate percentage after initialization."""
        # Validation
        if self.current_step < 0:
            raise ValidationError("current_step cannot be negative")
        
        if self.total_steps < 0:
            raise ValidationError("total_steps must be positive")
        
        if self.current_step > self.total_steps:
            raise ValidationError("current_step cannot exceed total_steps")
        
        # Calculate percentage
        if self.total_steps == 0:
            self.percentage = 0.0
        else:
            self.percentage = round((self.current_step / self.total_steps) * 100.0, 2)


@dataclass
class PublishResult:
    """Represents the result of a social media publishing operation."""
    platform: str
    post_id: str
    success: bool = True
    post_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self):
        """Validate publish result after initialization."""
        if not self.platform or not self.platform.strip():
            raise ValidationError("Platform name cannot be empty")
        
        if not self.success and not self.error:
            raise ValidationError("Failed publishes must have error information")


class TemplateSubstitution:
    """Utility class for template variable substitution."""
    
    @staticmethod
    def substitute(template: str, variables: Dict[str, Any]) -> str:
        """
        Substitute template variables with actual values.
        
        Supports:
        - Basic substitution: {variable_name}
        - Fallback values: {primary_var|fallback_var}
        - Conditional content: {?condition_var: content with {variable}}
        
        Args:
            template: Template string with variables
            variables: Dictionary of variable values
            
        Returns:
            String with variables substituted
            
        Raises:
            TemplateError: If template processing fails
        """
        if not TemplateSubstitution.validate_template(template):
            raise TemplateError(f"Invalid template syntax", template=template)
        
        try:
            result = template
            
            # Process conditional blocks first: {?var: content}
            # This pattern matches {?variable: content} where content can contain nested braces
            conditional_pattern = r'\{\?(\w+):\s*([^{}]*(?:\{[^}]*\}[^{}]*)*)\}'
            
            # Process all conditional blocks (may need multiple passes for nested conditions)
            while True:
                matches = list(re.finditer(conditional_pattern, result))
                if not matches:
                    break
                    
                for match in matches:
                    condition_var = match.group(1)
                    conditional_content = match.group(2)
                    
                    if condition_var in variables and variables[condition_var]:
                        # Condition met, process the conditional content
                        processed_content = TemplateSubstitution._substitute_simple(
                            conditional_content, variables
                        )
                        # Add space if conditional content doesn't start with space
                        if processed_content and not processed_content.startswith(' '):
                            processed_content = ' ' + processed_content
                        result = result.replace(match.group(0), processed_content)
                    else:
                        # Condition not met, remove the conditional block
                        result = result.replace(match.group(0), "")
            
            # Process fallback variables: {var1|var2}
            fallback_pattern = r'\{(\w+)\|(\w+)\}'
            for match in re.finditer(fallback_pattern, result):
                primary_var = match.group(1)
                fallback_var = match.group(2)
                
                if primary_var in variables and variables[primary_var]:
                    value = str(variables[primary_var])
                elif fallback_var in variables and variables[fallback_var]:
                    value = str(variables[fallback_var])
                else:
                    raise TemplateError(
                        f"Neither primary variable '{primary_var}' nor fallback '{fallback_var}' found",
                        template=template,
                        variable_name=primary_var
                    )
                
                result = result.replace(match.group(0), value)
            
            # Process simple variables: {variable}
            result = TemplateSubstitution._substitute_simple(result, variables)
            
            return result.strip()
            
        except Exception as e:
            if isinstance(e, TemplateError):
                raise
            raise TemplateError(f"Template processing failed: {e}", template=template)
    
    @staticmethod
    def _substitute_simple(text: str, variables: Dict[str, Any]) -> str:
        """Substitute simple {variable} patterns."""
        simple_pattern = r'\{(\w+)\}'
        
        def replace_var(match):
            var_name = match.group(1)
            if var_name not in variables:
                raise TemplateError(
                    f"Missing template variable: {var_name}",
                    variable_name=var_name
                )
            return str(variables[var_name])
        
        return re.sub(simple_pattern, replace_var, text)
    
    @staticmethod
    def validate_template(template: str) -> bool:
        """
        Validate template syntax.
        
        Args:
            template: Template string to validate
            
        Returns:
            True if template is valid, False otherwise
        """
        try:
            # Check for balanced braces
            brace_count = 0
            for char in template:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count < 0:  # More closing than opening braces
                        return False
            
            return brace_count == 0  # Should be balanced
            
        except Exception:
            return False
    
    @staticmethod
    def extract_variables(template: str) -> List[str]:
        """
        Extract all variable names from a template.
        
        Args:
            template: Template string
            
        Returns:
            List of variable names found in the template
        """
        variables = set()
        
        # Extract from simple variables: {variable}
        simple_pattern = r'\{(\w+)\}'
        variables.update(re.findall(simple_pattern, template))
        
        # Extract from fallback variables: {var1|var2}
        fallback_pattern = r'\{(\w+)\|(\w+)\}'
        for match in re.finditer(fallback_pattern, template):
            variables.add(match.group(1))
            variables.add(match.group(2))
        
        # Extract from conditional blocks: {?var: content}
        conditional_pattern = r'\{\?(\w+):\s*([^}]*)\}'
        for match in re.finditer(conditional_pattern, template):
            variables.add(match.group(1))
            # Also extract variables from conditional content
            conditional_content = match.group(2)
            variables.update(re.findall(simple_pattern, conditional_content))
        
        return sorted(list(variables))


class BasePublisher(ABC):
    """
    Abstract base class for all social media publishers.
    
    Provides common functionality including:
    - Authentication management
    - Template substitution for dynamic content
    - Post validation and formatting
    - Error handling and retry logic
    - Progress reporting
    - Async context manager support
    """
    
    def __init__(self, platform_name: str, config: Optional[PlatformConfig] = None):
        """
        Initialize the base publisher.
        
        Args:
            platform_name: Name of the platform (e.g., 'facebook', 'twitter')
            config: Platform-specific configuration
            
        Raises:
            ValidationError: If platform_name is empty
        """
        if not platform_name or not platform_name.strip():
            raise ValidationError("Platform name cannot be empty")
        
        self.platform_name = platform_name.strip()
        self.config = config or PlatformConfig(platform_name=self.platform_name)
        self.is_authenticated = False
        self.logger = logging.getLogger(f"medusa.publisher.{self.platform_name}")
        
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
    async def _publish_post(
        self,
        content: str,
        metadata: Dict[str, Any],
        progress_callback: Optional[Callable[[PublishProgress], None]] = None
    ) -> PublishResult:
        """
        Platform-specific post publishing implementation.
        
        Args:
            content: Post content (with variables already substituted)
            metadata: Platform-specific metadata
            progress_callback: Optional callback for progress updates
            
        Returns:
            PublishResult with publishing information
            
        Raises:
            PublishError: If publishing fails
        """
        pass
    
    @abstractmethod
    def _validate_content(self, content: str, metadata: Dict[str, Any]) -> None:
        """
        Validate content and metadata for platform-specific requirements.
        
        Args:
            content: Post content to validate
            metadata: Platform-specific metadata to validate
            
        Raises:
            ValidationError: If content or metadata is invalid
        """
        pass
    
    async def publish_post(
        self,
        content: str,
        metadata: Dict[str, Any],
        progress_callback: Optional[Callable[[PublishProgress], None]] = None
    ) -> PublishResult:
        """
        Publish post with template substitution, validation, and retry logic.
        
        Args:
            content: Post content (may contain template variables)
            metadata: Platform-specific metadata and template variables
            progress_callback: Optional callback for progress updates
            
        Returns:
            PublishResult with publishing information
            
        Raises:
            AuthenticationError: If authentication is required or fails
            ValidationError: If content validation fails
            TemplateError: If template processing fails
            PublishError: If publishing fails after all retries
        """
        # Check authentication
        if not self.is_authenticated:
            raise AuthenticationError(
                "Authentication required before publishing",
                platform=self.platform_name
            )
        
        # Process template substitution
        processed_content = self._process_template(content, metadata)
        
        # Validate content and metadata
        self._validate_content(processed_content, metadata)
        
        # Attempt publishing with retry logic
        last_error = None
        for attempt in range(self.retry_attempts + 1):
            try:
                if self.timeout > 0:
                    result = await asyncio.wait_for(
                        self._publish_post(processed_content, metadata, progress_callback),
                        timeout=self.timeout
                    )
                else:
                    result = await self._publish_post(processed_content, metadata, progress_callback)
                
                self.logger.info(f"Publishing successful on attempt {attempt + 1}")
                return result
                
            except Exception as e:
                last_error = e
                
                # Don't retry certain types of errors
                if not self._is_retryable_error(e) or attempt == self.retry_attempts:
                    self.logger.error(f"Publishing failed after {attempt + 1} attempts: {e}")
                    raise e
                
                # Log retry attempt
                self.logger.warning(f"Publishing attempt {attempt + 1} failed, retrying: {e}")
                
                # Exponential backoff
                await asyncio.sleep(2 ** attempt)
        
        # This should not be reached, but just in case
        if last_error:
            raise last_error
        else:
            raise PublishError("Publishing failed for unknown reason", platform=self.platform_name)
    
    def _process_template(self, content: str, metadata: Dict[str, Any]) -> str:
        """
        Process template variables in content.
        
        Args:
            content: Content with potential template variables
            metadata: Variables for substitution
            
        Returns:
            Content with variables substituted
            
        Raises:
            TemplateError: If template processing fails
        """
        try:
            # Only process if content contains template variables
            if '{' in content and '}' in content:
                return TemplateSubstitution.substitute(content, metadata)
            return content
            
        except TemplateError:
            raise
        except Exception as e:
            raise TemplateError(
                f"Template processing failed: {e}",
                template=content,
                platform=self.platform_name
            )
    
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
        if isinstance(error, (AuthenticationError, ValidationError, TemplateError)):
            return False
        
        # Other MedusaError types are generally not retryable
        if isinstance(error, MedusaError):
            return False
        
        # Generic exceptions are generally not retryable unless specifically network-related
        return False
    
    async def cleanup(self) -> None:
        """
        Clean up resources after publishing operations.
        
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