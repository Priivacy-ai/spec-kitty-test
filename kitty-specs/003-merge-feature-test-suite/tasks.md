# Work Packages: Merge Feature Test Suite

**Inputs**: Design documents from `kitty-specs/003-merge-feature-test-suite/`
**Prerequisites**: spec.md (user stories, 32 FRs), existing test patterns in tests/functional/

**Tests**: This feature IS the test suite - all work is test implementation.

**Organization**: 45 subtasks (`T001`-`T045`) rolled into 8 work packages (`WP01`-`WP08`). Each WP maps to a test module or fixture group.

**Prompt Files**: Each work package has a matching prompt file in `tasks/` with detailed implementation guidance.

---

## Work Package WP01: Test Infrastructure & Fixtures (Priority: P0)

**Goal**: Create shared fixtures for multi-WP feature creation, merge state simulation, and conflict scenarios.
**Independent Test**: `pytest tests/functional/test_merge_fixtures.py -v` passes; fixtures are importable and functional.
**Prompt**: `tasks/WP01-test-infrastructure-fixtures.md`
**Estimated Size**: ~450 lines

### Included Subtasks
- [x] T001 [P] Create `tests/functional/test_merge_fixtures.py` module structure with docstrings
- [x] T002 Create `MergeTestFeature` fixture class for multi-WP feature scaffolding
- [x] T003 Create `WPFixture` dataclass for configurable work package state
- [x] T004 [P] Create `MergeStateFixture` helper for `.kittify/merge-state.json` manipulation
- [x] T005 [P] Create `ConflictFixture` helper for status file and code file conflicts
- [x] T006 Implement `create_test_feature()` fixture factory with configurable WP count and states
- [x] T007 Add cleanup utilities for test isolation (worktree/branch removal)

### Implementation Notes
1. Follow existing `spec_kitty_project` fixture pattern from `conftest.py`
2. Fixtures must support both functional and distribution test modes
3. Each fixture should be session-scoped where possible for performance
4. Use `tmp_path` for test isolation per pytest conventions

### Parallel Opportunities
- T001, T004, T005 can proceed in parallel (independent modules)
- T002, T003 define core classes needed by T006

### Dependencies
- None (foundation package)

### Risks & Mitigations
- Risk: Fixture complexity → Start simple, add features incrementally
- Risk: Test isolation failures → Use unique tmp directories per test

---

## Work Package WP02: Pre-flight Validation Tests (Priority: P1) 🎯 MVP

**Goal**: Implement tests for User Story 1 (FR-005 to FR-008) - pre-flight validation.
**Independent Test**: `pytest tests/functional/test_merge_preflight.py -v` validates dirty worktrees, diverged branches, and aggregated error reporting.
**Prompt**: `tasks/WP02-preflight-validation-tests.md`
**Estimated Size**: ~400 lines

### Included Subtasks
- [x] T008 Create `tests/functional/test_merge_preflight.py` module
- [x] T009 Test: dirty worktrees are detected and reported (FR-005)
- [x] T010 Test: multiple dirty worktrees reported together, not one-at-a-time (FR-007)
- [x] T011 Test: target branch divergence is detected (FR-006)
- [x] T012 Test: pre-flight failure exits non-zero without branch modifications (FR-008)
- [x] T013 Test: clean worktrees with up-to-date target passes pre-flight
- [x] T014 Test: deleted worktree with existing branch detected

### Implementation Notes
1. Create feature with 3 WPs using `create_test_feature()` fixture
2. Modify worktree state (add uncommitted files) to trigger dirty detection
3. Verify merge command output contains all WP statuses
4. Assert exit code and branch state before/after

### Parallel Opportunities
- T009-T014 are independent test functions, can be written in parallel

### Dependencies
- Depends on WP01 (fixtures)

### Risks & Mitigations
- Risk: Git state manipulation complexity → Use subprocess for explicit git commands

---

## Work Package WP03: Conflict Forecast Tests (Priority: P2)

**Goal**: Implement tests for User Story 2 (FR-009 to FR-012) - conflict prediction in dry-run.
**Independent Test**: `pytest tests/functional/test_merge_forecast.py -v` validates conflict prediction accuracy.
**Prompt**: `tasks/WP03-conflict-forecast-tests.md`
**Estimated Size**: ~380 lines

### Included Subtasks
- [x] T015 Create `tests/functional/test_merge_forecast.py` module
- [x] T016 Test: overlapping file modifications predicted as conflicts (FR-009)
- [x] T017 Test: non-overlapping modifications show no conflicts
- [x] T018 Test: conflicts grouped by file in dry-run output (FR-010)
- [ ] T019 Test: merge order displayed in dry-run output (FR-011)
- [ ] T020 Test: status files marked as auto-resolvable in predictions (FR-012)

