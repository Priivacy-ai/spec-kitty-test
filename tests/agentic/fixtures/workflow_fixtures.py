"""Workflow validation and test scaffolding fixtures for agentic E2E testing.

This module provides:
- WorkflowValidator: Validates WP lane transitions
- RejectionCycleHandler: Handles rejection cycles with iteration limits
- WorkflowEngine: Orchestrates workflow execution with limits
- LaneMonitor: Polls WP status via spec-kitty CLI
- TestFeatureScaffold: Creates isolated test features

Per CLAUDE.md: These are distribution tests - spec-kitty is installed from PyPI,
NOT from local source. No SPEC_KITTY_TEMPLATE_ROOT is ever set.
"""

import json
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import pytest


class TestStatus(Enum):
    """Status of a test run.

    Values:
        PENDING: Test not yet started
        RUNNING: Test currently executing
        PASSED: Test completed successfully
        FAILED: Test completed with assertion failure
        ERROR: Test completed with unexpected error
        SKIPPED: Test was skipped
    """

    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


class EventType(Enum):
    """Types of workflow events.

    Events are recorded as WorkflowObservations during test execution.
    """

    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"
    AGENT_TIMEOUT = "agent_timeout"
    STATE_CHANGED = "state_changed"
    FAULT_INJECTED = "fault_injected"
    CONTAINER_CREATED = "container_created"
    CONTAINER_DESTROYED = "container_destroyed"
    WP_LANE_CHANGED = "wp_lane_changed"


class WPLane(Enum):
    """Valid WP lane values.

    Represents the kanban-style workflow lanes:
    - PLANNED: Work not yet started
    - DOING: Work in progress
    - FOR_REVIEW: Awaiting review
    - DONE: Work completed
    """

    PLANNED = "planned"
    DOING = "doing"
    FOR_REVIEW = "for_review"
    DONE = "done"


@dataclass
class WorkflowObservation:
    """Captured data from a workflow step.

    Observations are immutable records of workflow events.

    Attributes:
        step: Name of the workflow step
        agent_id: ID of the agent involved (if any)
        event_type: Type of event that occurred
        data: Additional event data
        success: Whether the step succeeded
        timestamp: When the event occurred
        observation_id: Unique ID for this observation
    """

    step: str
    agent_id: Optional[str]
    event_type: EventType
    data: Dict[str, Any]
    success: bool = True
    timestamp: datetime = field(default_factory=datetime.utcnow)
    observation_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "observation_id": self.observation_id,
            "timestamp": self.timestamp.isoformat() + "Z",
            "step": self.step,
            "agent_id": self.agent_id,
            "event_type": self.event_type.value,
            "data": self.data,
            "success": self.success,
        }


@dataclass
class WorkflowState:
    """Current state of the workflow.

    Tracks the current position within the workflow.

    Attributes:
        current_step: Name of the current step
        wp_lane: Current WP lane
        iteration: Current iteration (for rejection cycles)
    """

    current_step: str
    wp_lane: WPLane
    iteration: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "current_step": self.current_step,
            "wp_lane": self.wp_lane.value,
            "iteration": self.iteration,
        }


@dataclass
class TestRun:
    """A complete test execution record.

    Aggregates all data from a single test run.

    Attributes:
        path_id: ID of the test path being executed
        agent_assignments: Mapping of roles to agent IDs
        status: Current test status
        workflow_state: Current workflow state
        observations: List of all workflow observations
        failure_reason: Reason for failure (if any)
        started_at: When the test started
        completed_at: When the test completed
        run_id: Unique ID for this test run
    """

    path_id: str
    agent_assignments: Dict[str, str]
    status: TestStatus = TestStatus.PENDING
    workflow_state: Optional[WorkflowState] = None
    observations: List[WorkflowObservation] = field(default_factory=list)
    failure_reason: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def start(self):
        """Mark run as started."""
        self.status = TestStatus.RUNNING
        self.started_at = datetime.utcnow()

    def complete(self, success: bool = True, failure_reason: Optional[str] = None):
        """Mark run as complete.

        Args:
            success: Whether the test passed
            failure_reason: Reason for failure (if any)
        """
        self.completed_at = datetime.utcnow()
        self.status = TestStatus.PASSED if success else TestStatus.FAILED
        self.failure_reason = failure_reason

    def add_observation(self, observation: WorkflowObservation):
        """Add an observation to the run."""
        self.observations.append(observation)

    def to_json(self) -> Dict[str, Any]:
        """Export to JSON-serializable dict per data-model.md schema."""
        return {
            "run_id": self.run_id,
            "path_id": self.path_id,
            "agent_assignments": self.agent_assignments,
            "started_at": self.started_at.isoformat() + "Z",
            "completed_at": (
                self.completed_at.isoformat() + "Z" if self.completed_at else None
            ),
            "status": self.status.value,
            "workflow_state": self.workflow_state.to_dict() if self.workflow_state else None,
            "observations": [obs.to_dict() for obs in self.observations],
            "failure_reason": self.failure_reason,
        }


