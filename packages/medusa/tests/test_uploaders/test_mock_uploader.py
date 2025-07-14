"""
Tests for MockUploader implementation.
Tests configurable success/failure scenarios and realistic behavior simulation.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from medusa.uploaders.mock import MockUploader, MockConfig
from medusa.uploaders.base import UploadProgress, UploadResult
from medusa.models import MediaMetadata, PlatformConfig
from medusa.exceptions import (
    UploadError,
    AuthenticationError,
    ValidationError,
    NetworkError,
    RateLimitError
)


class TestMockConfig:
    """Test MockConfig configuration class."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = MockConfig()
        
        assert config.auth_success is True
        assert config.upload_success is True
        assert config.upload_delay == 0.1
        assert config.auth_delay == 0.05
        assert config.simulate_progress is True
        assert config.progress_steps == 5
        assert config.auth_error is None
        assert config.upload_error is None
        assert config.metadata_requirements == []
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = MockConfig(
            auth_success=False,
            upload_success=False,
            upload_delay=2.0,
            auth_delay=1.0,
            simulate_progress=False,
            progress_steps=10,
            auth_error="Custom auth error",
            upload_error="Custom upload error",
            metadata_requirements=["title", "description"]
        )
        
        assert config.auth_success is False
        assert config.upload_success is False
        assert config.upload_delay == 2.0
        assert config.auth_delay == 1.0
        assert config.simulate_progress is False
        assert config.progress_steps == 10
        assert config.auth_error == "Custom auth error"
        assert config.upload_error == "Custom upload error"
        assert config.metadata_requirements == ["title", "description"]


