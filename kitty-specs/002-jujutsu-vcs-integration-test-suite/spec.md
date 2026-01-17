# Feature Specification: Jujutsu VCS Integration Test Suite

**Feature Branch**: `002-jujutsu-vcs-integration-test-suite`
**Created**: 2026-01-17
**Status**: Draft
**Input**: External QA test suite for spec-kitty feature 015 (First-Class Jujutsu VCS Integration)

## Overview

This test suite validates spec-kitty's jujutsu (jj) VCS integration from the perspective of real users. As the external QA team, we catch what implementers miss by testing the shipped package, not development conveniences.

**Testing Philosophy**: "Test what you ship, not just what you write."

**Source Feature**: `/Users/robert/Code/spec-kitty/kitty-specs/015-first-class-jujutsu-vcs-integration/spec.md`

**Critical Principle**: All distribution tests MUST run without `SPEC_KITTY_TEMPLATE_ROOT` bypass to validate actual user experience.

## Required Research Phase

**IMPORTANT**: Before proceeding to implementation planning, a research phase is required to study the actual jujutsu implementation in the spec-kitty repository.

### Research Objectives

1. **Implementation Status**: Determine which work packages (WP01-WP09) have been implemented
2. **Code Location**: Map the actual file locations of VCS abstraction layer (`src/specify_cli/core/vcs/`)
3. **API Surface**: Document the actual Protocol methods and their signatures
4. **Command Integration**: Verify which CLI commands have been updated for VCS abstraction
5. **Existing Tests**: Review any existing jj tests in spec-kitty to avoid duplication
6. **Edge Case Handling**: Study how edge cases are actually handled vs. spec'd
7. **Gaps**: Identify gaps between spec and implementation for adversarial testing

### Research Deliverables

- `research/implementation-status.md`: WP completion status and code locations
- `research/api-surface.md`: Actual VCS Protocol and type definitions
- `research/test-gaps.md`: Identified testing gaps and adversarial opportunities

## User Scenarios & Testing *(mandatory)*

### User Story 1 - VCS Detection Validation (Priority: P0)

A QA engineer validates that spec-kitty correctly detects jj/git availability and selects the appropriate VCS. This is foundational - if detection fails, all jj features are broken.

**Why this priority**: VCS detection is the entry point for all jj functionality. A bug here breaks everything downstream.

**Independent Test**: Run `spec-kitty init` in isolated environments with different tool availability combinations.

**Acceptance Scenarios**:

1. **Given** jj is installed and in PATH, **When** `spec-kitty init` runs, **Then** output confirms jj selected as default VCS
2. **Given** jj is NOT installed but git is, **When** `spec-kitty init` runs, **Then** output shows git selected AND displays jj recommendation message
3. **Given** neither jj nor git is installed, **When** `spec-kitty init` runs, **Then** command fails with clear error listing both tools
4. **Given** jj is installed, **When** `spec-kitty init --vcs=git` runs, **Then** git is used despite jj availability
5. **Given** jj binary exists but is broken/crashes, **When** `spec-kitty init` runs, **Then** system falls back to git with warning (not silent failure)
6. **Given** jj is a different tool with same name (not jujutsu), **When** detection runs, **Then** system validates it's actually jujutsu via version output

---

### User Story 2 - Per-Feature VCS Lock Enforcement (Priority: P0)

A QA engineer validates that VCS selection is locked per-feature and cannot be changed mid-feature, preventing data corruption.

**Why this priority**: VCS lock prevents catastrophic data loss from mixing git/jj operations on the same feature.

**Independent Test**: Create feature with one VCS, attempt to change it, verify rejection.

**Acceptance Scenarios**:

