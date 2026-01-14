# Data Model: Critical Test Coverage for v0.12.0

## Overview

This document defines the entities used in the test suite implementation. These are conceptual entities that organize the 96 tests across parallel development tracks.

---

## Core Entities

### Test Suite

**Definition**: A collection of related test cases validating a specific aspect of functionality.

**Attributes**:
- `suite_name`: string - Descriptive name (e.g., "Suite 1: Worktree Creation")
- `test_count`: integer - Number of tests in suite
- `test_file`: Path - File containing test implementations
- `priority`: enum(CRITICAL, HIGH, MEDIUM) - Release blocking priority
- `status`: enum(not_started, in_progress, complete) - Implementation progress
- `pass_rate`: float (0.0-1.0) - Percentage of tests passing

**Relationships**:
- Contains many `Test Case` (composition)
- Part of one `Test Phase`
- Validates one or more `Implementation Code` references

**Examples**:
```
Suite 1: Worktree Creation
├─ test_count: 8
├─ test_file: tests/functional/test_sparse_checkout_infrastructure.py
├─ priority: CRITICAL
├─ validates: implement.py:596-642
└─ contains: [test_sparse_checkout_excludes_kitty_specs, test_sparse_checkout_file_created, ...]

Suite 6: Edge Cases
├─ test_count: 8
├─ test_file: tests/functional/test_sparse_checkout_infrastructure.py
├─ priority: CRITICAL
├─ validates: implement.py:596-642, tasks.py:432-475, workflow.py:236-264
└─ contains: [test_corrupted_sparse_checkout_recovery, test_permission_errors_clear_message, ...]
```

---

### Test Case

**Definition**: An individual test function validating one specific behavior.

**Attributes**:
- `test_name`: string - Function name (e.g., "test_sparse_checkout_excludes_kitty_specs")
- `docstring`: string - Multi-line description (what tested, why matters, references)
- `implementation_reference`: string - Code location validated (e.g., "implement.py:596-642")
- `expected_behavior`: string - What should happen when test passes
- `assertion_count`: integer - Number of assertions in test
- `execution_time`: float - Seconds to execute

**Relationships**:
- Part of one `Test Suite`
- Validates one or more `Functional Requirement`
- Uses one or more `Test Fixture`

**State Transitions**:
```
not_implemented → implemented → passing → failing (if bug found) → passing (after fix)
```

**Examples**:
```python
test_sparse_checkout_excludes_kitty_specs
├─ suite: Suite 1 (Worktree Creation)
├─ validates: FR-001 (Sparse-Checkout Infrastructure Test Suite)
├─ uses_fixtures: [temp_project_dir, init_spec_kitty_project]
├─ implementation_reference: "implement.py:596-642"
├─ assertion_count: 3
│   ├─ assert not (worktree / 'kitty-specs').exists()
│   ├─ assert (main_repo / 'kitty-specs').exists()
│   └─ assert git ls-files output empty for kitty-specs/
└─ execution_time: 2.1 seconds

test_documentation_mission_loads_from_package (Distribution Test subtype)
├─ suite: Test Documentation Mission Distribution
├─ validates: FR-002 (Documentation Mission Distribution Test Suite)
├─ uses_fixtures: [clean_environment]
├─ environment_clean: true (SPEC_KITTY_TEMPLATE_ROOT removed)
├─ package_mode: true (tests pip package, not local)
├─ simulates_pypi_user: true
└─ would_catch: Issues #62-64 (path-based divergence)
```

---

### Test Fixture

**Definition**: Reusable test infrastructure component providing setup, resources, or utilities.

**Attributes**:
- `fixture_name`: string - Fixture identifier (e.g., "spec_kitty_repo_root")
- `scope`: enum(session, function, class, module) - Lifespan of fixture instance
- `cleanup_required`: boolean - Whether fixture must clean up resources
- `dependencies`: list[string] - Other fixtures this fixture depends on
- `location`: Path - File where fixture is defined

**Relationships**:
- Defined in one location (typically `conftest.py`)
- Used by many `Test Case`
- May depend on other `Test Fixture` (fixture chains)

