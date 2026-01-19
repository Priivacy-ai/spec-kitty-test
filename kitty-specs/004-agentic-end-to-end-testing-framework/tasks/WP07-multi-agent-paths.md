---
work_package_id: WP07
title: 'Multi-Agent Paths: Cross-Review and Parallel'
lane: "for_review"
dependencies: []
subtasks:
- T016
- T017
phase: Phase 3 - Test Paths
assignee: ''
agent: "claude-opus"
shell_pid: "66829"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-19T00:00:00Z'
  lane: planned
  agent: system
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP07 – Multi-Agent Paths: Cross-Review and Parallel

## Objective

Extend the test path framework with CrossReviewPath (2-agent workflow where different agents implement and review) and ParallelThreePath (3-agent workflow with parallel WP execution).

## Context

**Depends On**: WP04 (SingleAgentPath), WP05 (workflow engine)
**User Stories Addressed**: US2 (Two-Agent Cross-Review), US3 (Three-Agent Parallel)
**Functional Requirements**: FR-008, FR-009

These paths build on the TestPath base class established in WP04. The cross-review path enforces that the reviewer is a different agent than the implementer. The parallel path coordinates multiple agents working on independent WPs simultaneously.

## Subtasks

### T016: Implement CrossReviewPath for 2-agent workflow

Create `tests/agentic/paths/cross_review.py`:

```python
"""Two-agent cross-review test path implementation."""

from typing import List, Optional, Callable, Dict, Any
import asyncio

from .base_path import (
    TestPath, TestPathConfig, WorkflowStep, AgentRole, AgentSlot
)

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
    """

    @classmethod
    def from_config(cls, config: TestPathConfig) -> 'CrossReviewPath':
        """Create CrossReviewPath from config."""
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
        """Build cross-review workflow steps."""
        return [
            WorkflowStep(
                step_id="implement",
                slot_id="implementer",
                action="implement",
                on_success="review",
                on_failure=None
            ),
            WorkflowStep(
                step_id="review",
                slot_id="reviewer",  # Different agent via different_from constraint
                action="review",
                on_success="complete",
                on_failure="rework"
            ),
            WorkflowStep(
                step_id="rework",
                slot_id="implementer",  # Back to original implementer
                action="rework",
                on_success="review",
                on_failure=None
            ),
            WorkflowStep(
                step_id="complete",
                slot_id=None,
                action="complete",
                on_success=None,
                on_failure=None
            )
        ]

    async def execute(
        self,
        container_factory: 'AgentContainerFactory',
        agent_registry: 'AgentRegistry',
        worktree_path: str,
        on_step_complete: Optional[Callable] = None
    ) -> 'TestRun':
        """Execute the cross-review workflow.

        Key behaviors:
        - Validates implementer != reviewer at start
        - Tracks which agent performs each action
        - Ensures rework goes back to original implementer
        """
        from ..fixtures.workflow_fixtures import (
            TestRun, TestStatus, WorkflowObservation, EventType
        )

        # Get agents for both slots
        implementer_id = self.get_agent_for_slot("implementer")
        reviewer_id = self.get_agent_for_slot("reviewer")

        # Validate different agents
        if implementer_id == reviewer_id:
            raise ValueError(
                f"CrossReviewPath requires different agents, got {implementer_id} for both"
            )

        implementer_config = agent_registry.get_agent(implementer_id)
        reviewer_config = agent_registry.get_agent(reviewer_id)

        if not implementer_config or not reviewer_config:
            raise ValueError("Required agent not found in registry")

        # Create test run
        run = TestRun(
            path_id=self.path_id,
            agent_assignments=self._agent_assignments.copy(),
            status=TestStatus.RUNNING
        )

        # Record agent pairing observation
        run.observations.append(WorkflowObservation(
            step="setup",
            agent_id=None,
            event_type=EventType.STATE_CHANGED,
            data={
                "implementer": implementer_id,
                "reviewer": reviewer_id,
                "cross_review": True
            },
            success=True
        ))

        # Build and execute workflow
        self._workflow_steps = self.build_workflow()
        self._current_step = 0
        self._iteration = 0

        try:
            while self._current_step < len(self._workflow_steps):
                step = self._workflow_steps[self._current_step]

                if step.action == "complete":
                    run.status = TestStatus.PASSED
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
                    worktree_path=worktree_path
                )
                run.observations.append(observation)

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
                    else:
                        run.status = TestStatus.FAILED
                        run.failure_reason = f"Step '{step.step_id}' failed"
                        break

        except Exception as e:
            run.status = TestStatus.ERROR
            run.failure_reason = str(e)

        run.complete()
        return run

    async def _execute_step(
        self,
        step: WorkflowStep,
        agent_config: 'AgentConfig',
        container_factory: 'AgentContainerFactory',
        worktree_path: str
    ) -> 'WorkflowObservation':
        """Execute a single workflow step."""
        from ..fixtures.workflow_fixtures import WorkflowObservation, EventType

        container = container_factory.create_container(
            agent_id=agent_config.agent_id,
            worktree_path=worktree_path,
            resource_limits=agent_config.resource_limits
        )

        try:
            cmd = self._build_command(step.action, agent_config)

            exit_code, stdout, stderr = container.exec_command(
                cmd,
                timeout=agent_config.timeout_seconds
            )

            return WorkflowObservation(
                step=step.step_id,
                agent_id=agent_config.agent_id,
                event_type=EventType.AGENT_COMPLETED if exit_code == 0 else EventType.AGENT_FAILED,
                data={
                    "exit_code": exit_code,
                    "stdout": stdout,
                    "stderr": stderr,
                    "command": cmd,
                    "role": step.slot_id  # Track which role this agent played
                },
                success=exit_code == 0
            )
        finally:
            container.container.stop()

    def _find_step_index(self, step_id: str) -> int:
        for i, step in enumerate(self._workflow_steps):
            if step.step_id == step_id:
                return i
        raise ValueError(f"Step '{step_id}' not found")

    def _build_command(self, action: str, agent: 'AgentConfig') -> str:
        """Build command for an action."""
        prompts = {
            "implement": "Implement the work package per the prompt file",
            "review": "Review the implementation and approve or reject with feedback",
            "rework": "Address the review feedback and fix the issues"
        }
        prompt = prompts.get(action, action)
        return f"{agent.command} '{prompt}'"
```

