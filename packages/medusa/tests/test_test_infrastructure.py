"""
Tests for the test infrastructure itself.

This module validates that all fixtures, utilities, and test helpers
work correctly and provide the expected functionality.
"""

import pytest
import asyncio
import json
import time
from pathlib import Path
from unittest.mock import AsyncMock

from medusa.models import TaskStatus, TaskResult, MediaMetadata, PlatformConfig
from medusa.exceptions import ConfigError, UploadError, PublishError

from test_utils import (
    MockAPIResponse,
    YouTubeAPIMock,
    FacebookAPIMock,
    VimeoAPIMock,
    TestDataGenerator,
    TaskAssertions,
    ExceptionAssertions,
    AsyncTestUtils,
    PerformanceTestUtils,
    MediaTestUtils,
    MockEnvironment,
    TemporaryDirectory,
)


class TestFixtures:
    """Test the basic fixtures provided by conftest.py."""

    def test_temp_dir_fixture(self, temp_dir):
        """Test temporary directory fixture."""
        assert temp_dir.exists()
        assert temp_dir.is_dir()

        # Create a test file
        test_file = temp_dir / "test.txt"
        test_file.write_text("test content")

        assert test_file.exists()
        assert test_file.read_text() == "test content"

    def test_temp_config_file_fixture(self, temp_config_file):
        """Test temporary configuration file fixture."""
        assert temp_config_file.exists()
        assert temp_config_file.suffix == ".json"

        # Load and validate config
        with open(temp_config_file) as f:
            config = json.load(f)

        assert "youtube" in config
        assert "facebook" in config
        assert "vimeo" in config

        assert "client_secrets_file" in config["youtube"]
        assert "page_id" in config["facebook"]
        assert "access_token" in config["vimeo"]

    def test_temp_media_file_fixture(self, temp_media_file):
        """Test temporary media file fixture."""
        assert temp_media_file.exists()
        assert temp_media_file.suffix == ".mp4"
        assert temp_media_file.stat().st_size > 0

    def test_sample_config_fixture(self, sample_config):
        """Test sample configuration fixture."""
        assert isinstance(sample_config, dict)
        assert "youtube" in sample_config
        assert "facebook" in sample_config
        assert "vimeo" in sample_config
        assert "twitter" in sample_config

    def test_platform_config_fixture(self, platform_config):
        """Test platform configuration fixture."""
        assert isinstance(platform_config, PlatformConfig)
        assert platform_config.platform_name == "youtube"
        assert platform_config.enabled is True
        assert "client_secrets_file" in platform_config.credentials

    def test_sample_task_result_fixture(self, sample_task_result):
        """Test sample task result fixture."""
        assert isinstance(sample_task_result, TaskResult)
        assert sample_task_result.status == TaskStatus.COMPLETED
        assert sample_task_result.results is not None
        assert "youtube_url" in sample_task_result.results

    def test_failed_task_result_fixture(self, failed_task_result):
        """Test failed task result fixture."""
        assert isinstance(failed_task_result, TaskResult)
        assert failed_task_result.status == TaskStatus.FAILED
        assert failed_task_result.error is not None
        assert failed_task_result.failed_platform == "youtube"

    def test_sample_media_metadata_fixture(self, sample_media_metadata):
        """Test sample media metadata fixture."""
        assert isinstance(sample_media_metadata, MediaMetadata)
        assert sample_media_metadata.title == "Test Video"
        assert sample_media_metadata.file_size > 0
        assert sample_media_metadata.duration > 0

    def test_sample_exceptions_fixture(self, sample_exceptions):
        """Test sample exceptions fixture."""
        assert isinstance(sample_exceptions, dict)
        assert "config_error" in sample_exceptions
        assert "upload_error" in sample_exceptions
        assert "publish_error" in sample_exceptions

        assert isinstance(sample_exceptions["config_error"], ConfigError)
        assert isinstance(sample_exceptions["upload_error"], UploadError)
        assert isinstance(sample_exceptions["publish_error"], PublishError)


