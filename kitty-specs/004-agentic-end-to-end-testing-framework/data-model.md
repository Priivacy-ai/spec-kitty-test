# Data Model: Agentic End-to-End Testing Framework

**Purpose**: Define the entities and schemas for the containerized agentic testing framework.

## Entities

### Entity: TestPath

A reusable workflow template defining agent interaction patterns without specifying which agents.

- **Description**: Represents a test scenario structure (1-agent, 2-agent, 3-agent) that can be instantiated with different agent combinations
- **Attributes**:
  - `path_id` (str) – Unique identifier, e.g., "single-agent", "cross-review", "parallel-3"
  - `agent_slots` (list[AgentSlot]) – Ordered list of agent roles required
  - `workflow_steps` (list[WorkflowStep]) – Sequence of steps to execute
  - `max_iterations` (int) – Maximum review rejection cycles before failure
  - `timeout_seconds` (int) – Overall path execution timeout
- **Identifiers**: `path_id` (primary)
- **Lifecycle Notes**: Defined in code, immutable at runtime

### Entity: AgentSlot

A placeholder in a TestPath filled with a specific agent at runtime.

- **Description**: Represents a role in a test that an agent will fill (implementer, reviewer, etc.)
- **Attributes**:
  - `slot_id` (str) – Unique within path, e.g., "implementer", "reviewer", "worker_1"
  - `role` (AgentRole) – Either "implementation" or "review"
  - `required` (bool) – If true, test fails without this agent available
  - `fallback_allowed` (bool) – Whether another agent can fill this slot if primary unavailable
- **Identifiers**: `slot_id` within parent TestPath
- **Lifecycle Notes**: Defined as part of TestPath

### Entity: AgentConfig

Configuration for a specific AI coding agent.

- **Description**: Stores per-agent settings including credentials reference, timeouts, and availability
- **Attributes**:
  - `agent_id` (str) – Identifier matching orchestrator config, e.g., "claude-code"
  - `enabled` (bool) – Whether this agent is available for testing
  - `command` (str) – CLI command to invoke agent
  - `invocation_pattern` (InvocationPattern) – How to pass prompts (stdin, arg, file)
  - `timeout_seconds` (int) – Per-invocation timeout
  - `resource_limits` (ResourceLimits) – CPU, memory, disk constraints
  - `credentials_secret` (str) – Name of Docker secret containing API key
  - `requires_timeout_wrapper` (bool) – True for Cursor agent
- **Identifiers**: `agent_id` (primary)
- **Lifecycle Notes**: Loaded from YAML at test start, can be overridden per-test

### Entity: TestContainer

An isolated container environment for agent invocation.

- **Description**: Docker container configured for safe, isolated agent execution
- **Attributes**:
  - `container_id` (str) – Docker container ID
  - `agent_id` (str) – Which agent this container runs
  - `image` (str) – Docker image name and tag
  - `network` (str) – Docker network (internal, no internet)
  - `resource_limits` (ResourceLimits) – Applied constraints
  - `mounts` (list[Mount]) – Worktree and secret mounts
  - `status` (ContainerStatus) – running, stopped, failed
  - `started_at` (datetime) – Container start time
  - `stopped_at` (datetime | None) – Container stop time
- **Identifiers**: `container_id` (primary)
- **Lifecycle Notes**: Created per agent invocation, destroyed after completion

### Entity: FaultInjector

Component for injecting specific failure conditions during test execution.

- **Description**: Provides methods to simulate crashes, timeouts, corruption, and network failures
- **Attributes**:
  - `injector_type` (FaultType) – process_crash, timeout, corruption, network, auth_failure
  - `target` (str) – What to inject fault into (container_id, file_path, network)
  - `parameters` (dict) – Fault-specific parameters (delay_ms, error_code, etc.)
  - `trigger` (TriggerCondition) – When to inject (immediate, after_n_calls, random_probability)
- **Identifiers**: Generated UUID per injection
- **Lifecycle Notes**: Created per test, cleared between tests

### Entity: TestRun

A single execution of a TestPath with specific agents.

- **Description**: Tracks complete test execution including all inputs, outputs, and observations
- **Attributes**:
  - `run_id` (str) – UUID for this run
  - `path_id` (str) – Which TestPath was executed
  - `agent_assignments` (dict[str, str]) – Slot ID → Agent ID mapping
  - `started_at` (datetime) – Test start time
  - `completed_at` (datetime | None) – Test completion time
  - `status` (TestStatus) – pending, running, passed, failed, error
  - `workflow_state` (WorkflowState) – Current position in workflow
  - `observations` (list[WorkflowObservation]) – All captured data
  - `fault_injections` (list[FaultInjection]) – Faults applied during run
  - `failure_reason` (str | None) – Why test failed if applicable
- **Identifiers**: `run_id` (primary)
- **Lifecycle Notes**: Created at test start, updated throughout, persisted for analysis

