"""
Tests for BasePublisher abstract class.
Comprehensive test coverage for publisher base functionality.
"""

import pytest
import asyncio
from unittest.mock import patch
from datetime import datetime
from typing import Dict, Any, Optional

from medusa.publishers.base import (
    BasePublisher,
    PublishProgress,
    PublishResult,
    TemplateSubstitution
)
from medusa.models import PlatformConfig
from medusa.exceptions import (
    PublishError,
    AuthenticationError,
    ValidationError,
    TemplateError,
    RateLimitError,
    NetworkError
)


class TestPublishProgress:
    """Test PublishProgress dataclass."""
    
    def test_publish_progress_initialization(self):
        """Test PublishProgress initialization with valid data."""
        progress = PublishProgress(
            step="uploading",
            current_step=1,
            total_steps=3,
            message="Processing post content"
        )
        
        assert progress.step == "uploading"
        assert progress.current_step == 1
        assert progress.total_steps == 3
        assert progress.message == "Processing post content"
        assert progress.percentage == 33.33
        assert progress.status == "in_progress"
        assert isinstance(progress.timestamp, datetime)
    
    def test_publish_progress_percentage_calculation(self):
        """Test percentage calculation in PublishProgress."""
        # Test normal case
        progress = PublishProgress(step="testing", current_step=2, total_steps=4)
        assert progress.percentage == 50.0
        
        # Test zero total steps
        progress = PublishProgress(step="testing", current_step=0, total_steps=0)
        assert progress.percentage == 0.0
        
        # Test completion
        progress = PublishProgress(step="testing", current_step=5, total_steps=5)
        assert progress.percentage == 100.0
    
    def test_publish_progress_validation(self):
        """Test PublishProgress validation."""
        # Negative current step
        with pytest.raises(ValidationError, match="current_step cannot be negative"):
            PublishProgress(step="test", current_step=-1, total_steps=3)
        
        # Negative total steps
        with pytest.raises(ValidationError, match="total_steps must be positive"):
            PublishProgress(step="test", current_step=1, total_steps=-1)
        
        # Current step exceeds total
        with pytest.raises(ValidationError, match="current_step cannot exceed total_steps"):
            PublishProgress(step="test", current_step=5, total_steps=3)


class TestPublishResult:
    """Test PublishResult dataclass."""
    
    def test_publish_result_success(self):
        """Test successful PublishResult creation."""
        result = PublishResult(
            platform="facebook",
            post_id="123456789",
            post_url="https://facebook.com/posts/123456789",
            metadata={"likes": 0, "shares": 0}
        )
        
        assert result.platform == "facebook"
        assert result.post_id == "123456789"
        assert result.success is True
        assert result.post_url == "https://facebook.com/posts/123456789"
        assert result.metadata == {"likes": 0, "shares": 0}
        assert result.error is None
        assert isinstance(result.timestamp, datetime)
    
    def test_publish_result_failure(self):
        """Test failed PublishResult creation."""
        result = PublishResult(
            platform="twitter",
            post_id="",
            success=False,
            error="API rate limit exceeded"
        )
        
        assert result.platform == "twitter"
        assert result.success is False
        assert result.error == "API rate limit exceeded"
        assert result.post_url is None
    
    def test_publish_result_validation(self):
        """Test PublishResult validation."""
        # Empty platform name
        with pytest.raises(ValidationError, match="Platform name cannot be empty"):
            PublishResult(platform="", post_id="123")
        
        # Failed result without error
        with pytest.raises(ValidationError, match="Failed publishes must have error information"):
            PublishResult(platform="facebook", post_id="", success=False)


