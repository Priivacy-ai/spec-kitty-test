---
work_package_id: WP05
title: 'Workflow Engine: State Transitions and Validation'
lane: "for_review"
dependencies: []
subtasks:
- T018
- T019
- T020
- T021
- T024
phase: Phase 2 - Fixtures
assignee: ''
agent: "claude-opus"
shell_pid: "60062"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-19T00:00:00Z'
  lane: planned
  agent: system
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP05 – Workflow Engine: State Transitions and Validation

## Objective

Implement the workflow validation logic for the implement → review workflow phase. This includes state transition validation, rejection cycle handling, max iteration limits, and lane transition verification. Also create workflow_fixtures.py for test feature scaffolding.

## Context

**Depends On**: WP03 (fixtures), WP04 (test paths)
**User Stories Addressed**: US1-3 (Workflow Validation)
**Functional Requirements**: FR-017, FR-018, FR-019, FR-020

This work package implements the core workflow engine that validates spec-kitty's behavior. It tracks WP lane transitions (planned → doing → for_review → done), handles rejection cycles (for_review → planned), and enforces iteration limits.

## Subtasks

### T018: Implement workflow validation (implement → review)

Create `tests/agentic/fixtures/workflow_fixtures.py`:

```python
"""Workflow validation and test scaffolding fixtures."""

import pytest
import json
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum
import uuid

class TestStatus(Enum):
    """Status of a test run."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"

class EventType(Enum):
    """Types of workflow events."""
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
    """Valid WP lane values."""
    PLANNED = "planned"
    DOING = "doing"
    FOR_REVIEW = "for_review"
    DONE = "done"

@dataclass
class WorkflowObservation:
    """Captured data from a workflow step."""
    step: str
    agent_id: Optional[str]
    event_type: EventType
    data: Dict[str, Any]
    success: bool = True
    timestamp: datetime = field(default_factory=datetime.utcnow)
    observation_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

@dataclass
class WorkflowState:
    """Current state of the workflow."""
    current_step: str
    wp_lane: WPLane
    iteration: int = 0

@dataclass
class TestRun:
    """A complete test execution record."""
    path_id: str
    agent_assignments: Dict[str, str]
    status: TestStatus = TestStatus.PENDING
    workflow_state: Optional[WorkflowState] = None
    observations: List[WorkflowObservation] = field(default_factory=list)
    failure_reason: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def complete(self):
        """Mark run as complete."""
        self.completed_at = datetime.utcnow()

    def to_json(self) -> dict:
        """Export to JSON-serializable dict per data-model.md schema."""
        return {
            "run_id": self.run_id,
            "path_id": self.path_id,
            "agent_assignments": self.agent_assignments,
            "started_at": self.started_at.isoformat() + "Z",
            "completed_at": self.completed_at.isoformat() + "Z" if self.completed_at else None,
            "status": self.status.value,
            "workflow_state": {
                "current_step": self.workflow_state.current_step,
                "wp_lane": self.workflow_state.wp_lane.value,
                "iteration": self.workflow_state.iteration
            } if self.workflow_state else None,
            "observations": [
                {
                    "observation_id": obs.observation_id,
                    "timestamp": obs.timestamp.isoformat() + "Z",
                    "step": obs.step,
                    "agent_id": obs.agent_id,
                    "event_type": obs.event_type.value,
                    "data": obs.data
                }
                for obs in self.observations
            ],
            "failure_reason": self.failure_reason
        }

class WorkflowValidator:
    """Validates workflow state transitions."""

    # Valid lane transitions
    VALID_TRANSITIONS = {
        WPLane.PLANNED: [WPLane.DOING],
        WPLane.DOING: [WPLane.FOR_REVIEW],
        WPLane.FOR_REVIEW: [WPLane.DONE, WPLane.PLANNED],  # Can go back on rejection
        WPLane.DONE: []  # Terminal state
    }

    def __init__(self, max_iterations: int = 5):
        self.max_iterations = max_iterations
        self._transitions: List[tuple] = []

    def validate_transition(
        self,
        from_lane: WPLane,
        to_lane: WPLane
    ) -> bool:
        """Check if lane transition is valid."""
        valid = to_lane in self.VALID_TRANSITIONS.get(from_lane, [])
        self._transitions.append((from_lane, to_lane, valid))
        return valid

    def record_lane_change(
        self,
        from_lane: WPLane,
        to_lane: WPLane,
        timestamp: datetime = None
    ) -> WorkflowObservation:
        """Record a lane change observation."""
        is_valid = self.validate_transition(from_lane, to_lane)

        return WorkflowObservation(
            step="lane_change",
            agent_id=None,
            event_type=EventType.WP_LANE_CHANGED,
            data={
                "from_lane": from_lane.value,
                "to_lane": to_lane.value,
                "valid": is_valid
            },
            success=is_valid,
            timestamp=timestamp or datetime.utcnow()
        )

    def get_transition_history(self) -> List[tuple]:
        """Return all recorded transitions."""
        return self._transitions.copy()
```

