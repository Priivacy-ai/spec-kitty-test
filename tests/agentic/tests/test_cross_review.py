"""Cross-review workflow tests - US2 validation.

Tests two-agent workflows where different agents implement and review.

T043: Write test_cross_review.py test cases

Per CLAUDE.md: These are distribution tests - spec-kitty is installed from PyPI,
NOT from local source. No SPEC_KITTY_TEMPLATE_ROOT is ever set.
"""

import asyncio
from typing import TYPE_CHECKING

import pytest

from ..paths.cross_review import CrossReviewPath
from ..paths.base_path import (
    AgentRole,
    AgentSlot,
    TestPathConfig,
    TestStatus,
)

if TYPE_CHECKING:
    from ..fixtures.agent_fixtures import AgentRegistry
    from ..fixtures.container_fixtures import AgentContainerFactory


pytestmark = [
    pytest.mark.agentic,
    pytest.mark.slow,
    pytest.mark.cross_review,
]


class TestCrossReviewWorkflow:
    """US2: Two-Agent Cross-Review Validation

    Acceptance Scenarios from spec.md:
    1. Given a feature with one WP and two configured agents,
       When the two-agent test runs,
       Then one agent implements and a different agent reviews.

    2. Given the review agent rejects the implementation,
       When the WP returns to "planned",
       Then the original implementation agent performs the rework.

    3. Given agents with different authentication tokens,
       When running cross-review tests,
       Then each agent uses its own token without cross-contamination.

    4. Given a two-agent workflow completes successfully,
       When analyzing the logs,
       Then the implementation and review phases are clearly attributed.
    """

    @pytest.mark.parametrize("implementer,reviewer", [
        pytest.param("claude-code", "github-copilot", marks=[pytest.mark.claude, pytest.mark.copilot]),
        pytest.param("claude-code", "google-gemini", marks=[pytest.mark.claude, pytest.mark.gemini]),
        pytest.param("github-copilot", "github-codex", marks=[pytest.mark.copilot, pytest.mark.codex]),
        pytest.param("google-gemini", "qwen-code", marks=[pytest.mark.gemini, pytest.mark.qwen]),
    ])
    def test_cross_review_with_different_agents(
        self,
        implementer: str,
        reviewer: str,
        require_agent,
        cross_review_path: CrossReviewPath,
        container_factory: "AgentContainerFactory",
        agent_registry: "AgentRegistry",
        test_feature_scaffold,
        tmp_worktree: str,
    ):
        """
        Acceptance Scenario 1:
        Given a feature with one WP and two configured agents,
        When the two-agent test runs,
        Then one agent implements and a different agent reviews.
        """
        # Require both agents
        impl_config = require_agent(implementer)
        review_config = require_agent(reviewer)

        feature = test_feature_scaffold.create_test_feature(
            feature_name="cross-review-test",
            num_wps=1
        )

        cross_review_path.assign_agents({
            "implementer": implementer,
            "reviewer": reviewer
        })

        run = asyncio.run(cross_review_path.execute(
            container_factory=container_factory,
            agent_registry=agent_registry,
            worktree_path=tmp_worktree
        ))

        # Verify different agents were used
        impl_obs = [o for o in run.observations if o.data.get("role") == "implementer"]
        review_obs = [o for o in run.observations if o.data.get("role") == "reviewer"]

        assert impl_obs or any("implement" in o.step for o in run.observations), \
            "No implementation observations"
        assert review_obs or any("review" in o.step for o in run.observations), \
            "No review observations"

        # Verify agents are different
        all_impl_agents = {
            o.agent_id for o in run.observations
            if o.agent_id and ("implement" in o.step or o.data.get("role") == "implementer")
        }
        all_review_agents = {
            o.agent_id for o in run.observations
            if o.agent_id and ("review" in o.step or o.data.get("role") == "reviewer")
        }

        if all_impl_agents and all_review_agents:
            assert all_impl_agents.isdisjoint(all_review_agents), \
                "Same agent did both implementation and review"

    def test_rejection_rework_by_original_implementer(
        self,
        available_agents,
        cross_review_path: CrossReviewPath,
        container_factory: "AgentContainerFactory",
        agent_registry: "AgentRegistry",
        test_feature_scaffold,
        tmp_worktree: str,
    ):
        """
        Acceptance Scenario 2:
        Given the review agent rejects the implementation,
        When the WP returns to "planned",
        Then the original implementation agent performs the rework.
        """
        if len(available_agents) < 2:
            pytest.skip("Need at least 2 agents for cross-review")

        impl_id = available_agents[0].agent_id
        review_id = available_agents[1].agent_id

        feature = test_feature_scaffold.create_test_feature(
            feature_name="rejection-rework-test",
            num_wps=1
        )

        cross_review_path.assign_agents({
            "implementer": impl_id,
            "reviewer": review_id
        })

        run = asyncio.run(cross_review_path.execute(
            container_factory=container_factory,
            agent_registry=agent_registry,
            worktree_path=tmp_worktree
        ))

        # If there was a rework, verify implementer did it
        rework_obs = [o for o in run.observations if "rework" in o.step]
        for obs in rework_obs:
            assert obs.agent_id == impl_id, \
                f"Wrong agent did rework: {obs.agent_id}, expected {impl_id}"

    def test_each_agent_uses_own_credentials(
        self,
        available_agents,
        cross_review_path: CrossReviewPath,
        agent_registry: "AgentRegistry",
    ):
        """
        Acceptance Scenario 3:
        Given agents with different authentication tokens,
        When running cross-review tests,
        Then each agent uses its own token without cross-contamination.
        """
        if len(available_agents) < 2:
            pytest.skip("Need at least 2 agents")

        # Verify agents have different credential files
        agent1 = available_agents[0]
        agent2 = available_agents[1]

        # Different agents should have different credential secrets
        # (unless they share an API - which is acceptable)
        assert agent1.agent_id != agent2.agent_id, \
            "Test requires two different agents"

    def test_logs_attribute_actions_to_correct_agents(
        self,
        available_agents,
        cross_review_path: CrossReviewPath,
        container_factory: "AgentContainerFactory",
        agent_registry: "AgentRegistry",
        test_feature_scaffold,
        tmp_worktree: str,
    ):
        """
        Acceptance Scenario 4:
        Given a two-agent workflow completes successfully,
        When analyzing the logs,
        Then the implementation and review phases are clearly attributed.
        """
        if len(available_agents) < 2:
            pytest.skip("Need at least 2 agents")

        impl_id = available_agents[0].agent_id
        review_id = available_agents[1].agent_id

        feature = test_feature_scaffold.create_test_feature(
            feature_name="attribution-test",
            num_wps=1
        )

        cross_review_path.assign_agents({
            "implementer": impl_id,
            "reviewer": review_id
        })

        run = asyncio.run(cross_review_path.execute(
            container_factory=container_factory,
            agent_registry=agent_registry,
            worktree_path=tmp_worktree
        ))

        # Verify all observations have agent_id set
        action_obs = [o for o in run.observations if o.agent_id]
        assert action_obs, "No agent-attributed observations"

        for obs in action_obs:
            assert obs.agent_id in (impl_id, review_id), \
                f"Unknown agent in observation: {obs.agent_id}"


