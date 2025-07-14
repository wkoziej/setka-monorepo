"""
YouTube video uploader implementation.
Handles video uploads to YouTube with progress tracking and error handling.
"""

import os
import logging
import asyncio
import random
import time
from typing import Optional, Callable, Dict, Any
from datetime import datetime, timezone

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
import socket

from .base import BaseUploader, UploadProgress, UploadResult
from .youtube_auth import YouTubeAuth
from ..models import MediaMetadata, PlatformConfig
from ..exceptions import (
    UploadError,
    AuthenticationError,
    ValidationError,
    NetworkError,
    RateLimitError,
    MedusaError
)


class YouTubeUploader(BaseUploader):
    """
    YouTube video uploader implementation.
    
    Provides functionality for uploading videos to YouTube with:
    - OAuth authentication via YouTubeAuth
    - Progress tracking for large uploads
    - Resumable upload support
    - Comprehensive error handling
    - Metadata validation and conversion
    """
    
    # YouTube API constants
    YOUTUBE_API_SERVICE_NAME = "youtube"
    YOUTUBE_API_VERSION = "v3"
    
    # File size limits (YouTube allows up to 256GB)
    MAX_FILE_SIZE = 256 * 1024 * 1024 * 1024  # 256GB in bytes
    
    # YouTube category mappings
    CATEGORY_MAPPINGS = {
        "film": "1",
        "autos": "2", 
        "music": "10",
        "pets": "15",
        "sports": "17",
        "travel": "19",
        "gaming": "20",
        "people": "22",
        "comedy": "23",
        "entertainment": "24",
        "news": "25",
        "howto": "26",
        "education": "27",
        "science": "28",
        "nonprofits": "29"
    }
    
    # Default category (People & Blogs)
    DEFAULT_CATEGORY_ID = "22"
    
    # Retryable HTTP status codes
    RETRYABLE_STATUS_CODES = [500, 502, 503, 504]
    
    # Maximum retry attempts for resumable uploads
    MAX_RESUMABLE_RETRIES = 10
    
    def __init__(self, platform_name: str = "youtube", config: Optional[PlatformConfig] = None):
        """
        Initialize YouTube uploader.
        
        Args:
            platform_name: Platform name (default: "youtube")
            config: Platform configuration
        """
        super().__init__(platform_name, config)
        
        # Initialize YouTube authentication manager
        self.auth_manager = YouTubeAuth(config)
        
        # YouTube API service instance
        self.service = None
        
        self.logger = logging.getLogger(f"medusa.uploader.{self.platform_name}")
    
    async def authenticate(self) -> bool:
        """
        Authenticate with YouTube API.
        
        Returns:
            True if authentication successful, False otherwise
            
        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            # Authenticate using the auth manager
            auth_result = await self.auth_manager.authenticate()
            
            if not auth_result:
                self.logger.warning("YouTube authentication failed")
                return False
            
            # Build YouTube API service
            self.service = build(
                self.YOUTUBE_API_SERVICE_NAME,
                self.YOUTUBE_API_VERSION,
                credentials=self.auth_manager.credentials
            )
            
            self.is_authenticated = True
            self.logger.info("YouTube authentication successful")
            return True
            
        except Exception as e:
            self.logger.error(f"YouTube authentication error: {e}")
            self.is_authenticated = False
            self.service = None
            
            if isinstance(e, AuthenticationError):
                raise
            else:
                raise AuthenticationError(
                    f"YouTube authentication failed: {e}",
                    platform=self.platform_name,
                    original_error=e
                )
    
    def _validate_metadata(self, metadata: MediaMetadata) -> None:
        """
        Validate metadata for YouTube requirements.
        
        Args:
            metadata: Media metadata to validate
            
        Raises:
            ValidationError: If metadata is invalid
        """
        # Title is required and must not be empty
        if not metadata.title or not metadata.title.strip():
            raise ValidationError(
                "Title is required for YouTube uploads",
                platform=self.platform_name
            )
        
        # YouTube title limit is 100 characters
        if len(metadata.title) > 100:
            raise ValidationError(
                f"Title too long for YouTube (max 100 characters, got {len(metadata.title)})",
                platform=self.platform_name
            )
        
        # YouTube description limit is 5000 characters
        if metadata.description and len(metadata.description) > 5000:
            raise ValidationError(
                f"Description too long for YouTube (max 5000 characters, got {len(metadata.description)})",
                platform=self.platform_name
            )
        
        # YouTube allows up to 50 tags
        if metadata.tags and len(metadata.tags) > 50:
            raise ValidationError(
                f"Too many tags for YouTube (max 50, got {len(metadata.tags)})",
                platform=self.platform_name
            )
        
        # Validate total tags length (YouTube limit: 500 characters)
        if metadata.tags:
            total_tags_length = sum(len(tag) for tag in metadata.tags)
            if total_tags_length > 500:
                raise ValidationError(
                    f"Total tags length exceeds YouTube limit (max 500 characters, got {total_tags_length})",
                    platform=self.platform_name
                )
        
        # Validate privacy setting
        if metadata.privacy and metadata.privacy not in ["public", "private", "unlisted"]:
            raise ValidationError(
                f"Invalid privacy setting for YouTube: {metadata.privacy}",
                platform=self.platform_name
            )
        
        # Validate scheduled publishing (only allowed with private videos)
        if metadata.scheduled_publish_time and metadata.privacy != "private":
            raise ValidationError(
                "Scheduled publishing is only allowed for private videos on YouTube",
                platform=self.platform_name
            )
        
        # Validate category
        if metadata.category and metadata.category not in self.CATEGORY_MAPPINGS:
            raise ValidationError(
                f"Invalid category for YouTube: {metadata.category}. Valid categories: {list(self.CATEGORY_MAPPINGS.keys())}",
                platform=self.platform_name
            )
        
        # Validate language codes (basic validation)
        if metadata.default_language and len(metadata.default_language) > 10:
            raise ValidationError(
                f"Invalid default language code: {metadata.default_language}",
                platform=self.platform_name
            )
        
        if metadata.default_audio_language and len(metadata.default_audio_language) > 10:
            raise ValidationError(
                f"Invalid default audio language code: {metadata.default_audio_language}",
                platform=self.platform_name
            )
    
    def _validate_file(self, file_path: str) -> None:
        """
        Validate video file for YouTube upload.
        
        Args:
            file_path: Path to the video file
            
        Raises:
            ValidationError: If file is invalid
        """
        # Check if file exists
        if not os.path.exists(file_path):
            raise ValidationError(
                f"Video file not found: {file_path}",
                platform=self.platform_name
            )
        
        # Check file size
        file_size = os.path.getsize(file_path)
        
        if file_size == 0:
            raise ValidationError(
                f"Video file is empty: {file_path}",
                platform=self.platform_name
            )
        
        if file_size > self.MAX_FILE_SIZE:
            raise ValidationError(
                f"Video file too large for YouTube (max 256GB, got {file_size / (1024**3):.1f}GB)",
                platform=self.platform_name
            )
    
    def _convert_metadata_to_youtube_format(self, metadata: MediaMetadata) -> Dict[str, Any]:
        """
        Convert MediaMetadata to YouTube API format.
        
        Args:
            metadata: Media metadata
            
        Returns:
            Dictionary in YouTube API format
        """
        # Build snippet (video information)
        snippet = {
            "title": metadata.title,
            "description": metadata.description or "",
            "tags": metadata.tags or [],
            "categoryId": self._get_category_id(metadata.category)
        }
        
        # Add language settings
        if metadata.default_language:
            snippet["defaultLanguage"] = metadata.default_language
        
        if metadata.default_audio_language:
            snippet["defaultAudioLanguage"] = metadata.default_audio_language
        
        # Build status (privacy and other settings)
        status = {
            "privacyStatus": metadata.privacy or "unlisted"  # Default to unlisted
        }
        
        # Add scheduled publish time
        if metadata.scheduled_publish_time:
            status["publishAt"] = metadata.scheduled_publish_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Add additional status fields
        if metadata.made_for_kids is not None:
            status["madeForKids"] = metadata.made_for_kids
        
        if metadata.embeddable is not None:
            status["embeddable"] = metadata.embeddable
        
        if metadata.public_stats_viewable is not None:
            status["publicStatsViewable"] = metadata.public_stats_viewable
        
        if metadata.license_type:
            status["license"] = metadata.license_type
        
        return {
            "snippet": snippet,
            "status": status
        }
    
    def _get_category_id(self, category: Optional[str]) -> str:
        """
        Map category name to YouTube category ID.
        
        Args:
            category: Category name
            
        Returns:
            YouTube category ID
        """
        if not category:
            return self.DEFAULT_CATEGORY_ID
        
        category_lower = category.lower()
        return self.CATEGORY_MAPPINGS.get(category_lower, self.DEFAULT_CATEGORY_ID)
    
    def _get_video_url(self, video_id: str) -> str:
        """
        Generate YouTube video URL from video ID.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Complete YouTube video URL
        """
        return f"https://www.youtube.com/watch?v={video_id}"
    
    async def upload_thumbnail(self, video_id: str, thumbnail_path: str) -> bool:
        """
        Upload custom thumbnail for a YouTube video.
        
        Args:
            video_id: YouTube video ID
            thumbnail_path: Path to thumbnail image file
            
        Returns:
            True if thumbnail upload succeeded
            
        Raises:
            ValidationError: If thumbnail file is invalid
            UploadError: If thumbnail upload fails
        """
        # Validate thumbnail file
        self._validate_thumbnail_file(thumbnail_path)
        
        try:
            # Create media upload for thumbnail
            media = MediaFileUpload(
                thumbnail_path,
                mimetype=self._get_thumbnail_mimetype(thumbnail_path)
            )
            
            # Upload thumbnail
            self.service.thumbnails().set(
                videoId=video_id,
                media_body=media
            ).execute()
            
            self.logger.info(f"Thumbnail uploaded successfully for video: {video_id}")
            return True
            
        except HttpError as e:
            self.logger.error(f"Thumbnail upload failed: {e}")
            self._handle_http_error(e)
            
        except Exception as e:
            self.logger.error(f"Unexpected error during thumbnail upload: {e}")
            raise UploadError(
                f"Thumbnail upload failed: {e}",
                platform=self.platform_name,
                original_error=e
            )
    
    def _validate_thumbnail_file(self, thumbnail_path: str) -> None:
        """
        Validate thumbnail file for YouTube requirements.
        
        Args:
            thumbnail_path: Path to thumbnail file
            
        Raises:
            ValidationError: If thumbnail is invalid
        """
        import os
        from PIL import Image
        
        # Check if file exists
        if not os.path.exists(thumbnail_path):
            raise ValidationError(
                f"Thumbnail file not found: {thumbnail_path}",
                platform=self.platform_name
            )
        
        # Check file size (YouTube limit: 2MB)
        file_size = os.path.getsize(thumbnail_path)
        max_thumbnail_size = 2 * 1024 * 1024  # 2MB
        if file_size > max_thumbnail_size:
            raise ValidationError(
                f"Thumbnail file too large: {file_size} bytes (max {max_thumbnail_size} bytes)",
                platform=self.platform_name
            )
        
        # Check file format and dimensions
        try:
            with Image.open(thumbnail_path) as img:
                # YouTube supports JPG, GIF, PNG
                if img.format not in ['JPEG', 'PNG', 'GIF']:
                    raise ValidationError(
                        f"Unsupported thumbnail format: {img.format}. Supported: JPEG, PNG, GIF",
                        platform=self.platform_name
                    )
                
                # Check minimum resolution (640x360)
                width, height = img.size
                if width < 640 or height < 360:
                    raise ValidationError(
                        f"Thumbnail resolution too low: {width}x{height}. Minimum: 640x360",
                        platform=self.platform_name
                    )
                
                # Check aspect ratio (16:9 recommended)
                aspect_ratio = width / height
                if not (1.5 <= aspect_ratio <= 2.0):  # Allow some flexibility
                    self.logger.warning(
                        f"Thumbnail aspect ratio {aspect_ratio:.2f} may not be optimal. Recommended: 16:9 (1.78)"
                    )
                    
        except Exception as e:
            raise ValidationError(
                f"Invalid thumbnail file: {e}",
                platform=self.platform_name,
                original_error=e
            )
    
    def _get_thumbnail_mimetype(self, thumbnail_path: str) -> str:
        """
        Get MIME type for thumbnail file.
        
        Args:
            thumbnail_path: Path to thumbnail file
            
        Returns:
            MIME type string
        """
        import mimetypes
        
        mimetype, _ = mimetypes.guess_type(thumbnail_path)
        if mimetype:
            return mimetype
        
        # Fallback based on file extension
        ext = thumbnail_path.lower().split('.')[-1]
        if ext == 'jpg' or ext == 'jpeg':
            return 'image/jpeg'
        elif ext == 'png':
            return 'image/png'
        elif ext == 'gif':
            return 'image/gif'
        else:
            return 'image/jpeg'  # Default fallback
    
    def _sanitize_metadata(self, metadata: MediaMetadata) -> MediaMetadata:
        """
        Sanitize metadata for YouTube compatibility.
        
        Args:
            metadata: Original metadata
            
        Returns:
            Sanitized metadata copy
        """
        import re
        import copy
        
        # Create a copy to avoid modifying original
        sanitized = copy.deepcopy(metadata)
        
        # Clean title - remove control characters, HTML tags, and excessive whitespace
        if sanitized.title:
            # Remove HTML/XML tags
            sanitized.title = re.sub(r'<[^>]+>', '', sanitized.title)
            # Remove control characters
            sanitized.title = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', sanitized.title)
            # Normalize whitespace
            sanitized.title = re.sub(r'\s+', ' ', sanitized.title).strip()
        
        # Clean description - remove null chars but preserve formatting
        if sanitized.description:
            sanitized.description = re.sub(r'\x00', '', sanitized.description)
        
        # Clean tags - remove special characters and normalize
        if sanitized.tags:
            clean_tags = []
            for tag in sanitized.tags:
                # Remove control characters and normalize spaces
                clean_tag = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', tag)
                clean_tag = re.sub(r'\s+', ' ', clean_tag).strip()
                
                # Only add non-empty tags
                if clean_tag:
                    clean_tags.append(clean_tag)
            
            sanitized.tags = clean_tags
        
        return sanitized
    
    async def _upload_media(
        self,
        file_path: str,
        metadata: MediaMetadata,
        progress_callback: Optional[Callable[[UploadProgress], None]] = None
    ) -> UploadResult:
        """
        Upload video to YouTube.
        
        Args:
            file_path: Path to the video file
            metadata: Video metadata
            progress_callback: Optional progress callback
            
        Returns:
            UploadResult with upload information
            
        Raises:
            UploadError: If upload fails
            ValidationError: If file or metadata is invalid
        """
        # Validate file
        self._validate_file(file_path)
        
        # Convert metadata to YouTube format
        youtube_metadata = self._convert_metadata_to_youtube_format(metadata)
        
        try:
            # Create media upload object
            file_size = os.path.getsize(file_path)
            media = MediaFileUpload(
                file_path,
                chunksize=-1,  # Upload entire file at once for better performance
                resumable=True
            )
            
            # Create insert request
            insert_request = self.service.videos().insert(
                part=",".join(youtube_metadata.keys()),
                body=youtube_metadata,
                media_body=media
            )
            
            self.logger.info(f"Starting YouTube upload for file: {file_path}")
            
            # Perform resumable upload
            response = await self._perform_resumable_upload(
                insert_request,
                progress_callback,
                file_size
            )
            
            # Extract video information from response
            video_id = response["id"]
            video_url = self._get_video_url(video_id)
            
            self.logger.info(f"YouTube upload successful. Video ID: {video_id}")
            
            # Upload thumbnail if provided
            thumbnail_uploaded = False
            if metadata.thumbnail_path:
                try:
                    thumbnail_uploaded = await self.upload_thumbnail(video_id, metadata.thumbnail_path)
                    self.logger.info(f"Thumbnail uploaded for video: {video_id}")
                except Exception as e:
                    self.logger.warning(f"Thumbnail upload failed (continuing with video upload): {e}")

            return UploadResult(
                platform=self.platform_name,
                upload_id=video_id,
                success=True,
                media_url=video_url,
                metadata={
                    "video_id": video_id,
                    "title": response.get("snippet", {}).get("title"),
                    "description": response.get("snippet", {}).get("description"),
                    "privacy_status": response.get("status", {}).get("privacyStatus"),
                    "thumbnail_uploaded": thumbnail_uploaded
                }
            )

        except HttpError as e:
            self.logger.error(f"YouTube API error: {e}")
            self._handle_http_error(e)
            # _handle_http_error always raises, this line never executes
            raise

        except (RateLimitError, AuthenticationError, ValidationError):
            # Re-raise Medusa exceptions without wrapping
            raise

        except (socket.error, OSError) as e:
            self.logger.error(f"Network error during YouTube upload: {e}")
            raise NetworkError(
                f"Network error during YouTube upload: {e}",
                platform=self.platform_name,
                original_error=e
            )

        except Exception as e:
            self.logger.error(f"Unexpected error during YouTube upload: {e}")
            raise UploadError(
                f"YouTube upload failed: {e}",
                platform=self.platform_name,
                original_error=e
            )
    
    async def _perform_resumable_upload(
        self,
        insert_request,
        progress_callback: Optional[Callable[[UploadProgress], None]],
        file_size: int
    ) -> Dict[str, Any]:
        """
        Perform resumable upload with retry logic.
        
        Args:
            insert_request: YouTube API insert request
            progress_callback: Optional progress callback
            file_size: Total file size in bytes
            
        Returns:
            YouTube API response
            
        Raises:
            UploadError: If upload fails after all retries
        """
        response = None
        error = None
        retry = 0
        
        while response is None:
            try:
                self.logger.debug("Uploading chunk...")
                status, response = insert_request.next_chunk()
                
                # Report progress if callback provided
                if progress_callback and status:
                    progress = UploadProgress(
                        bytes_uploaded=int(status.resumable_progress * file_size),
                        total_bytes=file_size,
                        status="uploading"
                    )
                    progress_callback(progress)
                
                if response is not None:
                    if 'id' in response:
                        self.logger.info(f"Video upload completed. ID: {response['id']}")
                        
                        # Final progress update
                        if progress_callback:
                            final_progress = UploadProgress(
                                bytes_uploaded=file_size,
                                total_bytes=file_size,
                                status="completed"
                            )
                            progress_callback(final_progress)
                        
                        return response
                    else:
                        raise UploadError(
                            f"Unexpected YouTube API response: {response}",
                            platform=self.platform_name
                        )
                        
            except HttpError as e:
                if e.resp.status in self.RETRYABLE_STATUS_CODES:
                    error = f"Retriable HTTP error {e.resp.status}: {e.content}"
                else:
                    raise self._handle_http_error(e)
                    
            except Exception as e:
                if self._is_retryable_error(e):
                    error = f"Retriable error: {e}"
                else:
                    raise UploadError(
                        f"YouTube upload failed: {e}",
                        platform=self.platform_name,
                        original_error=e
                    )
            
            if error is not None:
                retry += 1
                if retry > self.MAX_RESUMABLE_RETRIES:
                    raise UploadError(
                        f"YouTube upload failed after {self.MAX_RESUMABLE_RETRIES} retries: {error}",
                        platform=self.platform_name
                    )
                
                # Exponential backoff with jitter
                max_sleep = 2 ** retry
                sleep_seconds = random.random() * max_sleep
                
                self.logger.warning(f"Upload retry {retry}/{self.MAX_RESUMABLE_RETRIES}. "
                                  f"Sleeping {sleep_seconds:.1f}s. Error: {error}")
                
                await asyncio.sleep(sleep_seconds)
                error = None
        
        # This should never be reached, but just in case
        raise UploadError(
            "YouTube upload failed unexpectedly",
            platform=self.platform_name
        )
    
    def _handle_http_error(self, error: HttpError) -> None:
        """
        Handle YouTube API HTTP errors.
        
        Args:
            error: HTTP error from YouTube API
            
        Raises:
            Appropriate exception based on error type
        """
        status_code = error.resp.status
        error_content = error.content.decode('utf-8') if error.content else ""
        
        # Extract error message from JSON response if possible
        try:
            import json
            error_data = json.loads(error_content)
            error_message = error_data.get("error", {}).get("message", str(error))
        except (json.JSONDecodeError, KeyError):
            error_message = str(error)
        
        # Handle specific error types
        if status_code == 403:
            if "quota" in error_message.lower():
                raise RateLimitError(
                    f"YouTube API quota exceeded: {error_message}",
                    platform=self.platform_name,
                    original_error=error
                )
            else:
                raise AuthenticationError(
                    f"YouTube API access forbidden: {error_message}",
                    platform=self.platform_name,
                    original_error=error
                )
        
        elif status_code == 401:
            raise AuthenticationError(
                f"YouTube API authentication failed: {error_message}",
                platform=self.platform_name,
                original_error=error
            )
        
        elif status_code in [400, 422]:
            raise ValidationError(
                f"YouTube API validation error: {error_message}",
                platform=self.platform_name,
                original_error=error
            )
        
        elif status_code in self.RETRYABLE_STATUS_CODES:
            raise UploadError(
                f"YouTube API server error: {error_message}",
                platform=self.platform_name,
                original_error=error
            )
        
        else:
            raise UploadError(
                f"YouTube API error ({status_code}): {error_message}",
                platform=self.platform_name,
                original_error=error
            )
    
    def _is_retryable_error(self, error: Exception) -> bool:
        """
        Determine if an error is retryable.
        
        Args:
            error: Exception to check
            
        Returns:
            True if error is retryable, False otherwise
        """
        # Network-related errors are retryable
        if isinstance(error, (socket.error, OSError, ConnectionError)):
            return True
        
        # HTTP errors with retryable status codes
        if isinstance(error, HttpError):
            return error.resp.status in self.RETRYABLE_STATUS_CODES
        
        # Other specific retryable exceptions
        retryable_exceptions = (
            "HttpLib2Error",
            "NotConnected", 
            "IncompleteRead",
            "ImproperConnectionState",
            "CannotSendRequest",
            "CannotSendHeader",
            "ResponseNotReady",
            "BadStatusLine"
        )
        
        return any(exc_name in str(type(error)) for exc_name in retryable_exceptions)
    
    async def cleanup(self) -> None:
        """
        Clean up resources.
        """
        await super().cleanup()
        
        # Clean up auth manager
        if self.auth_manager:
            await self.auth_manager.cleanup()
        
        # Clear service reference
        self.service = None
        
        self.logger.debug("YouTube uploader cleanup completed")