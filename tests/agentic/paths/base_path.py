"""Base class for test path definitions.

A TestPath defines a workflow template that can be instantiated with specific
agents at runtime. Agent slots are placeholders filled with available agents,
enabling the same test path to run with different agent combinations.

Per CLAUDE.md: These are distribution tests - spec-kitty is installed from PyPI,
NOT from local source. No SPEC_KITTY_TEMPLATE_ROOT is ever set.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..fixtures.container_fixtures import AgentContainerFactory
    from ..fixtures.agent_fixtures import AgentRegistry


class AgentRole(Enum):
    """Roles an agent can fill in a test path.

    IMPLEMENTATION: Agent writes code to implement a feature
    REVIEW: Agent reviews code written by another (or same) agent
    """

    IMPLEMENTATION = "implementation"
    REVIEW = "review"


@dataclass
class AgentSlot:
    """A placeholder in a TestPath filled with a specific agent at runtime.

    Agent slots define:
    - The role the agent plays (implementation vs review)
    - Whether the slot must be filled
    - Constraints on which agents can fill the slot

    Attributes:
        slot_id: Unique identifier for this slot within the path
        role: The role this slot plays in the workflow
        required: Whether this slot must be filled for the path to run
        fallback_allowed: Whether a fallback agent can be used
        same_as: Slot ID that must use the same agent as this slot
        different_from: Slot ID that must use a different agent
    """

    slot_id: str
    role: AgentRole
    required: bool = True
    fallback_allowed: bool = False
    same_as: Optional[str] = None
    different_from: Optional[str] = None


@dataclass
class WorkflowStep:
    """A single step in the test workflow.

    Each step is executed by an agent in a specific slot, performing
    an action like implementing code or reviewing changes.

    Attributes:
        step_id: Unique identifier for this step
        slot_id: Which agent slot executes this step (None for terminal steps)
        action: The action to perform ("implement", "review", "rework", "complete")
        on_success: Step ID to transition to on success
        on_failure: Step ID to transition to on failure
    """

    step_id: str
    slot_id: Optional[str]
    action: str
    on_success: Optional[str] = None
    on_failure: Optional[str] = None


class TestStatus(Enum):
    """Status of a test run.

    PENDING: Test not yet started
    RUNNING: Test currently executing
    PASSED: Test completed successfully
    FAILED: Test completed with failure
    SKIPPED: Test skipped (e.g., agent unavailable)
    ERROR: Test encountered an unexpected error
    """

    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class EventType(Enum):
    """Types of events observed during test execution.

    STEP_STARTED: A workflow step began execution
    STEP_COMPLETED: A workflow step completed successfully
    STEP_FAILED: A workflow step failed
    AGENT_INVOKED: An agent command was invoked
    AGENT_COMPLETED: An agent command completed
    AGENT_FAILED: An agent command failed
    AGENT_TIMEOUT: An agent command timed out
    CONTAINER_STARTED: A container was started
    CONTAINER_STOPPED: A container was stopped
    """

    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    AGENT_INVOKED = "agent_invoked"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"
    AGENT_TIMEOUT = "agent_timeout"
    CONTAINER_STARTED = "container_started"
    CONTAINER_STOPPED = "container_stopped"


@dataclass
class WorkflowObservation:
    """Observation of an event during test execution.

    Records what happened at each step for debugging and analysis.

    Attributes:
        step: The step ID where this observation occurred
        agent_id: The agent that produced this observation
        event_type: Type of event observed
        timestamp: When the event occurred
        data: Additional event-specific data
        success: Whether the event indicates success
    """

    step: str
    agent_id: str
    event_type: EventType
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)
    success: bool = True


@dataclass
class TestRun:
    """Complete results of a test path execution.

    Captures everything needed to understand what happened during
    a test run, including all observations and final status.

    Attributes:
        path_id: ID of the test path that was run
        agent_assignments: Mapping of slot_id to agent_id
        status: Final status of the test run
        observations: All events observed during execution
        started_at: When the test started
        completed_at: When the test completed
        failure_reason: Human-readable failure explanation
        iteration_count: Number of rework iterations performed
    """

    path_id: str
    agent_assignments: Dict[str, str]
    status: TestStatus = TestStatus.PENDING
    observations: List[WorkflowObservation] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    iteration_count: int = 0

    def start(self):
        """Mark the test run as started."""
        self.status = TestStatus.RUNNING
        self.started_at = datetime.now()

    def complete(self, status: Optional[TestStatus] = None):
        """Mark the test run as completed.

        Args:
            status: Optional status to set (uses current status if not provided)
        """
        if status:
            self.status = status
        self.completed_at = datetime.now()

    @property
    def duration_seconds(self) -> Optional[float]:
        """Total duration of the test run in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def add_observation(self, observation: WorkflowObservation):
        """Add an observation to the test run."""
        self.observations.append(observation)


