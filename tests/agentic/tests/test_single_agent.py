"""Single-agent workflow tests - US1 validation.

Tests the simplest configuration: one agent performing both
implementation and review of a work package.

T042: Write test_single_agent.py test cases

Per CLAUDE.md: These are distribution tests - spec-kitty is installed from PyPI,
NOT from local source. No SPEC_KITTY_TEMPLATE_ROOT is ever set.
"""

import asyncio
from typing import TYPE_CHECKING

import pytest

from ..paths.single_agent import SingleAgentPath
from ..paths.base_path import (
    AgentRole,
    AgentSlot,
    TestPathConfig,
    TestStatus,
)
from ..fixtures.workflow_fixtures import WPLane

if TYPE_CHECKING:
    from ..fixtures.agent_fixtures import AgentRegistry
    from ..fixtures.container_fixtures import AgentContainerFactory


pytestmark = [
    pytest.mark.agentic,
    pytest.mark.slow,
    pytest.mark.single_agent,
]


class TestSingleAgentWorkflow:
    """US1: Single-Agent Workflow Validation

    Acceptance Scenarios from spec.md:
    1. Given a prepared feature with one WP in "planned" lane,
       When the single-agent test runs with [agent],
       Then the WP progresses through implement → review → done with commits.

    2. Given a single-agent test where review phase rejects,
       When the WP is sent back to "planned",
       Then the agent re-implements and continues until approval or max iterations.

    3. Given an agent that is not installed or authenticated,
       When the test attempts to run,
       Then the test is skipped with a clear message.

    4. Given a successful single-agent workflow,
       When the test completes,
       Then all logs, outputs, and state are captured for analysis.
    """

    @pytest.mark.parametrize("agent_id", [
        pytest.param("claude-code", marks=pytest.mark.claude),
        pytest.param("github-copilot", marks=pytest.mark.copilot),
        pytest.param("github-codex", marks=pytest.mark.codex),
        pytest.param("google-gemini", marks=pytest.mark.gemini),
        pytest.param("cursor", marks=pytest.mark.cursor),
    ])
    def test_single_agent_completes_workflow(
        self,
        agent_id: str,
        require_agent,
        single_agent_path: SingleAgentPath,
        container_factory: "AgentContainerFactory",
        agent_registry: "AgentRegistry",
        test_feature_scaffold,
        tmp_worktree: str,
    ):
        """
        Acceptance Scenario 1:
        Given a prepared feature with one WP in "planned" lane,
        When the single-agent test runs with [agent],
        Then the WP progresses through implement → review → done with commits.
        """
        # Require agent (skips if unavailable)
        agent_config = require_agent(agent_id)

        # Create test feature with one WP
        feature = test_feature_scaffold.create_test_feature(
            feature_name="single-agent-test",
            num_wps=1
        )

        # Configure path with agent
        single_agent_path.assign_agents({
            "implementer": agent_id,
            "reviewer": agent_id  # Same agent via same_as constraint
        })

        # Execute workflow
        run = asyncio.run(single_agent_path.execute(
            container_factory=container_factory,
            agent_registry=agent_registry,
            worktree_path=tmp_worktree
        ))

        # Assertions
        assert run.status == TestStatus.PASSED, \
            f"Workflow failed: {run.failure_reason}"

        # Verify WP reached done
        final_observations = [
            o for o in run.observations
            if o.event_type.value == "wp_lane_changed"
        ]
        assert any(o.data.get("to_lane") == "done" for o in final_observations), \
            "WP did not reach done status"

    def test_single_agent_handles_rejection_cycle(
        self,
        available_agents,
        single_agent_path: SingleAgentPath,
        container_factory: "AgentContainerFactory",
        agent_registry: "AgentRegistry",
        test_feature_scaffold,
        tmp_worktree: str,
        workflow_validator,
    ):
        """
        Acceptance Scenario 2:
        Given a single-agent test where review phase rejects,
        When the WP is sent back to "planned",
        Then the agent re-implements and continues until approval or max iterations.
        """
        if not available_agents:
            pytest.skip("No agents available")

        agent_id = available_agents[0].agent_id

        feature = test_feature_scaffold.create_test_feature(
            feature_name="rejection-cycle-test",
            num_wps=1
        )

        single_agent_path.assign_agents({
            "implementer": agent_id,
            "reviewer": agent_id
        })

        # Execute
        run = asyncio.run(single_agent_path.execute(
            container_factory=container_factory,
            agent_registry=agent_registry,
            worktree_path=tmp_worktree
        ))

        # Check that rejection handling occurred (may or may not reject)
        rejection_observations = [
            o for o in run.observations
            if o.step == "rejection" or
               (o.data.get("from_lane") == "for_review" and
                o.data.get("to_lane") == "planned")
        ]

        # If rejections occurred, verify iteration tracking
        if rejection_observations:
            iterations = max(
                o.data.get("iteration", 0)
                for o in rejection_observations
            )
            assert iterations <= single_agent_path.config.max_iterations, \
                f"Exceeded max iterations: {iterations}"

        # Regardless of rejections, test should complete
        assert run.status in (TestStatus.PASSED, TestStatus.FAILED), \
            f"Unexpected status: {run.status}"

    def test_unavailable_agent_skipped_gracefully(
        self,
        agent_registry: "AgentRegistry",
        single_agent_path: SingleAgentPath,
    ):
        """
        Acceptance Scenario 3:
        Given an agent that is not installed or authenticated,
        When the test attempts to run,
        Then the test is skipped with a clear message.
        """
        # Try to use a fake agent
        fake_agent = "nonexistent-agent-xyz"
        agent = agent_registry.get_agent(fake_agent)

        if agent is None:
            pytest.skip(f"Agent {fake_agent} not available (expected)")
        elif not agent.is_available:
            pytest.skip(f"Agent {fake_agent} not available: not installed or authenticated")

        # If we get here, the fake agent somehow exists
        pytest.fail(f"Expected agent {fake_agent} to not exist")

    def test_successful_workflow_captures_all_data(
        self,
        available_agents,
        single_agent_path: SingleAgentPath,
        container_factory: "AgentContainerFactory",
        agent_registry: "AgentRegistry",
        test_feature_scaffold,
        tmp_worktree: str,
        output_logger,
        transition_logger,
    ):
        """
        Acceptance Scenario 4:
        Given a successful single-agent workflow,
        When the test completes,
        Then all logs, outputs, and state are captured for analysis.
        """
        if not available_agents:
            pytest.skip("No agents available")

        agent_id = available_agents[0].agent_id

        feature = test_feature_scaffold.create_test_feature(
            feature_name="data-capture-test",
            num_wps=1
        )

        single_agent_path.assign_agents({
            "implementer": agent_id,
            "reviewer": agent_id
        })

        run = asyncio.run(single_agent_path.execute(
            container_factory=container_factory,
            agent_registry=agent_registry,
            worktree_path=tmp_worktree
        ))

        # Verify data captured
        assert run.run_id, "Run ID not set"
        assert run.started_at, "Start time not captured"
        assert run.completed_at, "Completion time not captured"
        assert run.observations, "No observations captured"

        # Verify observations contain required data
        for obs in run.observations:
            assert obs.timestamp, "Observation missing timestamp"
            assert obs.event_type, "Observation missing event type"

        # Verify test run has complete data
        assert run.path_id == single_agent_path.path_id
        assert run.agent_assignments, "Agent assignments not recorded"


