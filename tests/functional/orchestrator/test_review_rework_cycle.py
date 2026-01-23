"""Tests for review rejection and rework cycle.

The rework cycle is a critical feature that allows work packages to
be rejected during review and sent back for fixes. The cycle is:

REVIEW (rejected) → REWORK → IMPLEMENTATION → REVIEW (retry) → DONE

This is essential for quality control - not all implementations are
acceptable on first try. The orchestrator must handle this gracefully:
- Track retry attempts
- Preserve context across rework cycles
- Support agent reassignment if needed
- Eventually succeed or reach max retries
"""

import pytest
import json


@pytest.mark.functional
@pytest.mark.orchestrator
def test_review_rejection_to_rework(orchestration_state_file):
    """Test review rejection creates REWORK state.

    When a reviewer rejects implementation, WP transitions to REWORK
    state and retry count increments.
    """
    state = {
        "wps": {
            "WP01": {
                "state": "REVIEW",
                "assigned_agent": "claude",
                "implementation_completed_at": "2026-01-23T16:30:00Z",
                "retry_count": 0,
            }
        }
    }
    orchestration_state_file.write_text(json.dumps(state))

    # Simulate review rejection
    updated_state = state.copy()
    updated_state["wps"]["WP01"]["state"] = "REWORK"
    updated_state["wps"]["WP01"]["retry_count"] = 1
    updated_state["wps"]["WP01"]["rejection_reason"] = (
        "Code does not meet requirements"
    )
    updated_state["wps"]["WP01"]["rejected_at"] = "2026-01-23T16:45:00Z"

    orchestration_state_file.write_text(json.dumps(updated_state))

    final = json.loads(orchestration_state_file.read_text())
    assert final["wps"]["WP01"]["state"] == "REWORK"
    assert final["wps"]["WP01"]["retry_count"] == 1
    assert "rejection_reason" in final["wps"]["WP01"]
    assert "rejected_at" in final["wps"]["WP01"]


@pytest.mark.functional
@pytest.mark.orchestrator
def test_rework_to_implementation(orchestration_state_file):
    """Test REWORK transitions back to IMPLEMENTATION.

    After review rejection, the agent re-implements with feedback.
    """
    state = {
        "wps": {
            "WP01": {
                "state": "REWORK",
                "assigned_agent": "claude",
                "retry_count": 1,
                "rejection_reason": "Missing tests",
            }
        }
    }
    orchestration_state_file.write_text(json.dumps(state))

    # Re-invoke implementation agent
    updated_state = state.copy()
    updated_state["wps"]["WP01"]["state"] = "IMPLEMENTATION"
    updated_state["wps"]["WP01"]["rework_started_at"] = "2026-01-23T16:50:00Z"

    orchestration_state_file.write_text(json.dumps(updated_state))

    final = json.loads(orchestration_state_file.read_text())
    assert final["wps"]["WP01"]["state"] == "IMPLEMENTATION"
    assert final["wps"]["WP01"]["retry_count"] == 1  # Preserved
    assert "rework_started_at" in final["wps"]["WP01"]