### Entity: WorkflowObservation

Captured data from a specific point in test execution.

- **Description**: Immutable record of what happened at a workflow step
- **Attributes**:
  - `observation_id` (str) – UUID
  - `run_id` (str) – Parent test run
  - `timestamp` (datetime) – When observation was captured
  - `step` (str) – Which workflow step
  - `agent_id` (str | None) – Which agent was involved
  - `event_type` (EventType) – agent_started, agent_completed, agent_failed, state_changed, fault_injected
  - `data` (dict) – Event-specific data (exit_code, stdout, stderr, files_modified, etc.)
  - `container_metrics` (ContainerMetrics | None) – CPU, memory, network stats
- **Identifiers**: `observation_id` (primary)
- **Lifecycle Notes**: Append-only during test run

### Entity: ResourceLimits

Constraints applied to agent containers.

- **Description**: Defines CPU, memory, and disk limits for container isolation
- **Attributes**:
  - `cpu_cores` (float) – Max CPU cores, e.g., 2.0
  - `memory_mb` (int) – Max memory in MB, e.g., 4096
  - `disk_mb` (int) – Max disk space in MB, e.g., 10240
  - `network_bandwidth_kbps` (int | None) – Optional bandwidth limit
  - `io_read_bps` (int | None) – Optional I/O read limit
  - `io_write_bps` (int | None) – Optional I/O write limit
- **Identifiers**: Embedded in AgentConfig and TestContainer
- **Lifecycle Notes**: Defined in config, applied at container creation

### Entity: ContainerMetrics

Runtime metrics captured from a container.

- **Description**: Snapshot of container resource usage at a point in time
- **Attributes**:
  - `timestamp` (datetime) – When metrics were captured
  - `cpu_percent` (float) – CPU usage percentage
  - `memory_used_mb` (int) – Memory currently used
  - `memory_percent` (float) – Memory usage percentage
  - `disk_used_mb` (int) – Disk space used
  - `network_rx_bytes` (int) – Bytes received
  - `network_tx_bytes` (int) – Bytes transmitted
- **Identifiers**: Embedded in WorkflowObservation
- **Lifecycle Notes**: Captured periodically during container execution

## Relationships

| Source | Relation | Target | Cardinality | Notes |
|--------|----------|--------|-------------|-------|
| TestPath | has | AgentSlot | 1:N | A path has 1-3 slots |
| TestRun | executes | TestPath | N:1 | Many runs can use same path |
| TestRun | assigns | AgentConfig | N:N | Via agent_assignments dict |
| TestRun | spawns | TestContainer | 1:N | One container per invocation |
| TestRun | contains | WorkflowObservation | 1:N | Append-only observations |
| TestContainer | uses | ResourceLimits | 1:1 | Embedded limits |
| WorkflowObservation | includes | ContainerMetrics | 1:0..1 | Optional metrics |
| FaultInjector | targets | TestContainer | N:1 | Multiple faults can target one container |

## Enums

```python
class AgentRole(Enum):
    IMPLEMENTATION = "implementation"
    REVIEW = "review"

class InvocationPattern(Enum):
    STDIN = "stdin"           # Pipe prompt to stdin
    ARGUMENT = "argument"     # Pass prompt as CLI argument
    FILE = "file"             # Write prompt to temp file, pass path

class ContainerStatus(Enum):
    CREATING = "creating"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"
    TERMINATED = "terminated"  # Force killed

class TestStatus(Enum):
    PENDING = "pending"        # Not started
    RUNNING = "running"        # In progress
    PASSED = "passed"          # All assertions passed
    FAILED = "failed"          # Assertion failed
    ERROR = "error"            # Infrastructure error
    SKIPPED = "skipped"        # Agent unavailable

class EventType(Enum):
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"
    AGENT_TIMEOUT = "agent_timeout"
    STATE_CHANGED = "state_changed"
    FAULT_INJECTED = "fault_injected"
    CONTAINER_CREATED = "container_created"
    CONTAINER_DESTROYED = "container_destroyed"
    WP_LANE_CHANGED = "wp_lane_changed"

class FaultType(Enum):
    PROCESS_CRASH = "process_crash"       # Kill agent process
    TIMEOUT = "timeout"                   # Simulate slow response
    FILE_CORRUPTION = "file_corruption"   # Corrupt state files
    NETWORK_FAILURE = "network_failure"   # Block/delay network
    AUTH_FAILURE = "auth_failure"         # Invalid credentials
    DISK_FULL = "disk_full"               # Exhaust disk space
    MEMORY_PRESSURE = "memory_pressure"   # OOM conditions

class TriggerCondition(Enum):
    IMMEDIATE = "immediate"               # Inject immediately
    AFTER_N_CALLS = "after_n_calls"       # After N agent invocations
    RANDOM = "random"                     # Random probability
    ON_EVENT = "on_event"                 # When specific event occurs
```