1. **Given** project default is jj, **When** new feature created, **Then** `meta.json` contains `"vcs": "jj"`
2. **Given** feature created with jj, **When** attempting `--vcs=git` on implement command, **Then** command fails with clear error explaining VCS is locked
3. **Given** feature A uses git and feature B uses jj, **When** working on both concurrently, **Then** each feature uses its designated VCS without cross-contamination
4. **Given** meta.json is manually edited to change VCS, **When** next spec-kitty command runs, **Then** system detects tampering and warns/fails
5. **Given** feature created with jj, **When** user deletes meta.json and re-runs command, **Then** system handles gracefully (doesn't corrupt workspace)

---

### User Story 3 - Workspace Creation Parity (Priority: P1)

A QA engineer validates that jj workspace creation produces equivalent functionality to git worktrees, ensuring no regression for users adopting jj.

**Why this priority**: Workspace creation is the foundation for all implementation work. Must work identically to git for user confidence.

**Independent Test**: Create workspaces with both VCS backends, compare structure and capabilities.

**Acceptance Scenarios**:

1. **Given** feature uses jj, **When** `spec-kitty implement WP01` runs, **Then** `.worktrees/###-feature-WP01/` created with valid jj workspace
2. **Given** feature uses jj with git colocated, **When** workspace created, **Then** both `.jj/` and `.git/` directories exist
3. **Given** feature uses jj, **When** `spec-kitty implement WP02 --base WP01` runs, **Then** WP02 workspace sees WP01's changes
4. **Given** workspace created with jj, **When** files modified, **Then** changes tracked automatically (no staging required)
5. **Given** jj workspace, **When** running standard git commands in colocated mode, **Then** git commands work correctly
6. **Given** jj-only mode (no git), **When** workspace created, **Then** only `.jj/` exists and workspace fully functional

---

### User Story 4 - Auto-Rebase Chain Validation (Priority: P1)

A QA engineer validates that jj's auto-rebase correctly propagates changes through dependency chains, the primary value proposition of jj integration.

**Why this priority**: Auto-rebase is THE reason to use jj. If this doesn't work, the feature has no value.

**Independent Test**: Create WP dependency chain, modify upstream WP, verify downstream WPs can sync.

**Acceptance Scenarios**:

1. **Given** WP02 depends on WP01, both using jj, **When** WP01 commits changes, **Then** jj marks WP02 as needing rebase
2. **Given** WP02 workspace is stale, **When** `spec-kitty sync` runs in WP02, **Then** files update to include WP01's changes
3. **Given** WP01→WP02→WP03 dependency chain, **When** WP01 changes, **Then** both WP02 and WP03 can sync to get updates
4. **Given** 10+ WP dependency chain, **When** WP01 changes, **Then** all downstream WPs can sync (no chain length limit)
5. **Given** diamond dependency (WP03 depends on both WP01 and WP02), **When** both change, **Then** WP03 syncs both correctly
6. **Given** circular dependency attempt, **When** detected, **Then** system rejects with clear error

---

### User Story 5 - Non-Blocking Conflict Handling (Priority: P1)

A QA engineer validates that jj conflicts don't block work, enabling true parallel development.

**Why this priority**: Non-blocking conflicts enable autonomous agent workflows - critical for multi-agent spec-kitty usage.

**Independent Test**: Create conflict scenario, verify work continues on non-conflicting files.

**Acceptance Scenarios**:

1. **Given** sync causes conflict in file X, **When** sync completes, **Then** file X has conflict markers BUT operation succeeds
2. **Given** workspace has stored conflicts, **When** editing non-conflicting files, **Then** edits work normally
3. **Given** workspace has conflicts, **When** `/spec-kitty.review` runs, **Then** review BLOCKED until conflicts resolved
4. **Given** workspace has conflicts, **When** merge attempted, **Then** merge BLOCKED with list of conflicted files
5. **Given** conflict resolved by editing file, **When** saved, **Then** jj automatically records resolution
6. **Given** WP02 resolved conflicts, **When** WP03 (depends on WP02) syncs, **Then** WP03 gets resolution (no re-conflict)
7. **Given** 3-way merge conflict, **When** sync completes, **Then** all 3 sides visible in conflict markers

---

### User Story 6 - Sync Command Abstraction (Priority: P2)

A QA engineer validates that `spec-kitty sync` provides unified interface for both VCS backends.

**Why this priority**: Unified interface ensures agents/users don't need to know which VCS is in use.

**Independent Test**: Run sync command on both git and jj workspaces, verify equivalent behavior.

**Acceptance Scenarios**:

1. **Given** jj workspace is stale, **When** `spec-kitty sync` runs, **Then** workspace updates via `jj workspace update-stale`
2. **Given** git workspace needs rebase, **When** `spec-kitty sync` runs, **Then** workspace updates via git rebase
3. **Given** workspace already up to date, **When** `spec-kitty sync` runs, **Then** output says "already up to date"
4. **Given** sync results in conflicts, **When** command completes, **Then** output lists conflicted files with line ranges
5. **Given** `--repair` flag used, **When** workspace corrupted, **Then** recovery attempted using operation log (jj) or reset (git)
6. **Given** network unavailable during remote sync, **When** sync fails, **Then** clear error message (not cryptic git/jj output)

---

### User Story 7 - Operation Log and Undo (Priority: P2)

A QA engineer validates operation history and undo capabilities work correctly.

**Why this priority**: Undo is a safety net - lower priority but critical for user confidence.

**Independent Test**: Perform operations, verify log shows history, verify undo restores state.

**Acceptance Scenarios**:

1. **Given** feature uses jj, **When** `spec-kitty ops log` runs, **Then** jj operation history displayed
2. **Given** feature uses git, **When** `spec-kitty ops log` runs, **Then** git reflog displayed with capability warning
3. **Given** mistake made, **When** `spec-kitty ops undo` runs, **Then** last operation reversed
4. **Given** multiple undos performed, **When** checking state, **Then** each undo correctly reverses one operation
5. **Given** git backend, **When** undo attempted, **Then** warning displayed about git's limited undo capability
6. **Given** operation log is empty, **When** undo attempted, **Then** clear "nothing to undo" message

---

### User Story 8 - Stable Change Identity (Priority: P3)

A QA engineer validates that jj Change IDs remain stable across rebases.

**Why this priority**: Stable identity enables reliable tracking but is an advanced feature.

**Independent Test**: Rebase workspace multiple times, verify Change ID unchanged.

**Acceptance Scenarios**:

1. **Given** WP created with jj, **When** rebased 5 times, **Then** Change ID in metadata remains constant
2. **Given** Change ID recorded, **When** querying by Change ID, **Then** system finds current state regardless of rebases
3. **Given** git backend, **When** tracking identity, **Then** falls back to branch name (no Change ID)
4. **Given** workspace deleted and recreated, **When** using same WP, **Then** new Change ID assigned (not reused)

---

### User Story 9 - Colocated Repository Mode (Priority: P3)

A QA engineer validates colocated mode (.jj/ + .git/) works for gradual adoption.

**Why this priority**: Colocated mode enables adoption without breaking CI/CD - important but not critical path.

**Independent Test**: Create colocated repo, verify both jj and git commands work.

**Acceptance Scenarios**:

1. **Given** both jj and git installed, **When** feature created, **Then** workspace has both `.jj/` and `.git/`
2. **Given** colocated workspace, **When** changes made via jj, **Then** `git log` shows same commits
3. **Given** colocated workspace, **When** changes made via git, **Then** `jj log` shows commits after next jj command
4. **Given** jj installed but git NOT installed, **When** feature created, **Then** only `.jj/` exists (pure jj mode)
5. **Given** colocated workspace, **When** GitHub Actions runs git commands, **Then** CI works normally
6. **Given** colocated workspace with diverged state, **When** jj command runs, **Then** sync happens automatically

---

### User Story 10 - Upgrade Path: Git-Only to Jujutsu (Priority: P1)

A QA engineer validates that existing git-only projects can adopt jj without data loss.

**Why this priority**: Upgrade path is critical for adoption - users won't adopt if migration is risky.

**Independent Test**: Take existing git-only spec-kitty project, install jj, verify new features use jj while old features remain git.

**Acceptance Scenarios**:

1. **Given** existing project with 5 git features, **When** jj installed and new feature created, **Then** new feature uses jj, old features unchanged
2. **Given** git feature with 3 WPs in progress, **When** jj installed, **Then** existing WPs continue working with git
3. **Given** upgrade scenario, **When** `spec-kitty init` re-run, **Then** config.yaml updated to prefer jj for new features
4. **Given** old git worktrees exist, **When** jj features added, **Then** no interference between git worktrees and jj workspaces
5. **Given** project upgraded to jj, **When** jj uninstalled, **Then** existing jj features error clearly (not silent corruption)

---

### User Story 11 - Distribution Testing: No Template Bypass (Priority: P0)

A QA engineer validates that all jj functionality works for PyPI users without development environment overrides.

**Why this priority**: This is THE critical test category. Validates what users actually experience.

**Independent Test**: Install spec-kitty from wheel/PyPI, run all jj commands WITHOUT `SPEC_KITTY_TEMPLATE_ROOT`.

**Acceptance Scenarios**:

1. **Given** spec-kitty installed from PyPI, **When** `spec-kitty init` runs (no SPEC_KITTY_TEMPLATE_ROOT), **Then** jj detection works
2. **Given** PyPI installation, **When** jj feature created, **Then** all templates use correct Python CLI commands
3. **Given** PyPI installation, **When** jj workspace created, **Then** workspace fully functional
4. **Given** PyPI installation, **When** sync command runs, **Then** no "template not found" errors
5. **Given** PyPI installation, **When** VCS abstraction used, **Then** all code paths work (not just tested paths)

---

### User Story 12 - Gitignore Configuration Validation (Priority: P1)

A QA engineer validates that spec-kitty's gitignore generation correctly handles kitty-specs in main vs worktrees.

**Why this priority**: Bug discovered during spec creation - kitty-specs incorrectly ignored in main repo.

**Independent Test**: Verify gitignore rules for kitty-specs/ in main repo vs worktrees.

**Acceptance Scenarios**:

1. **Given** main repository, **When** `spec-kitty init` runs, **Then** kitty-specs/ is NOT in .gitignore (should be tracked)
2. **Given** worktree created, **When** checking gitignore, **Then** kitty-specs/ MAY be ignored (status in main)
3. **Given** .gitignore generated by spec-kitty, **When** `git add kitty-specs/`, **Then** files are added (not ignored)
4. **Given** existing project with kitty-specs ignored, **When** upgrade runs, **Then** gitignore fixed to track kitty-specs

---

### Edge Cases

**VCS Tool Issues**:
- What happens when jj binary exists but always returns error code?
- What happens when jj version is below minimum (< 0.20)?
- What happens when jj is installed but not initialized in repo?
- What happens when PATH changes mid-session (jj becomes unavailable)?

**Workspace Corruption**:
- What happens when .jj/ directory is partially deleted?
- What happens when workspace metadata is corrupted?
- What happens when workspace points to non-existent commit?
- What happens when two workspaces claim same directory?

**Concurrency Issues**:
- What happens when two agents sync same workspace simultaneously?
- What happens when workspace modified during sync operation?
- What happens when jj operation interrupted (SIGKILL)?
- What happens when git and jj commands run simultaneously in colocated mode?

**Data Integrity**:
- What happens when conflict markers manually corrupted?
- What happens when meta.json has invalid VCS value?
- What happens when Change ID references deleted commit?
- What happens when operation log is truncated?

**Network Issues**:
- What happens when remote sync fails mid-operation?
- What happens when remote repo is force-pushed?
- What happens when SSH key authentication fails?

**Resource Limits**:
- What happens with 100+ workspaces?
- What happens with 1000+ file conflict?
- What happens when disk is full during operation?

## Requirements *(mandatory)*

### Functional Requirements

**Test Infrastructure**:
- **TR-001**: Test suite MUST include `@pytest.mark.jj` marker for jj-specific tests
- **TR-002**: Test suite MUST skip jj tests gracefully when jj not installed
- **TR-003**: Test suite MUST NOT mock jj behavior - real execution required
- **TR-004**: Test suite MUST include both functional and distribution test categories
- **TR-005**: Distribution tests MUST NOT use `SPEC_KITTY_TEMPLATE_ROOT` bypass

**Coverage Requirements**:
- **TR-006**: Tests MUST cover all 9 user stories from feature 015 spec
- **TR-007**: Tests MUST validate all 24 functional requirements (FR-001 to FR-024)
- **TR-008**: Tests MUST include adversarial scenarios (corruption, race conditions, partial failures)
- **TR-009**: Tests MUST include upgrade path validation (git-only to jj)
- **TR-010**: Tests MUST validate gitignore handling for kitty-specs/

**Test Organization**:
- **TR-011**: Tests MUST be organized in `tests/functional/` and `tests/distribution/` directories
- **TR-012**: Tests MUST use parametrized fixtures for git/jj backend parity testing
- **TR-013**: Tests MUST include version-gated tests using `requires_v*` fixtures
- **TR-014**: Tests MUST produce clear failure messages identifying exact issue

**Validation Requirements**:
- **TR-015**: Tests MUST validate meta.json VCS field correctness
- **TR-016**: Tests MUST validate workspace directory structure
- **TR-017**: Tests MUST validate conflict detection and blocking behavior
- **TR-018**: Tests MUST validate sync command output format
- **TR-019**: Tests MUST validate operation log contents
- **TR-020**: Tests MUST validate Change ID stability across rebases

### Key Entities

- **TestFixture**: Reusable test setup (jj_available, git_repo, jj_repo, colocated_repo)
- **TestMarker**: Pytest markers for conditional test execution (@pytest.mark.jj, @pytest.mark.distribution)
- **VCSBackend**: Parametrized backend for parity testing ("git", "jj")
- **TestProject**: Isolated spec-kitty project for testing (with/without jj features)
- **ConflictScenario**: Predefined conflict situations for testing (simple, multi-file, multi-sided)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of feature 015 user stories have corresponding test coverage
- **SC-002**: 100% of feature 015 functional requirements have observable test validation
- **SC-003**: All distribution tests pass without `SPEC_KITTY_TEMPLATE_ROOT` set
- **SC-004**: Test suite detects VCS detection failures within first 5 tests
- **SC-005**: Test suite catches meta.json VCS lock violations
- **SC-006**: Test suite validates conflict blocking before review/merge
- **SC-007**: Test suite includes minimum 10 adversarial/edge case scenarios
- **SC-008**: Test suite runs in under 5 minutes for functional tests (jj available)
- **SC-009**: Test suite gracefully skips jj tests in under 30 seconds (jj unavailable)
- **SC-010**: Zero false positives in 10 consecutive CI runs

## Assumptions

- jj 0.20+ is the minimum supported version for testing
- Test environments have either jj, git, or both installed
- CI/CD environments may not have jj installed (tests must skip gracefully)
- Real jj/git execution is required (no mocking per spec requirement)
- Test isolation is maintained via temporary directories
- Network tests may be skipped in offline CI environments
- Research phase will be completed before implementation planning to validate against actual implementation