**Examples**:
```python
spec_kitty_repo_root (session scope)
├─ location: tests/conftest.py
├─ scope: session (created once, reused by all tests)
├─ cleanup_required: false
├─ dependencies: []
├─ returns: Path to ~/Code/spec-kitty
├─ fallback: Checks SPEC_KITTY_REPO env var
└─ validates: Repository exists with src/specify_cli/ directory

temp_project_dir (function scope)
├─ location: tests/conftest.py (or test class)
├─ scope: function (new directory for each test)
├─ cleanup_required: true (via tempfile.TemporaryDirectory)
├─ dependencies: []
├─ returns: Path to temporary directory
└─ cleanup: Automatic on function exit

init_spec_kitty_project (function scope, factory pattern)
├─ location: test class or conftest.py
├─ scope: function
├─ cleanup_required: false (handled by temp_project_dir)
├─ dependencies: [spec_kitty_repo_root, temp_project_dir]
├─ returns: Factory function (callable)
├─ usage: project = init_spec_kitty_project("test-project")
├─ sets_env: SPEC_KITTY_TEMPLATE_ROOT (for functional tests)
└─ runs_command: spec-kitty init with auto-accept

clean_environment (function scope)
├─ location: tests/distribution/conftest.py
├─ scope: function (new clean env for each distribution test)
├─ cleanup_required: false
├─ dependencies: []
├─ returns: dict (environment variables)
├─ removes: [SPEC_KITTY_TEMPLATE_ROOT, SPEC_KITTY_REPO, SPEC_KITTY_*]
├─ keeps: [SPEC_KITTY_API_KEY]
└─ purpose: Simulate PyPI user environment (no development overrides)
```

---

### Implementation Code (Read-Only Reference)

**Definition**: Source code in spec-kitty repository that tests validate. Not created by tests, only referenced for understanding behavior.

**Attributes**:
- `file_path`: string - Full path to file (e.g., "~/Code/spec-kitty/src/specify_cli/cli/commands/implement.py")
- `line_range`: string - Line numbers (e.g., "596-642")
- `function_name`: string - Function/method being validated
- `behavior`: string - Description of what code does
- `version`: string - spec-kitty version (e.g., "v0.12.0")

**Relationships**:
- Tested by many `Test Case`
- Located in spec-kitty repository (external to test suite)
- Part of `Feature Release` (v0.12.0)

**Examples**:
```
implement.py:596-642
├─ function: create_feature_worktree
├─ behavior: Configures sparse-checkout when creating worktree
│   ├─ Sets git config core.sparseCheckout=true
│   ├─ Sets git config core.sparseCheckoutCone=false
│   ├─ Writes patterns to .git/info/sparse-checkout
│   │   ├─ /* (include all root files)
│   │   ├─ !/kitty-specs/ (exclude directory)
│   │   └─ !/kitty-specs/** (exclude contents)
│   └─ Applies via git read-tree -mu HEAD
├─ version: v0.12.0
├─ tested_by: Suite 1 (8 tests), Suite 5 (6 tests), Suite 6 (3 tests)
└─ risk: CRITICAL (data corruption if bugs, blocks release)

tasks.py:432-475
├─ function: move_task (auto-commit logic)
├─ behavior: Commits WP file changes to main branch after move
│   ├─ Gets main repo root via _get_main_repo_root
│   ├─ Commits specific file: git commit <wp_file> -m <msg>
│   ├─ Message format: "chore: Move {wp_id} to {lane} [{agent}]"
│   └─ Works even if other files in main are modified
├─ version: v0.12.0
├─ tested_by: Suite 3 (10 tests), Suite 4 (8 tests)
└─ risk: HIGH (synchronization breaks if auto-commit fails)
```

---

### Distribution Test (Test Case Subtype)

**Definition**: Specialized test case that validates package behavior without development environment overrides.

**Attributes** (inherited + specialized):
- All `Test Case` attributes, plus:
- `environment_clean`: boolean - MUST be true (SPEC_KITTY_TEMPLATE_ROOT removed)
- `package_mode`: boolean - Tests pip package, not local repo
- `template_source`: enum(package, local_repo) - MUST be "package"
- `simulates_pypi_user`: boolean - MUST be true

**Invariants**:
- `environment_clean` MUST be true
- SPEC_KITTY_TEMPLATE_ROOT MUST NOT be set during test execution
- Templates MUST load via importlib.resources (from package)
- Test MUST fail if templates not in package

