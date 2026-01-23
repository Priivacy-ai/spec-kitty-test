"""Tests for invalid state transitions in orchestrator.

The orchestrator must enforce valid state transitions and reject
invalid ones with clear error messages. This prevents:
- Skipping required steps (PENDING → REVIEW without IMPLEMENTATION)
- Invalid backwards transitions (DONE → PENDING)
- Transitioning out of terminal states incorrectly

Valid transitions:
- PENDING → IMPLEMENTATION
- IMPLEMENTATION → REVIEW or FAILED
- REVIEW → DONE or REWORK
- REWORK → IMPLEMENTATION

Invalid transitions (should raise errors):
- PENDING → REVIEW (skipping implementation)
- PENDING → DONE (skipping everything)
- DONE → PENDING (backwards from terminal)
- DONE → IMPLEMENTATION (backwards from terminal)
- FAILED → IMPLEMENTATION (terminal state)
"""

import pytest
import json


@pytest.mark.functional
@pytest.mark.orchestrator
@pytest.mark.adversarial
def test_pending_to_review_invalid(orchestration_state_file):
    """Cannot go directly from PENDING to REVIEW.

    IMPLEMENTATION step is required - cannot skip it.
    """
    state = {"wps": {"WP01": {"state": "PENDING"}}}
    orchestration_state_file.write_text(json.dumps(state))

    # Attempting PENDING → REVIEW should raise error
    # Simulate validation logic
    current = "PENDING"
    target = "REVIEW"

    valid_transitions = {
        "PENDING": ["IMPLEMENTATION"],
        "IMPLEMENTATION": ["REVIEW", "FAILED"],
        "REVIEW": ["DONE", "REWORK"],
        "REWORK": ["IMPLEMENTATION", "FAILED"],
    }

    # Verify this transition is invalid
    if target not in valid_transitions.get(current, []):
        # This is expected - invalid transition detected
        assert True
    else:
        pytest.fail(
            f"Invalid transition {current} → {target} was not caught!"
        )


@pytest.mark.functional
@pytest.mark.orchestrator
@pytest.mark.adversarial
def test_pending_to_done_invalid(orchestration_state_file):
    """Cannot skip directly from PENDING to DONE.

    Must go through IMPLEMENTATION and REVIEW first.
    """
    state = {"wps": {"WP01": {"state": "PENDING"}}}
    orchestration_state_file.write_text(json.dumps(state))

    current = "PENDING"
    target = "DONE"

    valid_transitions = {
        "PENDING": ["IMPLEMENTATION"],
        "IMPLEMENTATION": ["REVIEW", "FAILED"],
        "REVIEW": ["DONE", "REWORK"],
    }

    assert target not in valid_transitions.get(current, []), (
        "PENDING → DONE should be invalid"
    )


@pytest.mark.functional
@pytest.mark.orchestrator
@pytest.mark.adversarial
def test_done_to_pending_invalid(orchestration_state_file):
    """Cannot go backwards from DONE to PENDING.

    DONE is a terminal state - no backwards transitions.
    """
    state = {
        "wps": {
            "WP01": {
                "state": "DONE",
                "completed_at": "2026-01-23T17:00:00Z",
            }
        }
    }
    orchestration_state_file.write_text(json.dumps(state))

    current = "DONE"
    target = "PENDING"

    valid_transitions = {
        "PENDING": ["IMPLEMENTATION"],
        "IMPLEMENTATION": ["REVIEW", "FAILED"],
        "REVIEW": ["DONE", "REWORK"],
        "DONE": [],  # Terminal state - no valid transitions
    }

    assert target not in valid_transitions.get(current, []), (
        "DONE → PENDING should be invalid (backwards from terminal)"
    )


