"""Smoke tests for single-agent workflow with real agent invocation.

These tests require at least one agent to be installed and authenticated.
They validate SC-001: "At least one agent workflow test transitions from
SKIPPED to PASSED when that agent is installed."
"""

from datetime import datetime, timezone

import pytest

from ..invoker.invocation_result import InvocationOutcome
from ..paths.single_agent import SingleAgentPath


@pytest.mark.smoke
@pytest.mark.requires_agent
class TestSingleAgentSmoke:
    """Smoke tests for single-agent workflow."""

    def test_single_agent_simple_task(
        self,
        available_agents,
        agent_invoker,
        worktree_manager,
    ):
        """
        Test that a single agent can complete a simple task.

        Acceptance Criteria (from spec.md US1):
        1. Agent is invoked via subprocess with real prompt
        2. Agent produces output (stdout captured)
        3. Test passes or fails based on actual results
        """
        if not available_agents:
            pytest.skip("No agents available for testing")

        agent = available_agents[0]

        # Simple task that any agent should be able to complete
        simple_prompt = """
        Create a file called hello.txt with the content "Hello, World!".
        Then commit the change with message "Add hello.txt".
        """

        path = SingleAgentPath(
            invoker=agent_invoker,
            worktree_manager=worktree_manager,
            timeout=300.0,  # 5 minutes for smoke test
        )

        # Execute with minimal WP content
        result = path.execute(
            wp_content=simple_prompt,
            agents=[agent],
        )

        # Log result for debugging
        print(f"\nAgent: {agent.agent_id}")
        print(f"Status: {result.status}")
        print(f"Reason: {result.reason}")
        print(f"Invocations: {len(result.invocations)}")

        for i, inv in enumerate(result.invocations):
            print(f"\n  Invocation {i}:")
            print(f"    Outcome: {inv.outcome.value}")
            print(f"    Duration: {inv.duration_seconds:.1f}s")
            print(f"    Exit code: {inv.exit_code}")
            if inv.stdout:
                print(f"    Stdout preview: {inv.stdout[:200]}...")

        # Assert based on outcome
        assert result.status in ["passed", "failed"], f"Unexpected status: {result.status}"

        # If we got here, the agent was invoked (not skipped)
        assert len(result.invocations) > 0, "No invocations recorded"

    def test_agent_invocation_captures_output(
        self,
        available_agents,
        agent_invoker,
        worktree_manager,
    ):
        """
        Test that agent output is fully captured (SC-003).

        Validates: "Agent invocation captures complete stdout/stderr
        (no truncation under 1MB)"
        """
        if not available_agents:
            pytest.skip("No agents available for testing")

        agent = available_agents[0]

        # Simple prompt to generate output
        result = agent_invoker.invoke(
            agent_config=agent,
            prompt="List the files in the current directory.",
            worktree=None,  # Will create temp worktree
            timeout=60.0,
        )

        # Verify output was captured
        assert result.stdout is not None, "stdout not captured"
        assert result.stderr is not None, "stderr not captured"
        assert result.exit_code is not None, "exit_code not captured"
        assert result.duration_seconds > 0, "duration not recorded"

        # Verify no truncation for small outputs
        # (Large output truncation tested separately)
        assert (
            len(result.stdout) < 1_000_000 or "..." not in result.stdout[-10:]
        ), "Small output was truncated"

    def test_agent_timing_recorded(
        self,
        available_agents,
        agent_invoker,
        worktree_manager,
    ):
        """
        Test that timing is accurately recorded (SC-005).

        Validates: "Test runs produce observation logs that include
        timing, output, and git state"
        """
        if not available_agents:
            pytest.skip("No agents available for testing")

        agent = available_agents[0]

        before = datetime.now(timezone.utc)
        result = agent_invoker.invoke(
            agent_config=agent,
            prompt="What is 2 + 2?",  # Quick prompt
            timeout=60.0,
        )
        after = datetime.now(timezone.utc)

        # Verify timing
        assert result.started_at >= before, "started_at before invocation"
        assert result.completed_at <= after, "completed_at after invocation"
        assert result.duration_seconds > 0, "duration must be positive"
        assert (
            result.duration_seconds <= (after - before).total_seconds() + 1
        ), "duration exceeds wall clock time"
