"""
Tests for YouTubeUploader implementation.
Tests basic video upload functionality with progress tracking and error handling.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from medusa.uploaders.youtube import YouTubeUploader
from medusa.uploaders.base import UploadProgress, UploadResult
from medusa.uploaders.youtube_auth import YouTubeAuth
from medusa.models import MediaMetadata, PlatformConfig
from medusa.exceptions import (
    UploadError,
    AuthenticationError,
    ValidationError,
    RateLimitError,
)


class TestYouTubeUploaderInitialization:
    """Test YouTubeUploader initialization."""

    def test_default_initialization(self):
        """Test default initialization."""
        uploader = YouTubeUploader()

        assert uploader.platform_name == "youtube"
        assert isinstance(uploader.auth_manager, YouTubeAuth)
        assert uploader.is_authenticated is False
        assert uploader.service is None
        assert uploader.retry_attempts == 3
        assert uploader.timeout == 30

    def test_initialization_with_config(self):
        """Test initialization with custom configuration."""
        config = PlatformConfig(
            platform_name="youtube",
            credentials={
                "client_secrets_file": "test_secrets.json",
                "credentials_file": "test_credentials.json",
            },
            retry_attempts=5,
            timeout=60,
        )

        uploader = YouTubeUploader(config=config)

        assert uploader.platform_name == "youtube"
        assert uploader.config == config
        assert uploader.retry_attempts == 5
        assert uploader.timeout == 60
        assert uploader.auth_manager.config == config

    def test_initialization_with_custom_platform_name(self):
        """Test initialization with custom platform name."""
        uploader = YouTubeUploader(platform_name="test_youtube")

        assert uploader.platform_name == "test_youtube"


class TestYouTubeUploaderAuthentication:
    """Test YouTubeUploader authentication."""

    @pytest.mark.asyncio
    async def test_successful_authentication(self):
        """Test successful authentication."""
        uploader = YouTubeUploader()

        with (
            patch.object(
                uploader.auth_manager, "authenticate", return_value=True
            ) as mock_auth,
            patch("medusa.uploaders.youtube.build") as mock_build,
        ):
            mock_service = MagicMock()
            mock_build.return_value = mock_service

            result = await uploader.authenticate()

            assert result is True
            assert uploader.is_authenticated is True
            assert uploader.service == mock_service
            mock_auth.assert_called_once()
            mock_build.assert_called_once_with(
                "youtube", "v3", credentials=uploader.auth_manager.credentials
            )

    @pytest.mark.asyncio
    async def test_failed_authentication(self):
        """Test failed authentication."""
        uploader = YouTubeUploader()

        with patch.object(
            uploader.auth_manager, "authenticate", return_value=False
        ) as mock_auth:
            result = await uploader.authenticate()

            assert result is False
            assert uploader.is_authenticated is False
            assert uploader.service is None
            mock_auth.assert_called_once()

    @pytest.mark.asyncio
    async def test_authentication_exception(self):
        """Test authentication with exception."""
        uploader = YouTubeUploader()

        auth_error = AuthenticationError("OAuth failed", platform="youtube")
        with patch.object(
            uploader.auth_manager, "authenticate", side_effect=auth_error
        ):
            with pytest.raises(AuthenticationError):
                await uploader.authenticate()

            assert uploader.is_authenticated is False
            assert uploader.service is None


class TestYouTubeUploaderMetadataValidation:
    """Test metadata validation for YouTube requirements."""

    def test_valid_metadata(self):
        """Test validation of valid metadata."""
        uploader = YouTubeUploader()
        metadata = MediaMetadata(
            title="Test Video",
            description="Test description",
            tags=["test", "video"],
            privacy="public",
        )

        # Should not raise any exception
        uploader._validate_metadata(metadata)

    def test_missing_title(self):
        """Test validation with missing title."""
        uploader = YouTubeUploader()
        metadata = MediaMetadata(description="Test description")

        with pytest.raises(ValidationError) as exc_info:
            uploader._validate_metadata(metadata)

        assert "title" in str(exc_info.value).lower()

    def test_empty_title(self):
        """Test validation with empty title."""
        uploader = YouTubeUploader()
        metadata = MediaMetadata(title="", description="Test description")

        with pytest.raises(ValidationError) as exc_info:
            uploader._validate_metadata(metadata)

        assert "title" in str(exc_info.value).lower()

    def test_title_too_long(self):
        """Test validation with title too long."""
        uploader = YouTubeUploader()
        long_title = "x" * 101  # YouTube limit is 100 characters
        metadata = MediaMetadata(title=long_title, description="Test description")

        with pytest.raises(ValidationError) as exc_info:
            uploader._validate_metadata(metadata)

        assert "title" in str(exc_info.value).lower()
        assert "100" in str(exc_info.value)

    def test_description_too_long(self):
        """Test validation with description too long."""
        uploader = YouTubeUploader()
        long_description = "x" * 5001  # YouTube limit is 5000 characters
        metadata = MediaMetadata(title="Test", description=long_description)

        with pytest.raises(ValidationError) as exc_info:
            uploader._validate_metadata(metadata)

        assert "description" in str(exc_info.value).lower()
        assert "5000" in str(exc_info.value)

    def test_too_many_tags(self):
        """Test validation with too many tags."""
        uploader = YouTubeUploader()
        too_many_tags = [f"tag{i}" for i in range(51)]  # YouTube limit is 50
        metadata = MediaMetadata(title="Test", tags=too_many_tags)

        with pytest.raises(ValidationError) as exc_info:
            uploader._validate_metadata(metadata)

        assert "tags" in str(exc_info.value).lower()
        assert "50" in str(exc_info.value)

    def test_invalid_privacy_setting(self):
        """Test validation with invalid privacy setting."""
        uploader = YouTubeUploader()
        metadata = MediaMetadata(title="Test", privacy="invalid")

        with pytest.raises(ValidationError) as exc_info:
            uploader._validate_metadata(metadata)

        assert "privacy" in str(exc_info.value).lower()

    def test_tags_total_length_validation(self):
        """Test validation of total tags length."""
        uploader = YouTubeUploader()
        # Create tags that exceed 500 character limit
        long_tags = ["verylongtagname" * 10 for _ in range(10)]  # Each ~150 chars
        metadata = MediaMetadata(title="Test", tags=long_tags)

        with pytest.raises(ValidationError) as exc_info:
            uploader._validate_metadata(metadata)

        assert "tags" in str(exc_info.value).lower()
        assert "500" in str(exc_info.value)

    def test_scheduled_publish_validation(self):
        """Test validation of scheduled publishing."""
        uploader = YouTubeUploader()

        # Valid scheduled time (future)
        future_time = datetime.now(timezone.utc).replace(microsecond=0)
        metadata = MediaMetadata(
            title="Test", privacy="private", scheduled_publish_time=future_time
        )
        uploader._validate_metadata(metadata)

        # Invalid: scheduled time with non-private privacy
        metadata = MediaMetadata(
            title="Test", privacy="public", scheduled_publish_time=future_time
        )
        with pytest.raises(ValidationError) as exc_info:
            uploader._validate_metadata(metadata)

        assert "scheduled" in str(exc_info.value).lower()
        assert "private" in str(exc_info.value).lower()

    def test_category_validation(self):
        """Test validation of video category."""
        uploader = YouTubeUploader()

        # Valid category
        metadata = MediaMetadata(title="Test", category="education")
        uploader._validate_metadata(metadata)

        # Invalid category
        metadata = MediaMetadata(title="Test", category="invalid_category")
        with pytest.raises(ValidationError) as exc_info:
            uploader._validate_metadata(metadata)

        assert "category" in str(exc_info.value).lower()

    def test_language_validation(self):
        """Test validation of language codes."""
        uploader = YouTubeUploader()

        # Valid language codes
        metadata = MediaMetadata(
            title="Test", default_language="en", default_audio_language="en-US"
        )
        uploader._validate_metadata(metadata)

        # Invalid language code format
        metadata = MediaMetadata(title="Test", default_language="invalid-lang-code")
        with pytest.raises(ValidationError) as exc_info:
            uploader._validate_metadata(metadata)

        assert "language" in str(exc_info.value).lower()


class TestYouTubeUploaderMetadataEnhancement:
    """Test enhanced metadata handling features."""

    def test_sanitize_metadata(self):
        """Test metadata sanitization."""
        uploader = YouTubeUploader()

        # Test with special characters and encoding issues
        metadata = MediaMetadata(
            title="Test Video with émojis 🎥 & special chars <script>",
            description="Description with\x00null chars and\ttabs\nand newlines",
            tags=["tag with spaces", "tag-with-dashes", "tag_with_underscores"],
        )

        sanitized = uploader._sanitize_metadata(metadata)

        # Title should be cleaned but preserve basic special chars
        assert "🎥" in sanitized.title
        assert "<script>" not in sanitized.title

        # Description should preserve newlines but remove null chars
        assert "\x00" not in sanitized.description
        assert "\n" in sanitized.description

        # Tags should be properly formatted
        assert all(isinstance(tag, str) for tag in sanitized.tags)

    def test_metadata_conversion_with_all_fields(self):
        """Test comprehensive metadata conversion."""
        uploader = YouTubeUploader()

        metadata = MediaMetadata(
            title="Complete Test Video",
            description="Full description with details",
            tags=["test", "video", "complete"],
            privacy="unlisted",
            category="education",
            default_language="en",
            default_audio_language="en-US",
            scheduled_publish_time=datetime(
                2024, 12, 31, 12, 0, 0, tzinfo=timezone.utc
            ),
            made_for_kids=False,
            embeddable=True,
            public_stats_viewable=True,
            license_type="youtube",
        )

        youtube_metadata = uploader._convert_metadata_to_youtube_format(metadata)

        # Check snippet
        assert youtube_metadata["snippet"]["title"] == "Complete Test Video"
        assert (
            youtube_metadata["snippet"]["description"]
            == "Full description with details"
        )
        assert youtube_metadata["snippet"]["tags"] == ["test", "video", "complete"]
        assert youtube_metadata["snippet"]["categoryId"] == "27"  # Education
        assert youtube_metadata["snippet"]["defaultLanguage"] == "en"
        assert youtube_metadata["snippet"]["defaultAudioLanguage"] == "en-US"

        # Check status
        assert youtube_metadata["status"]["privacyStatus"] == "unlisted"
        assert youtube_metadata["status"]["publishAt"] == "2024-12-31T12:00:00Z"
        assert youtube_metadata["status"]["madeForKids"] == False
        assert youtube_metadata["status"]["embeddable"] == True
        assert youtube_metadata["status"]["publicStatsViewable"] == True
        assert youtube_metadata["status"]["license"] == "youtube"

    def test_thumbnail_upload_validation(self):
        """Test thumbnail upload validation."""
        uploader = YouTubeUploader()

        # Valid thumbnail path
        mock_image = MagicMock()
        mock_image.format = "JPEG"
        mock_image.size = (1920, 1080)  # Valid resolution
        mock_image.__enter__ = MagicMock(return_value=mock_image)
        mock_image.__exit__ = MagicMock(return_value=None)

        with (
            patch("os.path.exists", return_value=True),
            patch("os.path.getsize", return_value=2 * 1024 * 1024),
            patch("PIL.Image.open", return_value=mock_image),
        ):
            uploader._validate_thumbnail_file("/path/to/thumbnail.jpg")

        # Non-existent thumbnail
        with patch("os.path.exists", return_value=False):
            with pytest.raises(ValidationError) as exc_info:
                uploader._validate_thumbnail_file("/path/to/missing.jpg")
            assert "thumbnail" in str(exc_info.value).lower()
            assert "not found" in str(exc_info.value).lower()

        # Thumbnail too large
        with (
            patch("os.path.exists", return_value=True),
            patch("os.path.getsize", return_value=3 * 1024 * 1024),
        ):  # 3MB
            with pytest.raises(ValidationError) as exc_info:
                uploader._validate_thumbnail_file("/path/to/large.jpg")
            assert "thumbnail" in str(exc_info.value).lower()
            assert "2097152 bytes" in str(exc_info.value)

        # Invalid format
        mock_invalid_image = MagicMock()
        mock_invalid_image.format = "BMP"  # Unsupported format
        mock_invalid_image.size = (1920, 1080)
        mock_invalid_image.__enter__ = MagicMock(return_value=mock_invalid_image)
        mock_invalid_image.__exit__ = MagicMock(return_value=None)

        with (
            patch("os.path.exists", return_value=True),
            patch("os.path.getsize", return_value=1 * 1024 * 1024),
            patch("PIL.Image.open", return_value=mock_invalid_image),
        ):
            with pytest.raises(ValidationError) as exc_info:
                uploader._validate_thumbnail_file("/path/to/image.gif")
            assert "thumbnail" in str(exc_info.value).lower()
            assert "format" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_upload_thumbnail(self):
        """Test thumbnail upload functionality."""
        uploader = YouTubeUploader()
        uploader.service = MagicMock()

        # Mock successful thumbnail upload
        mock_request = MagicMock()
        mock_request.execute.return_value = {
            "items": [{"default": {"url": "https://example.com/thumb.jpg"}}]
        }
        uploader.service.thumbnails().set.return_value = mock_request

        with (
            patch.object(uploader, "_validate_thumbnail_file"),
            patch("medusa.uploaders.youtube.MediaFileUpload") as mock_media,
        ):
            mock_media.return_value = MagicMock()

            result = await uploader.upload_thumbnail("video123", "/path/to/thumb.jpg")

            assert result is True
            uploader.service.thumbnails().set.assert_called_once()
            mock_request.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_with_thumbnail(self):
        """Test video upload with thumbnail."""
        uploader = YouTubeUploader()
        uploader.is_authenticated = True
        uploader.service = MagicMock()

        metadata = MediaMetadata(
            title="Test with Thumbnail",
            description="Test description",
            thumbnail_path="/path/to/thumb.jpg",
        )

        # Mock video upload
        mock_video_response = {"id": "video123"}

        # Mock thumbnail upload
        mock_thumb_success = True

        # Mock video upload response
        mock_response = {
            "id": "video123",
            "snippet": {
                "title": "Test with Thumbnail",
                "description": "Test description",
            },
            "status": {"privacyStatus": "unlisted"},
        }

        mock_insert_request = MagicMock()
        mock_insert_request.next_chunk.return_value = (None, mock_response)
        uploader.service.videos().insert.return_value = mock_insert_request

        with (
            patch.object(uploader, "_validate_file"),
            patch("medusa.uploaders.youtube.MediaFileUpload"),
            patch("os.path.getsize", return_value=1024 * 1024),
            patch.object(
                uploader, "upload_thumbnail", return_value=mock_thumb_success
            ) as mock_thumb_upload,
        ):
            result = await uploader.upload_media("/path/to/video.mp4", metadata)

            # Verify thumbnail upload was called
            mock_thumb_upload.assert_called_once_with("video123", "/path/to/thumb.jpg")

            # Verify result includes thumbnail status
            assert result.metadata.get("thumbnail_uploaded") == mock_thumb_success


class TestYouTubeUploaderFileValidation:
    """Test file validation for YouTube uploads."""

    def test_valid_video_file(self):
        """Test validation of valid video file."""
        uploader = YouTubeUploader()

        with (
            patch("os.path.exists", return_value=True),
            patch("os.path.getsize", return_value=1024 * 1024),
        ):  # 1MB
            # Should not raise any exception
            uploader._validate_file("/path/to/video.mp4")

    def test_missing_file(self):
        """Test validation with missing file."""
        uploader = YouTubeUploader()

        with patch("os.path.exists", return_value=False):
            with pytest.raises(ValidationError) as exc_info:
                uploader._validate_file("/path/to/nonexistent.mp4")

            assert "not found" in str(exc_info.value).lower()

    def test_file_too_large(self):
        """Test validation with file too large."""
        uploader = YouTubeUploader()

        with (
            patch("os.path.exists", return_value=True),
            patch("os.path.getsize", return_value=256 * 1024 * 1024 * 1024 + 1),
        ):  # > 256GB
            with pytest.raises(ValidationError) as exc_info:
                uploader._validate_file("/path/to/huge_video.mp4")

            assert "too large" in str(exc_info.value).lower()

    def test_empty_file(self):
        """Test validation with empty file."""
        uploader = YouTubeUploader()

        with (
            patch("os.path.exists", return_value=True),
            patch("os.path.getsize", return_value=0),
        ):
            with pytest.raises(ValidationError) as exc_info:
                uploader._validate_file("/path/to/empty.mp4")

            assert "empty" in str(exc_info.value).lower()


class TestYouTubeUploaderUpload:
    """Test video upload functionality."""

    @pytest.mark.asyncio
    async def test_successful_upload(self):
        """Test successful video upload."""
        uploader = YouTubeUploader()
        uploader.is_authenticated = True
        uploader.service = MagicMock()

        # Mock the YouTube API response
        mock_response = {
            "id": "test_video_id_123",
            "snippet": {"title": "Test Video", "description": "Test description"},
        }

        mock_insert_request = MagicMock()
        mock_insert_request.next_chunk.return_value = (
            None,
            mock_response,
        )  # Mock resumable upload
        uploader.service.videos().insert.return_value = mock_insert_request

        metadata = MediaMetadata(title="Test Video", description="Test description")

        with (
            patch.object(uploader, "_validate_file"),
            patch("medusa.uploaders.youtube.MediaFileUpload") as mock_media_upload,
            patch("os.path.getsize", return_value=1024 * 1024),
        ):  # Mock file size
            mock_media_upload.return_value = MagicMock()

            result = await uploader._upload_media("/path/to/video.mp4", metadata)

            assert isinstance(result, UploadResult)
            assert result.platform == "youtube"
            assert result.success is True
            assert result.upload_id == "test_video_id_123"
            assert (
                result.media_url == "https://www.youtube.com/watch?v=test_video_id_123"
            )
            assert result.metadata["video_id"] == "test_video_id_123"

    @pytest.mark.asyncio
    async def test_upload_with_progress_callback(self):
        """Test upload with progress reporting."""
        uploader = YouTubeUploader()
        uploader.is_authenticated = True
        uploader.service = MagicMock()

        # Mock resumable upload with progress
        mock_response = {"id": "test_video_id_123"}
        mock_insert_request = MagicMock()

        # Simulate progress updates
        progress_calls = []

        def mock_next_chunk():
            if len(progress_calls) == 0:
                progress_calls.append(1)
                status = MagicMock()
                status.resumable_progress = 0.5
                return (status, None)
            else:
                status = MagicMock()
                status.resumable_progress = 1.0
                return (status, mock_response)

        mock_insert_request.next_chunk = mock_next_chunk
        uploader.service.videos().insert.return_value = mock_insert_request

        metadata = MediaMetadata(title="Test Video")
        progress_updates = []

        def progress_callback(progress: UploadProgress):
            progress_updates.append(progress)

        with (
            patch.object(uploader, "_validate_file"),
            patch("medusa.uploaders.youtube.MediaFileUpload") as mock_media_upload,
            patch("os.path.getsize", return_value=1024 * 1024),
        ):  # Mock file size
            mock_media_upload.return_value = MagicMock()

            result = await uploader._upload_media(
                "/path/to/video.mp4", metadata, progress_callback
            )

            assert result.success is True
            assert len(progress_updates) >= 1

    @pytest.mark.asyncio
    async def test_upload_api_error(self):
        """Test upload with YouTube API error."""
        uploader = YouTubeUploader()
        uploader.is_authenticated = True
        uploader.service = MagicMock()

        from googleapiclient.errors import HttpError

        # Mock API error
        mock_response = MagicMock()
        mock_response.status = 400
        mock_response.reason = "Bad Request"
        api_error = HttpError(mock_response, b'{"error": {"message": "Invalid video"}}')

        mock_insert_request = MagicMock()
        mock_insert_request.next_chunk.side_effect = api_error
        uploader.service.videos().insert.return_value = mock_insert_request

        metadata = MediaMetadata(title="Test Video")

        with (
            patch.object(uploader, "_validate_file"),
            patch("medusa.uploaders.youtube.MediaFileUpload"),
            patch("os.path.getsize", return_value=1024 * 1024),
        ):  # Mock file size
            with pytest.raises(ValidationError) as exc_info:
                await uploader._upload_media("/path/to/video.mp4", metadata)

            assert "Invalid video" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_upload_quota_exceeded(self):
        """Test upload with quota exceeded error."""
        uploader = YouTubeUploader()
        uploader.is_authenticated = True
        uploader.service = MagicMock()

        from googleapiclient.errors import HttpError

        # Mock quota exceeded error
        mock_response = MagicMock()
        mock_response.status = 403
        mock_response.reason = "Forbidden"
        api_error = HttpError(
            mock_response, b'{"error": {"message": "Quota exceeded"}}'
        )

        mock_insert_request = MagicMock()
        mock_insert_request.next_chunk.side_effect = api_error
        uploader.service.videos().insert.return_value = mock_insert_request

        metadata = MediaMetadata(title="Test Video")

        with (
            patch.object(uploader, "_validate_file"),
            patch("medusa.uploaders.youtube.MediaFileUpload"),
            patch("os.path.getsize", return_value=1024 * 1024),
        ):  # Mock file size
            with pytest.raises(RateLimitError) as exc_info:
                await uploader._upload_media("/path/to/video.mp4", metadata)

            assert "quota" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_upload_network_error(self):
        """Test upload with network error."""
        uploader = YouTubeUploader()
        uploader.is_authenticated = True
        uploader.service = MagicMock()

        import socket

        network_error = socket.error("Connection failed")

        mock_insert_request = MagicMock()
        # Make sure to simulate non-retryable error to avoid infinite loop
        mock_insert_request.next_chunk.side_effect = network_error
        uploader.service.videos().insert.return_value = mock_insert_request

        metadata = MediaMetadata(title="Test Video")

        # Mock _is_retryable_error to return False for this test
        with (
            patch.object(uploader, "_validate_file"),
            patch("medusa.uploaders.youtube.MediaFileUpload"),
            patch("os.path.getsize", return_value=1024 * 1024),
            patch.object(uploader, "_is_retryable_error", return_value=False),
        ):
            with pytest.raises(UploadError) as exc_info:
                await uploader._upload_media("/path/to/video.mp4", metadata)

            assert "Connection failed" in str(exc_info.value)


class TestYouTubeUploaderMetadataConversion:
    """Test metadata conversion for YouTube API."""

    def test_basic_metadata_conversion(self):
        """Test conversion of basic metadata."""
        uploader = YouTubeUploader()
        metadata = MediaMetadata(
            title="Test Video",
            description="Test description",
            tags=["test", "video"],
            privacy="public",
        )

        result = uploader._convert_metadata_to_youtube_format(metadata)

        assert result["snippet"]["title"] == "Test Video"
        assert result["snippet"]["description"] == "Test description"
        assert result["snippet"]["tags"] == ["test", "video"]
        assert result["status"]["privacyStatus"] == "public"

    def test_metadata_conversion_with_category(self):
        """Test metadata conversion with category."""
        uploader = YouTubeUploader()
        metadata = MediaMetadata(title="Test Video", category="gaming")

        result = uploader._convert_metadata_to_youtube_format(metadata)

        # Category should be mapped to YouTube category ID
        assert "categoryId" in result["snippet"]

    def test_metadata_conversion_with_defaults(self):
        """Test metadata conversion with default values."""
        uploader = YouTubeUploader()
        metadata = MediaMetadata(title="Test Video")

        result = uploader._convert_metadata_to_youtube_format(metadata)

        assert result["snippet"]["title"] == "Test Video"
        assert result["snippet"]["description"] == ""
        assert result["snippet"]["tags"] == []
        assert result["status"]["privacyStatus"] == "unlisted"  # Default privacy


class TestYouTubeUploaderResumableUpload:
    """Test resumable upload functionality."""

    @pytest.mark.asyncio
    async def test_resumable_upload_success(self):
        """Test successful resumable upload."""
        uploader = YouTubeUploader()

        mock_insert_request = MagicMock()
        mock_response = {"id": "test_video_id_123"}

        # Simulate resumable upload process
        call_count = 0

        def mock_next_chunk():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                status = MagicMock()
                status.resumable_progress = 0.5
                return (status, None)
            else:
                status = MagicMock()
                status.resumable_progress = 1.0
                return (status, mock_response)

        mock_insert_request.next_chunk = mock_next_chunk

        progress_updates = []

        def progress_callback(progress):
            progress_updates.append(progress)

        result = await uploader._perform_resumable_upload(
            mock_insert_request, progress_callback, 1000
        )

        assert result == mock_response
        assert len(progress_updates) >= 1

    @pytest.mark.asyncio
    async def test_resumable_upload_with_retry(self):
        """Test resumable upload with retry on failure."""
        uploader = YouTubeUploader()

        mock_insert_request = MagicMock()
        mock_response = {"id": "test_video_id_123"}

        # Mock a retryable error (socket error)
        import socket

        # Simulate failure then success
        call_count = 0

        def mock_next_chunk():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise socket.error("Temporary network failure")
            else:
                status = MagicMock()
                status.resumable_progress = 1.0
                return (status, mock_response)

        mock_insert_request.next_chunk = mock_next_chunk

        result = await uploader._perform_resumable_upload(
            mock_insert_request, None, 1000
        )

        assert result == mock_response


class TestYouTubeUploaderIntegration:
    """Test integration scenarios."""

    @pytest.mark.asyncio
    async def test_full_upload_workflow(self):
        """Test complete upload workflow from start to finish."""
        config = PlatformConfig(
            platform_name="youtube",
            credentials={
                "client_secrets_file": "test_secrets.json",
                "credentials_file": "test_credentials.json",
            },
        )

        uploader = YouTubeUploader(config=config)

        # Mock authentication
        with (
            patch.object(uploader.auth_manager, "authenticate", return_value=True),
            patch("medusa.uploaders.youtube.build") as mock_build,
        ):
            mock_service = MagicMock()
            mock_response = {"id": "test_video_id_123"}
            mock_insert_request = MagicMock()
            mock_insert_request.execute.return_value = mock_response
            # Mock next_chunk for resumable upload
            mock_insert_request.next_chunk.return_value = (None, mock_response)
            mock_service.videos().insert.return_value = mock_insert_request
            mock_build.return_value = mock_service

            # Authenticate
            await uploader.authenticate()

            # Upload video
            metadata = MediaMetadata(title="Integration Test Video")

            with (
                patch.object(uploader, "_validate_file"),
                patch("medusa.uploaders.youtube.MediaFileUpload"),
                patch("os.path.getsize", return_value=1024 * 1024),
            ):  # Mock file size
                result = await uploader.upload_media("/path/to/video.mp4", metadata)

                assert result.success is True
                assert result.upload_id == "test_video_id_123"

    @pytest.mark.asyncio
    async def test_upload_without_authentication(self):
        """Test upload attempt without authentication."""
        uploader = YouTubeUploader()
        metadata = MediaMetadata(title="Test Video")

        with pytest.raises(AuthenticationError) as exc_info:
            await uploader.upload_media("/path/to/video.mp4", metadata)

        assert "authentication required" in str(exc_info.value).lower()


class TestYouTubeUploaderUtilities:
    """Test utility methods."""

    def test_get_video_url(self):
        """Test video URL generation."""
        uploader = YouTubeUploader()

        url = uploader._get_video_url("test_video_id_123")

        assert url == "https://www.youtube.com/watch?v=test_video_id_123"

    def test_get_category_id_mapping(self):
        """Test category ID mapping."""
        uploader = YouTubeUploader()

        # Test known categories
        assert uploader._get_category_id("gaming") == "20"
        assert uploader._get_category_id("music") == "10"
        assert uploader._get_category_id("education") == "27"

        # Test unknown category (should return default)
        assert uploader._get_category_id("unknown") == "22"  # People & Blogs

    def test_is_retryable_error(self):
        """Test retryable error detection."""
        uploader = YouTubeUploader()

        # Network errors should be retryable
        import socket

        network_error = socket.error("Connection failed")
        assert uploader._is_retryable_error(network_error) is True

        # HTTP 5xx errors should be retryable
        from googleapiclient.errors import HttpError

        mock_response = MagicMock()
        mock_response.status = 500
        http_error = HttpError(mock_response, b'{"error": {"message": "Server error"}}')
        assert uploader._is_retryable_error(http_error) is True

        # HTTP 4xx errors should not be retryable (except specific ones)
        mock_response.status = 400
        http_error = HttpError(mock_response, b'{"error": {"message": "Bad request"}}')
        assert uploader._is_retryable_error(http_error) is False

    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Test cleanup functionality."""
        uploader = YouTubeUploader()
        uploader.is_authenticated = True
        uploader.service = MagicMock()

        with patch.object(uploader.auth_manager, "cleanup") as mock_cleanup:
            await uploader.cleanup()

            mock_cleanup.assert_called_once()
            assert uploader.service is None