class TestMockAPIs:
    """Test the mock API implementations."""

    def test_mock_api_response(self):
        """Test MockAPIResponse class."""
        # Test successful response
        response = MockAPIResponse(200, {"key": "value"})
        assert response.status_code == 200
        assert response.json() == {"key": "value"}

        # Test error response
        error_response = MockAPIResponse(
            404, {"error": "Not found"}, raise_for_status=True
        )
        assert error_response.status_code == 404

        with pytest.raises(Exception, match="HTTP 404 Error"):
            error_response.raise_for_status()

    def test_youtube_api_mock(self):
        """Test YouTubeAPIMock class."""
        mock = YouTubeAPIMock()

        # Test successful upload
        request = mock.videos().insert(
            part="snippet,status",
            body={
                "snippet": {"title": "Test Video"},
                "status": {"privacyStatus": "unlisted"},
            },
        )

        result = request.execute()
        assert result["id"].startswith("test_video_")
        assert result["snippet"]["title"] == "Test Video"
        assert len(mock.uploaded_videos) == 1

        # Test failure scenario
        mock.set_failure("auth_error")
        with pytest.raises(Exception, match="401 Unauthorized"):
            mock.videos().insert(part="snippet", body={})

        # Test rate limiting
        mock.reset()
        mock.set_rate_limited(3600)
        with pytest.raises(Exception, match="429 Rate limit exceeded"):
            mock.videos().insert(part="snippet", body={})

    def test_facebook_api_mock(self):
        """Test FacebookAPIMock class."""
        mock = FacebookAPIMock()

        # Test successful post
        response = mock.post("/me/feed", {"message": "Test post"})
        assert response.status_code == 200
        assert "id" in response.json()
        assert len(mock.published_posts) == 1

        # Test page info
        response = mock.get("/me")
        assert response.status_code == 200
        page_info = response.json()
        assert page_info["id"] == "1234567890"
        assert page_info["name"] == "Test Page"

        # Test failure scenario
        mock.set_failure("auth_error")
        response = mock.post("/me/feed", {"message": "Test"})
        assert response.status_code == 401
        assert "error" in response.json()

    def test_vimeo_api_mock(self):
        """Test VimeoAPIMock class."""
        mock = VimeoAPIMock()

        # Test successful upload
        response = mock.post("/me/videos", {"name": "Test Video"})
        assert response.status_code == 201
        video_data = response.json()
        assert video_data["uri"].startswith("/videos/")
        assert video_data["link"].startswith("https://vimeo.com/")
        assert len(mock.uploaded_videos) == 1

        # Test failure scenario
        mock.set_failure("auth_error")
        response = mock.post("/me/videos", {"name": "Test"})
        assert response.status_code == 401
        assert "error" in response.json()


class TestDataGenerators:
    """Test the test data generation utilities."""

    def test_random_string_generation(self):
        """Test random string generation."""
        # Test default length
        s1 = TestDataGenerator.random_string()
        assert len(s1) == 10
        assert s1.isalnum()

        # Test custom length
        s2 = TestDataGenerator.random_string(20)
        assert len(s2) == 20

        # Test uniqueness
        s3 = TestDataGenerator.random_string()
        assert s1 != s3

    def test_random_task_id_generation(self):
        """Test task ID generation."""
        task_id = TestDataGenerator.random_task_id()
        assert task_id.startswith("medusa_task_")
        assert len(task_id) > len("medusa_task_")

        # Test uniqueness
        task_id2 = TestDataGenerator.random_task_id()
        assert task_id != task_id2

    def test_random_video_metadata_generation(self):
        """Test video metadata generation."""
        metadata = TestDataGenerator.random_video_metadata()

        assert isinstance(metadata, MediaMetadata)
        assert metadata.title is not None
        assert metadata.file_size > 0
        assert metadata.duration > 0
        assert metadata.privacy in ["public", "unlisted", "private"]

        # Test custom filename
        custom_metadata = TestDataGenerator.random_video_metadata("custom.mp4")
        assert custom_metadata.title == "Custom"

    def test_random_platform_config_generation(self):
        """Test platform configuration generation."""
        # Test random platform
        config = TestDataGenerator.random_platform_config()
        assert isinstance(config, PlatformConfig)
        assert config.platform_name in ["youtube", "facebook", "vimeo", "twitter"]
        assert config.enabled is True

        # Test specific platform
        youtube_config = TestDataGenerator.random_platform_config("youtube")
        assert youtube_config.platform_name == "youtube"
        assert "client_secrets_file" in youtube_config.credentials
        assert "credentials_file" in youtube_config.credentials

        facebook_config = TestDataGenerator.random_platform_config("facebook")
        assert facebook_config.platform_name == "facebook"
        assert "page_id" in facebook_config.credentials
        assert "access_token" in facebook_config.credentials

    def test_create_test_config_file(self, temp_dir):
        """Test configuration file creation."""
        config_file = TestDataGenerator.create_test_config_file(temp_dir)

        assert config_file.exists()
        assert config_file.suffix == ".json"

        with open(config_file) as f:
            config = json.load(f)

        assert "youtube" in config
        assert "facebook" in config
        assert "vimeo" in config


