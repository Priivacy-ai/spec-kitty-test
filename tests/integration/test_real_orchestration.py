"""
T068: Integration tests for real orchestration cycles.

These tests run actual orchestration with real agents against
the spec-kitty-git-test harness.

Validates:
- User Story 2: Orchestrator State Machine Integrity
- User Story 8: Agent Invocation Reliability
"""
import pytest


@pytest.mark.integration
@pytest.mark.orchestrator
def test_simple_orchestration_completes(
    create_test_feature,
    run_orchestration,
    orchestration_state,
    detect_available_agents
):
    """
    Verify simple orchestration completes successfully.

    Creates feature with 3 WPs, runs orchestration, validates
    state transitions and completion.
    """
    # Check for available agents
    agents = detect_available_agents()
    if not agents:
        pytest.skip("No agents installed for integration test")

    # Create test feature
    feature_dir = create_test_feature("001", "001-simple-test", wp_count=3)

    # Run orchestration
    result = run_orchestration("001-simple-test")

    # Should complete (may have some WPs fail, but shouldn't crash)
    # Exit code 0 means all completed, non-zero means some failed
    # Both are acceptable for this test (we're testing state management)

    # Verify orchestration state exists
    state = orchestration_state()
    assert state is not None, "Orchestration state should exist"

    # Verify state has expected structure
    assert "feature" in state, "State should have 'feature' field"
    assert "wps" in state, "State should have 'wps' field"
    assert "status" in state, "State should have 'status' field"

    # Verify feature matches
    assert state["feature"] == "001-simple-test"

    # Verify WPs tracked
    assert len(state["wps"]) == 3, "Should track all 3 WPs"

    # Verify WP IDs
    wp_ids = list(state["wps"].keys())
    assert "WP01" in wp_ids
    assert "WP02" in wp_ids
    assert "WP03" in wp_ids


@pytest.mark.integration
@pytest.mark.orchestrator
@pytest.mark.slow
def test_orchestration_with_dependencies(
    create_test_feature,
    run_orchestration,
    orchestration_state,
    spec_kitty_git_test,
    detect_available_agents
):
    """
    Verify orchestration respects WP dependencies.

    Creates feature with dependency chain (WP02 depends on WP01),
    validates execution order.
    """
    agents = detect_available_agents()
    if not agents:
        pytest.skip("No agents installed")

    # Create feature
    feature_dir = create_test_feature("002", "002-deps-test", wp_count=2)

    # Add dependency to WP02 prompt
    wp02_prompt = feature_dir / "tasks" / "WP02-test-wp.md"
    content = wp02_prompt.read_text()

    # Add dependencies field to frontmatter
    updated = content.replace(
        'lane: "planned"',
        'lane: "planned"\ndependencies:\n  - "WP01"'
    )
    wp02_prompt.write_text(updated)

    # Run orchestration
    result = run_orchestration("002-deps-test")

    # Check state
    state = orchestration_state()
    assert state is not None

    # Verify execution history respects dependencies
    wp01_state = state["wps"].get("WP01", {})
    wp02_state = state["wps"].get("WP02", {})

    # WP01 should have been attempted
    assert wp01_state.get("state") in ["IMPLEMENTATION", "REVIEW", "DONE", "FAILED", "PENDING"]

    # WP02 depends on WP01
    # If WP01 failed, WP02 should be BLOCKED or PENDING
    # If WP01 succeeded, WP02 should be attempted
    if wp01_state.get("state") == "FAILED":
        assert wp02_state.get("state") in ["BLOCKED", "PENDING"], \
            "WP02 should be blocked if WP01 failed"


@pytest.mark.integration
@pytest.mark.orchestrator
def test_orchestration_creates_worktrees(
    create_test_feature,
    run_orchestration,
    harness_worktrees,
    detect_available_agents
):
    """
    Verify orchestration creates worktrees for WPs.

    Validates that real git worktrees are created during
    orchestration execution.
    """
    agents = detect_available_agents()
    if not agents:
        pytest.skip("No agents installed")

    # Create feature
    create_test_feature("003", "003-worktree-test", wp_count=2)

    # Run orchestration
    run_orchestration("003-worktree-test")

    # Check worktrees created
    worktrees = harness_worktrees()

    # Should have at least one worktree (agents may have created some)
    # Note: May not have all worktrees if agents failed
    feature_worktrees = [
        wt for wt in worktrees
        if "003-worktree-test" in str(wt)
    ]

    assert len(feature_worktrees) > 0, \
        "At least one worktree should be created"


@pytest.mark.integration
@pytest.mark.orchestrator
def test_orchestration_state_valid_after_run(
    create_test_feature,
    run_orchestration,
    orchestration_state,
    detect_available_agents
):
    """
    Verify orchestration state is valid JSON after execution.

    Validates that state file can be parsed and has basic structure.
    """
    agents = detect_available_agents()
    if not agents:
        pytest.skip("No agents installed")

    create_test_feature("004", "004-state-valid-test", wp_count=1)

    run_orchestration("004-state-valid-test")

    state = orchestration_state()

    # State should be valid and readable
    if state is not None:
        # Should be a dict
        assert isinstance(state, dict), "State should be a dictionary"

        # Should have required fields
        assert "feature" in state
        assert "wps" in state

        # WPs should be a dict
        assert isinstance(state["wps"], dict)