**Acceptance Criteria**:
- WorkflowState tracks current step and lane
- VALID_TRANSITIONS defines allowed lane changes
- validate_transition checks legality
- WorkflowObservation captures lane changes
- TestRun aggregates all workflow data

### T019: Implement rejection cycle handling (back to planned)

Extend WorkflowValidator for rejection cycles:

```python
# In workflow_fixtures.py

class RejectionCycleHandler:
    """Handles WP rejection cycles (for_review → planned)."""

    def __init__(self, max_iterations: int = 5):
        self.max_iterations = max_iterations
        self.current_iteration = 0
        self._rejections: List[Dict[str, Any]] = []

    def handle_rejection(
        self,
        wp_id: str,
        rejection_reason: str,
        reviewer_agent: str
    ) -> WorkflowObservation:
        """Handle a review rejection.

        Returns:
            Observation recording the rejection
        """
        self.current_iteration += 1

        rejection_data = {
            "wp_id": wp_id,
            "iteration": self.current_iteration,
            "reason": rejection_reason,
            "reviewer": reviewer_agent,
            "max_reached": self.current_iteration >= self.max_iterations
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
                "iteration": self.current_iteration
            },
            success=True
        )

    def can_continue(self) -> bool:
        """Check if more rejection cycles are allowed."""
        return self.current_iteration < self.max_iterations

    def get_rejection_history(self) -> List[Dict[str, Any]]:
        """Return all rejection records."""
        return self._rejections.copy()
```

**Acceptance Criteria**:
- Tracks rejection cycles with iteration count
- Records rejection reason and reviewer
- can_continue() respects max_iterations
- Rejection history available for analysis

### T020: Implement max iteration limits

Add iteration limit enforcement:

```python
# In workflow_fixtures.py

class IterationLimitError(Exception):
    """Raised when max iterations exceeded."""
    pass

class WorkflowEngine:
    """Orchestrates workflow execution with limits."""

    def __init__(
        self,
        validator: WorkflowValidator,
        rejection_handler: RejectionCycleHandler
    ):
        self.validator = validator
        self.rejection_handler = rejection_handler

    def check_iteration_limit(self) -> None:
        """Raise if max iterations exceeded."""
        if not self.rejection_handler.can_continue():
            raise IterationLimitError(
                f"Max iterations ({self.rejection_handler.max_iterations}) exceeded. "
                f"Rejections: {self.rejection_handler.get_rejection_history()}"
            )

    def should_rework(self, review_result: Dict[str, Any]) -> bool:
        """Determine if rework is needed based on review result."""
        if review_result.get("approved", False):
            return False

        self.check_iteration_limit()
        return True
```

**Acceptance Criteria**:
- IterationLimitError raised when limit exceeded
- check_iteration_limit() callable at any point
- Limit configurable per test path
- Clear error message with iteration history

### T021: Implement WP lane transition verification

Create lane monitoring utilities:

```python
# In workflow_fixtures.py

import time
from typing import Callable

class LaneMonitor:
    """Monitors WP lane transitions during test execution."""

    def __init__(
        self,
        worktree_path: str,
        wp_id: str,
        poll_interval: float = 1.0
    ):
        self.worktree_path = worktree_path
        self.wp_id = wp_id
        self.poll_interval = poll_interval
        self._observations: List[WorkflowObservation] = []

    def get_current_lane(self) -> WPLane:
        """Read current WP lane from spec-kitty status."""
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "get-task", self.wp_id, "--json"],
            cwd=self.worktree_path,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise RuntimeError(f"Failed to get WP status: {result.stderr}")

        data = json.loads(result.stdout)
        return WPLane(data.get("lane", "planned"))

    def wait_for_lane(
        self,
        target_lane: WPLane,
        timeout: int = 300,
        validator: Optional[WorkflowValidator] = None
    ) -> bool:
        """Wait for WP to reach target lane.

        Args:
            target_lane: Lane to wait for
            timeout: Maximum wait time in seconds
            validator: Optional validator for transition checking

        Returns:
            True if lane reached, False on timeout
        """
        start_time = time.time()
        last_lane = self.get_current_lane()

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
                        "to_lane": current_lane.value
                    },
                    success=True
                )
                self._observations.append(obs)

                if validator:
                    validator.validate_transition(last_lane, current_lane)

                last_lane = current_lane

            if current_lane == target_lane:
                return True

            time.sleep(self.poll_interval)

        return False

    def get_observations(self) -> List[WorkflowObservation]:
        """Return all lane change observations."""
        return self._observations.copy()


@pytest.fixture
def workflow_validator():
    """Create a workflow validator for testing."""
    return WorkflowValidator(max_iterations=5)

@pytest.fixture
def rejection_handler():
    """Create a rejection cycle handler."""
    return RejectionCycleHandler(max_iterations=5)

@pytest.fixture
def workflow_engine(workflow_validator, rejection_handler):
    """Create a workflow engine."""
    return WorkflowEngine(workflow_validator, rejection_handler)
```

