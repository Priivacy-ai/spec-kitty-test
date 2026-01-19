---
work_package_id: WP04
title: 'Test Path Framework: Base Class and Path Definitions'
lane: "for_review"
dependencies: []
subtasks:
- T013
- T014
- T015
phase: Phase 2 - Fixtures
assignee: ''
agent: "claude-opus"
shell_pid: "45460"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-19T00:00:00Z'
  lane: planned
  agent: system
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP04 – Test Path Framework: Base Class and Path Definitions

## Objective

Create the TestPath abstraction layer that defines reusable workflow templates with pluggable agent slots. Implement parameterized test support and the SingleAgentPath implementation as the foundation for multi-agent paths.

## Context

**Depends On**: WP03 (fixtures must exist)
**User Stories Addressed**: US1 (Single-Agent), US2 (Two-Agent), US3 (Three-Agent)
**Functional Requirements**: FR-007, FR-010, FR-011

A TestPath is a workflow template that defines agent interaction patterns without specifying which agents. Agent slots are filled at runtime based on available agents, enabling the same test path to run with different agent combinations.

## Subtasks

### T013: Implement TestPath base class with agent slots

Create `tests/agentic/paths/base_path.py`:

```python
"""Base class for test path definitions."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from enum import Enum

class AgentRole(Enum):
    """Roles an agent can fill in a test path."""
    IMPLEMENTATION = "implementation"
    REVIEW = "review"

@dataclass
class AgentSlot:
    """A placeholder in a TestPath filled with a specific agent at runtime."""
    slot_id: str
    role: AgentRole
    required: bool = True
    fallback_allowed: bool = False
    same_as: Optional[str] = None  # Must be same agent as this slot
    different_from: Optional[str] = None  # Must be different agent

@dataclass
class WorkflowStep:
    """A single step in the test workflow."""
    step_id: str
    slot_id: str  # Which agent slot executes this step
    action: str  # "implement", "review", "rework"
    on_success: Optional[str] = None  # Next step ID
    on_failure: Optional[str] = None  # Step ID on failure

@dataclass
class TestPathConfig:
    """Configuration loaded from paths.yaml."""
    path_id: str
    description: str
    agent_slots: List[AgentSlot]
    max_iterations: int = 3
    timeout_seconds: int = 1800

class TestPath(ABC):
    """Abstract base class for test path implementations.

    A TestPath defines a workflow template that can be instantiated
    with specific agents at runtime.
    """

    def __init__(self, config: TestPathConfig):
        self.config = config
        self._agent_assignments: Dict[str, str] = {}  # slot_id -> agent_id
        self._workflow_steps: List[WorkflowStep] = []
        self._current_step: int = 0
        self._iteration: int = 0

    @property
    def path_id(self) -> str:
        return self.config.path_id

    @property
    def agent_slots(self) -> List[AgentSlot]:
        return self.config.agent_slots

    def assign_agents(self, assignments: Dict[str, str]) -> None:
        """Assign agents to slots.

        Args:
            assignments: Mapping of slot_id to agent_id

        Raises:
            ValueError: If required slot not assigned or constraints violated
        """
        # Validate required slots
        for slot in self.agent_slots:
            if slot.required and slot.slot_id not in assignments:
                raise ValueError(f"Required slot '{slot.slot_id}' not assigned")

        # Validate constraints
        for slot in self.agent_slots:
            if slot.slot_id not in assignments:
                continue

            agent_id = assignments[slot.slot_id]

            if slot.same_as and slot.same_as in assignments:
                if assignments[slot.same_as] != agent_id:
                    raise ValueError(
                        f"Slot '{slot.slot_id}' must use same agent as '{slot.same_as}'"
                    )

            if slot.different_from and slot.different_from in assignments:
                if assignments[slot.different_from] == agent_id:
                    raise ValueError(
                        f"Slot '{slot.slot_id}' must use different agent than '{slot.different_from}'"
                    )

        self._agent_assignments = assignments

    def get_agent_for_slot(self, slot_id: str) -> Optional[str]:
        """Get the agent ID assigned to a slot."""
        return self._agent_assignments.get(slot_id)

    @abstractmethod
    def build_workflow(self) -> List[WorkflowStep]:
        """Build the workflow steps for this path.

        Must be implemented by subclasses to define the specific
        workflow sequence.
        """
        pass

    @abstractmethod
    async def execute(
        self,
        container_factory: 'AgentContainerFactory',
        agent_registry: 'AgentRegistry',
        worktree_path: str,
        on_step_complete: Optional[Callable] = None
    ) -> 'TestRun':
        """Execute the test path workflow.

        Args:
            container_factory: Factory for creating agent containers
            agent_registry: Registry of available agents
            worktree_path: Path to the test worktree
            on_step_complete: Callback after each step

        Returns:
            TestRun with complete execution results
        """
        pass
```

