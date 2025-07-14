"""
Test utilities and helpers for Medusa library tests.

This module provides:
- API mocking utilities
- Test data generators
- Assertion helpers
- Async testing utilities
- Performance testing helpers
"""

import asyncio
import json
import time
import random
import string
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable, Union
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import pytest

from medusa.models import TaskStatus, TaskResult, MediaMetadata, PlatformConfig
from medusa.exceptions import (
    MedusaError, ConfigError, UploadError, PublishError,
    AuthenticationError, ValidationError, RateLimitError, NetworkError
)


# ============================================================================
# API Mocking Utilities
# ============================================================================

class MockAPIResponse:
    """Mock API response for testing external service calls."""
    
    def __init__(self, status_code: int = 200, json_data: Dict[str, Any] = None, 
                 text: str = "", headers: Dict[str, str] = None, 
                 raise_for_status: bool = False):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text
        self.headers = headers or {}
        self._raise_for_status = raise_for_status
    
    def json(self):
        """Return JSON data."""
        return self._json_data
    
    def raise_for_status(self):
        """Raise exception if status indicates error."""
        if self._raise_for_status and self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code} Error")


class YouTubeAPIMock:
    """Comprehensive YouTube API mock for testing."""
    
    def __init__(self):
        self.uploaded_videos = []
        self.upload_progress = {}
        self.should_fail = False
        self.failure_reason = None
        self.rate_limited = False
        self.quota_exceeded = False
    
    def reset(self):
        """Reset mock state."""
        self.uploaded_videos.clear()
        self.upload_progress.clear()
        self.should_fail = False
        self.failure_reason = None
        self.rate_limited = False
        self.quota_exceeded = False
    
    def set_failure(self, reason: str = "upload_failed"):
        """Configure mock to fail."""
        self.should_fail = True
        self.failure_reason = reason
    
    def set_rate_limited(self, retry_after: int = 3600):
        """Configure mock to return rate limit error."""
        self.rate_limited = True
        self.retry_after = retry_after
    
    def videos(self):
        """Mock videos resource."""
        return self
    
    def insert(self, part: str = None, body: Dict[str, Any] = None, 
               media_body=None):
        """Mock video insert operation."""
        if self.should_fail:
            if self.failure_reason == "auth_error":
                raise Exception("401 Unauthorized")
            elif self.failure_reason == "quota_exceeded":
                raise Exception("403 Quota exceeded")
            else:
                raise Exception(f"Upload failed: {self.failure_reason}")
        
        if self.rate_limited:
            raise Exception(f"429 Rate limit exceeded. Retry after {self.retry_after} seconds")
        
        # Generate mock video ID
        video_id = f"test_video_{len(self.uploaded_videos) + 1}"
        
        video_data = {
            "id": video_id,
            "snippet": body.get("snippet", {}),
            "status": body.get("status", {"privacyStatus": "unlisted"})
        }
        
        self.uploaded_videos.append(video_data)
        
        # Mock the insert request object
        mock_request = Mock()
        mock_request.execute.return_value = video_data
        mock_request.next_chunk.return_value = (None, None)  # Upload complete
        
        return mock_request


class FacebookAPIMock:
    """Comprehensive Facebook API mock for testing."""
    
    def __init__(self):
        self.published_posts = []
        self.should_fail = False
        self.failure_reason = None
        self.page_info = {
            "id": "1234567890",
            "name": "Test Page",
            "access_token": "test_page_token"
        }
    
    def reset(self):
        """Reset mock state."""
        self.published_posts.clear()
        self.should_fail = False
        self.failure_reason = None
    
    def set_failure(self, reason: str = "publish_failed"):
        """Configure mock to fail."""
        self.should_fail = True
        self.failure_reason = reason
    
    def post(self, url: str, data: Dict[str, Any] = None, **kwargs):
        """Mock POST request."""
        if self.should_fail:
            if self.failure_reason == "auth_error":
                return MockAPIResponse(401, {"error": {"message": "Invalid access token"}}, raise_for_status=True)
            elif self.failure_reason == "rate_limited":
                return MockAPIResponse(429, {"error": {"message": "Rate limit exceeded"}}, raise_for_status=True)
            else:
                return MockAPIResponse(400, {"error": {"message": f"Post failed: {self.failure_reason}"}}, raise_for_status=True)
        
        # Generate mock post ID
        post_id = f"{self.page_info['id']}_{len(self.published_posts) + 1}"
        
        post_data = {
            "id": post_id,
            "message": data.get("message", ""),
            "created_time": datetime.now().isoformat()
        }
        
        self.published_posts.append(post_data)
        
        return MockAPIResponse(200, {"id": post_id})
    
    def get(self, url: str, params: Dict[str, Any] = None, **kwargs):
        """Mock GET request."""
        if "me" in url:
            return MockAPIResponse(200, self.page_info)
        
        return MockAPIResponse(200, {})