class IterationLimitError(Exception):
    """Raised when max iterations exceeded.

    Attributes:
        iterations: Number of iterations that occurred
        max_iterations: Maximum allowed iterations
        rejection_history: List of rejection records
    """

    def __init__(
        self,
        iterations: int,
        max_iterations: int,
        rejection_history: List[Dict[str, Any]],
    ):
        self.iterations = iterations
        self.max_iterations = max_iterations
        self.rejection_history = rejection_history
        msg = (
            f"Max iterations ({max_iterations}) exceeded after {iterations} rejections. "
            f"Rejection history: {rejection_history}"
        )
        super().__init__(msg)


class WorkflowValidator:
    """Validates workflow state transitions.

    Enforces the valid WP lane transitions:
    - planned -> doing
    - doing -> for_review
    - for_review -> done OR for_review -> planned (rejection)
    - done is terminal

    Attributes:
        max_iterations: Maximum allowed rejection cycles
    """

    # Valid lane transitions
    VALID_TRANSITIONS: Dict[WPLane, List[WPLane]] = {
        WPLane.PLANNED: [WPLane.DOING],
        WPLane.DOING: [WPLane.FOR_REVIEW],
        WPLane.FOR_REVIEW: [WPLane.DONE, WPLane.PLANNED],  # Can go back on rejection
        WPLane.DONE: [],  # Terminal state
    }

    def __init__(self, max_iterations: int = 5):
        """Initialize the validator.

        Args:
            max_iterations: Maximum allowed rejection cycles
        """
        self.max_iterations = max_iterations
        self._transitions: List[tuple] = []

    def validate_transition(self, from_lane: WPLane, to_lane: WPLane) -> bool:
        """Check if lane transition is valid.

        Args:
            from_lane: Current lane
            to_lane: Target lane

        Returns:
            True if transition is valid, False otherwise
        """
        valid = to_lane in self.VALID_TRANSITIONS.get(from_lane, [])
        self._transitions.append((from_lane, to_lane, valid, datetime.utcnow()))
        return valid

    def record_lane_change(
        self,
        from_lane: WPLane,
        to_lane: WPLane,
        timestamp: Optional[datetime] = None,
    ) -> WorkflowObservation:
        """Record a lane change observation.

        Args:
            from_lane: Lane being left
            to_lane: Lane being entered
            timestamp: When the change occurred

        Returns:
            WorkflowObservation recording the change
        """
        is_valid = self.validate_transition(from_lane, to_lane)

        return WorkflowObservation(
            step="lane_change",
            agent_id=None,
            event_type=EventType.WP_LANE_CHANGED,
            data={
                "from_lane": from_lane.value,
                "to_lane": to_lane.value,
                "valid": is_valid,
            },
            success=is_valid,
            timestamp=timestamp or datetime.utcnow(),
        )

    def get_transition_history(self) -> List[tuple]:
        """Return all recorded transitions.

        Returns:
            List of (from_lane, to_lane, valid, timestamp) tuples
        """
        return self._transitions.copy()

    def get_invalid_transitions(self) -> List[tuple]:
        """Return only invalid transitions.

        Returns:
            List of (from_lane, to_lane, valid, timestamp) tuples where valid=False
        """
        return [(f, t, v, ts) for f, t, v, ts in self._transitions if not v]

    def reset(self):
        """Clear transition history."""
        self._transitions.clear()


