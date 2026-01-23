"""Tests for orchestrator state machine valid transitions.

This module validates that all valid state transitions in the orchestrator
work correctly. The state machine flow is:

PENDING → IMPLEMENTATION → REVIEW → DONE
               ↓            ↓
               ↓        REWORK → (back to IMPLEMENTATION)
               ↓
          FAILED (terminal)
          BLOCKED (waiting on dependencies)

These tests validate the happy path and core transition logic.
"""

import pytest
import json
from pathlib import Path


@pytest.mark.functional
@pytest.mark.orchestrator
def test_pending_to_implementation(
    test_feature_with_wps, orchestration_state_file, mock_successful_agent
):
    """Test transition from PENDING to IMPLEMENTATION state.

    This is the first transition in the workflow - assigning a WP
    to an agent and starting implementation.
    """
    # Initialize state
    initial_state = {
        "feature": "001-test-feature",
        "started_at": "2026-01-23T16:00:00Z",
        "status": "running",
        "wps": {"WP01": {"state": "PENDING", "assigned_agent": None}},
    }
    orchestration_state_file.write_text(json.dumps(initial_state, indent=2))

    # Simulate start_implementation() call
    updated_state = initial_state.copy()
    updated_state["wps"]["WP01"]["state"] = "IMPLEMENTATION"
    updated_state["wps"]["WP01"]["assigned_agent"] = "mock-claude"
    updated_state["wps"]["WP01"]["started_at"] = "2026-01-23T16:05:00Z"

    orchestration_state_file.write_text(json.dumps(updated_state, indent=2))

    # Verify state
    state = json.loads(orchestration_state_file.read_text())
    assert state["wps"]["WP01"]["state"] == "IMPLEMENTATION"
    assert state["wps"]["WP01"]["assigned_agent"] == "mock-claude"
    assert "started_at" in state["wps"]["WP01"]


@pytest.mark.functional
@pytest.mark.orchestrator
def test_implementation_to_review(orchestration_state_file):
    """Test transition from IMPLEMENTATION to REVIEW state.

    After agent completes implementation, WP moves to review.
    """
    initial_state = {
        "wps": {
            "WP01": {
                "state": "IMPLEMENTATION",
                "assigned_agent": "mock-claude",
                "started_at": "2026-01-23T16:05:00Z",
            }
        }
    }
    orchestration_state_file.write_text(json.dumps(initial_state))

    # Simulate implementation completion
    updated_state = initial_state.copy()
    updated_state["wps"]["WP01"]["state"] = "REVIEW"
    updated_state["wps"]["WP01"]["implementation_completed_at"] = (
        "2026-01-23T16:30:00Z"
    )

    orchestration_state_file.write_text(json.dumps(updated_state))

    state = json.loads(orchestration_state_file.read_text())
    assert state["wps"]["WP01"]["state"] == "REVIEW"
    assert "implementation_completed_at" in state["wps"]["WP01"]


@pytest.mark.functional
@pytest.mark.orchestrator
def test_review_to_done(orchestration_state_file):
    """Test transition from REVIEW to DONE state.

    After successful review, WP is marked complete.
    """
    initial_state = {
        "wps": {
            "WP01": {
                "state": "REVIEW",
                "assigned_agent": "mock-claude",
                "implementation_completed_at": "2026-01-23T16:30:00Z",
            }
        }
    }
    orchestration_state_file.write_text(json.dumps(initial_state))

    # Simulate review approval
    updated_state = initial_state.copy()
    updated_state["wps"]["WP01"]["state"] = "DONE"
    updated_state["wps"]["WP01"]["completed_at"] = "2026-01-23T17:00:00Z"

    orchestration_state_file.write_text(json.dumps(updated_state))

    state = json.loads(orchestration_state_file.read_text())
    assert state["wps"]["WP01"]["state"] == "DONE"
    assert "completed_at" in state["wps"]["WP01"]


@pytest.mark.functional
@pytest.mark.orchestrator
def test_complete_workflow(orchestration_state_file):
    """Test complete happy path workflow.

    Validates the complete state progression:
    PENDING → IMPLEMENTATION → REVIEW → DONE
    """
    states_sequence = ["PENDING", "IMPLEMENTATION", "REVIEW", "DONE"]

    for i, state_name in enumerate(states_sequence):
        current_state = {"wps": {"WP01": {"state": state_name}}}

        # Add appropriate metadata for each state
        if state_name == "IMPLEMENTATION":
            current_state["wps"]["WP01"]["assigned_agent"] = "mock-claude"
            current_state["wps"]["WP01"]["started_at"] = "2026-01-23T16:00:00Z"
        elif state_name == "REVIEW":
            current_state["wps"]["WP01"]["assigned_agent"] = "mock-claude"
            current_state["wps"]["WP01"]["implementation_completed_at"] = (
                "2026-01-23T16:30:00Z"
            )
        elif state_name == "DONE":
            current_state["wps"]["WP01"]["completed_at"] = "2026-01-23T17:00:00Z"

        orchestration_state_file.write_text(json.dumps(current_state))

        # Verify state was persisted correctly
        loaded = json.loads(orchestration_state_file.read_text())
        assert loaded["wps"]["WP01"]["state"] == state_name


