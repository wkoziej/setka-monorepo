"""
Tests for BaseUploader abstract class.
Comprehensive test coverage for base uploader functionality and interface compliance.
"""

import pytest
import asyncio
from abc import ABC
from unittest.mock import patch
from typing import Optional, Callable

from medusa.uploaders.base import BaseUploader, UploadProgress, UploadResult
from medusa.models import MediaMetadata, PlatformConfig
from medusa.exceptions import (
    UploadError,
    AuthenticationError,
    ValidationError,
    RateLimitError,
    NetworkError,
)


class TestUploadProgress:
    """Test UploadProgress data class."""

    def test_upload_progress_creation(self):
        """Test creating UploadProgress with valid data."""
        progress = UploadProgress(
            bytes_uploaded=1000, total_bytes=5000, status="uploading"
        )

        assert progress.bytes_uploaded == 1000
        assert progress.total_bytes == 5000
        assert progress.percentage == 20.0
        assert progress.status == "uploading"

    def test_upload_progress_defaults(self):
        """Test UploadProgress with default values."""
        progress = UploadProgress(bytes_uploaded=500, total_bytes=1000)

        assert progress.bytes_uploaded == 500
        assert progress.total_bytes == 1000
        assert progress.percentage == 50.0
        assert progress.status == "uploading"

    def test_upload_progress_validation(self):
        """Test UploadProgress validation."""
        # Test negative bytes
        with pytest.raises(ValidationError, match="bytes_uploaded cannot be negative"):
            UploadProgress(bytes_uploaded=-1, total_bytes=1000)

        # Test negative total
        with pytest.raises(ValidationError, match="total_bytes must be positive"):
            UploadProgress(bytes_uploaded=500, total_bytes=-1)

        # Test bytes > total
        with pytest.raises(
            ValidationError, match="bytes_uploaded cannot exceed total_bytes"
        ):
            UploadProgress(bytes_uploaded=1500, total_bytes=1000)

    def test_upload_progress_percentage_calculation(self):
        """Test automatic percentage calculation."""
        progress = UploadProgress(bytes_uploaded=750, total_bytes=1000)
        assert progress.percentage == 75.0

        # Test zero total bytes
        progress = UploadProgress(bytes_uploaded=0, total_bytes=0)
        assert progress.percentage == 0.0


class TestUploadResult:
    """Test UploadResult data class."""

    def test_upload_result_creation(self):
        """Test creating UploadResult with valid data."""
        result = UploadResult(
            platform="youtube",
            upload_id="test_upload_123",
            media_url="https://youtube.com/watch?v=abc123",
            metadata={"title": "Test Video"},
        )

        assert result.platform == "youtube"
        assert result.upload_id == "test_upload_123"
        assert result.media_url == "https://youtube.com/watch?v=abc123"
        assert result.metadata["title"] == "Test Video"
        assert result.success is True
        assert result.error is None

    def test_upload_result_failed(self):
        """Test creating failed UploadResult."""
        result = UploadResult(
            platform="youtube",
            upload_id="test_upload_123",
            success=False,
            error="Upload failed",
        )

        assert result.success is False
        assert result.error == "Upload failed"
        assert result.media_url is None

    def test_upload_result_validation(self):
        """Test UploadResult validation."""
        # Test empty platform
        with pytest.raises(ValidationError, match="Platform name cannot be empty"):
            UploadResult(platform="", upload_id="test")

        # Test failed result without error
        with pytest.raises(
            ValidationError, match="Failed uploads must have error information"
        ):
            UploadResult(platform="youtube", upload_id="test", success=False)