**Acceptance Criteria**:
- Enforces implementer != reviewer constraint
- Records which agent performs each action
- Rework always goes to implementer
- Tracks cross-review metadata in observations
- Clear error messages for constraint violations

### T017: Implement ParallelThreePath for 3-agent workflow

Create `tests/agentic/paths/parallel_three.py`:

```python
"""Three-agent parallel execution test path."""

from typing import List, Optional, Callable, Dict, Any, Tuple
import asyncio
from dataclasses import dataclass

from .base_path import (
    TestPath, TestPathConfig, WorkflowStep, AgentRole, AgentSlot
)

@dataclass
class ParallelWorkItem:
    """A work item for parallel execution."""
    wp_id: str
    slot_id: str
    agent_id: str

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
    3. Each gets reviewed (can be cross-review or self)
    4. Complete when all three WPs are done
    """

    def __init__(self, config: TestPathConfig):
        super().__init__(config)
        self._work_items: List[ParallelWorkItem] = []
        self._results: Dict[str, 'TestRun'] = {}

    @classmethod
    def from_config(cls, config: TestPathConfig) -> 'ParallelThreePath':
        """Create ParallelThreePath from config."""
        # Validate we have 3 worker slots
        worker_slots = [s for s in config.agent_slots if s.slot_id.startswith("worker_")]
        if len(worker_slots) < 1:
            raise ValueError("ParallelThreePath requires at least one worker slot")
        return cls(config)

    def assign_work_items(
        self,
        wp_ids: List[str],
        agent_assignments: Dict[str, str]
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

            self._work_items.append(ParallelWorkItem(
                wp_id=wp_id,
                slot_id=slot_id,
                agent_id=agent_id
            ))

        return self._work_items

    def build_workflow(self) -> List[WorkflowStep]:
        """Build parallel workflow - one step per work item."""
        steps = []

        for item in self._work_items:
            steps.append(WorkflowStep(
                step_id=f"implement_{item.wp_id}",
                slot_id=item.slot_id,
                action="implement",
                on_success=f"review_{item.wp_id}",
                on_failure=None
            ))
            steps.append(WorkflowStep(
                step_id=f"review_{item.wp_id}",
                slot_id=item.slot_id,  # Self-review for simplicity
                action="review",
                on_success=f"complete_{item.wp_id}",
                on_failure=f"rework_{item.wp_id}"
            ))
            steps.append(WorkflowStep(
                step_id=f"rework_{item.wp_id}",
                slot_id=item.slot_id,
                action="rework",
                on_success=f"review_{item.wp_id}",
                on_failure=None
            ))
            steps.append(WorkflowStep(
                step_id=f"complete_{item.wp_id}",
                slot_id=None,
                action="complete",
                on_success=None,
                on_failure=None
            ))

        return steps

    async def execute(
        self,
        container_factory: 'AgentContainerFactory',
        agent_registry: 'AgentRegistry',
        worktree_path: str,
        on_step_complete: Optional[Callable] = None
    ) -> 'TestRun':
        """Execute parallel workflow.

        Key behaviors:
        - Launches all agents concurrently
        - Tracks individual and aggregate timing
        - Reports partial success if some agents complete
        """
        from ..fixtures.workflow_fixtures import (
            TestRun, TestStatus, WorkflowObservation, EventType
        )
        import time

        if not self._work_items:
            raise ValueError("No work items assigned. Call assign_work_items first.")

        # Create aggregate test run
        run = TestRun(
            path_id=self.path_id,
            agent_assignments=self._agent_assignments.copy(),
            status=TestStatus.RUNNING
        )

        # Record parallel setup
        run.observations.append(WorkflowObservation(
            step="parallel_setup",
            agent_id=None,
            event_type=EventType.STATE_CHANGED,
            data={
                "parallel": True,
                "work_items": [
                    {"wp_id": item.wp_id, "agent_id": item.agent_id}
                    for item in self._work_items
                ],
                "num_parallel": len(self._work_items)
            },
            success=True
        ))

        start_time = time.time()

        try:
            # Execute all work items in parallel
            tasks = [
                self._execute_work_item(
                    item=item,
                    agent_registry=agent_registry,
                    container_factory=container_factory,
                    worktree_path=worktree_path
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
                    run.observations.append(WorkflowObservation(
                        step=f"parallel_{item.wp_id}",
                        agent_id=item.agent_id,
                        event_type=EventType.AGENT_FAILED,
                        data={"error": str(result), "wp_id": item.wp_id},
                        success=False
                    ))
                elif result.status == TestStatus.PASSED:
                    successes += 1
                    run.observations.extend(result.observations)
                else:
                    failures += 1
                    run.observations.extend(result.observations)

                self._results[item.wp_id] = result

            elapsed_time = time.time() - start_time

            # Record parallel completion
            run.observations.append(WorkflowObservation(
                step="parallel_complete",
                agent_id=None,
                event_type=EventType.STATE_CHANGED,
                data={
                    "successes": successes,
                    "failures": failures,
                    "total": len(self._work_items),
                    "elapsed_seconds": elapsed_time
                },
                success=failures == 0
            ))

            # Determine overall status
            if failures == 0:
                run.status = TestStatus.PASSED
            elif successes > 0:
                run.status = TestStatus.FAILED
                run.failure_reason = f"{failures}/{len(self._work_items)} work items failed"
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
        agent_registry: 'AgentRegistry',
        container_factory: 'AgentContainerFactory',
        worktree_path: str
    ) -> 'TestRun':
        """Execute a single work item (implement -> review cycle)."""
        from ..fixtures.workflow_fixtures import (
            TestRun, TestStatus, WorkflowObservation, EventType
        )

        agent_config = agent_registry.get_agent(item.agent_id)
        if not agent_config:
            raise ValueError(f"Agent {item.agent_id} not found")

        # Create sub-run for this work item
        sub_run = TestRun(
            path_id=f"{self.path_id}:{item.wp_id}",
            agent_assignments={item.slot_id: item.agent_id},
            status=TestStatus.RUNNING
        )

        iteration = 0
        max_iterations = self.config.max_iterations

        # Simple implement -> review -> (rework) loop
        while iteration < max_iterations:
            # Implement
            impl_result = await self._run_agent_step(
                agent_config, container_factory, worktree_path,
                "implement", item.wp_id
            )
            sub_run.observations.append(impl_result)

            if not impl_result.success:
                sub_run.status = TestStatus.FAILED
                sub_run.failure_reason = f"Implementation failed for {item.wp_id}"
                break

            # Review
            review_result = await self._run_agent_step(
                agent_config, container_factory, worktree_path,
                "review", item.wp_id
            )
            sub_run.observations.append(review_result)

            if review_result.success:
                sub_run.status = TestStatus.PASSED
                break
            else:
                iteration += 1
                if iteration < max_iterations:
                    # Rework
                    rework_result = await self._run_agent_step(
                        agent_config, container_factory, worktree_path,
                        "rework", item.wp_id
                    )
                    sub_run.observations.append(rework_result)

        if iteration >= max_iterations:
            sub_run.status = TestStatus.FAILED
            sub_run.failure_reason = f"Max iterations exceeded for {item.wp_id}"

        sub_run.complete()
        return sub_run

    async def _run_agent_step(
        self,
        agent_config: 'AgentConfig',
        container_factory: 'AgentContainerFactory',
        worktree_path: str,
        action: str,
        wp_id: str
    ) -> 'WorkflowObservation':
        """Run a single agent action."""
        from ..fixtures.workflow_fixtures import WorkflowObservation, EventType

        container = container_factory.create_container(
            agent_id=agent_config.agent_id,
            worktree_path=worktree_path,
            resource_limits=agent_config.resource_limits
        )

        try:
            cmd = f"{agent_config.command} '{action} for {wp_id}'"
            exit_code, stdout, stderr = container.exec_command(
                cmd,
                timeout=agent_config.timeout_seconds
            )

            return WorkflowObservation(
                step=f"{action}_{wp_id}",
                agent_id=agent_config.agent_id,
                event_type=EventType.AGENT_COMPLETED if exit_code == 0 else EventType.AGENT_FAILED,
                data={
                    "exit_code": exit_code,
                    "stdout": stdout[-1000:] if stdout else "",  # Truncate for parallel
                    "stderr": stderr[-1000:] if stderr else "",
                    "wp_id": wp_id,
                    "action": action
                },
                success=exit_code == 0
            )
        finally:
            container.container.stop()

    def get_parallel_timing(self) -> Dict[str, float]:
        """Get timing data for parallel execution analysis."""
        timings = {}
        for wp_id, result in self._results.items():
            if result.started_at and result.completed_at:
                timings[wp_id] = (result.completed_at - result.started_at).total_seconds()
        return timings
```