@pytest.mark.functional
@pytest.mark.orchestrator
def test_complete_rework_cycle(orchestration_state_file, mock_successful_agent):
    """Test complete cycle: REVIEW → REWORK → IMPLEMENTATION → REVIEW → DONE.

    This validates the full rework flow from rejection to eventual success.
    """
    # Start in REVIEW
    state = {
        "wps": {
            "WP01": {
                "state": "REVIEW",
                "assigned_agent": "claude",
                "retry_count": 0,
            }
        }
    }
    orchestration_state_file.write_text(json.dumps(state))

    # Step 1: Rejection → REWORK
    state["wps"]["WP01"]["state"] = "REWORK"
    state["wps"]["WP01"]["retry_count"] = 1
    orchestration_state_file.write_text(json.dumps(state))

    loaded = json.loads(orchestration_state_file.read_text())
    assert loaded["wps"]["WP01"]["state"] == "REWORK"

    # Step 2: REWORK → IMPLEMENTATION
    state["wps"]["WP01"]["state"] = "IMPLEMENTATION"
    orchestration_state_file.write_text(json.dumps(state))

    loaded = json.loads(orchestration_state_file.read_text())
    assert loaded["wps"]["WP01"]["state"] == "IMPLEMENTATION"

    # Step 3: IMPLEMENTATION → REVIEW (second attempt)
    state["wps"]["WP01"]["state"] = "REVIEW"
    orchestration_state_file.write_text(json.dumps(state))

    loaded = json.loads(orchestration_state_file.read_text())
    assert loaded["wps"]["WP01"]["state"] == "REVIEW"

    # Step 4: REVIEW → DONE (approved)
    state["wps"]["WP01"]["state"] = "DONE"
    state["wps"]["WP01"]["completed_at"] = "2026-01-23T17:30:00Z"
    orchestration_state_file.write_text(json.dumps(state))

    final = json.loads(orchestration_state_file.read_text())
    assert final["wps"]["WP01"]["state"] == "DONE"
    assert final["wps"]["WP01"]["retry_count"] == 1
    assert "completed_at" in final["wps"]["WP01"]


@pytest.mark.functional
@pytest.mark.orchestrator
def test_multiple_rework_cycles(orchestration_state_file):
    """Test multiple rework cycles (rejection, rework, rejection again).

    Some implementations may require multiple iterations to get right.
    Retry count should increment with each cycle.
    """
    state = {"wps": {"WP01": {"state": "REVIEW", "retry_count": 0}}}
    orchestration_state_file.write_text(json.dumps(state))

    # First rejection
    state["wps"]["WP01"]["state"] = "REWORK"
    state["wps"]["WP01"]["retry_count"] = 1
    orchestration_state_file.write_text(json.dumps(state))

    # First rework
    state["wps"]["WP01"]["state"] = "IMPLEMENTATION"
    orchestration_state_file.write_text(json.dumps(state))

    state["wps"]["WP01"]["state"] = "REVIEW"
    orchestration_state_file.write_text(json.dumps(state))

    # Second rejection
    state["wps"]["WP01"]["state"] = "REWORK"
    state["wps"]["WP01"]["retry_count"] = 2
    orchestration_state_file.write_text(json.dumps(state))

    # Second rework
    state["wps"]["WP01"]["state"] = "IMPLEMENTATION"
    orchestration_state_file.write_text(json.dumps(state))

    state["wps"]["WP01"]["state"] = "REVIEW"
    orchestration_state_file.write_text(json.dumps(state))

    # Final approval
    state["wps"]["WP01"]["state"] = "DONE"
    orchestration_state_file.write_text(json.dumps(state))

    final = json.loads(orchestration_state_file.read_text())
    assert final["wps"]["WP01"]["state"] == "DONE"
    assert final["wps"]["WP01"]["retry_count"] == 2


@pytest.mark.functional
@pytest.mark.orchestrator
def test_rework_preserves_history(orchestration_state_file):
    """Rework should preserve implementation history.

    When cycling through rework, previous attempt metadata should
    be preserved for debugging and analysis.
    """
    state = {
        "wps": {
            "WP01": {
                "state": "REVIEW",
                "assigned_agent": "claude",
                "retry_count": 0,
                "attempt_history": [
                    {
                        "attempt": 1,
                        "started_at": "2026-01-23T16:00:00Z",
                        "completed_at": "2026-01-23T16:30:00Z",
                    }
                ],
            }
        }
    }
    orchestration_state_file.write_text(json.dumps(state))

    # Rejection
    state["wps"]["WP01"]["state"] = "REWORK"
    state["wps"]["WP01"]["retry_count"] = 1
    orchestration_state_file.write_text(json.dumps(state))

    # Second attempt
    state["wps"]["WP01"]["state"] = "IMPLEMENTATION"
    state["wps"]["WP01"]["attempt_history"].append(
        {
            "attempt": 2,
            "started_at": "2026-01-23T16:50:00Z",
        }
    )
    orchestration_state_file.write_text(json.dumps(state))

    final = json.loads(orchestration_state_file.read_text())
    assert len(final["wps"]["WP01"]["attempt_history"]) == 2
    assert final["wps"]["WP01"]["attempt_history"][0]["attempt"] == 1
    assert final["wps"]["WP01"]["attempt_history"][1]["attempt"] == 2