class ConcreteUploader(BaseUploader):
    """Concrete implementation of BaseUploader for testing."""

    def __init__(
        self, platform_name: str = "test", config: Optional[PlatformConfig] = None
    ):
        super().__init__(platform_name, config)
        self.authenticate_called = False
        self.upload_called = False
        self.validate_called = False
        self.cleanup_called = False
        self.should_fail_auth = False
        self.should_fail_upload = False
        self.should_fail_validation = False
        self.upload_delay = 0.1
        self.progress_callback_calls = []

    async def authenticate(self) -> bool:
        """Mock authentication."""
        self.authenticate_called = True
        if self.should_fail_auth:
            raise AuthenticationError(
                "Authentication failed", platform=self.platform_name
            )
        self.is_authenticated = True
        return True

    async def _upload_media(
        self,
        file_path: str,
        metadata: MediaMetadata,
        progress_callback: Optional[Callable[[UploadProgress], None]] = None,
    ) -> UploadResult:
        """Mock media upload."""
        self.upload_called = True

        if self.should_fail_upload:
            raise UploadError("Upload failed", platform=self.platform_name)

        # Simulate progress updates
        if progress_callback:
            for i in range(0, 101, 25):
                progress = UploadProgress(
                    bytes_uploaded=i * 10,
                    total_bytes=1000,
                    status="uploading" if i < 100 else "completed",
                )
                self.progress_callback_calls.append(progress)
                progress_callback(progress)
                await asyncio.sleep(0.01)

        await asyncio.sleep(self.upload_delay)

        return UploadResult(
            platform=self.platform_name,
            upload_id="test_upload_123",
            media_url="https://test.com/media/123",
            metadata=metadata.to_dict(),
        )

    def _validate_metadata(self, metadata: MediaMetadata) -> None:
        """Mock metadata validation."""
        self.validate_called = True
        if self.should_fail_validation:
            raise ValidationError("Invalid metadata", platform=self.platform_name)

    async def cleanup(self) -> None:
        """Mock cleanup."""
        self.cleanup_called = True