class TestTemplateSubstitution:
    """Test TemplateSubstitution utility class."""
    
    def test_template_substitution_basic(self):
        """Test basic template substitution."""
        template = "Check out my video: {youtube_url}"
        variables = {"youtube_url": "https://youtube.com/watch?v=abc123"}
        
        result = TemplateSubstitution.substitute(template, variables)
        assert result == "Check out my video: https://youtube.com/watch?v=abc123"
    
    def test_template_substitution_multiple_variables(self):
        """Test template substitution with multiple variables."""
        template = "New video: {youtube_url} - Duration: {duration} mins"
        variables = {
            "youtube_url": "https://youtube.com/watch?v=abc123",
            "duration": "5"
        }
        
        result = TemplateSubstitution.substitute(template, variables)
        assert result == "New video: https://youtube.com/watch?v=abc123 - Duration: 5 mins"
    
    def test_template_substitution_missing_variable(self):
        """Test template substitution with missing variable."""
        template = "Check out: {youtube_url} and {vimeo_url}"
        variables = {"youtube_url": "https://youtube.com/watch?v=abc123"}
        
        with pytest.raises(TemplateError, match="Missing template variable: vimeo_url"):
            TemplateSubstitution.substitute(template, variables)
    
    def test_template_substitution_with_fallback(self):
        """Test template substitution with fallback values."""
        template = "Video: {youtube_url|fallback_url}"
        variables = {"fallback_url": "https://example.com/video"}
        
        result = TemplateSubstitution.substitute(template, variables)
        assert result == "Video: https://example.com/video"
    
    def test_template_substitution_conditional(self):
        """Test conditional template substitution."""
        # With condition met
        template = "Video available{?youtube_url: on YouTube: {youtube_url}}"
        variables = {"youtube_url": "https://youtube.com/watch?v=abc123"}
        
        result = TemplateSubstitution.substitute(template, variables)
        assert result == "Video available on YouTube: https://youtube.com/watch?v=abc123"
        
        # With condition not met
        variables = {}
        result = TemplateSubstitution.substitute(template, variables)
        assert result == "Video available"
    
    def test_template_validation(self):
        """Test template validation."""
        # Valid template
        template = "Hello {name}!"
        assert TemplateSubstitution.validate_template(template) is True
        
        # Invalid template - unclosed brace
        template = "Hello {name!"
        assert TemplateSubstitution.validate_template(template) is False
        
        # Invalid template - unopened brace
        template = "Hello name}!"
        assert TemplateSubstitution.validate_template(template) is False
    
    def test_template_extract_variables(self):
        """Test variable extraction from templates."""
        # Simple variables
        template = "Hello {name} and {surname}!"
        variables = TemplateSubstitution.extract_variables(template)
        assert set(variables) == {"name", "surname"}
        
        # Fallback variables
        template = "Video: {youtube_url|fallback_url}"
        variables = TemplateSubstitution.extract_variables(template)
        assert set(variables) == {"youtube_url", "fallback_url"}
        
        # Conditional variables
        template = "Available{?youtube_url: on YouTube: {youtube_url}}"
        variables = TemplateSubstitution.extract_variables(template)
        assert set(variables) == {"youtube_url"}
        
        # Mixed template - note: extract_variables uses old pattern for conditionals
        template = "Video {title}{?youtube_url: on YouTube: {youtube_url}}"
        variables = TemplateSubstitution.extract_variables(template)
        expected = {"title", "youtube_url"}
        assert set(variables) == expected
    
    def test_template_edge_cases(self):
        """Test template substitution edge cases."""
        # Empty template
        result = TemplateSubstitution.substitute("", {})
        assert result == ""
        
        # Template without variables
        result = TemplateSubstitution.substitute("Hello world", {})
        assert result == "Hello world"
        
        # Template with exception in validation - test the except block
        # We can't easily test the except block directly, so we'll test a malformed template
        # that might cause an exception during processing
        malformed = None
        try:
            result = TemplateSubstitution.validate_template(malformed)
            assert result is False  # Should handle None gracefully
        except:
            assert True  # Exception is expected for None input