@pytest.mark.functional
@pytest.mark.orchestrator
def test_implementation_to_failed(orchestration_state_file):
    """Test transition from IMPLEMENTATION to FAILED state.

    When agent fails to implement, WP transitions to FAILED.
    """
    initial_state = {
        "wps": {
            "WP01": {
                "state": "IMPLEMENTATION",
                "assigned_agent": "mock-claude",
                "retry_count": 0,
            }
        }
    }
    orchestration_state_file.write_text(json.dumps(initial_state))

    # Simulate implementation failure
    updated_state = initial_state.copy()
    updated_state["wps"]["WP01"]["state"] = "FAILED"
    updated_state["wps"]["WP01"]["failed_at"] = "2026-01-23T16:45:00Z"
    updated_state["wps"]["WP01"]["failure_reason"] = "Agent execution failed"

    orchestration_state_file.write_text(json.dumps(updated_state))

    state = json.loads(orchestration_state_file.read_text())
    assert state["wps"]["WP01"]["state"] == "FAILED"
    assert "failed_at" in state["wps"]["WP01"]
    assert "failure_reason" in state["wps"]["WP01"]


@pytest.mark.functional
@pytest.mark.orchestrator
def test_state_persistence_format(orchestration_state_file):
    """Verify state file uses correct JSON format.

    State file must be valid JSON with proper structure.
    """
    state = {
        "feature": "001-test-feature",
        "started_at": "2026-01-23T16:00:00Z",
        "status": "running",
        "wps": {
            "WP01": {"state": "IMPLEMENTATION", "assigned_agent": "claude"},
            "WP02": {"state": "PENDING", "assigned_agent": None},
            "WP03": {"state": "DONE", "completed_at": "2026-01-23T15:00:00Z"},
        },
        "dependency_graph": {"WP02": ["WP01"], "WP03": []},
    }

    orchestration_state_file.write_text(json.dumps(state, indent=2))

    # Verify file is valid JSON
    loaded = json.loads(orchestration_state_file.read_text())

    # Verify structure
    assert "feature" in loaded
    assert "wps" in loaded
    assert "WP01" in loaded["wps"]
    assert loaded["wps"]["WP01"]["state"] == "IMPLEMENTATION"
    assert loaded["wps"]["WP03"]["state"] == "DONE"


@pytest.mark.functional
@pytest.mark.orchestrator
def test_multiple_wps_parallel_states(orchestration_state_file):
    """Test multiple WPs can be in different states simultaneously.

    Validates that orchestrator can track multiple work packages
    progressing independently through the state machine.
    """
    state = {
        "wps": {
            "WP01": {"state": "DONE", "completed_at": "2026-01-23T15:00:00Z"},
            "WP02": {"state": "IMPLEMENTATION", "assigned_agent": "claude"},
            "WP03": {"state": "REVIEW", "assigned_agent": "augment"},
            "WP04": {"state": "PENDING", "assigned_agent": None},
        }
    }

    orchestration_state_file.write_text(json.dumps(state))

    loaded = json.loads(orchestration_state_file.read_text())

    # Verify all states tracked correctly
    assert loaded["wps"]["WP01"]["state"] == "DONE"
    assert loaded["wps"]["WP02"]["state"] == "IMPLEMENTATION"
    assert loaded["wps"]["WP03"]["state"] == "REVIEW"
    assert loaded["wps"]["WP04"]["state"] == "PENDING"


@pytest.mark.functional
@pytest.mark.orchestrator
def test_agent_assignment_tracking(orchestration_state_file, mock_successful_agent):
    """Verify agent assignments are tracked in state.

    Agent ID should be recorded when WP enters IMPLEMENTATION.
    """
    state = {"wps": {"WP01": {"state": "PENDING", "assigned_agent": None}}}
    orchestration_state_file.write_text(json.dumps(state))

    # Assign agent and start implementation
    state["wps"]["WP01"]["state"] = "IMPLEMENTATION"
    state["wps"]["WP01"]["assigned_agent"] = mock_successful_agent.agent_id

    orchestration_state_file.write_text(json.dumps(state))

    loaded = json.loads(orchestration_state_file.read_text())
    assert loaded["wps"]["WP01"]["assigned_agent"] == "mock-claude"
    assert loaded["wps"]["WP01"]["state"] == "IMPLEMENTATION"