**Acceptance Criteria**:
- Executes work items truly in parallel (asyncio.gather)
- Tracks individual and aggregate timing
- Reports partial success if some complete
- Container isolation verified (no interference)
- Performance metric: elapsed < 2x slowest single

## Technical Notes

- Use asyncio.gather for true parallelism
- Each work item gets its own container
- Worktree access must be coordinated (different paths or locks)
- Truncate stdout/stderr for parallel runs to avoid memory issues

## Files to Create/Modify

1. `tests/agentic/paths/cross_review.py` (create)
2. `tests/agentic/paths/parallel_three.py` (create)
3. `tests/agentic/paths/__init__.py` (update exports)

## Verification

```bash
# Import check
python -c "
from tests.agentic.paths.cross_review import CrossReviewPath
from tests.agentic.paths.parallel_three import ParallelThreePath
"

# Unit tests
pytest tests/agentic/paths/test_cross_review.py -v
pytest tests/agentic/paths/test_parallel.py -v
```

## Definition of Done

- [ ] CrossReviewPath with different agent enforcement
- [ ] ParallelThreePath with asyncio.gather execution
- [ ] Parallel timing tracking
- [ ] Partial success handling
- [ ] Work item assignment logic
- [ ] Unit tests for both paths

## Activity Log

- 2026-01-19T14:48:41Z – claude-opus – shell_pid=66829 – lane=doing – Started implementation via workflow command
- 2026-01-19T14:52:41Z – claude-opus – shell_pid=66829 – lane=for_review – Ready for review: CrossReviewPath with different-agent enforcement, ParallelThreePath with asyncio.gather. Both exported in __init__.py with helper classes.