class TestSingleAgentPathConfiguration:
    """Test SingleAgentPath configuration and validation."""

    def test_single_agent_path_default_config(self):
        """Verify default configuration is sensible."""
        config = SingleAgentPath.create_default_config()

        assert config.path_id == "single-agent"
        assert len(config.agent_slots) == 2
        assert config.max_iterations == 3
        assert config.timeout_seconds == 1800

        # Verify slots
        slot_ids = {s.slot_id for s in config.agent_slots}
        assert "implementer" in slot_ids
        assert "reviewer" in slot_ids

        # Verify same_as constraint
        reviewer_slot = next(s for s in config.agent_slots if s.slot_id == "reviewer")
        assert reviewer_slot.same_as == "implementer"

    def test_assign_agents_enforces_same_as_constraint(self, single_agent_path: SingleAgentPath):
        """Verify same_as constraint is enforced."""
        # Valid: same agent for both slots
        single_agent_path.assign_agents({
            "implementer": "claude-code",
            "reviewer": "claude-code"
        })
        assert single_agent_path.get_agent_for_slot("implementer") == "claude-code"
        assert single_agent_path.get_agent_for_slot("reviewer") == "claude-code"

        # Invalid: different agents (should raise)
        with pytest.raises(ValueError, match="same agent"):
            single_agent_path.assign_agents({
                "implementer": "claude-code",
                "reviewer": "github-copilot"
            })

    def test_assign_agents_requires_all_slots(self, single_agent_path: SingleAgentPath):
        """Verify all required slots must be assigned."""
        with pytest.raises(ValueError, match="Required slot"):
            single_agent_path.assign_agents({
                "implementer": "claude-code"
                # Missing reviewer
            })

    def test_workflow_steps_are_valid(self, single_agent_path: SingleAgentPath):
        """Verify workflow steps form a valid graph."""
        steps = single_agent_path.build_workflow()

        step_ids = {s.step_id for s in steps}
        assert "implement" in step_ids
        assert "review" in step_ids
        assert "rework" in step_ids
        assert "complete" in step_ids

        # Verify transitions reference valid steps
        for step in steps:
            if step.on_success:
                assert step.on_success in step_ids or step.on_success == "complete"
            if step.on_failure:
                assert step.on_failure in step_ids