class TestBaseUploader:
    """Test BaseUploader abstract class functionality."""

    def test_base_uploader_is_abstract(self):
        """Test that BaseUploader is properly abstract."""
        assert issubclass(BaseUploader, ABC)

        # Should not be able to instantiate directly
        with pytest.raises(TypeError):
            BaseUploader("test")

    def test_concrete_uploader_creation(self):
        """Test creating concrete uploader instance."""
        config = PlatformConfig(platform_name="test")
        uploader = ConcreteUploader("test", config)

        assert uploader.platform_name == "test"
        assert uploader.config == config
        assert uploader.is_authenticated is False
        assert uploader.retry_attempts == 3
        assert uploader.timeout == 30

    def test_uploader_with_custom_config(self):
        """Test uploader with custom configuration."""
        config = PlatformConfig(platform_name="test", retry_attempts=5, timeout=60)
        uploader = ConcreteUploader("test", config)

        assert uploader.retry_attempts == 5
        assert uploader.timeout == 60

    @pytest.mark.asyncio
    async def test_authenticate_success(self):
        """Test successful authentication."""
        uploader = ConcreteUploader()

        result = await uploader.authenticate()

        assert result is True
        assert uploader.is_authenticated is True
        assert uploader.authenticate_called is True

    @pytest.mark.asyncio
    async def test_authenticate_failure(self):
        """Test authentication failure."""
        uploader = ConcreteUploader()
        uploader.should_fail_auth = True

        with pytest.raises(AuthenticationError):
            await uploader.authenticate()

        assert uploader.is_authenticated is False

    @pytest.mark.asyncio
    async def test_upload_media_success(self):
        """Test successful media upload."""
        uploader = ConcreteUploader()
        metadata = MediaMetadata(title="Test Video", description="Test Description")
        progress_calls = []

        def progress_callback(progress: UploadProgress):
            progress_calls.append(progress)

        await uploader.authenticate()
        result = await uploader.upload_media(
            file_path="test_video.mp4",
            metadata=metadata,
            progress_callback=progress_callback,
        )

        assert isinstance(result, UploadResult)
        assert result.success is True
        assert result.platform == "test"
        assert result.upload_id == "test_upload_123"
        assert result.media_url == "https://test.com/media/123"
        assert uploader.upload_called is True
        assert uploader.validate_called is True
        assert len(progress_calls) > 0

    @pytest.mark.asyncio
    async def test_upload_media_authentication_required(self):
        """Test upload requires authentication."""
        uploader = ConcreteUploader()
        metadata = MediaMetadata(title="Test Video")

        # Should fail without authentication
        with pytest.raises(AuthenticationError, match="Authentication required"):
            await uploader.upload_media("test_video.mp4", metadata)

    @pytest.mark.asyncio
    async def test_upload_media_with_validation_error(self):
        """Test upload with metadata validation error."""
        uploader = ConcreteUploader()
        uploader.should_fail_validation = True
        metadata = MediaMetadata(title="Invalid Video")

        await uploader.authenticate()

        with pytest.raises(ValidationError):
            await uploader.upload_media("test_video.mp4", metadata)

    @pytest.mark.asyncio
    async def test_upload_media_with_upload_error(self):
        """Test upload with upload error."""
        uploader = ConcreteUploader()
        uploader.should_fail_upload = True
        metadata = MediaMetadata(title="Test Video")

        await uploader.authenticate()

        with pytest.raises(UploadError):
            await uploader.upload_media("test_video.mp4", metadata)

    @pytest.mark.asyncio
    async def test_upload_with_retry_logic(self):
        """Test upload retry logic on transient failures."""
        uploader = ConcreteUploader()
        uploader.retry_attempts = 2
        metadata = MediaMetadata(title="Test Video")

        await uploader.authenticate()

        # Mock network error that should trigger retry
        with patch.object(uploader, "_upload_media") as mock_upload:
            mock_upload.side_effect = [
                NetworkError("Network timeout", platform="test"),
                UploadResult(
                    platform="test", upload_id="123", media_url="https://test.com/123"
                ),
            ]

            result = await uploader.upload_media("test_video.mp4", metadata)

            assert result.success is True
            assert mock_upload.call_count == 2

    @pytest.mark.asyncio
    async def test_upload_retry_exhausted(self):
        """Test upload when all retries are exhausted."""
        uploader = ConcreteUploader()
        uploader.retry_attempts = 2
        metadata = MediaMetadata(title="Test Video")

        await uploader.authenticate()

        with patch.object(uploader, "_upload_media") as mock_upload:
            mock_upload.side_effect = NetworkError(
                "Persistent network error", platform="test"
            )

            with pytest.raises(NetworkError):
                await uploader.upload_media("test_video.mp4", metadata)

            assert mock_upload.call_count == 3  # Initial + 2 retries

    @pytest.mark.asyncio
    async def test_upload_no_retry_on_auth_error(self):
        """Test that authentication errors are not retried."""
        uploader = ConcreteUploader()
        metadata = MediaMetadata(title="Test Video")

        await uploader.authenticate()

        with patch.object(uploader, "_upload_media") as mock_upload:
            mock_upload.side_effect = AuthenticationError(
                "Token expired", platform="test"
            )

            with pytest.raises(AuthenticationError):
                await uploader.upload_media("test_video.mp4", metadata)

            assert mock_upload.call_count == 1  # No retries for auth errors

    @pytest.mark.asyncio
    async def test_upload_no_retry_on_validation_error(self):
        """Test that validation errors are not retried."""
        uploader = ConcreteUploader()
        metadata = MediaMetadata(title="Test Video")

        await uploader.authenticate()

        with patch.object(uploader, "_upload_media") as mock_upload:
            mock_upload.side_effect = ValidationError(
                "Invalid file format", platform="test"
            )

            with pytest.raises(ValidationError):
                await uploader.upload_media("test_video.mp4", metadata)

            assert mock_upload.call_count == 1  # No retries for validation errors

    @pytest.mark.asyncio
    async def test_progress_reporting(self):
        """Test progress reporting during upload."""
        uploader = ConcreteUploader()
        metadata = MediaMetadata(title="Test Video")
        progress_updates = []

        def progress_callback(progress: UploadProgress):
            progress_updates.append(progress)

        await uploader.authenticate()
        await uploader.upload_media("test_video.mp4", metadata, progress_callback)

        assert len(progress_updates) > 0
        assert all(isinstance(p, UploadProgress) for p in progress_updates)
        assert progress_updates[0].percentage == 0.0
        assert progress_updates[-1].percentage == 100.0

    @pytest.mark.asyncio
    async def test_cleanup_called(self):
        """Test that cleanup is called."""
        uploader = ConcreteUploader()

        await uploader.cleanup()

        assert uploader.cleanup_called is True

    def test_is_retryable_error(self):
        """Test error retry classification."""
        uploader = ConcreteUploader()

        # Retryable errors
        assert uploader._is_retryable_error(NetworkError("Timeout", platform="test"))
        assert uploader._is_retryable_error(
            RateLimitError("Rate limited", platform="test")
        )

        # Non-retryable errors
        assert not uploader._is_retryable_error(
            AuthenticationError("Auth failed", platform="test")
        )
        assert not uploader._is_retryable_error(
            ValidationError("Invalid data", platform="test")
        )
        # Generic exceptions are not retryable by default in our implementation
        assert not uploader._is_retryable_error(ValueError("Generic error"))

    @pytest.mark.asyncio
    async def test_upload_with_timeout(self):
        """Test upload with timeout."""
        uploader = ConcreteUploader()
        uploader.timeout = 0.05  # Very short timeout
        uploader.upload_delay = 0.1  # Longer than timeout
        metadata = MediaMetadata(title="Test Video")

        await uploader.authenticate()

        with pytest.raises(asyncio.TimeoutError):
            await uploader.upload_media("test_video.mp4", metadata)

    def test_abstract_methods_defined(self):
        """Test that all abstract methods are properly defined."""
        # These should be abstract methods
        abstract_methods = BaseUploader.__abstractmethods__

        expected_methods = {"authenticate", "_upload_media", "_validate_metadata"}
        assert abstract_methods == expected_methods

    def test_platform_name_validation(self):
        """Test platform name validation."""
        # Valid platform name
        uploader = ConcreteUploader("youtube")
        assert uploader.platform_name == "youtube"

        # Empty platform name should raise error
        with pytest.raises(ValidationError, match="Platform name cannot be empty"):
            ConcreteUploader("")

    @pytest.mark.asyncio
    async def test_context_manager_support(self):
        """Test that uploader supports async context manager."""
        uploader = ConcreteUploader()

        async with uploader:
            assert uploader.authenticate_called is True

        assert uploader.cleanup_called is True

    @pytest.mark.asyncio
    async def test_context_manager_cleanup_on_exception(self):
        """Test cleanup is called even when exception occurs."""
        uploader = ConcreteUploader()

        try:
            async with uploader:
                raise ValueError("Test error")
        except ValueError:
            pass

        assert uploader.cleanup_called is True


