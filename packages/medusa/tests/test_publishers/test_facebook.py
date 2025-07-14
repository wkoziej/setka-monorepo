"""
Tests for FacebookPublisher class.

This module contains comprehensive tests for Facebook post publishing
functionality, including text posts, link posts, validation, and error handling.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from medusa.publishers.facebook import FacebookPublisher
from medusa.publishers.base import PublishResult, PublishProgress
from medusa.models import PlatformConfig
from medusa.exceptions import (
    PublishError,
    AuthenticationError,
    ValidationError,
    NetworkError,
    ConfigurationError,
    TemplateError
)


class TestFacebookPublisher:
    """Test suite for FacebookPublisher class."""
    
    @pytest.fixture
    def valid_config(self) -> Dict[str, Any]:
        """Provide valid Facebook configuration for testing."""
        return {
            "page_id": "123456789",
            "access_token": "valid_access_token",
            "app_id": "app_123456",
            "app_secret": "app_secret_123",
            "api_version": "v19.0"
        }
    
    @pytest.fixture
    def platform_config(self, valid_config: Dict[str, Any]) -> PlatformConfig:
        """Provide PlatformConfig instance for testing."""
        return PlatformConfig(platform_name="facebook", credentials=valid_config)
    
    @pytest.fixture
    def publisher(self, platform_config: PlatformConfig) -> FacebookPublisher:
        """Create FacebookPublisher instance for testing."""
        return FacebookPublisher(config=platform_config)
    
    @pytest.fixture
    def mock_auth(self):
        """Mock FacebookAuth for testing."""
        with patch('medusa.publishers.facebook.FacebookAuth') as mock_auth:
            mock_instance = Mock()
            mock_instance.test_connection.return_value = True
            mock_instance.check_permissions.return_value = True
            mock_instance.verify_page_access.return_value = True
            mock_auth.return_value = mock_instance
            yield mock_instance

    def test_init_with_valid_config(self, platform_config: PlatformConfig):
        """Test FacebookPublisher initialization with valid configuration."""
        publisher = FacebookPublisher(config=platform_config)
        
        assert publisher.platform_name == "facebook"
        assert publisher.config == platform_config
        assert publisher._auth is None  # Not initialized until authenticate()
    
    def test_init_with_invalid_config_type(self):
        """Test FacebookPublisher initialization with invalid config type."""
        with pytest.raises(ValidationError) as exc_info:
            FacebookPublisher(config="invalid_config")
        
        assert "Invalid configuration type" in str(exc_info.value)
    
    def test_init_with_none_config(self):
        """Test FacebookPublisher initialization with None config."""
        with pytest.raises(ValidationError) as exc_info:
            FacebookPublisher(config=None)
        
        assert "Configuration cannot be None" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_authenticate_success(self, publisher: FacebookPublisher, mock_auth):
        """Test successful authentication."""
        result = await publisher.authenticate()
        
        assert result is True
        assert publisher._auth is not None
        mock_auth.test_connection.assert_called_once()
        mock_auth.check_permissions.assert_called_once()
        mock_auth.verify_page_access.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_authenticate_connection_failure(self, publisher: FacebookPublisher, mock_auth):
        """Test authentication failure due to connection issues."""
        mock_auth.test_connection.return_value = False
        
        with pytest.raises(AuthenticationError) as exc_info:
            await publisher.authenticate()
        
        assert "Failed to connect to Facebook API" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_authenticate_permission_failure(self, publisher: FacebookPublisher, mock_auth):
        """Test authentication failure due to insufficient permissions."""
        mock_auth.check_permissions.return_value = False
        
        with pytest.raises(AuthenticationError) as exc_info:
            await publisher.authenticate()
        
        assert "Insufficient Facebook permissions" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_authenticate_page_access_failure(self, publisher: FacebookPublisher, mock_auth):
        """Test authentication failure due to page access issues."""
        mock_auth.verify_page_access.return_value = False
        
        with pytest.raises(AuthenticationError) as exc_info:
            await publisher.authenticate()
        
        assert "Cannot access Facebook page" in str(exc_info.value)
    
    def test_validate_content_valid_text_post(self, publisher: FacebookPublisher):
        """Test content validation for valid text post."""
        content = "This is a valid Facebook post with some text."
        metadata = {"type": "text"}
        
        # Should not raise any exception
        publisher._validate_content(content, metadata)
    
    def test_validate_content_valid_link_post(self, publisher: FacebookPublisher):
        """Test content validation for valid link post."""
        content = "Check out this video: https://youtube.com/watch?v=abc123"
        metadata = {"type": "link", "link": "https://youtube.com/watch?v=abc123"}
        
        # Should not raise any exception
        publisher._validate_content(content, metadata)
    
    def test_validate_content_empty_content(self, publisher: FacebookPublisher):
        """Test content validation with empty content."""
        with pytest.raises(ValidationError) as exc_info:
            publisher._validate_content("", {})
        
        assert "Post content cannot be empty" in str(exc_info.value)
    
    def test_validate_content_too_long(self, publisher: FacebookPublisher):
        """Test content validation with content too long."""
        # Facebook limit is 63,206 characters
        long_content = "a" * 65000
        
        with pytest.raises(ValidationError) as exc_info:
            publisher._validate_content(long_content, {})
        
        assert "Post content exceeds maximum length" in str(exc_info.value)
    
    def test_validate_content_invalid_link(self, publisher: FacebookPublisher):
        """Test content validation with invalid link."""
        content = "Check out this link"
        metadata = {
            "type": "link",
            "link": "not-a-valid-url"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            publisher._validate_content(content, metadata)
        
        assert "Invalid URL format" in str(exc_info.value)
    
    def test_validate_content_scheduled_post_invalid_timestamp_type(self, publisher: FacebookPublisher):
        """Test validation of scheduled post with invalid timestamp type."""
        content = "Scheduled post"
        metadata = {
            "scheduled_publish_time": "not-a-number"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            publisher._validate_content(content, metadata)
        
        assert "must be a positive integer timestamp" in str(exc_info.value)
    
    def test_validate_content_scheduled_post_negative_timestamp(self, publisher: FacebookPublisher):
        """Test validation of scheduled post with negative timestamp."""
        content = "Scheduled post"
        metadata = {
            "scheduled_publish_time": -1
        }
        
        with pytest.raises(ValidationError) as exc_info:
            publisher._validate_content(content, metadata)
        
        assert "must be a positive integer timestamp" in str(exc_info.value)
    
    def test_validate_content_scheduled_post_zero_timestamp(self, publisher: FacebookPublisher):
        """Test validation of scheduled post with zero timestamp."""
        content = "Scheduled post"
        metadata = {
            "scheduled_publish_time": 0
        }
        
        with pytest.raises(ValidationError) as exc_info:
            publisher._validate_content(content, metadata)
        
        assert "must be a positive integer timestamp" in str(exc_info.value)
    
    def test_validate_content_scheduled_post_past_timestamp(self, publisher: FacebookPublisher):
        """Test validation of scheduled post with past timestamp."""
        content = "Scheduled post"
        past_time = int(datetime.now(timezone.utc).timestamp()) - 3600  # 1 hour ago
        metadata = {
            "scheduled_publish_time": past_time
        }
        
        with pytest.raises(ValidationError) as exc_info:
            publisher._validate_content(content, metadata)
        
        assert "must be in the future" in str(exc_info.value)
    
    def test_validate_content_scheduled_post_current_timestamp(self, publisher: FacebookPublisher):
        """Test validation of scheduled post with current timestamp."""
        content = "Scheduled post"
        current_time = int(datetime.now(timezone.utc).timestamp())
        metadata = {
            "scheduled_publish_time": current_time
        }
        
        with pytest.raises(ValidationError) as exc_info:
            publisher._validate_content(content, metadata)
        
        assert "must be in the future" in str(exc_info.value)
    
    def test_validate_content_scheduled_post_valid_future_timestamp(self, publisher: FacebookPublisher):
        """Test validation of scheduled post with valid future timestamp."""
        content = "Scheduled post"
        future_time = int(datetime.now(timezone.utc).timestamp()) + 3600  # 1 hour from now
        metadata = {
            "scheduled_publish_time": future_time
        }
        
        # Should not raise any exception
        publisher._validate_content(content, metadata)
    
    @pytest.mark.asyncio
    async def test_publish_post_text_success(self, publisher: FacebookPublisher, mock_auth):
        """Test successful text post publishing."""
        # Setup
        await publisher.authenticate()
        
        content = "This is a test post"
        metadata = {"type": "text"}
        
        # Mock API response
        mock_response = {
            "id": "123456789_987654321",
            "post_id": "987654321"
        }
        
        with patch.object(publisher._auth, '_make_api_request', return_value=mock_response):
            result = await publisher._publish_post(content, metadata)
        
        # Verify result
        assert isinstance(result, PublishResult)
        assert result.platform == "facebook"
        assert result.post_id == "987654321"
        assert result.success is True
        assert result.post_url == "https://facebook.com/123456789/posts/987654321"
        assert result.error is None
    
    @pytest.mark.asyncio
    async def test_publish_post_link_success(self, publisher: FacebookPublisher, mock_auth):
        """Test successful link post publishing."""
        # Setup
        await publisher.authenticate()
        
        content = "Check out this video: https://youtube.com/watch?v=abc123"
        metadata = {
            "type": "link",
            "link": "https://youtube.com/watch?v=abc123",
            "name": "My Video Title",
            "description": "Video description"
        }
        
        # Mock API response
        mock_response = {
            "id": "123456789_987654321",
            "post_id": "987654321"
        }
        
        with patch.object(publisher._auth, '_make_api_request', return_value=mock_response):
            result = await publisher._publish_post(content, metadata)
        
        # Verify result
        assert isinstance(result, PublishResult)
        assert result.platform == "facebook"
        assert result.post_id == "987654321"
        assert result.success is True
        assert result.metadata["link"] == "https://youtube.com/watch?v=abc123"
    
    @pytest.mark.asyncio
    async def test_publish_post_scheduled_success(self, publisher: FacebookPublisher, mock_auth):
        """Test successful scheduled post publishing."""
        # Setup
        await publisher.authenticate()
        
        content = "This is a scheduled post"
        future_time = int((datetime.now(timezone.utc).timestamp()) + 3600)  # 1 hour from now
        metadata = {
            "type": "text",
            "scheduled_publish_time": future_time
        }
        
        # Mock API response
        mock_response = {
            "id": "123456789_987654321",
            "post_id": "987654321"
        }
        
        with patch.object(publisher._auth, '_make_api_request', return_value=mock_response):
            result = await publisher._publish_post(content, metadata)
        
        # Verify result
        assert result.success is True
        assert result.metadata["scheduled_publish_time"] == future_time
    
    @pytest.mark.asyncio
    async def test_publish_post_progress_callback(self, publisher: FacebookPublisher, mock_auth):
        """Test progress callback during post publishing."""
        # Setup
        await publisher.authenticate()
        
        content = "Test post with progress"
        metadata = {"type": "text"}
        progress_calls = []
        
        def progress_callback(progress: PublishProgress):
            progress_calls.append(progress)
        
        # Mock API response
        mock_response = {
            "id": "123456789_987654321",
            "post_id": "987654321"
        }
        
        with patch.object(publisher._auth, '_make_api_request', return_value=mock_response):
            await publisher._publish_post(content, metadata, progress_callback)
        
        # Verify progress callbacks
        assert len(progress_calls) >= 2  # At least start and complete
        assert progress_calls[0].step == "Preparing post"
        assert progress_calls[-1].step == "Post published"
        assert progress_calls[-1].status == "completed"
    
    @pytest.mark.asyncio
    async def test_publish_post_api_error(self, publisher: FacebookPublisher, mock_auth):
        """Test post publishing with API error."""
        # Setup
        await publisher.authenticate()
        
        content = "Test post"
        metadata = {"type": "text"}
        
        # Mock API error
        api_error = NetworkError("API rate limit exceeded", platform="facebook")
        
        with patch.object(publisher._auth, '_make_api_request', side_effect=api_error):
            with pytest.raises(PublishError) as exc_info:
                await publisher._publish_post(content, metadata)
        
        assert "Failed to publish post to Facebook" in str(exc_info.value)
        assert exc_info.value.platform == "facebook"
    
    @pytest.mark.asyncio
    async def test_publish_post_not_authenticated(self, publisher: FacebookPublisher):
        """Test post publishing without authentication."""
        content = "Test post"
        metadata = {"type": "text"}
        
        with pytest.raises(AuthenticationError) as exc_info:
            await publisher._publish_post(content, metadata)
        
        assert "Not authenticated" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_publish_post_template_substitution(self, publisher: FacebookPublisher, mock_auth):
        """Test post publishing with template variable substitution."""
        # Setup
        await publisher.authenticate()
        
        content = "Check out my video: {youtube_url}"
        metadata = {
            "type": "link",
            "youtube_url": "https://youtube.com/watch?v=abc123"
        }
        
        # Mock API response
        mock_response = {
            "id": "123456789_987654321",
            "post_id": "987654321"
        }
        
        with patch.object(publisher._auth, '_make_api_request', return_value=mock_response) as mock_api:
            await publisher._publish_post(content, metadata)
        
        # Verify that the API was called with substituted content
        call_args = mock_api.call_args
        assert "Check out my video: https://youtube.com/watch?v=abc123" in str(call_args)
    
    @pytest.mark.asyncio
    async def test_publish_post_template_error(self, publisher: FacebookPublisher, mock_auth):
        """Test post publishing with template substitution error."""
        # Setup
        await publisher.authenticate()
        
        content = "Check out my video: {missing_variable}"
        metadata = {"type": "text"}
        
        with pytest.raises(TemplateError) as exc_info:
            await publisher._publish_post(content, metadata)
        
        assert "Missing template variable: missing_variable" in str(exc_info.value)
    
    def test_format_post_data_text_post(self, publisher: FacebookPublisher):
        """Test formatting post data for text post."""
        content = "This is a text post"
        metadata = {"type": "text"}
        
        post_data = publisher._format_post_data(content, metadata)
        
        assert post_data["message"] == content
        assert "link" not in post_data
        assert "name" not in post_data
    
    def test_format_post_data_link_post(self, publisher: FacebookPublisher):
        """Test formatting post data for link post."""
        content = "Check out this link"
        metadata = {
            "type": "link",
            "link": "https://example.com",
            "name": "Example Title",
            "description": "Example description"
        }
        
        post_data = publisher._format_post_data(content, metadata)
        
        assert post_data["message"] == content
        assert post_data["link"] == "https://example.com"
        assert post_data["name"] == "Example Title"
        assert post_data["description"] == "Example description"
    
    def test_format_post_data_scheduled_post(self, publisher: FacebookPublisher):
        """Test formatting post data for scheduled post."""
        content = "Scheduled post"
        future_time = int(datetime.now(timezone.utc).timestamp()) + 3600
        metadata = {
            "type": "text",
            "scheduled_publish_time": future_time
        }
        
        post_data = publisher._format_post_data(content, metadata)
        
        assert post_data["message"] == content
        assert post_data["scheduled_publish_time"] == future_time
        assert post_data["published"] == "false"
    
    def test_extract_post_id_from_response(self, publisher: FacebookPublisher):
        """Test extracting post ID from Facebook API response."""
        response = {
            "id": "123456789_987654321",
            "post_id": "987654321"
        }
        
        post_id = publisher._extract_post_id(response)
        assert post_id == "987654321"
    
    def test_extract_post_id_from_response_fallback(self, publisher: FacebookPublisher):
        """Test extracting post ID from response using fallback method."""
        response = {
            "id": "123456789_987654321"
            # No explicit post_id field
        }
        
        post_id = publisher._extract_post_id(response)
        assert post_id == "987654321"  # Extracted from compound ID
    
    def test_extract_post_id_invalid_response(self, publisher: FacebookPublisher):
        """Test extracting post ID from invalid response."""
        response = {}
        
        with pytest.raises(PublishError) as exc_info:
            publisher._extract_post_id(response)
        
        assert "Invalid response format" in str(exc_info.value)
    
    def test_build_post_url(self, publisher: FacebookPublisher):
        """Test building post URL from page ID and post ID."""
        publisher.config.credentials["page_id"] = "123456789"
        post_id = "987654321"
        
        url = publisher._build_post_url(post_id)
        assert url == "https://facebook.com/123456789/posts/987654321"
    
    @pytest.mark.asyncio
    async def test_cleanup(self, publisher: FacebookPublisher):
        """Test cleanup method."""
        # Should not raise any exceptions
        await publisher.cleanup()
    
    def test_health_check_not_authenticated(self, publisher: FacebookPublisher):
        """Test health check when not authenticated."""
        result = publisher.health_check()
        assert result is False
    
    def test_health_check_authenticated(self, publisher: FacebookPublisher, mock_auth):
        """Test health check when authenticated."""
        publisher._auth = mock_auth
        mock_auth.test_connection.return_value = True
        
        result = publisher.health_check()
        assert result is True
    
    def test_health_check_connection_failure(self, publisher: FacebookPublisher, mock_auth):
        """Test health check with connection failure."""
        publisher._auth = mock_auth
        mock_auth.test_connection.return_value = False
        
        result = publisher.health_check()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_context_manager(self, publisher: FacebookPublisher, mock_auth):
        """Test using FacebookPublisher as async context manager."""
        async with publisher as pub:
            assert pub is publisher
            assert pub._auth is not None  # Should be authenticated
    
    @pytest.mark.asyncio
    async def test_context_manager_cleanup_on_exception(self, publisher: FacebookPublisher, mock_auth):
        """Test context manager cleanup when exception occurs."""
        cleanup_called = False
        
        async def mock_cleanup():
            nonlocal cleanup_called
            cleanup_called = True
        
        publisher.cleanup = mock_cleanup
        
        try:
            async with publisher:
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        assert cleanup_called is True
    
    def test_repr(self, publisher: FacebookPublisher):
        """Test string representation of FacebookPublisher."""
        repr_str = repr(publisher)
        assert "FacebookPublisher" in repr_str
        assert "facebook" in repr_str


class TestFacebookPublisherIntegration:
    """Integration tests for FacebookPublisher with realistic scenarios."""
    
    @pytest.fixture
    def publisher_config(self) -> Dict[str, Any]:
        """Provide realistic Facebook configuration."""
        return {
            "page_id": "123456789012345",
            "access_token": "EAABwzLixnjYBO1234567890abcdef",
            "app_id": "1234567890123456",
            "app_secret": "abcdef1234567890abcdef1234567890",
            "api_version": "v19.0"
        }
    
    @pytest.fixture
    def platform_config(self, publisher_config: Dict[str, Any]) -> PlatformConfig:
        """Provide PlatformConfig for integration tests."""
        return PlatformConfig(platform_name="facebook", credentials=publisher_config)
    
    @pytest.mark.asyncio
    async def test_complete_workflow_text_post(self, platform_config: PlatformConfig):
        """Test complete workflow for text post publishing."""
        publisher = FacebookPublisher(config=platform_config)
        
        with patch('medusa.publishers.facebook.FacebookAuth') as mock_auth_class:
            # Setup mock auth
            mock_auth = Mock()
            mock_auth.test_connection.return_value = True
            mock_auth.check_permissions.return_value = True
            mock_auth.verify_page_access.return_value = True
            mock_auth._make_api_request.return_value = {
                "id": "123456789_987654321",
                "post_id": "987654321"
            }
            mock_auth_class.return_value = mock_auth
            
            # Test complete workflow
            content = "This is a complete workflow test post!"
            metadata = {"type": "text"}
            
            result = await publisher.publish_post(content, metadata)
            
            assert result.success is True
            assert result.platform == "facebook"
            assert result.post_id == "987654321"
            assert "facebook.com" in result.post_url
    
    @pytest.mark.asyncio
    async def test_complete_workflow_link_post_with_template(self, platform_config: PlatformConfig):
        """Test complete workflow for link post with template substitution."""
        publisher = FacebookPublisher(config=platform_config)
        
        with patch('medusa.publishers.facebook.FacebookAuth') as mock_auth_class:
            # Setup mock auth
            mock_auth = Mock()
            mock_auth.test_connection.return_value = True
            mock_auth.check_permissions.return_value = True
            mock_auth.verify_page_access.return_value = True
            mock_auth._make_api_request.return_value = {
                "id": "123456789_987654321",
                "post_id": "987654321"
            }
            mock_auth_class.return_value = mock_auth
            
            # Test with template variables
            content = "Check out my new video: {youtube_url} #video #content"
            metadata = {
                "type": "link",
                "youtube_url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
                "link": "https://youtube.com/watch?v=dQw4w9WgXcQ",
                "name": "Amazing Video Title",
                "description": "This is an amazing video you should watch"
            }
            
            result = await publisher.publish_post(content, metadata)
            
            assert result.success is True
            assert result.metadata["link"] == "https://youtube.com/watch?v=dQw4w9WgXcQ"
            
            # Verify API was called with substituted content
            api_calls = mock_auth._make_api_request.call_args_list
            assert len(api_calls) == 1
            call_data = api_calls[0][1]["data"]  # Get the data parameter
            assert "https://youtube.com/watch?v=dQw4w9WgXcQ" in call_data["message"] 