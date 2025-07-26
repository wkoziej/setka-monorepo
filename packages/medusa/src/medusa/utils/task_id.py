"""
Secure task ID generation system for Medusa library.

This module provides task ID generation with:
- UUID4-based cryptographically secure IDs
- Prefix-based categorization
- Task type classification
- Timestamp tracking
- Full validation and parsing utilities
"""

import uuid
import re
from datetime import datetime
from typing import Optional, Dict, Any

from medusa.exceptions import ValidationError


class InvalidTaskIDError(Exception):
    """Exception raised for invalid task ID operations."""
    
    def __init__(self, message: str, task_id: Optional[str] = None):
        """
        Initialize InvalidTaskIDError.
        
        Args:
            message: Error message
            task_id: Optional task ID that caused the error
        """
        super().__init__(message)
        self.task_id = task_id


class TaskIDGenerator:
    """
    Secure task ID generator with validation and parsing capabilities.
    
    Generates task IDs with format:
    - Basic: {prefix}_{timestamp}_{uuid4}
    - With type: {prefix}_{task_type}_{timestamp}_{uuid4}
    
    Where:
    - prefix: Configurable prefix (default: "medusa_task")
    - task_type: Optional categorization (e.g., "upload", "publish")
    - timestamp: UTC timestamp in YYYYMMDDHHMMSS format
    - uuid4: Cryptographically secure UUID4
    """
    
    DEFAULT_PREFIX = "medusa_task"
    
    # Regex patterns for validation
    PREFIX_PATTERN = re.compile(r'^[a-zA-Z][a-zA-Z0-9_]*$')
    TASK_TYPE_PATTERN = re.compile(r'^[a-zA-Z][a-zA-Z0-9_]*$')
    TIMESTAMP_PATTERN = re.compile(r'^\d{14}$')
    UUID4_PATTERN = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
    )
    
    def __init__(self, prefix: str = DEFAULT_PREFIX):
        """
        Initialize TaskIDGenerator with optional custom prefix.
        
        Args:
            prefix: Custom prefix for task IDs (default: "medusa_task")
            
        Raises:
            MedusaValidationError: If prefix format is invalid
        """
        if not self._validate_prefix(prefix):
            raise ValidationError(
                f"Invalid prefix format: '{prefix}'. "
                f"Prefix must start with letter and contain only letters, numbers, and underscores."
            )
        self.prefix = prefix
    
    def generate_task_id(self, task_type: Optional[str] = None) -> str:
        """
        Generate a secure task ID.
        
        Args:
            task_type: Optional task type for categorization
            
        Returns:
            Generated task ID string
            
        Raises:
            MedusaValidationError: If task_type format is invalid
        """
        if task_type is not None and not self._validate_task_type(task_type):
            raise ValidationError(
                f"Invalid task type format: '{task_type}'. "
                f"Task type must start with letter and contain only letters, numbers, and underscores."
            )
        
        # Generate components
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_id = str(uuid.uuid4())
        
        # Build task ID
        parts = [self.prefix]
        if task_type:
            parts.append(task_type)
        parts.extend([timestamp, unique_id])
        
        return "_".join(parts)
    
    def validate_task_id(self, task_id: Any) -> bool:
        """
        Validate if a string is a valid task ID.
        
        Args:
            task_id: Task ID to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(task_id, str):
            return False
            
        try:
            self.parse_task_id(task_id)
            return True
        except (InvalidTaskIDError, ValueError, AttributeError):
            return False
    
    def parse_task_id(self, task_id: str) -> Dict[str, Any]:
        """
        Parse task ID into its components.
        
        Args:
            task_id: Task ID to parse
            
        Returns:
            Dictionary containing parsed components:
            - prefix: Task prefix
            - task_type: Task type (None if not present)
            - timestamp: Datetime object
            - uuid: UUID object
            
        Raises:
            InvalidTaskIDError: If task ID format is invalid
        """
        if not isinstance(task_id, str):
            raise InvalidTaskIDError(f"Task ID must be string, got {type(task_id)}", task_id)
        
        # Use regex to parse task ID components more accurately
        # Pattern: prefix_[tasktype_]timestamp_uuid
        # UUID is always at the end, timestamp before it
        uuid_match = re.search(r'([0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})$', task_id)
        if not uuid_match:
            raise InvalidTaskIDError(f"No valid UUID4 found in task ID: {task_id}", task_id)
        
        uuid_str = uuid_match.group(1)
        uuid_start = uuid_match.start()
        
        # Everything before UUID should end with _timestamp_
        before_uuid = task_id[:uuid_start-1]  # Remove the last underscore
        
        # Extract timestamp (14 digits at the end of before_uuid)
        timestamp_match = re.search(r'(\d{14})$', before_uuid)
        if not timestamp_match:
            raise InvalidTaskIDError(f"No valid timestamp found in task ID: {task_id}", task_id)
        
        timestamp_str = timestamp_match.group(1)
        timestamp_start = timestamp_match.start()
        
        # Everything before timestamp
        before_timestamp = before_uuid[:timestamp_start-1]  # Remove the last underscore
        
        # Check if it starts with our prefix
        if not before_timestamp.startswith(self.prefix):
            raise InvalidTaskIDError(f"Task ID prefix mismatch: expected '{self.prefix}', got prefix from '{task_id}'", task_id)
        
        # Determine task type (if any)
        task_type = None
        after_prefix = before_timestamp[len(self.prefix):]
        
        if after_prefix:
            if not after_prefix.startswith('_'):
                raise InvalidTaskIDError(f"Invalid task ID format after prefix: {task_id}", task_id)
            task_type = after_prefix[1:]  # Remove the leading underscore
            
            # Validate task type
            if not self._validate_task_type(task_type):
                raise InvalidTaskIDError(f"Invalid task type in task ID: {task_type}", task_id)
        
        # Validate timestamp format
        if not self._validate_timestamp(timestamp_str):
            raise InvalidTaskIDError(f"Invalid timestamp format in task ID: {timestamp_str}", task_id)
        
        try:
            timestamp = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
        except ValueError as e:
            raise InvalidTaskIDError(f"Invalid timestamp value in task ID: {timestamp_str}", task_id) from e
        
        # Validate and parse UUID
        if not self.UUID4_PATTERN.match(uuid_str):
            raise InvalidTaskIDError(f"Invalid UUID format in task ID: {uuid_str}", task_id)
        
        try:
            uuid_obj = uuid.UUID(uuid_str)
            if uuid_obj.version != 4:
                raise InvalidTaskIDError(f"Task ID must use UUID4, got UUID{uuid_obj.version}", task_id)
        except ValueError as e:
            raise InvalidTaskIDError(f"Invalid UUID in task ID: {uuid_str}", task_id) from e
        
        return {
            "prefix": self.prefix,
            "task_type": task_type,
            "timestamp": timestamp,
            "uuid": uuid_obj
        }
    
    def is_task_id(self, task_id: Any) -> bool:
        """
        Check if a value is a valid task ID (alias for validate_task_id).
        
        Args:
            task_id: Value to check
            
        Returns:
            True if valid task ID, False otherwise
        """
        return self.validate_task_id(task_id)
    
    def extract_uuid(self, task_id: str) -> uuid.UUID:
        """
        Extract UUID component from task ID.
        
        Args:
            task_id: Task ID to extract UUID from
            
        Returns:
            UUID object
            
        Raises:
            InvalidTaskIDError: If task ID is invalid
        """
        parsed = self.parse_task_id(task_id)
        return parsed["uuid"]
    
    def extract_timestamp(self, task_id: str) -> datetime:
        """
        Extract timestamp component from task ID.
        
        Args:
            task_id: Task ID to extract timestamp from
            
        Returns:
            Datetime object
            
        Raises:
            InvalidTaskIDError: If task ID is invalid
        """
        parsed = self.parse_task_id(task_id)
        return parsed["timestamp"]
    
    def extract_task_type(self, task_id: str) -> Optional[str]:
        """
        Extract task type component from task ID.
        
        Args:
            task_id: Task ID to extract task type from
            
        Returns:
            Task type string or None if not present
            
        Raises:
            InvalidTaskIDError: If task ID is invalid
        """
        parsed = self.parse_task_id(task_id)
        return parsed["task_type"]
    
    def get_task_id_summary(self, task_id: str) -> Dict[str, Any]:
        """
        Get a summary of task ID components.
        
        Args:
            task_id: Task ID to summarize
            
        Returns:
            Dictionary with task ID summary
            
        Raises:
            InvalidTaskIDError: If task ID is invalid
        """
        parsed = self.parse_task_id(task_id)
        
        return {
            "id": task_id,
            "prefix": parsed["prefix"],
            "task_type": parsed["task_type"],
            "created_at": parsed["timestamp"].isoformat(),
            "uuid_short": str(parsed["uuid"])[:8]
        }
    
    def _validate_prefix(self, prefix: Any) -> bool:
        """
        Validate prefix format.
        
        Args:
            prefix: Prefix to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not prefix or not isinstance(prefix, str):
            return False
        return bool(self.PREFIX_PATTERN.match(prefix))
    
    def _validate_task_type(self, task_type: Any) -> bool:
        """
        Validate task type format.
        
        Args:
            task_type: Task type to validate (None is valid)
            
        Returns:
            True if valid, False otherwise
        """
        if task_type is None:
            return True
        if not isinstance(task_type, str):
            return False
        return bool(self.TASK_TYPE_PATTERN.match(task_type))
    
    def _validate_timestamp(self, timestamp: Any) -> bool:
        """
        Validate timestamp format.
        
        Args:
            timestamp: Timestamp string to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(timestamp, str):
            return False
        return bool(self.TIMESTAMP_PATTERN.match(timestamp))
    
    @classmethod
    def quick_generate(cls, prefix: str = DEFAULT_PREFIX, task_type: Optional[str] = None) -> str:
        """
        Quick task ID generation without creating generator instance.
        
        Args:
            prefix: Task prefix (default: "medusa_task")
            task_type: Optional task type
            
        Returns:
            Generated task ID
        """
        generator = cls(prefix=prefix)
        return generator.generate_task_id(task_type=task_type)
    
    @classmethod
    def quick_validate(cls, task_id: str, prefix: str = DEFAULT_PREFIX) -> bool:
        """
        Quick task ID validation without creating generator instance.
        
        Args:
            task_id: Task ID to validate
            prefix: Expected prefix (default: "medusa_task")
            
        Returns:
            True if valid, False otherwise
        """
        generator = cls(prefix=prefix)
        return generator.validate_task_id(task_id) 