**Acceptance Criteria**:
- LaneMonitor polls WP status via spec-kitty CLI
- wait_for_lane() blocks until target or timeout
- All lane changes recorded as observations
- Integrates with WorkflowValidator

### T024: Create workflow_fixtures.py for test feature scaffolding

Add test feature creation utilities:

```python
# In workflow_fixtures.py

import tempfile
import shutil

class TestFeatureScaffold:
    """Creates isolated test features for workflow testing."""

    def __init__(self, base_worktree: str):
        self.base_worktree = base_worktree
        self._created_features: List[str] = []

    def create_test_feature(
        self,
        feature_name: str,
        num_wps: int = 1
    ) -> Dict[str, Any]:
        """Create a minimal test feature with WPs.

        Args:
            feature_name: Name for the test feature
            num_wps: Number of work packages to create

        Returns:
            Dict with feature_dir, wp_ids, etc.
        """
        # Create feature directory
        feature_id = f"test-{feature_name}-{uuid.uuid4().hex[:8]}"
        feature_dir = Path(self.base_worktree) / "kitty-specs" / feature_id

        feature_dir.mkdir(parents=True, exist_ok=True)
        (feature_dir / "tasks").mkdir(exist_ok=True)

        # Create minimal spec.md
        spec_content = f"""# Test Feature: {feature_name}

**Feature Branch**: `{feature_id}`
**Created**: {datetime.utcnow().isoformat()}
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

# Work Package Prompt: {wp_id} – Test WP {i}

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
            "wp_ids": wp_ids
        }

    def cleanup(self):
        """Remove all created test features."""
        for feature_dir in self._created_features:
            shutil.rmtree(feature_dir, ignore_errors=True)
        self._created_features.clear()


@pytest.fixture
def test_feature_scaffold(tmp_path):
    """Create test feature scaffolding."""
    scaffold = TestFeatureScaffold(str(tmp_path))
    yield scaffold
    scaffold.cleanup()

@pytest.fixture
def tmp_worktree(tmp_path):
    """Create a temporary worktree directory."""
    worktree = tmp_path / "worktree"
    worktree.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=worktree, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=worktree, check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=worktree, check=True
    )

    # Initial commit
    (worktree / ".gitkeep").touch()
    subprocess.run(["git", "add", "."], cwd=worktree, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=worktree, check=True
    )

    return str(worktree)
```

**Acceptance Criteria**:
- TestFeatureScaffold creates minimal test features
- WP files created with proper frontmatter
- Automatic cleanup after tests
- tmp_worktree fixture provides git-initialized directory

## Technical Notes

- Lane monitoring uses spec-kitty CLI commands
- Test features are minimal to speed up tests
- All scaffolding cleaned up automatically
- Fixtures compose for complete test setup

## Files to Create/Modify

1. `tests/agentic/fixtures/workflow_fixtures.py` (create)
2. `tests/agentic/fixtures/__init__.py` (update exports)
3. `tests/agentic/conftest.py` (import fixtures)

## Verification

```bash
# Import check
python -c "
from tests.agentic.fixtures.workflow_fixtures import (
    WorkflowValidator, RejectionCycleHandler, TestRun, WPLane
)
"

# Unit tests
pytest tests/agentic/fixtures/test_workflow.py -v
```

## Definition of Done

- [ ] WorkflowValidator with transition validation
- [ ] RejectionCycleHandler with iteration tracking
- [ ] WorkflowEngine with limit enforcement
- [ ] LaneMonitor for WP status polling
- [ ] TestFeatureScaffold for test setup
- [ ] All classes exported in __init__.py
- [ ] Fixtures registered in conftest.py
- [ ] Unit tests pass

## Activity Log

- 2026-01-19T14:35:19Z – claude-opus – shell_pid=60062 – lane=doing – Started implementation via workflow command
- 2026-01-19T14:39:26Z – claude-opus – shell_pid=60062 – lane=for_review – Ready for review: WorkflowValidator, RejectionCycleHandler, WorkflowEngine, LaneMonitor, TestFeatureScaffold implemented. All classes exported in __init__.py and fixtures registered in conftest.py. Verified imports and basic functionality.