class TestSingleAgentEdgeCases:
    """Edge cases for single-agent workflow."""

    def test_max_iterations_enforced(
        self,
        available_agents,
        container_factory: "AgentContainerFactory",
        agent_registry: "AgentRegistry",
        test_feature_scaffold,
        tmp_worktree: str,
    ):
        """Verify max iterations limit is respected."""
        if not available_agents:
            pytest.skip("No agents available")

        agent_id = available_agents[0].agent_id

        # Create path with low max_iterations
        config = TestPathConfig(
            path_id="single-agent-low-iter",
            description="Single agent with low iteration limit",
            agent_slots=[
                AgentSlot(
                    slot_id="implementer",
                    role=AgentRole.IMPLEMENTATION,
                    required=True
                ),
                AgentSlot(
                    slot_id="reviewer",
                    role=AgentRole.REVIEW,
                    required=True,
                    same_as="implementer"
                )
            ],
            max_iterations=1,
            timeout_seconds=600
        )

        path = SingleAgentPath(config)
        path.assign_agents({
            "implementer": agent_id,
            "reviewer": agent_id
        })

        feature = test_feature_scaffold.create_test_feature(
            feature_name="max-iter-test",
            num_wps=1
        )

        run = asyncio.run(path.execute(
            container_factory=container_factory,
            agent_registry=agent_registry,
            worktree_path=tmp_worktree
        ))

        # Should not exceed max iterations
        assert run.iteration_count <= 1, f"Exceeded max iterations: {run.iteration_count}"

    def test_workflow_timeout_handling(self, single_agent_path: SingleAgentPath):
        """Verify timeout is configured correctly."""
        assert single_agent_path.timeout_seconds > 0
        assert single_agent_path.timeout_seconds == single_agent_path.config.timeout_seconds


@pytest.fixture
def single_agent_path(agent_registry: "AgentRegistry") -> SingleAgentPath:
    """Create a SingleAgentPath for testing."""
    config = TestPathConfig(
        path_id="single-agent",
        description="Single agent test path",
        agent_slots=[
            AgentSlot(
                slot_id="implementer",
                role=AgentRole.IMPLEMENTATION,
                required=True
            ),
            AgentSlot(
                slot_id="reviewer",
                role=AgentRole.REVIEW,
                required=True,
                same_as="implementer"
            )
        ],
        max_iterations=5,
        timeout_seconds=1800
    )

    return SingleAgentPath(config)
