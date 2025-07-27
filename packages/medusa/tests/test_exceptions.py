"""
Tests for Medusa exception hierarchy and error handling.

This module tests all custom exceptions, error chaining, context preservation,
and exception translation utilities.
"""

from datetime import datetime

from medusa.exceptions import (
    MedusaError,
    ConfigError,
    ConfigurationError,
    UploadError,
    PublishError,
    TaskError,
    AuthenticationError,
    ValidationError,
    RateLimitError,
    NetworkError,
    translate_api_error,
    create_error_chain,
)


class TestMedusaError:
    """Tests for the base MedusaError class."""

    def test_basic_error_creation(self):
        """Test basic error creation with minimal parameters."""
        error = MedusaError("Test error message")

        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.error_code == "MEDUSAERROR"
        assert error.platform is None
        assert error.context == {}
        assert error.original_error is None
        assert isinstance(error.timestamp, datetime)

    def test_error_with_all_parameters(self):
        """Test error creation with all parameters."""
        original_error = ValueError("Original error")
        context = {"key": "value", "number": 42}

        error = MedusaError(
            message="Test error",
            error_code="CUSTOM_CODE",
            platform="youtube",
            context=context,
            original_error=original_error,
        )

        assert error.message == "Test error"
        assert error.error_code == "CUSTOM_CODE"
        assert error.platform == "youtube"
        assert error.context == context
        assert error.original_error == original_error
        assert error.__cause__ == original_error

    def test_string_representation(self):
        """Test string representation with different combinations."""
        # Basic error
        error1 = MedusaError("Basic error")
        assert str(error1) == "Basic error"

        # Error with platform
        error2 = MedusaError("Platform error", platform="youtube")
        assert str(error2) == "[YOUTUBE] Platform error"

        # Error with custom code
        error3 = MedusaError("Custom error", error_code="CUSTOM")
        assert str(error3) == "(CUSTOM) Custom error"

        # Error with platform and custom code
        error4 = MedusaError("Full error", platform="facebook", error_code="FB_ERROR")
        assert str(error4) == "[FACEBOOK] (FB_ERROR) Full error"

    def test_get_user_message(self):
        """Test user-friendly message generation."""
        # Without platform
        error1 = MedusaError("Basic error")
        assert error1.get_user_message() == "Basic error"

        # With platform
        error2 = MedusaError("Platform error", platform="youtube")
        assert error2.get_user_message() == "Youtube error: Platform error"

    def test_get_error_details(self):
        """Test comprehensive error details generation."""
        original_error = ValueError("Original error")
        context = {"key": "value"}

        error = MedusaError(
            message="Test error",
            error_code="TEST_CODE",
            platform="youtube",
            context=context,
            original_error=original_error,
        )

        details = error.get_error_details()

        assert details["error_type"] == "MedusaError"
        assert details["error_code"] == "TEST_CODE"
        assert details["message"] == "Test error"
        assert details["platform"] == "youtube"
        assert details["context"] == context
        assert "timestamp" in details
        assert "original_error" in details
        assert details["original_error"]["type"] == "ValueError"
        assert details["original_error"]["message"] == "Original error"

    def test_error_details_without_original_error(self):
        """Test error details when no original error is present."""
        error = MedusaError("Test error")
        details = error.get_error_details()

        assert "original_error" not in details or details["original_error"] is None


class TestConfigError:
    """Tests for ConfigError exception."""

    def test_basic_config_error(self):
        """Test basic config error creation."""
        error = ConfigError("Config file not found")

        assert error.message == "Config file not found"
        assert error.error_code == "CONFIG_ERROR"
        assert error.config_file is None
        assert error.missing_fields == []
        assert error.invalid_fields == []

    def test_config_error_with_details(self):
        """Test config error with all details."""
        error = ConfigError(
            message="Invalid configuration",
            config_file="config.json",
            missing_fields=["youtube.client_id", "facebook.token"],
            invalid_fields=["youtube.privacy"],
            original_error=FileNotFoundError("File not found"),
        )

        assert error.config_file == "config.json"
        assert error.missing_fields == ["youtube.client_id", "facebook.token"]
        assert error.invalid_fields == ["youtube.privacy"]
        assert error.context["config_file"] == "config.json"
        assert error.context["missing_fields"] == [
            "youtube.client_id",
            "facebook.token",
        ]
        assert error.context["invalid_fields"] == ["youtube.privacy"]

    def test_configuration_error_alias(self):
        """Test that ConfigurationError is an alias for ConfigError."""
        assert ConfigurationError is ConfigError