@dataclass
class TestPathConfig:
    """Configuration loaded from paths.yaml.

    Defines the static configuration for a test path that can be
    loaded from YAML and used to create TestPath instances.

    Attributes:
        path_id: Unique identifier for this path
        description: Human-readable description
        agent_slots: List of agent slots required by this path
        max_iterations: Maximum rework iterations before failure
        timeout_seconds: Overall timeout for the entire path
    """

    path_id: str
    description: str
    agent_slots: List[AgentSlot]
    max_iterations: int = 3
    timeout_seconds: int = 1800


class TestPath(ABC):
    """Abstract base class for test path implementations.

    A TestPath defines a workflow template that can be instantiated
    with specific agents at runtime. Subclasses implement specific
    workflow patterns like single-agent or cross-review.

    Usage:
        path = SingleAgentPath.from_config(config)
        path.assign_agents({"implementer": "claude-code", "reviewer": "claude-code"})
        result = await path.execute(factory, registry, worktree)
    """

    def __init__(self, config: TestPathConfig):
        """Initialize with configuration.

        Args:
            config: Path configuration from YAML
        """
        self.config = config
        self._agent_assignments: Dict[str, str] = {}
        self._workflow_steps: List[WorkflowStep] = []
        self._current_step: int = 0
        self._iteration: int = 0

    @property
    def path_id(self) -> str:
        """Unique identifier for this path."""
        return self.config.path_id

    @property
    def agent_slots(self) -> List[AgentSlot]:
        """List of agent slots defined by this path."""
        return self.config.agent_slots

    @property
    def max_iterations(self) -> int:
        """Maximum rework iterations before failure."""
        return self.config.max_iterations

    @property
    def timeout_seconds(self) -> int:
        """Overall timeout for path execution."""
        return self.config.timeout_seconds

    def assign_agents(self, assignments: Dict[str, str]) -> None:
        """Assign agents to slots.

        Validates that all required slots are assigned and that
        all constraints (same_as, different_from) are satisfied.

        Args:
            assignments: Mapping of slot_id to agent_id

        Raises:
            ValueError: If required slot not assigned or constraints violated
        """
        # Validate required slots are assigned
        for slot in self.agent_slots:
            if slot.required and slot.slot_id not in assignments:
                raise ValueError(f"Required slot '{slot.slot_id}' not assigned")

        # Validate constraints
        for slot in self.agent_slots:
            if slot.slot_id not in assignments:
                continue

            agent_id = assignments[slot.slot_id]

            # Check same_as constraint
            if slot.same_as and slot.same_as in assignments:
                if assignments[slot.same_as] != agent_id:
                    raise ValueError(
                        f"Slot '{slot.slot_id}' must use same agent as '{slot.same_as}'"
                    )

            # Check different_from constraint
            if slot.different_from and slot.different_from in assignments:
                if assignments[slot.different_from] == agent_id:
                    raise ValueError(
                        f"Slot '{slot.slot_id}' must use different agent than "
                        f"'{slot.different_from}'"
                    )

        self._agent_assignments = assignments.copy()

    def get_agent_for_slot(self, slot_id: str) -> Optional[str]:
        """Get the agent ID assigned to a slot.

        Args:
            slot_id: The slot to look up

        Returns:
            Agent ID if assigned, None otherwise
        """
        return self._agent_assignments.get(slot_id)

    def validate_assignments(self) -> bool:
        """Check if current assignments are valid.

        Returns:
            True if all constraints are satisfied
        """
        try:
            # Re-validate by calling assign_agents with current assignments
            temp = self._agent_assignments.copy()
            self._agent_assignments = {}
            self.assign_agents(temp)
            return True
        except ValueError:
            return False

    @abstractmethod
    def build_workflow(self) -> List[WorkflowStep]:
        """Build the workflow steps for this path.

        Must be implemented by subclasses to define the specific
        workflow sequence for their pattern.

        Returns:
            List of WorkflowStep defining the execution order
        """
        pass

    @abstractmethod
    async def execute(
        self,
        container_factory: "AgentContainerFactory",
        agent_registry: "AgentRegistry",
        worktree_path: str,
        on_step_complete: Optional[Callable[[WorkflowStep, WorkflowObservation], None]] = None,
    ) -> TestRun:
        """Execute the test path workflow.

        Creates containers, invokes agents, and captures results
        for each step in the workflow.

        Args:
            container_factory: Factory for creating agent containers
            agent_registry: Registry of available agents
            worktree_path: Path to the test worktree
            on_step_complete: Optional callback after each step completes

        Returns:
            TestRun with complete execution results
        """
        pass

    def _find_step_index(self, step_id: str) -> int:
        """Find index of step by ID.

        Args:
            step_id: Step ID to find

        Returns:
            Index of the step

        Raises:
            ValueError: If step not found
        """
        for i, step in enumerate(self._workflow_steps):
            if step.step_id == step_id:
                return i
        raise ValueError(f"Step '{step_id}' not found in workflow")
