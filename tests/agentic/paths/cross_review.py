"""Two-agent cross-review test path implementation.

This path enforces that different agents implement and review, which:
- Catches blind spots that self-review might miss
- Validates that code is understandable by another agent
- Tests the cross-agent communication via spec-kitty's workflow

Per CLAUDE.md: These are distribution tests - spec-kitty is installed from PyPI,
NOT from local source. No SPEC_KITTY_TEMPLATE_ROOT is ever set.
"""

from typing import TYPE_CHECKING, Callable, Dict, List, Optional

from .base_path import (
    AgentRole,
    AgentSlot,
    EventType,
    TestPath,
    TestPathConfig,
    TestRun,
    TestStatus,
    WorkflowObservation,
    WorkflowStep,
)

if TYPE_CHECKING:
    from ..fixtures.agent_fixtures import AgentConfig, AgentRegistry
    from ..fixtures.container_fixtures import AgentContainerFactory


class CrossReviewPath(TestPath):
    """Test path where different agents implement and review.

    Key difference from SingleAgentPath:
    - Implementer and reviewer MUST be different agents
    - Catches blind spots that self-review might miss
    - Rework is done by original implementer

    Workflow:
    1. Agent A implements the WP
    2. Agent B reviews the implementation
    3. If rejected, Agent A reworks
    4. Agent B reviews again (up to max_iterations)
    5. Complete when approved or max iterations reached

    Example usage:
        config = TestPathConfig(
            path_id="cross-review-impl-rev",
            description="Different agents for implementation and review",
            agent_slots=[
                AgentSlot(slot_id="implementer", role=AgentRole.IMPLEMENTATION),
                AgentSlot(
                    slot_id="reviewer",
                    role=AgentRole.REVIEW,
                    different_from="implementer"  # REQUIRED
                ),
            ],
            max_iterations=3
        )
        path = CrossReviewPath.from_config(config)
        path.assign_agents({"implementer": "claude", "reviewer": "copilot"})
        result = await path.execute(factory, registry, worktree)
    """

    @classmethod
    def from_config(cls, config: TestPathConfig) -> "CrossReviewPath":
        """Create CrossReviewPath from config.

        Args:
            config: Path configuration

        Returns:
            CrossReviewPath instance

        Raises:
            ValueError: If reviewer slot doesn't have different_from constraint
        """
        # Validate that different_from constraint exists
        reviewer_slot = None
        for slot in config.agent_slots:
            if slot.slot_id == "reviewer":
                reviewer_slot = slot
                break

        if not reviewer_slot or not reviewer_slot.different_from:
            raise ValueError(
                "CrossReviewPath requires reviewer slot with different_from constraint"
            )

        return cls(config)

    def build_workflow(self) -> List[WorkflowStep]:
        """Build cross-review workflow steps.

        Returns:
            List of WorkflowStep defining:
            1. implement (implementer) -> review on success
            2. review (reviewer) -> complete on success, rework on failure
            3. rework (implementer) -> review on success
            4. complete (terminal)
        """
        return [
            WorkflowStep(
                step_id="implement",
                slot_id="implementer",
                action="implement",
                on_success="review",
                on_failure=None,
            ),
            WorkflowStep(
                step_id="review",
                slot_id="reviewer",  # Different agent via different_from constraint
                action="review",
                on_success="complete",
                on_failure="rework",
            ),
            WorkflowStep(
                step_id="rework",
                slot_id="implementer",  # Back to original implementer
                action="rework",
                on_success="review",
                on_failure=None,
            ),
            WorkflowStep(
                step_id="complete",
                slot_id=None,
                action="complete",
                on_success=None,
                on_failure=None,
            ),
        ]

    async def execute(
        self,
        container_factory: "AgentContainerFactory",
        agent_registry: "AgentRegistry",
        worktree_path: str,
        on_step_complete: Optional[
            Callable[[WorkflowStep, WorkflowObservation], None]
        ] = None,
    ) -> TestRun:
        """Execute the cross-review workflow.

        Key behaviors:
        - Validates implementer != reviewer at start
        - Tracks which agent performs each action
        - Ensures rework goes back to original implementer
        - Records cross-review metadata in observations

        Args:
            container_factory: Factory for creating agent containers
            agent_registry: Registry of available agents
            worktree_path: Path to the test worktree
            on_step_complete: Optional callback after each step completes

        Returns:
            TestRun with complete execution results

        Raises:
            ValueError: If implementer equals reviewer or agents not found
        """
        # Get agents for both slots
        implementer_id = self.get_agent_for_slot("implementer")
        reviewer_id = self.get_agent_for_slot("reviewer")

        # Validate different agents
        if implementer_id == reviewer_id:
            raise ValueError(
                f"CrossReviewPath requires different agents, got {implementer_id} for both"
            )

        if not implementer_id or not reviewer_id:
            raise ValueError("Both implementer and reviewer must be assigned")

        implementer_config = agent_registry.get_agent(implementer_id)
        reviewer_config = agent_registry.get_agent(reviewer_id)

        if not implementer_config or not reviewer_config:
            raise ValueError("Required agent not found in registry")

        # Create test run
        run = TestRun(
            path_id=self.path_id,
            agent_assignments=self._agent_assignments.copy(),
            status=TestStatus.RUNNING,
        )
        run.start()

        # Record agent pairing observation
        run.add_observation(
            WorkflowObservation(
                step="setup",
                agent_id="system",
                event_type=EventType.STEP_STARTED,
                data={
                    "implementer": implementer_id,
                    "reviewer": reviewer_id,
                    "cross_review": True,
                    "path_id": self.path_id,
                },
                success=True,
            )
        )

        # Build and execute workflow
        self._workflow_steps = self.build_workflow()
        self._current_step = 0
        self._iteration = 0

        try:
            while self._current_step < len(self._workflow_steps):
                step = self._workflow_steps[self._current_step]

                if step.action == "complete":
                    run.status = TestStatus.PASSED
                    run.add_observation(
                        WorkflowObservation(
                            step=step.step_id,
                            agent_id="system",
                            event_type=EventType.STEP_COMPLETED,
                            data={"iteration_count": self._iteration},
                            success=True,
                        )
                    )
                    break

                if self._iteration >= self.config.max_iterations:
                    run.status = TestStatus.FAILED
                    run.failure_reason = (
                        f"Max iterations ({self.config.max_iterations}) exceeded. "
                        f"Implementer: {implementer_id}, Reviewer: {reviewer_id}"
                    )
                    break

                # Select agent based on slot
                if step.slot_id == "implementer":
                    agent_config = implementer_config
                else:
                    agent_config = reviewer_config

                # Execute step
                observation = await self._execute_step(
                    step=step,
                    agent_config=agent_config,
                    container_factory=container_factory,
                    worktree_path=worktree_path,
                )
                run.add_observation(observation)

                if on_step_complete:
                    on_step_complete(step, observation)

                # Determine next step
                if observation.success:
                    if step.on_success:
                        self._current_step = self._find_step_index(step.on_success)
                    else:
                        self._current_step += 1
                else:
                    if step.on_failure:
                        self._current_step = self._find_step_index(step.on_failure)
                        self._iteration += 1
                        run.iteration_count = self._iteration
                    else:
                        run.status = TestStatus.FAILED
                        run.failure_reason = f"Step '{step.step_id}' failed with no recovery path"
                        break

        except Exception as e:
            run.status = TestStatus.ERROR
            run.failure_reason = str(e)

        run.complete()
        return run

    async def _execute_step(
        self,
        step: WorkflowStep,
        agent_config: "AgentConfig",
        container_factory: "AgentContainerFactory",
        worktree_path: str,
    ) -> WorkflowObservation:
        """Execute a single workflow step.

        Args:
            step: The workflow step to execute
            agent_config: Configuration for the agent to use
            container_factory: Factory for creating containers
            worktree_path: Path to the worktree

        Returns:
            WorkflowObservation recording what happened
        """
        # Record step start
        start_obs = WorkflowObservation(
            step=step.step_id,
            agent_id=agent_config.agent_id,
            event_type=EventType.STEP_STARTED,
            data={"action": step.action, "role": step.slot_id},
            success=True,
        )

        container = container_factory.create_container(
            agent_id=agent_config.agent_id,
            worktree_path=worktree_path,
            resource_limits=agent_config.resource_limits,
        )

        try:
            cmd = self._build_command(step.action, agent_config)

            exit_code, stdout, stderr = container.exec_command(
                cmd, timeout=agent_config.timeout_seconds
            )

            event_type = (
                EventType.AGENT_COMPLETED if exit_code == 0 else EventType.AGENT_FAILED
            )

            return WorkflowObservation(
                step=step.step_id,
                agent_id=agent_config.agent_id,
                event_type=event_type,
                data={
                    "exit_code": exit_code,
                    "stdout": stdout,
                    "stderr": stderr,
                    "command": cmd,
                    "role": step.slot_id,  # Track which role this agent played
                    "action": step.action,
                },
                success=exit_code == 0,
            )
        finally:
            container.stop()

    def _build_command(self, action: str, agent: "AgentConfig") -> str:
        """Build command for an action.

        Args:
            action: The action to perform
            agent: Agent configuration with command info

        Returns:
            Command string to execute
        """
        prompts = {
            "implement": "Implement the work package per the prompt file",
            "review": "Review the implementation and approve or reject with feedback",
            "rework": "Address the review feedback and fix the issues",
        }
        prompt = prompts.get(action, action)

        # Build command based on agent's invocation pattern
        if agent.headless_flag:
            return f"{agent.command} {agent.headless_flag} '{prompt}'"
        return f"{agent.command} '{prompt}'"

    def get_cross_review_stats(self) -> Dict[str, any]:
        """Get statistics about the cross-review execution.

        Returns:
            Dictionary with cross-review specific metrics
        """
        implementer_id = self.get_agent_for_slot("implementer")
        reviewer_id = self.get_agent_for_slot("reviewer")

        return {
            "implementer": implementer_id,
            "reviewer": reviewer_id,
            "iterations_used": self._iteration,
            "max_iterations": self.config.max_iterations,
            "different_agents_enforced": implementer_id != reviewer_id,
        }