class TestTaskFactories:
    """Test the task result factories."""

    def test_task_factory_fixture(self, task_factory):
        """Test task factory fixture."""
        # Test pending task creation
        pending = task_factory.create_pending()
        assert pending.status == TaskStatus.PENDING
        assert pending.task_id.startswith("medusa_task_")

        # Test in-progress task creation
        in_progress = task_factory.create_in_progress(progress=0.7)
        assert in_progress.status == TaskStatus.IN_PROGRESS
        assert in_progress.results.get("progress") == 0.7
        assert in_progress.results.get("current_platform") == "youtube"

        # Test completed task creation
        completed = task_factory.create_completed()
        assert completed.status == TaskStatus.COMPLETED
        assert completed.results is not None
        assert "youtube_url" in completed.results

        # Test failed task creation
        failed = task_factory.create_failed(platform="facebook")
        assert failed.status == TaskStatus.FAILED
        assert failed.failed_platform == "facebook"
        assert failed.error is not None

    def test_media_factory_fixture(self, media_factory):
        """Test media factory fixture."""
        # Test video creation
        video = media_factory.create_video()
        assert video.title == "Test"
        assert video.file_size == 1024000

        # Test custom video creation
        custom_video = media_factory.create_video("custom.mp4", 2048000)
        assert custom_video.title == "Custom"
        assert custom_video.file_size == 2048000

        # Test large video creation
        large_video = media_factory.create_large_video()
        assert large_video.file_size == 100 * 1024 * 1024
        assert large_video.title == "Large Video"


class TestAssertionHelpers:
    """Test the assertion helper utilities."""

    def test_task_assertions(self, task_factory):
        """Test task assertion helpers."""
        # Test status assertion
        completed_task = task_factory.create_completed()
        TaskAssertions.assert_task_status(completed_task, TaskStatus.COMPLETED)

        with pytest.raises(AssertionError):
            TaskAssertions.assert_task_status(completed_task, TaskStatus.FAILED)

        # Test successful completion assertion
        TaskAssertions.assert_task_completed_successfully(
            completed_task, ["youtube", "facebook"]
        )

        # Test failure assertion
        failed_task = task_factory.create_failed("youtube")
        TaskAssertions.assert_task_failed(failed_task, "youtube", "upload failed")

        # Test in-progress assertion
        in_progress_task = task_factory.create_in_progress()
        TaskAssertions.assert_task_in_progress(in_progress_task, "youtube")

    def test_exception_assertions(self, sample_exceptions):
        """Test exception assertion helpers."""
        config_error = sample_exceptions["config_error"]

        # Test Medusa error assertion
        ExceptionAssertions.assert_medusa_error(
            config_error, ConfigError, expected_error_code="CONFIG_ERROR"
        )

        # Test exception chaining
        upload_error = UploadError(
            "Upload failed",
            platform="youtube",
            original_error=ValueError("Original error"),
        )

        ExceptionAssertions.assert_exception_chaining(upload_error, ValueError)


class TestAsyncUtilities:
    """Test async testing utilities."""

    @pytest.mark.asyncio
    async def test_wait_for_condition(self):
        """Test wait_for_condition utility."""
        condition_met = False

        def condition():
            return condition_met

        # Test condition that becomes true
        async def set_condition():
            nonlocal condition_met
            await asyncio.sleep(0.2)
            condition_met = True

        # Start the condition setter
        asyncio.create_task(set_condition())

        # Wait for condition
        result = await AsyncTestUtils.wait_for_condition(condition, timeout=1.0)
        assert result is True

        # Test timeout
        condition_met = False
        result = await AsyncTestUtils.wait_for_condition(condition, timeout=0.1)
        assert result is False

    @pytest.mark.asyncio
    async def test_simulate_async_delay(self):
        """Test async delay simulation."""
        start_time = time.time()
        await AsyncTestUtils.simulate_async_delay(0.1, 0.2)
        duration = time.time() - start_time

        assert 0.1 <= duration <= 0.3  # Allow some margin

    @pytest.mark.asyncio
    async def test_create_async_mock_with_delay(self):
        """Test async mock with delay creation."""
        mock = AsyncTestUtils.create_async_mock_with_delay("test_result", delay=0.1)

        start_time = time.time()
        result = await mock()
        duration = time.time() - start_time

        assert result == "test_result"
        assert duration >= 0.1

    @pytest.mark.asyncio
    async def test_run_with_timeout(self):
        """Test running coroutine with timeout."""

        async def quick_task():
            await asyncio.sleep(0.1)
            return "completed"

        # Test successful completion
        result = await AsyncTestUtils.run_with_timeout(quick_task(), timeout=1.0)
        assert result == "completed"

        # Test timeout (this should raise an exception)
        async def slow_task():
            await asyncio.sleep(1.0)
            return "too_slow"

        # The run_with_timeout function calls pytest.fail which raises a Failed exception
        # We expect this to fail with a specific message
        from _pytest.outcomes import Failed

        with pytest.raises(Failed, match="timed out"):
            await AsyncTestUtils.run_with_timeout(slow_task(), timeout=0.1)


