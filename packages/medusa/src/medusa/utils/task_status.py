"""
Task Status Interface for Medusa library.

This module provides comprehensive task status management functionality including:
- TaskStatusManager for status operations and formatted responses
- Task status querying with filtering and pagination
- Performance metrics collection and tracking
- Status history management with progress indicators
- Spec-compliant response formatting
"""

import logging
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from ..models import TaskResult, TaskStatus
from ..utils.task_store import TaskStore
from ..utils.states import TaskStateManager
from ..exceptions import MedusaError

# Set up logging
logger = logging.getLogger(__name__)


class TaskStatusError(MedusaError):
    """Exception raised for task status operations."""
    
    def __init__(self, message: str, task_id: Optional[str] = None):
        """
        Initialize TaskStatusError.
        
        Args:
            message: Error message
            task_id: Optional task ID for context
        """
        if task_id:
            message = f"Task {task_id}: {message}"
        super().__init__(message)
        self.task_id = task_id


@dataclass
class TaskStatusQuery:
    """Query parameters for filtering task statuses."""
    status_filter: Optional[List[TaskStatus]] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    limit: Optional[int] = None
    offset: int = 0
    
    def __post_init__(self):
        """Validate query parameters."""
        if self.limit is not None and self.limit < 0:
            raise ValueError("Limit must be non-negative")
        
        if self.offset < 0:
            raise ValueError("Offset must be non-negative")
        
        if (self.created_after is not None and 
            self.created_before is not None and 
            self.created_after >= self.created_before):
            raise ValueError("created_after must be before created_before")