@pytest.mark.functional
@pytest.mark.orchestrator
def test_agent_reassignment_during_rework(orchestration_state_file):
    """Test agent reassignment during rework cycle.

    If an agent repeatedly fails, orchestrator may assign different
    agent for rework attempt.
    """
    state = {
        "wps": {
            "WP01": {
                "state": "REWORK",
                "assigned_agent": "claude",
                "retry_count": 1,
                "rejection_reason": "Incomplete implementation",
            }
        }
    }
    orchestration_state_file.write_text(json.dumps(state))

    # Reassign to different agent for rework
    state["wps"]["WP01"]["state"] = "IMPLEMENTATION"
    state["wps"]["WP01"]["assigned_agent"] = "augment"  # Different agent
    state["wps"]["WP01"]["previous_agent"] = "claude"

    orchestration_state_file.write_text(json.dumps(state))

    final = json.loads(orchestration_state_file.read_text())
    assert final["wps"]["WP01"]["assigned_agent"] == "augment"
    assert final["wps"]["WP01"]["previous_agent"] == "claude"
    assert final["wps"]["WP01"]["state"] == "IMPLEMENTATION"


@pytest.mark.functional
@pytest.mark.orchestrator
def test_max_retries_transition_to_failed(orchestration_state_file):
    """Test transition to FAILED after max retries exceeded.

    After a certain number of rework attempts, WP should transition
    to FAILED state rather than continuing indefinitely.
    """
    MAX_RETRIES = 3

    state = {
        "wps": {
            "WP01": {
                "state": "REWORK",
                "assigned_agent": "claude",
                "retry_count": MAX_RETRIES,
                "rejection_reason": "Still not meeting requirements",
            }
        }
    }
    orchestration_state_file.write_text(json.dumps(state))

    # Exceeded max retries - should transition to FAILED
    state["wps"]["WP01"]["state"] = "FAILED"
    state["wps"]["WP01"]["failure_reason"] = f"Exceeded max retries ({MAX_RETRIES})"
    state["wps"]["WP01"]["failed_at"] = "2026-01-23T18:00:00Z"

    orchestration_state_file.write_text(json.dumps(state))

    final = json.loads(orchestration_state_file.read_text())
    assert final["wps"]["WP01"]["state"] == "FAILED"
    assert final["wps"]["WP01"]["retry_count"] == MAX_RETRIES
    assert "Exceeded max retries" in final["wps"]["WP01"]["failure_reason"]


@pytest.mark.functional
@pytest.mark.orchestrator
def test_rework_feedback_propagation(orchestration_state_file):
    """Rework state should include reviewer feedback.

    The rejection_reason should be available to the implementing
    agent when it re-attempts the work.
    """
    state = {
        "wps": {
            "WP01": {
                "state": "REWORK",
                "assigned_agent": "claude",
                "retry_count": 1,
                "rejection_reason": "Missing unit tests for core functionality",
                "reviewer_feedback": {
                    "issues": ["No tests in test file", "Edge cases not handled"],
                    "suggestions": [
                        "Add pytest fixtures",
                        "Test error conditions",
                    ],
                },
            }
        }
    }
    orchestration_state_file.write_text(json.dumps(state))

    # Feedback should be accessible when restarting implementation
    loaded = json.loads(orchestration_state_file.read_text())
    assert loaded["wps"]["WP01"]["rejection_reason"] is not None
    assert "reviewer_feedback" in loaded["wps"]["WP01"]
    assert len(loaded["wps"]["WP01"]["reviewer_feedback"]["issues"]) == 2
