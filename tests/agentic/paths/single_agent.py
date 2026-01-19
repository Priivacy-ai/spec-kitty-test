"""Single-agent test path implementation.

This path tests a single agent performing both implementation and review.
The agent implements a work package, then reviews its own work, potentially
going through rework cycles until the work is approved or max iterations
are reached.

Per CLAUDE.md: These are distribution tests - spec-kitty is installed from PyPI,
NOT from local source. No SPEC_KITTY_TEMPLATE_ROOT is ever set.

Supports two execution modes:
1. Container-based (legacy): Uses Docker containers via execute()
2. Host-based (new): Uses direct subprocess via execute_host_based()
"""

from datetime import datetime
from typing import Callable, List, Optional, TYPE_CHECKING

from .base_path import (
    AgentRole,
    AgentSlot,
    EventType,
    PathResult,
    TestPath,
    TestPathConfig,
    TestRun,
    TestStatus,
    WorkflowObservation,
    WorkflowStep,
)

if TYPE_CHECKING:
    from ..fixtures.container_fixtures import AgentContainerFactory
    from ..fixtures.agent_fixtures import AgentConfig, AgentRegistry
    from ..invoker.agent_invoker import AgentInvoker
    from ..invoker.worktree_manager import WorktreeManager
    from ..invoker.invocation_result import InvocationResult
    from ..agents.base import BaseAgentConfig


