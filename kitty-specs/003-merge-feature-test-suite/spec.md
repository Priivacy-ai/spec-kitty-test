# Feature Specification: Merge Feature Test Suite

**Feature Branch**: `003-merge-feature-test-suite`
**Created**: 2026-01-18
**Status**: Draft
**Input**: Comprehensive test coverage for spec-kitty Feature 017 (Smarter Feature Merge with Pre-flight)

## Problem Statement

Spec-kitty v0.11.0 introduced significant enhancements to the `spec-kitty merge` command through Feature 017, including pre-flight validation, conflict forecasting, dependency-based merge ordering, status file auto-resolution, and merge state persistence. These capabilities have 51 internal tests but lack external validation in the spec-kitty-test repository.

This test suite ensures:
1. New merge features work correctly from a user perspective (black-box CLI testing)
2. Edge cases and complex multi-WP scenarios are properly handled (fixture-based integration tests)
3. Both functional and distribution test variants exist per the dual-testing paradigm

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Pre-flight Validation Tests (Priority: P1)

Test that `spec-kitty merge` identifies all blockers before starting any merge operation, allowing users to fix issues in one pass.

**Why this priority**: Pre-flight validation is the highest-impact improvement. Tests must verify that dirty worktrees, diverged branches, and other blockers are all reported upfront with remediation steps.

**Independent Test**: Create a feature with multiple WP worktrees in various states (clean, dirty, diverged) and verify the merge command reports all issues without attempting any merge.

**Acceptance Scenarios**:

1. **Given** a feature with 3 WP worktrees where 2 have uncommitted changes, **When** running `spec-kitty merge`, **Then** the command lists all 3 WPs with their status and exits with non-zero code before any merge
2. **Given** a feature where the target branch has diverged from origin, **When** running `spec-kitty merge`, **Then** the command reports the divergence and suggests remediation
3. **Given** a feature with all worktrees clean and target branch up-to-date, **When** running `spec-kitty merge`, **Then** pre-flight passes and merge proceeds
4. **Given** a WP worktree that was deleted but its branch still exists, **When** running `spec-kitty merge`, **Then** pre-flight detects and reports the inconsistency

---

### User Story 2 - Conflict Forecast Tests (Priority: P2)

Test that `spec-kitty merge --dry-run` accurately predicts which files will conflict before committing to the merge.

**Why this priority**: Conflict forecasting allows developers to prepare resolution strategies. Tests must verify accurate prediction without false positives/negatives.

**Independent Test**: Create a feature where multiple WPs modify overlapping files and verify dry-run output correctly identifies conflicts.

**Acceptance Scenarios**:

1. **Given** WP01 and WP03 both modify `conftest.py`, **When** running `spec-kitty merge --dry-run`, **Then** output shows this file will conflict between the two WPs
2. **Given** WPs that modify completely separate files, **When** running `spec-kitty merge --dry-run`, **Then** output shows "No conflicts predicted"
3. **Given** status files that would conflict but are auto-resolvable, **When** running `spec-kitty merge --dry-run`, **Then** output marks these as "auto-resolvable" separately from manual conflicts
4. **Given** a dry-run with predicted conflicts, **When** reviewing the output, **Then** the merge order is visible and conflicts are grouped by file

---

### User Story 3 - Smart Merge Ordering Tests (Priority: P2)

Test that WPs are merged in dependency order based on frontmatter declarations rather than numerical order.

**Why this priority**: Dependency-ordered merging reduces cascading conflicts. Tests must verify topological sorting and cycle detection.

**Independent Test**: Create a feature where WP03 depends on WP01 and verify WP01 merges first regardless of which worktree the user is in.

**Acceptance Scenarios**:

1. **Given** WP02 depends on WP01 (per frontmatter `dependencies: ["WP01"]`), **When** running `spec-kitty merge`, **Then** WP01 is merged before WP02
2. **Given** WP03 depends on WP01, and WP04 depends on WP02, **When** running `spec-kitty merge`, **Then** both dependency chains are respected
3. **Given** a diamond dependency (WP04 depends on WP02 and WP03, both depend on WP01), **When** running `spec-kitty merge`, **Then** WP01 merges first, then WP02/WP03, then WP04
4. **Given** a circular dependency in frontmatter, **When** running `spec-kitty merge`, **Then** pre-flight fails with a clear error explaining the cycle
5. **Given** WPs with no dependency declarations, **When** running `spec-kitty merge`, **Then** merge proceeds in numerical order (WP01, WP02, WP03...)

---

### User Story 4 - Status File Auto-Resolution Tests (Priority: P2)

Test that conflicts in status tracking files are resolved automatically so users only manually resolve code conflicts.

**Why this priority**: 100% of conflicts in some feature merges were in status files. Auto-resolution eliminates this manual work.

**Independent Test**: Create conflicting status in two WPs and verify merge auto-resolves without user intervention.

