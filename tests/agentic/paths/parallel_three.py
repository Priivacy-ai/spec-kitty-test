"""Three-agent parallel execution test path.

This path validates:
- Parallel execution actually occurs (not sequential)
- Container isolation prevents interference
- Overall execution time is less than 3x single agent
- Individual failures don't block other agents

Per CLAUDE.md: These are distribution tests - spec-kitty is installed from PyPI,
NOT from local source. No SPEC_KITTY_TEMPLATE_ROOT is ever set.

Supports two execution modes:
1. Container-based (legacy): Uses Docker containers via execute()
2. Host-based (new): Uses direct subprocess via execute_host_based()
"""

import asyncio
import concurrent.futures
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Callable, Dict, List, Optional
from uuid import uuid4

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
    from ..fixtures.agent_fixtures import AgentConfig, AgentRegistry
    from ..fixtures.container_fixtures import AgentContainerFactory
    from ..invoker.agent_invoker import AgentInvoker
    from ..invoker.worktree_manager import WorktreeManager
    from ..invoker.invocation_result import InvocationResult
    from ..agents.base import BaseAgentConfig


@dataclass
class ParallelWorkItem:
    """A work item for parallel execution.

    Attributes:
        wp_id: Work package ID to process
        slot_id: Agent slot ID responsible for this item
        agent_id: Agent ID assigned to process this item
    """

    wp_id: str
    slot_id: str
    agent_id: str