class SingleAgentPath(TestPath):
    """Test path where one agent performs both implementation and review.

    Workflow:
    1. Agent implements the work package
    2. Same agent reviews its own work
    3. If rejected, agent reworks (up to max_iterations)
    4. Complete when approved or max iterations reached

    This path is useful for testing an agent's ability to self-correct
    and for baseline single-agent performance measurements.

    Slots:
    - implementer: Agent that implements the feature
    - reviewer: Must be same agent as implementer (same_as constraint)
    """

    @classmethod
    def create_default_config(cls) -> TestPathConfig:
        """Create default configuration for single-agent path."""
        return TestPathConfig(
            path_id="single-agent",
            description="Single agent implements and reviews its own work",
            agent_slots=[
                AgentSlot(
                    slot_id="implementer",
                    role=AgentRole.IMPLEMENTATION,
                    required=True,
                ),
                AgentSlot(
                    slot_id="reviewer",
                    role=AgentRole.REVIEW,
                    required=True,
                    same_as="implementer",  # Must be same agent
                ),
            ],
            max_iterations=3,
            timeout_seconds=1800,  # 30 minutes
        )

    @classmethod
    def from_config(cls, config: TestPathConfig) -> "SingleAgentPath":
        """Create SingleAgentPath from config.

        Args:
            config: Path configuration

        Returns:
            Configured SingleAgentPath instance
        """
        return cls(config)

    def build_workflow(self) -> List[WorkflowStep]:
        """Build single-agent workflow steps.

        The workflow is: implement -> review -> (rework -> review)* -> complete

        Returns:
            List of workflow steps
        """
        return [
            WorkflowStep(
                step_id="implement",
                slot_id="implementer",
                action="implement",
                on_success="review",
                on_failure=None,  # Immediate failure terminates test
            ),
            WorkflowStep(
                step_id="review",
                slot_id="reviewer",
                action="review",
                on_success="complete",  # Review passed
                on_failure="rework",  # Review rejected, needs rework
            ),
            WorkflowStep(
                step_id="rework",
                slot_id="implementer",
                action="rework",
                on_success="review",  # Back to review after rework
                on_failure=None,  # Rework failure terminates test
            ),
            WorkflowStep(
                step_id="complete",
                slot_id=None,  # Terminal step, no agent needed
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
        """Execute the single-agent workflow.

        Creates containers, runs agent commands, and captures results
        for each step. Handles the rework loop up to max_iterations.

        Args:
            container_factory: Factory for creating agent containers
            agent_registry: Registry of available agents
            worktree_path: Path to the test worktree
            on_step_complete: Optional callback after each step

        Returns:
            TestRun with complete execution results
        """
        # Get the single agent (same for both slots due to same_as constraint)
        agent_id = self.get_agent_for_slot("implementer")
        if not agent_id:
            raise ValueError("No agent assigned to 'implementer' slot")

        agent_config = agent_registry.get_agent(agent_id)
        if not agent_config:
            raise ValueError(f"Agent '{agent_id}' not found in registry")

        # Create test run
        run = TestRun(
            path_id=self.path_id,
            agent_assignments=self._agent_assignments.copy(),
        )
        run.start()

        # Build workflow
        self._workflow_steps = self.build_workflow()
        self._current_step = 0
        self._iteration = 0

        try:
            while self._current_step < len(self._workflow_steps):
                step = self._workflow_steps[self._current_step]

                # Check for completion
                if step.action == "complete":
                    run.status = TestStatus.PASSED
                    break

                # Check iteration limit
                if self._iteration >= self.config.max_iterations:
                    run.status = TestStatus.FAILED
                    run.failure_reason = (
                        f"Max iterations ({self.config.max_iterations}) exceeded"
                    )
                    break

                # Execute step in container
                observation = await self._execute_step(
                    step=step,
                    agent_config=agent_config,
                    container_factory=container_factory,
                    worktree_path=worktree_path,
                )
                run.add_observation(observation)

                # Callback if provided
                if on_step_complete:
                    on_step_complete(step, observation)

                # Determine next step based on success/failure
                if observation.success:
                    if step.on_success:
                        self._current_step = self._find_step_index(step.on_success)
                    else:
                        self._current_step += 1
                else:
                    if step.on_failure:
                        self._current_step = self._find_step_index(step.on_failure)
                        # Increment iteration count when entering rework
                        if step.action == "review":
                            self._iteration += 1
                            run.iteration_count = self._iteration
                    else:
                        run.status = TestStatus.FAILED
                        run.failure_reason = (
                            f"Step '{step.step_id}' failed with no recovery path"
                        )
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
        """Execute a single workflow step in a container.

        Creates an isolated container, runs the agent command, and
        captures the result as a WorkflowObservation.

        Args:
            step: The workflow step to execute
            agent_config: Configuration for the agent
            container_factory: Factory for creating containers
            worktree_path: Path to mount as /workspace

        Returns:
            WorkflowObservation capturing the step execution
        """
        # Record step start
        start_time = datetime.now()

        # Create container for this step
        container = container_factory.create_container(
            agent_id=agent_config.agent_id,
            worktree_path=worktree_path,
            resource_limits=agent_config.resource_limits,
        )

        try:
            # Build command based on action
            cmd = self._build_command(step.action, agent_config)

            # Execute with timeout
            exit_code, stdout, stderr = container.exec_command(
                cmd,
                timeout=agent_config.timeout_seconds,
            )

            # Determine success based on exit code
            success = exit_code == 0

            # For review steps, also check if review passed
            if step.action == "review" and success:
                # Parse output to determine if review passed or requested changes
                success = self._parse_review_result(stdout)

            return WorkflowObservation(
                step=step.step_id,
                agent_id=agent_config.agent_id,
                event_type=(
                    EventType.AGENT_COMPLETED if success else EventType.AGENT_FAILED
                ),
                timestamp=start_time,
                data={
                    "exit_code": exit_code,
                    "stdout": stdout[:10000] if stdout else "",  # Truncate for storage
                    "stderr": stderr[:10000] if stderr else "",
                    "command": cmd,
                    "duration_seconds": (datetime.now() - start_time).total_seconds(),
                },
                success=success,
            )

        except Exception as e:
            return WorkflowObservation(
                step=step.step_id,
                agent_id=agent_config.agent_id,
                event_type=EventType.AGENT_FAILED,
                timestamp=start_time,
                data={
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                success=False,
            )

        finally:
            # Always stop the container
            try:
                container.stop()
            except Exception:
                pass  # Best effort cleanup

    def _build_command(self, action: str, agent: "AgentConfig") -> str:
        """Build the command for an action.

        Uses agent-specific invocation patterns per research.md E007.

        Args:
            action: The action to perform (implement, review, rework)
            agent: Agent configuration

        Returns:
            Command string to execute
        """
        # Get the prompt for this action
        prompt = self._get_action_prompt(action)

        # Build command based on agent's invocation pattern
        base_cmd = agent.command

        # Add headless flag if available
        if agent.headless_flag:
            base_cmd = f"{base_cmd} {agent.headless_flag}"

        # Build invocation based on pattern
        if agent.invocation_pattern.value == "stdin":
            # Prompt via stdin
            return f"echo '{prompt}' | {base_cmd}"
        elif agent.invocation_pattern.value == "argument":
            # Prompt as argument
            return f"{base_cmd} '{prompt}'"
        elif agent.invocation_pattern.value == "file":
            # Write prompt to file and pass path
            return f"echo '{prompt}' > /tmp/prompt.txt && {base_cmd} /tmp/prompt.txt"
        else:
            # Default to argument style
            return f"{base_cmd} '{prompt}'"

    def _get_action_prompt(self, action: str) -> str:
        """Get the prompt text for an action.

        Args:
            action: The action (implement, review, rework)

        Returns:
            Prompt string for the agent
        """
        prompts = {
            "implement": (
                "Implement the work package according to the prompt file. "
                "Read the WP prompt file in this workspace and implement all requirements. "
                "Commit your changes when complete."
            ),
            "review": (
                "Review the implementation in this workspace. "
                "Check that all requirements from the WP prompt are met. "
                "If the implementation is correct, output 'APPROVED'. "
                "If changes are needed, output 'CHANGES_REQUESTED: ' followed by feedback."
            ),
            "rework": (
                "Address the review feedback and improve the implementation. "
                "Read the previous review comments and make the necessary changes. "
                "Commit your changes when complete."
            ),
        }
        return prompts.get(action, f"Perform action: {action}")

    def _parse_review_result(self, output: str) -> bool:
        """Parse review output to determine if approved.

        Args:
            output: Agent's review output

        Returns:
            True if review passed (approved), False if changes requested
        """
        output_lower = output.lower()

        # Check for explicit approval
        if "approved" in output_lower:
            # Make sure it's not "not approved" or "changes_requested"
            if "changes_requested" not in output_lower and "not approved" not in output_lower:
                return True

        # Check for rejection indicators
        rejection_indicators = [
            "changes_requested",
            "changes requested",
            "needs changes",
            "needs work",
            "rejected",
            "not approved",
            "requires changes",
        ]

        for indicator in rejection_indicators:
            if indicator in output_lower:
                return False

        # Default to approved if no rejection indicators found
        # (agent completed review without explicit rejection)
        return True

    # =========================================================================
    # Host-based execution (AgentInvoker)
    # =========================================================================

    def execute_host_based(
        self,
        invoker: "AgentInvoker",
        worktree_manager: "WorktreeManager",
        wp_content: str,
        agents: List["BaseAgentConfig"],
        timeout: float = 1800.0,
    ) -> "PathResult":
        """Execute single-agent implement→review workflow via host subprocess.

        US1 Acceptance Criteria:
        1. Agent is invoked for implementation
        2. Same agent runs review
        3. If rejected, agent is re-invoked for rework
        4. Test passes/fails based on final outcome

        Args:
            invoker: AgentInvoker for subprocess management
            worktree_manager: WorktreeManager for git isolation
            wp_content: Work package content/requirements
            agents: List of available agent configurations
            timeout: Timeout in seconds for each invocation

        Returns:
            PathResult with execution details
        """
        from ..invoker.invocation_result import InvocationOutcome

        if not agents:
            return PathResult(
                status="skipped",
                reason="No agents available",
                invocations=[],
            )

        agent = agents[0]
        invocations: List["InvocationResult"] = []
        max_iterations = self.config.max_iterations

        # Create worktree for this test
        worktree_info = worktree_manager.create()
        try:
            # Phase 1: Implementation
            impl_prompt = self._build_implement_prompt(wp_content)
            impl_result = invoker.invoke(
                agent_config=agent,
                prompt=impl_prompt,
                worktree=worktree_info.path,
                timeout=timeout,
            )
            invocations.append(impl_result)

            if impl_result.outcome != InvocationOutcome.SUCCESS:
                return PathResult(
                    status="failed",
                    reason=f"Implementation failed: {impl_result.error_message}",
                    invocations=invocations,
                )

            # Phase 2: Review (same agent - SAME_AS constraint)
            for iteration in range(max_iterations):
                review_prompt = self._build_review_prompt(
                    wp_content,
                    impl_result.stdout,
                )

                review_result = invoker.invoke(
                    agent_config=agent,  # Same agent
                    prompt=review_prompt,
                    worktree=worktree_info.path,
                    timeout=timeout,
                )
                invocations.append(review_result)

                if review_result.outcome != InvocationOutcome.SUCCESS:
                    return PathResult(
                        status="failed",
                        reason=f"Review failed: {review_result.error_message}",
                        invocations=invocations,
                    )

                # Check approval
                if review_result.parsed_response and review_result.parsed_response.approval:
                    return PathResult(
                        status="passed",
                        reason="Implementation approved",
                        invocations=invocations,
                    )

                # Also check raw output for approval indicators
                if self._parse_review_result(review_result.stdout):
                    return PathResult(
                        status="passed",
                        reason="Implementation approved (detected from output)",
                        invocations=invocations,
                    )

                # Rejected - rework needed
                if iteration < max_iterations - 1:
                    requested_changes = []
                    if review_result.parsed_response:
                        requested_changes = review_result.parsed_response.requested_changes

                    rework_prompt = self._build_rework_prompt(
                        wp_content,
                        requested_changes,
                    )
                    impl_result = invoker.invoke(
                        agent_config=agent,
                        prompt=rework_prompt,
                        worktree=worktree_info.path,
                        timeout=timeout,
                    )
                    invocations.append(impl_result)

                    if impl_result.outcome != InvocationOutcome.SUCCESS:
                        return PathResult(
                            status="failed",
                            reason=f"Rework failed: {impl_result.error_message}",
                            invocations=invocations,
                        )

            return PathResult(
                status="failed",
                reason="Max iterations reached without approval",
                invocations=invocations,
            )

        finally:
            # Cleanup worktree
            worktree_manager.remove(worktree_info.path)