## File Schemas

### tests/agentic/config/agents.yaml

```yaml
# Agent configuration for E2E testing
version: "1.0"

agents:
  claude-code:
    enabled: true
    command: "claude"
    invocation_pattern: "stdin"
    timeout_seconds: 600
    credentials_secret: "claude_api_key"
    requires_timeout_wrapper: false
    resource_limits:
      cpu_cores: 2.0
      memory_mb: 4096
      disk_mb: 10240

  github-codex:
    enabled: true
    command: "codex exec"
    invocation_pattern: "stdin"
    timeout_seconds: 300
    credentials_secret: "github_token"
    requires_timeout_wrapper: false
    resource_limits:
      cpu_cores: 2.0
      memory_mb: 4096
      disk_mb: 10240

  cursor:
    enabled: true
    command: "cursor agent"
    invocation_pattern: "argument"
    timeout_seconds: 300
    credentials_secret: "cursor_api_key"
    requires_timeout_wrapper: true  # Known hanging issue
    resource_limits:
      cpu_cores: 2.0
      memory_mb: 4096
      disk_mb: 10240

  # ... other agents follow same pattern

defaults:
  timeout_seconds: 300
  resource_limits:
    cpu_cores: 2.0
    memory_mb: 4096
    disk_mb: 10240

network:
  name: "agent-test-internal"
  driver: "bridge"
  internal: true  # No internet access
```

### tests/agentic/results/run-{uuid}.json

```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "path_id": "cross-review",
  "agent_assignments": {
    "implementer": "claude-code",
    "reviewer": "github-codex"
  },
  "started_at": "2026-01-19T14:00:00Z",
  "completed_at": "2026-01-19T14:15:32Z",
  "status": "passed",
  "workflow_state": {
    "current_step": "completed",
    "wp_lane": "done",
    "iteration": 1
  },
  "observations": [
    {
      "observation_id": "obs-001",
      "timestamp": "2026-01-19T14:00:05Z",
      "step": "implementation",
      "agent_id": "claude-code",
      "event_type": "agent_started",
      "data": {
        "container_id": "abc123",
        "command": ["claude", "-p", "--output-format", "json"]
      }
    },
    {
      "observation_id": "obs-002",
      "timestamp": "2026-01-19T14:08:42Z",
      "step": "implementation",
      "agent_id": "claude-code",
      "event_type": "agent_completed",
      "data": {
        "exit_code": 0,
        "files_modified": ["src/main.py", "tests/test_main.py"],
        "commits_made": ["abc1234"]
      },
      "container_metrics": {
        "cpu_percent": 45.2,
        "memory_used_mb": 1024,
        "memory_percent": 25.0
      }
    }
  ],
  "fault_injections": [],
  "failure_reason": null
}
```

## Validation Rules

### AgentConfig
- `agent_id` must match known agent list
- `timeout_seconds` must be >= 30
- `credentials_secret` must be non-empty
- `resource_limits.cpu_cores` must be >= 0.5
- `resource_limits.memory_mb` must be >= 512

### TestPath
- Must have at least one AgentSlot
- `max_iterations` must be >= 1
- `timeout_seconds` must be >= sum of expected step timeouts

### TestRun
- `agent_assignments` must cover all required slots
- `completed_at` requires `status` not in [pending, running]
- `failure_reason` required if `status` is failed or error

### FaultInjector
- `target` must be valid for `injector_type`
- `parameters` must match schema for fault type
- Cannot inject PROCESS_CRASH on completed container

## Directory Structure

```
tests/agentic/
├── config/
│   ├── agents.yaml          # Agent configurations
│   ├── paths.yaml           # TestPath definitions
│   └── secrets/             # Git-ignored, contains API keys
│       ├── claude_api_key.txt
│       ├── github_token.txt
│       └── ...
├── containers/
│   ├── Dockerfile.base      # Base image with spec-kitty
│   ├── Dockerfile.claude    # Claude-specific if needed
│   └── docker-compose.yaml  # Network and service definitions
├── fixtures/
│   ├── conftest.py          # pytest fixtures for containers
│   ├── agent_fixtures.py    # Agent-specific fixtures
│   └── fault_fixtures.py    # Fault injection fixtures
├── paths/
│   ├── single_agent.py      # 1-agent test path
│   ├── cross_review.py      # 2-agent test path
│   └── parallel_three.py    # 3-agent test path
├── tests/
│   ├── test_single_agent_workflow.py
│   ├── test_cross_agent_review.py
│   ├── test_parallel_execution.py
│   ├── test_fault_injection.py
│   └── test_natural_failures.py
└── results/                  # Git-ignored, test results
    └── run-{uuid}.json
```

> Treat this as a working model. Update as implementation reveals new requirements.