**Acceptance Scenarios**:

1. **Given** WP01 has `lane: done` and WP02 has `lane: for_review` for the same task, **When** merge encounters this conflict, **Then** auto-resolve to `lane: done` (more-done wins)
2. **Given** WP01 has `- [x] Task A` and WP02 has `- [ ] Task A` in tasks.md, **When** merge encounters this conflict, **Then** auto-resolve to `- [x] Task A` (checked wins)
3. **Given** conflicting `history:` arrays in frontmatter, **When** merge encounters this conflict, **Then** auto-resolve by concatenating entries chronologically
4. **Given** a conflict in actual code (not status files), **When** merge encounters this conflict, **Then** pause for manual resolution as normal
5. **Given** conflicts in both status files and code files, **When** merge encounters this, **Then** status files are auto-resolved and only code conflicts require manual resolution
6. **Given** malformed YAML in a status file conflict, **When** merge attempts auto-resolution, **Then** skip that file gracefully and report it requires manual resolution

---

### User Story 5 - Automatic Cleanup Tests (Priority: P3)

Test that worktrees and branches are automatically deleted after successful merge.

**Why this priority**: Cleanup automation eliminates the 12+ manual commands reported in post-mortems.

**Independent Test**: Run `spec-kitty merge` on a 3-WP feature and verify no worktrees or branches remain afterward.

**Acceptance Scenarios**:

1. **Given** a successful merge of 3 WPs, **When** merge completes, **Then** all 3 worktree directories are removed from `.worktrees/`
2. **Given** a successful merge of 3 WPs, **When** merge completes, **Then** all 3 WP branches are deleted from git
3. **Given** `--keep-worktree` flag is provided, **When** merge completes successfully, **Then** worktrees are preserved but branches are still deleted
4. **Given** `--keep-branch` flag is provided, **When** merge completes successfully, **Then** branches are preserved but worktrees are removed
5. **Given** worktree removal fails for one WP (e.g., directory locked), **When** merge continues, **Then** failure is reported but other cleanup continues
6. **Given** a merge that fails mid-way due to unresolvable conflicts, **When** user aborts, **Then** already-merged WPs are cleaned up but the conflicting WP resources remain

---

### User Story 6 - Merge Resume Tests (Priority: P3)

Test that interrupted merges can be resumed without losing progress.

**Why this priority**: Context compaction and network failures can interrupt merges. Resume capability prevents restarting from scratch.

**Independent Test**: Start a merge, interrupt after 2 of 4 WPs, run `spec-kitty merge --resume`, verify it continues from WP03.

**Acceptance Scenarios**:

1. **Given** a merge in progress (2 of 4 WPs complete), **When** running `spec-kitty merge --resume`, **Then** merge continues from WP03
2. **Given** no merge in progress, **When** running `spec-kitty merge --resume`, **Then** command reports "No merge in progress" and exits with non-zero code
3. **Given** a merge with conflicts pending in WP02, **When** running `spec-kitty merge --resume` after resolving, **Then** WP02 is committed and merge proceeds to WP03
4. **Given** an interrupted merge, **When** running `spec-kitty merge --abort`, **Then** merge state is cleared and any partial changes are rolled back
5. **Given** `.kittify/merge-state.json` exists but is corrupted, **When** running `spec-kitty merge --resume`, **Then** command reports the corruption and suggests `--abort`
6. **Given** a resumed merge that encounters new conflicts, **When** user interrupts again, **Then** state is updated to reflect current progress

---

### User Story 7 - Feature-Wide Merge Default Tests (Priority: P3)

Test that merge operates on all "done" WPs for the feature by default, not just the current WP.

**Why this priority**: Users expect merge to handle the entire feature, with `--single` for legacy behavior.

**Independent Test**: From any WP worktree, run `spec-kitty merge` and verify all done WPs are merged.

**Acceptance Scenarios**:

1. **Given** a feature with 4 WPs all marked done, **When** running `spec-kitty merge` from WP02 worktree, **Then** all 4 WPs are merged
2. **Given** a feature with 4 WPs where only WP01 and WP03 are done, **When** running `spec-kitty merge`, **Then** only WP01 and WP03 are merged
3. **Given** `--single` flag is provided, **When** running `spec-kitty merge` from WP02 worktree, **Then** only WP02 is merged
4. **Given** running from main branch with `--feature <slug>`, **When** merge executes, **Then** all done WPs for that feature are merged
5. **Given** running from main branch without `--feature` flag and no feature context detectable, **When** merge executes, **Then** command prompts for feature slug or lists available features

---

### Edge Cases

- What happens when merge is run during an active git rebase/merge?
- What happens when a WP branch was force-pushed after worktree creation?
- What happens when `.kittify/` directory doesn't exist?
- What happens when running merge on a feature with 0 WPs?
- What happens when all WPs are still in "doing" or "planned" state?
- What happens when network is unavailable during origin checks?
- What happens when git version is < 2.38 (no merge-tree support)?

