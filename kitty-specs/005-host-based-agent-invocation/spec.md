# Feature Specification: Host-Based Agent Invocation for Agentic Tests

**Feature Branch**: `005-host-based-agent-invocation`
**Created**: 2026-01-19
**Status**: Draft
**Input**: Build the missing infrastructure to actually invoke real AI coding agents and execute implement→review workflows

## Context: The Gap This Fills

Feature 004 created comprehensive test scaffolding for agentic E2E testing:
- Test paths (single-agent, cross-review, parallel)
- Fixtures and configuration
- 104 test cases

**The problem**: When tests run, **100% of agent workflow tests are skipped** because:
- No infrastructure exists to actually invoke agents
- Agent "availability" checks pass/fail but never lead to real execution
- The `execute()` methods on test paths are abstract stubs

**This feature fills that gap** by building the actual agent invocation layer that makes those tests run for real.

## User Scenarios & Testing

### User Story 1 - Single Agent Workflow Execution (Priority: P1)

A developer runs the agentic test suite and watches a single available agent (e.g., Claude Code) actually execute an implement→review→done workflow on a test work package.

**Why this priority**: This is the minimum viable proof that the test framework works. If one agent can complete one workflow, the architecture is validated.

**Independent Test**: Run `pytest tests/agentic/tests/test_single_agent.py -k "claude" -v` and observe:
- Claude Code CLI is invoked with a real prompt
- Agent produces output (commits, file changes)
- WP transitions through lanes
- Test passes or fails based on actual results

**Acceptance Scenarios**:

1. **Given** Claude Code is installed and authenticated on the host, **When** the single-agent test runs, **Then** the agent is invoked via subprocess with the implementation prompt and its stdout/stderr is captured.

2. **Given** the agent completes implementation, **When** the same agent runs review, **Then** the review prompt is sent and the agent's approval/rejection is parsed from output.

3. **Given** the agent approves the implementation, **When** the workflow completes, **Then** the test reports PASSED with timing and observation data.

4. **Given** the agent rejects the implementation, **When** max iterations not exceeded, **Then** the agent is re-invoked for rework.

---

### User Story 2 - Runtime Agent Discovery (Priority: P1)

The test framework detects at runtime which agents are actually installed and authenticated, without hardcoding agent names in tests.

**Why this priority**: The test paths are designed for N agents (1, 2, or 3+). Discovery must work for paths to select agents dynamically.

**Independent Test**: Run agent discovery and verify it correctly identifies installed agents on this machine.

**Acceptance Scenarios**:

1. **Given** Claude Code CLI is installed (`claude --version` succeeds), **When** discovery runs, **Then** "claude-code" appears in available agents list.

2. **Given** an agent CLI is not installed, **When** discovery runs, **Then** that agent is excluded from available agents.

3. **Given** an agent is installed but not authenticated (auth check fails), **When** discovery runs, **Then** that agent is marked unavailable with reason.

4. **Given** multiple agents are available, **When** a 2-agent test path runs, **Then** it selects any 2 available agents (not hardcoded pair).

---

### User Story 3 - Cross-Review with Two Agents (Priority: P2)

When 2+ agents are available, a cross-review test runs where Agent A implements and Agent B reviews.

**Why this priority**: Validates multi-agent coordination after single-agent works.

**Independent Test**: With 2 agents available, run `pytest tests/agentic/tests/test_cross_review.py -v` and observe both agents being invoked.

**Acceptance Scenarios**:

1. **Given** 2 agents are available, **When** cross-review test runs, **Then** implementation invokes Agent A and review invokes Agent B.

2. **Given** Agent B rejects, **When** rework is needed, **Then** Agent A (original implementer) is re-invoked.

3. **Given** only 1 agent is available, **When** cross-review test starts, **Then** test is skipped with clear message.

---

### User Story 4 - Parallel Execution with Three Agents (Priority: P3)

When 3+ agents are available, parallel tests run 3 WPs simultaneously with different agents.

**Why this priority**: Advanced scenario after single and cross-review work.

**Independent Test**: With 3 agents available, run parallel tests and verify concurrent execution.

**Acceptance Scenarios**:

1. **Given** 3 agents are available, **When** parallel test runs, **Then** 3 agent subprocesses start within 30 seconds of each other.

2. **Given** parallel execution completes, **When** measuring timing, **Then** total time is less than 2x the slowest individual agent.

---

### User Story 5 - Output Capture and Observability (Priority: P2)

All agent invocations capture stdout, stderr, exit codes, timing, and git state for debugging and analysis.

**Why this priority**: Essential for understanding failures and validating behavior.

**Independent Test**: Run any agent test and verify comprehensive logs are written.

**Acceptance Scenarios**:

1. **Given** an agent is invoked, **When** it produces output, **Then** stdout and stderr are captured to the test run's observations.

2. **Given** an agent times out, **When** timeout occurs, **Then** the process is killed and timeout is recorded.

3. **Given** a test completes, **When** reviewing results, **Then** git state (branch, last commit, dirty files) is captured.

---

### Edge Cases

- What happens when an agent hangs indefinitely? Timeout kills it after configured limit.
- What happens when agent output is malformed/unparseable? Record raw output, mark as parse failure.
- What happens when agent crashes mid-execution? Capture exit code, stderr, mark as crash.
- What happens when git worktree is in conflicted state? Abort or record conflict.
- What happens when credentials expire mid-test? Auth failure recorded, test fails gracefully.

## Requirements

### Functional Requirements

- **FR-001**: System MUST detect installed agent CLIs by checking if their command exists in PATH
- **FR-002**: System MUST verify agent authentication by running a lightweight auth-check command for each agent type
- **FR-003**: System MUST invoke agents via subprocess with configurable timeout (default: 30 minutes per invocation)
- **FR-004**: System MUST capture agent stdout, stderr, and exit code for every invocation
- **FR-005**: System MUST kill agent processes that exceed timeout and record timeout as failure reason
- **FR-006**: System MUST support different invocation patterns per agent (stdin prompt, file prompt, CLI argument prompt)
- **FR-007**: System MUST parse agent output to detect success/failure/approval/rejection signals
- **FR-008**: System MUST create isolated git worktrees for each test run to prevent interference
- **FR-009**: System MUST pass the worktree path to agents so they operate in the correct directory
- **FR-010**: System MUST record timing for each invocation (start time, end time, duration)
- **FR-011**: System MUST support the `same_as` constraint (single-agent: same agent implements and reviews)
- **FR-012**: System MUST support the `different_from` constraint (cross-review: different agents for implement vs review)
- **FR-013**: System MUST clean up agent processes on test teardown (no orphan processes)
- **FR-014**: System MUST work without Docker (direct host invocation)

### Key Entities

- **AgentInvoker**: Responsible for starting agent processes, passing prompts, capturing output
- **AgentProcess**: Represents a running agent subprocess with methods to wait, kill, get output
- **InvocationResult**: Contains stdout, stderr, exit_code, duration, parsed_outcome
- **WorktreeManager**: Creates and cleans up isolated git worktrees for test runs

## Success Criteria

### Measurable Outcomes

- **SC-001**: At least one agent workflow test transitions from SKIPPED to PASSED when that agent is installed
- **SC-002**: Agent discovery correctly identifies 100% of installed agents on the test machine
- **SC-003**: Agent invocation captures complete stdout/stderr (no truncation under 1MB)
- **SC-004**: Timeout enforcement kills hung processes within 5 seconds of timeout
- **SC-005**: Test runs produce observation logs that include timing, output, and git state
- **SC-006**: No orphan agent processes remain after test suite completes
- **SC-007**: Cross-review tests use two different agents when 2+ are available
