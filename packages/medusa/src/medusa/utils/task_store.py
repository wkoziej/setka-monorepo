"""
In-memory task storage system for Medusa library.

This module provides comprehensive task storage functionality including:
- Thread-safe operations using appropriate locking
- Task lifecycle management with CRUD operations
- Efficient task lookup by ID and status
- Task querying and filtering capabilities
- Configurable task retention policies with automatic cleanup
- Support for concurrent access scenarios
"""

import logging
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Union, Any
from collections import defaultdict

from ..models import TaskResult, TaskStatus
from ..exceptions import MedusaError

# Set up logging
logger = logging.getLogger(__name__)


class TaskStoreError(MedusaError):
    """Exception raised for task store operations."""
    pass


class TaskStore:
    """
    Thread-safe in-memory task storage with lifecycle management.
    
    Provides comprehensive task storage functionality with:
    - Thread-safe CRUD operations
    - Task querying and filtering
    - Automatic cleanup of old tasks
    - Concurrent access support
    """
    
    def __init__(self, 
                 cleanup_enabled: bool = True, 
                 max_task_age_hours: int = 24,
                 cleanup_interval_minutes: int = 60):
        """
        Initialize TaskStore with optional cleanup configuration.
        
        Args:
            cleanup_enabled: Whether to enable automatic cleanup
            max_task_age_hours: Maximum age of tasks before cleanup (hours)
            cleanup_interval_minutes: Interval between cleanup runs (minutes)
        """
        self._tasks: Dict[str, TaskResult] = {}
        self._lock = threading.RLock()  # Re-entrant lock for nested operations
        
        # Cleanup configuration
        self.cleanup_enabled = cleanup_enabled
        self.max_task_age_hours = max_task_age_hours
        self.cleanup_interval_minutes = cleanup_interval_minutes
        
        # Automatic cleanup timer
        self._cleanup_timer: Optional[threading.Timer] = None
        if self.cleanup_enabled:
            self._schedule_cleanup()
        
        logger.debug(f"TaskStore initialized with cleanup_enabled={cleanup_enabled}, "
                    f"max_age={max_task_age_hours}h, interval={cleanup_interval_minutes}m")
    
    def store_task(self, task: TaskResult) -> bool:
        """
        Store a task in the task store.
        
        Args:
            task: TaskResult to store
            
        Returns:
            True if task was stored successfully
            
        Raises:
            TaskStoreError: If task is invalid or already exists
        """
        if task is None:
            raise TaskStoreError("Task cannot be None")
        
        if not task.task_id or not task.task_id.strip():
            raise TaskStoreError("Task ID cannot be empty")
        
        with self._lock:
            if task.task_id in self._tasks:
                raise TaskStoreError(f"Task {task.task_id} already exists")
            
            # Store the task
            self._tasks[task.task_id] = task
            
            logger.debug(f"Stored task {task.task_id} with status {task.status}")
            return True
    
    def get_task(self, task_id: str) -> Optional[TaskResult]:
        """
        Retrieve a task by ID.
        
        Args:
            task_id: Task ID to retrieve
            
        Returns:
            TaskResult if found, None otherwise
        """
        if not task_id:
            return None
        
        with self._lock:
            return self._tasks.get(task_id)
    
    def update_task(self, task: TaskResult) -> bool:
        """
        Update an existing task.
        
        Args:
            task: Updated TaskResult
            
        Returns:
            True if task was updated successfully
            
        Raises:
            TaskStoreError: If task doesn't exist
        """
        if task is None:
            raise TaskStoreError("Task cannot be None")
        
        if not task.task_id or not task.task_id.strip():
            raise TaskStoreError("Task ID cannot be empty")
        
        with self._lock:
            if task.task_id not in self._tasks:
                raise TaskStoreError(f"Task {task.task_id} not found")
            
            # Update the task
            self._tasks[task.task_id] = task
            
            logger.debug(f"Updated task {task.task_id} with status {task.status}")
            return True
    
    def delete_task(self, task_id: str) -> bool:
        """
        Delete a task by ID.
        
        Args:
            task_id: Task ID to delete
            
        Returns:
            True if task was deleted, False if not found
        """
        if not task_id:
            return False
        
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                logger.debug(f"Deleted task {task_id}")
                return True
            return False
    
    def get_all_tasks(self) -> List[TaskResult]:
        """
        Get all tasks in the store.
        
        Returns:
            List of all TaskResult objects
        """
        with self._lock:
            return list(self._tasks.values())
    
    def get_tasks_by_status(self, status: Union[TaskStatus, List[TaskStatus]]) -> List[TaskResult]:
        """
        Get tasks filtered by status.
        
        Args:
            status: TaskStatus or list of TaskStatus to filter by
            
        Returns:
            List of TaskResult objects with matching status
        """
        if isinstance(status, TaskStatus):
            status_list = [status]
        else:
            status_list = status
        
        with self._lock:
            return [task for task in self._tasks.values() if task.status in status_list]
    
    def get_tasks_created_after(self, cutoff_time: datetime) -> List[TaskResult]:
        """
        Get tasks created after a specific time.
        
        Args:
            cutoff_time: Datetime cutoff for filtering
            
        Returns:
            List of TaskResult objects created after cutoff_time
        """
        with self._lock:
            return [task for task in self._tasks.values() if task.created_at > cutoff_time]
    
    def get_task_count(self, status: Optional[TaskStatus] = None) -> int:
        """
        Get count of tasks, optionally filtered by status.
        
        Args:
            status: Optional TaskStatus to filter by
            
        Returns:
            Number of tasks matching criteria
        """
        with self._lock:
            if status is None:
                return len(self._tasks)
            else:
                return sum(1 for task in self._tasks.values() if task.status == status)
    
    def task_exists(self, task_id: str) -> bool:
        """
        Check if a task exists in the store.
        
        Args:
            task_id: Task ID to check
            
        Returns:
            True if task exists, False otherwise
        """
        if not task_id:
            return False
        
        with self._lock:
            return task_id in self._tasks
    
    def clear_all_tasks(self) -> int:
        """
        Clear all tasks from the store.
        
        Returns:
            Number of tasks that were cleared
        """
        with self._lock:
            count = len(self._tasks)
            self._tasks.clear()
            logger.debug(f"Cleared all {count} tasks from store")
            return count
    
    def cleanup_old_tasks(self, 
                         max_age_hours: Optional[int] = None, 
                         status_filter: Optional[List[TaskStatus]] = None) -> int:
        """
        Clean up old tasks based on age and optionally status.
        
        Args:
            max_age_hours: Maximum age in hours (uses default if None)
            status_filter: Optional list of statuses to clean up
            
        Returns:
            Number of tasks cleaned up
        """
        if max_age_hours is None:
            max_age_hours = self.max_task_age_hours
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        cleaned_count = 0
        
        with self._lock:
            tasks_to_remove = []
            
            for task_id, task in self._tasks.items():
                # Check age
                if task.created_at <= cutoff_time:
                    # Check status filter if provided
                    if status_filter is None or task.status in status_filter:
                        tasks_to_remove.append(task_id)
            
            # Remove old tasks
            for task_id in tasks_to_remove:
                del self._tasks[task_id]
                cleaned_count += 1
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} old tasks (older than {max_age_hours}h)")
        
        return cleaned_count
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.
        
        Returns:
            Dictionary with storage statistics
        """
        with self._lock:
            total_tasks = len(self._tasks)
            
            # Count by status
            status_counts = defaultdict(int)
            for task in self._tasks.values():
                status_counts[task.status.value] += 1
            
            # Calculate age statistics
            now = datetime.now(timezone.utc)
            ages = [(now - task.created_at).total_seconds() / 3600 for task in self._tasks.values()]
            
            return {
                "total_tasks": total_tasks,
                "status_counts": dict(status_counts),
                "oldest_task_hours": max(ages) if ages else 0,
                "newest_task_hours": min(ages) if ages else 0,
                "average_age_hours": sum(ages) / len(ages) if ages else 0,
                "cleanup_enabled": self.cleanup_enabled,
                "max_task_age_hours": self.max_task_age_hours
            }
    
    def _schedule_cleanup(self) -> None:
        """Schedule automatic cleanup task."""
        if not self.cleanup_enabled:
            return
        
        def cleanup_task():
            try:
                self.cleanup_old_tasks()
            except Exception as e:
                logger.error(f"Error during automatic cleanup: {e}")
            finally:
                # Schedule next cleanup
                if self.cleanup_enabled:
                    self._schedule_cleanup()
        
        self._cleanup_timer = threading.Timer(
            self.cleanup_interval_minutes * 60, 
            cleanup_task
        )
        self._cleanup_timer.daemon = True  # Don't prevent program exit
        self._cleanup_timer.start()
        
        logger.debug(f"Scheduled automatic cleanup in {self.cleanup_interval_minutes} minutes")
    
    def stop_cleanup(self) -> None:
        """Stop automatic cleanup if running."""
        if self._cleanup_timer:
            self._cleanup_timer.cancel()
            self._cleanup_timer = None
            logger.debug("Stopped automatic cleanup")
    
    def __del__(self):
        """Cleanup when TaskStore is destroyed."""
        self.stop_cleanup() 