class TestUploadError:
    """Tests for UploadError exception."""

    def test_basic_upload_error(self):
        """Test basic upload error creation."""
        error = UploadError("Upload failed", platform="youtube")

        assert error.message == "Upload failed"
        assert error.platform == "youtube"
        assert error.error_code == "UPLOAD_ERROR"
        assert error.media_file is None
        assert error.upload_id is None
        assert error.progress is None

    def test_upload_error_with_details(self):
        """Test upload error with all details."""
        error = UploadError(
            message="Upload failed at 50%",
            platform="youtube",
            media_file="video.mp4",
            upload_id="upload_123",
            progress=0.5,
            original_error=ConnectionError("Network error"),
        )

        assert error.media_file == "video.mp4"
        assert error.upload_id == "upload_123"
        assert error.progress == 0.5
        assert error.context["media_file"] == "video.mp4"
        assert error.context["upload_id"] == "upload_123"
        assert error.context["progress"] == 0.5


class TestPublishError:
    """Tests for PublishError exception."""

    def test_basic_publish_error(self):
        """Test basic publish error creation."""
        error = PublishError("Publish failed", platform="facebook")

        assert error.message == "Publish failed"
        assert error.platform == "facebook"
        assert error.error_code == "PUBLISH_ERROR"
        assert error.post_content is None
        assert error.post_id is None

    def test_publish_error_with_details(self):
        """Test publish error with all details."""
        long_content = "x" * 200  # Long content to test truncation

        error = PublishError(
            message="Publish failed",
            platform="facebook",
            post_content=long_content,
            post_id="post_123",
            original_error=ValueError("Invalid post"),
        )

        assert error.post_content == long_content
        assert error.post_id == "post_123"
        # Check truncation in context
        assert len(error.context["post_content"]) == 103  # 100 + "..."
        assert error.context["post_content"].endswith("...")
        assert error.context["post_id"] == "post_123"

    def test_publish_error_short_content(self):
        """Test publish error with short content (no truncation)."""
        short_content = "Short post"

        error = PublishError(
            message="Publish failed", platform="facebook", post_content=short_content
        )

        assert error.context["post_content"] == short_content


class TestTaskError:
    """Tests for TaskError exception."""

    def test_basic_task_error(self):
        """Test basic task error creation."""
        error = TaskError("Task failed")

        assert error.message == "Task failed"
        assert error.error_code == "TASK_ERROR"
        assert error.task_id is None
        assert error.task_status is None
        assert error.failed_platform is None

    def test_task_error_with_details(self):
        """Test task error with all details."""
        error = TaskError(
            message="Task failed during upload",
            task_id="task_123",
            task_status="uploading",
            failed_platform="youtube",
            original_error=TimeoutError("Upload timeout"),
        )

        assert error.task_id == "task_123"
        assert error.task_status == "uploading"
        assert error.failed_platform == "youtube"
        assert error.platform == "youtube"  # Should be set from failed_platform
        assert error.context["task_id"] == "task_123"
        assert error.context["task_status"] == "uploading"
        assert error.context["failed_platform"] == "youtube"


class TestAuthenticationError:
    """Tests for AuthenticationError exception."""

    def test_basic_auth_error(self):
        """Test basic authentication error creation."""
        error = AuthenticationError("Auth failed", platform="youtube")

        assert error.message == "Auth failed"
        assert error.platform == "youtube"
        assert error.error_code == "AUTH_ERROR"
        assert error.auth_type is None
        assert error.token_expired is False

    def test_auth_error_with_details(self):
        """Test authentication error with all details."""
        error = AuthenticationError(
            message="Token expired",
            platform="youtube",
            auth_type="oauth2",
            token_expired=True,
            original_error=Exception("Invalid token"),
        )

        assert error.auth_type == "oauth2"
        assert error.token_expired is True
        assert error.context["auth_type"] == "oauth2"
        assert error.context["token_expired"] is True