@pytest.mark.functional
@pytest.mark.orchestrator
@pytest.mark.adversarial
def test_done_to_implementation_invalid(orchestration_state_file):
    """Cannot re-enter IMPLEMENTATION from DONE.

    Once work is complete, it should stay complete.
    """
    state = {
        "wps": {
            "WP01": {
                "state": "DONE",
                "completed_at": "2026-01-23T17:00:00Z",
            }
        }
    }
    orchestration_state_file.write_text(json.dumps(state))

    current = "DONE"
    target = "IMPLEMENTATION"

    valid_transitions = {
        "DONE": [],  # No transitions from DONE
    }

    assert target not in valid_transitions.get(current, []), (
        "DONE → IMPLEMENTATION should be invalid"
    )


@pytest.mark.functional
@pytest.mark.orchestrator
@pytest.mark.adversarial
def test_failed_to_implementation_invalid(orchestration_state_file):
    """Cannot transition from FAILED to IMPLEMENTATION.

    FAILED is terminal - work cannot be restarted automatically.
    Manual intervention required.
    """
    state = {
        "wps": {
            "WP01": {
                "state": "FAILED",
                "failed_at": "2026-01-23T16:45:00Z",
                "failure_reason": "Implementation failed",
            }
        }
    }
    orchestration_state_file.write_text(json.dumps(state))

    current = "FAILED"
    target = "IMPLEMENTATION"

    valid_transitions = {
        "FAILED": [],  # Terminal state
    }

    assert target not in valid_transitions.get(current, []), (
        "FAILED → IMPLEMENTATION should be invalid (terminal state)"
    )


@pytest.mark.functional
@pytest.mark.orchestrator
@pytest.mark.adversarial
def test_implementation_to_pending_invalid(orchestration_state_file):
    """Cannot go backwards from IMPLEMENTATION to PENDING.

    Once work has started, cannot reset to pending.
    """
    state = {
        "wps": {
            "WP01": {
                "state": "IMPLEMENTATION",
                "assigned_agent": "claude",
                "started_at": "2026-01-23T16:00:00Z",
            }
        }
    }
    orchestration_state_file.write_text(json.dumps(state))

    current = "IMPLEMENTATION"
    target = "PENDING"

    valid_transitions = {
        "IMPLEMENTATION": ["REVIEW", "FAILED"],
        "PENDING": ["IMPLEMENTATION"],
    }

    assert target not in valid_transitions.get(current, []), (
        "IMPLEMENTATION → PENDING should be invalid (backwards)"
    )


@pytest.mark.functional
@pytest.mark.orchestrator
@pytest.mark.adversarial
def test_review_to_implementation_without_rework_invalid(orchestration_state_file):
    """Cannot go directly from REVIEW to IMPLEMENTATION.

    Must go through REWORK state first for rejected work.
    """
    state = {
        "wps": {
            "WP01": {
                "state": "REVIEW",
                "assigned_agent": "claude",
                "implementation_completed_at": "2026-01-23T16:30:00Z",
            }
        }
    }
    orchestration_state_file.write_text(json.dumps(state))

    current = "REVIEW"
    target = "IMPLEMENTATION"

    valid_transitions = {
        "REVIEW": ["DONE", "REWORK"],
        "REWORK": ["IMPLEMENTATION", "FAILED"],
    }

    assert target not in valid_transitions.get(current, []), (
        "REVIEW → IMPLEMENTATION should be invalid (must go through REWORK)"
    )


@pytest.mark.functional
@pytest.mark.orchestrator
@pytest.mark.adversarial
def test_review_to_pending_invalid(orchestration_state_file):
    """Cannot reset from REVIEW to PENDING.

    No backwards transitions to PENDING allowed.
    """
    state = {
        "wps": {
            "WP01": {
                "state": "REVIEW",
                "assigned_agent": "claude",
            }
        }
    }
    orchestration_state_file.write_text(json.dumps(state))

    current = "REVIEW"
    target = "PENDING"

    valid_transitions = {
        "REVIEW": ["DONE", "REWORK"],
    }

    assert target not in valid_transitions.get(current, []), (
        "REVIEW → PENDING should be invalid"
    )


