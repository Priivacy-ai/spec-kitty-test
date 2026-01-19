# Tasks: Agentic End-to-End Testing Framework

**Feature**: 004-agentic-end-to-end-testing-framework
**Generated**: 2026-01-19
**Total Subtasks**: 42
**Work Packages**: 10

## Subtask Index

| ID | Description | User Stories | Functional Reqs | Priority |
|----|-------------|--------------|-----------------|----------|
| T001 | Create tests/agentic/ directory structure | All | - | P0 |
| T002 | Create Dockerfile.base with spec-kitty from PyPI | US4, US7 | FR-001, FR-032 | P1 |
| T003 | Configure resource limits in Dockerfile (CPU, memory, disk) | US4 | FR-002 | P1 |
| T004 | Create docker-compose.yaml with internal network | US4 | FR-003 | P1 |
| T005 | Document container build process in README | US4 | FR-004 | P1 |
| T006 | Implement container timeout enforcement | US4 | FR-005 | P1 |
| T007 | Configure worktree mount as only writable path | US4 | FR-006 | P1 |
| T008 | Create agents.yaml schema with all 9 agents | US8 | FR-012, FR-015 | P1 |
| T009 | Implement agent detection (installed + authenticated) | US8 | FR-013 | P1 |
| T010 | Implement graceful skip for unavailable agents | US1, US8 | FR-014 | P1 |
| T011 | Support dynamic agent configuration loading | US8 | FR-016 | P2 |
| T012 | Create paths.yaml schema for test path definitions | US1-3 | FR-007, FR-008, FR-009 | P1 |
| T013 | Implement TestPath base class with agent slots | US1-3 | FR-010 | P1 |
| T014 | Implement parameterized test support for agent combos | US2-3 | FR-011 | P1 |
| T015 | Implement SingleAgentPath for 1-agent workflow | US1 | FR-007 | P1 |
| T016 | Implement CrossReviewPath for 2-agent workflow | US2 | FR-008 | P1 |
| T017 | Implement ParallelThreePath for 3-agent workflow | US3 | FR-009 | P2 |
| T018 | Implement workflow validation (implement → review) | US1-3 | FR-017 | P1 |
| T019 | Implement rejection cycle handling (back to planned) | US1-2 | FR-018 | P1 |
| T020 | Implement max iteration limits | US1-2 | FR-019 | P1 |
| T021 | Implement WP lane transition verification | US1-3 | FR-020 | P1 |
| T022 | Create container_fixtures.py with TestContainer mgmt | US4 | FR-001 | P1 |
| T023 | Create agent_fixtures.py for agent config loading | US8 | FR-015 | P1 |
| T024 | Create workflow_fixtures.py for test feature scaffolding | US1-3 | FR-017 | P1 |
| T025 | Implement process crash injection (SIGKILL, SIGTERM) | US5 | FR-021 | P2 |
| T026 | Implement timeout injection (delayed responses) | US5 | FR-022 | P2 |
| T027 | Implement state file corruption injection | US5 | FR-023 | P2 |
| T028 | Implement git conflict injection | US5 | FR-024 | P2 |
| T029 | Implement auth failure injection | US5 | FR-025 | P2 |
| T030 | Implement resource exhaustion injection | US5 | FR-026 | P2 |
| T031 | Implement stdout/stderr capture to log files | US6 | FR-027 | P1 |
| T032 | Implement git state capture at workflow points | US6 | FR-028 | P1 |
| T033 | Implement WP status transition logging with timestamps | US6 | FR-029 | P1 |
| T034 | Implement container metrics capture (CPU, mem, net) | US6 | FR-030 | P2 |
| T035 | Implement post-mortem data export for failures | US6 | FR-031 | P2 |
| T036 | Verify PyPI install (no SPEC_KITTY_TEMPLATE_ROOT) | US7 | FR-033, FR-034 | P1 |
| T037 | Implement version verification for spec-kitty | US7 | FR-033 | P1 |
| T038 | Add pytest markers for manual test triggering | - | FR-035 | P1 |
| T039 | Implement test filtering (by agent, path, scenario) | - | FR-036 | P1 |
| T040 | Generate JUnit XML test reports | - | FR-037 | P2 |
| T041 | Generate human-readable summary reports | - | FR-038 | P2 |
| T042 | Write test_single_agent.py test cases | US1 | - | P1 |
| T043 | Write test_cross_review.py test cases | US2 | - | P1 |
| T044 | Write test_parallel.py test cases | US3 | - | P2 |
| T045 | Write test_container_isolation.py test cases | US4 | - | P1 |
| T046 | Write test_fault_injection.py test cases | US5 | - | P2 |
| T047 | Write test_natural_failures.py test cases | US6 | - | P2 |
| T048 | Write test_distribution.py test cases | US7 | - | P1 |
| T049 | Write test_agent_config.py test cases | US8 | - | P2 |

