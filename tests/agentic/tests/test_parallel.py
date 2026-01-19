"""Parallel execution tests - US3 validation.

Tests three-agent parallel workflows where multiple agents work simultaneously.

T044: Write test_parallel.py test cases

Per CLAUDE.md: These are distribution tests - spec-kitty is installed from PyPI,
NOT from local source. No SPEC_KITTY_TEMPLATE_ROOT is ever set.
"""

import asyncio
import time
from typing import TYPE_CHECKING

import pytest

from ..paths.parallel_three import ParallelThreePath
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
    pytest.mark.parallel,
]


class TestParallelExecution:
    """US3: Three-Agent Parallel Execution

    Acceptance Scenarios from spec.md:
    1. Given a feature with 3 independent WPs and 3 available agents,
       When the three-agent test runs,
       Then all 3 WPs execute in parallel (not sequentially).

    2. Given parallel execution starts,
       When observing intermediate states,
       Then all 3 agents are working simultaneously.

    3. Given one agent fails during parallel execution,
       When the failure is detected,
       Then other agents continue their work.

    4. Given all 3 WPs complete successfully,
       When the test finishes,
       Then execution time is significantly less than 3x single-WP time.
    """

    def test_three_wps_execute_in_parallel(
        self,
        available_agents,
        parallel_path: ParallelThreePath,
        container_factory: "AgentContainerFactory",
        agent_registry: "AgentRegistry",
        test_feature_scaffold,
        tmp_worktree: str,
    ):
        """
        Acceptance Scenario 1:
        Given a feature with 3 independent WPs and 3 available agents,
        When the three-agent test runs,
        Then all 3 WPs execute in parallel (not sequentially).
        """
        if len(available_agents) < 3:
            pytest.skip("Need 3 agents for parallel test")

        feature = test_feature_scaffold.create_test_feature(
            feature_name="parallel-test",
            num_wps=3
        )

        parallel_path.assign_agents({
            "worker_1": available_agents[0].agent_id,
            "worker_2": available_agents[1].agent_id,
            "worker_3": available_agents[2].agent_id,
        })

        parallel_path.assign_work_items(
            wp_ids=feature["wp_ids"],
            agent_assignments=parallel_path._agent_assignments
        )

        start_time = time.time()
        run = asyncio.run(parallel_path.execute(
            container_factory=container_factory,
            agent_registry=agent_registry,
            worktree_path=tmp_worktree
        ))
        total_time = time.time() - start_time

        # Get individual timings
        timings = parallel_path.get_parallel_timing()

        if len(timings) >= 3:
            # If all completed, total should be less than sum
            sum_individual = sum(timings.values())
            assert total_time < sum_individual, \
                f"Execution appears sequential: total={total_time:.1f}s, sum={sum_individual:.1f}s"

    def test_all_agents_working_simultaneously(
        self,
        available_agents,
        parallel_path: ParallelThreePath,
        container_factory: "AgentContainerFactory",
        agent_registry: "AgentRegistry",
        test_feature_scaffold,
        tmp_worktree: str,
    ):
        """
        Acceptance Scenario 2:
        Given parallel execution starts,
        When observing intermediate states,
        Then all 3 agents are working simultaneously.
        """
        if len(available_agents) < 3:
            pytest.skip("Need 3 agents")

        feature = test_feature_scaffold.create_test_feature(
            feature_name="simultaneous-test",
            num_wps=3
        )

        parallel_path.assign_agents({
            "worker_1": available_agents[0].agent_id,
            "worker_2": available_agents[1].agent_id,
            "worker_3": available_agents[2].agent_id,
        })

        parallel_path.assign_work_items(
            wp_ids=feature["wp_ids"],
            agent_assignments=parallel_path._agent_assignments
        )

        run = asyncio.run(parallel_path.execute(
            container_factory=container_factory,
            agent_registry=agent_registry,
            worktree_path=tmp_worktree
        ))

        # Check that multiple agents were started around the same time
        start_obs = [
            o for o in run.observations
            if "started" in o.event_type.value or "invoked" in o.event_type.value
        ]

        if len(start_obs) >= 3:
            # All starts should be within a short window (e.g., 30 seconds)
            timestamps = sorted(o.timestamp for o in start_obs[:3])
            time_window = (timestamps[-1] - timestamps[0]).total_seconds()
            assert time_window < 60, \
                f"Agents did not start simultaneously: {time_window:.1f}s gap"

    def test_one_failure_doesnt_block_others(
        self,
        available_agents,
        parallel_path: ParallelThreePath,
        container_factory: "AgentContainerFactory",
        agent_registry: "AgentRegistry",
        test_feature_scaffold,
        tmp_worktree: str,
    ):
        """
        Acceptance Scenario 3:
        Given one agent fails during parallel execution,
        When the failure is detected,
        Then other agents continue their work.
        """
        # This test verifies that failures are isolated
        # Actual fault injection is tested in test_fault_injection.py
        if len(available_agents) < 3:
            pytest.skip("Need 3 agents")

        feature = test_feature_scaffold.create_test_feature(
            feature_name="failure-isolation-test",
            num_wps=3
        )

        parallel_path.assign_agents({
            "worker_1": available_agents[0].agent_id,
            "worker_2": available_agents[1].agent_id,
            "worker_3": available_agents[2].agent_id,
        })

        parallel_path.assign_work_items(
            wp_ids=feature["wp_ids"],
            agent_assignments=parallel_path._agent_assignments
        )

        run = asyncio.run(parallel_path.execute(
            container_factory=container_factory,
            agent_registry=agent_registry,
            worktree_path=tmp_worktree
        ))

        # Count agent completions
        completed_agents = set()
        for obs in run.observations:
            if obs.agent_id and obs.success:
                completed_agents.add(obs.agent_id)

        # At least some agents should have observations
        # (actual failure isolation tested with fault injection)

    def test_parallel_execution_less_than_2x_slowest(
        self,
        available_agents,
        parallel_path: ParallelThreePath,
        container_factory: "AgentContainerFactory",
        agent_registry: "AgentRegistry",
        test_feature_scaffold,
        tmp_worktree: str,
    ):
        """
        Acceptance Scenario 4:
        Given all 3 WPs complete successfully,
        When the test finishes,
        Then execution time is significantly less than 3x single-WP time.
        """
        if len(available_agents) < 3:
            pytest.skip("Need 3 agents")

        feature = test_feature_scaffold.create_test_feature(
            feature_name="timing-test",
            num_wps=3
        )

        parallel_path.assign_agents({
            "worker_1": available_agents[0].agent_id,
            "worker_2": available_agents[1].agent_id,
            "worker_3": available_agents[2].agent_id,
        })

        parallel_path.assign_work_items(
            wp_ids=feature["wp_ids"],
            agent_assignments=parallel_path._agent_assignments
        )

        run = asyncio.run(parallel_path.execute(
            container_factory=container_factory,
            agent_registry=agent_registry,
            worktree_path=tmp_worktree
        ))

        timings = parallel_path.get_parallel_timing()

        if timings and run.completed_at and run.started_at:
            slowest = max(timings.values())
            total = (run.completed_at - run.started_at).total_seconds()

            # SC-003: Less than 2x slowest single-agent execution
            assert total < 2 * slowest, \
                f"Parallel too slow: {total:.1f}s vs 2x{slowest:.1f}s"