### Implementation Notes
1. Create WPs that modify the same file (e.g., `conftest.py`)
2. Run `spec-kitty merge --dry-run` and parse output
3. Verify file paths and WP IDs in conflict predictions
4. Create status file conflicts to verify auto-resolvable marking

### Parallel Opportunities
- All test functions (T016-T020) are independent

### Dependencies
- Depends on WP01 (fixtures)

### Risks & Mitigations
- Risk: Output format changes → Use flexible regex/contains assertions

---

## Work Package WP04: Smart Merge Ordering Tests (Priority: P2)

**Goal**: Implement tests for User Story 3 (FR-013 to FR-016) - dependency-based merge ordering.
**Independent Test**: `pytest tests/functional/test_merge_ordering.py -v` validates topological sort and cycle detection.
**Prompt**: `tasks/WP04-smart-merge-ordering-tests.md`
**Estimated Size**: ~420 lines

### Included Subtasks
- [ ] T021 Create `tests/functional/test_merge_ordering.py` module
- [ ] T022 Test: WP with dependency merges after its dependency (FR-014)
- [ ] T023 Test: diamond dependency pattern merges in correct order
- [ ] T024 Test: circular dependency detected with clear error (FR-015)
- [ ] T025 Test: no dependencies falls back to numerical order (FR-016)
- [ ] T026 Test: frontmatter `dependencies: []` parsed correctly (FR-013)
- [ ] T027 Test: multiple parallel dependency chains respected

### Implementation Notes
1. Create WP frontmatter with `dependencies: ["WP01"]` declarations
2. Verify merge log shows correct WP sequence
3. Create intentional cycle (WP01→WP02→WP01) and verify error
4. Test with no dependencies to verify numerical fallback

### Parallel Opportunities
- T022-T027 are independent test scenarios

### Dependencies
- Depends on WP01 (fixtures)

### Risks & Mitigations
- Risk: Frontmatter parsing differences → Use exact YAML format from spec-kitty

---

## Work Package WP05: Status File Auto-Resolution Tests (Priority: P2)

**Goal**: Implement tests for User Story 4 (FR-017 to FR-021) - automatic status file conflict resolution.
**Independent Test**: `pytest tests/functional/test_merge_status_resolution.py -v` validates lane, checkbox, and history conflict resolution.
**Prompt**: `tasks/WP05-status-file-auto-resolution-tests.md`
**Estimated Size**: ~480 lines

### Included Subtasks
- [ ] T028 Create `tests/functional/test_merge_status_resolution.py` module
- [ ] T029 Test: lane conflicts resolve by "more done" wins (FR-017)
- [ ] T030 Test: checkbox conflicts resolve by preferring `[x]` (FR-018)
- [ ] T031 Test: history arrays merge chronologically (FR-019)
- [ ] T032 Test: code file conflicts NOT auto-resolved (FR-020)
- [ ] T033 Test: only `kitty-specs/**/tasks/*.md` patterns auto-resolved (FR-021)
- [ ] T034 Test: mixed status and code conflicts - status auto-resolved, code pauses
- [ ] T035 Test: malformed YAML in status file skipped gracefully

### Implementation Notes
1. Create WPs with conflicting lane values in task frontmatter
2. Modify `tasks.md` checkboxes to create checkbox conflicts
3. Add history entries with different timestamps
4. Verify resolution result matches spec rules
5. Create code file conflicts to verify they are NOT auto-resolved

### Parallel Opportunities
- T029-T035 are independent test scenarios

### Dependencies
- Depends on WP01 (fixtures)

### Risks & Mitigations
- Risk: YAML formatting sensitivity → Use ruamel.yaml for safe manipulation

---

## Work Package WP06: Automatic Cleanup Tests (Priority: P3)

**Goal**: Implement tests for User Story 5 (FR-022 to FR-025) - worktree and branch cleanup after merge.
**Independent Test**: `pytest tests/functional/test_merge_cleanup.py -v` validates automatic resource cleanup.
**Prompt**: `tasks/WP06-automatic-cleanup-tests.md`
**Estimated Size**: ~350 lines

### Included Subtasks
- [ ] T036 Create `tests/functional/test_merge_cleanup.py` module
- [ ] T037 Test: worktrees removed after successful merge (FR-022)
- [ ] T038 Test: branches deleted after successful merge (FR-023)
- [ ] T039 Test: `--keep-worktree` flag preserves worktrees (FR-024)
- [ ] T040 Test: `--keep-branch` flag preserves branches (FR-024)
- [ ] T041 Test: cleanup continues even if one operation fails (FR-025)

