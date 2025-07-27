"""
Task state management system for Medusa library.

This module provides comprehensive state management functionality including:
- State transitions with validation
- State history tracking with timestamps
- Event system for state change notifications
- Centralized task state management
- Support for state rollback scenarios
"""

import logging
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from collections import defaultdict

from ..exceptions import MedusaError

# Set up logging
logger = logging.getLogger(__name__)


class StateTransitionError(MedusaError):
    """Exception raised for invalid state transitions."""

    pass


class InvalidStateError(MedusaError):
    """Exception raised for invalid state operations."""

    pass


class TaskState(Enum):
    """Enumeration of possible task states with proper state transitions."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @classmethod
    def get_valid_transitions(cls) -> Dict["TaskState", set]:
        """
        Get valid state transitions mapping.

        Returns:
            Dictionary mapping each state to its valid next states
        """
        return {
            cls.PENDING: {
                cls.IN_PROGRESS,
                cls.COMPLETED,
                cls.CANCELLED,
            },  # Allow direct completion
            cls.IN_PROGRESS: {cls.COMPLETED, cls.FAILED, cls.CANCELLED},
            cls.COMPLETED: {cls.COMPLETED},  # Can stay completed
            cls.FAILED: {cls.FAILED},  # Can stay failed
            cls.CANCELLED: {cls.CANCELLED},  # Can stay cancelled
        }

    def can_transition_to(self, target_state: "TaskState") -> bool:
        """
        Check if transition to target state is valid.

        Args:
            target_state: Target state to transition to

        Returns:
            True if transition is valid, False otherwise
        """
        valid_transitions = self.get_valid_transitions()
        return target_state in valid_transitions.get(self, set())


@dataclass
class StateTransition:
    """Represents a task state transition with validation and metadata."""

    from_state: Optional[TaskState]
    to_state: TaskState
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    message: Optional[str] = None
    is_rollback: bool = False

    def validate(self) -> None:
        """
        Validate the state transition.

        Raises:
            StateTransitionError: If the transition is invalid
        """
        if self.from_state is None:
            # Initial state setting is always valid
            return

        # Rollback transitions skip normal validation rules
        if self.is_rollback:
            return

        if not self.from_state.can_transition_to(self.to_state):
            raise StateTransitionError(
                f"Invalid state transition from {self.from_state.value} to {self.to_state.value}"
            )

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize StateTransition to dictionary.

        Returns:
            Dictionary representation of the transition
        """
        return {
            "from_state": self.from_state.value if self.from_state else None,
            "to_state": self.to_state.value,
            "timestamp": self.timestamp.isoformat(),
            "message": self.message,
            "is_rollback": self.is_rollback,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StateTransition":
        """
        Deserialize StateTransition from dictionary.

        Args:
            data: Dictionary containing transition data

        Returns:
            StateTransition instance
        """
        from_state = TaskState(data["from_state"]) if data["from_state"] else None
        to_state = TaskState(data["to_state"])
        timestamp = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))

        return cls(
            from_state=from_state,
            to_state=to_state,
            timestamp=timestamp,
            message=data.get("message"),
            is_rollback=data.get("is_rollback", False),
        )