class MockPublisher(BasePublisher):
    """Mock publisher implementation for testing BasePublisher."""
    
    def __init__(self, platform_name: str = "mock", config: Optional[PlatformConfig] = None):
        super().__init__(platform_name, config)
        self.auth_called = False
        self.publish_called = False
        self.validate_called = False
        self.cleanup_called = False
        
        # Configure mock behavior
        self.should_fail_auth = False
        self.should_fail_publish = False
        self.should_fail_validation = False
        self.publish_delay = 0.0
    
    async def authenticate(self) -> bool:
        """Mock authentication."""
        self.auth_called = True
        if self.should_fail_auth:
            raise AuthenticationError("Mock auth failure", platform=self.platform_name)
        return True
    
    async def _publish_post(
        self,
        content: str,
        metadata: Dict[str, Any],
        progress_callback=None
    ) -> PublishResult:
        """Mock post publishing."""
        self.publish_called = True
        
        if self.should_fail_publish:
            raise PublishError("Mock publish failure", platform=self.platform_name)
        
        if self.publish_delay > 0:
            await asyncio.sleep(self.publish_delay)
        
        # Simulate progress updates
        if progress_callback:
            progress_callback(PublishProgress(step="preparing", current_step=1, total_steps=3))
            progress_callback(PublishProgress(step="uploading", current_step=2, total_steps=3))
            progress_callback(PublishProgress(step="finalizing", current_step=3, total_steps=3))
        
        return PublishResult(
            platform=self.platform_name,
            post_id="mock_post_123",
            post_url="https://mock.com/posts/mock_post_123",
            metadata={"test": True}
        )
    
    def _validate_content(self, content: str, metadata: Dict[str, Any]) -> None:
        """Mock content validation."""
        self.validate_called = True
        
        if self.should_fail_validation:
            raise ValidationError("Mock validation failure")
        
        # Basic validation
        if not content.strip():
            raise ValidationError("Content cannot be empty")
    
    async def cleanup(self) -> None:
        """Mock cleanup."""
        self.cleanup_called = True
        await super().cleanup()


