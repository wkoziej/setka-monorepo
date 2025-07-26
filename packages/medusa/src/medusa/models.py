# ABOUTME: Data models and enums for task status, metadata, and platform configurations
# ABOUTME: Defines structured data types used throughout the Medusa library

import os
import re
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .exceptions import MedusaError


class TaskStatus(Enum):
    """Enumeration of possible task states with proper state transitions."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


def validate_task_transition(from_status: TaskStatus, to_status: TaskStatus) -> bool:
    """
    Validate if a task state transition is allowed.
    
    Args:
        from_status: Current task status
        to_status: Target task status
        
    Returns:
        True if transition is valid, False otherwise
    """
    # Define valid transitions
    valid_transitions = {
        TaskStatus.PENDING: {TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED},
        TaskStatus.IN_PROGRESS: {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED},
        TaskStatus.COMPLETED: {TaskStatus.COMPLETED},  # Can stay completed
        TaskStatus.FAILED: {TaskStatus.FAILED},  # Can stay failed
        TaskStatus.CANCELLED: {TaskStatus.CANCELLED}  # Can stay cancelled
    }
    
    return to_status in valid_transitions.get(from_status, set())


@dataclass
class TaskTransition:
    """Represents a task state transition with validation."""
    from_status: TaskStatus
    to_status: TaskStatus
    timestamp: datetime
    message: Optional[str] = None
    
    def validate(self) -> None:
        """
        Validate the state transition.
        
        Raises:
            MedusaError: If the transition is invalid
        """
        if not validate_task_transition(self.from_status, self.to_status):
            raise MedusaError(
                f"Invalid state transition from {self.from_status.value} to {self.to_status.value}"
            )


@dataclass
class TaskResult:
    """Represents the result of a task with comprehensive tracking."""
    task_id: str
    status: TaskStatus
    message: Optional[str] = None
    error: Optional[str] = None
    failed_platform: Optional[str] = None
    results: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def validate(self) -> None:
        """
        Validate the task result.
        
        Raises:
            MedusaError: If validation fails
        """
        if not self.task_id or not self.task_id.strip():
            raise MedusaError("Task ID cannot be empty")
        
        if self.status == TaskStatus.FAILED and not self.error:
            raise MedusaError("Failed tasks must have error information")
    
    def update_status(self, new_status: TaskStatus, message: Optional[str] = None) -> None:
        """
        Update the task status with validation.
        
        Args:
            new_status: New status to set
            message: Optional status message
            
        Raises:
            MedusaError: If the status transition is invalid
        """
        if not validate_task_transition(self.status, new_status):
            raise MedusaError(
                f"Invalid status transition from {self.status.value} to {new_status.value}"
            )
        
        self.status = new_status
        self.message = message
        self.updated_at = datetime.now(timezone.utc)
    
    def add_platform_result(self, platform: str, result: Dict[str, Any]) -> None:
        """
        Add platform-specific result data.
        
        Args:
            platform: Platform name
            result: Platform result data
        """
        self.results[platform] = result
        self.updated_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize TaskResult to dictionary.
        
        Returns:
            Dictionary representation of the task result
        """
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "message": self.message,
            "error": self.error,
            "failed_platform": self.failed_platform,
            "results": self.results,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskResult':
        """
        Deserialize TaskResult from dictionary.
        
        Args:
            data: Dictionary containing task result data
            
        Returns:
            TaskResult instance
        """
        # Parse datetime fields
        created_at = datetime.fromisoformat(data["created_at"].replace('Z', '+00:00'))
        updated_at = datetime.fromisoformat(data["updated_at"].replace('Z', '+00:00'))
        
        return cls(
            task_id=data["task_id"],
            status=TaskStatus(data["status"]),
            message=data.get("message"),
            error=data.get("error"),
            failed_platform=data.get("failed_platform"),
            results=data.get("results", {}),
            created_at=created_at,
            updated_at=updated_at
        )