## Work Package Summary

### WP01 - Foundation: Directory Structure and Configuration Schemas
**Phase**: Phase 1 - Infrastructure
**Subtasks**: T001, T008, T012
**Priority**: P0/P1
**Est. Lines**: 200-300

Creates the base directory structure under `tests/agentic/` and defines the YAML configuration schemas for agents and test paths. This is the foundation that all other work packages depend on.

---

### WP02 - Container Infrastructure: Dockerfile and Docker Compose
**Phase**: Phase 1 - Infrastructure
**Subtasks**: T002, T003, T004, T005, T007
**Priority**: P1
**Est. Lines**: 150-250

Creates the Docker infrastructure: base image with spec-kitty from PyPI, resource limits, internal network, worktree mounts, and build documentation. Implements FR-001 through FR-006 except timeout (in WP03).

---

### WP03 - Core Fixtures: Container and Agent Lifecycle
**Phase**: Phase 2 - Fixtures
**Subtasks**: T006, T022, T023, T009, T010
**Priority**: P1
**Est. Lines**: 350-450

Implements the pytest fixtures for container lifecycle management and agent configuration loading. Includes timeout enforcement, agent detection, and graceful skip logic.

---

### WP04 - Test Path Framework: Base Class and Path Definitions
**Phase**: Phase 2 - Fixtures
**Subtasks**: T013, T014, T015
**Priority**: P1
**Est. Lines**: 250-350

Creates the TestPath abstraction, parameterized test support, and the SingleAgentPath implementation. Establishes the pattern for agent slot mapping.

---

### WP05 - Workflow Engine: State Transitions and Validation
**Phase**: Phase 2 - Fixtures
**Subtasks**: T018, T019, T020, T021, T024
**Priority**: P1
**Est. Lines**: 300-400

Implements the workflow validation logic: implement → review transitions, rejection cycle handling, max iterations, and lane transition verification. Includes workflow_fixtures.py.

---

### WP06 - Observability: Logging and Metrics Capture
**Phase**: Phase 2 - Fixtures
**Subtasks**: T031, T032, T033, T034, T035
**Priority**: P1/P2
**Est. Lines**: 250-350

Implements comprehensive observability: stdout/stderr capture, git state snapshots, WP transition logging, container metrics, and post-mortem data export.

---

### WP07 - Multi-Agent Paths: Cross-Review and Parallel
**Phase**: Phase 3 - Test Paths
**Subtasks**: T016, T017
**Priority**: P1/P2
**Est. Lines**: 200-300

Extends the test path framework with CrossReviewPath (2-agent) and ParallelThreePath (3-agent) implementations.

---

### WP08 - Fault Injection: Adversarial Testing Components
**Phase**: Phase 3 - Fault Injection
**Subtasks**: T025, T026, T027, T028, T029, T030
**Priority**: P2
**Est. Lines**: 350-450

Implements the full fault injection suite: process crashes, timeouts, file corruption, git conflicts, auth failures, and resource exhaustion scenarios.

---

### WP09 - Core Tests: Single-Agent, Distribution, and Isolation
**Phase**: Phase 4 - Test Implementation
**Subtasks**: T036, T037, T042, T045, T048
**Priority**: P1
**Est. Lines**: 400-500

Implements the P1 test files: test_single_agent.py, test_distribution.py (PyPI validation), and test_container_isolation.py.

---

### WP10 - Extended Tests and Reporting
**Phase**: Phase 4 - Test Implementation
**Subtasks**: T011, T038, T039, T040, T041, T043, T044, T046, T047, T049
**Priority**: P2
**Est. Lines**: 500-600

Implements remaining tests (cross-review, parallel, fault injection, natural failures, agent config) plus test execution controls (markers, filtering, reporting).

---

## Dependency Graph

```
WP01 ──┬──► WP02 ──┬──► WP03 ──┬──► WP04 ──► WP07
       │          │           │
       │          │           └──► WP05 ──► WP09
       │          │                    │
       │          │                    └──► WP06
       │          │
       │          └──► WP08
       │
       └──────────────────────────────────► WP10
```

**Critical Path**: WP01 → WP02 → WP03 → WP05 → WP09

## Notes

- WP01-WP05 form the critical path and must be completed in order
- WP06-WP10 can be parallelized once WP03-WP05 are complete
- P1 work packages should be prioritized for initial implementation
- WP10 is the largest and may be split further during implementation