class RejectionCycleHandler:
    """Handles WP rejection cycles (for_review -> planned).

    Tracks rejection iterations and enforces limits.

    Attributes:
        max_iterations: Maximum allowed rejections
        current_iteration: Current rejection count
    """

    def __init__(self, max_iterations: int = 5):
        """Initialize the handler.

        Args:
            max_iterations: Maximum allowed rejection cycles
        """
        self.max_iterations = max_iterations
        self.current_iteration = 0
        self._rejections: List[Dict[str, Any]] = []

    def handle_rejection(
        self,
        wp_id: str,
        rejection_reason: str,
        reviewer_agent: str,
    ) -> WorkflowObservation:
        """Handle a review rejection.

        Args:
            wp_id: ID of the rejected WP
            rejection_reason: Why the WP was rejected
            reviewer_agent: ID of the agent that rejected

        Returns:
            Observation recording the rejection
        """
        self.current_iteration += 1

        rejection_data = {
            "wp_id": wp_id,
            "iteration": self.current_iteration,
            "reason": rejection_reason,
            "reviewer": reviewer_agent,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "max_reached": self.current_iteration >= self.max_iterations,
        }
        self._rejections.append(rejection_data)

        return WorkflowObservation(
            step="rejection",
            agent_id=reviewer_agent,
            event_type=EventType.WP_LANE_CHANGED,
            data={
                "from_lane": WPLane.FOR_REVIEW.value,
                "to_lane": WPLane.PLANNED.value,
                "rejection_reason": rejection_reason,
                "iteration": self.current_iteration,
            },
            success=True,
        )

    def can_continue(self) -> bool:
        """Check if more rejection cycles are allowed.

        Returns:
            True if iterations remaining, False if limit reached
        """
        return self.current_iteration < self.max_iterations

    def get_rejection_history(self) -> List[Dict[str, Any]]:
        """Return all rejection records.

        Returns:
            List of rejection data dictionaries
        """
        return self._rejections.copy()

    def reset(self):
        """Reset iteration count and history."""
        self.current_iteration = 0
        self._rejections.clear()


class WorkflowEngine:
    """Orchestrates workflow execution with limits.

    Combines validator and rejection handler for complete workflow management.

    Attributes:
        validator: WorkflowValidator instance
        rejection_handler: RejectionCycleHandler instance
    """

    def __init__(
        self,
        validator: WorkflowValidator,
        rejection_handler: RejectionCycleHandler,
    ):
        """Initialize the engine.

        Args:
            validator: Validator for lane transitions
            rejection_handler: Handler for rejection cycles
        """
        self.validator = validator
        self.rejection_handler = rejection_handler

    def check_iteration_limit(self) -> None:
        """Raise if max iterations exceeded.

        Raises:
            IterationLimitError: If max iterations reached
        """
        if not self.rejection_handler.can_continue():
            raise IterationLimitError(
                iterations=self.rejection_handler.current_iteration,
                max_iterations=self.rejection_handler.max_iterations,
                rejection_history=self.rejection_handler.get_rejection_history(),
            )

    def should_rework(self, review_result: Dict[str, Any]) -> bool:
        """Determine if rework is needed based on review result.

        Args:
            review_result: Result from review containing 'approved' key

        Returns:
            True if rework needed, False if approved

        Raises:
            IterationLimitError: If rework needed but limit exceeded
        """
        if review_result.get("approved", False):
            return False

        self.check_iteration_limit()
        return True

    def process_transition(
        self,
        from_lane: WPLane,
        to_lane: WPLane,
        wp_id: str,
        rejection_reason: Optional[str] = None,
        reviewer_agent: Optional[str] = None,
    ) -> WorkflowObservation:
        """Process a lane transition.

        Args:
            from_lane: Current lane
            to_lane: Target lane
            wp_id: ID of the WP
            rejection_reason: Reason if this is a rejection
            reviewer_agent: Agent ID if this is a rejection

        Returns:
            WorkflowObservation for the transition

        Raises:
            ValueError: If transition is invalid
            IterationLimitError: If rejection exceeds limit
        """
        # Validate the transition
        if not self.validator.validate_transition(from_lane, to_lane):
            raise ValueError(
                f"Invalid transition: {from_lane.value} -> {to_lane.value}"
            )

        # Handle rejection case
        if from_lane == WPLane.FOR_REVIEW and to_lane == WPLane.PLANNED:
            if rejection_reason is None:
                rejection_reason = "No reason provided"
            if reviewer_agent is None:
                reviewer_agent = "unknown"

            return self.rejection_handler.handle_rejection(
                wp_id=wp_id,
                rejection_reason=rejection_reason,
                reviewer_agent=reviewer_agent,
            )

        # Normal transition
        return self.validator.record_lane_change(from_lane, to_lane)

    def reset(self):
        """Reset both validator and rejection handler."""
        self.validator.reset()
        self.rejection_handler.reset()