class TestBaseUploaderIntegration:
    """Integration tests for BaseUploader functionality."""

    @pytest.mark.asyncio
    async def test_full_upload_workflow(self):
        """Test complete upload workflow."""
        uploader = ConcreteUploader()
        metadata = MediaMetadata(
            title="Integration Test Video",
            description="Test description",
            tags=["test", "integration"],
            privacy="unlisted",
        )
        progress_updates = []

        def progress_callback(progress: UploadProgress):
            progress_updates.append(progress)

        # Full workflow
        await uploader.authenticate()
        result = await uploader.upload_media(
            "test_video.mp4", metadata, progress_callback
        )
        await uploader.cleanup()

        # Verify all steps completed
        assert uploader.authenticate_called
        assert uploader.upload_called
        assert uploader.validate_called
        assert uploader.cleanup_called
        assert result.success
        assert len(progress_updates) > 0

    @pytest.mark.asyncio
    async def test_concurrent_uploads(self):
        """Test handling concurrent uploads."""
        uploader = ConcreteUploader()
        metadata = MediaMetadata(title="Concurrent Test")

        await uploader.authenticate()

        # Start multiple uploads concurrently
        tasks = [uploader.upload_media(f"video_{i}.mp4", metadata) for i in range(3)]

        results = await asyncio.gather(*tasks)

        assert len(results) == 3
        assert all(result.success for result in results)
        assert all(isinstance(result, UploadResult) for result in results)
