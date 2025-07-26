# ABOUTME: Custom exception classes for Medusa library operations
# ABOUTME: Defines hierarchical exception structure for upload, publish, and config errors

from typing import Optional, Dict, Any, List
import traceback
from datetime import datetime


class MedusaError(Exception):
    """Base exception for all Medusa-related errors.

    Provides common attributes and functionality for all Medusa exceptions.
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        platform: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__.upper()
        self.platform = platform
        self.context = context or {}
        self.original_error = original_error
        self.timestamp = datetime.now()

        # Preserve original traceback if available
        if original_error and hasattr(original_error, "__traceback__"):
            self.__cause__ = original_error

    def get_error_details(self) -> Dict[str, Any]:
        """Get comprehensive error details for logging and debugging."""
        details = {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "platform": self.platform,
            "context": self.context,
        }

        if self.original_error:
            details["original_error"] = {
                "type": self.original_error.__class__.__name__,
                "message": str(self.original_error),
                "traceback": "".join(
                    traceback.format_exception(
                        type(self.original_error),
                        self.original_error,
                        self.original_error.__traceback__,
                    )
                )
                if hasattr(self.original_error, "__traceback__")
                and self.original_error.__traceback__ is not None
                else None,
            }

        return details

    def get_user_message(self) -> str:
        """Get user-friendly error message without technical details."""
        if self.platform:
            return f"{self.platform.title()} error: {self.message}"
        return self.message

    def __str__(self) -> str:
        """String representation including platform and error code."""
        parts = []
        if self.platform:
            parts.append(f"[{self.platform.upper()}]")
        if self.error_code and self.error_code != "MEDUSAERROR":
            parts.append(f"({self.error_code})")
        parts.append(self.message)
        return " ".join(parts)


class ConfigError(MedusaError):
    """Raised when configuration is invalid or missing."""

    def __init__(
        self,
        message: str,
        config_file: Optional[str] = None,
        missing_fields: Optional[List[str]] = None,
        invalid_fields: Optional[List[str]] = None,
        original_error: Optional[Exception] = None,
    ):
        context = {}
        if config_file:
            context["config_file"] = config_file
        if missing_fields:
            context["missing_fields"] = missing_fields
        if invalid_fields:
            context["invalid_fields"] = invalid_fields

        super().__init__(
            message=message,
            error_code="CONFIG_ERROR",
            context=context,
            original_error=original_error,
        )

        self.config_file = config_file
        self.missing_fields = missing_fields or []
        self.invalid_fields = invalid_fields or []


# Alias for backward compatibility and clearer naming
ConfigurationError = ConfigError


class UploadError(MedusaError):
    """Raised when media upload fails."""

    def __init__(
        self,
        message: str,
        platform: str,
        media_file: Optional[str] = None,
        upload_id: Optional[str] = None,
        progress: Optional[float] = None,
        original_error: Optional[Exception] = None,
    ):
        context = {}
        if media_file:
            context["media_file"] = media_file
        if upload_id:
            context["upload_id"] = upload_id
        if progress is not None:
            context["progress"] = progress

        super().__init__(
            message=message,
            error_code="UPLOAD_ERROR",
            platform=platform,
            context=context,
            original_error=original_error,
        )

        self.media_file = media_file
        self.upload_id = upload_id
        self.progress = progress


class PublishError(MedusaError):
    """Raised when social media publishing fails."""

    def __init__(
        self,
        message: str,
        platform: str,
        post_content: Optional[str] = None,
        post_id: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        context = {}
        if post_content:
            context["post_content"] = (
                post_content[:100] + "..." if len(post_content) > 100 else post_content
            )
        if post_id:
            context["post_id"] = post_id

        super().__init__(
            message=message,
            error_code="PUBLISH_ERROR",
            platform=platform,
            context=context,
            original_error=original_error,
        )

        self.post_content = post_content
        self.post_id = post_id


class TaskError(MedusaError):
    """Raised when task processing fails."""

    def __init__(
        self,
        message: str,
        task_id: Optional[str] = None,
        task_status: Optional[str] = None,
        failed_platform: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        context = {}
        if task_id:
            context["task_id"] = task_id
        if task_status:
            context["task_status"] = task_status
        if failed_platform:
            context["failed_platform"] = failed_platform

        super().__init__(
            message=message,
            error_code="TASK_ERROR",
            platform=failed_platform,
            context=context,
            original_error=original_error,
        )

        self.task_id = task_id
        self.task_status = task_status
        self.failed_platform = failed_platform


class AuthenticationError(MedusaError):
    """Raised when authentication fails for a platform."""

    def __init__(
        self,
        message: str,
        platform: str,
        auth_type: Optional[str] = None,
        token_expired: bool = False,
        original_error: Optional[Exception] = None,
    ):
        context = {"auth_type": auth_type, "token_expired": token_expired}

        super().__init__(
            message=message,
            error_code="AUTH_ERROR",
            platform=platform,
            context=context,
            original_error=original_error,
        )

        self.auth_type = auth_type
        self.token_expired = token_expired


class ValidationError(MedusaError):
    """Raised when data validation fails."""

    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        field_value: Optional[Any] = None,
        validation_rule: Optional[str] = None,
        platform: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        context = {}
        if field_name:
            context["field_name"] = field_name
        if field_value is not None:
            context["field_value"] = str(field_value)[:100]  # Truncate long values
        if validation_rule:
            context["validation_rule"] = validation_rule

        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            platform=platform,
            context=context,
            original_error=original_error,
        )

        self.field_name = field_name
        self.field_value = field_value
        self.validation_rule = validation_rule


class RateLimitError(MedusaError):
    """Raised when API rate limits are exceeded."""

    def __init__(
        self,
        message: str,
        platform: str,
        retry_after: Optional[int] = None,
        quota_exceeded: bool = False,
        original_error: Optional[Exception] = None,
    ):
        context = {"retry_after": retry_after, "quota_exceeded": quota_exceeded}

        super().__init__(
            message=message,
            error_code="RATE_LIMIT_ERROR",
            platform=platform,
            context=context,
            original_error=original_error,
        )

        self.retry_after = retry_after
        self.quota_exceeded = quota_exceeded


class NetworkError(MedusaError):
    """Raised when network operations fail."""

    def __init__(
        self,
        message: str,
        platform: Optional[str] = None,
        status_code: Optional[int] = None,
        endpoint: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        context = {}
        if status_code:
            context["status_code"] = status_code
        if endpoint:
            context["endpoint"] = endpoint

        super().__init__(
            message=message,
            error_code="NETWORK_ERROR",
            platform=platform,
            context=context,
            original_error=original_error,
        )

        self.status_code = status_code
        self.endpoint = endpoint


class TemplateError(MedusaError):
    """Raised when template processing fails."""

    def __init__(
        self,
        message: str,
        template: Optional[str] = None,
        variable_name: Optional[str] = None,
        platform: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        context = {}
        if template:
            context["template"] = (
                template[:100] + "..." if len(template) > 100 else template
            )
        if variable_name:
            context["variable_name"] = variable_name

        super().__init__(
            message=message,
            error_code="TEMPLATE_ERROR",
            platform=platform,
            context=context,
            original_error=original_error,
        )

        self.template = template
        self.variable_name = variable_name


# Exception translation utilities
def translate_api_error(
    original_error: Exception, platform: str, operation: str = "unknown"
) -> MedusaError:
    """Translate platform-specific API errors to Medusa exceptions.

    Args:
        original_error: The original exception from the API
        platform: The platform where the error occurred
        operation: The operation being performed when the error occurred

    Returns:
        Appropriate MedusaError subclass
    """
    error_msg = str(original_error)
    error_type = type(original_error).__name__

    # Common HTTP error patterns
    if "401" in error_msg or "unauthorized" in error_msg.lower():
        return AuthenticationError(
            f"Authentication failed during {operation}",
            platform=platform,
            original_error=original_error,
        )

    if "403" in error_msg or "forbidden" in error_msg.lower():
        return AuthenticationError(
            f"Access forbidden during {operation} - check permissions",
            platform=platform,
            original_error=original_error,
        )

    if "429" in error_msg or "rate limit" in error_msg.lower():
        return RateLimitError(
            f"Rate limit exceeded during {operation}",
            platform=platform,
            original_error=original_error,
        )

    if (
        any(code in error_msg for code in ["400", "422"])
        or "validation" in error_msg.lower()
    ):
        return ValidationError(
            f"Validation failed during {operation}: {error_msg}",
            platform=platform,
            original_error=original_error,
        )

    if any(code in error_msg for code in ["500", "502", "503", "504"]):
        return NetworkError(
            f"Network error during {operation}: {error_msg}",
            platform=platform,
            original_error=original_error,
        )

    # Check for network-related errors by exception type
    if isinstance(original_error, (ConnectionError, TimeoutError)):
        return NetworkError(
            f"Network error during {operation}: {error_msg}",
            platform=platform,
            original_error=original_error,
        )

    # Default to appropriate error type based on operation
    if operation in ["upload", "uploading"]:
        return UploadError(
            f"Upload failed: {error_msg}",
            platform=platform,
            original_error=original_error,
        )
    elif operation in ["publish", "publishing", "post"]:
        return PublishError(
            f"Publishing failed: {error_msg}",
            platform=platform,
            original_error=original_error,
        )
    else:
        return MedusaError(
            f"{operation.title()} failed: {error_msg}",
            platform=platform,
            original_error=original_error,
        )


def create_error_chain(*errors: Exception) -> MedusaError:
    """Create a chained error from multiple exceptions.

    Args:
        *errors: Multiple exceptions to chain together

    Returns:
        MedusaError with all errors in the chain
    """
    if not errors:
        return MedusaError("Unknown error occurred")

    primary_error = errors[0]

    # If primary error is already a MedusaError, use it as base
    if isinstance(primary_error, MedusaError):
        base_error = primary_error
    else:
        base_error = MedusaError(str(primary_error), original_error=primary_error)

    # Add additional errors to context
    if len(errors) > 1:
        base_error.context["error_chain"] = [
            {"type": type(err).__name__, "message": str(err)} for err in errors[1:]
        ]

    return base_error
