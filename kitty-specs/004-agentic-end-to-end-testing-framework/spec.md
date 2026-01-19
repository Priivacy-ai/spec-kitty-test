# Feature Specification: Agentic End-to-End Testing Framework

**Feature Branch**: `004-agentic-end-to-end-testing-framework`
**Created**: 2026-01-19
**Status**: Draft
**Input**: Containerized, adversarial testing framework for spec-kitty multi-agent orchestration

## Problem Statement

Spec-kitty's autonomous multi-agent orchestrator (Feature 020) enables features to be implemented by up to 9 different AI coding agents working in parallel. Testing this system presents unique challenges:

1. **Multi-agent complexity**: Each of 9 agents has different CLI interfaces, authentication methods, and behavioral quirks
2. **Workflow depth**: The implement → review cycle includes rejection/rework loops that send WPs back to "planned"
3. **Safety concerns**: Autonomous agents could potentially damage host systems, leak credentials, or behave unexpectedly
4. **Distribution blindness**: Previous test suites tested development code, missing packaging bugs that affected 100% of users
5. **Cost and time**: Real agent tests make actual LLM API calls, requiring careful resource management

This test framework must validate that spec-kitty's orchestrator works correctly with real agents through complete workflows, using shipped PyPI packages, with an adversarial mindset that actively seeks to break the system.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Single-Agent Workflow Validation (Priority: P1)

A test developer runs the single-agent test path to validate that spec-kitty can execute a complete implement → review workflow using one agent for both roles.

**Why this priority**: Single-agent mode is the simplest configuration and the baseline for all other tests. If this fails, nothing else will work.

**Independent Test**: Can be validated by running a single-agent workflow with any available agent and verifying the WP reaches "done" status with committed code.

**Acceptance Scenarios**:

1. **Given** a prepared feature with one WP in "planned" lane, **When** the single-agent test runs with Claude Code, **Then** the WP progresses through implement → review → done with commits in the worktree
2. **Given** a single-agent test where the review phase rejects the implementation, **When** the WP is sent back to "planned", **Then** the agent re-implements and the cycle continues until approval or max iterations
3. **Given** an agent that is not installed or authenticated, **When** the test attempts to run, **Then** the test is skipped with a clear message (not failed)
4. **Given** a successful single-agent workflow, **When** the test completes, **Then** all logs, outputs, and state are captured for analysis

---

### User Story 2 - Two-Agent Cross-Review Validation (Priority: P1)

A test developer runs the two-agent test path to validate that spec-kitty can use different agents for implementation vs. review, catching blind spots that single-agent review might miss.

**Why this priority**: Cross-agent review is a key value proposition of the orchestrator. Different LLMs have different strengths and catch different issues.

**Independent Test**: Can be validated by running a two-agent workflow and verifying the review agent is different from the implementation agent.

**Acceptance Scenarios**:

1. **Given** a feature with one WP and two configured agents (e.g., Claude Code + GitHub Copilot), **When** the two-agent test runs, **Then** one agent implements and a different agent reviews
2. **Given** the review agent rejects the implementation, **When** the WP returns to "planned", **Then** the original implementation agent performs the rework (not the reviewer)
3. **Given** multiple agent combinations available, **When** tests are parameterized, **Then** each combination (Claude+Copilot, Claude+Gemini, Copilot+Codex, etc.) can be tested independently
4. **Given** a two-agent workflow completes successfully, **When** analyzing the logs, **Then** the implementation and review phases are clearly attributed to their respective agents

---

### User Story 3 - Three-Agent Parallel Execution (Priority: P2)

A test developer runs the three-agent test path to validate that spec-kitty can orchestrate multiple agents working in parallel on independent WPs.

**Why this priority**: Parallel execution is where the orchestrator provides maximum value (speed) but also maximum risk (race conditions, resource contention).

**Independent Test**: Can be validated by running a three-WP feature where all WPs are independent and verifying parallel execution occurs.

**Acceptance Scenarios**:

1. **Given** a feature with 3 independent WPs and 3 available agents, **When** the three-agent test runs, **Then** all 3 WPs execute in parallel (not sequentially)
2. **Given** parallel execution, **When** monitoring resource usage, **Then** container isolation prevents agents from interfering with each other
3. **Given** one agent fails during parallel execution, **When** the failure is detected, **Then** other agents continue their work and the failed WP is handled per fallback strategy
4. **Given** all 3 WPs complete successfully, **When** the test finishes, **Then** execution time is significantly less than 3x single-WP time

---

### User Story 4 - Containerized Agent Isolation (Priority: P1)

A test developer runs any test path knowing that agents are fully isolated in containers, preventing host system damage or uncontrolled network access.

**Why this priority**: Safety is non-negotiable. Without container isolation, adversarial testing could brick the host system or allow agents to access unintended resources.

**Independent Test**: Can be validated by attempting malicious operations from within a container and verifying they are blocked.

**Acceptance Scenarios**:

1. **Given** an agent running in a container, **When** it attempts to access files outside the designated worktree, **Then** the operation fails with permission denied
2. **Given** an agent running in a container, **When** it attempts to make network requests to non-allowlisted hosts, **Then** the operation fails or is blocked
3. **Given** an agent running in a container, **When** it consumes excessive resources (CPU, memory, disk), **Then** resource limits terminate the container
4. **Given** a container that crashes or hangs, **When** the timeout is exceeded, **Then** the container is forcibly terminated and the test captures the failure state
5. **Given** the container build process, **When** building test containers, **Then** the build is reproducible and documented for future sprint reuse

---

### User Story 5 - Adversarial Fault Injection (Priority: P2)

A test developer injects specific failures to validate spec-kitty's error handling and recovery mechanisms.

**Why this priority**: Red team testing requires deliberately breaking things. Fault injection validates that the orchestrator fails gracefully and recovers correctly.

**Independent Test**: Can be validated by running fault injection scenarios and verifying expected error handling behavior.

**Acceptance Scenarios**:

1. **Given** a running agent process, **When** the test kills the process mid-task (simulating crash), **Then** the orchestrator detects the failure and applies the configured fallback strategy
2. **Given** an agent execution, **When** the test injects a timeout by delaying responses, **Then** the orchestrator terminates the agent and retries or fails appropriately
3. **Given** a merge state file, **When** the test corrupts the JSON structure, **Then** the orchestrator detects corruption and reports it clearly
4. **Given** two WPs modifying the same file, **When** the test creates a git conflict scenario, **Then** the orchestrator pauses for manual resolution or applies auto-resolution for status files
5. **Given** the test simulates authentication failure, **When** an agent cannot authenticate, **Then** the fallback strategy activates (next agent or escalate to user)

---

### User Story 6 - Natural Failure Observation (Priority: P2)

A test developer runs extended test sessions to observe how agents naturally fail without injected faults, capturing real-world failure modes.

**Why this priority**: Injected faults test known failure modes. Natural failures reveal unknown failure modes that only emerge from real agent behavior.

**Independent Test**: Can be validated by running multiple real-agent workflows and analyzing captured logs for unexpected behaviors.

**Acceptance Scenarios**:

1. **Given** a real agent executing a complex WP, **When** the agent produces invalid output (malformed commits, syntax errors), **Then** the test captures the output and the orchestrator's response
2. **Given** extended test runs, **When** agents make unexpected decisions (wrong files, off-topic changes), **Then** all actions are logged for post-mortem analysis
3. **Given** any agent failure (natural or injected), **When** reviewing test results, **Then** comprehensive logs include: agent stdout/stderr, git state, WP status, timing, and container metrics
4. **Given** multiple test runs over time, **When** analyzing failure patterns, **Then** recurring failure modes can be identified and documented

---

### User Story 7 - Distribution Testing (Priority: P1)

A test developer validates that tests run against the shipped PyPI package, not the development branch, to catch packaging errors before users do.

**Why this priority**: The 0.10.8 catastrophe proved that testing development code creates a blind spot for packaging bugs. Distribution testing is mandatory.