**Purpose**: Prevent repeat of Issues #62-64 (local tests pass with template bypass, PyPI users fail without bypass)

**Examples**:
```python
test_documentation_mission_loads_from_package
├─ type: Distribution Test
├─ environment_clean: true ✓
├─ package_mode: true ✓
├─ template_source: package ✓
├─ simulates_pypi_user: true ✓
├─ uses_fixture: clean_environment (removes SPEC_KITTY_TEMPLATE_ROOT)
├─ validates: Templates accessible via importlib.resources
├─ would_catch: Issues #62-64 (if templates missing from package)
└─ failure_meaning: Template bundling broken, DO NOT SHIP

test_jsdoc_generator_from_package
├─ type: Distribution Test
├─ environment_clean: true ✓
├─ validates: JSDoc generator accessible from installed package
├─ checks: Generator templates not leaked from local repo
└─ ensures: PyPI users can use JSDoc generator
```

---

### Test Phase

**Definition**: High-level grouping of test suites with release-blocking implications.

**Attributes**:
- `phase_number`: integer (1 or 2)
- `phase_name`: string (e.g., "Phase 1: Critical - Blocking Release")
- `test_count`: integer - Total tests in phase
- `priority`: enum(CRITICAL, HIGH, MEDIUM)
- `estimated_effort`: string (e.g., "13-19 hours")
- `completion_criteria`: string - What defines "done"
- `blocks_release`: boolean - Whether v0.12.0 waits for this phase

**Relationships**:
- Contains many `Test Suite`
- Has `Completion Criteria` (quality gate)
- May block `Feature Release` (v0.12.0)

**Examples**:
```
Phase 1: Critical (Blocking v0.12.0)
├─ phase_number: 1
├─ test_count: 96
│   ├─ Track 1: Sparse-checkout (46 tests)
│   │   ├─ Suite 1: Worktree Creation (8)
│   │   ├─ Suite 2: Path Resolution (6)
│   │   ├─ Suite 3: Auto-Commit (10)
│   │   ├─ Suite 4: Multi-Agent (8)
│   │   ├─ Suite 5: Merge (6)
│   │   └─ Suite 6: Edge Cases (8)
│   └─ Track 2: Documentation Mission (50 tests)
│       ├─ test_doc_generators_distribution.py (15)
│       ├─ test_documentation_mission_distribution.py (20)
│       └─ test_documentation_mission_end_to_end.py (15)
├─ priority: CRITICAL
├─ estimated_effort: "13-19 hours"
├─ completion_criteria:
│   ├─ All 96 tests passing (46/46 + 50/50)
│   ├─ Zero xfails, zero skips
│   ├─ All spec-kitty bugs found during testing fixed
│   ├─ Test execution <15 minutes total
│   └─ ≥95% overall pass rate (≥519/546 total tests)
└─ blocks_release: true (v0.12.0 cannot ship without Phase 1 complete)

Phase 2: Additional Coverage (Post-Release)
├─ phase_number: 2
├─ test_count: 27
│   ├─ Workflow improvements (18 tests)
│   ├─ Migration tests (9 tests)
│   └─ Cross-platform tests (5 tests - not in original count)
├─ priority: MEDIUM
├─ blocks_release: false (can defer to v0.12.1)
└─ rationale: Nice-to-have, not critical for initial release
```

---

## Test Organization Hierarchy

```
Test Phase (Phase 1: Critical)
└─── Test Track (Sparse-Checkout or Documentation)
     └─── Test Suite (Suite 1, Suite 2, etc.)
          └─── Test Class (TestWorktreeCreation, TestAutoCommitSynchronization)
               └─── Test Case (test_sparse_checkout_excludes_kitty_specs)
                    ├─── uses Test Fixture (temp_project_dir, init_spec_kitty_project)
                    └─── validates Implementation Code (implement.py:596-642)
```