@dataclass
class StateHistory:
    """Manages the complete history of state transitions for a task."""

    task_id: str
    transitions: List[StateTransition] = field(default_factory=list)

    @property
    def current_state(self) -> Optional[TaskState]:
        """
        Get the current state of the task.

        Returns:
            Current TaskState or None if no transitions exist
        """
        if not self.transitions:
            return None
        return self.transitions[-1].to_state

    def add_transition(self, transition: StateTransition) -> None:
        """
        Add a state transition to the history.

        Args:
            transition: StateTransition to add

        Raises:
            StateTransitionError: If transition is invalid based on current state
        """
        # Validate transition sequence
        if self.transitions:
            current_state = self.current_state
            if transition.from_state != current_state:
                raise StateTransitionError(
                    f"Transition from_state {transition.from_state} doesn't match current state {current_state}"
                )

        # Validate the transition itself
        transition.validate()

        # Add to history
        self.transitions.append(transition)

        logger.debug(
            f"Task {self.task_id}: State transition {transition.from_state} -> {transition.to_state}"
        )

    def get_state_durations(self) -> Dict[TaskState, timedelta]:
        """
        Calculate how long the task spent in each state.

        Returns:
            Dictionary mapping states to their durations
        """
        durations = defaultdict(timedelta)

        if not self.transitions:
            return dict(durations)

        current_time = datetime.now(timezone.utc)

        for i, transition in enumerate(self.transitions):
            state = transition.to_state
            start_time = transition.timestamp

            # Calculate end time (next transition or current time)
            if i + 1 < len(self.transitions):
                end_time = self.transitions[i + 1].timestamp
            else:
                end_time = current_time

            duration = end_time - start_time
            durations[state] += duration

        return dict(durations)

    def rollback_to_state(
        self, target_state: TaskState, message: Optional[str] = None
    ) -> StateTransition:
        """
        Rollback to a previous state in the history.

        Args:
            target_state: State to rollback to
            message: Optional message for the rollback transition

        Returns:
            The rollback transition

        Raises:
            InvalidStateError: If target state is not in history
        """
        # Check if target state exists in history
        target_exists = any(t.to_state == target_state for t in self.transitions)
        if not target_exists:
            raise InvalidStateError(
                f"Cannot rollback to state {target_state.value} - not in history"
            )

        # Create rollback transition
        rollback_transition = StateTransition(
            from_state=self.current_state,
            to_state=target_state,
            message=message or f"Rollback to {target_state.value}",
            is_rollback=True,
        )

        self.add_transition(rollback_transition)
        return rollback_transition


class StateEventSystem:
    """Event system for notifying listeners about state changes."""

    def __init__(self):
        """Initialize the event system."""
        self._listeners: Dict[TaskState, List[Callable]] = defaultdict(list)

    def register_listener(
        self, state: TaskState, callback: Callable[[str, StateTransition], None]
    ) -> None:
        """
        Register a listener for state changes.

        Args:
            state: TaskState to listen for
            callback: Function to call when state is reached
        """
        self._listeners[state].append(callback)
        logger.debug(f"Registered listener for state {state.value}")

    def unregister_listener(
        self, state: TaskState, callback: Callable[[str, StateTransition], None]
    ) -> None:
        """
        Unregister a listener for state changes.

        Args:
            state: TaskState to stop listening for
            callback: Function to remove from listeners
        """
        if callback in self._listeners[state]:
            self._listeners[state].remove(callback)
            logger.debug(f"Unregistered listener for state {state.value}")

    def emit_state_change(self, task_id: str, transition: StateTransition) -> None:
        """
        Emit a state change event to all registered listeners.

        Args:
            task_id: ID of the task that changed state
            transition: StateTransition that occurred
        """
        state = transition.to_state
        listeners = self._listeners.get(state, [])

        for listener in listeners:
            try:
                listener(task_id, transition)
            except Exception as e:
                logger.error(f"Error in state change listener for {state.value}: {e}")
                # Don't re-raise to prevent one failing listener from affecting others


