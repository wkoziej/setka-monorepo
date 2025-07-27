"""
Test suite for the Medusa models and data structures.

This module tests all data models, enums, and their validation methods,
ensuring robust handling of task states, metadata, and platform configurations.
"""

import pytest
import tempfile
import os
from datetime import datetime, timezone

from medusa.models import (
    TaskStatus,
    TaskResult,
    MediaMetadata,
    PlatformConfig,
    PublishRequest,
    TaskTransition,
    validate_task_transition,
)
from medusa.exceptions import MedusaError


class TestTaskStatus:
    """Test the TaskStatus enum and state transitions."""

    def test_task_status_enum_values(self):
        """Test that TaskStatus enum has all required values."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"

    def test_task_status_from_string(self):
        """Test creating TaskStatus from string values."""
        assert TaskStatus("pending") == TaskStatus.PENDING
        assert TaskStatus("in_progress") == TaskStatus.IN_PROGRESS
        assert TaskStatus("completed") == TaskStatus.COMPLETED
        assert TaskStatus("failed") == TaskStatus.FAILED
        assert TaskStatus("cancelled") == TaskStatus.CANCELLED

    def test_task_status_invalid_value(self):
        """Test that invalid TaskStatus values raise ValueError."""
        with pytest.raises(ValueError):
            TaskStatus("invalid_status")

    def test_task_status_comparison(self):
        """Test TaskStatus comparison operations."""
        assert TaskStatus.PENDING != TaskStatus.IN_PROGRESS
        assert TaskStatus.COMPLETED == TaskStatus.COMPLETED

    def test_task_status_string_representation(self):
        """Test string representation of TaskStatus."""
        assert str(TaskStatus.PENDING) == "TaskStatus.PENDING"
        assert repr(TaskStatus.IN_PROGRESS) == "<TaskStatus.IN_PROGRESS: 'in_progress'>"


class TestTaskTransition:
    """Test task state transition validation."""

    def test_valid_transitions(self):
        """Test all valid task state transitions."""
        # From PENDING
        assert (
            validate_task_transition(TaskStatus.PENDING, TaskStatus.IN_PROGRESS) is True
        )
        assert (
            validate_task_transition(TaskStatus.PENDING, TaskStatus.CANCELLED) is True
        )

        # From IN_PROGRESS
        assert (
            validate_task_transition(TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED)
            is True
        )
        assert (
            validate_task_transition(TaskStatus.IN_PROGRESS, TaskStatus.FAILED) is True
        )
        assert (
            validate_task_transition(TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED)
            is True
        )

        # Terminal states should not transition
        assert (
            validate_task_transition(TaskStatus.COMPLETED, TaskStatus.COMPLETED) is True
        )
        assert validate_task_transition(TaskStatus.FAILED, TaskStatus.FAILED) is True
        assert (
            validate_task_transition(TaskStatus.CANCELLED, TaskStatus.CANCELLED) is True
        )

    def test_invalid_transitions(self):
        """Test invalid task state transitions."""
        # Cannot go backwards
        assert (
            validate_task_transition(TaskStatus.IN_PROGRESS, TaskStatus.PENDING)
            is False
        )
        assert (
            validate_task_transition(TaskStatus.COMPLETED, TaskStatus.PENDING) is False
        )
        assert (
            validate_task_transition(TaskStatus.COMPLETED, TaskStatus.IN_PROGRESS)
            is False
        )

        # Cannot transition from terminal states
        assert (
            validate_task_transition(TaskStatus.COMPLETED, TaskStatus.FAILED) is False
        )
        assert (
            validate_task_transition(TaskStatus.FAILED, TaskStatus.COMPLETED) is False
        )
        assert (
            validate_task_transition(TaskStatus.CANCELLED, TaskStatus.IN_PROGRESS)
            is False
        )

        # Cannot skip states
        assert (
            validate_task_transition(TaskStatus.PENDING, TaskStatus.COMPLETED) is False
        )
        assert validate_task_transition(TaskStatus.PENDING, TaskStatus.FAILED) is False

    def test_transition_validation_with_exception(self):
        """Test transition validation that raises exceptions."""
        transition = TaskTransition(
            from_status=TaskStatus.COMPLETED,
            to_status=TaskStatus.PENDING,
            timestamp=datetime.now(timezone.utc),
        )

        with pytest.raises(MedusaError) as exc_info:
            transition.validate()

        assert "Invalid state transition" in str(exc_info.value)
        assert "completed" in str(exc_info.value)
        assert "pending" in str(exc_info.value)


class TestTaskResult:
    """Test the TaskResult dataclass."""

    def test_task_result_creation(self):
        """Test basic TaskResult creation."""
        result = TaskResult(task_id="test_task_123", status=TaskStatus.COMPLETED)

        assert result.task_id == "test_task_123"
        assert result.status == TaskStatus.COMPLETED
        assert result.message is None
        assert result.error is None
        assert result.failed_platform is None
        assert result.results == {}
        assert result.created_at is not None
        assert result.updated_at is not None

    def test_task_result_with_all_fields(self):
        """Test TaskResult with all fields populated."""
        results_data = {
            "youtube_url": "https://youtube.com/watch?v=abc123",
            "facebook_post_id": "123456789",
        }

        result = TaskResult(
            task_id="test_task_456",
            status=TaskStatus.FAILED,
            message="Upload failed",
            error="YouTube API error: Video file too large",
            failed_platform="youtube",
            results=results_data,
        )

        assert result.task_id == "test_task_456"
        assert result.status == TaskStatus.FAILED
        assert result.message == "Upload failed"
        assert result.error == "YouTube API error: Video file too large"
        assert result.failed_platform == "youtube"
        assert result.results == results_data

    def test_task_result_validation_success(self):
        """Test TaskResult validation for successful completion."""
        result = TaskResult(
            task_id="valid_task",
            status=TaskStatus.COMPLETED,
            results={"youtube_url": "https://youtube.com/watch?v=test"},
        )

        # Should not raise any exceptions
        result.validate()

    def test_task_result_validation_failed_without_error(self):
        """Test TaskResult validation fails when status is FAILED but no error provided."""
        result = TaskResult(task_id="invalid_task", status=TaskStatus.FAILED)

        with pytest.raises(MedusaError) as exc_info:
            result.validate()

        assert "Failed tasks must have error information" in str(exc_info.value)

    def test_task_result_validation_invalid_task_id(self):
        """Test TaskResult validation fails with invalid task ID."""
        result = TaskResult(
            task_id="",  # Empty task ID
            status=TaskStatus.PENDING,
        )

        with pytest.raises(MedusaError) as exc_info:
            result.validate()

        assert "Task ID cannot be empty" in str(exc_info.value)

    def test_task_result_to_dict(self):
        """Test TaskResult serialization to dictionary."""
        result = TaskResult(
            task_id="serialize_test",
            status=TaskStatus.COMPLETED,
            message="Success",
            results={"url": "https://example.com"},
        )

        result_dict = result.to_dict()

        assert result_dict["task_id"] == "serialize_test"
        assert result_dict["status"] == "completed"
        assert result_dict["message"] == "Success"
        assert result_dict["results"] == {"url": "https://example.com"}
        assert "created_at" in result_dict
        assert "updated_at" in result_dict

    def test_task_result_from_dict(self):
        """Test TaskResult deserialization from dictionary."""
        data = {
            "task_id": "deserialize_test",
            "status": "in_progress",
            "message": "Processing...",
            "error": None,
            "failed_platform": None,
            "results": {"progress": 50},
            "created_at": "2024-01-01T12:00:00Z",
            "updated_at": "2024-01-01T12:05:00Z",
        }

        result = TaskResult.from_dict(data)

        assert result.task_id == "deserialize_test"
        assert result.status == TaskStatus.IN_PROGRESS
        assert result.message == "Processing..."
        assert result.results == {"progress": 50}

    def test_task_result_update_status(self):
        """Test updating TaskResult status."""
        result = TaskResult(task_id="update_test", status=TaskStatus.PENDING)

        original_created = result.created_at
        original_updated = result.updated_at

        # Update status
        result.update_status(TaskStatus.IN_PROGRESS, "Starting upload...")

        assert result.status == TaskStatus.IN_PROGRESS
        assert result.message == "Starting upload..."
        assert result.created_at == original_created  # Should not change
        assert result.updated_at > original_updated  # Should be updated

    def test_task_result_update_status_invalid_transition(self):
        """Test TaskResult status update with invalid transition."""
        result = TaskResult(task_id="invalid_update_test", status=TaskStatus.COMPLETED)

        with pytest.raises(MedusaError) as exc_info:
            result.update_status(TaskStatus.PENDING)

        assert "Invalid status transition" in str(exc_info.value)

    def test_task_result_add_platform_result(self):
        """Test adding platform-specific results."""
        result = TaskResult(task_id="platform_test", status=TaskStatus.IN_PROGRESS)

        result.add_platform_result(
            "youtube", {"url": "https://youtube.com/watch?v=123"}
        )
        result.add_platform_result("facebook", {"post_id": "fb_123"})

        assert result.results["youtube"]["url"] == "https://youtube.com/watch?v=123"
        assert result.results["facebook"]["post_id"] == "fb_123"


class TestMediaMetadata:
    """Test the MediaMetadata dataclass."""

    def test_media_metadata_creation(self):
        """Test basic MediaMetadata creation."""
        metadata = MediaMetadata(
            title="Test Video", description="A test video description"
        )

        assert metadata.title == "Test Video"
        assert metadata.description == "A test video description"
        assert metadata.tags == []
        assert metadata.privacy is None
        assert metadata.thumbnail_url is None
        assert metadata.duration is None
        assert metadata.file_size is None

    def test_media_metadata_with_all_fields(self):
        """Test MediaMetadata with all fields populated."""
        metadata = MediaMetadata(
            title="Complete Video",
            description="A complete video with all metadata",
            tags=["test", "demo", "video"],
            privacy="public",
            thumbnail_url="https://example.com/thumb.jpg",
            duration=120,  # 2 minutes
            file_size=1048576,  # 1MB
            category="Education",
            language="en",
        )

        assert metadata.title == "Complete Video"
        assert metadata.tags == ["test", "demo", "video"]
        assert metadata.privacy == "public"
        assert metadata.duration == 120
        assert metadata.file_size == 1048576
        assert metadata.category == "Education"
        assert metadata.language == "en"

    def test_media_metadata_validation_success(self):
        """Test MediaMetadata validation for valid data."""
        metadata = MediaMetadata(
            title="Valid Video",
            description="Valid description",
            tags=["valid", "tags"],
            privacy="public",
        )

        # Should not raise any exceptions
        metadata.validate()

    def test_media_metadata_validation_long_title(self):
        """Test MediaMetadata validation fails for overly long title."""
        metadata = MediaMetadata(
            title="x" * 101,  # Too long (max 100 chars)
            description="Valid description",
        )

        with pytest.raises(MedusaError) as exc_info:
            metadata.validate()

        assert "Title too long" in str(exc_info.value)

    def test_media_metadata_validation_long_description(self):
        """Test MediaMetadata validation fails for overly long description."""
        metadata = MediaMetadata(
            title="Valid Title",
            description="x" * 5001,  # Too long (max 5000 chars)
        )

        with pytest.raises(MedusaError) as exc_info:
            metadata.validate()

        assert "Description too long" in str(exc_info.value)

    def test_media_metadata_validation_invalid_privacy(self):
        """Test MediaMetadata validation fails for invalid privacy setting."""
        metadata = MediaMetadata(title="Valid Title", privacy="invalid_privacy")

        with pytest.raises(MedusaError) as exc_info:
            metadata.validate()

        assert "Invalid privacy setting" in str(exc_info.value)

    def test_media_metadata_validation_too_many_tags(self):
        """Test MediaMetadata validation fails for too many tags."""
        metadata = MediaMetadata(
            title="Valid Title",
            tags=["tag" + str(i) for i in range(51)],  # Too many tags (max 50)
        )

        with pytest.raises(MedusaError) as exc_info:
            metadata.validate()

        assert "Too many tags" in str(exc_info.value)

    def test_media_metadata_validation_long_tag(self):
        """Test MediaMetadata validation fails for overly long tag."""
        metadata = MediaMetadata(
            title="Valid Title",
            tags=["x" * 51],  # Too long tag (max 50 chars)
        )

        with pytest.raises(MedusaError) as exc_info:
            metadata.validate()

        assert "Tag too long" in str(exc_info.value)

    def test_media_metadata_to_dict(self):
        """Test MediaMetadata serialization to dictionary."""
        metadata = MediaMetadata(
            title="Serialize Test",
            description="Test description",
            tags=["test"],
            privacy="unlisted",
        )

        metadata_dict = metadata.to_dict()

        assert metadata_dict["title"] == "Serialize Test"
        assert metadata_dict["description"] == "Test description"
        assert metadata_dict["tags"] == ["test"]
        assert metadata_dict["privacy"] == "unlisted"

    def test_media_metadata_from_dict(self):
        """Test MediaMetadata deserialization from dictionary."""
        data = {
            "title": "Deserialize Test",
            "description": "Test description",
            "tags": ["test", "demo"],
            "privacy": "private",
            "duration": 300,
        }

        metadata = MediaMetadata.from_dict(data)

        assert metadata.title == "Deserialize Test"
        assert metadata.description == "Test description"
        assert metadata.tags == ["test", "demo"]
        assert metadata.privacy == "private"
        assert metadata.duration == 300

    def test_media_metadata_sanitize_tags(self):
        """Test MediaMetadata tag sanitization."""
        metadata = MediaMetadata(
            title="Tag Test", tags=["  spaced  ", "UPPERCASE", "special@chars!", ""]
        )

        metadata.sanitize()

        # Should clean up tags
        assert "spaced" in metadata.tags
        assert "uppercase" in metadata.tags
        assert "specialchars" in metadata.tags
        assert "" not in metadata.tags

    def test_media_metadata_sanitize_empty_tags(self):
        """Test MediaMetadata sanitization with empty tags list."""
        metadata = MediaMetadata(title="Empty Tags Test", tags=[])

        metadata.sanitize()

        # Should handle empty tags gracefully
        assert metadata.tags == []


class TestPlatformConfig:
    """Test the enhanced PlatformConfig dataclass."""

    def test_platform_config_creation(self):
        """Test basic PlatformConfig creation."""
        config = PlatformConfig(platform_name="youtube", enabled=True)

        assert config.platform_name == "youtube"
        assert config.enabled is True
        assert config.credentials == {}
        assert config.metadata == {}
        assert config.rate_limit is None
        assert config.retry_attempts == 3

    def test_platform_config_with_all_fields(self):
        """Test PlatformConfig with all fields populated."""
        credentials = {
            "client_secrets_file": "secrets.json",
            "credentials_file": "creds.json",
        }
        metadata = {"default_privacy": "unlisted", "default_category": "Education"}

        config = PlatformConfig(
            platform_name="youtube",
            enabled=True,
            credentials=credentials,
            metadata=metadata,
            rate_limit=100,
            retry_attempts=5,
            timeout=30,
        )

        assert config.platform_name == "youtube"
        assert config.credentials == credentials
        assert config.metadata == metadata
        assert config.rate_limit == 100
        assert config.retry_attempts == 5
        assert config.timeout == 30

    def test_platform_config_validation_success(self):
        """Test PlatformConfig validation for valid configuration."""
        config = PlatformConfig(
            platform_name="facebook",
            enabled=True,
            credentials={"access_token": "valid_token"},
            retry_attempts=3,
        )

        # Should not raise any exceptions
        config.validate()

    def test_platform_config_validation_invalid_platform(self):
        """Test PlatformConfig validation fails for invalid platform name."""
        config = PlatformConfig(platform_name="invalid_platform", enabled=True)

        with pytest.raises(MedusaError) as exc_info:
            config.validate()

        assert "Unsupported platform" in str(exc_info.value)

    def test_platform_config_validation_negative_retry(self):
        """Test PlatformConfig validation fails for negative retry attempts."""
        config = PlatformConfig(
            platform_name="youtube", enabled=True, retry_attempts=-1
        )

        with pytest.raises(MedusaError) as exc_info:
            config.validate()

        assert "Retry attempts must be non-negative" in str(exc_info.value)

    def test_platform_config_validation_invalid_timeout(self):
        """Test PlatformConfig validation fails for invalid timeout."""
        config = PlatformConfig(
            platform_name="youtube",
            enabled=True,
            timeout=0,  # Invalid timeout (must be positive)
        )

        with pytest.raises(MedusaError) as exc_info:
            config.validate()

        assert "Timeout must be positive" in str(exc_info.value)

    def test_platform_config_is_configured(self):
        """Test PlatformConfig.is_configured method."""
        # Not configured (no credentials)
        config1 = PlatformConfig(platform_name="youtube", enabled=True)
        assert config1.is_configured() is False

        # Configured
        config2 = PlatformConfig(
            platform_name="youtube", enabled=True, credentials={"access_token": "token"}
        )
        assert config2.is_configured() is True

        # Disabled
        config3 = PlatformConfig(
            platform_name="youtube",
            enabled=False,
            credentials={"access_token": "token"},
        )
        assert config3.is_configured() is False

    def test_platform_config_to_dict(self):
        """Test PlatformConfig serialization to dictionary."""
        config = PlatformConfig(
            platform_name="youtube",
            enabled=True,
            credentials={"token": "test"},
            retry_attempts=5,
        )

        config_dict = config.to_dict()

        assert config_dict["platform_name"] == "youtube"
        assert config_dict["enabled"] is True
        assert config_dict["credentials"] == {"token": "test"}
        assert config_dict["retry_attempts"] == 5

    def test_platform_config_from_dict(self):
        """Test PlatformConfig deserialization from dictionary."""
        data = {
            "platform_name": "facebook",
            "enabled": True,
            "credentials": {"access_token": "token"},
            "metadata": {"default": "value"},
            "rate_limit": 100,
            "retry_attempts": 3,
            "timeout": 30,
        }

        config = PlatformConfig.from_dict(data)

        assert config.platform_name == "facebook"
        assert config.enabled is True
        assert config.credentials == {"access_token": "token"}
        assert config.metadata == {"default": "value"}
        assert config.rate_limit == 100
        assert config.retry_attempts == 3
        assert config.timeout == 30


class TestPublishRequest:
    """Test the PublishRequest dataclass."""

    def test_publish_request_creation(self):
        """Test basic PublishRequest creation."""
        request = PublishRequest(
            media_file_path="/path/to/video.mp4", platforms=["youtube", "facebook"]
        )

        assert request.media_file_path == "/path/to/video.mp4"
        assert request.platforms == ["youtube", "facebook"]
        assert request.metadata == {}
        assert request.priority == 1
        assert request.schedule_time is None
        assert request.created_at is not None

    def test_publish_request_with_metadata(self):
        """Test PublishRequest with platform-specific metadata."""
        metadata = {
            "youtube": {
                "title": "Test Video",
                "description": "Test description",
                "privacy": "unlisted",
            },
            "facebook": {"message": "Check out my video: {youtube_url}"},
        }

        request = PublishRequest(
            media_file_path="/path/to/video.mp4",
            platforms=["youtube", "facebook"],
            metadata=metadata,
            priority=2,
        )

        assert request.metadata == metadata
        assert request.priority == 2

    def test_publish_request_validation_with_real_file(self):
        """Test PublishRequest validation with a real temporary file."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b"test video content")
            temp_path = temp_file.name

        try:
            request = PublishRequest(media_file_path=temp_path, platforms=["youtube"])

            # Should not raise any exceptions
            request.validate()
        finally:
            # Clean up
            os.unlink(temp_path)

    def test_publish_request_validation_file_not_found(self):
        """Test PublishRequest validation fails when file doesn't exist."""
        request = PublishRequest(
            media_file_path="/path/to/nonexistent_video.mp4", platforms=["youtube"]
        )

        with pytest.raises(MedusaError) as exc_info:
            request.validate()

        assert "Media file not found" in str(exc_info.value)

    def test_publish_request_validation_empty_platforms(self):
        """Test PublishRequest validation fails for empty platforms list."""
        request = PublishRequest(media_file_path="/path/to/video.mp4", platforms=[])

        with pytest.raises(MedusaError) as exc_info:
            request.validate()

        assert "At least one platform must be specified" in str(exc_info.value)

    def test_publish_request_validation_invalid_priority(self):
        """Test PublishRequest validation fails for invalid priority."""
        request = PublishRequest(
            media_file_path="/path/to/video.mp4",
            platforms=["youtube"],
            priority=0,  # Invalid priority (must be >= 1)
        )

        with pytest.raises(MedusaError) as exc_info:
            request.validate()

        assert "Priority must be >= 1" in str(exc_info.value)

    def test_publish_request_validation_invalid_platform(self):
        """Test PublishRequest validation fails for unsupported platform."""
        # Create a temporary file so file existence check passes
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b"test content")
            temp_path = temp_file.name

        try:
            request = PublishRequest(
                media_file_path=temp_path, platforms=["invalid_platform"]
            )

            with pytest.raises(MedusaError) as exc_info:
                request.validate()

            assert "Unsupported platform" in str(exc_info.value)
        finally:
            # Clean up
            os.unlink(temp_path)

    def test_publish_request_get_platform_metadata(self):
        """Test getting platform-specific metadata."""
        metadata = {
            "youtube": {"title": "YouTube Title"},
            "facebook": {"message": "Facebook Message"},
        }

        request = PublishRequest(
            media_file_path="/path/to/video.mp4",
            platforms=["youtube", "facebook"],
            metadata=metadata,
        )

        youtube_meta = request.get_platform_metadata("youtube")
        facebook_meta = request.get_platform_metadata("facebook")
        vimeo_meta = request.get_platform_metadata("vimeo")

        assert youtube_meta == {"title": "YouTube Title"}
        assert facebook_meta == {"message": "Facebook Message"}
        assert vimeo_meta == {}  # Should return empty dict for missing platform

    def test_publish_request_to_dict(self):
        """Test PublishRequest serialization to dictionary."""
        request = PublishRequest(
            media_file_path="/path/to/video.mp4", platforms=["youtube"], priority=2
        )

        request_dict = request.to_dict()

        assert request_dict["media_file_path"] == "/path/to/video.mp4"
        assert request_dict["platforms"] == ["youtube"]
        assert request_dict["priority"] == 2
        assert "created_at" in request_dict

    def test_publish_request_to_dict_with_schedule_time(self):
        """Test PublishRequest serialization with schedule time."""
        schedule_time = datetime.now(timezone.utc)
        request = PublishRequest(
            media_file_path="/path/to/video.mp4",
            platforms=["youtube"],
            schedule_time=schedule_time,
        )

        request_dict = request.to_dict()

        assert request_dict["schedule_time"] == schedule_time.isoformat()

    def test_publish_request_from_dict(self):
        """Test PublishRequest deserialization from dictionary."""
        data = {
            "media_file_path": "/path/to/video.mp4",
            "platforms": ["youtube", "facebook"],
            "metadata": {"youtube": {"title": "Test"}},
            "priority": 3,
            "schedule_time": None,
            "created_at": "2024-01-01T12:00:00Z",
        }

        request = PublishRequest.from_dict(data)

        assert request.media_file_path == "/path/to/video.mp4"
        assert request.platforms == ["youtube", "facebook"]
        assert request.metadata == {"youtube": {"title": "Test"}}
        assert request.priority == 3

    def test_publish_request_from_dict_with_schedule_time(self):
        """Test PublishRequest deserialization with schedule time."""
        data = {
            "media_file_path": "/path/to/video.mp4",
            "platforms": ["youtube"],
            "metadata": {},
            "priority": 1,
            "schedule_time": "2024-12-31T23:59:59Z",
            "created_at": "2024-01-01T12:00:00Z",
        }

        request = PublishRequest.from_dict(data)

        assert request.schedule_time is not None
        assert request.schedule_time.year == 2024
        assert request.schedule_time.month == 12
        assert request.schedule_time.day == 31
