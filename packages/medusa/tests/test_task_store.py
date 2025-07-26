"""
Tests for TaskStore - In-memory task storage system.

This module tests the TaskStore class with comprehensive coverage including:
- Thread-safe operations
- Task lifecycle management
- CRUD operations (Create, Read, Update, Delete)
- Task querying and filtering capabilities
- Automatic cleanup of old tasks
- Concurrent access scenarios
"""

import pytest
import threading
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from medusa.utils.task_store import TaskStore, TaskStoreError
from medusa.models import TaskResult, TaskStatus
from medusa.utils.task_id import TaskIDGenerator


class TestTaskStore:
    """Test cases for TaskStore functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.task_store = TaskStore()
        self.task_id_generator = TaskIDGenerator()
    
    def teardown_method(self):
        """Clean up after tests."""
        self.task_store.clear_all_tasks()
    
    def create_sample_task_result(self, task_id: str = None, status: TaskStatus = TaskStatus.PENDING) -> TaskResult:
        """Create a sample TaskResult for testing."""
        if not task_id:
            task_id = self.task_id_generator.generate_task_id()
        
        return TaskResult(
            task_id=task_id,
            status=status,
            message="Test task",
            results={"test": "data"}
        )
    
    def test_store_task_success(self):
        """Test successful task storage."""
        task = self.create_sample_task_result()
        
        result = self.task_store.store_task(task)
        assert result is True
        
        # Verify task is stored
        stored_task = self.task_store.get_task(task.task_id)
        assert stored_task is not None
        assert stored_task.task_id == task.task_id
        assert stored_task.status == task.status
    
    def test_store_duplicate_task_fails(self):
        """Test that storing duplicate task ID fails."""
        task = self.create_sample_task_result()
        
        # Store first time - should succeed
        assert self.task_store.store_task(task) is True
        
        # Store same task ID again - should fail
        duplicate_task = self.create_sample_task_result(task_id=task.task_id)
        with pytest.raises(TaskStoreError, match="Task .* already exists"):
            self.task_store.store_task(duplicate_task)
    
    def test_get_task_success(self):
        """Test successful task retrieval."""
        task = self.create_sample_task_result()
        self.task_store.store_task(task)
        
        retrieved_task = self.task_store.get_task(task.task_id)
        assert retrieved_task is not None
        assert retrieved_task.task_id == task.task_id
        assert retrieved_task.status == task.status
        assert retrieved_task.message == task.message
    
    def test_get_nonexistent_task_returns_none(self):
        """Test retrieving non-existent task returns None."""
        fake_task_id = self.task_id_generator.generate_task_id()
        result = self.task_store.get_task(fake_task_id)
        assert result is None
    
    def test_update_task_success(self):
        """Test successful task update."""
        task = self.create_sample_task_result()
        self.task_store.store_task(task)
        
        # Update task status
        task.status = TaskStatus.IN_PROGRESS
        task.message = "Updated message"
        
        result = self.task_store.update_task(task)
        assert result is True
        
        # Verify update
        updated_task = self.task_store.get_task(task.task_id)
        assert updated_task.status == TaskStatus.IN_PROGRESS
        assert updated_task.message == "Updated message"
    
    def test_update_nonexistent_task_fails(self):
        """Test updating non-existent task fails."""
        task = self.create_sample_task_result()
        
        with pytest.raises(TaskStoreError, match="Task .* not found"):
            self.task_store.update_task(task)
    
    def test_delete_task_success(self):
        """Test successful task deletion."""
        task = self.create_sample_task_result()
        self.task_store.store_task(task)
        
        result = self.task_store.delete_task(task.task_id)
        assert result is True
        
        # Verify deletion
        deleted_task = self.task_store.get_task(task.task_id)
        assert deleted_task is None
    
    def test_delete_nonexistent_task_returns_false(self):
        """Test deleting non-existent task returns False."""
        fake_task_id = self.task_id_generator.generate_task_id()
        result = self.task_store.delete_task(fake_task_id)
        assert result is False


class TestTaskStoreQuerying:
    """Test task querying and filtering capabilities."""
    
    def setup_method(self):
        self.task_store = TaskStore()
        self.task_id_generator = TaskIDGenerator()
        
        # Create sample tasks for testing
        self.sample_tasks = []
        for i in range(5):
            status = [TaskStatus.PENDING, TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED, TaskStatus.FAILED][i % 4]
            task = self.create_sample_task_result(status=status)
            self.sample_tasks.append(task)
            self.task_store.store_task(task)
    
    def create_sample_task_result(self, task_id: str = None, status: TaskStatus = TaskStatus.PENDING) -> TaskResult:
        """Create a sample TaskResult for testing."""
        if not task_id:
            task_id = self.task_id_generator.generate_task_id()
        
        return TaskResult(
            task_id=task_id,
            status=status,
            message="Test task",
            results={"test": "data"}
        )
    
    def test_get_all_tasks(self):
        """Test retrieving all tasks."""
        all_tasks = self.task_store.get_all_tasks()
        assert len(all_tasks) == 5
        
        # Verify all tasks are present
        task_ids = {task.task_id for task in all_tasks}
        expected_ids = {task.task_id for task in self.sample_tasks}
        assert task_ids == expected_ids
    
    def test_get_tasks_by_status(self):
        """Test filtering tasks by status."""
        pending_tasks = self.task_store.get_tasks_by_status(TaskStatus.PENDING)
        completed_tasks = self.task_store.get_tasks_by_status(TaskStatus.COMPLETED)
        
        # Count expected tasks by status
        expected_pending = sum(1 for task in self.sample_tasks if task.status == TaskStatus.PENDING)
        expected_completed = sum(1 for task in self.sample_tasks if task.status == TaskStatus.COMPLETED)
        
        assert len(pending_tasks) == expected_pending
        assert len(completed_tasks) == expected_completed
        
        # Verify all returned tasks have correct status
        for task in pending_tasks:
            assert task.status == TaskStatus.PENDING
        for task in completed_tasks:
            assert task.status == TaskStatus.COMPLETED
    
    def test_get_tasks_by_status_multiple(self):
        """Test filtering tasks by multiple statuses."""
        statuses = [TaskStatus.PENDING, TaskStatus.IN_PROGRESS]
        filtered_tasks = self.task_store.get_tasks_by_status(statuses)
        
        # Count expected tasks
        expected_count = sum(1 for task in self.sample_tasks if task.status in statuses)
        assert len(filtered_tasks) == expected_count
        
        # Verify all returned tasks have correct status
        for task in filtered_tasks:
            assert task.status in statuses
    
    def test_get_tasks_created_after(self):
        """Test filtering tasks by creation time."""
        # Create a new task after a delay
        time.sleep(0.1)  # Small delay to ensure different timestamps
        cutoff_time = datetime.now(timezone.utc)
        time.sleep(0.1)
        
        new_task = self.create_sample_task_result()
        self.task_store.store_task(new_task)
        
        # Get tasks created after cutoff
        recent_tasks = self.task_store.get_tasks_created_after(cutoff_time)
        assert len(recent_tasks) == 1
        assert recent_tasks[0].task_id == new_task.task_id
    
    def test_get_tasks_count(self):
        """Test getting task count."""
        total_count = self.task_store.get_task_count()
        assert total_count == 5
        
        # Test filtered count
        pending_count = self.task_store.get_task_count(status=TaskStatus.PENDING)
        expected_pending = sum(1 for task in self.sample_tasks if task.status == TaskStatus.PENDING)
        assert pending_count == expected_pending
    
    def test_task_exists(self):
        """Test checking if task exists."""
        existing_task = self.sample_tasks[0]
        fake_task_id = self.task_id_generator.generate_task_id()
        
        assert self.task_store.task_exists(existing_task.task_id) is True
        assert self.task_store.task_exists(fake_task_id) is False


class TestTaskStoreThreadSafety:
    """Test thread safety and concurrent access."""
    
    def setup_method(self):
        self.task_store = TaskStore()
        self.task_id_generator = TaskIDGenerator()
        self.results = []
        self.errors = []
    
    def test_concurrent_task_storage(self):
        """Test concurrent task storage from multiple threads."""
        num_threads = 10
        tasks_per_thread = 5
        threads = []
        
        def store_tasks():
            try:
                for i in range(tasks_per_thread):
                    task = self.create_sample_task_result()
                    result = self.task_store.store_task(task)
                    self.results.append((threading.current_thread().name, task.task_id, result))
            except Exception as e:
                self.errors.append((threading.current_thread().name, str(e)))
        
        # Create and start threads
        for i in range(num_threads):
            thread = threading.Thread(target=store_tasks, name=f"Thread-{i}")
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(self.errors) == 0, f"Errors occurred: {self.errors}"
        assert len(self.results) == num_threads * tasks_per_thread
        
        # Verify all tasks were stored
        total_tasks = self.task_store.get_task_count()
        assert total_tasks == num_threads * tasks_per_thread
    
    def test_concurrent_read_write_operations(self):
        """Test concurrent read and write operations."""
        # Pre-populate with some tasks
        initial_tasks = []
        for i in range(10):
            task = self.create_sample_task_result()
            self.task_store.store_task(task)
            initial_tasks.append(task)
        
        read_results = []
        write_results = []
        errors = []
        
        def reader_thread():
            try:
                for _ in range(20):
                    # Read random tasks
                    all_tasks = self.task_store.get_all_tasks()
                    read_results.append(len(all_tasks))
                    time.sleep(0.01)  # Small delay
            except Exception as e:
                errors.append(f"Reader error: {e}")
        
        def writer_thread():
            try:
                for i in range(10):
                    # Add new tasks
                    task = self.create_sample_task_result()
                    result = self.task_store.store_task(task)
                    write_results.append(result)
                    time.sleep(0.01)  # Small delay
            except Exception as e:
                errors.append(f"Writer error: {e}")
        
        # Create threads
        readers = [threading.Thread(target=reader_thread) for _ in range(3)]
        writers = [threading.Thread(target=writer_thread) for _ in range(2)]
        
        all_threads = readers + writers
        
        # Start all threads
        for thread in all_threads:
            thread.start()
        
        # Wait for completion
        for thread in all_threads:
            thread.join()
        
        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        
        # Verify read operations completed
        assert len(read_results) == 3 * 20  # 3 reader threads, 20 reads each
        
        # Verify write operations completed
        assert len(write_results) == 2 * 10  # 2 writer threads, 10 writes each
        assert all(result is True for result in write_results)
        
        # Verify final task count
        final_count = self.task_store.get_task_count()
        assert final_count == 10 + (2 * 10)  # Initial + new tasks
    
    def create_sample_task_result(self, task_id: str = None, status: TaskStatus = TaskStatus.PENDING) -> TaskResult:
        """Create a sample TaskResult for testing."""
        if not task_id:
            task_id = self.task_id_generator.generate_task_id()
        
        return TaskResult(
            task_id=task_id,
            status=status,
            message="Test task",
            results={"test": "data"}
        )


class TestTaskStoreCleanup:
    """Test automatic cleanup functionality."""
    
    def setup_method(self):
        self.task_store = TaskStore(cleanup_enabled=True, max_task_age_hours=1)
        self.task_id_generator = TaskIDGenerator()
    
    def test_automatic_cleanup_configuration(self):
        """Test cleanup configuration options."""
        # Test default settings
        default_store = TaskStore()
        assert default_store.cleanup_enabled is True
        assert default_store.max_task_age_hours == 24
        
        # Test custom settings
        custom_store = TaskStore(cleanup_enabled=False, max_task_age_hours=48)
        assert custom_store.cleanup_enabled is False
        assert custom_store.max_task_age_hours == 48
    
    def test_cleanup_old_tasks(self):
        """Test manual cleanup of old tasks."""
        # Create tasks with different ages
        old_tasks = []
        new_tasks = []
        
        # Create old tasks (modify creation time)
        for i in range(3):
            task = self.create_sample_task_result()
            # Manually set old creation time
            task.created_at = datetime.now(timezone.utc) - timedelta(hours=25)
            self.task_store.store_task(task)
            old_tasks.append(task)
        
        # Create new tasks
        for i in range(2):
            task = self.create_sample_task_result()
            self.task_store.store_task(task)
            new_tasks.append(task)
        
        # Verify all tasks are stored
        assert self.task_store.get_task_count() == 5
        
        # Run cleanup with 24-hour limit
        cleaned_count = self.task_store.cleanup_old_tasks(max_age_hours=24)
        assert cleaned_count == 3  # Should clean up 3 old tasks
        
        # Verify only new tasks remain
        remaining_tasks = self.task_store.get_all_tasks()
        assert len(remaining_tasks) == 2
        remaining_ids = {task.task_id for task in remaining_tasks}
        expected_ids = {task.task_id for task in new_tasks}
        assert remaining_ids == expected_ids
    
    def test_cleanup_respects_status_filter(self):
        """Test cleanup can be filtered by task status."""
        # Create completed and failed old tasks
        completed_task = self.create_sample_task_result(status=TaskStatus.COMPLETED)
        completed_task.created_at = datetime.now(timezone.utc) - timedelta(hours=25)
        
        failed_task = self.create_sample_task_result(status=TaskStatus.FAILED)
        failed_task.created_at = datetime.now(timezone.utc) - timedelta(hours=25)
        
        pending_task = self.create_sample_task_result(status=TaskStatus.PENDING)
        pending_task.created_at = datetime.now(timezone.utc) - timedelta(hours=25)
        
        self.task_store.store_task(completed_task)
        self.task_store.store_task(failed_task)
        self.task_store.store_task(pending_task)
        
        # Cleanup only completed and failed tasks
        cleaned_count = self.task_store.cleanup_old_tasks(
            max_age_hours=24,
            status_filter=[TaskStatus.COMPLETED, TaskStatus.FAILED]
        )
        assert cleaned_count == 2
        
        # Verify pending task remains
        remaining_tasks = self.task_store.get_all_tasks()
        assert len(remaining_tasks) == 1
        assert remaining_tasks[0].status == TaskStatus.PENDING
    
    @patch('medusa.utils.task_store.threading.Timer')
    def test_automatic_cleanup_scheduling(self, mock_timer):
        """Test automatic cleanup scheduling."""
        # Create store with auto cleanup
        store = TaskStore(cleanup_enabled=True, cleanup_interval_minutes=30)
        
        # Verify timer was created
        mock_timer.assert_called_once()
        call_args = mock_timer.call_args
        assert call_args[0][0] == 30 * 60  # 30 minutes in seconds
        
        # Verify timer was started
        mock_timer.return_value.start.assert_called_once()
    
    def create_sample_task_result(self, task_id: str = None, status: TaskStatus = TaskStatus.PENDING) -> TaskResult:
        """Create a sample TaskResult for testing."""
        if not task_id:
            task_id = self.task_id_generator.generate_task_id()
        
        return TaskResult(
            task_id=task_id,
            status=status,
            message="Test task",
            results={"test": "data"}
        )


class TestTaskStoreEdgeCases:
    """Test edge cases and error conditions."""
    
    def setup_method(self):
        self.task_store = TaskStore()
        self.task_id_generator = TaskIDGenerator()
    
    def test_store_invalid_task_data(self):
        """Test storing invalid task data."""
        # Test None task
        with pytest.raises(TaskStoreError, match="Task cannot be None"):
            self.task_store.store_task(None)
        
        # Test task with empty ID
        invalid_task = TaskResult(task_id="", status=TaskStatus.PENDING)
        with pytest.raises(TaskStoreError, match="Task ID cannot be empty"):
            self.task_store.store_task(invalid_task)
    
    def test_get_task_invalid_id(self):
        """Test getting task with invalid ID."""
        # Test None ID
        result = self.task_store.get_task(None)
        assert result is None
        
        # Test empty ID
        result = self.task_store.get_task("")
        assert result is None
    
    def test_operations_on_empty_store(self):
        """Test operations on empty task store."""
        # Test get all tasks
        all_tasks = self.task_store.get_all_tasks()
        assert all_tasks == []
        
        # Test get by status
        pending_tasks = self.task_store.get_tasks_by_status(TaskStatus.PENDING)
        assert pending_tasks == []
        
        # Test count
        count = self.task_store.get_task_count()
        assert count == 0
        
        # Test cleanup
        cleaned = self.task_store.cleanup_old_tasks()
        assert cleaned == 0
    
    def test_memory_usage_with_large_dataset(self):
        """Test memory behavior with large number of tasks."""
        # Create many tasks
        num_tasks = 1000
        for i in range(num_tasks):
            task = self.create_sample_task_result()
            task.results = {"large_data": "x" * 100}  # Add some data
            self.task_store.store_task(task)
        
        # Verify all tasks stored
        assert self.task_store.get_task_count() == num_tasks
        
        # Test bulk operations still work
        all_tasks = self.task_store.get_all_tasks()
        assert len(all_tasks) == num_tasks
        
        # Test cleanup works on large dataset
        cleaned = self.task_store.cleanup_old_tasks(max_age_hours=0)  # Clean all
        assert cleaned == num_tasks
        assert self.task_store.get_task_count() == 0
    
    def create_sample_task_result(self, task_id: str = None, status: TaskStatus = TaskStatus.PENDING) -> TaskResult:
        """Create a sample TaskResult for testing."""
        if not task_id:
            task_id = self.task_id_generator.generate_task_id()
        
        return TaskResult(
            task_id=task_id,
            status=status,
            message="Test task",
            results={"test": "data"}
        ) 