class VimeoAPIMock:
    """Comprehensive Vimeo API mock for testing."""
    
    def __init__(self):
        self.uploaded_videos = []
        self.should_fail = False
        self.failure_reason = None
    
    def reset(self):
        """Reset mock state."""
        self.uploaded_videos.clear()
        self.should_fail = False
        self.failure_reason = None
    
    def set_failure(self, reason: str = "upload_failed"):
        """Configure mock to fail."""
        self.should_fail = True
        self.failure_reason = reason
    
    def post(self, url: str, data: Dict[str, Any] = None, **kwargs):
        """Mock POST request for video upload."""
        if self.should_fail:
            if self.failure_reason == "auth_error":
                return MockAPIResponse(401, {"error": "Invalid access token"}, raise_for_status=True)
            else:
                return MockAPIResponse(400, {"error": f"Upload failed: {self.failure_reason}"}, raise_for_status=True)
        
        # Generate mock video data
        video_id = len(self.uploaded_videos) + 1
        video_data = {
            "uri": f"/videos/{video_id}",
            "link": f"https://vimeo.com/{video_id}",
            "upload": {
                "upload_link": f"https://upload.vimeo.com/upload_{video_id}"
            }
        }
        
        self.uploaded_videos.append(video_data)
        
        return MockAPIResponse(201, video_data)


# ============================================================================
# Test Data Generators
# ============================================================================

class TestDataGenerator:
    """Generate realistic test data for various scenarios."""
    
    @staticmethod
    def random_string(length: int = 10) -> str:
        """Generate random string of specified length."""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    @staticmethod
    def random_task_id() -> str:
        """Generate random task ID."""
        return f"medusa_task_{TestDataGenerator.random_string(8)}"
    
    @staticmethod
    def random_video_metadata(filename: str = None) -> MediaMetadata:
        """Generate random video metadata."""
        if not filename:
            filename = f"video_{TestDataGenerator.random_string(6)}.mp4"
        
        title = filename.replace('.mp4', '').replace('_', ' ').title()
        return MediaMetadata(
            title=title,
            description=f"Test video: {title}",
            file_size=random.randint(1024000, 1000000000),  # 1MB to 1GB
            duration=random.randint(30, 7200),  # 30 seconds to 2 hours
            privacy=random.choice(["public", "unlisted", "private"]),
            tags=[f"tag{i}" for i in range(random.randint(1, 5))]
        )
    
    @staticmethod
    def random_platform_config(platform: str = None) -> PlatformConfig:
        """Generate random platform configuration."""
        if not platform:
            platform = random.choice(["youtube", "facebook", "vimeo", "twitter"])
        
        credentials = {}
        metadata = {}
        
        if platform == "youtube":
            credentials = {
                "client_secrets_file": f"secrets/{platform}_secrets.json",
                "credentials_file": f"secrets/{platform}_creds.json"
            }
            metadata = {
                "default_privacy": random.choice(["public", "unlisted", "private"]),
                "max_file_size": random.choice([2, 8, 128]) * 1024 * 1024 * 1024
            }
        elif platform == "facebook":
            credentials = {
                "page_id": str(random.randint(1000000000, 9999999999)),
                "access_token": f"fb_token_{TestDataGenerator.random_string(32)}"
            }
        elif platform == "vimeo":
            credentials = {
                "access_token": f"vimeo_token_{TestDataGenerator.random_string(32)}"
            }
        
        return PlatformConfig(
            platform_name=platform,
            enabled=True,
            credentials=credentials,
            metadata=metadata
        )
    
    @staticmethod
    def create_test_config_file(temp_dir: Path, platforms: List[str] = None) -> Path:
        """Create a test configuration file."""
        if not platforms:
            platforms = ["youtube", "facebook", "vimeo"]
        
        config_data = {}
        for platform in platforms:
            platform_config = TestDataGenerator.random_platform_config(platform)
            config_data[platform] = {
                **platform_config.credentials,
                **platform_config.metadata
            }
        
        config_file = temp_dir / "test_config.json"
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        return config_file