**Independent Test**: Can be validated by verifying the test environment uses pip-installed spec-kitty from PyPI, not a local development install.

**Acceptance Scenarios**:

1. **Given** the test container build process, **When** spec-kitty is installed, **Then** it is installed from PyPI (not from local source or editable install)
2. **Given** a running test, **When** checking the spec-kitty installation, **Then** the version matches the target PyPI release
3. **Given** a test that passes with development code, **When** the same test runs against the PyPI package, **Then** any packaging-related failures are detected
4. **Given** a new spec-kitty release, **When** the test suite runs, **Then** it validates the actual shipped artifact that users will install

---

### User Story 8 - Modular Agent Configuration (Priority: P2)

A test developer configures which agents are available for testing without modifying test code, enabling easy extension as new agents are added.

**Why this priority**: The agent landscape evolves. New agents will be added, and the test framework must accommodate them without code changes.

**Independent Test**: Can be validated by adding a new agent to configuration and verifying tests discover and use it.

**Acceptance Scenarios**:

1. **Given** a YAML configuration file listing available agents with credentials, **When** tests run, **Then** only configured agents are used (unavailable agents are skipped)
2. **Given** a new agent is added to the configuration, **When** tests run, **Then** the new agent is automatically included in agent combination tests
3. **Given** an agent is removed from configuration, **When** tests run, **Then** tests requiring that agent are skipped gracefully
4. **Given** agent-specific configuration (timeouts, resource limits), **When** that agent runs, **Then** the specific configuration is applied

---

### Edge Cases

- What happens when zero agents are configured? (Test suite should fail fast with clear error)
- What happens when container build fails? (Clear error, no silent fallback to uncontained execution)
- What happens when PyPI package is unavailable? (Network error handling, retry with backoff)
- What happens when git operations fail inside container? (Capture state, fail test with diagnostics)
- What happens when agent rate limits are hit? (Respect rate limits, back off, potentially skip remaining tests)
- What happens when disk space runs out in container? (Resource limit triggers, container terminated, test fails cleanly)
- What happens when two tests run simultaneously? (Tests must be isolated, no shared state)
- What happens when credentials expire mid-test? (Detect auth failure, report clearly, skip remaining tests for that agent)

## Requirements *(mandatory)*

### Functional Requirements

**Container Infrastructure**

- **FR-001**: System MUST execute each agent invocation in an isolated container
- **FR-002**: System MUST enforce resource limits (CPU, memory, disk) on agent containers
- **FR-003**: System MUST enforce network policies that block non-allowlisted hosts
- **FR-004**: System MUST provide a documented, reproducible container build process
- **FR-005**: System MUST terminate containers that exceed configured timeouts
- **FR-006**: System MUST mount worktree directories as the only writable paths for agents

**Test Path Architecture**

- **FR-007**: System MUST implement a 1-agent test path for single-agent workflow validation
- **FR-008**: System MUST implement a 2-agent test path for cross-agent review validation
- **FR-009**: System MUST implement a 3-agent test path for parallel execution validation
- **FR-010**: System MUST allow any combination of available agents to be plugged into test paths
- **FR-011**: System MUST support parameterized tests for agent combinations

**Agent Management**

- **FR-012**: System MUST support all 9 CLI-capable agents: Claude Code, GitHub Codex, GitHub Copilot, Google Gemini CLI, Qwen Code, OpenCode, Kilocode, Augment Code, Cursor
- **FR-013**: System MUST detect which agents are installed and authenticated before test runs
- **FR-014**: System MUST skip tests gracefully when required agents are unavailable
- **FR-015**: System MUST read agent configuration from a YAML file (credentials, timeouts, limits)
- **FR-016**: System MUST support adding new agents via configuration without code changes

**Workflow Validation**

- **FR-017**: System MUST validate the implement → review workflow phase
- **FR-018**: System MUST handle review rejection cycles (WP sent back to "planned")
- **FR-019**: System MUST enforce maximum iteration limits on rejection cycles
- **FR-020**: System MUST verify WP lane transitions through the workflow

**Fault Injection**