class TestMockUploader:
    """Test MockUploader implementation."""
    
    def test_initialization(self):
        """Test MockUploader initialization."""
        uploader = MockUploader()
        
        assert uploader.platform_name == "mock"
        assert isinstance(uploader.mock_config, MockConfig)
        assert uploader.is_authenticated is False
        assert uploader.call_log == []
    
    def test_initialization_with_config(self):
        """Test MockUploader initialization with custom config."""
        platform_config = PlatformConfig(platform_name="test_mock")
        mock_config = MockConfig(upload_delay=5.0)
        
        uploader = MockUploader(
            platform_name="test_mock",
            config=platform_config,
            mock_config=mock_config
        )
        
        assert uploader.platform_name == "test_mock"
        assert uploader.config == platform_config
        assert uploader.mock_config.upload_delay == 5.0
    
    @pytest.mark.asyncio
    async def test_successful_authentication(self):
        """Test successful authentication."""
        uploader = MockUploader()
        
        result = await uploader.authenticate()
        
        assert result is True
        assert uploader.is_authenticated is True
        assert len(uploader.call_log) == 1
        assert uploader.call_log[0]["method"] == "authenticate"
        assert uploader.call_log[0]["success"] is True
    
    @pytest.mark.asyncio
    async def test_failed_authentication(self):
        """Test failed authentication."""
        mock_config = MockConfig(auth_success=False, auth_error="Auth failed")
        uploader = MockUploader(mock_config=mock_config)
        
        with pytest.raises(AuthenticationError) as exc_info:
            await uploader.authenticate()
        
        assert "Auth failed" in str(exc_info.value)
        assert uploader.is_authenticated is False
        assert len(uploader.call_log) == 1
        assert uploader.call_log[0]["method"] == "authenticate"
        assert uploader.call_log[0]["success"] is False
    
    @pytest.mark.asyncio
    async def test_authentication_delay(self):
        """Test authentication with realistic delay."""
        mock_config = MockConfig(auth_delay=0.2)
        uploader = MockUploader(mock_config=mock_config)
        
        start_time = datetime.now()
        await uploader.authenticate()
        end_time = datetime.now()
        
        duration = (end_time - start_time).total_seconds()
        assert duration >= 0.2
    
    def test_metadata_validation_success(self):
        """Test successful metadata validation."""
        uploader = MockUploader()
        metadata = MediaMetadata(title="Test", description="Test description")
        
        # Should not raise any exception
        uploader._validate_metadata(metadata)
    
    def test_metadata_validation_failure(self):
        """Test metadata validation failure."""
        mock_config = MockConfig(metadata_requirements=["title", "description"])
        uploader = MockUploader(mock_config=mock_config)
        metadata = MediaMetadata(title="Test")  # Missing description
        
        with pytest.raises(ValidationError) as exc_info:
            uploader._validate_metadata(metadata)
        
        assert "description" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_successful_upload(self):
        """Test successful media upload."""
        uploader = MockUploader()
        uploader.is_authenticated = True
        
        metadata = MediaMetadata(title="Test Video")
        result = await uploader._upload_media("/path/to/video.mp4", metadata)
        
        assert isinstance(result, UploadResult)
        assert result.platform == "mock"
        assert result.success is True
        assert result.media_url.startswith("https://mock-platform.com/")
        assert result.upload_id.startswith("mock_upload_")
        assert len(uploader.call_log) == 1
        assert uploader.call_log[0]["method"] == "_upload_media"
    
    @pytest.mark.asyncio
    async def test_failed_upload(self):
        """Test failed media upload."""
        mock_config = MockConfig(upload_success=False, upload_error="Upload failed")
        uploader = MockUploader(mock_config=mock_config)
        uploader.is_authenticated = True
        
        metadata = MediaMetadata(title="Test Video")
        
        with pytest.raises(UploadError) as exc_info:
            await uploader._upload_media("/path/to/video.mp4", metadata)
        
        assert "Upload failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_upload_with_progress_callback(self):
        """Test upload with progress reporting."""
        mock_config = MockConfig(simulate_progress=True, progress_steps=3)
        uploader = MockUploader(mock_config=mock_config)
        uploader.is_authenticated = True
        
        progress_calls = []
        
        def progress_callback(progress: UploadProgress):
            progress_calls.append(progress)
        
        metadata = MediaMetadata(title="Test Video")
        await uploader._upload_media("/path/to/video.mp4", metadata, progress_callback)
        
        # Should have received progress updates
        assert len(progress_calls) >= 3
        assert progress_calls[0].percentage == 0.0
        assert progress_calls[-1].percentage == 100.0
        
        # Progress should be increasing
        for i in range(1, len(progress_calls)):
            assert progress_calls[i].percentage >= progress_calls[i-1].percentage
    
    @pytest.mark.asyncio
    async def test_upload_delay(self):
        """Test upload with realistic delay."""
        mock_config = MockConfig(upload_delay=0.3, simulate_progress=False)
        uploader = MockUploader(mock_config=mock_config)
        uploader.is_authenticated = True
        
        metadata = MediaMetadata(title="Test Video")
        
        start_time = datetime.now()
        await uploader._upload_media("/path/to/video.mp4", metadata)
        end_time = datetime.now()
        
        duration = (end_time - start_time).total_seconds()
        assert duration >= 0.3
    
    @pytest.mark.asyncio
    async def test_network_error_simulation(self):
        """Test network error simulation."""
        mock_config = MockConfig(
            upload_success=False,
            upload_error="Network timeout",
            error_type="network"
        )
        uploader = MockUploader(mock_config=mock_config)
        uploader.is_authenticated = True
        
        metadata = MediaMetadata(title="Test Video")
        
        with pytest.raises(NetworkError):
            await uploader._upload_media("/path/to/video.mp4", metadata)
    
    @pytest.mark.asyncio
    async def test_rate_limit_error_simulation(self):
        """Test rate limit error simulation."""
        mock_config = MockConfig(
            upload_success=False,
            upload_error="Rate limit exceeded",
            error_type="rate_limit"
        )
        uploader = MockUploader(mock_config=mock_config)
        uploader.is_authenticated = True
        
        metadata = MediaMetadata(title="Test Video")
        
        with pytest.raises(RateLimitError):
            await uploader._upload_media("/path/to/video.mp4", metadata)
    
    def test_call_log_tracking(self):
        """Test that all calls are properly logged."""
        uploader = MockUploader()
        
        # Initially empty
        assert uploader.call_log == []
        
        # Clear log
        uploader.clear_call_log()
        assert uploader.call_log == []
    
    @pytest.mark.asyncio
    async def test_full_upload_workflow(self):
        """Test complete upload workflow through public interface."""
        uploader = MockUploader()
        metadata = MediaMetadata(title="Test Video", description="Test description")
        
        # Should fail without authentication
        with pytest.raises(AuthenticationError):
            await uploader.upload_media("/path/to/video.mp4", metadata)
        
        # Authenticate first
        await uploader.authenticate()
        
        # Now upload should work
        result = await uploader.upload_media("/path/to/video.mp4", metadata)
        
        assert result.success is True
        assert result.platform == "mock"
        assert len(uploader.call_log) >= 2  # authenticate + upload
    
    def test_verification_helpers(self):
        """Test verification helper methods."""
        uploader = MockUploader()
        
        # Test was_called
        assert uploader.was_called("authenticate") is False
        
        # Test get_call_count
        assert uploader.get_call_count("authenticate") == 0
        
        # Test get_calls
        assert uploader.get_calls("authenticate") == []
    
    @pytest.mark.asyncio
    async def test_verification_after_calls(self):
        """Test verification helpers after making calls."""
        uploader = MockUploader()
        metadata = MediaMetadata(title="Test")
        
        await uploader.authenticate()
        uploader.is_authenticated = True
        await uploader._upload_media("/path/to/video.mp4", metadata)
        
        # Test verification methods
        assert uploader.was_called("authenticate") is True
        assert uploader.was_called("_upload_media") is True
        assert uploader.was_called("nonexistent") is False
        
        assert uploader.get_call_count("authenticate") == 1
        assert uploader.get_call_count("_upload_media") == 1
        
        auth_calls = uploader.get_calls("authenticate")
        assert len(auth_calls) == 1
        assert auth_calls[0]["method"] == "authenticate"
        
        upload_calls = uploader.get_calls("_upload_media")
        assert len(upload_calls) == 1
        assert upload_calls[0]["file_path"] == "/path/to/video.mp4"
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager functionality."""
        uploader = MockUploader()
        
        async with uploader:
            assert uploader.is_authenticated is True
        
        # Cleanup should have been called
        assert uploader.was_called("cleanup")
    
    @pytest.mark.asyncio
    async def test_context_manager_auth_failure(self):
        """Test context manager with authentication failure."""
        mock_config = MockConfig(auth_success=False, auth_error="Auth failed")
        uploader = MockUploader(mock_config=mock_config)
        
        with pytest.raises(AuthenticationError):
            async with uploader:
                pass 