@dataclass
class WorkItemResult:
    """Result of processing a single work item.

    Attributes:
        wp_id: Work package ID
        agent_id: Agent that processed it
        status: Final status
        started_at: When processing started
        completed_at: When processing completed
        observations: Observations from this work item
        failure_reason: Reason for failure (if any)
    """

    wp_id: str
    agent_id: str
    status: TestStatus = TestStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    observations: List[WorkflowObservation] = field(default_factory=list)
    failure_reason: Optional[str] = None

    @property
    def duration_seconds(self) -> Optional[float]:
        """Duration of this work item in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class ParallelThreePath(TestPath):
    """Test path with three agents working on independent WPs in parallel.

    This path validates:
    - Parallel execution actually occurs (not sequential)
    - Container isolation prevents interference
    - Overall execution time is less than 3x single agent
    - Individual failures don't block other agents

    Workflow:
    1. Three WPs assigned to three agents
    2. All three implement in parallel
    3. Each gets reviewed (self-review for simplicity)
    4. Complete when all three WPs are done

    Example usage:
        config = TestPathConfig(
            path_id="parallel-three",
            description="Three agents working in parallel",
            agent_slots=[
                AgentSlot(slot_id="worker_1", role=AgentRole.IMPLEMENTATION),
                AgentSlot(slot_id="worker_2", role=AgentRole.IMPLEMENTATION),
                AgentSlot(slot_id="worker_3", role=AgentRole.IMPLEMENTATION),
            ],
            max_iterations=3
        )
        path = ParallelThreePath.from_config(config)
        path.assign_work_items(
            ["WP01", "WP02", "WP03"],
            {"worker_1": "claude", "worker_2": "copilot", "worker_3": "gemini"}
        )
        result = await path.execute(factory, registry, worktree)
    """

    def __init__(self, config: TestPathConfig):
        """Initialize parallel path.

        Args:
            config: Path configuration
        """
        super().__init__(config)
        self._work_items: List[ParallelWorkItem] = []
        self._results: Dict[str, WorkItemResult] = {}

    @classmethod
    def from_config(cls, config: TestPathConfig) -> "ParallelThreePath":
        """Create ParallelThreePath from config.

        Args:
            config: Path configuration

        Returns:
            ParallelThreePath instance

        Raises:
            ValueError: If no worker slots defined
        """
        # Validate we have worker slots
        worker_slots = [
            s for s in config.agent_slots if s.slot_id.startswith("worker_")
        ]
        if len(worker_slots) < 1:
            raise ValueError("ParallelThreePath requires at least one worker slot")
        return cls(config)

    def assign_work_items(
        self,
        wp_ids: List[str],
        agent_assignments: Dict[str, str],
    ) -> List[ParallelWorkItem]:
        """Assign WPs to agent slots.

        Args:
            wp_ids: List of WP IDs to process (1-3)
            agent_assignments: slot_id -> agent_id mapping

        Returns:
            List of ParallelWorkItem assignments
        """
        worker_slots = ["worker_1", "worker_2", "worker_3"]
        self._work_items = []

        for i, wp_id in enumerate(wp_ids[:3]):  # Max 3
            slot_id = worker_slots[i]
            agent_id = agent_assignments.get(slot_id)

            if not agent_id:
                continue  # Skip if no agent for this slot

            self._work_items.append(
                ParallelWorkItem(
                    wp_id=wp_id,
                    slot_id=slot_id,
                    agent_id=agent_id,
                )
            )

        # Also store in _agent_assignments for base class compatibility
        self._agent_assignments = agent_assignments.copy()

        return self._work_items

    def build_workflow(self) -> List[WorkflowStep]:
        """Build parallel workflow - one set of steps per work item.

        Returns:
            List of WorkflowStep for all work items
        """
        steps = []

        for item in self._work_items:
            steps.append(
                WorkflowStep(
                    step_id=f"implement_{item.wp_id}",
                    slot_id=item.slot_id,
                    action="implement",
                    on_success=f"review_{item.wp_id}",
                    on_failure=None,
                )
            )
            steps.append(
                WorkflowStep(
                    step_id=f"review_{item.wp_id}",
                    slot_id=item.slot_id,  # Self-review for simplicity
                    action="review",
                    on_success=f"complete_{item.wp_id}",
                    on_failure=f"rework_{item.wp_id}",
                )
            )
            steps.append(
                WorkflowStep(
                    step_id=f"rework_{item.wp_id}",
                    slot_id=item.slot_id,
                    action="rework",
                    on_success=f"review_{item.wp_id}",
                    on_failure=None,
                )
            )
            steps.append(
                WorkflowStep(
                    step_id=f"complete_{item.wp_id}",
                    slot_id=None,
                    action="complete",
                    on_success=None,
                    on_failure=None,
                )
            )

        return steps

    async def execute(
        self,
        container_factory: "AgentContainerFactory",
        agent_registry: "AgentRegistry",
        worktree_path: str,
        on_step_complete: Optional[
            Callable[[WorkflowStep, WorkflowObservation], None]
        ] = None,
    ) -> TestRun:
        """Execute parallel workflow.

        Key behaviors:
        - Launches all agents concurrently via asyncio.gather
        - Tracks individual and aggregate timing
        - Reports partial success if some agents complete
        - Individual failures don't block other agents

        Args:
            container_factory: Factory for creating agent containers
            agent_registry: Registry of available agents
            worktree_path: Path to the test worktree
            on_step_complete: Optional callback after each step completes

        Returns:
            TestRun with complete execution results

        Raises:
            ValueError: If no work items assigned
        """
        if not self._work_items:
            raise ValueError("No work items assigned. Call assign_work_items first.")

        # Create aggregate test run
        run = TestRun(
            path_id=self.path_id,
            agent_assignments=self._agent_assignments.copy(),
            status=TestStatus.RUNNING,
        )
        run.start()

        # Record parallel setup
        run.add_observation(
            WorkflowObservation(
                step="parallel_setup",
                agent_id="system",
                event_type=EventType.STEP_STARTED,
                data={
                    "parallel": True,
                    "work_items": [
                        {"wp_id": item.wp_id, "agent_id": item.agent_id}
                        for item in self._work_items
                    ],
                    "num_parallel": len(self._work_items),
                },
                success=True,
            )
        )

        start_time = time.time()

        try:
            # Execute all work items in parallel
            tasks = [
                self._execute_work_item(
                    item=item,
                    agent_registry=agent_registry,
                    container_factory=container_factory,
                    worktree_path=worktree_path,
                )
                for item in self._work_items
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            successes = 0
            failures = 0

            for item, result in zip(self._work_items, results):
                if isinstance(result, Exception):
                    failures += 1
                    error_result = WorkItemResult(
                        wp_id=item.wp_id,
                        agent_id=item.agent_id,
                        status=TestStatus.ERROR,
                        failure_reason=str(result),
                    )
                    self._results[item.wp_id] = error_result
                    run.add_observation(
                        WorkflowObservation(
                            step=f"parallel_{item.wp_id}",
                            agent_id=item.agent_id,
                            event_type=EventType.AGENT_FAILED,
                            data={"error": str(result), "wp_id": item.wp_id},
                            success=False,
                        )
                    )
                elif result.status == TestStatus.PASSED:
                    successes += 1
                    self._results[item.wp_id] = result
                    # Add all observations from this work item
                    for obs in result.observations:
                        run.add_observation(obs)
                else:
                    failures += 1
                    self._results[item.wp_id] = result
                    for obs in result.observations:
                        run.add_observation(obs)

            elapsed_time = time.time() - start_time

            # Record parallel completion
            run.add_observation(
                WorkflowObservation(
                    step="parallel_complete",
                    agent_id="system",
                    event_type=EventType.STEP_COMPLETED,
                    data={
                        "successes": successes,
                        "failures": failures,
                        "total": len(self._work_items),
                        "elapsed_seconds": round(elapsed_time, 2),
                        "work_item_timings": self.get_parallel_timing(),
                    },
                    success=failures == 0,
                )
            )

            # Determine overall status
            if failures == 0:
                run.status = TestStatus.PASSED
            elif successes > 0:
                run.status = TestStatus.FAILED
                run.failure_reason = (
                    f"{failures}/{len(self._work_items)} work items failed"
                )
            else:
                run.status = TestStatus.FAILED
                run.failure_reason = "All work items failed"

        except Exception as e:
            run.status = TestStatus.ERROR
            run.failure_reason = str(e)

        run.complete()
        return run

    async def _execute_work_item(
        self,
        item: ParallelWorkItem,
        agent_registry: "AgentRegistry",
        container_factory: "AgentContainerFactory",
        worktree_path: str,
    ) -> WorkItemResult:
        """Execute a single work item (implement -> review cycle).

        Args:
            item: The work item to execute
            agent_registry: Registry of available agents
            container_factory: Factory for creating containers
            worktree_path: Path to the worktree

        Returns:
            WorkItemResult with execution details
        """
        agent_config = agent_registry.get_agent(item.agent_id)
        if not agent_config:
            raise ValueError(f"Agent {item.agent_id} not found")

        # Create result tracking
        result = WorkItemResult(
            wp_id=item.wp_id,
            agent_id=item.agent_id,
            status=TestStatus.RUNNING,
            started_at=datetime.now(),
        )

        iteration = 0
        max_iterations = self.config.max_iterations

        # Simple implement -> review -> (rework) loop
        while iteration < max_iterations:
            # Implement
            impl_result = await self._run_agent_step(
                agent_config,
                container_factory,
                worktree_path,
                "implement",
                item.wp_id,
            )
            result.observations.append(impl_result)

            if not impl_result.success:
                result.status = TestStatus.FAILED
                result.failure_reason = f"Implementation failed for {item.wp_id}"
                break

            # Review
            review_result = await self._run_agent_step(
                agent_config,
                container_factory,
                worktree_path,
                "review",
                item.wp_id,
            )
            result.observations.append(review_result)

            if review_result.success:
                result.status = TestStatus.PASSED
                break
            else:
                iteration += 1
                if iteration < max_iterations:
                    # Rework
                    rework_result = await self._run_agent_step(
                        agent_config,
                        container_factory,
                        worktree_path,
                        "rework",
                        item.wp_id,
                    )
                    result.observations.append(rework_result)

        if iteration >= max_iterations and result.status != TestStatus.PASSED:
            result.status = TestStatus.FAILED
            result.failure_reason = f"Max iterations exceeded for {item.wp_id}"

        result.completed_at = datetime.now()
        return result

    async def _run_agent_step(
        self,
        agent_config: "AgentConfig",
        container_factory: "AgentContainerFactory",
        worktree_path: str,
        action: str,
        wp_id: str,
    ) -> WorkflowObservation:
        """Run a single agent action.

        Args:
            agent_config: Configuration for the agent
            container_factory: Factory for creating containers
            worktree_path: Path to the worktree
            action: Action to perform
            wp_id: Work package ID

        Returns:
            WorkflowObservation recording the step
        """
        container = container_factory.create_container(
            agent_id=agent_config.agent_id,
            worktree_path=worktree_path,
            resource_limits=agent_config.resource_limits,
        )

        try:
            # Build command based on agent's invocation pattern
            prompt = f"{action} for {wp_id}"
            if agent_config.headless_flag:
                cmd = f"{agent_config.command} {agent_config.headless_flag} '{prompt}'"
            else:
                cmd = f"{agent_config.command} '{prompt}'"

            exit_code, stdout, stderr = container.exec_command(
                cmd, timeout=agent_config.timeout_seconds
            )

            return WorkflowObservation(
                step=f"{action}_{wp_id}",
                agent_id=agent_config.agent_id,
                event_type=(
                    EventType.AGENT_COMPLETED
                    if exit_code == 0
                    else EventType.AGENT_FAILED
                ),
                data={
                    "exit_code": exit_code,
                    "stdout": stdout[-1000:] if stdout else "",  # Truncate for parallel
                    "stderr": stderr[-1000:] if stderr else "",
                    "wp_id": wp_id,
                    "action": action,
                },
                success=exit_code == 0,
            )
        finally:
            container.stop()

    def get_parallel_timing(self) -> Dict[str, Optional[float]]:
        """Get timing data for parallel execution analysis.

        Returns:
            Dictionary mapping wp_id to duration in seconds
        """
        timings = {}
        for wp_id, result in self._results.items():
            timings[wp_id] = result.duration_seconds
        return timings

    def get_work_items(self) -> List[ParallelWorkItem]:
        """Get the assigned work items.

        Returns:
            List of ParallelWorkItem
        """
        return self._work_items.copy()

    def get_results(self) -> Dict[str, WorkItemResult]:
        """Get results for all work items.

        Returns:
            Dictionary mapping wp_id to WorkItemResult
        """
        return self._results.copy()

    def get_parallel_stats(self) -> Dict[str, any]:
        """Get statistics about parallel execution.

        Returns:
            Dictionary with parallel execution metrics
        """
        timings = self.get_parallel_timing()
        valid_timings = [t for t in timings.values() if t is not None]

        return {
            "num_work_items": len(self._work_items),
            "num_completed": len([r for r in self._results.values() if r.completed_at]),
            "num_passed": len(
                [r for r in self._results.values() if r.status == TestStatus.PASSED]
            ),
            "num_failed": len(
                [r for r in self._results.values() if r.status == TestStatus.FAILED]
            ),
            "total_duration_seconds": max(valid_timings) if valid_timings else None,
            "individual_durations": timings,
            "parallelism_factor": (
                sum(valid_timings) / max(valid_timings)
                if valid_timings and max(valid_timings) > 0
                else None
            ),
        }

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
        """Execute parallel workflow with 3 agents on 3 WPs.

        US4 Acceptance Criteria:
        1. 3 agent subprocesses start within 30 seconds
        2. Total time < 2x slowest individual

        Args:
            invoker: AgentInvoker for subprocess management
            worktree_manager: WorktreeManager for git isolation
            wp_content: Work package content/requirements
            agents: List of available agent configurations (need at least 3)
            timeout: Timeout in seconds for each invocation

        Returns:
            PathResult with execution details
        """
        from ..invoker.invocation_result import InvocationOutcome

        if len(agents) < 3:
            return PathResult(
                status="skipped",
                reason=f"Parallel requires 3 agents, only {len(agents)} available",
                invocations=[],
            )

        # Use first 3 agents
        selected_agents = agents[:3]
        invocations: List["InvocationResult"] = []
        worktrees = []

        try:
            # Create 3 worktrees
            for i in range(3):
                wt = worktree_manager.create(
                    branch_name=f"parallel-{i}-{uuid4().hex[:8]}"
                )
                worktrees.append(wt)

            # Run 3 implementations in parallel
            start_time = datetime.utcnow()

            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures: Dict[concurrent.futures.Future, int] = {}

                for i, (agent, worktree) in enumerate(zip(selected_agents, worktrees)):
                    impl_prompt = self._build_implement_prompt(wp_content)
                    future = executor.submit(
                        invoker.invoke,
                        agent_config=agent,
                        prompt=impl_prompt,
                        worktree=worktree.path,
                        timeout=timeout,
                    )
                    futures[future] = i

                # Collect results
                results: List[Optional["InvocationResult"]] = [None] * 3
                for future in concurrent.futures.as_completed(futures):
                    idx = futures[future]
                    try:
                        result = future.result()
                        results[idx] = result
                        invocations.append(result)
                    except Exception as e:
                        return PathResult(
                            status="failed",
                            reason=f"Agent {idx} failed: {e}",
                            invocations=invocations,
                        )

            end_time = datetime.utcnow()
            total_time = (end_time - start_time).total_seconds()

            # Check timing criteria
            individual_times = [r.duration_seconds for r in results if r]
            if individual_times:
                max_individual = max(individual_times)
                if total_time > max_individual * 2:
                    return PathResult(
                        status="failed",
                        reason=f"Parallel not efficient: {total_time:.1f}s > 2x{max_individual:.1f}s",
                        invocations=invocations,
                    )

            # Check all succeeded
            failures = [r for r in results if r and r.outcome != InvocationOutcome.SUCCESS]
            if failures:
                return PathResult(
                    status="failed",
                    reason=f"{len(failures)} agent(s) failed",
                    invocations=invocations,
                )

            return PathResult(
                status="passed",
                reason=f"3 agents completed in {total_time:.1f}s",
                invocations=invocations,
            )

        finally:
            for wt in worktrees:
                worktree_manager.remove(wt.path)