class TestValidationError:
    """Tests for ValidationError exception."""

    def test_basic_validation_error(self):
        """Test basic validation error creation."""
        error = ValidationError("Validation failed")

        assert error.message == "Validation failed"
        assert error.error_code == "VALIDATION_ERROR"
        assert error.field_name is None
        assert error.field_value is None
        assert error.validation_rule is None

    def test_validation_error_with_details(self):
        """Test validation error with all details."""
        long_value = "x" * 200  # Long value to test truncation

        error = ValidationError(
            message="Invalid field value",
            field_name="title",
            field_value=long_value,
            validation_rule="max_length_100",
            platform="youtube",
            original_error=ValueError("Too long"),
        )

        assert error.field_name == "title"
        assert error.field_value == long_value
        assert error.validation_rule == "max_length_100"
        assert error.platform == "youtube"
        # Check truncation in context
        assert len(error.context["field_value"]) == 100
        assert error.context["validation_rule"] == "max_length_100"


class TestRateLimitError:
    """Tests for RateLimitError exception."""

    def test_basic_rate_limit_error(self):
        """Test basic rate limit error creation."""
        error = RateLimitError("Rate limit exceeded", platform="youtube")

        assert error.message == "Rate limit exceeded"
        assert error.platform == "youtube"
        assert error.error_code == "RATE_LIMIT_ERROR"
        assert error.retry_after is None
        assert error.quota_exceeded is False

    def test_rate_limit_error_with_details(self):
        """Test rate limit error with all details."""
        error = RateLimitError(
            message="Quota exceeded",
            platform="youtube",
            retry_after=3600,
            quota_exceeded=True,
            original_error=Exception("Quota exceeded"),
        )

        assert error.retry_after == 3600
        assert error.quota_exceeded is True
        assert error.context["retry_after"] == 3600
        assert error.context["quota_exceeded"] is True


class TestNetworkError:
    """Tests for NetworkError exception."""

    def test_basic_network_error(self):
        """Test basic network error creation."""
        error = NetworkError("Network error")

        assert error.message == "Network error"
        assert error.error_code == "NETWORK_ERROR"
        assert error.platform is None
        assert error.status_code is None
        assert error.endpoint is None

    def test_network_error_with_details(self):
        """Test network error with all details."""
        error = NetworkError(
            message="HTTP 500 error",
            platform="youtube",
            status_code=500,
            endpoint="/upload",
            original_error=ConnectionError("Connection failed"),
        )

        assert error.platform == "youtube"
        assert error.status_code == 500
        assert error.endpoint == "/upload"
        assert error.context["status_code"] == 500
        assert error.context["endpoint"] == "/upload"


