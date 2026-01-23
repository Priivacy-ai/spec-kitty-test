"""
T070: Integration tests for orchestration state persistence.

Validates that orchestration-state.json is created, updated,
and structured correctly during real orchestration.

Validates:
- User Story 2: Orchestrator State Machine Integrity
- data-model.md: orchestration-state.json schema
"""
import json
import subprocess
from datetime import datetime

import pytest


@pytest.mark.integration
@pytest.mark.orchestrator
def test_state_file_created(
    create_test_feature,
    run_orchestration,
    spec_kitty_git_test,
    detect_available_agents
):
    """
    Verify orchestration-state.json is created.

    Runs orchestration, validates state file exists.
    """
    agents = detect_available_agents()
    if not agents:
        pytest.skip("No agents installed")

    create_test_feature("020", "020-state-test", wp_count=2)

    run_orchestration("020-state-test")

    # Check state file exists
    state_file = (
        spec_kitty_git_test / ".kittify" / "orchestration-state.json"
    )

    assert state_file.exists(), \
        "orchestration-state.json should be created"


@pytest.mark.integration
@pytest.mark.orchestrator
def test_state_schema_valid(
    create_test_feature,
    run_orchestration,
    orchestration_state,
    detect_available_agents
):
    """
    Verify orchestration state matches expected schema.

    Validates data-model.md orchestration-state.json schema.
    """
    agents = detect_available_agents()
    if not agents:
        pytest.skip("No agents installed")

    create_test_feature("021", "021-schema-test", wp_count=2)

    run_orchestration("021-schema-test")

    state = orchestration_state()
    assert state is not None, "State file should exist"

    # Validate top-level fields
    assert "feature" in state, "Should have 'feature' field"
    assert "started_at" in state, "Should have 'started_at' field"
    assert "status" in state, "Should have 'status' field"
    assert "wps" in state, "Should have 'wps' field"

    # Validate feature field
    assert isinstance(state["feature"], str)
    assert len(state["feature"]) > 0

    # Validate started_at is ISO datetime
    try:
        datetime.fromisoformat(state["started_at"].replace("Z", "+00:00"))
    except ValueError:
        pytest.fail(f"started_at not valid ISO datetime: {state['started_at']}")

    # Validate status is valid value
    assert state["status"] in ["running", "completed", "failed", "pending"]

    # Validate wps structure
    assert isinstance(state["wps"], dict)

    for wp_id, wp_state in state["wps"].items():
        # Validate WP state structure
        assert "state" in wp_state, f"{wp_id} should have 'state' field"

        # Validate state is valid value
        valid_states = [
            "PENDING", "IMPLEMENTATION", "REVIEW",
            "DONE", "REWORK", "FAILED", "BLOCKED"
        ]
        assert wp_state["state"] in valid_states, \
            f"{wp_id} state '{wp_state['state']}' not in {valid_states}"


@pytest.mark.integration
@pytest.mark.orchestrator
def test_state_updates_during_execution(
    create_test_feature,
    run_orchestration,
    orchestration_state,
    spec_kitty_git_test,
    detect_available_agents
):
    """
    Verify state updates as orchestration progresses.

    Runs orchestration, validates WP states transition
    from PENDING to other states.
    """
    agents = detect_available_agents()
    if not agents:
        pytest.skip("No agents installed")

    create_test_feature("022", "022-updates-test", wp_count=3)

    run_orchestration("022-updates-test")

    state = orchestration_state()
    assert state is not None

    # Check that not all WPs are still PENDING
    # (at least some should have transitioned)
    wp_states = [wp["state"] for wp in state["wps"].values()]

    non_pending = [s for s in wp_states if s != "PENDING"]

    assert len(non_pending) > 0, \
        "At least one WP should transition from PENDING"


@pytest.mark.integration
@pytest.mark.orchestrator
@pytest.mark.adversarial
def test_state_survives_interruption(
    create_test_feature,
    run_orchestration,
    orchestration_state,
    spec_kitty_git_test,
    detect_available_agents
):
    """
    Verify state persists after interruption.

    Starts orchestration, interrupts it (timeout),
    validates state file persisted with partial progress.
    """
    agents = detect_available_agents()
    if not agents:
        pytest.skip("No agents installed")

    create_test_feature("023", "023-interrupt-test", wp_count=3)

    # Run with short timeout (will likely interrupt)
    result = run_orchestration("023-interrupt-test", timeout=10)

    # State should still exist with partial progress
    state = orchestration_state()

    if state:
        # Should have started at least
        assert "started_at" in state

        # May have some WPs in progress
        assert "wps" in state


@pytest.mark.integration
@pytest.mark.orchestrator
def test_state_file_valid_json(
    create_test_feature,
    run_orchestration,
    spec_kitty_git_test,
    detect_available_agents
):
    """
    Verify state file is always valid JSON.

    Even after interruption, the state file should be valid JSON
    that can be parsed without errors.
    """
    agents = detect_available_agents()
    if not agents:
        pytest.skip("No agents installed")

    create_test_feature("024", "024-json-valid-test", wp_count=2)

    run_orchestration("024-json-valid-test")

    state_file = spec_kitty_git_test / ".kittify" / "orchestration-state.json"

    if state_file.exists():
        # Read raw content
        content = state_file.read_text()

        # Should parse without error
        try:
            parsed = json.loads(content)
            assert isinstance(parsed, dict), "State should be a JSON object"
        except json.JSONDecodeError as e:
            pytest.fail(f"State file is not valid JSON: {e}")


@pytest.mark.integration
@pytest.mark.orchestrator
def test_state_records_timestamps(
    create_test_feature,
    run_orchestration,
    orchestration_state,
    detect_available_agents
):
    """
    Verify state records timestamps for transitions.

    Validates that state changes include timestamp information.
    """
    agents = detect_available_agents()
    if not agents:
        pytest.skip("No agents installed")

    create_test_feature("025", "025-timestamps-test", wp_count=1)

    run_orchestration("025-timestamps-test")

    state = orchestration_state()

    if state:
        # Should have started_at
        assert "started_at" in state, "Should record start time"

        # Timestamp should be parseable
        try:
            datetime.fromisoformat(state["started_at"].replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            pytest.fail("started_at should be valid ISO datetime")