- **FR-021**: System MUST support injecting process crashes (SIGKILL, SIGTERM)
- **FR-022**: System MUST support injecting timeouts (delayed responses)
- **FR-023**: System MUST support injecting corrupted state files
- **FR-024**: System MUST support injecting git conflicts
- **FR-025**: System MUST support injecting authentication failures
- **FR-026**: System MUST support injecting resource exhaustion scenarios

**Observability**

- **FR-027**: System MUST capture all agent stdout/stderr to log files
- **FR-028**: System MUST capture git state at key workflow points
- **FR-029**: System MUST capture WP status transitions with timestamps
- **FR-030**: System MUST capture container metrics (CPU, memory, network)
- **FR-031**: System MUST provide post-mortem analysis data for failed tests

**Distribution Testing**

- **FR-032**: System MUST install spec-kitty from PyPI in test containers (not development source)
- **FR-033**: System MUST verify spec-kitty version matches expected release
- **FR-034**: System MUST NOT set SPEC_KITTY_TEMPLATE_ROOT or similar development overrides

**Test Execution**

- **FR-035**: System MUST support manual trigger for test execution (not automatic on PR)
- **FR-036**: System MUST support running subsets of tests (by agent, by path, by scenario)
- **FR-037**: System MUST produce machine-readable test results (JUnit XML or similar)
- **FR-038**: System MUST produce human-readable summary reports

### Key Entities

- **TestPath**: A reusable workflow template (1-agent, 2-agent, 3-agent) that defines the structure of agent interactions without specifying which agents
- **AgentSlot**: A placeholder in a TestPath that is filled with a specific agent at runtime (e.g., "implementer", "reviewer", "parallel_worker_1")
- **AgentConfig**: Configuration for a specific agent including credentials reference, timeout, resource limits, and availability status
- **TestContainer**: An isolated container environment configured for a specific agent invocation with resource limits and network policies
- **FaultInjector**: A component that can inject specific failure conditions into agent execution or system state
- **TestRun**: A single execution of a TestPath with specific agents, capturing all inputs, outputs, and observations
- **WorkflowObservation**: Captured data from a test run including logs, state transitions, timing, and metrics

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 9 supported agents can execute the 1-agent test path when installed and authenticated
- **SC-002**: At least 5 different 2-agent combinations successfully complete cross-review workflows
- **SC-003**: 3-agent parallel execution completes in less than 2x the time of the slowest single-agent execution
- **SC-004**: Container isolation prevents 100% of attempted out-of-worktree file access
- **SC-005**: All injected faults (crash, timeout, corruption, conflict, auth failure) are correctly detected and handled
- **SC-006**: Test logs capture sufficient data to diagnose any failure without re-running the test
- **SC-007**: Adding a new agent requires only configuration changes, no code modifications
- **SC-008**: Distribution tests correctly identify packaging errors that functional tests miss
- **SC-009**: Test suite can run with as few as 1 available agent (graceful degradation)
- **SC-010**: Container build process is documented and reproducible across developer machines

## Assumptions

- At least one of the 9 supported agents is installed and authenticated on the test machine
- Docker is installed and the user has permission to build and run containers
- Network access is available for PyPI package installation
- Sufficient disk space is available for container images and test artifacts
- Git is installed and configured for worktree operations
- Test credentials are stored securely and not committed to the repository
- Spec-kitty releases are published to PyPI before distribution tests run against them

## Dependencies

- Docker Engine (for container isolation)
- pytest (test framework)
- spec-kitty >= 0.11.0 (the system under test)
- Agent CLIs installed by users (Claude Code, Copilot, etc.)
- GitHub Actions (for CI/CD integration of manual triggers)

## Out of Scope

- Automatic agent installation or credential provisioning
- Cost tracking or budget management for API calls
- Performance benchmarking beyond basic timing validation
- Testing spec-kitty commands outside implement/review (specify, plan, tasks, merge)
- Web dashboard integration testing
- Testing with agents beyond the 9 CLI-capable ones
- Automatic test scheduling (tests are manually triggered only)