@dataclass
class MediaMetadata:
    """Container for media-specific metadata with validation."""
    title: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    privacy: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration: Optional[int] = None  # Duration in seconds
    file_size: Optional[int] = None  # File size in bytes
    category: Optional[str] = None
    language: Optional[str] = None
    
    # Extended YouTube-specific fields
    default_language: Optional[str] = None
    default_audio_language: Optional[str] = None
    scheduled_publish_time: Optional[datetime] = None
    made_for_kids: Optional[bool] = None
    embeddable: Optional[bool] = None
    public_stats_viewable: Optional[bool] = None
    license_type: Optional[str] = None
    thumbnail_path: Optional[str] = None  # Local path to thumbnail file
    
    # Valid privacy settings
    VALID_PRIVACY_SETTINGS = {"public", "unlisted", "private"}
    
    # Validation limits
    MAX_TITLE_LENGTH = 100
    MAX_DESCRIPTION_LENGTH = 5000
    MAX_TAGS = 50
    MAX_TAG_LENGTH = 50
    
    def validate(self) -> None:
        """
        Validate media metadata.
        
        Raises:
            MedusaError: If validation fails
        """
        if self.title and len(self.title) > self.MAX_TITLE_LENGTH:
            raise MedusaError(f"Title too long (max {self.MAX_TITLE_LENGTH} characters)")
        
        if self.description and len(self.description) > self.MAX_DESCRIPTION_LENGTH:
            raise MedusaError(f"Description too long (max {self.MAX_DESCRIPTION_LENGTH} characters)")
        
        if self.privacy and self.privacy not in self.VALID_PRIVACY_SETTINGS:
            raise MedusaError(f"Invalid privacy setting: {self.privacy}")
        
        if len(self.tags) > self.MAX_TAGS:
            raise MedusaError(f"Too many tags (max {self.MAX_TAGS})")
        
        for tag in self.tags:
            if len(tag) > self.MAX_TAG_LENGTH:
                raise MedusaError(f"Tag too long: {tag} (max {self.MAX_TAG_LENGTH} characters)")
    
    def sanitize(self) -> None:
        """Sanitize metadata fields for platform compatibility."""
        # Clean up tags
        if self.tags:
            sanitized_tags = []
            for tag in self.tags:
                # Remove extra whitespace and special characters
                clean_tag = re.sub(r'[^\w\s-]', '', tag.strip().lower())
                clean_tag = re.sub(r'\s+', '', clean_tag)  # Remove spaces
                if clean_tag:  # Only add non-empty tags
                    sanitized_tags.append(clean_tag)
            self.tags = sanitized_tags
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize MediaMetadata to dictionary.
        
        Returns:
            Dictionary representation of the metadata
        """
        return {
            "title": self.title,
            "description": self.description,
            "tags": self.tags,
            "privacy": self.privacy,
            "thumbnail_url": self.thumbnail_url,
            "duration": self.duration,
            "file_size": self.file_size,
            "category": self.category,
            "language": self.language,
            "default_language": self.default_language,
            "default_audio_language": self.default_audio_language,
            "scheduled_publish_time": self.scheduled_publish_time.isoformat() if self.scheduled_publish_time else None,
            "made_for_kids": self.made_for_kids,
            "embeddable": self.embeddable,
            "public_stats_viewable": self.public_stats_viewable,
            "license_type": self.license_type,
            "thumbnail_path": self.thumbnail_path
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MediaMetadata':
        """
        Deserialize MediaMetadata from dictionary.
        
        Args:
            data: Dictionary containing metadata
            
        Returns:
            MediaMetadata instance
        """
        # Parse scheduled_publish_time if present
        scheduled_publish_time = None
        if data.get("scheduled_publish_time"):
            scheduled_publish_time = datetime.fromisoformat(data["scheduled_publish_time"].replace('Z', '+00:00'))
        
        return cls(
            title=data.get("title"),
            description=data.get("description"),
            tags=data.get("tags", []),
            privacy=data.get("privacy"),
            thumbnail_url=data.get("thumbnail_url"),
            duration=data.get("duration"),
            file_size=data.get("file_size"),
            category=data.get("category"),
            language=data.get("language"),
            default_language=data.get("default_language"),
            default_audio_language=data.get("default_audio_language"),
            scheduled_publish_time=scheduled_publish_time,
            made_for_kids=data.get("made_for_kids"),
            embeddable=data.get("embeddable"),
            public_stats_viewable=data.get("public_stats_viewable"),
            license_type=data.get("license_type"),
            thumbnail_path=data.get("thumbnail_path")
        )


@dataclass
class PlatformConfig:
    """Enhanced configuration for a specific platform."""
    platform_name: str
    enabled: bool = True
    credentials: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    rate_limit: Optional[int] = None  # Requests per minute
    retry_attempts: int = 3
    timeout: Optional[int] = None  # Timeout in seconds
    
    # Supported platforms
    SUPPORTED_PLATFORMS = {"youtube", "facebook", "vimeo", "twitter"}
    
    def validate(self) -> None:
        """
        Validate platform configuration.
        
        Raises:
            MedusaError: If validation fails
        """
        if self.platform_name not in self.SUPPORTED_PLATFORMS:
            raise MedusaError(f"Unsupported platform: {self.platform_name}")
        
        if self.retry_attempts < 0:
            raise MedusaError("Retry attempts must be non-negative")
        
        if self.timeout is not None and self.timeout <= 0:
            raise MedusaError("Timeout must be positive")
    
    def is_configured(self) -> bool:
        """
        Check if the platform is properly configured.
        
        Returns:
            True if platform is enabled and has credentials
        """
        return self.enabled and bool(self.credentials)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize PlatformConfig to dictionary.
        
        Returns:
            Dictionary representation of the configuration
        """
        return {
            "platform_name": self.platform_name,
            "enabled": self.enabled,
            "credentials": self.credentials,
            "metadata": self.metadata,
            "rate_limit": self.rate_limit,
            "retry_attempts": self.retry_attempts,
            "timeout": self.timeout
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlatformConfig':
        """
        Deserialize PlatformConfig from dictionary.
        
        Args:
            data: Dictionary containing configuration
            
        Returns:
            PlatformConfig instance
        """
        return cls(
            platform_name=data["platform_name"],
            enabled=data.get("enabled", True),
            credentials=data.get("credentials", {}),
            metadata=data.get("metadata", {}),
            rate_limit=data.get("rate_limit"),
            retry_attempts=data.get("retry_attempts", 3),
            timeout=data.get("timeout")
        )


@dataclass
class PublishRequest:
    """Request for publishing media to multiple platforms."""
    media_file_path: str
    platforms: List[str]
    metadata: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    priority: int = 1
    schedule_time: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def validate(self) -> None:
        """
        Validate the publish request.
        
        Raises:
            MedusaError: If validation fails
        """
        if not self.platforms:
            raise MedusaError("At least one platform must be specified")
        
        if self.priority < 1:
            raise MedusaError("Priority must be >= 1")
        
        if not os.path.exists(self.media_file_path):
            raise MedusaError(f"Media file not found: {self.media_file_path}")
        
        # Validate platform names
        for platform in self.platforms:
            if platform not in PlatformConfig.SUPPORTED_PLATFORMS:
                raise MedusaError(f"Unsupported platform: {platform}")
    
    def get_platform_metadata(self, platform: str) -> Dict[str, Any]:
        """
        Get metadata for a specific platform.
        
        Args:
            platform: Platform name
            
        Returns:
            Platform-specific metadata or empty dict
        """
        return self.metadata.get(platform, {})
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize PublishRequest to dictionary.
        
        Returns:
            Dictionary representation of the request
        """
        return {
            "media_file_path": self.media_file_path,
            "platforms": self.platforms,
            "metadata": self.metadata,
            "priority": self.priority,
            "schedule_time": self.schedule_time.isoformat() if self.schedule_time else None,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PublishRequest':
        """
        Deserialize PublishRequest from dictionary.
        
        Args:
            data: Dictionary containing request data
            
        Returns:
            PublishRequest instance
        """
        # Parse datetime fields
        created_at = datetime.fromisoformat(data["created_at"].replace('Z', '+00:00'))
        schedule_time = None
        if data.get("schedule_time"):
            schedule_time = datetime.fromisoformat(data["schedule_time"].replace('Z', '+00:00'))
        
        return cls(
            media_file_path=data["media_file_path"],
            platforms=data["platforms"],
            metadata=data.get("metadata", {}),
            priority=data.get("priority", 1),
            schedule_time=schedule_time,
            created_at=created_at
        )