**Acceptance Criteria**:
- AgentSlot captures role and constraints
- TestPath validates slot assignments
- same_as / different_from constraints enforced
- Abstract methods for subclass implementation
- Clean separation of config and execution

### T014: Implement parameterized test support for agent combinations

Create test parametrization utilities in `tests/agentic/paths/__init__.py`:

```python
"""Test path utilities and parametrization."""

import pytest
from itertools import combinations, permutations
from typing import List, Tuple, Optional
from .base_path import TestPath, AgentSlot

def generate_agent_combinations(
    available_agents: List[str],
    path: TestPath,
    max_combinations: Optional[int] = None
) -> List[dict]:
    """Generate valid agent assignment combinations for a path.

    Args:
        available_agents: List of available agent IDs
        path: TestPath to generate combinations for
        max_combinations: Maximum combinations to return (for test performance)

    Returns:
        List of slot_id -> agent_id assignment dicts
    """
    slots = path.agent_slots
    required_slots = [s for s in slots if s.required]

    if len(available_agents) < len(required_slots):
        return []  # Not enough agents

    combinations_list = []

    # For slots with same_as constraint, they share an agent
    # For slots with different_from constraint, they need different agents

    # Simple case: all slots independent
    if all(s.same_as is None and s.different_from is None for s in slots):
        for combo in permutations(available_agents, len(required_slots)):
            assignment = {
                slot.slot_id: agent
                for slot, agent in zip(required_slots, combo)
            }
            combinations_list.append(assignment)
    else:
        # Complex case: handle constraints
        combinations_list = _generate_constrained_combinations(
            available_agents, slots
        )

    if max_combinations:
        combinations_list = combinations_list[:max_combinations]

    return combinations_list

def _generate_constrained_combinations(
    agents: List[str],
    slots: List[AgentSlot]
) -> List[dict]:
    """Generate combinations respecting slot constraints."""
    # Implementation handles same_as and different_from constraints
    # ... detailed implementation
    pass

def agent_combo_ids(combos: List[dict]) -> List[str]:
    """Generate readable test IDs for agent combinations."""
    return [
        "+".join(f"{k}={v}" for k, v in sorted(combo.items()))
        for combo in combos
    ]

# Pytest parametrize decorator factory
def parametrize_agent_combos(path_id: str, max_combos: int = 10):
    """Decorator to parametrize tests over agent combinations.

    Usage:
        @parametrize_agent_combos("cross-review", max_combos=5)
        def test_cross_review_workflow(agent_assignments):
            ...
    """
    def decorator(func):
        # Actual parametrization happens at collection time
        # using available_agents fixture
        return pytest.mark.parametrize(
            "agent_assignments",
            [],  # Populated dynamically
            indirect=True
        )(func)
    return decorator
```

**Acceptance Criteria**:
- Generates valid agent combinations for any path
- Respects same_as and different_from constraints
- Limits combinations for test performance
- Readable test IDs for combination reporting
- Works with pytest.mark.parametrize

### T015: Implement SingleAgentPath for 1-agent workflow

Create `tests/agentic/paths/single_agent.py`:

```python
"""Single-agent test path implementation."""

from typing import List, Optional, Callable
from dataclasses import dataclass
import asyncio

from .base_path import (
    TestPath, TestPathConfig, WorkflowStep, AgentRole, AgentSlot
)

class SingleAgentPath(TestPath):
    """Test path where one agent performs both implementation and review.

    Workflow:
    1. Agent implements the WP
    2. Same agent reviews its own work
    3. If rejected, agent reworks (up to max_iterations)
    4. Complete when approved or max iterations reached
    """

    @classmethod
    def from_config(cls, config: TestPathConfig) -> 'SingleAgentPath':
        """Create SingleAgentPath from config."""
        return cls(config)

    def build_workflow(self) -> List[WorkflowStep]:
        """Build single-agent workflow steps."""
        return [
            WorkflowStep(
                step_id="implement",
                slot_id="implementer",
                action="implement",
                on_success="review",
                on_failure=None  # Test fails
            ),
            WorkflowStep(
                step_id="review",
                slot_id="reviewer",  # Same agent via same_as constraint
                action="review",
                on_success="complete",
                on_failure="rework"
            ),
            WorkflowStep(
                step_id="rework",
                slot_id="implementer",
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
        """Execute the single-agent workflow.

        Returns:
            TestRun with execution results
        """
        from ..fixtures.workflow_fixtures import TestRun, TestStatus, WorkflowObservation

        # Get the single agent (same for both slots)
        agent_id = self.get_agent_for_slot("implementer")
        agent_config = agent_registry.get_agent(agent_id)

        if not agent_config:
            raise ValueError(f"Agent {agent_id} not found in registry")

        # Create test run
        run = TestRun(
            path_id=self.path_id,
            agent_assignments=self._agent_assignments.copy(),
            status=TestStatus.RUNNING
        )

        # Build workflow
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
                    run.failure_reason = f"Max iterations ({self.config.max_iterations}) exceeded"
                    break

                # Execute step in container
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
                        run.failure_reason = f"Step '{step.step_id}' failed with no recovery"
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
        """Execute a single workflow step in a container."""
        from ..fixtures.workflow_fixtures import WorkflowObservation, EventType

        # Create container for this step
        container = container_factory.create_container(
            agent_id=agent_config.agent_id,
            worktree_path=worktree_path,
            resource_limits=agent_config.resource_limits
        )

        try:
            # Build command based on action
            if step.action == "implement":
                cmd = self._build_implement_command(agent_config)
            elif step.action == "review":
                cmd = self._build_review_command(agent_config)
            elif step.action == "rework":
                cmd = self._build_rework_command(agent_config)
            else:
                raise ValueError(f"Unknown action: {step.action}")

            # Execute with timeout
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
                    "command": cmd
                },
                success=exit_code == 0
            )
        finally:
            container.container.stop()

    def _find_step_index(self, step_id: str) -> int:
        """Find index of step by ID."""
        for i, step in enumerate(self._workflow_steps):
            if step.step_id == step_id:
                return i
        raise ValueError(f"Step '{step_id}' not found")

    def _build_implement_command(self, agent: 'AgentConfig') -> str:
        """Build the implementation command for an agent."""
        # Per research.md E007, agents have different invocation patterns
        if agent.agent_id == "claude-code":
            return "claude -p 'Implement the work package per the prompt file'"
        elif agent.agent_id == "github-copilot":
            return "copilot -p 'Implement the work package'"
        # ... other agents
        return f"{agent.command} 'Implement the work package'"

    def _build_review_command(self, agent: 'AgentConfig') -> str:
        """Build the review command for an agent."""
        return f"{agent.command} 'Review the implementation'"

    def _build_rework_command(self, agent: 'AgentConfig') -> str:
        """Build the rework command for an agent."""
        return f"{agent.command} 'Address review feedback'"
```

**Acceptance Criteria**:
- SingleAgentPath executes implement → review → (rework loop) → done
- Handles rejection cycles up to max_iterations
- Creates container per step execution
- Captures WorkflowObservation for each step
- Returns TestRun with complete results

## Technical Notes

- TestPath is async to support parallel execution in future WPs
- Container per step allows clean isolation
- WorkflowObservation records everything for debugging
- Agent command building is agent-specific per research.md

## Files to Create/Modify

1. `tests/agentic/paths/__init__.py` (update with utilities)
2. `tests/agentic/paths/base_path.py` (create)
3. `tests/agentic/paths/single_agent.py` (create)

## Verification

```bash
# Import check
python -c "from tests.agentic.paths.base_path import TestPath, AgentSlot"
python -c "from tests.agentic.paths.single_agent import SingleAgentPath"

# Unit tests
pytest tests/agentic/paths/ -v
```

## Definition of Done

- [ ] TestPath base class with slot validation
- [ ] AgentSlot with same_as/different_from constraints
- [ ] generate_agent_combinations utility
- [ ] SingleAgentPath implementation
- [ ] Workflow step execution with containers
- [ ] TestRun result capture
- [ ] Unit tests for path logic

## Activity Log

- 2026-01-19T12:53:15Z – claude-opus – shell_pid=45460 – lane=doing – Started implementation via workflow command
- 2026-01-19T12:57:24Z – claude-opus – shell_pid=45460 – lane=for_review – Ready for review: TestPath base class with slot constraints, combination generation, and SingleAgentPath workflow implementation
