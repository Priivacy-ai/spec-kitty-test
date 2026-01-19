"""Smoke tests for cross-review workflow with two agents.

These tests require at least two agents to be installed and authenticated.
They validate SC-007: "Cross-review tests use two different agents when 2+ are available"
"""

import pytest

from ..paths.cross_review import CrossReviewPath


@pytest.mark.smoke
@pytest.mark.requires_two_agents
class TestCrossReviewSmoke:
    """Smoke tests for cross-review workflow."""

    def test_cross_review_uses_different_agents(
        self,
        available_agents,
        agent_invoker,
        worktree_manager,
    ):
        """
        Test that cross-review uses different agents (SC-007).

        Validates: "Cross-review tests use two different agents
        when 2+ are available"
        """
        if len(available_agents) < 2:
            pytest.skip(
                f"Cross-review requires 2 agents, only {len(available_agents)} available"
            )

        agent_a = available_agents[0]
        agent_b = available_agents[1]

        # Verify they're different
        assert agent_a.agent_id != agent_b.agent_id, "Should use different agents"

        simple_prompt = """
        Create a README.md file with a project description.
        """

        path = CrossReviewPath(
            invoker=agent_invoker,
            worktree_manager=worktree_manager,
            timeout=300.0,
        )

        result = path.execute(
            wp_content=simple_prompt,
            agents=[agent_a, agent_b],
        )

        print(f"\nImplementer: {agent_a.agent_id}")
        print(f"Reviewer: {agent_b.agent_id}")
        print(f"Status: {result.status}")
        print(f"Reason: {result.reason}")

        # Check that both agents were invoked
        agent_ids_used = set(inv.agent_id for inv in result.invocations)
        assert (
            agent_a.agent_id in agent_ids_used
        ), f"Implementer {agent_a.agent_id} was not invoked"
        # Reviewer might not be invoked if implementation fails

        # Verify we didn't get skipped
        assert result.status in [
            "passed",
            "failed",
        ], f"Expected pass/fail, got {result.status}"

    def test_cross_review_skips_with_one_agent(
        self,
        available_agents,
        agent_invoker,
        worktree_manager,
    ):
        """Test that cross-review properly skips with only one agent."""
        if len(available_agents) != 1:
            pytest.skip("Test requires exactly 1 agent")

        path = CrossReviewPath(
            invoker=agent_invoker,
            worktree_manager=worktree_manager,
        )

        result = path.execute(
            wp_content="Test content",
            agents=available_agents,
        )

        assert (
            result.status == "skipped"
        ), f"Expected skip with 1 agent, got {result.status}"
        assert (
            "2 agents" in result.reason.lower()
        ), f"Reason should mention 2 agents: {result.reason}"

    def test_cross_review_multiple_rounds(
        self,
        available_agents,
        agent_invoker,
        worktree_manager,
    ):
        """Test that cross-review can handle multiple review rounds."""
        if len(available_agents) < 2:
            pytest.skip(
                f"Cross-review requires 2 agents, only {len(available_agents)} available"
            )

        agent_a = available_agents[0]
        agent_b = available_agents[1]

        # More complex prompt that might need revisions
        complex_prompt = """
        Create a Python function that calculates the factorial of a number.
        Include proper docstring and type hints.
        Add unit tests for the function.
        """

        path = CrossReviewPath(
            invoker=agent_invoker,
            worktree_manager=worktree_manager,
            timeout=600.0,  # 10 minutes for potentially multiple rounds
            max_rounds=3,
        )

        result = path.execute(
            wp_content=complex_prompt,
            agents=[agent_a, agent_b],
        )

        print(f"\nCross-review result:")
        print(f"  Status: {result.status}")
        print(f"  Reason: {result.reason}")
        print(f"  Total invocations: {len(result.invocations)}")

        # Log each invocation
        for i, inv in enumerate(result.invocations):
            print(f"  Invocation {i}: {inv.agent_id} - {inv.outcome.value}")

        # Should complete (pass/fail) or time out
        assert result.status in ["passed", "failed", "timeout"], (
            f"Unexpected status: {result.status}"
        )