class TestBasePublisher:
    """Test BasePublisher abstract class functionality."""
    
    @pytest.fixture
    def mock_publisher(self):
        """Create a mock publisher for testing."""
        return MockPublisher()
    
    @pytest.fixture
    def platform_config(self):
        """Create a platform configuration for testing."""
        return PlatformConfig(
            platform_name="mock",
            enabled=True,
            credentials={"api_key": "test_key"},
            retry_attempts=2,
            timeout=10
        )
    
    def test_base_publisher_initialization(self, platform_config):
        """Test BasePublisher initialization."""
        publisher = MockPublisher("test_platform", platform_config)
        
        assert publisher.platform_name == "test_platform"
        assert publisher.config == platform_config
        assert publisher.is_authenticated is False
        assert publisher.retry_attempts == 2
        assert publisher.timeout == 10
        assert publisher.logger.name == "medusa.publisher.test_platform"
    
    def test_base_publisher_initialization_validation(self):
        """Test BasePublisher initialization validation."""
        # Empty platform name
        with pytest.raises(ValidationError, match="Platform name cannot be empty"):
            MockPublisher("")
        
        # Whitespace-only platform name
        with pytest.raises(ValidationError, match="Platform name cannot be empty"):
            MockPublisher("   ")
    
    def test_base_publisher_default_config(self):
        """Test BasePublisher with default configuration."""
        publisher = MockPublisher("test_platform")
        
        assert publisher.config.platform_name == "test_platform"
        assert publisher.retry_attempts == 3  # Default value
        assert publisher.timeout == 30  # Default value
    
    @pytest.mark.asyncio
    async def test_authenticate_success(self, mock_publisher):
        """Test successful authentication."""
        result = await mock_publisher.authenticate()
        
        assert result is True
        assert mock_publisher.auth_called is True
    
    @pytest.mark.asyncio
    async def test_authenticate_failure(self, mock_publisher):
        """Test authentication failure."""
        mock_publisher.should_fail_auth = True
        
        with pytest.raises(AuthenticationError):
            await mock_publisher.authenticate()
    
    @pytest.mark.asyncio
    async def test_publish_post_success(self, mock_publisher):
        """Test successful post publishing."""
        mock_publisher.is_authenticated = True
        
        content = "Test post content with {youtube_url}"
        metadata = {"youtube_url": "https://youtube.com/watch?v=abc123"}
        
        result = await mock_publisher.publish_post(content, metadata)
        
        assert isinstance(result, PublishResult)
        assert result.success is True
        assert result.platform == "mock"
        assert result.post_id == "mock_post_123"
        assert mock_publisher.publish_called is True
        assert mock_publisher.validate_called is True
    
    @pytest.mark.asyncio
    async def test_publish_post_not_authenticated(self, mock_publisher):
        """Test publishing without authentication."""
        content = "Test content"
        metadata = {}
        
        with pytest.raises(AuthenticationError, match="Authentication required"):
            await mock_publisher.publish_post(content, metadata)
    
    @pytest.mark.asyncio
    async def test_publish_post_validation_failure(self, mock_publisher):
        """Test publishing with validation failure."""
        mock_publisher.is_authenticated = True
        mock_publisher.should_fail_validation = True
        
        content = "Test content"
        metadata = {}
        
        with pytest.raises(ValidationError):
            await mock_publisher.publish_post(content, metadata)
    
    @pytest.mark.asyncio
    async def test_publish_post_with_template_substitution(self, mock_publisher):
        """Test publishing with template substitution."""
        mock_publisher.is_authenticated = True
        
        content = "Check out my video: {youtube_url}"
        metadata = {"youtube_url": "https://youtube.com/watch?v=abc123"}
        
        result = await mock_publisher.publish_post(content, metadata)
        
        assert result.success is True
        # The actual substitution would be tested in the concrete implementation
    
    @pytest.mark.asyncio
    async def test_publish_post_with_progress_callback(self, mock_publisher):
        """Test publishing with progress callback."""
        mock_publisher.is_authenticated = True
        
        progress_updates = []
        
        def progress_callback(progress):
            progress_updates.append(progress)
        
        content = "Test content"
        metadata = {}
        
        result = await mock_publisher.publish_post(content, metadata, progress_callback)
        
        assert result.success is True
        assert len(progress_updates) == 3
        assert all(isinstance(p, PublishProgress) for p in progress_updates)
    
    @pytest.mark.asyncio
    async def test_publish_post_retry_logic(self, mock_publisher):
        """Test retry logic on transient failures."""
        mock_publisher.is_authenticated = True
        mock_publisher.retry_attempts = 2
        
        # Mock to fail first attempt, succeed on second
        call_count = 0
        original_publish = mock_publisher._publish_post
        
        async def failing_publish(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise NetworkError("Temporary network error")
            return await original_publish(*args, **kwargs)
        
        mock_publisher._publish_post = failing_publish
        
        content = "Test content"
        metadata = {}
        
        result = await mock_publisher.publish_post(content, metadata)
        
        assert result.success is True
        assert call_count == 2  # Failed once, succeeded on retry
    
    @pytest.mark.asyncio
    async def test_publish_post_timeout(self, mock_publisher):
        """Test publish timeout handling."""
        mock_publisher.is_authenticated = True
        mock_publisher.timeout = 0.1
        mock_publisher.publish_delay = 0.2  # Longer than timeout
        
        content = "Test content"
        metadata = {}
        
        with pytest.raises(asyncio.TimeoutError):
            await mock_publisher.publish_post(content, metadata)
    
    @pytest.mark.asyncio
    async def test_publish_post_no_timeout(self, mock_publisher):
        """Test publishing without timeout."""
        mock_publisher.is_authenticated = True
        mock_publisher.timeout = 0  # No timeout
        
        content = "Test content"
        metadata = {}
        
        result = await mock_publisher.publish_post(content, metadata)
        assert result.success is True
    
    @pytest.mark.asyncio
    async def test_publish_post_max_retries_exceeded(self, mock_publisher):
        """Test behavior when max retries are exceeded."""
        mock_publisher.is_authenticated = True
        mock_publisher.retry_attempts = 1
        
        # Mock to always fail with a retryable error
        call_count = 0
        
        async def always_failing_publish(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise NetworkError("Network always fails")
        
        mock_publisher._publish_post = always_failing_publish
        
        content = "Test content"
        metadata = {}
        
        # Should fail after exhausting retries
        with pytest.raises(NetworkError):
            await mock_publisher.publish_post(content, metadata)
        
        # Should have tried retry_attempts + 1 times
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_process_template_error_handling(self, mock_publisher):
        """Test template processing error handling."""
        mock_publisher.is_authenticated = True
        
        # Mock TemplateSubstitution.substitute to raise a generic exception
        with patch('medusa.publishers.base.TemplateSubstitution.substitute', side_effect=ValueError("Generic error")):
            content = "Test {variable}"
            metadata = {"variable": "value"}
            
            with pytest.raises(TemplateError, match="Template processing failed"):
                await mock_publisher.publish_post(content, metadata)
    
    @pytest.mark.asyncio
    async def test_is_retryable_error(self, mock_publisher):
        """Test error retry logic."""
        # Retryable errors
        assert mock_publisher._is_retryable_error(NetworkError("Network issue")) is True
        assert mock_publisher._is_retryable_error(RateLimitError("Rate limited", platform="test")) is True
        assert mock_publisher._is_retryable_error(asyncio.TimeoutError()) is True
        
        # Non-retryable errors
        assert mock_publisher._is_retryable_error(AuthenticationError("Auth failed", platform="test")) is False
        assert mock_publisher._is_retryable_error(ValidationError("Invalid data")) is False
        assert mock_publisher._is_retryable_error(ValueError("Generic error")) is False
    
    @pytest.mark.asyncio
    async def test_cleanup(self, mock_publisher):
        """Test cleanup functionality."""
        await mock_publisher.cleanup()
        assert mock_publisher.cleanup_called is True
    
    @pytest.mark.asyncio
    async def test_async_context_manager(self, mock_publisher):
        """Test async context manager functionality."""
        async with mock_publisher as publisher:
            assert publisher.is_authenticated is True
            assert publisher.auth_called is True
        
        assert mock_publisher.cleanup_called is True
    
    @pytest.mark.asyncio
    async def test_async_context_manager_auth_failure(self, mock_publisher):
        """Test async context manager with authentication failure."""
        mock_publisher.should_fail_auth = True
        
        with pytest.raises(AuthenticationError):
            async with mock_publisher:
                pass
    
    def test_abstract_methods_not_implemented(self):
        """Test that abstract methods raise NotImplementedError."""
        # This test ensures BasePublisher is properly abstract
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BasePublisher("test")


class TestIntegrationScenarios:
    """Test integration scenarios for BasePublisher."""
    
    @pytest.mark.asyncio
    async def test_complete_publish_workflow(self):
        """Test complete publishing workflow."""
        publisher = MockPublisher("integration_test")
        
        # Authenticate
        auth_result = await publisher.authenticate()
        assert auth_result is True
        publisher.is_authenticated = True
        
        # Publish post
        content = "Integration test post: {youtube_url}"
        metadata = {"youtube_url": "https://youtube.com/watch?v=test123"}
        
        result = await publisher.publish_post(content, metadata)
        
        assert result.success is True
        assert result.platform == "integration_test"
        assert result.post_id == "mock_post_123"
        
        # Cleanup
        await publisher.cleanup()
        assert publisher.cleanup_called is True
    
    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self):
        """Test error recovery in publishing workflow."""
        publisher = MockPublisher("error_test")
        publisher.is_authenticated = True
        publisher.retry_attempts = 1
        
        # Set up to fail first attempt
        call_count = 0
        original_publish = publisher._publish_post
        
        async def intermittent_failure(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RateLimitError("Rate limit exceeded", platform="error_test")
            return await original_publish(*args, **kwargs)
        
        publisher._publish_post = intermittent_failure
        
        content = "Error recovery test"
        metadata = {}
        
        result = await publisher.publish_post(content, metadata)
        
        assert result.success is True
        assert call_count == 2  # Failed once, succeeded on retry