# ============================================================================
# Assertion Helpers
# ============================================================================

class TaskAssertions:
    """Helper methods for asserting task properties."""
    
    @staticmethod
    def assert_task_status(task: TaskResult, expected_status: TaskStatus):
        """Assert task has expected status."""
        assert task.status == expected_status, f"Expected status {expected_status}, got {task.status}"
    
    @staticmethod
    def assert_task_completed_successfully(task: TaskResult, expected_platforms: List[str] = None):
        """Assert task completed successfully."""
        TaskAssertions.assert_task_status(task, TaskStatus.COMPLETED)
        assert task.error is None, f"Expected no error, got: {task.error}"
        assert task.results is not None, "Expected results for completed task"
        
        if expected_platforms:
            for platform in expected_platforms:
                assert any(platform in key for key in task.results.keys()), f"Missing results for platform: {platform}"
    
    @staticmethod
    def assert_task_failed(task: TaskResult, expected_platform: str = None, expected_error_type: str = None):
        """Assert task failed as expected."""
        TaskAssertions.assert_task_status(task, TaskStatus.FAILED)
        assert task.error is not None, "Expected error for failed task"
        
        if expected_platform:
            assert task.failed_platform == expected_platform, f"Expected failure on {expected_platform}, got {task.failed_platform}"
        
        if expected_error_type:
            assert expected_error_type.lower() in task.error.lower(), f"Expected error type {expected_error_type} in error: {task.error}"
    
    @staticmethod
    def assert_task_in_progress(task: TaskResult, expected_platform: str = None):
        """Assert task is in progress."""
        TaskAssertions.assert_task_status(task, TaskStatus.IN_PROGRESS)
        
        if expected_platform:
            current_platform = task.results.get("current_platform")
            assert current_platform == expected_platform, f"Expected current platform {expected_platform}, got {current_platform}"


class ExceptionAssertions:
    """Helper methods for asserting exception properties."""
    
    @staticmethod
    def assert_medusa_error(exception: Exception, expected_type: type, 
                          expected_platform: str = None, expected_error_code: str = None):
        """Assert exception is a Medusa error with expected properties."""
        assert isinstance(exception, expected_type), f"Expected {expected_type.__name__}, got {type(exception).__name__}"
        assert isinstance(exception, MedusaError), f"Expected MedusaError subclass, got {type(exception).__name__}"
        
        if expected_platform:
            assert exception.platform == expected_platform, f"Expected platform {expected_platform}, got {exception.platform}"
        
        if expected_error_code:
            assert exception.error_code == expected_error_code, f"Expected error code {expected_error_code}, got {exception.error_code}"
    
    @staticmethod
    def assert_exception_chaining(exception: MedusaError, expected_original_type: type = None):
        """Assert exception has proper chaining."""
        assert exception.original_error is not None, "Expected original error in exception chain"
        
        if expected_original_type:
            assert isinstance(exception.original_error, expected_original_type), \
                f"Expected original error type {expected_original_type.__name__}, got {type(exception.original_error).__name__}"


# ============================================================================
# Async Testing Utilities
# ============================================================================

