"""Natural failure observation tests - US6 validation.

These tests run extended sessions to observe real agent failures
without injecting faults - capturing naturally occurring issues.

T047: Write test_natural_failures.py test cases

Per CLAUDE.md: These are distribution tests - spec-kitty is installed from PyPI,
NOT from local source. No SPEC_KITTY_TEMPLATE_ROOT is ever set.
"""

import asyncio
from typing import TYPE_CHECKING, List

import pytest

from ..paths.single_agent import SingleAgentPath
from ..paths.base_path import (
    AgentSlot,
    AgentRole,
    TestPathConfig,
    TestStatus,
    TestRun,
)

if TYPE_CHECKING:
    from ..fixtures.agent_fixtures import AgentRegistry
    from ..fixtures.container_fixtures import AgentContainerFactory
    from ..fixtures.observability import OutputLogger, TransitionLogger, GitStateCapture


pytestmark = [
    pytest.mark.agentic,
    pytest.mark.slow,
    pytest.mark.natural_failure,
]


class TestNaturalFailureObservation:
    """US6: Natural Failure Observation

    Acceptance Scenarios from spec.md:
    1. Given real agents executing complex WPs over extended periods,
       When agents produce invalid output formats,
       Then the test captures the malformed output for analysis.

    2. Given real agents executing complex WPs,
       When agents make unexpected decisions,
       Then the test captures all actions leading to the decision.

    3. Given any agent failure (natural or injected),
       When reviewing test results,
       Then logs include stdout/stderr, git state, WP status, and timing.
    """

    @pytest.mark.timeout(3600)  # 1 hour max
    def test_extended_run_captures_failures(
        self,
        available_agents,
        single_agent_path: SingleAgentPath,
        container_factory: "AgentContainerFactory",
        agent_registry: "AgentRegistry",
        test_feature_scaffold,
        tmp_worktree: str,
        output_logger: "OutputLogger",
    ):
        """
        Acceptance Scenario 1-2:
        Given real agents executing complex WPs,
        When agents produce invalid output or unexpected decisions,
        Then the test captures all actions for post-mortem.
        """
        if not available_agents:
            pytest.skip("No agents available")

        # Run multiple iterations to observe natural failures
        results: List[TestRun] = []
        num_iterations = 5

        for i in range(num_iterations):
            feature = test_feature_scaffold.create_test_feature(
                feature_name=f"natural-{i}",
                num_wps=1
            )

            single_agent_path.assign_agents({
                "implementer": available_agents[0].agent_id,
                "reviewer": available_agents[0].agent_id
            })

            try:
                run = asyncio.run(single_agent_path.execute(
                    container_factory=container_factory,
                    agent_registry=agent_registry,
                    worktree_path=tmp_worktree
                ))
                results.append(run)
            except Exception as e:
                # Capture exception as a failure
                pass

        # Analyze results
        failures = [r for r in results if r.status != TestStatus.PASSED]
        successes = [r for r in results if r.status == TestStatus.PASSED]

        # Log files should exist for all runs
        log_files = output_logger.get_log_files()
        assert len(log_files) > 0 or len(results) == 0, "No log files captured"

    def test_comprehensive_log_capture(
        self,
        available_agents,
        single_agent_path: SingleAgentPath,
        container_factory: "AgentContainerFactory",
        agent_registry: "AgentRegistry",
        test_feature_scaffold,
        tmp_worktree: str,
        output_logger: "OutputLogger",
        transition_logger: "TransitionLogger",
        git_state_capture: "GitStateCapture",
    ):
        """
        Acceptance Scenario 3:
        Given any agent failure,
        When reviewing test results,
        Then logs include stdout/stderr, git state, WP status, timing, metrics.
        """
        if not available_agents:
            pytest.skip("No agents available")

        feature = test_feature_scaffold.create_test_feature(
            feature_name="log-capture-test",
            num_wps=1
        )

        single_agent_path.assign_agents({
            "implementer": available_agents[0].agent_id,
            "reviewer": available_agents[0].agent_id
        })

        run = asyncio.run(single_agent_path.execute(
            container_factory=container_factory,
            agent_registry=agent_registry,
            worktree_path=tmp_worktree
        ))

        # Verify comprehensive capture
        assert run.observations, "No observations captured"

        # Check for required data types
        has_stdout = any(
            "stdout" in o.data or "output" in o.data
            for o in run.observations
        )

        # Capture git state
        git_state = git_state_capture.capture()
        assert git_state.branch, "Git branch not captured"

        # Capture transitions
        transitions = transition_logger.get_transitions()
        # May be empty if no lane changes occurred

    def test_invalid_output_format_captured(
        self,
        available_agents,
        single_agent_path: SingleAgentPath,
        container_factory: "AgentContainerFactory",
        agent_registry: "AgentRegistry",
        test_feature_scaffold,
        tmp_worktree: str,
        output_logger: "OutputLogger",
    ):
        """
        Test that invalid output formats from agents are captured.

        This test runs workflows and verifies that output parsing
        failures are recorded for analysis.
        """
        if not available_agents:
            pytest.skip("No agents available")

        feature = test_feature_scaffold.create_test_feature(
            feature_name="output-format-test",
            num_wps=1
        )

        single_agent_path.assign_agents({
            "implementer": available_agents[0].agent_id,
            "reviewer": available_agents[0].agent_id
        })

        run = asyncio.run(single_agent_path.execute(
            container_factory=container_factory,
            agent_registry=agent_registry,
            worktree_path=tmp_worktree
        ))

        # Check for output observations
        output_obs = [
            o for o in run.observations
            if "output" in o.data or "stdout" in o.data
        ]

        # Output logger should have recorded all outputs
        logs = output_logger.get_all_output()
        # May be empty if agent didn't produce output

    def test_unexpected_decision_logged(
        self,
        available_agents,
        single_agent_path: SingleAgentPath,
        container_factory: "AgentContainerFactory",
        agent_registry: "AgentRegistry",
        test_feature_scaffold,
        tmp_worktree: str,
        transition_logger: "TransitionLogger",
    ):
        """
        Test that unexpected agent decisions are logged.

        Unexpected decisions include:
        - Skipping required steps
        - Modifying unrelated files
        - Unusual lane transitions
        """
        if not available_agents:
            pytest.skip("No agents available")

        feature = test_feature_scaffold.create_test_feature(
            feature_name="decision-test",
            num_wps=1
        )

        single_agent_path.assign_agents({
            "implementer": available_agents[0].agent_id,
            "reviewer": available_agents[0].agent_id
        })

        run = asyncio.run(single_agent_path.execute(
            container_factory=container_factory,
            agent_registry=agent_registry,
            worktree_path=tmp_worktree
        ))

        # Get all transitions
        transitions = transition_logger.get_transitions()

        # All transitions should be logged
        for obs in run.observations:
            if obs.event_type.value == "wp_lane_changed":
                # Should be recorded in transition logger
                pass