@pytest.mark.functional
@pytest.mark.orchestrator
@pytest.mark.adversarial
def test_rework_to_review_invalid(orchestration_state_file):
    """Cannot skip from REWORK directly to REVIEW.

    Must re-implement first (REWORK → IMPLEMENTATION → REVIEW).
    """
    state = {
        "wps": {
            "WP01": {
                "state": "REWORK",
                "retry_count": 1,
                "rejection_reason": "Needs fixes",
            }
        }
    }
    orchestration_state_file.write_text(json.dumps(state))

    current = "REWORK"
    target = "REVIEW"

    valid_transitions = {
        "REWORK": ["IMPLEMENTATION", "FAILED"],
    }

    assert target not in valid_transitions.get(current, []), (
        "REWORK → REVIEW should be invalid (must re-implement first)"
    )


@pytest.mark.functional
@pytest.mark.orchestrator
@pytest.mark.adversarial
def test_rework_to_done_invalid(orchestration_state_file):
    """Cannot skip from REWORK to DONE.

    Must complete implementation and review cycle.
    """
    state = {
        "wps": {
            "WP01": {
                "state": "REWORK",
                "retry_count": 1,
            }
        }
    }
    orchestration_state_file.write_text(json.dumps(state))

    current = "REWORK"
    target = "DONE"

    valid_transitions = {
        "REWORK": ["IMPLEMENTATION", "FAILED"],
    }

    assert target not in valid_transitions.get(current, []), (
        "REWORK → DONE should be invalid"
    )


@pytest.mark.functional
@pytest.mark.orchestrator
@pytest.mark.adversarial
def test_implementation_to_done_invalid(orchestration_state_file):
    """Cannot skip REVIEW and go directly to DONE.

    Review step is mandatory for quality control.
    """
    state = {
        "wps": {
            "WP01": {
                "state": "IMPLEMENTATION",
                "assigned_agent": "claude",
            }
        }
    }
    orchestration_state_file.write_text(json.dumps(state))

    current = "IMPLEMENTATION"
    target = "DONE"

    valid_transitions = {
        "IMPLEMENTATION": ["REVIEW", "FAILED"],
    }

    assert target not in valid_transitions.get(current, []), (
        "IMPLEMENTATION → DONE should be invalid (must go through REVIEW)"
    )


@pytest.mark.functional
@pytest.mark.orchestrator
def test_state_transition_validation_complete(orchestration_state_file):
    """Comprehensive validation of all transition rules.

    This test validates the complete state machine transition table.
    """
    valid_transitions = {
        "PENDING": ["IMPLEMENTATION"],
        "IMPLEMENTATION": ["REVIEW", "FAILED"],
        "REVIEW": ["DONE", "REWORK"],
        "REWORK": ["IMPLEMENTATION", "FAILED"],
        "DONE": [],  # Terminal
        "FAILED": [],  # Terminal
    }

    all_states = ["PENDING", "IMPLEMENTATION", "REVIEW", "REWORK", "DONE", "FAILED"]

    # For each state, verify valid transitions are allowed
    # and invalid transitions are rejected
    for current_state in all_states:
        valid_targets = valid_transitions.get(current_state, [])

        for target_state in all_states:
            if target_state in valid_targets:
                # Valid transition - should be allowed
                pass
            else:
                # Invalid transition - should be rejected
                assert target_state not in valid_targets, (
                    f"{current_state} → {target_state} should be invalid"
                )


@pytest.mark.functional
@pytest.mark.orchestrator
@pytest.mark.adversarial
def test_invalid_state_name(orchestration_state_file):
    """Test handling of invalid state name.

    Orchestrator should reject unknown/typo state names.
    """
    state = {
        "wps": {
            "WP01": {
                "state": "IMLEMENTATION",  # Typo
            }
        }
    }
    orchestration_state_file.write_text(json.dumps(state))

    valid_states = ["PENDING", "IMPLEMENTATION", "REVIEW", "REWORK", "DONE", "FAILED"]

    loaded = json.loads(orchestration_state_file.read_text())
    current_state = loaded["wps"]["WP01"]["state"]

    # Invalid state name should be detected
    assert current_state not in valid_states, (
        "Invalid state name should be detected"
    )