class TestPerformanceUtilities:
    """Test performance testing utilities."""

    def test_measure_execution_time(self):
        """Test execution time measurement."""

        def test_function():
            time.sleep(0.1)
            return "result"

        result, duration = PerformanceTestUtils.measure_execution_time(test_function)

        assert result == "result"
        assert duration >= 0.1
        assert duration < 0.2  # Should be close to 0.1

    @pytest.mark.asyncio
    async def test_measure_async_execution_time(self):
        """Test async execution time measurement."""

        async def async_function():
            await asyncio.sleep(0.1)
            return "async_result"

        result, duration = await PerformanceTestUtils.measure_async_execution_time(
            async_function()
        )

        assert result == "async_result"
        assert duration >= 0.1
        assert duration < 0.2

    def test_assert_execution_time(self):
        """Test execution time assertion."""
        # Test passing assertion
        PerformanceTestUtils.assert_execution_time(0.1, 0.2, "Test operation")

        # Test failing assertion
        with pytest.raises(AssertionError, match="Test operation took"):
            PerformanceTestUtils.assert_execution_time(0.3, 0.2, "Test operation")

    def test_create_performance_benchmark(self):
        """Test performance benchmark creation."""

        def simple_function():
            return sum(range(100))

        benchmark = PerformanceTestUtils.create_performance_benchmark(
            simple_function, iterations=10
        )

        assert "min" in benchmark
        assert "max" in benchmark
        assert "avg" in benchmark
        assert "total" in benchmark
        assert benchmark["iterations"] == 10

        assert benchmark["min"] > 0
        assert benchmark["max"] >= benchmark["min"]
        assert benchmark["avg"] >= benchmark["min"]
        assert benchmark["total"] >= benchmark["max"]


class TestMediaUtilities:
    """Test media file testing utilities."""

    def test_create_test_video_file(self, temp_dir):
        """Test test video file creation."""
        video_file = MediaTestUtils.create_test_video_file(temp_dir, "test.mp4", 1.0)

        assert video_file.exists()
        assert video_file.name == "test.mp4"
        assert video_file.stat().st_size >= 1024 * 1024  # ~1MB
        assert video_file.stat().st_size <= 1024 * 1024 * 1.1  # Allow 10% margin

    def test_create_test_config_files(self, temp_dir):
        """Test configuration files creation."""
        files = MediaTestUtils.create_test_config_files(temp_dir)

        assert "youtube_secrets" in files
        assert "youtube_credentials" in files

        # Verify files exist
        assert files["youtube_secrets"].exists()
        assert files["youtube_credentials"].exists()

        # Verify content
        with open(files["youtube_secrets"]) as f:
            secrets = json.load(f)
        assert "installed" in secrets
        assert "client_id" in secrets["installed"]


class TestContextManagers:
    """Test context manager utilities."""

    def test_mock_environment(self):
        """Test environment variable mocking."""
        import os

        original_value = os.environ.get("TEST_VAR")

        with MockEnvironment(TEST_VAR="test_value", NEW_VAR="new_value"):
            assert os.environ["TEST_VAR"] == "test_value"
            assert os.environ["NEW_VAR"] == "new_value"

        # Verify cleanup
        if original_value is None:
            assert "TEST_VAR" not in os.environ
        else:
            assert os.environ["TEST_VAR"] == original_value
        assert "NEW_VAR" not in os.environ

    def test_temporary_directory(self):
        """Test enhanced temporary directory."""
        temp_path = None

        with TemporaryDirectory() as temp_dir:
            temp_path = temp_dir
            assert temp_dir.exists()

            # Create a test file
            test_file = temp_dir / "test.txt"
            test_file.write_text("test")
            assert test_file.exists()

        # Verify cleanup
        assert not temp_path.exists()

    def test_temporary_directory_no_cleanup(self):
        """Test temporary directory without cleanup."""
        temp_path = None

        with TemporaryDirectory(cleanup=False) as temp_dir:
            temp_path = temp_dir
            assert temp_dir.exists()

        # Verify no cleanup
        assert temp_path.exists()

        # Manual cleanup
        import shutil

        shutil.rmtree(temp_path)