class AsyncTestUtils:
    """Utilities for testing async code."""
    
    @staticmethod
    async def wait_for_condition(condition: Callable[[], bool], timeout: float = 5.0, 
                                interval: float = 0.1) -> bool:
        """Wait for a condition to become true."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if condition():
                return True
            await asyncio.sleep(interval)
        
        return False
    
    @staticmethod
    async def simulate_async_delay(min_delay: float = 0.1, max_delay: float = 1.0):
        """Simulate realistic async operation delay."""
        delay = random.uniform(min_delay, max_delay)
        await asyncio.sleep(delay)
    
    @staticmethod
    def create_async_mock_with_delay(return_value: Any = None, delay: float = 0.1) -> AsyncMock:
        """Create async mock that simulates delay."""
        async def delayed_return(*args, **kwargs):
            await asyncio.sleep(delay)
            return return_value
        
        mock = AsyncMock()
        mock.side_effect = delayed_return
        return mock
    
    @staticmethod
    async def run_with_timeout(coro, timeout: float = 30.0):
        """Run coroutine with timeout."""
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            pytest.fail(f"Async operation timed out after {timeout} seconds")


# ============================================================================
# Performance Testing Helpers
# ============================================================================

class PerformanceTestUtils:
    """Utilities for performance testing."""
    
    @staticmethod
    def measure_execution_time(func: Callable, *args, **kwargs) -> tuple:
        """Measure function execution time."""
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        return result, end_time - start_time
    
    @staticmethod
    async def measure_async_execution_time(coro) -> tuple:
        """Measure async function execution time."""
        start_time = time.time()
        result = await coro
        end_time = time.time()
        
        return result, end_time - start_time
    
    @staticmethod
    def assert_execution_time(duration: float, max_duration: float, 
                            operation_name: str = "Operation"):
        """Assert execution time is within acceptable limits."""
        assert duration <= max_duration, \
            f"{operation_name} took {duration:.3f}s, expected <= {max_duration}s"
    
    @staticmethod
    def create_performance_benchmark(func: Callable, iterations: int = 100) -> Dict[str, float]:
        """Create performance benchmark for a function."""
        times = []
        
        for _ in range(iterations):
            _, duration = PerformanceTestUtils.measure_execution_time(func)
            times.append(duration)
        
        return {
            "min": min(times),
            "max": max(times),
            "avg": sum(times) / len(times),
            "total": sum(times),
            "iterations": iterations
        }


# ============================================================================
# File and Media Testing Utilities
# ============================================================================

class MediaTestUtils:
    """Utilities for testing media file operations."""
    
    @staticmethod
    def create_test_video_file(temp_dir: Path, filename: str = "test.mp4", 
                              size_mb: float = 1.0) -> Path:
        """Create a test video file with specified size."""
        video_file = temp_dir / filename
        size_bytes = int(size_mb * 1024 * 1024)
        
        with open(video_file, 'wb') as f:
            # Create file with random data to simulate video content
            chunk_size = 8192
            written = 0
            
            while written < size_bytes:
                remaining = min(chunk_size, size_bytes - written)
                chunk = bytes(random.getrandbits(8) for _ in range(remaining))
                f.write(chunk)
                written += remaining
        
        return video_file
    
    @staticmethod
    def create_test_config_files(temp_dir: Path) -> Dict[str, Path]:
        """Create test configuration files."""
        config_dir = temp_dir / "config"
        secrets_dir = config_dir / "secrets"
        
        config_dir.mkdir(exist_ok=True)
        secrets_dir.mkdir(exist_ok=True)
        
        files = {}
        
        # YouTube client secrets
        youtube_secrets = {
            "installed": {
                "client_id": "test_client_id.apps.googleusercontent.com",
                "client_secret": "test_client_secret",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"]
            }
        }
        
        youtube_secrets_file = secrets_dir / "youtube_client_secrets.json"
        with open(youtube_secrets_file, 'w') as f:
            json.dump(youtube_secrets, f, indent=2)
        files['youtube_secrets'] = youtube_secrets_file
        
        # YouTube credentials
        youtube_creds = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "token_type": "Bearer",
            "expires_in": 3600
        }
        
        youtube_creds_file = secrets_dir / "youtube_credentials.json"
        with open(youtube_creds_file, 'w') as f:
            json.dump(youtube_creds, f, indent=2)
        files['youtube_credentials'] = youtube_creds_file
        
        return files


# ============================================================================
# Context Managers for Testing
# ============================================================================

class MockEnvironment:
    """Context manager for mocking environment variables."""
    
    def __init__(self, **env_vars):
        self.env_vars = env_vars
        self.original_env = {}
    
    def __enter__(self):
        import os
        for key, value in self.env_vars.items():
            self.original_env[key] = os.environ.get(key)
            os.environ[key] = str(value)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        import os
        for key in self.env_vars:
            if self.original_env[key] is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = self.original_env[key]


class TemporaryDirectory:
    """Enhanced temporary directory context manager."""
    
    def __init__(self, cleanup: bool = True):
        self.cleanup = cleanup
        self.temp_dir = None
    
    def __enter__(self) -> Path:
        import tempfile
        self.temp_dir = Path(tempfile.mkdtemp())
        return self.temp_dir
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.cleanup and self.temp_dir and self.temp_dir.exists():
            import shutil
            shutil.rmtree(self.temp_dir)


# ============================================================================
# Test Fixtures and Decorators
# ============================================================================

def requires_async_support(func):
    """Decorator to mark tests that require async support."""
    func._requires_async = True
    return func


def slow_test(func):
    """Decorator to mark slow tests."""
    return pytest.mark.slow(func)


def integration_test(func):
    """Decorator to mark integration tests."""
    return pytest.mark.integration(func)


def mock_api_test(func):
    """Decorator to mark tests that use mocked APIs."""
    return pytest.mark.mock_api(func) 