**Example Instantiation**:
```
Phase 1: Critical
├─ Track 1: Sparse-Checkout (46 tests)
│  └─ Suite 1: Worktree Creation (8 tests)
│     └─ TestWorktreeCreation class
│        ├─ test_sparse_checkout_excludes_kitty_specs
│        │  ├─ uses: temp_project_dir, init_spec_kitty_project
│        │  └─ validates: implement.py:596-642
│        ├─ test_sparse_checkout_file_created
│        │  ├─ uses: temp_project_dir, init_spec_kitty_project
│        │  └─ validates: implement.py:601-607
│        └─ ... (6 more tests)
└─ Track 2: Documentation Mission (50 tests)
   └─ test_documentation_mission_distribution.py (20 tests)
      └─ TestMissionLoading class
         ├─ test_documentation_mission_loads_from_package (Distribution Test)
         │  ├─ uses: clean_environment
         │  ├─ validates: missions/documentation/mission.yaml
         │  └─ environment_clean: true, package_mode: true
         └─ ... (19 more tests)
```

---

## Data Flow

### Test Execution Flow
```
1. Test Developer selects Test Suite (e.g., Suite 1: Worktree Creation)
2. pytest discovers Test Cases in TestWorktreeCreation class
3. pytest creates Test Fixtures (temp_project_dir, init_spec_kitty_project)
4. Test Case executes:
   a. Invokes spec-kitty CLI command (subprocess.run)
   b. Validates outcome against expected behavior
   c. References Implementation Code location in docstring
5. Test passes → continue or Test fails → investigate:
   a. Determine: spec-kitty bug or test bug?
   b. If spec-kitty bug: Document in findings/, fix in ~/Code/spec-kitty
   c. If test bug: Fix test, ensure validates correct behavior
6. Test Fixtures cleaned up automatically
7. Next Test Case executes (repeat steps 3-6)
```

### Parallel Track Flow
```
┌─────────────────────────────┐   ┌─────────────────────────────┐
│ Track 1: Sparse-Checkout    │   │ Track 2: Documentation      │
│ Developer/Agent A           │   │ Developer/Agent B           │
├─────────────────────────────┤   ├─────────────────────────────┤
│ 1. Implement Suite 6 (Edge) │   │ 1. Implement test_doc_gen   │
│ 2. Tests fail → find bug    │   │ 2. Tests fail → find bug    │
│ 3. Document in findings/    │◄──┤ 3. Document in findings/    │
│ 4. Fix in ~/Code/spec-kitty │──►│ 4. Coordinate on fix        │
│ 5. Re-run tests → pass      │   │ 5. Re-run tests → pass      │
│ 6. Continue Suite 4         │   │ 6. Continue test_doc_mission│
└─────────────────────────────┘   └─────────────────────────────┘
              │                                 │
              └────────► Synchronization ◄──────┘
                        - findings/test-infrastructure/v0.12.0-bugs-found.md
                        - ~/Code/spec-kitty (coordinate fixes)
                        - Daily sync meetings
```

---

## Entity Cardinality

```
Test Phase 1 : N Test Suite (1 phase has many suites)
Test Suite 1 : N Test Case (1 suite has many tests)
Test Case N : M Test Fixture (tests use multiple fixtures, fixtures used by multiple tests)
Test Case 1 : 1 Implementation Code (test validates one code location, but code tested by many tests)
Test Suite 1 : N Implementation Code (suite may validate multiple code locations)
Test Phase 1 : 1 Feature Release (Phase 1 blocks v0.12.0, Phase 2 doesn't)
```

---

## Validation Rules

### Test Suite Rules
- `test_count` MUST equal number of test functions in class
- `pass_rate` MUST be between 0.0 and 1.0
- `priority` MUST be CRITICAL for Phase 1 suites
- Suite MUST have at least 1 Test Case

### Test Case Rules
- `test_name` MUST start with "test_"
- `docstring` MUST include: what tested, why matters, implementation reference
- Distribution Tests MUST use clean_environment fixture
- Distribution Tests MUST NOT set SPEC_KITTY_TEMPLATE_ROOT
- `assertion_count` MUST be ≥1

### Test Fixture Rules
- Function-scoped fixtures MUST clean up resources
- Session-scoped fixtures MAY leave resources (cleaned at session end)
- Distribution test fixtures MUST remove SPEC_KITTY_TEMPLATE_ROOT

### Test Phase Rules
- Phase 1 `blocks_release` MUST be true
- Phase 1 `completion_criteria` MUST include "All tests passing"
- Phase 1 `completion_criteria` MUST include "Zero xfails"