### Implementation Notes
1. Create 3-WP feature and run merge
2. Verify `.worktrees/` directory is empty after merge
3. Verify `git branch -a` shows no WP branches
4. Test flag combinations for resource preservation

### Parallel Opportunities
- T037-T041 are independent test scenarios

### Dependencies
- Depends on WP01 (fixtures)

### Risks & Mitigations
- Risk: Worktree locked files → Use timeouts and force removal

---

## Work Package WP07: Merge Resume Tests (Priority: P3)

**Goal**: Implement tests for User Story 6 (FR-026 to FR-029) - merge state persistence and resume capability.
**Independent Test**: `pytest tests/functional/test_merge_resume.py -v` validates state persistence and --resume/--abort flags.
**Prompt**: `tasks/WP07-merge-resume-tests.md`
**Estimated Size**: ~420 lines

### Included Subtasks
- [ ] T042 Create `tests/functional/test_merge_resume.py` module
- [ ] T043 Test: merge state persists to `.kittify/merge-state.json` (FR-026)
- [ ] T044 Test: `--resume` continues from last incomplete WP (FR-027)
- [ ] T045 Test: `--abort` clears state and rolls back (FR-028)
- [ ] T046 Test: corrupted state file detected and reported (FR-029)
- [ ] T047 Test: `--resume` with no merge in progress shows error
- [ ] T048 Test: state updated when resumed merge encounters new conflicts

### Implementation Notes
1. Create merge state file manually using `MergeStateFixture`
2. Interrupt merge by creating unresolvable conflict
3. Run `--resume` and verify continuation
4. Test `--abort` rollback behavior

### Parallel Opportunities
- T043-T048 are independent test scenarios

### Dependencies
- Depends on WP01 (fixtures)

### Risks & Mitigations
- Risk: Simulating interruption is complex → Use state file manipulation instead of actual interrupts

---

## Work Package WP08: CLI Flags & Integration Tests (Priority: P3)

**Goal**: Implement tests for User Story 7 (FR-030 to FR-032) and integration tests for full merge workflow.
**Independent Test**: `pytest tests/functional/test_merge_cli_integration.py -v` validates CLI flags and end-to-end workflow.
**Prompt**: `tasks/WP08-cli-flags-integration-tests.md`
**Estimated Size**: ~400 lines

### Included Subtasks
- [ ] T049 Create `tests/functional/test_merge_cli_integration.py` module
- [ ] T050 Test: `--feature <slug>` flag works from main branch (FR-030)
- [ ] T051 Test: `--single` flag merges only current WP (FR-031)
- [ ] T052 Test: `--dry-run` shows forecast without executing (FR-032)
- [ ] T053 Test: feature-wide merge from any WP worktree
- [ ] T054 Test: only "done" WPs are merged by default
- [ ] T055 Test: merge from main without --feature prompts for selection
- [ ] T056 Full integration test: 4-WP feature with dependencies, conflicts, and cleanup

### Implementation Notes
1. Test CLI invocation from different working directories
2. Verify `--single` isolation
3. Create comprehensive integration scenario with all features

### Parallel Opportunities
- T050-T055 are independent test scenarios
- T056 should run last as it's the full integration test

### Dependencies
- Depends on WP01-WP07 (uses all fixture types)

### Risks & Mitigations
- Risk: Long test execution → Use session-scoped fixtures where possible

---

## Dependency & Execution Summary

```
WP01 (Fixtures) ─────────────────────────────┐
  │                                          │
  ├──→ WP02 (Pre-flight) 🎯 MVP              │
  │                                          │
  ├──→ WP03 (Forecast)                       │
  │                                          │
  ├──→ WP04 (Ordering)                       │
  │                                          │
  ├──→ WP05 (Status Resolution)              │
  │                                          │
  ├──→ WP06 (Cleanup)                        │
  │                                          │
  ├──→ WP07 (Resume)                         │
  │                                          │
  └──→ WP08 (CLI & Integration) ─────────────┘
       (depends on all above)
```

- **Sequence**: WP01 first (foundation), then WP02-WP07 in parallel, WP08 last
- **Parallelization**: WP02-WP07 can all proceed in parallel after WP01 completes
- **MVP Scope**: WP01 + WP02 delivers pre-flight validation tests, the highest-priority capability

---

## Subtask Index (Reference)