class TestTranslateApiError:
    """Tests for the translate_api_error utility function."""

    def test_translate_401_error(self):
        """Test translation of 401 authentication errors."""
        original_error = Exception("401 Unauthorized")

        translated = translate_api_error(original_error, "youtube", "upload")

        assert isinstance(translated, AuthenticationError)
        assert translated.platform == "youtube"
        assert "Authentication failed during upload" in translated.message
        assert translated.original_error == original_error

    def test_translate_403_error(self):
        """Test translation of 403 forbidden errors."""
        original_error = Exception("403 Forbidden")

        translated = translate_api_error(original_error, "facebook", "publish")

        assert isinstance(translated, AuthenticationError)
        assert translated.platform == "facebook"
        assert "Access forbidden during publish" in translated.message

    def test_translate_429_error(self):
        """Test translation of 429 rate limit errors."""
        original_error = Exception("429 Too Many Requests")

        translated = translate_api_error(original_error, "youtube", "upload")

        assert isinstance(translated, RateLimitError)
        assert translated.platform == "youtube"
        assert "Rate limit exceeded during upload" in translated.message

    def test_translate_400_error(self):
        """Test translation of 400 validation errors."""
        original_error = Exception("400 Bad Request - validation failed")

        translated = translate_api_error(original_error, "youtube", "upload")

        assert isinstance(translated, ValidationError)
        assert translated.platform == "youtube"
        assert "Validation failed during upload" in translated.message

    def test_translate_500_error(self):
        """Test translation of 500 network errors."""
        original_error = Exception("500 Internal Server Error")

        translated = translate_api_error(original_error, "youtube", "upload")

        assert isinstance(translated, NetworkError)
        assert translated.platform == "youtube"
        assert "Network error during upload" in translated.message

    def test_translate_upload_operation(self):
        """Test translation for upload operations."""
        original_error = Exception("Unknown upload error")

        translated = translate_api_error(original_error, "youtube", "upload")

        assert isinstance(translated, UploadError)
        assert translated.platform == "youtube"
        assert "Upload failed" in translated.message

    def test_translate_publish_operation(self):
        """Test translation for publish operations."""
        original_error = Exception("Unknown publish error")

        translated = translate_api_error(original_error, "facebook", "publish")

        assert isinstance(translated, PublishError)
        assert translated.platform == "facebook"
        assert "Publishing failed" in translated.message

    def test_translate_unknown_operation(self):
        """Test translation for unknown operations."""
        original_error = Exception("Unknown error")

        translated = translate_api_error(original_error, "platform", "unknown")

        assert isinstance(translated, MedusaError)
        assert translated.platform == "platform"
        assert "Unknown failed" in translated.message

    def test_translate_case_insensitive(self):
        """Test that error translation is case insensitive."""
        original_error = Exception("UNAUTHORIZED access")

        translated = translate_api_error(original_error, "youtube", "upload")

        assert isinstance(translated, AuthenticationError)

    def test_translate_rate_limit_text(self):
        """Test translation of rate limit errors by text."""
        original_error = Exception("Rate limit exceeded, try again later")

        translated = translate_api_error(original_error, "youtube", "upload")

        assert isinstance(translated, RateLimitError)


class TestCreateErrorChain:
    """Tests for the create_error_chain utility function."""

    def test_create_chain_no_errors(self):
        """Test error chain creation with no errors."""
        chained = create_error_chain()

        assert isinstance(chained, MedusaError)
        assert chained.message == "Unknown error occurred"

    def test_create_chain_single_error(self):
        """Test error chain creation with single error."""
        original_error = ValueError("Test error")

        chained = create_error_chain(original_error)

        assert isinstance(chained, MedusaError)
        assert chained.message == "Test error"
        assert chained.original_error == original_error

    def test_create_chain_medusa_error_primary(self):
        """Test error chain creation with MedusaError as primary."""
        primary_error = UploadError("Upload failed", platform="youtube")
        secondary_error = ConnectionError("Connection lost")

        chained = create_error_chain(primary_error, secondary_error)

        assert isinstance(chained, UploadError)
        assert chained.platform == "youtube"
        assert "error_chain" in chained.context
        assert len(chained.context["error_chain"]) == 1
        assert chained.context["error_chain"][0]["type"] == "ConnectionError"
        assert chained.context["error_chain"][0]["message"] == "Connection lost"

    def test_create_chain_multiple_errors(self):
        """Test error chain creation with multiple errors."""
        error1 = ValueError("First error")
        error2 = ConnectionError("Second error")
        error3 = TimeoutError("Third error")

        chained = create_error_chain(error1, error2, error3)

        assert isinstance(chained, MedusaError)
        assert chained.message == "First error"
        assert chained.original_error == error1
        assert len(chained.context["error_chain"]) == 2

        # Check error chain details
        chain = chained.context["error_chain"]
        assert chain[0]["type"] == "ConnectionError"
        assert chain[0]["message"] == "Second error"
        assert chain[1]["type"] == "TimeoutError"
        assert chain[1]["message"] == "Third error"


