"""
Pytest configuration and fixtures for Medusa library tests.

This module provides:
- Common fixtures for testing
- Mock utilities for external services
- Test data factories
- Async testing configuration
- Test isolation setup
"""

import pytest
import asyncio
import tempfile
import json
import os
from pathlib import Path
from typing import Dict, Any, Generator, AsyncGenerator
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from datetime import datetime, timedelta

# Import Medusa components for fixtures
from medusa.models import TaskStatus, TaskResult, MediaMetadata, PlatformConfig
from medusa.exceptions import (
    MedusaError, ConfigError, UploadError, PublishError, 
    TaskError, AuthenticationError, ValidationError, 
    RateLimitError, NetworkError
)


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests"
    )
    config.addinivalue_line(
        "markers", "slow: Slow running tests"
    )
    config.addinivalue_line(
        "markers", "async_test: Async tests requiring event loop"
    )
    config.addinivalue_line(
        "markers", "mock_api: Tests using mocked external APIs"
    )


# ============================================================================
# Basic Fixtures
# ============================================================================

@pytest.fixture
def temp_dir():
    """Provide temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def temp_config_file(temp_dir):
    """Provide temporary configuration file."""
    config = {
        "youtube": {
            "client_secrets_file": "secrets/youtube_client_secrets.json",
            "credentials_file": "secrets/youtube_credentials.json"
        },
        "facebook": {
            "page_id": "1234567890",
            "access_token": "test_facebook_token"
        },
        "vimeo": {
            "access_token": "test_vimeo_token"
        }
    }
    
    config_file = temp_dir / "test_config.json"
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    return config_file


@pytest.fixture
def temp_media_file(temp_dir):
    """Provide temporary media file for testing."""
    media_file = temp_dir / "test_video.mp4"
    # Create a small test file
    with open(media_file, 'wb') as f:
        f.write(b'fake video content for testing' * 1000)
    return media_file


@pytest.fixture
def sample_config():
    """Provide sample configuration data."""
    return {
        "youtube": {
            "client_secrets_file": "secrets/youtube_client_secrets.json",
            "credentials_file": "secrets/youtube_credentials.json"
        },
        "facebook": {
            "page_id": "1234567890",
            "access_token": "test_facebook_access_token"
        },
        "vimeo": {
            "access_token": "test_vimeo_access_token"
        },
        "twitter": {
            "api_key": "test_twitter_api_key",
            "api_secret": "test_twitter_api_secret",
            "access_token": "test_twitter_access_token",
            "access_token_secret": "test_twitter_access_token_secret"
        }
    }


# ============================================================================
# Model Fixtures
# ============================================================================

@pytest.fixture
def platform_config():
    """Provide PlatformConfig instance for testing."""
    return PlatformConfig(
        platform_name="youtube",
        enabled=True,
        credentials={
            "client_secrets_file": "secrets/youtube_client_secrets.json",
            "credentials_file": "secrets/youtube_credentials.json"
        },
        metadata={
            "default_privacy": "unlisted",
            "max_file_size": 128 * 1024 * 1024 * 1024  # 128GB
        }
    )


@pytest.fixture
def sample_task_result():
    """Provide sample TaskResult for testing."""
    return TaskResult(
        task_id="medusa_task_12345",
        status=TaskStatus.COMPLETED,
        results={
            "youtube_url": "https://youtube.com/watch?v=abc123",
            "facebook_post_id": "123456789",
            "total_duration": 600.5,
            "file_size": 1024000,
            "processed_platforms": 2
        }
    )


@pytest.fixture
def failed_task_result():
    """Provide failed TaskResult for testing."""
    return TaskResult(
        task_id="medusa_task_failed",
        status=TaskStatus.FAILED,
        error="YouTube API error: Video file too large",
        failed_platform="youtube",
        results={
            "failure_reason": "file_too_large",
            "attempted_platforms": ["youtube"]
        }
    )


@pytest.fixture
def sample_media_metadata():
    """Provide sample MediaMetadata for testing."""
    return MediaMetadata(
        title="Test Video",
        description="A test video file",
        file_size=1024000,
        duration=120,
        privacy="unlisted",
        tags=["test", "video"]
    )


@pytest.fixture
def sample_exceptions():
    """Provide sample exceptions for testing."""
    return {
        "config_error": ConfigError(
            "Configuration file not found",
            config_file="missing_config.json"
        ),
        "upload_error": UploadError(
            "Upload failed",
            platform="youtube",
            media_file="test.mp4"
        ),
        "publish_error": PublishError(
            "Publish failed",
            platform="facebook",
            post_content="Test post"
        )
    }


# ============================================================================
# Factory Fixtures
# ============================================================================

class TaskResultFactory:
    """Factory for creating TaskResult instances."""
    
    @staticmethod
    def create_pending(task_id: str = None) -> TaskResult:
        """Create a pending task result."""
        return TaskResult(
            task_id=task_id or "medusa_task_pending",
            status=TaskStatus.PENDING
        )
    
    @staticmethod
    def create_in_progress(task_id: str = None, progress: float = 0.5) -> TaskResult:
        """Create an in-progress task result."""
        return TaskResult(
            task_id=task_id or "medusa_task_in_progress",
            status=TaskStatus.IN_PROGRESS,
            message=f"Processing... {int(progress * 100)}% complete",
            results={
                "progress": progress,
                "current_platform": "youtube"
            }
        )
    
    @staticmethod
    def create_completed(task_id: str = None) -> TaskResult:
        """Create a completed task result."""
        return TaskResult(
            task_id=task_id or "medusa_task_completed",
            status=TaskStatus.COMPLETED,
            results={
                "youtube_url": "https://youtube.com/watch?v=abc123",
                "facebook_post_id": "123456789",
                "total_duration": 600.5,
                "processed_platforms": 2
            }
        )
    
    @staticmethod
    def create_failed(task_id: str = None, platform: str = "youtube") -> TaskResult:
        """Create a failed task result."""
        return TaskResult(
            task_id=task_id or "medusa_task_failed",
            status=TaskStatus.FAILED,
            error=f"Upload failed on {platform}",
            failed_platform=platform,
            results={
                "failure_reason": "upload_error",
                "attempted_platforms": [platform]
            }
        )


class MediaMetadataFactory:
    """Factory for creating MediaMetadata instances."""
    
    @staticmethod
    def create_video(filename: str = "test.mp4", size: int = 1024000) -> MediaMetadata:
        """Create video metadata."""
        return MediaMetadata(
            title=filename.replace('.mp4', '').replace('_', ' ').title(),
            description=f"Test video: {filename}",
            file_size=size,
            duration=120,
            privacy="unlisted",
            tags=["test"]
        )
    
    @staticmethod
    def create_large_video() -> MediaMetadata:
        """Create large video metadata."""
        return MediaMetadata(
            title="Large Video",
            description="A large test video file",
            file_size=100 * 1024 * 1024,  # 100MB
            duration=1800,  # 30 minutes
            privacy="public",
            tags=["large", "test"]
        )


@pytest.fixture
def task_factory():
    """Provide TaskResultFactory for creating test tasks."""
    return TaskResultFactory


@pytest.fixture
def media_factory():
    """Provide MediaMetadataFactory for creating test media metadata."""
    return MediaMetadataFactory


# ============================================================================
# Mock API Fixtures
# ============================================================================

@pytest.fixture
def mock_youtube_api():
    """Provide mocked YouTube API."""
    return Mock()


@pytest.fixture
def mock_facebook_api():
    """Provide mocked Facebook API."""
    return Mock()


@pytest.fixture
def mock_vimeo_api():
    """Provide mocked Vimeo API."""
    return Mock()


# ============================================================================
# Async Fixtures
# ============================================================================

@pytest.fixture
def async_mock():
    """Provide AsyncMock for async testing."""
    return AsyncMock()


@pytest.fixture
def event_loop():
    """Provide event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def async_test_timeout():
    """Provide timeout for async tests."""
    return 30.0


# ============================================================================
# Test Isolation Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def isolate_tests():
    """Automatically isolate tests from each other."""
    # Store original environment
    original_env = dict(os.environ)
    
    yield
    
    # Restore environment
    os.environ.clear()
    os.environ.update(original_env) 