class LaneMonitor:
    """Monitors WP lane transitions during test execution.

    Polls spec-kitty CLI to track lane changes.

    Attributes:
        worktree_path: Path to the worktree
        wp_id: ID of the WP to monitor
        poll_interval: Seconds between polls
    """

    def __init__(
        self,
        worktree_path: str,
        wp_id: str,
        poll_interval: float = 1.0,
    ):
        """Initialize the monitor.

        Args:
            worktree_path: Path to the worktree
            wp_id: ID of the WP to monitor
            poll_interval: Seconds between status polls
        """
        self.worktree_path = worktree_path
        self.wp_id = wp_id
        self.poll_interval = poll_interval
        self._observations: List[WorkflowObservation] = []
        self._last_lane: Optional[WPLane] = None

    def get_current_lane(self) -> WPLane:
        """Read current WP lane from spec-kitty status.

        Returns:
            Current WPLane value

        Raises:
            RuntimeError: If spec-kitty command fails
        """
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "get-task", self.wp_id, "--json"],
            cwd=self.worktree_path,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Failed to get WP status: {result.stderr}")

        data = json.loads(result.stdout)
        return WPLane(data.get("lane", "planned"))

    def wait_for_lane(
        self,
        target_lane: WPLane,
        timeout: int = 300,
        validator: Optional[WorkflowValidator] = None,
        on_change: Optional[Callable[[WPLane, WPLane], None]] = None,
    ) -> bool:
        """Wait for WP to reach target lane.

        Args:
            target_lane: Lane to wait for
            timeout: Maximum wait time in seconds
            validator: Optional validator for transition checking
            on_change: Optional callback for lane changes

        Returns:
            True if lane reached, False on timeout
        """
        start_time = time.time()
        last_lane = self.get_current_lane()
        self._last_lane = last_lane

        while time.time() - start_time < timeout:
            current_lane = self.get_current_lane()

            if current_lane != last_lane:
                # Lane changed - record observation
                obs = WorkflowObservation(
                    step="lane_monitor",
                    agent_id=None,
                    event_type=EventType.WP_LANE_CHANGED,
                    data={
                        "from_lane": last_lane.value,
                        "to_lane": current_lane.value,
                        "wp_id": self.wp_id,
                    },
                    success=True,
                )
                self._observations.append(obs)

                if validator:
                    validator.validate_transition(last_lane, current_lane)

                if on_change:
                    on_change(last_lane, current_lane)

                last_lane = current_lane
                self._last_lane = current_lane

            if current_lane == target_lane:
                return True

            time.sleep(self.poll_interval)

        return False

    def get_observations(self) -> List[WorkflowObservation]:
        """Return all lane change observations.

        Returns:
            List of WorkflowObservation objects
        """
        return self._observations.copy()

    def get_last_lane(self) -> Optional[WPLane]:
        """Return the last observed lane.

        Returns:
            Last WPLane value or None if not yet observed
        """
        return self._last_lane


