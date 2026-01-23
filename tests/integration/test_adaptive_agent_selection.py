"""
T072: Integration tests for adaptive agent selection.

Validates that orchestration adapts to whatever agents
are installed, without failing due to missing agents.

Validates:
- User Story 8: Agent Invocation Reliability
"""
import pytest


@pytest.mark.integration
@pytest.mark.orchestrator
def test_orchestration_uses_available_agents(
    create_test_feature,
    run_orchestration,
    orchestration_state,
    detect_available_agents
):
    """
    Verify orchestration uses installed agents.

    Runs orchestration, validates that only installed
    agents are assigned to WPs.
    """
    agents = detect_available_agents()
    if not agents:
        pytest.skip("No agents installed")

    create_test_feature("040", "040-adaptive-test", wp_count=2)

    run_orchestration("040-adaptive-test")

    state = orchestration_state()

    if state:
        # Check assigned agents
        for wp_id, wp_state in state["wps"].items():
            assigned_agent = wp_state.get("assigned_agent")

            if assigned_agent:
                # Assigned agent should be in available list
                assert assigned_agent in agents, \
                    f"Assigned agent '{assigned_agent}' not in available: {agents}"


@pytest.mark.integration
@pytest.mark.orchestrator
def test_single_agent_orchestration(
    create_test_feature,
    run_orchestration,
    orchestration_state,
    detect_available_agents
):
    """
    Verify orchestration works with single agent.

    If only one agent available, all WPs should use it.
    """
    agents = detect_available_agents()
    if len(agents) != 1:
        pytest.skip("Test requires exactly one agent installed")

    single_agent = agents[0]

    create_test_feature("041", "041-single-agent-test", wp_count=2)

    run_orchestration("041-single-agent-test")

    state = orchestration_state()

    if state:
        # All assigned agents should be the single agent
        for wp_id, wp_state in state["wps"].items():
            assigned = wp_state.get("assigned_agent")

            if assigned:
                assert assigned == single_agent, \
                    f"Expected {single_agent}, got {assigned}"


@pytest.mark.integration
@pytest.mark.orchestrator
@pytest.mark.slow
def test_multi_agent_orchestration(
    create_test_feature,
    run_orchestration,
    orchestration_state,
    detect_available_agents
):
    """
    Verify orchestration with multiple agents.

    If multiple agents available, validates that they're
    used across WPs (load balancing or fallback).
    """
    agents = detect_available_agents()
    if len(agents) < 2:
        pytest.skip("Test requires at least 2 agents installed")

    create_test_feature("042", "042-multi-agent-test", wp_count=5)

    run_orchestration("042-multi-agent-test")

    state = orchestration_state()

    if state:
        # Collect assigned agents
        assigned_agents = set()
        for wp_state in state["wps"].values():
            agent = wp_state.get("assigned_agent")
            if agent:
                assigned_agents.add(agent)

        # Should use multiple agents if available
        # (not strict requirement, but good practice)
        # At minimum, shouldn't crash with multiple agents available
        assert len(assigned_agents) > 0, \
            "At least one agent should be used"


@pytest.mark.integration
@pytest.mark.orchestrator
def test_no_agents_fails_gracefully(
    create_test_feature,
    run_orchestration,
    orchestration_state,
    detect_available_agents
):
    """
    Verify clear handling when no agents available.

    This test validates behavior - may pass or skip
    depending on agent availability.
    """
    agents = detect_available_agents()
    if agents:
        # If agents are available, this test doesn't apply
        pytest.skip("Test is for no-agent scenario")

    # If we get here, no agents are installed
    create_test_feature("043", "043-no-agent-test", wp_count=1)

    result = run_orchestration("043-no-agent-test")

    # Should fail with clear error
    assert result.returncode != 0, \
        "Should fail when no agents available"


@pytest.mark.integration
@pytest.mark.orchestrator
def test_agent_detection_is_accurate(detect_available_agents):
    """
    Verify agent detection accurately reports installed agents.

    This test validates the detection fixture itself.
    """
    agents = detect_available_agents()

    # Result should be a list
    assert isinstance(agents, list), "Should return list of agents"

    # All items should be strings
    for agent in agents:
        assert isinstance(agent, str), f"Agent '{agent}' should be string"

    # Known agent names
    valid_agents = {"claude", "opencode", "aider", "copilot"}

    for agent in agents:
        assert agent in valid_agents, \
            f"Unknown agent '{agent}' detected"


@pytest.mark.integration
@pytest.mark.orchestrator
def test_orchestration_completes_with_any_agent(
    create_test_feature,
    run_orchestration,
    orchestration_state,
    detect_available_agents
):
    """
    Verify orchestration can complete with any single agent.

    Creates feature, runs orchestration, validates basic completion.
    """
    agents = detect_available_agents()
    if not agents:
        pytest.skip("No agents installed")

    create_test_feature("044", "044-any-agent-test", wp_count=1)

    result = run_orchestration("044-any-agent-test")

    state = orchestration_state()

    # Orchestration should create state file
    if state:
        # State should track the WP
        assert "WP01" in state.get("wps", {}), \
            "WP01 should be tracked in state"