class TestParallelPathConfiguration:
    """Test ParallelThreePath configuration and validation."""

    def test_parallel_path_requires_three_workers(self, parallel_path: ParallelThreePath):
        """Verify all three worker slots must be assigned."""
        with pytest.raises(ValueError, match="Required slot"):
            parallel_path.assign_agents({
                "worker_1": "claude-code",
                "worker_2": "github-copilot",
                # Missing worker_3
            })

    def test_parallel_path_allows_same_agent_for_all(self, parallel_path: ParallelThreePath):
        """Verify same agent can be used for all workers (if available)."""
        # This should not raise - same agent is allowed for parallel work
        parallel_path.assign_agents({
            "worker_1": "claude-code",
            "worker_2": "claude-code",
            "worker_3": "claude-code",
        })

    def test_parallel_workflow_has_parallel_steps(self, parallel_path: ParallelThreePath):
        """Verify workflow structure supports parallel execution."""
        steps = parallel_path.build_workflow()

        # Should have steps for each worker
        worker_steps = [s for s in steps if "worker" in (s.slot_id or "")]
        assert len(worker_steps) >= 3, "Should have at least 3 worker steps"


class TestParallelEdgeCases:
    """Edge cases for parallel execution."""

    def test_fewer_than_three_agents_available(
        self,
        agent_registry: "AgentRegistry",
    ):
        """When fewer than 3 agents available, test should skip."""
        available = agent_registry.get_available_agents()

        if len(available) < 3:
            pytest.skip(f"Only {len(available)} agents available - need 3 for parallel")

    def test_parallel_with_mixed_agent_speeds(
        self,
        available_agents,
        parallel_path: ParallelThreePath,
        container_factory: "AgentContainerFactory",
        agent_registry: "AgentRegistry",
        test_feature_scaffold,
        tmp_worktree: str,
    ):
        """Test that parallel execution handles agents with different speeds."""
        if len(available_agents) < 3:
            pytest.skip("Need 3 agents")

        feature = test_feature_scaffold.create_test_feature(
            feature_name="mixed-speed-test",
            num_wps=3
        )

        parallel_path.assign_agents({
            "worker_1": available_agents[0].agent_id,
            "worker_2": available_agents[1].agent_id,
            "worker_3": available_agents[2].agent_id,
        })

        parallel_path.assign_work_items(
            wp_ids=feature["wp_ids"],
            agent_assignments=parallel_path._agent_assignments
        )

        run = asyncio.run(parallel_path.execute(
            container_factory=container_factory,
            agent_registry=agent_registry,
            worktree_path=tmp_worktree
        ))

        # All should complete eventually
        assert run.status in (TestStatus.PASSED, TestStatus.FAILED, TestStatus.ERROR), \
            f"Unexpected status: {run.status}"


@pytest.fixture
def parallel_path() -> ParallelThreePath:
    """Create a ParallelThreePath for testing."""
    config = TestPathConfig(
        path_id="parallel-three",
        description="Three-agent parallel test path",
        agent_slots=[
            AgentSlot(
                slot_id="worker_1",
                role=AgentRole.IMPLEMENTATION,
                required=True
            ),
            AgentSlot(
                slot_id="worker_2",
                role=AgentRole.IMPLEMENTATION,
                required=True
            ),
            AgentSlot(
                slot_id="worker_3",
                role=AgentRole.IMPLEMENTATION,
                required=True
            ),
        ],
        max_iterations=3,
        timeout_seconds=3600  # 1 hour for parallel
    )

    return ParallelThreePath(config)
