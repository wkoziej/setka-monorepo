"""
Facebook post publishing implementation.

This module provides FacebookPublisher class for publishing text posts
and link posts to Facebook pages using the Facebook Graph API.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable
from urllib.parse import urlparse

from .base import BasePublisher, PublishResult, PublishProgress
from .facebook_auth import FacebookAuth
from ..models import PlatformConfig
from ..exceptions import (
    PublishError,
    AuthenticationError,
    ValidationError,
    TemplateError,
)

logger = logging.getLogger(__name__)


class FacebookPublisher(BasePublisher):
    """
    Facebook post publisher for publishing text and link posts to Facebook pages.

    This class extends BasePublisher to provide Facebook-specific functionality
    including authentication, post validation, and post publishing with support
    for text posts, link posts, and scheduled posts.
    """

    # Facebook post content limits
    MAX_POST_LENGTH = 63206  # Facebook's maximum post length

    def __init__(self, config: Optional[PlatformConfig] = None):
        """
        Initialize FacebookPublisher with configuration.

        Args:
            config: PlatformConfig containing Facebook API credentials

        Raises:
            ValidationError: If configuration is invalid
        """
        if config is None:
            raise ValidationError("Configuration cannot be None", platform="facebook")

        if not isinstance(config, PlatformConfig):
            raise ValidationError(
                f"Invalid configuration type: expected PlatformConfig, got {type(config).__name__}",
                platform="facebook",
            )

        super().__init__(platform_name="facebook", config=config)
        self._auth: Optional[FacebookAuth] = None

        logger.info("FacebookPublisher initialized")

    async def authenticate(self) -> bool:
        """
        Authenticate with Facebook API.

        Returns:
            True if authentication successful

        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            logger.info("Starting Facebook authentication")

            # Initialize FacebookAuth with configuration
            self._auth = FacebookAuth(self.config.credentials)

            # Test API connection
            if not self._auth.test_connection():
                raise AuthenticationError(
                    "Failed to connect to Facebook API", platform="facebook"
                )

            # Check permissions
            if not self._auth.check_permissions():
                raise AuthenticationError(
                    "Insufficient Facebook permissions for posting", platform="facebook"
                )

            # Verify page access
            if not self._auth.verify_page_access():
                raise AuthenticationError(
                    "Cannot access Facebook page with provided credentials",
                    platform="facebook",
                )

            logger.info("Facebook authentication successful")
            return True

        except Exception as e:
            if isinstance(e, AuthenticationError):
                raise

            logger.error(f"Facebook authentication failed: {e}")
            raise AuthenticationError(
                f"Authentication failed: {e}", platform="facebook"
            ) from e

    def _validate_content(self, content: str, metadata: Dict[str, Any]) -> None:
        """
        Validate post content and metadata.

        Args:
            content: Post content text
            metadata: Post metadata

        Raises:
            ValidationError: If content or metadata is invalid
        """
        # Check content is not empty
        if not content or not content.strip():
            raise ValidationError("Post content cannot be empty", platform="facebook")

        # Check content length
        if len(content) > self.MAX_POST_LENGTH:
            raise ValidationError(
                f"Post content exceeds maximum length of {self.MAX_POST_LENGTH} characters "
                f"(got {len(content)} characters)",
                platform="facebook",
            )

        # Validate link if present
        if metadata.get("type") == "link" and "link" in metadata:
            link = metadata["link"]
            if not self._is_valid_url(link):
                raise ValidationError(
                    f"Invalid URL format: {link}", platform="facebook"
                )

        # Validate scheduled publish time if present
        if "scheduled_publish_time" in metadata:
            scheduled_time = metadata["scheduled_publish_time"]
            if not isinstance(scheduled_time, int) or scheduled_time <= 0:
                raise ValidationError(
                    "scheduled_publish_time must be a positive integer timestamp",
                    platform="facebook",
                )

            # Check if scheduled time is in the future
            current_time = int(datetime.now(timezone.utc).timestamp())
            if scheduled_time <= current_time:
                raise ValidationError(
                    "scheduled_publish_time must be in the future", platform="facebook"
                )

    def _is_valid_url(self, url: str) -> bool:
        """
        Check if URL is valid.

        Args:
            url: URL to validate

        Returns:
            True if URL is valid, False otherwise
        """
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    async def _publish_post(
        self,
        content: str,
        metadata: Dict[str, Any],
        progress_callback: Optional[Callable[[PublishProgress], None]] = None,
    ) -> PublishResult:
        """
        Publish post to Facebook.

        Args:
            content: Post content text
            metadata: Post metadata
            progress_callback: Optional progress callback

        Returns:
            PublishResult with publishing results

        Raises:
            AuthenticationError: If not authenticated
            PublishError: If publishing fails
        """
        if self._auth is None:
            raise AuthenticationError(
                "Not authenticated with Facebook API", platform="facebook"
            )

        try:
            # Report progress - preparing
            if progress_callback:
                progress_callback(
                    PublishProgress(
                        step="Preparing post",
                        current_step=1,
                        total_steps=3,
                        message="Processing content and metadata",
                    )
                )

            # Process template variables
            processed_content = self._process_template(content, metadata)

            # Format post data for Facebook API
            post_data = self._format_post_data(processed_content, metadata)

            # Report progress - publishing
            if progress_callback:
                progress_callback(
                    PublishProgress(
                        step="Publishing to Facebook",
                        current_step=2,
                        total_steps=3,
                        message="Sending post to Facebook API",
                    )
                )

            # Make API request to publish post
            page_id = self.config.credentials["page_id"]
            endpoint = f"/{page_id}/feed"

            response = self._auth._make_api_request(
                method="POST", endpoint=endpoint, data=post_data
            )

            # Extract post ID from response
            post_id = self._extract_post_id(response)
            post_url = self._build_post_url(post_id)

            # Report progress - completed
            if progress_callback:
                progress_callback(
                    PublishProgress(
                        step="Post published",
                        current_step=3,
                        total_steps=3,
                        message=f"Post published successfully: {post_id}",
                        status="completed",
                    )
                )

            # Create result with metadata
            result_metadata = dict(metadata)
            if "link" in metadata:
                result_metadata["link"] = metadata["link"]
            if "scheduled_publish_time" in metadata:
                result_metadata["scheduled_publish_time"] = metadata[
                    "scheduled_publish_time"
                ]

            logger.info(f"Facebook post published successfully: {post_id}")

            return PublishResult(
                platform="facebook",
                post_id=post_id,
                success=True,
                post_url=post_url,
                metadata=result_metadata,
            )

        except TemplateError:
            # Re-raise template errors as-is
            raise
        except Exception as e:
            logger.error(f"Failed to publish Facebook post: {e}")
            raise PublishError(
                f"Failed to publish post to Facebook: {e}", platform="facebook"
            ) from e

    def _format_post_data(
        self, content: str, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Format post data for Facebook API.

        Args:
            content: Processed post content
            metadata: Post metadata

        Returns:
            Dictionary formatted for Facebook API
        """
        post_data = {"message": content}

        # Add link information if present
        if metadata.get("type") == "link" and "link" in metadata:
            post_data["link"] = metadata["link"]

            # Add optional link metadata
            if "name" in metadata:
                post_data["name"] = metadata["name"]
            if "description" in metadata:
                post_data["description"] = metadata["description"]

        # Add scheduling information if present
        if "scheduled_publish_time" in metadata:
            post_data["scheduled_publish_time"] = metadata["scheduled_publish_time"]
            post_data["published"] = "false"  # Required for scheduled posts

        return post_data

    def _extract_post_id(self, response: Dict[str, Any]) -> str:
        """
        Extract post ID from Facebook API response.

        Args:
            response: Facebook API response

        Returns:
            Post ID string

        Raises:
            PublishError: If post ID cannot be extracted
        """
        # Try to get explicit post_id first
        if "post_id" in response:
            return response["post_id"]

        # Fallback to extracting from compound ID
        if "id" in response:
            compound_id = response["id"]
            # Facebook returns IDs in format: page_id_post_id
            if "_" in compound_id:
                return compound_id.split("_", 1)[1]
            return compound_id

        raise PublishError(
            "Invalid response format: no post ID found", platform="facebook"
        )

    def _build_post_url(self, post_id: str) -> str:
        """
        Build Facebook post URL.

        Args:
            post_id: Post ID

        Returns:
            Complete post URL
        """
        page_id = self.config.credentials["page_id"]
        return f"https://facebook.com/{page_id}/posts/{post_id}"

    async def cleanup(self) -> None:
        """Clean up resources."""
        # No specific cleanup needed for Facebook publisher
        logger.debug("FacebookPublisher cleanup completed")

    def health_check(self) -> bool:
        """
        Check if Facebook publisher is healthy.

        Returns:
            True if healthy, False otherwise
        """
        if self._auth is None:
            return False

        try:
            return self._auth.test_connection()
        except Exception:
            return False

    def __repr__(self) -> str:
        """Return string representation of FacebookPublisher."""
        return f"FacebookPublisher(platform=facebook, authenticated={self._auth is not None})"