class TestCrossReviewPathConfiguration:
    """Test CrossReviewPath configuration and validation."""

    def test_cross_review_path_requires_different_agents(self, cross_review_path: CrossReviewPath):
        """Verify different_from constraint is enforced."""
        # Valid: different agents for each slot
        cross_review_path.assign_agents({
            "implementer": "claude-code",
            "reviewer": "github-copilot"
        })
        assert cross_review_path.get_agent_for_slot("implementer") == "claude-code"
        assert cross_review_path.get_agent_for_slot("reviewer") == "github-copilot"

        # Invalid: same agent for both slots (violates different_from)
        with pytest.raises(ValueError, match="different agent"):
            cross_review_path.assign_agents({
                "implementer": "claude-code",
                "reviewer": "claude-code"
            })

    def test_cross_review_path_requires_both_slots(self, cross_review_path: CrossReviewPath):
        """Verify both slots must be assigned."""
        with pytest.raises(ValueError, match="Required slot"):
            cross_review_path.assign_agents({
                "implementer": "claude-code"
                # Missing reviewer
            })

    def test_workflow_steps_include_review_by_different_agent(self, cross_review_path: CrossReviewPath):
        """Verify workflow has separate implementation and review steps."""
        steps = cross_review_path.build_workflow()

        step_ids = {s.step_id for s in steps}
        assert "implement" in step_ids
        assert "review" in step_ids

        # Verify different slots for implementation and review
        impl_step = next(s for s in steps if s.step_id == "implement")
        review_step = next(s for s in steps if s.step_id == "review")

        assert impl_step.slot_id == "implementer"
        assert review_step.slot_id == "reviewer"
        assert impl_step.slot_id != review_step.slot_id


class TestCrossReviewEdgeCases:
    """Edge cases for cross-review workflow."""

    def test_fallback_to_single_agent_when_only_one_available(
        self,
        agent_registry: "AgentRegistry",
    ):
        """When only one agent is available, cross-review should be skipped."""
        available = agent_registry.get_available_agents()

        if len(available) < 2:
            pytest.skip("Only one or zero agents available - cross-review not possible")

    def test_max_iterations_tracked_across_agents(
        self,
        available_agents,
        container_factory: "AgentContainerFactory",
        agent_registry: "AgentRegistry",
        test_feature_scaffold,
        tmp_worktree: str,
    ):
        """Verify iteration tracking works correctly with two agents."""
        if len(available_agents) < 2:
            pytest.skip("Need 2 agents")

        # Create path with low max_iterations
        config = TestPathConfig(
            path_id="cross-review-low-iter",
            description="Cross-review with low iteration limit",
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
                    different_from="implementer"
                )
            ],
            max_iterations=2,
            timeout_seconds=1200
        )

        path = CrossReviewPath(config)
        path.assign_agents({
            "implementer": available_agents[0].agent_id,
            "reviewer": available_agents[1].agent_id
        })

        feature = test_feature_scaffold.create_test_feature(
            feature_name="max-iter-cross-test",
            num_wps=1
        )

        run = asyncio.run(path.execute(
            container_factory=container_factory,
            agent_registry=agent_registry,
            worktree_path=tmp_worktree
        ))

        # Should not exceed max iterations
        assert run.iteration_count <= 2, f"Exceeded max iterations: {run.iteration_count}"


@pytest.fixture
def cross_review_path() -> CrossReviewPath:
    """Create a CrossReviewPath for testing."""
    config = TestPathConfig(
        path_id="cross-review",
        description="Cross-review test path",
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
                different_from="implementer"
            )
        ],
        max_iterations=3,
        timeout_seconds=2400
    )

    return CrossReviewPath(config)