@dataclass
class TaskStatusResponse:
    """Formatted response for task status according to spec."""
    task_id: str
    status: str
    message: Optional[str] = None
    error: Optional[str] = None
    failed_platform: Optional[str] = None
    results: Optional[Dict[str, Any]] = None
    history: Optional[List[Dict[str, Any]]] = None
    progress: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert response to dictionary matching API specification exactly.
        
        Returns:
            Dictionary representation following spec format
        """
        result: Dict[str, Any] = {"status": self.status}
        
        # Add fields based on status following spec
        if self.status == "completed" and self.results:
            result["results"] = self.results
        elif self.status == "failed":
            if self.error:
                result["error"] = self.error
            if self.failed_platform:
                result["failed_platform"] = self.failed_platform
        elif self.status == "in_progress" and self.message:
            result["message"] = self.message
        
        # Add optional fields if present and requested
        if self.history is not None:
            result["history"] = self.history
        if self.progress is not None:
            result["progress"] = self.progress
            
        return result


class TaskStatusManager:
    """
    Manager for task status operations with formatted responses.
    
    Provides comprehensive task status functionality including:
    - Status querying with spec-compliant formatting
    - Performance metrics collection
    - History tracking with progress indicators
    - Bulk status operations
    - Filtering and pagination support
    """
    
    def __init__(self, 
                 task_store: Optional[TaskStore] = None,
                 state_manager: Optional[TaskStateManager] = None):
        """
        Initialize TaskStatusManager.
        
        Args:
            task_store: Optional TaskStore instance (creates new if None)
            state_manager: Optional TaskStateManager instance (creates new if None)
        """
        self.task_store = task_store or TaskStore()
        self.state_manager = state_manager or TaskStateManager()
        self.performance_metrics: Dict[str, Any] = {}
        self.config: Dict[str, Any] = {
            "default_include_history": False,
            "default_include_progress": False,
            "max_query_limit": 1000
        }
        self._lock = threading.RLock()
        
        logger.debug("TaskStatusManager initialized")
    
    def get_task_status(self, 
                       task_id: Optional[str],
                       include_history: bool = False,
                       include_progress: bool = False) -> TaskStatusResponse:
        """
        Get formatted status for a single task.
        
        Args:
            task_id: Task ID to query
            include_history: Whether to include state history
            include_progress: Whether to include progress information
            
        Returns:
            TaskStatusResponse with formatted status
            
        Raises:
            TaskStatusError: If task not found or invalid parameters
        """
        if not task_id or (isinstance(task_id, str) and not task_id.strip()):
            raise TaskStatusError("Task ID cannot be empty")
        
        with self._lock:
            # Get task from store
            task_result = self.task_store.get_task(task_id)
            if task_result is None:
                raise TaskStatusError("Task not found", task_id=task_id)
            
            # Format basic response
            response = self._format_status_response(task_result)
            
            # Add history if requested
            if include_history:
                try:
                    history = self.state_manager.get_task_history(task_id)
                    if history and history.transitions:
                        response.history = [
                            transition.to_dict() for transition in history.transitions
                        ]
                except Exception as e:
                    logger.warning(f"Failed to get history for task {task_id}: {e}")
            
            # Add progress if requested and available
            if include_progress and task_result.results:
                progress_data = task_result.results.get("progress")
                if progress_data:
                    response.progress = progress_data
            
            return response
    
    def get_multiple_task_statuses(self, 
                                  task_ids: List[str],
                                  skip_missing: bool = True,
                                  include_history: bool = False,
                                  include_progress: bool = False) -> List[TaskStatusResponse]:
        """
        Get statuses for multiple tasks.
        
        Args:
            task_ids: List of task IDs to query
            skip_missing: Whether to skip missing tasks (True) or raise error (False)
            include_history: Whether to include state history
            include_progress: Whether to include progress information
            
        Returns:
            List of TaskStatusResponse objects
            
        Raises:
            TaskStatusError: If task not found and skip_missing=False
        """
        responses = []
        missing_tasks = []
        
        for task_id in task_ids:
            try:
                response = self.get_task_status(
                    task_id, 
                    include_history=include_history,
                    include_progress=include_progress
                )
                responses.append(response)
            except TaskStatusError:
                if skip_missing:
                    missing_tasks.append(task_id)
                    continue
                else:
                    raise
        
        if missing_tasks:
            logger.debug(f"Skipped missing tasks: {missing_tasks}")
        
        return responses
    
    def query_task_statuses(self, 
                           query: TaskStatusQuery,
                           include_history: bool = False,
                           include_progress: bool = False) -> List[TaskStatusResponse]:
        """
        Query task statuses with filtering and pagination.
        
        Args:
            query: TaskStatusQuery with filter parameters
            include_history: Whether to include state history
            include_progress: Whether to include progress information
            
        Returns:
            List of TaskStatusResponse objects matching query
        """
        with self._lock:
            # Get all tasks from store
            all_tasks = self.task_store.get_all_tasks()
            
            # Apply status filter
            if query.status_filter:
                all_tasks = [t for t in all_tasks if t.status in query.status_filter]
            
            # Apply time range filters
            if query.created_after:
                all_tasks = [t for t in all_tasks if t.created_at >= query.created_after]
            
            if query.created_before:
                all_tasks = [t for t in all_tasks if t.created_at <= query.created_before]
            
            # Sort by creation time (newest first)
            all_tasks.sort(key=lambda t: t.created_at, reverse=True)
            
            # Apply pagination
            start_idx = query.offset
            if query.limit is not None:
                end_idx = start_idx + query.limit
                all_tasks = all_tasks[start_idx:end_idx]
            else:
                all_tasks = all_tasks[start_idx:]
            
            # Convert to responses
            responses = []
            for task in all_tasks:
                response = self._format_status_response(task)
                
                # Add history if requested
                if include_history:
                    try:
                        history = self.state_manager.get_task_history(task.task_id)
                        if history and history.transitions:
                            response.history = [
                                transition.to_dict() for transition in history.transitions
                            ]
                    except Exception as e:
                        logger.warning(f"Failed to get history for task {task.task_id}: {e}")
                
                # Add progress if requested and available
                if include_progress and task.results:
                    progress_data = task.results.get("progress")
                    if progress_data:
                        response.progress = progress_data
                
                responses.append(response)
            
            return responses
    
    def get_task_performance_metrics(self, task_id: str) -> Dict[str, Any]:
        """
        Get performance metrics for a specific task.
        
        Args:
            task_id: Task ID to get metrics for
            
        Returns:
            Dictionary with performance metrics
            
        Raises:
            TaskStatusError: If task not found
        """
        with self._lock:
            task_result = self.task_store.get_task(task_id)
            if task_result is None:
                raise TaskStatusError("Task not found", task_id=task_id)
            
            # Calculate total duration
            total_duration = (task_result.updated_at - task_result.created_at).total_seconds()
            
            metrics = {
                "task_id": task_id,
                "status": task_result.status.value,
                "total_duration": total_duration,
                "created_at": task_result.created_at.isoformat(),
                "updated_at": task_result.updated_at.isoformat()
            }
            
            # Get state durations if available
            try:
                history = self.state_manager.get_task_history(task_id)
                if history:
                    state_durations = history.get_state_durations()
                    metrics["state_durations"] = {
                        state.value: duration.total_seconds()
                        for state, duration in state_durations.items()
                    }
            except Exception as e:
                logger.warning(f"Failed to get state durations for task {task_id}: {e}")
                metrics["state_durations"] = {}
            
            return metrics
    
    def get_aggregated_performance_metrics(self) -> Dict[str, Any]:
        """
        Get aggregated performance metrics for all tasks.
        
        Returns:
            Dictionary with aggregated metrics
        """
        with self._lock:
            all_tasks = self.task_store.get_all_tasks()
            
            if not all_tasks:
                return {
                    "total_tasks": 0,
                    "average_duration": 0,
                    "status_breakdown": {},
                    "generated_at": datetime.now(timezone.utc).isoformat()
                }
            
            # Calculate basic metrics
            total_tasks = len(all_tasks)
            total_duration = sum(
                (task.updated_at - task.created_at).total_seconds()
                for task in all_tasks
            )
            average_duration = total_duration / total_tasks if total_tasks > 0 else 0
            
            # Status breakdown
            status_breakdown = {}
            for task in all_tasks:
                status = task.status.value
                status_breakdown[status] = status_breakdown.get(status, 0) + 1
            
            # Duration breakdown by status
            duration_by_status = {}
            for task in all_tasks:
                status = task.status.value
                duration = (task.updated_at - task.created_at).total_seconds()
                if status not in duration_by_status:
                    duration_by_status[status] = []
                duration_by_status[status].append(duration)
            
            # Calculate average duration by status
            avg_duration_by_status = {}
            for status, durations in duration_by_status.items():
                avg_duration_by_status[status] = sum(durations) / len(durations)
            
            return {
                "total_tasks": total_tasks,
                "average_duration": average_duration,
                "status_breakdown": status_breakdown,
                "average_duration_by_status": avg_duration_by_status,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
    
    def clear_performance_metrics(self) -> None:
        """Clear stored performance metrics."""
        with self._lock:
            self.performance_metrics.clear()
            logger.debug("Performance metrics cleared")
    
    def _format_status_response(self, task_result: TaskResult) -> TaskStatusResponse:
        """
        Format TaskResult into spec-compliant TaskStatusResponse.
        
        Args:
            task_result: TaskResult to format
            
        Returns:
            Formatted TaskStatusResponse
        """
        # Map TaskStatus to string values
        status_mapping = {
            TaskStatus.PENDING: "pending",
            TaskStatus.IN_PROGRESS: "in_progress", 
            TaskStatus.COMPLETED: "completed",
            TaskStatus.FAILED: "failed",
            TaskStatus.CANCELLED: "cancelled"
        }
        
        status_str = status_mapping.get(task_result.status, task_result.status.value)
        
        response = TaskStatusResponse(
            task_id=task_result.task_id,
            status=status_str,
            message=task_result.message,
            error=task_result.error,
            failed_platform=task_result.failed_platform,
            results=task_result.results if task_result.results else None,
            created_at=task_result.created_at,
            updated_at=task_result.updated_at
        )
        
        return response 