class TestFeatureScaffold:
    """Creates isolated test features for workflow testing.

    Generates minimal spec-kitty feature structure for tests.

    Attributes:
        base_worktree: Base path for creating features
    """

    def __init__(self, base_worktree: str):
        """Initialize the scaffold.

        Args:
            base_worktree: Base path for feature directories
        """
        self.base_worktree = base_worktree
        self._created_features: List[str] = []

    def create_test_feature(
        self,
        feature_name: str,
        num_wps: int = 1,
    ) -> Dict[str, Any]:
        """Create a minimal test feature with WPs.

        Args:
            feature_name: Name for the test feature
            num_wps: Number of work packages to create

        Returns:
            Dict with feature_id, feature_dir, wp_ids
        """
        # Create feature directory with unique ID
        feature_id = f"test-{feature_name}-{uuid.uuid4().hex[:8]}"
        feature_dir = Path(self.base_worktree) / "kitty-specs" / feature_id

        feature_dir.mkdir(parents=True, exist_ok=True)
        (feature_dir / "tasks").mkdir(exist_ok=True)

        # Create minimal spec.md
        spec_content = f"""# Test Feature: {feature_name}

**Feature Branch**: `{feature_id}`
**Created**: {datetime.utcnow().isoformat()}Z
**Status**: Test

## Problem Statement

Test feature for agentic E2E testing.

## User Scenarios

Test scenario for validation.

## Requirements

- Test requirement 1
"""
        (feature_dir / "spec.md").write_text(spec_content)

        # Create WP files
        wp_ids = []
        for i in range(1, num_wps + 1):
            wp_id = f"WP{i:02d}"
            wp_content = f"""---
work_package_id: "{wp_id}"
title: "Test Work Package {i}"
lane: "planned"
subtasks:
  - "T{i:03d}"
phase: "Test Phase"
assignee: ""
agent: ""
history:
  - timestamp: "{datetime.utcnow().isoformat()}Z"
    lane: "planned"
    agent: "system"
    action: "Created for testing"
---

# Work Package Prompt: {wp_id} - Test WP {i}

## Objective

Test work package for E2E validation.

## Subtasks

### T{i:03d}: Test task

Do something testable.

## Definition of Done

- [ ] Test passes
"""
            wp_file = feature_dir / "tasks" / f"{wp_id}-test-wp-{i}.md"
            wp_file.write_text(wp_content)
            wp_ids.append(wp_id)

        self._created_features.append(str(feature_dir))

        return {
            "feature_id": feature_id,
            "feature_dir": str(feature_dir),
            "wp_ids": wp_ids,
        }

    def cleanup(self):
        """Remove all created test features."""
        for feature_dir in self._created_features:
            shutil.rmtree(feature_dir, ignore_errors=True)
        self._created_features.clear()

    def get_created_features(self) -> List[str]:
        """Return list of created feature directories."""
        return self._created_features.copy()


# === Pytest Fixtures ===


@pytest.fixture
def workflow_validator() -> WorkflowValidator:
    """Create a workflow validator for testing.

    Returns:
        WorkflowValidator instance with default max_iterations=5
    """
    return WorkflowValidator(max_iterations=5)


@pytest.fixture
def rejection_handler() -> RejectionCycleHandler:
    """Create a rejection cycle handler.

    Returns:
        RejectionCycleHandler instance with default max_iterations=5
    """
    return RejectionCycleHandler(max_iterations=5)


@pytest.fixture
def workflow_engine(
    workflow_validator: WorkflowValidator,
    rejection_handler: RejectionCycleHandler,
) -> WorkflowEngine:
    """Create a workflow engine.

    Args:
        workflow_validator: Validator fixture
        rejection_handler: Handler fixture

    Returns:
        WorkflowEngine combining both
    """
    return WorkflowEngine(workflow_validator, rejection_handler)


@pytest.fixture
def test_feature_scaffold(tmp_path) -> TestFeatureScaffold:
    """Create test feature scaffolding.

    Automatically cleans up created features after test.

    Args:
        tmp_path: pytest's tmp_path fixture

    Yields:
        TestFeatureScaffold instance
    """
    scaffold = TestFeatureScaffold(str(tmp_path))
    yield scaffold
    scaffold.cleanup()


@pytest.fixture
def lane_monitor_factory(tmp_path):
    """Factory fixture for creating LaneMonitor instances.

    Returns:
        Function that creates LaneMonitor for given wp_id
    """
    def _create_monitor(wp_id: str, poll_interval: float = 1.0) -> LaneMonitor:
        return LaneMonitor(
            worktree_path=str(tmp_path),
            wp_id=wp_id,
            poll_interval=poll_interval,
        )

    return _create_monitor


@pytest.fixture
def test_run_factory():
    """Factory fixture for creating TestRun instances.

    Returns:
        Function that creates TestRun with given parameters
    """
    def _create_run(
        path_id: str,
        agent_assignments: Optional[Dict[str, str]] = None,
    ) -> TestRun:
        return TestRun(
            path_id=path_id,
            agent_assignments=agent_assignments or {},
        )

    return _create_run