class TaskStateManager:
    """Centralized manager for task state operations and history tracking."""

    def __init__(self):
        """Initialize the task state manager."""
        self._task_histories: Dict[str, StateHistory] = {}
        self._event_system = StateEventSystem()

    def initialize_task(self, task_id: str, initial_state: TaskState) -> None:
        """
        Initialize a new task with its initial state.

        Args:
            task_id: Unique identifier for the task
            initial_state: Initial state to set

        Raises:
            InvalidStateError: If task already exists
        """
        if task_id in self._task_histories:
            raise InvalidStateError(f"Task {task_id} already exists")

        # Create history and initial transition
        history = StateHistory(task_id)
        initial_transition = StateTransition(from_state=None, to_state=initial_state)

        history.add_transition(initial_transition)
        self._task_histories[task_id] = history

        # Emit state change event
        self._event_system.emit_state_change(task_id, initial_transition)

        logger.info(f"Initialized task {task_id} with state {initial_state.value}")

    def transition_state(
        self, task_id: str, new_state: TaskState, message: Optional[str] = None
    ) -> StateTransition:
        """
        Transition a task to a new state.

        Args:
            task_id: Task identifier
            new_state: Target state
            message: Optional transition message

        Returns:
            The created StateTransition

        Raises:
            InvalidStateError: If task doesn't exist
            StateTransitionError: If transition is invalid
        """
        if task_id not in self._task_histories:
            raise InvalidStateError(f"Task {task_id} not found")

        history = self._task_histories[task_id]
        current_state = history.current_state

        # Create and validate transition
        transition = StateTransition(
            from_state=current_state, to_state=new_state, message=message
        )

        # Add to history (validates transition)
        history.add_transition(transition)

        # Emit state change event
        self._event_system.emit_state_change(task_id, transition)

        logger.info(
            f"Task {task_id}: {current_state.value if current_state else 'None'} -> {new_state.value}"
        )
        return transition

    def get_current_state(self, task_id: str) -> TaskState:
        """
        Get the current state of a task.

        Args:
            task_id: Task identifier

        Returns:
            Current TaskState

        Raises:
            InvalidStateError: If task doesn't exist
        """
        if task_id not in self._task_histories:
            raise InvalidStateError(f"Task {task_id} not found")

        current_state = self._task_histories[task_id].current_state
        if current_state is None:
            raise InvalidStateError(f"Task {task_id} has no state history")

        return current_state

    def get_task_history(self, task_id: str) -> StateHistory:
        """
        Get the complete state history for a task.

        Args:
            task_id: Task identifier

        Returns:
            StateHistory for the task

        Raises:
            InvalidStateError: If task doesn't exist
        """
        if task_id not in self._task_histories:
            raise InvalidStateError(f"Task {task_id} not found")

        return self._task_histories[task_id]

    def rollback_task(
        self, task_id: str, target_state: TaskState, message: Optional[str] = None
    ) -> StateTransition:
        """
        Rollback a task to a previous state.

        Args:
            task_id: Task identifier
            target_state: State to rollback to
            message: Optional rollback message

        Returns:
            The rollback StateTransition

        Raises:
            InvalidStateError: If task doesn't exist or invalid rollback
        """
        if task_id not in self._task_histories:
            raise InvalidStateError(f"Task {task_id} not found")

        history = self._task_histories[task_id]
        rollback_transition = history.rollback_to_state(target_state, message)

        # Emit state change event
        self._event_system.emit_state_change(task_id, rollback_transition)

        logger.info(f"Task {task_id}: Rolled back to {target_state.value}")
        return rollback_transition

    def register_state_listener(
        self, state: TaskState, callback: Callable[[str, StateTransition], None]
    ) -> None:
        """
        Register a listener for state changes.

        Args:
            state: TaskState to listen for
            callback: Function to call when state is reached
        """
        self._event_system.register_listener(state, callback)

    def unregister_state_listener(
        self, state: TaskState, callback: Callable[[str, StateTransition], None]
    ) -> None:
        """
        Unregister a listener for state changes.

        Args:
            state: TaskState to stop listening for
            callback: Function to remove from listeners
        """
        self._event_system.unregister_listener(state, callback)

    def cleanup_old_tasks(self, max_age_hours: int = 24) -> int:
        """
        Clean up old task histories to prevent memory leaks.

        Args:
            max_age_hours: Maximum age in hours for keeping task histories

        Returns:
            Number of tasks cleaned up
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        tasks_to_remove = []

        for task_id, history in self._task_histories.items():
            if history.transitions:
                last_transition_time = history.transitions[-1].timestamp
                if last_transition_time < cutoff_time:
                    tasks_to_remove.append(task_id)

        for task_id in tasks_to_remove:
            del self._task_histories[task_id]
            logger.debug(f"Cleaned up old task history: {task_id}")

        return len(tasks_to_remove)

    def get_state_statistics(self) -> Dict[TaskState, int]:
        """
        Get statistics about current task states.

        Returns:
            Dictionary mapping states to their counts
        """
        stats = {state: 0 for state in TaskState}

        for history in self._task_histories.values():
            if history.current_state:
                stats[history.current_state] += 1

        return stats
