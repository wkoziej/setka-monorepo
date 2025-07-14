"""
Test module for task state management system.

This module tests all aspects of task state management including:
- State transitions and validation
- State history tracking
- Event system for state changes
- Error handling for invalid transitions
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from typing import List, Callable

from medusa.utils.states import (
    TaskState, 
    StateTransition, 
    StateHistory, 
    StateEventSystem, 
    TaskStateManager,
    StateTransitionError,
    InvalidStateError
)


class TestTaskState:
    """Test TaskState enum and basic functionality."""
    
    def test_task_state_values(self):
        """Test that all expected state values exist."""
        assert TaskState.PENDING.value == "pending"
        assert TaskState.IN_PROGRESS.value == "in_progress"
        assert TaskState.COMPLETED.value == "completed"
        assert TaskState.FAILED.value == "failed"
        assert TaskState.CANCELLED.value == "cancelled"
    
    def test_task_state_from_string(self):
        """Test creating TaskState from string values."""
        assert TaskState("pending") == TaskState.PENDING
        assert TaskState("in_progress") == TaskState.IN_PROGRESS
        assert TaskState("completed") == TaskState.COMPLETED
        assert TaskState("failed") == TaskState.FAILED
        assert TaskState("cancelled") == TaskState.CANCELLED
    
    def test_invalid_state_string(self):
        """Test that invalid state strings raise ValueError."""
        with pytest.raises(ValueError):
            TaskState("invalid_state")


class TestStateTransition:
    """Test StateTransition class functionality."""
    
    def test_create_state_transition(self):
        """Test creating a valid state transition."""
        transition = StateTransition(
            from_state=TaskState.PENDING,
            to_state=TaskState.IN_PROGRESS,
            message="Starting task execution"
        )
        
        assert transition.from_state == TaskState.PENDING
        assert transition.to_state == TaskState.IN_PROGRESS
        assert transition.message == "Starting task execution"
        assert isinstance(transition.timestamp, datetime)
        assert transition.timestamp.tzinfo is not None
    
    def test_transition_with_custom_timestamp(self):
        """Test creating transition with custom timestamp."""
        custom_time = datetime.now(timezone.utc)
        transition = StateTransition(
            from_state=TaskState.PENDING,
            to_state=TaskState.IN_PROGRESS,
            timestamp=custom_time
        )
        
        assert transition.timestamp == custom_time
    
    def test_transition_validation_valid(self):
        """Test validation of valid state transitions."""
        valid_transitions = [
            (TaskState.PENDING, TaskState.IN_PROGRESS),
            (TaskState.PENDING, TaskState.CANCELLED),
            (TaskState.IN_PROGRESS, TaskState.COMPLETED),
            (TaskState.IN_PROGRESS, TaskState.FAILED),
            (TaskState.IN_PROGRESS, TaskState.CANCELLED),
        ]
        
        for from_state, to_state in valid_transitions:
            transition = StateTransition(from_state, to_state)
            transition.validate()  # Should not raise exception
    
    def test_transition_validation_invalid(self):
        """Test validation of invalid state transitions."""
        invalid_transitions = [
            (TaskState.COMPLETED, TaskState.PENDING),
            (TaskState.COMPLETED, TaskState.IN_PROGRESS),
            (TaskState.FAILED, TaskState.PENDING),
            (TaskState.FAILED, TaskState.IN_PROGRESS),
            (TaskState.CANCELLED, TaskState.PENDING),
            (TaskState.CANCELLED, TaskState.IN_PROGRESS),
        ]
        
        for from_state, to_state in invalid_transitions:
            transition = StateTransition(from_state, to_state)
            with pytest.raises(StateTransitionError):
                transition.validate()
    
    def test_transition_to_dict(self):
        """Test serialization of state transition."""
        transition = StateTransition(
            from_state=TaskState.PENDING,
            to_state=TaskState.IN_PROGRESS,
            message="Test message"
        )
        
        data = transition.to_dict()
        
        assert data["from_state"] == "pending"
        assert data["to_state"] == "in_progress"
        assert data["message"] == "Test message"
        assert "timestamp" in data
    
    def test_transition_from_dict(self):
        """Test deserialization of state transition."""
        data = {
            "from_state": "pending",
            "to_state": "in_progress",
            "message": "Test message",
            "timestamp": "2024-01-01T12:00:00+00:00"
        }
        
        transition = StateTransition.from_dict(data)
        
        assert transition.from_state == TaskState.PENDING
        assert transition.to_state == TaskState.IN_PROGRESS
        assert transition.message == "Test message"


class TestStateHistory:
    """Test StateHistory class functionality."""
    
    def test_create_empty_history(self):
        """Test creating empty state history."""
        history = StateHistory("task_123")
        
        assert history.task_id == "task_123"
        assert len(history.transitions) == 0
        assert history.current_state is None
    
    def test_add_first_transition(self):
        """Test adding the first state transition."""
        history = StateHistory("task_123")
        transition = StateTransition(TaskState.PENDING, TaskState.IN_PROGRESS)
        
        history.add_transition(transition)
        
        assert len(history.transitions) == 1
        assert history.current_state == TaskState.IN_PROGRESS
        assert history.transitions[0] == transition
    
    def test_add_multiple_transitions(self):
        """Test adding multiple state transitions."""
        history = StateHistory("task_123")
        
        t1 = StateTransition(TaskState.PENDING, TaskState.IN_PROGRESS)
        t2 = StateTransition(TaskState.IN_PROGRESS, TaskState.COMPLETED)
        
        history.add_transition(t1)
        history.add_transition(t2)
        
        assert len(history.transitions) == 2
        assert history.current_state == TaskState.COMPLETED
        assert history.transitions[-1] == t2
    
    def test_add_invalid_transition_sequence(self):
        """Test adding invalid transition sequence."""
        history = StateHistory("task_123")
        
        t1 = StateTransition(TaskState.PENDING, TaskState.IN_PROGRESS)
        t2 = StateTransition(TaskState.COMPLETED, TaskState.FAILED)  # Invalid sequence
        
        history.add_transition(t1)
        
        with pytest.raises(StateTransitionError):
            history.add_transition(t2)
    
    def test_get_state_duration(self):
        """Test calculating duration in each state."""
        history = StateHistory("task_123")
        
        # Mock timestamps for predictable testing
        t1 = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2024, 1, 1, 12, 5, 0, tzinfo=timezone.utc)
        t3 = datetime(2024, 1, 1, 12, 10, 0, tzinfo=timezone.utc)
        
        history.add_transition(StateTransition(TaskState.PENDING, TaskState.IN_PROGRESS, timestamp=t1))
        history.add_transition(StateTransition(TaskState.IN_PROGRESS, TaskState.COMPLETED, timestamp=t2))
        
        with patch('medusa.utils.states.datetime') as mock_datetime:
            mock_datetime.now.return_value = t3
            
            durations = history.get_state_durations()
            
            assert durations[TaskState.IN_PROGRESS].total_seconds() == 300  # 5 minutes
            assert durations[TaskState.COMPLETED].total_seconds() == 300  # 5 minutes
    
    def test_rollback_to_previous_state(self):
        """Test rolling back to previous state."""
        history = StateHistory("task_123")
        
        t1 = StateTransition(TaskState.PENDING, TaskState.IN_PROGRESS)
        t2 = StateTransition(TaskState.IN_PROGRESS, TaskState.FAILED)
        
        history.add_transition(t1)
        history.add_transition(t2)
        
        # Rollback to in_progress
        rollback_transition = history.rollback_to_state(TaskState.IN_PROGRESS, "Rolling back from failure")
        
        assert history.current_state == TaskState.IN_PROGRESS
        assert len(history.transitions) == 3
        assert rollback_transition.message == "Rolling back from failure"
    
    def test_rollback_to_invalid_state(self):
        """Test rollback to state not in history."""
        history = StateHistory("task_123")
        
        t1 = StateTransition(TaskState.PENDING, TaskState.IN_PROGRESS)
        history.add_transition(t1)
        
        with pytest.raises(InvalidStateError):
            history.rollback_to_state(TaskState.COMPLETED, "Invalid rollback")


class TestStateEventSystem:
    """Test StateEventSystem class functionality."""
    
    def test_create_event_system(self):
        """Test creating state event system."""
        event_system = StateEventSystem()
        
        assert len(event_system._listeners) == 0
    
    def test_register_listener(self):
        """Test registering state change listeners."""
        event_system = StateEventSystem()
        callback = Mock()
        
        event_system.register_listener(TaskState.COMPLETED, callback)
        
        assert TaskState.COMPLETED in event_system._listeners
        assert callback in event_system._listeners[TaskState.COMPLETED]
    
    def test_register_multiple_listeners(self):
        """Test registering multiple listeners for same state."""
        event_system = StateEventSystem()
        callback1 = Mock()
        callback2 = Mock()
        
        event_system.register_listener(TaskState.COMPLETED, callback1)
        event_system.register_listener(TaskState.COMPLETED, callback2)
        
        assert len(event_system._listeners[TaskState.COMPLETED]) == 2
    
    def test_emit_event(self):
        """Test emitting state change events."""
        event_system = StateEventSystem()
        callback = Mock()
        
        event_system.register_listener(TaskState.COMPLETED, callback)
        
        transition = StateTransition(TaskState.IN_PROGRESS, TaskState.COMPLETED)
        event_system.emit_state_change("task_123", transition)
        
        callback.assert_called_once_with("task_123", transition)
    
    def test_emit_event_no_listeners(self):
        """Test emitting event with no registered listeners."""
        event_system = StateEventSystem()
        
        transition = StateTransition(TaskState.IN_PROGRESS, TaskState.COMPLETED)
        # Should not raise exception
        event_system.emit_state_change("task_123", transition)
    
    def test_unregister_listener(self):
        """Test unregistering state change listeners."""
        event_system = StateEventSystem()
        callback = Mock()
        
        event_system.register_listener(TaskState.COMPLETED, callback)
        event_system.unregister_listener(TaskState.COMPLETED, callback)
        
        assert len(event_system._listeners.get(TaskState.COMPLETED, [])) == 0
    
    def test_emit_event_with_exception(self):
        """Test event emission when listener raises exception."""
        event_system = StateEventSystem()
        
        def failing_callback(task_id, transition):
            raise Exception("Listener failed")
        
        event_system.register_listener(TaskState.FAILED, failing_callback)
        
        transition = StateTransition(TaskState.IN_PROGRESS, TaskState.FAILED)
        # Should not raise exception but log the error
        event_system.emit_state_change("task_123", transition)


class TestTaskStateManager:
    """Test TaskStateManager class functionality."""
    
    def test_create_state_manager(self):
        """Test creating task state manager."""
        manager = TaskStateManager()
        
        assert len(manager._task_histories) == 0
        assert isinstance(manager._event_system, StateEventSystem)
    
    def test_initialize_task(self):
        """Test initializing new task state."""
        manager = TaskStateManager()
        
        manager.initialize_task("task_123", TaskState.PENDING)
        
        assert "task_123" in manager._task_histories
        assert manager.get_current_state("task_123") == TaskState.PENDING
    
    def test_initialize_existing_task(self):
        """Test initializing task that already exists."""
        manager = TaskStateManager()
        
        manager.initialize_task("task_123", TaskState.PENDING)
        
        with pytest.raises(InvalidStateError):
            manager.initialize_task("task_123", TaskState.PENDING)
    
    def test_transition_state(self):
        """Test transitioning task state."""
        manager = TaskStateManager()
        callback = Mock()
        
        manager.initialize_task("task_123", TaskState.PENDING)
        manager.register_state_listener(TaskState.IN_PROGRESS, callback)
        
        transition = manager.transition_state("task_123", TaskState.IN_PROGRESS, "Starting execution")
        
        assert manager.get_current_state("task_123") == TaskState.IN_PROGRESS
        assert transition.message == "Starting execution"
        callback.assert_called_once()
    
    def test_transition_invalid_state(self):
        """Test transitioning to invalid state."""
        manager = TaskStateManager()
        
        manager.initialize_task("task_123", TaskState.COMPLETED)
        
        with pytest.raises(StateTransitionError):
            manager.transition_state("task_123", TaskState.PENDING, "Invalid transition")
    
    def test_transition_nonexistent_task(self):
        """Test transitioning state of nonexistent task."""
        manager = TaskStateManager()
        
        with pytest.raises(InvalidStateError):
            manager.transition_state("nonexistent", TaskState.IN_PROGRESS)
    
    def test_get_task_history(self):
        """Test getting complete task history."""
        manager = TaskStateManager()
        
        manager.initialize_task("task_123", TaskState.PENDING)
        manager.transition_state("task_123", TaskState.IN_PROGRESS)
        manager.transition_state("task_123", TaskState.COMPLETED)
        
        history = manager.get_task_history("task_123")
        
        assert len(history.transitions) == 3
        assert history.current_state == TaskState.COMPLETED
    
    def test_rollback_task_state(self):
        """Test rolling back task to previous state."""
        manager = TaskStateManager()
        
        manager.initialize_task("task_123", TaskState.PENDING)
        manager.transition_state("task_123", TaskState.IN_PROGRESS)
        manager.transition_state("task_123", TaskState.FAILED)
        
        rollback_transition = manager.rollback_task("task_123", TaskState.IN_PROGRESS, "Retrying after failure")
        
        assert manager.get_current_state("task_123") == TaskState.IN_PROGRESS
        assert rollback_transition.message == "Retrying after failure"
    
    def test_cleanup_old_tasks(self):
        """Test cleaning up old task histories."""
        manager = TaskStateManager()
        
        # Create tasks with old timestamps
        with patch('medusa.utils.states.datetime') as mock_datetime:
            old_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
            mock_datetime.now.return_value = old_time
            
            manager.initialize_task("old_task", TaskState.PENDING)
            manager.transition_state("old_task", TaskState.COMPLETED)
        
        # Create recent task
        manager.initialize_task("new_task", TaskState.PENDING)
        
        # Cleanup tasks older than 1 hour
        cleanup_count = manager.cleanup_old_tasks(max_age_hours=1)
        
        assert cleanup_count == 1
        assert "old_task" not in manager._task_histories
        assert "new_task" in manager._task_histories
    
    def test_get_state_statistics(self):
        """Test getting statistics about task states."""
        manager = TaskStateManager()
        
        # Create multiple tasks in various states
        manager.initialize_task("task_1", TaskState.PENDING)
        manager.initialize_task("task_2", TaskState.PENDING)
        manager.transition_state("task_2", TaskState.IN_PROGRESS)
        manager.initialize_task("task_3", TaskState.PENDING)
        manager.transition_state("task_3", TaskState.IN_PROGRESS)
        manager.transition_state("task_3", TaskState.COMPLETED)
        
        stats = manager.get_state_statistics()
        
        assert stats[TaskState.PENDING] == 1
        assert stats[TaskState.IN_PROGRESS] == 1
        assert stats[TaskState.COMPLETED] == 1
        assert stats[TaskState.FAILED] == 0
        assert stats[TaskState.CANCELLED] == 0


class TestTaskStateManagerIntegration:
    """Integration tests for complete state management workflow."""
    
    def test_complete_task_lifecycle(self):
        """Test complete task lifecycle from creation to completion."""
        manager = TaskStateManager()
        events = []
        
        def event_logger(task_id, transition):
            events.append((task_id, transition.from_state, transition.to_state, transition.message))
        
        # Register listeners for all states
        for state in TaskState:
            manager.register_state_listener(state, event_logger)
        
        # Complete lifecycle
        manager.initialize_task("task_123", TaskState.PENDING)
        manager.transition_state("task_123", TaskState.IN_PROGRESS, "Starting upload")
        manager.transition_state("task_123", TaskState.COMPLETED, "Upload successful")
        
        # Verify events were fired
        assert len(events) == 3
        assert events[0] == ("task_123", None, TaskState.PENDING, None)
        assert events[1] == ("task_123", TaskState.PENDING, TaskState.IN_PROGRESS, "Starting upload")
        assert events[2] == ("task_123", TaskState.IN_PROGRESS, TaskState.COMPLETED, "Upload successful")
        
        # Verify final state
        assert manager.get_current_state("task_123") == TaskState.COMPLETED
        
        # Verify history
        history = manager.get_task_history("task_123")
        assert len(history.transitions) == 3
        assert all(isinstance(t, StateTransition) for t in history.transitions)
    
    def test_task_failure_and_rollback(self):
        """Test task failure scenario with rollback capability."""
        manager = TaskStateManager()
        
        # Start task
        manager.initialize_task("failing_task", TaskState.PENDING)
        manager.transition_state("failing_task", TaskState.IN_PROGRESS, "Processing")
        manager.transition_state("failing_task", TaskState.FAILED, "Network error")
        
        # Verify failure state
        assert manager.get_current_state("failing_task") == TaskState.FAILED
        
        # Rollback and retry
        manager.rollback_task("failing_task", TaskState.IN_PROGRESS, "Retrying after network recovery")
        manager.transition_state("failing_task", TaskState.COMPLETED, "Retry successful")
        
        # Verify final state
        assert manager.get_current_state("failing_task") == TaskState.COMPLETED
        
        # Verify complete history includes rollback
        history = manager.get_task_history("failing_task")
        assert len(history.transitions) == 5  # init, progress, failed, rollback, completed 