"""Fixtures for orchestrator state machine testing.

This module provides fixtures for testing the orchestrator state machine,
including mock agents, test features, and state management.
"""

import pytest
from pathlib import Path
import json
from datetime import datetime
import random
import time


@pytest.fixture
def test_feature_with_wps(tmp_path):
    """Create test feature with 3 work packages.

    Returns:
        Path: Path to feature directory
    """
    feature_dir = tmp_path / "kitty-specs" / "001-test-feature"
    feature_dir.mkdir(parents=True)

    # Create basic feature structure
    (feature_dir / "spec.md").write_text("# Feature Specification\n")
    (feature_dir / "plan.md").write_text("# Implementation Plan\n")
    (feature_dir / "tasks.md").write_text(
        "# Work Packages\n## WP01\n## WP02\n## WP03\n"
    )

    # Create task prompt files
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir()
    for wp in ["WP01", "WP02", "WP03"]:
        (tasks_dir / f"{wp}.md").write_text(
            f"---\nwork_package_id: {wp}\nlane: planned\n---\n# {wp}\n"
        )

    return feature_dir


@pytest.fixture
def orchestration_state_file(tmp_path):
    """Provides path to orchestration state file.

    Returns:
        Path: Path to orchestration-state.json
    """
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir()
    state_file = kittify_dir / "orchestration-state.json"
    return state_file


class MockAgent:
    """Mock agent for orchestrator testing.

    This class simulates AI agent behavior for deterministic testing
    without requiring actual AI agents to be installed.

    Attributes:
        agent_id: Identifier for the agent (e.g., "mock-claude")
        success_probability: Probability of success (0.0-1.0)
        execution_delay: Simulated execution time in seconds
        exit_code: Exit code to return on failure
        invocations: List of all invocation records
    """

    def __init__(
        self,
        agent_id="mock-claude",
        success_probability=1.0,
        execution_delay=0.0,
        exit_code=0,
    ):
        """Initialize mock agent with configuration.

        Args:
            agent_id: Agent identifier
            success_probability: Chance of success (0.0-1.0)
            execution_delay: Delay in seconds (for timeout testing)
            exit_code: Exit code on failure
        """
        self.agent_id = agent_id
        self.success_probability = success_probability
        self.execution_delay = execution_delay
        self.exit_code = exit_code
        self.invocations = []

    def invoke(self, prompt_file: Path, workspace: Path) -> int:
        """Simulate agent invocation.

        Args:
            prompt_file: Path to work package prompt file
            workspace: Path to workspace directory

        Returns:
            int: Exit code (0 for success, non-zero for failure)
        """
        # Log invocation
        self.invocations.append(
            {
                "prompt_file": str(prompt_file),
                "workspace": str(workspace),
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Simulate execution delay
        if self.execution_delay > 0:
            time.sleep(self.execution_delay)

        # Determine success based on probability
        if random.random() < self.success_probability:
            # Success: create some dummy changes
            workspace.mkdir(parents=True, exist_ok=True)
            (workspace / "MOCK_CHANGES.txt").write_text(
                f"Changes by {self.agent_id} at {datetime.now()}"
            )
            return 0
        else:
            return self.exit_code

    def reset(self):
        """Clear invocation history."""
        self.invocations = []


@pytest.fixture
def mock_agent_factory():
    """Factory for creating mock agents with custom config.

    Returns:
        Callable: Function that creates MockAgent instances

    Usage:
        def test_something(mock_agent_factory):
            agent = mock_agent_factory(
                agent_id="test-agent",
                success_probability=0.8
            )
    """

    def create_mock_agent(
        agent_id="mock-claude",
        success_probability=1.0,
        execution_delay=0.0,
        exit_code=0,
    ):
        return MockAgent(agent_id, success_probability, execution_delay, exit_code)

    return create_mock_agent


@pytest.fixture
def mock_successful_agent(mock_agent_factory):
    """Mock agent that always succeeds.

    Returns:
        MockAgent: Agent configured for 100% success rate
    """
    return mock_agent_factory(success_probability=1.0, exit_code=0)


@pytest.fixture
def mock_flaky_agent(mock_agent_factory):
    """Mock agent that fails 50% of the time.

    Returns:
        MockAgent: Agent configured for 50% success rate

    Usage:
        Test retry logic and failure handling
    """
    return mock_agent_factory(success_probability=0.5, exit_code=1)


@pytest.fixture
def mock_failing_agent(mock_agent_factory):
    """Mock agent that always fails.

    Returns:
        MockAgent: Agent configured for 0% success rate

    Usage:
        Test failure scenarios and error handling
    """
    return mock_agent_factory(success_probability=0.0, exit_code=1)