| ID | Summary | WP | Priority | Parallel? |
|----|---------|-----|----------|-----------|
| T001 | Create test_merge_fixtures.py module | WP01 | P0 | Yes |
| T002 | Create MergeTestFeature fixture class | WP01 | P0 | No |
| T003 | Create WPFixture dataclass | WP01 | P0 | No |
| T004 | Create MergeStateFixture helper | WP01 | P0 | Yes |
| T005 | Create ConflictFixture helper | WP01 | P0 | Yes |
| T006 | Implement create_test_feature() factory | WP01 | P0 | No |
| T007 | Add cleanup utilities | WP01 | P0 | No |
| T008 | Create test_merge_preflight.py module | WP02 | P1 | No |
| T009 | Test dirty worktree detection | WP02 | P1 | Yes |
| T010 | Test multiple dirty worktrees reported together | WP02 | P1 | Yes |
| T011 | Test target branch divergence | WP02 | P1 | Yes |
| T012 | Test non-zero exit without branch modification | WP02 | P1 | Yes |
| T013 | Test clean worktrees pass pre-flight | WP02 | P1 | Yes |
| T014 | Test deleted worktree detection | WP02 | P1 | Yes |
| T015 | Create test_merge_forecast.py module | WP03 | P2 | No |
| T016 | Test overlapping file conflict prediction | WP03 | P2 | Yes |
| T017 | Test non-overlapping shows no conflicts | WP03 | P2 | Yes |
| T018 | Test conflicts grouped by file | WP03 | P2 | Yes |
| T019 | Test merge order in dry-run output | WP03 | P2 | Yes |
| T020 | Test status files marked auto-resolvable | WP03 | P2 | Yes |
| T021 | Create test_merge_ordering.py module | WP04 | P2 | No |
| T022 | Test dependency ordering | WP04 | P2 | Yes |
| T023 | Test diamond dependency pattern | WP04 | P2 | Yes |
| T024 | Test circular dependency detection | WP04 | P2 | Yes |
| T025 | Test numerical fallback | WP04 | P2 | Yes |
| T026 | Test frontmatter dependency parsing | WP04 | P2 | Yes |
| T027 | Test multiple parallel chains | WP04 | P2 | Yes |
| T028 | Create test_merge_status_resolution.py module | WP05 | P2 | No |
| T029 | Test lane "more done" wins | WP05 | P2 | Yes |
| T030 | Test checkbox `[x]` wins | WP05 | P2 | Yes |
| T031 | Test history chronological merge | WP05 | P2 | Yes |
| T032 | Test code conflicts NOT auto-resolved | WP05 | P2 | Yes |
| T033 | Test status file pattern matching | WP05 | P2 | Yes |
| T034 | Test mixed status/code conflicts | WP05 | P2 | Yes |
| T035 | Test malformed YAML handling | WP05 | P2 | Yes |
| T036 | Create test_merge_cleanup.py module | WP06 | P3 | No |
| T037 | Test worktrees removed | WP06 | P3 | Yes |
| T038 | Test branches deleted | WP06 | P3 | Yes |
| T039 | Test --keep-worktree flag | WP06 | P3 | Yes |
| T040 | Test --keep-branch flag | WP06 | P3 | Yes |
| T041 | Test cleanup continues on partial failure | WP06 | P3 | Yes |
| T042 | Create test_merge_resume.py module | WP07 | P3 | No |
| T043 | Test merge state persistence | WP07 | P3 | Yes |
| T044 | Test --resume continuation | WP07 | P3 | Yes |
| T045 | Test --abort rollback | WP07 | P3 | Yes |
| T046 | Test corrupted state detection | WP07 | P3 | Yes |
| T047 | Test --resume with no merge in progress | WP07 | P3 | Yes |
| T048 | Test state update on resumed conflicts | WP07 | P3 | Yes |
| T049 | Create test_merge_cli_integration.py module | WP08 | P3 | No |
| T050 | Test --feature flag from main | WP08 | P3 | Yes |
| T051 | Test --single flag | WP08 | P3 | Yes |
| T052 | Test --dry-run flag | WP08 | P3 | Yes |
| T053 | Test feature-wide merge from any worktree | WP08 | P3 | Yes |
| T054 | Test only "done" WPs merged | WP08 | P3 | Yes |
| T055 | Test merge from main prompts for feature | WP08 | P3 | Yes |
| T056 | Full integration test | WP08 | P3 | No |

---

> All 56 subtasks mapped to 8 work packages. WP01 is the foundation; WP02-WP07 can parallelize; WP08 is the integration capstone.
