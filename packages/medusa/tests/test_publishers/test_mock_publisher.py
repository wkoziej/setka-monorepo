"""
Tests for MockPublisher implementation.
Tests configurable success/failure scenarios and template substitution.
"""

import pytest
from datetime import datetime

from medusa.publishers.mock import MockPublisher, MockPublishConfig
from medusa.publishers.base import PublishProgress, PublishResult
from medusa.models import PlatformConfig
from medusa.exceptions import (
    PublishError,
    AuthenticationError,
    ValidationError,
    TemplateError,
    NetworkError,
    RateLimitError,
)


class TestMockPublishConfig:
    """Test MockPublishConfig configuration class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = MockPublishConfig()

        assert config.auth_success is True
        assert config.publish_success is True
        assert config.publish_delay == 0.1
        assert config.auth_delay == 0.05
        assert config.simulate_progress is True
        assert config.progress_steps == 3
        assert config.auth_error is None
        assert config.publish_error is None
        assert config.content_requirements == []
        assert config.max_content_length == 5000

    def test_custom_config(self):
        """Test custom configuration values."""
        config = MockPublishConfig(
            auth_success=False,
            publish_success=False,
            publish_delay=2.0,
            auth_delay=1.0,
            simulate_progress=False,
            progress_steps=10,
            auth_error="Custom auth error",
            publish_error="Custom publish error",
            content_requirements=["title", "message"],
            max_content_length=280,
        )

        assert config.auth_success is False
        assert config.publish_success is False
        assert config.publish_delay == 2.0
        assert config.auth_delay == 1.0
        assert config.simulate_progress is False
        assert config.progress_steps == 10
        assert config.auth_error == "Custom auth error"
        assert config.publish_error == "Custom publish error"
        assert config.content_requirements == ["title", "message"]
        assert config.max_content_length == 280


class TestMockPublisher:
    """Test MockPublisher implementation."""

    def test_initialization(self):
        """Test MockPublisher initialization."""
        publisher = MockPublisher()

        assert publisher.platform_name == "mock"
        assert isinstance(publisher.mock_config, MockPublishConfig)
        assert publisher.is_authenticated is False
        assert publisher.call_log == []

    def test_initialization_with_config(self):
        """Test MockPublisher initialization with custom config."""
        platform_config = PlatformConfig(platform_name="test_mock")
        mock_config = MockPublishConfig(publish_delay=5.0)

        publisher = MockPublisher(
            platform_name="test_mock", config=platform_config, mock_config=mock_config
        )

        assert publisher.platform_name == "test_mock"
        assert publisher.config == platform_config
        assert publisher.mock_config.publish_delay == 5.0

    @pytest.mark.asyncio
    async def test_successful_authentication(self):
        """Test successful authentication."""
        publisher = MockPublisher()

        result = await publisher.authenticate()

        assert result is True
        assert publisher.is_authenticated is True
        assert len(publisher.call_log) == 1
        assert publisher.call_log[0]["method"] == "authenticate"
        assert publisher.call_log[0]["success"] is True

    @pytest.mark.asyncio
    async def test_failed_authentication(self):
        """Test failed authentication."""
        mock_config = MockPublishConfig(auth_success=False, auth_error="Auth failed")
        publisher = MockPublisher(mock_config=mock_config)

        with pytest.raises(AuthenticationError) as exc_info:
            await publisher.authenticate()

        assert "Auth failed" in str(exc_info.value)
        assert publisher.is_authenticated is False
        assert len(publisher.call_log) == 1
        assert publisher.call_log[0]["method"] == "authenticate"
        assert publisher.call_log[0]["success"] is False

    @pytest.mark.asyncio
    async def test_authentication_delay(self):
        """Test authentication with realistic delay."""
        mock_config = MockPublishConfig(auth_delay=0.2)
        publisher = MockPublisher(mock_config=mock_config)

        start_time = datetime.now()
        await publisher.authenticate()
        end_time = datetime.now()

        duration = (end_time - start_time).total_seconds()
        assert duration >= 0.2

    def test_content_validation_success(self):
        """Test successful content validation."""
        publisher = MockPublisher()
        content = "Test post content"
        metadata = {"title": "Test Title"}

        # Should not raise any exception
        publisher._validate_content(content, metadata)

    def test_content_validation_length_failure(self):
        """Test content validation failure due to length."""
        mock_config = MockPublishConfig(max_content_length=10)
        publisher = MockPublisher(mock_config=mock_config)
        content = "This content is too long for the limit"
        metadata = {}

        with pytest.raises(ValidationError) as exc_info:
            publisher._validate_content(content, metadata)

        assert "too long" in str(exc_info.value)

    def test_content_validation_requirements_failure(self):
        """Test content validation failure due to missing requirements."""
        mock_config = MockPublishConfig(content_requirements=["title", "message"])
        publisher = MockPublisher(mock_config=mock_config)
        content = "Test content"
        metadata = {"title": "Test"}  # Missing message

        with pytest.raises(ValidationError) as exc_info:
            publisher._validate_content(content, metadata)

        assert "message" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_successful_publish(self):
        """Test successful post publishing."""
        publisher = MockPublisher()
        publisher.is_authenticated = True

        content = "Test post content"
        metadata = {"title": "Test Post"}
        result = await publisher._publish_post(content, metadata)

        assert isinstance(result, PublishResult)
        assert result.platform == "mock"
        assert result.success is True
        assert result.post_url.startswith("https://mock-platform.com/")
        assert result.post_id.startswith("mock_post_")
        assert len(publisher.call_log) == 1
        assert publisher.call_log[0]["method"] == "_publish_post"

    @pytest.mark.asyncio
    async def test_failed_publish(self):
        """Test failed post publishing."""
        mock_config = MockPublishConfig(
            publish_success=False, publish_error="Publish failed"
        )
        publisher = MockPublisher(mock_config=mock_config)
        publisher.is_authenticated = True

        content = "Test post content"
        metadata = {"title": "Test Post"}

        with pytest.raises(PublishError) as exc_info:
            await publisher._publish_post(content, metadata)

        assert "Publish failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_publish_with_progress_callback(self):
        """Test publishing with progress reporting."""
        mock_config = MockPublishConfig(simulate_progress=True, progress_steps=3)
        publisher = MockPublisher(mock_config=mock_config)
        publisher.is_authenticated = True

        progress_calls = []

        def progress_callback(progress: PublishProgress):
            progress_calls.append(progress)

        content = "Test post content"
        metadata = {"title": "Test Post"}
        await publisher._publish_post(content, metadata, progress_callback)

        # Should have received progress updates
        assert len(progress_calls) >= 3
        assert progress_calls[0].percentage == 0.0
        assert progress_calls[-1].percentage == 100.0

        # Progress should be increasing
        for i in range(1, len(progress_calls)):
            assert progress_calls[i].percentage >= progress_calls[i - 1].percentage

    @pytest.mark.asyncio
    async def test_publish_delay(self):
        """Test publishing with realistic delay."""
        mock_config = MockPublishConfig(publish_delay=0.3, simulate_progress=False)
        publisher = MockPublisher(mock_config=mock_config)
        publisher.is_authenticated = True

        content = "Test post content"
        metadata = {"title": "Test Post"}

        start_time = datetime.now()
        await publisher._publish_post(content, metadata)
        end_time = datetime.now()

        duration = (end_time - start_time).total_seconds()
        assert duration >= 0.3

    @pytest.mark.asyncio
    async def test_network_error_simulation(self):
        """Test network error simulation."""
        mock_config = MockPublishConfig(
            publish_success=False, publish_error="Network timeout", error_type="network"
        )
        publisher = MockPublisher(mock_config=mock_config)
        publisher.is_authenticated = True

        content = "Test post content"
        metadata = {"title": "Test Post"}

        with pytest.raises(NetworkError):
            await publisher._publish_post(content, metadata)

    @pytest.mark.asyncio
    async def test_rate_limit_error_simulation(self):
        """Test rate limit error simulation."""
        mock_config = MockPublishConfig(
            publish_success=False,
            publish_error="Rate limit exceeded",
            error_type="rate_limit",
        )
        publisher = MockPublisher(mock_config=mock_config)
        publisher.is_authenticated = True

        content = "Test post content"
        metadata = {"title": "Test Post"}

        with pytest.raises(RateLimitError):
            await publisher._publish_post(content, metadata)

    @pytest.mark.asyncio
    async def test_template_substitution(self):
        """Test template variable substitution."""
        publisher = MockPublisher()
        publisher.is_authenticated = True

        content = "Check out my video: {youtube_url}"
        metadata = {
            "youtube_url": "https://youtube.com/watch?v=abc123",
            "title": "Test Post",
        }

        result = await publisher.publish_post(content, metadata)

        assert result.success is True
        # Check that template was processed (logged content should contain substituted URL)
        publish_calls = publisher.get_calls("_publish_post")
        assert len(publish_calls) == 1
        assert "https://youtube.com/watch?v=abc123" in publish_calls[0]["content"]

    @pytest.mark.asyncio
    async def test_template_error_handling(self):
        """Test template error handling."""
        mock_config = MockPublishConfig(
            publish_success=False, publish_error="Template error", error_type="template"
        )
        publisher = MockPublisher(mock_config=mock_config)
        publisher.is_authenticated = True

        content = "Check out my video: {missing_variable}"
        metadata = {"title": "Test Post"}

        with pytest.raises(TemplateError):
            await publisher.publish_post(content, metadata)

    def test_call_log_tracking(self):
        """Test that all calls are properly logged."""
        publisher = MockPublisher()

        # Initially empty
        assert publisher.call_log == []

        # Clear log
        publisher.clear_call_log()
        assert publisher.call_log == []

    @pytest.mark.asyncio
    async def test_full_publish_workflow(self):
        """Test complete publishing workflow through public interface."""
        publisher = MockPublisher()
        content = "Test post content"
        metadata = {"title": "Test Post"}

        # Should fail without authentication
        with pytest.raises(AuthenticationError):
            await publisher.publish_post(content, metadata)

        # Authenticate first
        await publisher.authenticate()

        # Now publish should work
        result = await publisher.publish_post(content, metadata)

        assert result.success is True
        assert result.platform == "mock"
        assert len(publisher.call_log) >= 2  # authenticate + publish

    def test_verification_helpers(self):
        """Test verification helper methods."""
        publisher = MockPublisher()

        # Test was_called
        assert publisher.was_called("authenticate") is False

        # Test get_call_count
        assert publisher.get_call_count("authenticate") == 0

        # Test get_calls
        assert publisher.get_calls("authenticate") == []

    @pytest.mark.asyncio
    async def test_verification_after_calls(self):
        """Test verification helpers after making calls."""
        publisher = MockPublisher()
        content = "Test post"
        metadata = {"title": "Test"}

        await publisher.authenticate()
        publisher.is_authenticated = True
        await publisher._publish_post(content, metadata)

        # Test verification methods
        assert publisher.was_called("authenticate") is True
        assert publisher.was_called("_publish_post") is True
        assert publisher.was_called("nonexistent") is False

        assert publisher.get_call_count("authenticate") == 1
        assert publisher.get_call_count("_publish_post") == 1

        auth_calls = publisher.get_calls("authenticate")
        assert len(auth_calls) == 1
        assert auth_calls[0]["method"] == "authenticate"

        publish_calls = publisher.get_calls("_publish_post")
        assert len(publish_calls) == 1
        assert publish_calls[0]["content"] == content

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager functionality."""
        publisher = MockPublisher()

        async with publisher:
            assert publisher.is_authenticated is True

        # Cleanup should have been called
        assert publisher.was_called("cleanup")

    @pytest.mark.asyncio
    async def test_context_manager_auth_failure(self):
        """Test context manager with authentication failure."""
        mock_config = MockPublishConfig(auth_success=False, auth_error="Auth failed")
        publisher = MockPublisher(mock_config=mock_config)

        with pytest.raises(AuthenticationError):
            async with publisher:
                pass
