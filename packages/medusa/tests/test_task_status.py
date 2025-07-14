"""
Task Status Interface tests for Medusa library.

This module contains comprehensive tests for the TaskStatusManager class,
including status querying, formatting, history tracking, and performance metrics.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional

from medusa.models import TaskResult, TaskStatus
from medusa.utils.task_status import TaskStatusManager, TaskStatusError, TaskStatusQuery, TaskStatusResponse
from medusa.utils.task_store import TaskStore
from medusa.utils.states import TaskStateManager, TaskState, StateTransition
from medusa.exceptions import MedusaError


class TestTaskStatusManager:
    """Test cases for TaskStatusManager class."""
    
    def test_init_creates_dependencies(self):
        """Test that TaskStatusManager initializes with proper dependencies."""
        manager = TaskStatusManager()
        
        assert manager.task_store is not None
        assert manager.state_manager is not None
        assert hasattr(manager, 'performance_metrics')
        assert hasattr(manager, 'config')
    
    def test_init_with_custom_dependencies(self):
        """Test initialization with custom dependencies."""
        mock_task_store = Mock(spec=TaskStore)
        mock_state_manager = Mock(spec=TaskStateManager)
        
        manager = TaskStatusManager(
            task_store=mock_task_store,
            state_manager=mock_state_manager
        )
        
        assert manager.task_store is mock_task_store
        assert manager.state_manager is mock_state_manager
    
    def test_get_task_status_completed_success(self):
        """Test getting status for completed task with results."""
        # Setup
        task_id = "test_task_123"
        task_result = TaskResult(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            results={
                "youtube_url": "https://youtube.com/watch?v=abc123",
                "facebook_post_id": "123456789"
            }
        )
        
        manager = TaskStatusManager()
        manager.task_store.store_task(task_result)
        
        # Execute
        status_response = manager.get_task_status(task_id)
        
        # Verify
        assert status_response.status == "completed"
        assert status_response.results == {
            "youtube_url": "https://youtube.com/watch?v=abc123",
            "facebook_post_id": "123456789"
        }
        assert status_response.message is None
        assert status_response.error is None
        assert status_response.failed_platform is None
    
    def test_get_task_status_failed_with_error(self):
        """Test getting status for failed task with error details."""
        # Setup
        task_id = "test_task_456"
        task_result = TaskResult(
            task_id=task_id,
            status=TaskStatus.FAILED,
            error="YouTube API error: Video file too large (max 128GB)",
            failed_platform="youtube"
        )
        
        manager = TaskStatusManager()
        manager.task_store.store_task(task_result)
        
        # Execute
        status_response = manager.get_task_status(task_id)
        
        # Verify
        assert status_response.status == "failed"
        assert status_response.error == "YouTube API error: Video file too large (max 128GB)"
        assert status_response.failed_platform == "youtube"
        assert status_response.results is None
        assert status_response.message is None
    
    def test_get_task_status_in_progress_with_message(self):
        """Test getting status for in-progress task with message."""
        # Setup
        task_id = "test_task_789"
        task_result = TaskResult(
            task_id=task_id,
            status=TaskStatus.IN_PROGRESS,
            message="Uploading to YouTube..."
        )
        
        manager = TaskStatusManager()
        manager.task_store.store_task(task_result)
        
        # Execute
        status_response = manager.get_task_status(task_id)
        
        # Verify
        assert status_response.status == "in_progress"
        assert status_response.message == "Uploading to YouTube..."
        assert status_response.results is None
        assert status_response.error is None
        assert status_response.failed_platform is None
    
    def test_get_task_status_pending(self):
        """Test getting status for pending task."""
        # Setup
        task_id = "test_task_pending"
        task_result = TaskResult(
            task_id=task_id,
            status=TaskStatus.PENDING
        )
        
        manager = TaskStatusManager()
        manager.task_store.store_task(task_result)
        
        # Execute
        status_response = manager.get_task_status(task_id)
        
        # Verify
        assert status_response.status == "pending"
        assert status_response.message is None
        assert status_response.results is None
        assert status_response.error is None
        assert status_response.failed_platform is None
    
    def test_get_task_status_not_found(self):
        """Test getting status for non-existent task."""
        manager = TaskStatusManager()
        
        with pytest.raises(TaskStatusError) as exc_info:
            manager.get_task_status("non_existent_task")
        
        assert "Task not found" in str(exc_info.value)
    
    def test_get_task_status_with_history(self):
        """Test getting status with state history included."""
        # Setup
        task_id = "test_task_history"
        task_result = TaskResult(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            results={"youtube_url": "https://youtube.com/watch?v=test"}
        )
        
        manager = TaskStatusManager()
        manager.task_store.store_task(task_result)
        
        # Mock state history
        mock_history = Mock()
        mock_history.transitions = [
            StateTransition(None, TaskState.PENDING, datetime.now(timezone.utc)),
            StateTransition(TaskState.PENDING, TaskState.IN_PROGRESS, datetime.now(timezone.utc)),
            StateTransition(TaskState.IN_PROGRESS, TaskState.COMPLETED, datetime.now(timezone.utc))
        ]
        manager.state_manager.get_task_history = Mock(return_value=mock_history)
        
        # Execute
        status_response = manager.get_task_status(task_id, include_history=True)
        
        # Verify
        assert status_response.status == "completed"
        assert status_response.history is not None
        assert len(status_response.history) == 3
    
    def test_get_task_status_with_progress(self):
        """Test getting status with progress information."""
        # Setup
        task_id = "test_task_progress"
        task_result = TaskResult(
            task_id=task_id,
            status=TaskStatus.IN_PROGRESS,
            message="Processing platforms...",
            results={"progress": {"completed": 1, "total": 3, "percentage": 33.33}}
        )
        
        manager = TaskStatusManager()
        manager.task_store.store_task(task_result)
        
        # Execute
        status_response = manager.get_task_status(task_id, include_progress=True)
        
        # Verify
        assert status_response.status == "in_progress"
        assert status_response.progress is not None
        assert status_response.progress["percentage"] == 33.33
    
    def test_get_multiple_task_statuses(self):
        """Test getting statuses for multiple tasks."""
        # Setup
        task_ids = ["task_1", "task_2", "task_3"]
        tasks = [
            TaskResult(task_id="task_1", status=TaskStatus.COMPLETED),
            TaskResult(task_id="task_2", status=TaskStatus.IN_PROGRESS),
            TaskResult(task_id="task_3", status=TaskStatus.FAILED, error="Test error")
        ]
        
        manager = TaskStatusManager()
        for task in tasks:
            manager.task_store.store_task(task)
        
        # Execute
        statuses = manager.get_multiple_task_statuses(task_ids)
        
        # Verify
        assert len(statuses) == 3
        assert statuses[0].status == "completed"
        assert statuses[1].status == "in_progress"
        assert statuses[2].status == "failed"
        assert statuses[2].error == "Test error"
    
    def test_get_multiple_task_statuses_with_missing(self):
        """Test getting statuses for multiple tasks with some missing."""
        # Setup
        task_ids = ["task_1", "missing_task", "task_3"]
        tasks = [
            TaskResult(task_id="task_1", status=TaskStatus.COMPLETED),
            TaskResult(task_id="task_3", status=TaskStatus.PENDING)
        ]
        
        manager = TaskStatusManager()
        for task in tasks:
            manager.task_store.store_task(task)
        
        # Execute
        statuses = manager.get_multiple_task_statuses(task_ids, skip_missing=True)
        
        # Verify
        assert len(statuses) == 2
        assert statuses[0].status == "completed"
        assert statuses[1].status == "pending"
    
    def test_get_multiple_task_statuses_strict_mode(self):
        """Test getting statuses for multiple tasks in strict mode."""
        # Setup
        task_ids = ["task_1", "missing_task"]
        tasks = [TaskResult(task_id="task_1", status=TaskStatus.COMPLETED)]
        
        manager = TaskStatusManager()
        for task in tasks:
            manager.task_store.store_task(task)
        
        # Execute & Verify
        with pytest.raises(TaskStatusError) as exc_info:
            manager.get_multiple_task_statuses(task_ids, skip_missing=False)
        
        assert "missing_task" in str(exc_info.value)
    
    def test_query_tasks_by_status(self):
        """Test querying tasks by status."""
        # Setup
        tasks = [
            TaskResult(task_id="pending_1", status=TaskStatus.PENDING),
            TaskResult(task_id="pending_2", status=TaskStatus.PENDING),
            TaskResult(task_id="completed_1", status=TaskStatus.COMPLETED),
            TaskResult(task_id="failed_1", status=TaskStatus.FAILED)
        ]
        
        manager = TaskStatusManager()
        for task in tasks:
            manager.task_store.store_task(task)
        
        # Execute
        query = TaskStatusQuery(status_filter=[TaskStatus.PENDING])
        results = manager.query_task_statuses(query)
        
        # Verify
        assert len(results) == 2
        assert all(result.status == "pending" for result in results)
    
    def test_query_tasks_by_time_range(self):
        """Test querying tasks by time range."""
        # Setup
        now = datetime.now(timezone.utc)
        old_time = now - timedelta(hours=2)
        
        tasks = [
            TaskResult(task_id="old_task", status=TaskStatus.COMPLETED, created_at=old_time),
            TaskResult(task_id="new_task", status=TaskStatus.COMPLETED, created_at=now)
        ]
        
        manager = TaskStatusManager()
        for task in tasks:
            manager.task_store.store_task(task)
        
        # Execute
        query = TaskStatusQuery(created_after=now - timedelta(hours=1))
        results = manager.query_task_statuses(query)
        
        # Verify
        assert len(results) == 1
        assert results[0].task_id == "new_task"
    
    def test_query_tasks_with_pagination(self):
        """Test querying tasks with pagination."""
        # Setup
        tasks = [
            TaskResult(task_id=f"task_{i}", status=TaskStatus.COMPLETED)
            for i in range(10)
        ]
        
        manager = TaskStatusManager()
        for task in tasks:
            manager.task_store.store_task(task)
        
        # Execute - First page
        query = TaskStatusQuery(limit=5, offset=0)
        results = manager.query_task_statuses(query)
        
        # Verify
        assert len(results) == 5
        
        # Execute - Second page
        query = TaskStatusQuery(limit=5, offset=5)
        results = manager.query_task_statuses(query)
        
        # Verify
        assert len(results) == 5
    
    def test_get_task_performance_metrics(self):
        """Test getting performance metrics for tasks."""
        # Setup
        task_id = "test_task_metrics"
        task_result = TaskResult(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            created_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            updated_at=datetime.now(timezone.utc)
        )
        
        manager = TaskStatusManager()
        manager.task_store.store_task(task_result)
        
        # Mock state history with durations
        mock_history = Mock()
        mock_history.get_state_durations.return_value = {
            TaskState.PENDING: timedelta(seconds=30),
            TaskState.IN_PROGRESS: timedelta(minutes=4, seconds=30)
        }
        manager.state_manager.get_task_history = Mock(return_value=mock_history)
        
        # Execute
        metrics = manager.get_task_performance_metrics(task_id)
        
        # Verify
        assert metrics["task_id"] == task_id
        assert metrics["total_duration"] > 0
        assert "state_durations" in metrics
        assert TaskState.PENDING.value in metrics["state_durations"]
        assert TaskState.IN_PROGRESS.value in metrics["state_durations"]
    
    def test_get_aggregated_performance_metrics(self):
        """Test getting aggregated performance metrics."""
        # Setup
        tasks = [
            TaskResult(
                task_id=f"task_{i}",
                status=TaskStatus.COMPLETED,
                created_at=datetime.now(timezone.utc) - timedelta(minutes=i+1),
                updated_at=datetime.now(timezone.utc)
            )
            for i in range(5)
        ]
        
        manager = TaskStatusManager()
        for task in tasks:
            manager.task_store.store_task(task)
        
        # Execute
        metrics = manager.get_aggregated_performance_metrics()
        
        # Verify
        assert metrics["total_tasks"] == 5
        assert metrics["average_duration"] > 0
        assert "status_breakdown" in metrics
        assert metrics["status_breakdown"]["completed"] == 5
    
    def test_format_status_response_completed(self):
        """Test formatting completed status response."""
        # Setup
        task_result = TaskResult(
            task_id="test_task",
            status=TaskStatus.COMPLETED,
            results={"youtube_url": "https://youtube.com/watch?v=test"}
        )
        
        manager = TaskStatusManager()
        
        # Execute
        response = manager._format_status_response(task_result)
        
        # Verify
        response_dict = response.to_dict()
        assert response_dict["status"] == "completed"
        assert response_dict["results"]["youtube_url"] == "https://youtube.com/watch?v=test"
        assert "error" not in response_dict or response_dict["error"] is None
    
    def test_format_status_response_failed(self):
        """Test formatting failed status response."""
        # Setup
        task_result = TaskResult(
            task_id="test_task",
            status=TaskStatus.FAILED,
            error="Test error message",
            failed_platform="youtube"
        )
        
        manager = TaskStatusManager()
        
        # Execute
        response = manager._format_status_response(task_result)
        
        # Verify
        response_dict = response.to_dict()
        assert response_dict["status"] == "failed"
        assert response_dict["error"] == "Test error message"
        assert response_dict["failed_platform"] == "youtube"
        assert "results" not in response_dict or response_dict["results"] is None
    
    def test_format_status_response_in_progress(self):
        """Test formatting in-progress status response."""
        # Setup
        task_result = TaskResult(
            task_id="test_task",
            status=TaskStatus.IN_PROGRESS,
            message="Processing upload..."
        )
        
        manager = TaskStatusManager()
        
        # Execute
        response = manager._format_status_response(task_result)
        
        # Verify
        response_dict = response.to_dict()
        assert response_dict["status"] == "in_progress"
        assert response_dict["message"] == "Processing upload..."
        assert "results" not in response_dict or response_dict["results"] is None
        assert "error" not in response_dict or response_dict["error"] is None
    
    def test_clear_task_metrics(self):
        """Test clearing performance metrics."""
        # Setup
        manager = TaskStatusManager()
        manager.performance_metrics["test_metric"] = "test_value"
        
        # Execute
        manager.clear_performance_metrics()
        
        # Verify
        assert len(manager.performance_metrics) == 0
    
    def test_invalid_task_id_empty(self):
        """Test handling of empty task ID."""
        manager = TaskStatusManager()
        
        with pytest.raises(TaskStatusError) as exc_info:
            manager.get_task_status("")
        
        assert "Task ID cannot be empty" in str(exc_info.value)
    
    def test_invalid_task_id_none(self):
        """Test handling of None task ID."""
        manager = TaskStatusManager()
        
        with pytest.raises(TaskStatusError) as exc_info:
            manager.get_task_status(None)
        
        assert "Task ID cannot be empty" in str(exc_info.value)
    
    def test_concurrent_status_access(self):
        """Test concurrent access to task status."""
        import threading
        import time
        
        # Setup
        task_id = "concurrent_task"
        task_result = TaskResult(task_id=task_id, status=TaskStatus.IN_PROGRESS)
        
        manager = TaskStatusManager()
        manager.task_store.store_task(task_result)
        
        results = []
        errors = []
        
        def get_status():
            try:
                status = manager.get_task_status(task_id)
                results.append(status)
            except Exception as e:
                errors.append(e)
        
        # Execute multiple threads
        threads = [threading.Thread(target=get_status) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # Verify
        assert len(errors) == 0
        assert len(results) == 10
        assert all(result.status == "in_progress" for result in results)


class TestTaskStatusQuery:
    """Test cases for TaskStatusQuery class."""
    
    def test_query_initialization(self):
        """Test TaskStatusQuery initialization."""
        query = TaskStatusQuery()
        
        assert query.status_filter is None
        assert query.created_after is None
        assert query.created_before is None
        assert query.limit is None
        assert query.offset == 0
    
    def test_query_with_parameters(self):
        """Test TaskStatusQuery with parameters."""
        now = datetime.now(timezone.utc)
        
        query = TaskStatusQuery(
            status_filter=[TaskStatus.PENDING, TaskStatus.COMPLETED],
            created_after=now - timedelta(hours=1),
            created_before=now,
            limit=10,
            offset=5
        )
        
        assert query.status_filter == [TaskStatus.PENDING, TaskStatus.COMPLETED]
        assert query.created_after == now - timedelta(hours=1)
        assert query.created_before == now
        assert query.limit == 10
        assert query.offset == 5
    
    def test_query_validation(self):
        """Test TaskStatusQuery validation."""
        # Test invalid limit
        with pytest.raises(ValueError):
            TaskStatusQuery(limit=-1)
        
        # Test invalid offset
        with pytest.raises(ValueError):
            TaskStatusQuery(offset=-1)
        
        # Test invalid time range
        now = datetime.now(timezone.utc)
        with pytest.raises(ValueError):
            TaskStatusQuery(
                created_after=now,
                created_before=now - timedelta(hours=1)
            )


class TestTaskStatusResponse:
    """Test cases for TaskStatusResponse class."""
    
    def test_response_initialization(self):
        """Test TaskStatusResponse initialization."""
        response = TaskStatusResponse(
            task_id="test_task",
            status="completed"
        )
        
        assert response.task_id == "test_task"
        assert response.status == "completed"
        assert response.message is None
        assert response.error is None
        assert response.failed_platform is None
        assert response.results is None
        assert response.history is None
        assert response.progress is None
        assert response.created_at is not None
        assert response.updated_at is not None
    
    def test_response_to_dict(self):
        """Test TaskStatusResponse to_dict method."""
        response = TaskStatusResponse(
            task_id="test_task",
            status="completed",
            results={"youtube_url": "https://youtube.com/test"}
        )
        
        response_dict = response.to_dict()
        
        assert response_dict["status"] == "completed"
        assert response_dict["results"]["youtube_url"] == "https://youtube.com/test"
        # task_id should not be in response according to spec
        assert "task_id" not in response_dict
        assert "message" not in response_dict
        assert "error" not in response_dict
    
    def test_response_to_dict_failed(self):
        """Test TaskStatusResponse to_dict for failed status."""
        response = TaskStatusResponse(
            task_id="test_task",
            status="failed",
            error="Test error",
            failed_platform="youtube"
        )
        
        response_dict = response.to_dict()
        
        assert response_dict["status"] == "failed"
        assert response_dict["error"] == "Test error"
        assert response_dict["failed_platform"] == "youtube"
        assert "results" not in response_dict
        assert "message" not in response_dict
    
    def test_response_to_dict_in_progress(self):
        """Test TaskStatusResponse to_dict for in-progress status."""
        response = TaskStatusResponse(
            task_id="test_task",
            status="in_progress",
            message="Processing..."
        )
        
        response_dict = response.to_dict()
        
        assert response_dict["status"] == "in_progress"
        assert response_dict["message"] == "Processing..."
        assert "results" not in response_dict
        assert "error" not in response_dict
    
    def test_response_to_dict_with_history(self):
        """Test TaskStatusResponse to_dict with history."""
        history = [
            {"from_state": None, "to_state": "pending", "timestamp": "2024-01-01T00:00:00Z"},
            {"from_state": "pending", "to_state": "completed", "timestamp": "2024-01-01T00:01:00Z"}
        ]
        
        response = TaskStatusResponse(
            task_id="test_task",
            status="completed",
            history=history
        )
        
        response_dict = response.to_dict()
        
        assert response_dict["history"] == history
        assert len(response_dict["history"]) == 2
    
    def test_response_spec_compliance_completed(self):
        """Test that response format matches spec for completed status."""
        response = TaskStatusResponse(
            task_id="test_task",
            status="completed",
            results={
                "youtube_url": "https://youtube.com/watch?v=abc123",
                "facebook_post_id": "123456789"
            }
        )
        
        response_dict = response.to_dict()
        
        # Should match spec exactly
        expected_keys = {"status", "results"}
        assert set(response_dict.keys()) == expected_keys
        assert response_dict["status"] == "completed"
        assert response_dict["results"]["youtube_url"] == "https://youtube.com/watch?v=abc123"
        assert response_dict["results"]["facebook_post_id"] == "123456789"
    
    def test_response_spec_compliance_failed(self):
        """Test that response format matches spec for failed status."""
        response = TaskStatusResponse(
            task_id="test_task",
            status="failed",
            error="YouTube API error: Video file too large (max 128GB)",
            failed_platform="youtube"
        )
        
        response_dict = response.to_dict()
        
        # Should match spec exactly
        expected_keys = {"status", "error", "failed_platform"}
        assert set(response_dict.keys()) == expected_keys
        assert response_dict["status"] == "failed"
        assert response_dict["error"] == "YouTube API error: Video file too large (max 128GB)"
        assert response_dict["failed_platform"] == "youtube"
    
    def test_response_spec_compliance_in_progress(self):
        """Test that response format matches spec for in-progress status."""
        response = TaskStatusResponse(
            task_id="test_task",
            status="in_progress",
            message="Uploading to YouTube..."
        )
        
        response_dict = response.to_dict()
        
        # Should match spec exactly
        expected_keys = {"status", "message"}
        assert set(response_dict.keys()) == expected_keys
        assert response_dict["status"] == "in_progress"
        assert response_dict["message"] == "Uploading to YouTube..."


class TestTaskStatusError:
    """Test cases for TaskStatusError exception."""
    
    def test_error_creation(self):
        """Test TaskStatusError creation."""
        error = TaskStatusError("Test error message")
        
        assert "Test error message" in str(error)
        assert isinstance(error, MedusaError)
    
    def test_error_with_task_id(self):
        """Test TaskStatusError with task ID context."""
        error = TaskStatusError("Task not found", task_id="test_task_123")
        
        assert "test_task_123" in str(error)
        assert "Task not found" in str(error) 