## Requirements *(mandatory)*

### Functional Requirements

**Test Infrastructure**
- **FR-001**: Test suite MUST create isolated git repositories for each test to prevent cross-test contamination
- **FR-002**: Test suite MUST provide fixtures for creating multi-WP features with configurable states
- **FR-003**: Test suite MUST support both functional tests (with SPEC_KITTY_TEMPLATE_ROOT) and distribution tests (without)
- **FR-004**: Test suite MUST clean up all created repositories, worktrees, and branches after tests complete

**Pre-flight Validation Tests**
- **FR-005**: Tests MUST verify uncommitted changes in worktrees are detected and reported
- **FR-006**: Tests MUST verify target branch divergence is detected and reported
- **FR-007**: Tests MUST verify all issues are collected and displayed together (not one at a time)
- **FR-008**: Tests MUST verify pre-flight failure exits with non-zero code without modifying branches

**Conflict Forecast Tests**
- **FR-009**: Tests MUST verify file conflicts are predicted by comparing WP changes
- **FR-010**: Tests MUST verify predicted conflicts are grouped by file in dry-run output
- **FR-011**: Tests MUST verify merge order is shown in dry-run output
- **FR-012**: Tests MUST verify status files are marked as auto-resolvable in predictions

**Smart Merge Ordering Tests**
- **FR-013**: Tests MUST verify frontmatter `dependencies: []` is parsed correctly
- **FR-014**: Tests MUST verify topological ordering (dependencies merge before dependents)
- **FR-015**: Tests MUST verify circular dependencies are detected with clear error
- **FR-016**: Tests MUST verify fallback to numerical order when no dependencies declared

**Status File Auto-Resolution Tests**
- **FR-017**: Tests MUST verify `lane:` conflicts resolve by "more done" wins (done > for_review > doing > planned)
- **FR-018**: Tests MUST verify checkbox conflicts resolve by preferring `[x]` over `[ ]`
- **FR-019**: Tests MUST verify `history:` arrays merge chronologically
- **FR-020**: Tests MUST verify non-status file conflicts are NOT auto-resolved
- **FR-021**: Tests MUST verify only files matching `kitty-specs/**/tasks/*.md` patterns are auto-resolved

**Automatic Cleanup Tests**
- **FR-022**: Tests MUST verify worktrees are removed after successful merge
- **FR-023**: Tests MUST verify branches are deleted after successful merge
- **FR-024**: Tests MUST verify `--keep-worktree` and `--keep-branch` flags preserve resources
- **FR-025**: Tests MUST verify cleanup continues even if one operation fails

**Merge Resume Tests**
- **FR-026**: Tests MUST verify merge state persists to `.kittify/merge-state.json`
- **FR-027**: Tests MUST verify `--resume` continues from last incomplete WP
- **FR-028**: Tests MUST verify `--abort` clears state and rolls back partial changes
- **FR-029**: Tests MUST verify corrupted state file is detected and reported

**CLI Flag Tests**
- **FR-030**: Tests MUST verify `--feature <slug>` flag works from main branch
- **FR-031**: Tests MUST verify `--single` flag merges only current WP
- **FR-032**: Tests MUST verify `--dry-run` flag shows forecast without executing merge

### Key Entities

- **Test Feature**: A spec-kitty feature created specifically for testing, with configurable number of WPs and states
- **WP Fixture**: A work package with configurable: branch name, worktree path, dirty/clean status, frontmatter dependencies, lane status
- **Merge State Fixture**: A `.kittify/merge-state.json` file with configurable: completed WPs, current WP, pending conflicts
- **Conflict Fixture**: Two WPs with modifications to the same file(s), configurable as status file or code file conflicts

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Test suite covers all 27 functional requirements from spec-kitty Feature 017
- **SC-002**: Each of the 7 user stories has at least 3 test cases covering happy path, error path, and edge case
- **SC-003**: Both functional and distribution test variants exist for CLI-facing tests
- **SC-004**: All tests pass on a fresh clone of spec-kitty-test with spec-kitty >= 0.11.0 installed
- **SC-005**: Test execution completes in under 5 minutes for the full suite
- **SC-006**: No test requires manual intervention or user input

## Assumptions

- Spec-kitty >= 0.11.0 is installed and available on PATH
- Git >= 2.20 is available (2.38+ preferred for merge-tree support)
- Tests run on macOS or Linux (Windows not in scope)
- The spec-kitty-test repository structure remains stable
- Tests can create temporary directories in `/tmp` or system temp location

## Out of Scope

- Testing jj (Jujutsu) VCS integration (separate test suite exists)
- Performance benchmarking beyond basic timeout validation
- Testing spec-kitty internal module APIs (covered by spec-kitty's own tests)
- UI/dashboard integration with merge features
- Testing merge behavior with external merge tools (vimdiff, meld)