class TestErrorChaining:
    """Tests for proper error chaining and traceback preservation."""

    def test_original_error_chaining(self):
        """Test that original errors are properly chained."""
        try:
            raise ValueError("Original error")
        except ValueError as e:
            medusa_error = MedusaError("Medusa error", original_error=e)

            assert medusa_error.__cause__ == e
            assert medusa_error.original_error == e

    def test_traceback_preservation(self):
        """Test that tracebacks are preserved in error details."""
        try:
            raise ValueError("Original error")
        except ValueError as e:
            medusa_error = MedusaError("Medusa error", original_error=e)
            details = medusa_error.get_error_details()

            assert "original_error" in details
            assert details["original_error"]["traceback"] is not None
            assert (
                "ValueError: Original error" in details["original_error"]["traceback"]
            )

    def test_no_traceback_when_not_available(self):
        """Test handling when traceback is not available."""
        original_error = ValueError("Original error")
        # Remove traceback
        original_error.__traceback__ = None

        medusa_error = MedusaError("Medusa error", original_error=original_error)
        details = medusa_error.get_error_details()

        assert details["original_error"]["traceback"] is None


class TestErrorContextHandling:
    """Tests for error context handling and preservation."""

    def test_context_preservation(self):
        """Test that context is properly preserved."""
        context = {
            "file_path": "/path/to/file.mp4",
            "file_size": 1024000,
            "platform_settings": {"privacy": "private"},
        }

        error = MedusaError("Test error", context=context)

        assert error.context == context

        details = error.get_error_details()
        assert details["context"] == context

    def test_context_merging_in_subclasses(self):
        """Test that subclasses properly merge their context."""
        error = UploadError(
            message="Upload failed",
            platform="youtube",
            media_file="video.mp4",
            progress=0.75,
        )

        assert "media_file" in error.context
        assert "progress" in error.context
        assert error.context["media_file"] == "video.mp4"
        assert error.context["progress"] == 0.75

    def test_empty_context_handling(self):
        """Test handling of empty or None context."""
        error1 = MedusaError("Test error", context=None)
        error2 = MedusaError("Test error", context={})

        assert error1.context == {}
        assert error2.context == {}


# Integration tests
class TestErrorIntegration:
    """Integration tests for error handling scenarios."""

    def test_realistic_upload_error_scenario(self):
        """Test a realistic upload error scenario."""
        # Simulate a network error during upload
        network_error = ConnectionError("Connection timed out")

        # Translate to upload error
        upload_error = translate_api_error(network_error, "youtube", "upload")

        # Create task error from upload error
        task_error = TaskError(
            message="Task failed during upload phase",
            task_id="task_123",
            task_status="uploading",
            failed_platform="youtube",
            original_error=upload_error,
        )

        # Verify error hierarchy
        assert isinstance(task_error, TaskError)
        assert task_error.failed_platform == "youtube"
        assert task_error.original_error == upload_error
        assert isinstance(upload_error, NetworkError)
        assert upload_error.original_error == network_error

        # Verify error details
        details = task_error.get_error_details()
        assert details["error_type"] == "TaskError"
        assert details["platform"] == "youtube"
        assert "original_error" in details

    def test_realistic_auth_error_scenario(self):
        """Test a realistic authentication error scenario."""
        # Simulate expired token
        api_error = Exception("401 - Token has expired")

        # Translate to auth error
        auth_error = translate_api_error(api_error, "facebook", "publish")

        # Verify translation
        assert isinstance(auth_error, AuthenticationError)
        assert auth_error.platform == "facebook"
        assert "Authentication failed during publish" in auth_error.message

        # Test user-friendly message
        user_msg = auth_error.get_user_message()
        assert "Facebook error:" in user_msg

    def test_error_chain_complex_scenario(self):
        """Test complex error chaining scenario."""
        # Multiple failures in sequence
        network_error = ConnectionError("Network unreachable")
        timeout_error = TimeoutError("Request timeout")
        auth_error = AuthenticationError("Token refresh failed", platform="youtube")

        # Create error chain
        chained_error = create_error_chain(auth_error, network_error, timeout_error)

        # Verify chain structure
        assert isinstance(chained_error, AuthenticationError)
        assert chained_error.platform == "youtube"
        assert len(chained_error.context["error_chain"]) == 2

        # Verify chain contents
        chain = chained_error.context["error_chain"]
        assert chain[0]["type"] == "ConnectionError"
        assert chain[1]["type"] == "TimeoutError"