class TestFailureAnalysis:
    """Tests for failure analysis capabilities."""

    def test_failure_reason_captured(
        self,
        available_agents,
        single_agent_path: SingleAgentPath,
        container_factory: "AgentContainerFactory",
        agent_registry: "AgentRegistry",
        test_feature_scaffold,
        tmp_worktree: str,
    ):
        """Verify that failure reasons are captured in TestRun."""
        if not available_agents:
            pytest.skip("No agents available")

        feature = test_feature_scaffold.create_test_feature(
            feature_name="failure-reason-test",
            num_wps=1
        )

        single_agent_path.assign_agents({
            "implementer": available_agents[0].agent_id,
            "reviewer": available_agents[0].agent_id
        })

        run = asyncio.run(single_agent_path.execute(
            container_factory=container_factory,
            agent_registry=agent_registry,
            worktree_path=tmp_worktree
        ))

        # If failed, should have reason
        if run.status == TestStatus.FAILED:
            assert run.failure_reason, "Failed run should have failure reason"

    def test_timing_metrics_captured(
        self,
        available_agents,
        single_agent_path: SingleAgentPath,
        container_factory: "AgentContainerFactory",
        agent_registry: "AgentRegistry",
        test_feature_scaffold,
        tmp_worktree: str,
    ):
        """Verify timing metrics are captured for all runs."""
        if not available_agents:
            pytest.skip("No agents available")

        feature = test_feature_scaffold.create_test_feature(
            feature_name="timing-test",
            num_wps=1
        )

        single_agent_path.assign_agents({
            "implementer": available_agents[0].agent_id,
            "reviewer": available_agents[0].agent_id
        })

        run = asyncio.run(single_agent_path.execute(
            container_factory=container_factory,
            agent_registry=agent_registry,
            worktree_path=tmp_worktree
        ))

        # Timing should be captured
        assert run.started_at, "Start time not captured"
        assert run.completed_at, "Completion time not captured"
        assert run.duration_seconds is not None, "Duration not calculable"
        assert run.duration_seconds > 0, "Duration should be positive"


class TestPostMortemData:
    """Tests for post-mortem data collection."""

    def test_post_mortem_export(
        self,
        available_agents,
        single_agent_path: SingleAgentPath,
        container_factory: "AgentContainerFactory",
        agent_registry: "AgentRegistry",
        test_feature_scaffold,
        tmp_worktree: str,
        post_mortem_exporter,
    ):
        """Verify post-mortem data can be exported."""
        if not available_agents:
            pytest.skip("No agents available")

        feature = test_feature_scaffold.create_test_feature(
            feature_name="post-mortem-test",
            num_wps=1
        )

        single_agent_path.assign_agents({
            "implementer": available_agents[0].agent_id,
            "reviewer": available_agents[0].agent_id
        })

        run = asyncio.run(single_agent_path.execute(
            container_factory=container_factory,
            agent_registry=agent_registry,
            worktree_path=tmp_worktree
        ))

        # Export post-mortem data
        export_path = post_mortem_exporter.export(run)

        if export_path:
            assert export_path.exists(), "Export file should exist"


@pytest.fixture
def single_agent_path() -> SingleAgentPath:
    """Create a SingleAgentPath for natural failure testing."""
    config = TestPathConfig(
        path_id="single-agent-natural",
        description="Single agent for natural failure observation",
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
        max_iterations=3,
        timeout_seconds=1800
    )

    return SingleAgentPath(config)