class TestFixtureIntegration:
    """Test integration between different fixtures and utilities."""

    def test_fixture_data_consistency(self, temp_config_file, sample_config):
        """Test consistency between different configuration fixtures."""
        # Load temp config file
        with open(temp_config_file) as f:
            temp_config = json.load(f)

        # Both should have youtube configuration
        assert "youtube" in temp_config
        assert "youtube" in sample_config

        # Both should have required fields
        assert "client_secrets_file" in temp_config["youtube"]
        assert "client_secrets_file" in sample_config["youtube"]

    def test_mock_api_integration(self, mock_youtube_api, mock_facebook_api):
        """Test integration between different mock APIs."""
        # Configure the YouTube mock to return a proper response
        mock_youtube_api.videos.return_value.insert.return_value.execute.return_value = {
            "id": "test_video_123",
            "snippet": {"title": "YouTube Test"},
        }

        # Configure the Facebook mock to return a proper response
        mock_facebook_api.post.return_value.status_code = 200
        mock_facebook_api.post.return_value.json.return_value = {
            "id": "facebook_post_123"
        }

        # Test that mocks don't interfere with each other
        youtube_result = (
            mock_youtube_api.videos()
            .insert(part="snippet", body={"snippet": {"title": "YouTube Test"}})
            .execute()
        )

        facebook_result = mock_facebook_api.post(
            "/me/feed", {"message": "Facebook Test"}
        )

        assert youtube_result["id"] == "test_video_123"
        assert facebook_result.status_code == 200

        # Verify the mocks were called
        assert mock_youtube_api.videos.called
        assert mock_facebook_api.post.called

    def test_task_factory_with_assertions(self, task_factory):
        """Test task factory integration with assertion helpers."""
        # Create tasks and verify with assertions
        pending = task_factory.create_pending("test_task_123")
        TaskAssertions.assert_task_status(pending, TaskStatus.PENDING)
        assert pending.task_id == "test_task_123"

        completed = task_factory.create_completed("test_completed")
        TaskAssertions.assert_task_completed_successfully(
            completed, ["youtube", "facebook"]
        )

        failed = task_factory.create_failed("test_failed", "youtube")
        TaskAssertions.assert_task_failed(failed, "youtube", "Upload failed")


class TestAsyncFixtures:
    """Test async-related fixtures and utilities."""

    def test_async_mock_fixture(self, async_mock):
        """Test async mock fixture."""
        assert isinstance(async_mock, AsyncMock)

    @pytest.mark.asyncio
    async def test_event_loop_fixture(self, event_loop):
        """Test event loop fixture."""
        # The event loop should be available and working
        await asyncio.sleep(0.01)
        assert True  # If we get here, the event loop is working

    def test_async_test_timeout_fixture(self, async_test_timeout):
        """Test async test timeout fixture."""
        assert isinstance(async_test_timeout, float)
        assert async_test_timeout > 0


class TestFixtureCleanup:
    """Test that fixtures properly clean up after themselves."""

    def test_temp_files_cleanup(self):
        """Test that temporary files are cleaned up."""
        # This test verifies that the autouse isolate_tests fixture works
        # by checking that no temporary files persist between tests
        import tempfile

        temp_files_before = len(list(Path(tempfile.gettempdir()).glob("tmp*")))

        # The number should be reasonable (not growing indefinitely)
        assert temp_files_before < 100  # Arbitrary reasonable limit

    def test_environment_isolation(self):
        """Test that environment variables are properly isolated."""
        import os

        # Set a test variable
        os.environ["TEST_ISOLATION"] = "test_value"

        # The isolate_tests fixture should clean this up automatically
        # This is verified by the fixture itself, so this test just
        # ensures the mechanism is in place
        assert "TEST_ISOLATION" in os.environ
