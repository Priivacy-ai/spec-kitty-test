# Feature Specification: Comprehensive Post-JJ-Rollback Test Suite

**Feature Branch**: `006-comprehensive-post-jj-rollback-test-suite`
**Created**: 2026-01-23
**Status**: Draft
**Input**: Create comprehensive adversarial test suite covering all spec-kitty changes since 2026-01-19, including orchestrator system, JJ rollback, VCS abstraction refactoring, stale detection, merge improvements, and critical bug fixes. Use both functional and distribution testing to prevent catastrophic failures like 0.10.8.

## Overview

This test suite provides comprehensive, adversarial validation of all changes made to spec-kitty since January 19, 2026. The testing philosophy is **skeptical and protective**: assume the implementation team made mistakes, don't trust that edge cases were handled, and relentlessly hunt for bugs before they reach users.

**Context**: Since the last commit in this repo (2026-01-19), spec-kitty has undergone major changes:
- **Orchestrator system** (F020, F021, F022): Complete autonomous multi-agent execution framework with 9 agents, state machine, parallel execution
- **JJ VCS rollback** (F015): Full jj integration built then disabled due to sparse checkout incompatibility
- **VCS abstraction refactor**: Separate git/jj code paths in implement.py to enable future jj re-enablement
- **Critical bug fixes**: Main repo kitty-specs usage, agent aliases, state transitions, bookmark management
- **New features**: Stale WP detection, merge preflight validation, dependency-ordered merging

**Motivation**: The 0.10.8 catastrophic failure (100% of PyPI users broken for 8+ releases despite 323 passing tests) demonstrated that existing tests had systemic blind spots. This suite uses both functional tests (fast iteration) AND distribution tests (real user experience) to catch packaging issues, environment problems, and integration failures.

**Scope**: Comprehensive coverage across five equally-critical risk areas:
1. **Orchestrator corruption** - State machine failures, agent invocation bugs, parallel execution races
2. **VCS abstraction bugs** - Git/jj path confusion, jj behavior leaking despite being disabled
3. **Data loss scenarios** - Main repo corruption, worktree cleanup errors, merge conflicts destroying code
4. **Distribution/packaging** - Templates missing from PyPI, env vars not working, migrations failing
5. **Integration failures** - Command interactions, workflow breakage, backward compatibility

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Distribution Test: Fresh Install Workflow (Priority: P1)

A user installs spec-kitty from PyPI for the first time and attempts the basic workflow: init → specify → plan → tasks → implement → merge. This must work without any environment variable bypasses or local repository access.

**Why this priority**: The 0.10.8 failure showed that ALL existing tests used `SPEC_KITTY_TEMPLATE_ROOT` to bypass the real user experience. This is the single most critical test to prevent another catastrophic PyPI release.

**Independent Test**: Can be tested by installing spec-kitty in a clean virtualenv from the built distribution package, running the full workflow without any bypass environment variables, and verifying all artifacts are created correctly.

**Acceptance Scenarios**:

1. **Given** fresh virtualenv with spec-kitty installed from wheel, **When** user runs `spec-kitty init` in new project, **Then** `.kittify/` directory is created with all required config files and templates from the package (NOT from local repo)

2. **Given** initialized project from PyPI install, **When** user runs `spec-kitty agent feature create-feature "test-feature"`, **Then** feature directory is created with correct structure and all template files are populated

3. **Given** feature created from PyPI install, **When** user runs `spec-kitty implement WP01`, **Then** worktree is created successfully and task prompt file is populated from packaged templates

4. **Given** full workflow from init through implement, **When** checking all generated files, **Then** zero files contain placeholder text like "TEMPLATE_FEATURE_NAME" or broken template references

5. **Given** PyPI install in environment with NO git repo access, **When** running any command that uses templates, **Then** command succeeds using packaged templates without attempting repo access

---

### User Story 2 - Orchestrator State Machine Integrity (Priority: P1)

The orchestrator manages complex state transitions (PENDING → IMPLEMENTATION → REVIEW → DONE/REWORK) across multiple parallel WPs. State machine bugs could corrupt features, lose work, or create deadlocks. Adversarial testing must try to break the state machine through interruptions, failures, and edge cases.

**Why this priority**: The orchestrator is brand new code (F020-F022) with complex concurrency and state management. State machine bugs are often subtle and only appear under specific failure conditions.

**Independent Test**: Can be tested by creating features with various dependency graphs, simulating agent failures/interruptions at each state, and verifying state transitions are correct and idempotent.

**Acceptance Scenarios**:

1. **Given** orchestration in IMPLEMENTATION state for WP01, **When** agent is interrupted (SIGINT) mid-execution, **Then** state persists to disk and --resume continues from IMPLEMENTATION (not back to PENDING)

2. **Given** WP01 in REVIEW state with rejection outcome, **When** orchestrator processes review, **Then** state transitions to REWORK and implementation agent is re-invoked

3. **Given** orchestration with parallel WPs (WP01, WP02, WP03), **When** WP02 fails after WP01 succeeds, **Then** WP03 continues independently and WP02 can be retried without affecting WP01/WP03 state

4. **Given** orchestration state file exists from previous run, **When** user starts new orchestration without --resume, **Then** command detects stale state and prompts user to --resume or --clean

5. **Given** WP in IMPLEMENTATION state, **When** calling start_implementation() again (idempotent transition), **Then** state remains IMPLEMENTATION without error (no invalid transition exception)

6. **Given** dependency graph with WP04 depending on WP01-WP03, **When** WP02 fails permanently, **Then** WP04 is marked as BLOCKED and not attempted until WP02 succeeds

7. **Given** circular dependency detected (WP01 → WP02 → WP03 → WP01), **When** orchestrator validates dependency graph, **Then** orchestration fails fast with clear error before any WP execution

---

### User Story 3 - VCS Abstraction Isolation (Priority: P1)

The implement.py refactoring created separate code paths for git vs jj (`_ensure_planning_artifacts_committed_git()` and `_ensure_planning_artifacts_committed_jj()`). Cross-contamination between these paths could cause git users to experience jj-related failures or vice versa.

**Why this priority**: VCS abstraction bugs affect every user on every implement operation. If git users hit jj code paths (or jj is invoked despite being disabled), this breaks core workflows.

**Independent Test**: Can be tested by mocking VCS detection to force each path, then verifying the other path's code is never executed and correct VCS commands are used.

**Acceptance Scenarios**:

1. **Given** git-only environment (jj not installed), **When** running `spec-kitty implement WP01`, **Then** only git commands are executed (verified via command logging) and jj-specific code paths are never entered

2. **Given** feature with `meta.json` containing `"vcs": "git"`, **When** running any VCS operation, **Then** git implementation is used exclusively regardless of jj installation status

3. **Given** git implementation path, **When** checking planning artifacts, **Then** validation uses `git diff --cached` and `git status`, NOT jj equivalents

4. **Given** jj implementation path (when/if re-enabled), **When** checking planning artifacts, **Then** validation uses jj working-copy logic without artificial commit requirements

5. **Given** VCS factory selection, **When** jj is disabled (detection returns False), **Then** factory ALWAYS returns GitVCS instance even if jj binary exists on PATH

6. **Given** mixed feature set (some features with vcs=git, some with vcs=jj), **When** switching between features, **Then** correct VCS implementation is used for each feature without cross-contamination

---

### User Story 4 - JJ Rollback Validation: No Leaking Behavior (Priority: P2)

JJ support was fully implemented (detection, workspaces, bookmarks, sync, conflict handling) then disabled by making `is_jj_available()` always return False. Adversarial testing must verify that disabled code doesn't leak behavior, and that the abstraction layer cleanly falls back to git.

**Why this priority**: The jj code is still present in the codebase but dormant. If jj commands are executed despite detection being disabled, or if jj-specific assumptions leak into git paths, users experience mysterious failures.

**Independent Test**: Can be tested by installing jj, verifying it's on PATH, then confirming spec-kitty NEVER invokes jj commands and always uses git.

**Acceptance Scenarios**:

1. **Given** jj binary installed and on PATH, **When** running `is_jj_available()`, **Then** function returns False (disabled) regardless of actual jj availability

2. **Given** jj installed, **When** running `spec-kitty init`, **Then** output shows git as VCS (no jj detection or preference), and `.kittify/config.yaml` contains only git configuration

3. **Given** jj installed, **When** creating feature with `create-feature`, **Then** `meta.json` contains `"vcs": "git"` (never "jj")

4. **Given** feature with legacy `"vcs": "jj"` in meta.json, **When** running `spec-kitty implement WP01`, **Then** system automatically converts to git, displays conversion warning, and updates meta.json to `"vcs": "git"`

5. **Given** jj installed, **When** running any spec-kitty command (init, specify, implement, sync, merge), **Then** no jj commands are executed (verified by command logging/tracing)

6. **Given** jj-specific code paths in jujutsu.py, **When** running full feature workflow, **Then** zero calls to JujutsuVCS methods occur (verified via instrumentation)

7. **Given** error messages in detection.py, **When** VCS detection fails, **Then** error mentions only git installation (no jj references)

---

### User Story 5 - Data Loss Prevention (Priority: P1)

Several changes involve file operations that could cause data loss: main repo kitty-specs usage (prevents corruption), worktree cleanup, merge conflict handling, and orchestrator workspace management. Adversarial testing must try to trigger data loss scenarios.

**Why this priority**: Data loss is the worst possible bug category. Users losing code or work-in-progress is unacceptable and destroys trust.

**Independent Test**: Can be tested by creating test data in various locations (main repo, worktrees, feature directories), running operations that clean up or modify files, and verifying no unexpected deletions or corruptions occur.

**Acceptance Scenarios**:

1. **Given** feature with completed WPs in worktrees, **When** running `spec-kitty merge --delete-branch --remove-worktree`, **Then** only WP worktrees are deleted (not main repo, not .kittify/, not other features' worktrees)

2. **Given** WP worktree with uncommitted changes, **When** attempting merge, **Then** preflight validation fails and NO cleanup operations are attempted (worktree preserved)

3. **Given** main repo kitty-specs with feature data, **When** running WP operations from worktree, **Then** operations use main repo paths (verified by file modification timestamps) and worktree copies are NOT modified

4. **Given** worktree cleanup failure (permissions issue, locked file), **When** merge continues, **Then** other worktrees are still cleaned up and failure is logged (not silent)

5. **Given** orchestrator creating workspace for WP01, **When** workspace creation fails mid-operation, **Then** partial workspace is cleaned up (no orphaned directories with incomplete state)

6. **Given** merge with status file conflicts (tasks.md frontmatter), **When** auto-resolution occurs, **Then** history is preserved (concatenated) and no task completion data is lost

7. **Given** interrupted orchestration with partial commits, **When** resuming, **Then** committed work is preserved and not re-executed or overwritten

8. **Given** sync operation with upstream changes, **When** detecting stale workspaces, **Then** local uncommitted changes are preserved (not clobbered by sync)

---

### User Story 6 - Stale Detection Accuracy (Priority: P2)

The new stale detection feature (commit 0783557) identifies WPs in "doing" lane with no recent commits. False positives could interrupt active work; false negatives could miss stuck agents. Adversarial testing must validate threshold logic and edge cases.

**Why this priority**: Stale detection affects orchestrator reliability and developer workflow visibility. Incorrect staleness reporting could cause confusion or unnecessary interruptions.

**Independent Test**: Can be tested by creating WPs with known commit timestamps, configuring various staleness thresholds, and verifying correct detection and reporting.

**Acceptance Scenarios**:

1. **Given** WP01 in "doing" lane with last commit 15 minutes ago, **When** running `spec-kitty status --stale-threshold=10`, **Then** WP01 is marked as stale with ⚠️ indicator

2. **Given** WP02 in "doing" lane with last commit 5 minutes ago, **When** running `spec-kitty status --stale-threshold=10`, **Then** WP02 is NOT marked as stale

3. **Given** WP03 in "done" lane with no commits for 30 minutes, **When** running `spec-kitty status --stale-threshold=10`, **Then** WP03 is NOT marked as stale (only "doing" lane is checked)

4. **Given** WP04 in "doing" lane with no worktree created, **When** checking staleness, **Then** stale detection handles missing worktree gracefully (not an exception)

5. **Given** worktree branch with no commits (just created), **When** checking staleness, **Then** detection uses worktree creation time as baseline (not crash)

6. **Given** multiple WPs in various states, **When** running `spec-kitty status --format=json`, **Then** JSON output includes `stale_wps` count and list of stale WP identifiers

7. **Given** git log parsing failure (corrupted repo), **When** stale detection runs, **Then** graceful degradation (skip staleness for that WP, don't fail entire status command)

---

### User Story 7 - Merge Preflight Validation (Priority: P2)

Feature 017 added preflight checks before merge to detect uncommitted changes, diverged branches, and missing worktrees. These checks must catch all blockers in a single pass (not iteratively) and provide actionable remediation steps.

**Why this priority**: Preflight validation prevents merge failures mid-operation. If validation has false negatives (misses blockers) or false positives (blocks valid merges), user experience degrades significantly.

**Independent Test**: Can be tested by creating features with various blocker conditions, running merge with --dry-run, and verifying all issues are reported before any merge operations begin.

**Acceptance Scenarios**:

1. **Given** 4 WPs where WP01 and WP03 have uncommitted changes, **When** running `spec-kitty merge`, **Then** preflight reports both WPs with uncommitted changes before exiting (no merge attempted)

2. **Given** target branch (main) has diverged from origin/main, **When** running `spec-kitty merge`, **Then** preflight detects divergence and suggests `git pull` before exiting

3. **Given** WP02 worktree directory deleted but branch still exists, **When** running preflight, **Then** inconsistency is detected and reported with remediation steps

4. **Given** all preflight checks pass, **When** running `spec-kitty merge --dry-run`, **Then** predicted conflicts are shown (if any) without performing actual merge

5. **Given** WP dependency graph with WP03 depending on WP01, **When** running `spec-kitty merge --dry-run`, **Then** merge order shows WP01 before WP03

6. **Given** circular dependency detected in frontmatter, **When** preflight runs, **Then** validation fails with clear error identifying the cycle (e.g., "WP01 → WP02 → WP03 → WP01")

7. **Given** preflight failure, **When** command exits, **Then** exit code is non-zero and no git state is modified (branches, refs, worktrees all unchanged)

---

### User Story 8 - Agent Invocation Reliability (Priority: P2)

The orchestrator supports 9 different agents (Claude Code, GitHub Codex, Copilot, Gemini, Qwen, OpenCode, Kilocode, Augment, Cursor) with different CLI invocation patterns. Recent fixes addressed agent aliases, timeouts, and permissions. Adversarial testing must validate agent detection, selection, and invocation.

**Why this priority**: Agent invocation is the core of orchestrator functionality. If agents are misidentified, selected incorrectly, or invoked with wrong parameters, orchestration fails completely.

**Independent Test**: Can be tested by mocking agent installations, configuring priority lists, and verifying correct agent selection and invocation command construction.

**Acceptance Scenarios**:

1. **Given** user config with aliases ("claude", "auggie"), **When** orchestrator resolves agent IDs, **Then** aliases are normalized to canonical names ("claude-code", "augment")

2. **Given** multiple agents available, **When** selecting agent for implementation, **Then** highest-priority agent from config is chosen

3. **Given** primary agent fails (rate limit), **When** fallback strategy is "next_in_list", **Then** next available agent in priority order is attempted

4. **Given** Cursor agent selected, **When** constructing invocation command, **Then** timeout wrapper is applied (Tier-2 workaround)

5. **Given** OpenCode agent selected, **When** constructing invocation command, **Then** `--agent build` flag is included for permissions

6. **Given** Gemini agent selected, **When** invoking agent, **Then** timeout is set to 120s minimum (increased from default)

7. **Given** agent not installed, **When** orchestrator detects available agents, **Then** that agent is excluded from selection pool (not attempted)

8. **Given** all configured agents unavailable, **When** orchestrator starts, **Then** clear error message with installation instructions is shown (orchestration doesn't start)

9. **Given** agent invocation with exit code 1, **When** orchestrator processes result, **Then** failure is recorded and retry/fallback logic is triggered

---

### User Story 9 - Template and Migration Integrity (Priority: P1)

Distribution testing revealed that templates were missing from PyPI packages (0.10.8 catastrophic failure) and migrations weren't registered properly (commit dfb8ca8). Adversarial testing must validate packaging, template bundling, and migration execution.

**Why this priority**: Template and migration failures cause 100% user breakage on fresh installs or upgrades. This is the highest-severity failure mode.

**Independent Test**: Can be tested by building wheel, installing in clean environment, and verifying all templates and migrations are accessible without repository access.

**Acceptance Scenarios**:

1. **Given** wheel built from source, **When** inspecting wheel contents, **Then** all template files from `.kittify/missions/*/templates/` are present in package

2. **Given** fresh install from wheel, **When** running `spec-kitty init`, **Then** templates are loaded from package site-packages (not from local repo or fallback)

3. **Given** spec-kitty 0.11.1 installed, **When** upgrading to 0.11.2, **Then** all migrations execute successfully (m_0_10_9, m_0_10_14, m_0_11_1, m_0_11_2, m_0_12_0)

4. **Given** migration m_0_11_2 executing, **When** checking migration registry, **Then** migration is registered in `__init__.py` and executed (not skipped)

5. **Given** environment with NO SPEC_KITTY_TEMPLATE_ROOT set, **When** creating feature, **Then** templates are resolved from package without environment variable bypass

6. **Given** package installed, **When** running `python -c "from spec_kitty.templates import get_template; print(get_template('spec-template.md'))"`, **Then** template content is returned (not FileNotFoundError)

7. **Given** damaged or missing template file in package, **When** operation requires template, **Then** clear error message indicates which template is missing (not generic exception)

8. **Given** multiple mission templates (software-dev, research, documentation), **When** creating feature with specific mission, **Then** correct mission's templates are used (not default)

---

### User Story 10 - Backward Compatibility (Priority: P2)

Changes included automatic conversion of legacy jj features to git, agent alias normalization, and main repo kitty-specs usage. Existing users with in-progress features must not experience breaking changes.

**Why this priority**: Breaking existing user workflows destroys trust and creates support burden. Gradual migration and backward compatibility are essential for real-world deployments.

**Independent Test**: Can be tested by creating features with old formats/configurations, running new spec-kitty version, and verifying graceful migration or clear upgrade paths.

**Acceptance Scenarios**:

1. **Given** feature with `"vcs": "jj"` in meta.json from pre-rollback version, **When** running `spec-kitty implement WP01`, **Then** meta.json is updated to `"vcs": "git"` and warning message is displayed

2. **Given** agents.yaml with old alias ("claude"), **When** orchestrator loads config, **Then** alias is transparently mapped to "claude-code" without user intervention

3. **Given** feature created before main-repo-kitty-specs fix (worktree has stale kitty-specs copy), **When** running WP operations, **Then** main repo paths are used and stale copies are ignored

4. **Given** feature with old frontmatter format (missing dependency fields), **When** merge runs, **Then** fallback to numerical order occurs with warning (not error)

5. **Given** orchestration state file from older orchestrator version, **When** running --resume, **Then** state is migrated to new format or clear error indicates incompatibility

6. **Given** project initialized before stale detection feature, **When** running `spec-kitty status`, **Then** stale detection works on existing features (not just new ones)

7. **Given** existing feature with completed WPs, **When** upgrading spec-kitty version, **Then** all existing work remains accessible and commands work without re-initialization

---

### Edge Cases

**Orchestrator Edge Cases:**
- What happens when WP dependency graph has unreachable nodes (WP05 depends on WP99 which doesn't exist)?
- What happens when agent produces output that can't be parsed as success/failure?
- What happens when worktree creation succeeds but initial commit fails (partial workspace state)?
- What happens when state file is corrupted (invalid JSON)?
- What happens when two orchestration processes run concurrently on the same feature?
- What happens when agent timeout occurs during critical operation (mid-commit)?

**VCS Edge Cases:**
- What happens when git binary exists but is broken (returns non-zero for `--version`)?
- What happens when feature meta.json has `"vcs": "invalid-vcs-name"`?
- What happens when git worktree creation fails due to existing directory?
- What happens when user manually modifies VCS field in meta.json after feature creation?

**Data Safety Edge Cases:**
- What happens when merge cleanup encounters file in use (Windows lock)?
- What happens when worktree path exceeds OS path length limits?
- What happens when main repo kitty-specs directory is deleted during WP operation?
- What happens when disk full during state persistence?

**Distribution Edge Cases:**
- What happens when package is installed with --no-deps (missing dependencies)?
- What happens when template file has incorrect encoding (non-UTF8)?
- What happens when migration partially completes then crashes?
- What happens when user has both pip and conda installations (PATH priority issues)?

**Stale Detection Edge Cases:**
- What happens when git log returns empty output (no commits in worktree)?
- What happens when worktree exists but branch is deleted?
- What happens when system clock is set backwards (negative time delta)?
- What happens when --stale-threshold is set to 0 or negative value?

**Agent Invocation Edge Cases:**
- What happens when agent binary exists but requires interactive auth on first run?
- What happens when agent writes to stderr but exits with code 0?
- What happens when agent produces extremely large output (>100MB logs)?
- What happens when agent config has empty priority list (no agents specified)?

## Requirements *(mandatory)*

### Functional Requirements

**Distribution Testing**
- **FR-001**: Test suite MUST include distribution tests that install from wheel without SPEC_KITTY_TEMPLATE_ROOT or repository access
- **FR-002**: Distribution tests MUST validate fresh install workflow: init → specify → plan → tasks → implement → merge
- **FR-003**: Distribution tests MUST verify all templates are accessible from packaged installation
- **FR-004**: Distribution tests MUST verify all migrations execute successfully on upgrade

**Orchestrator Testing**
- **FR-005**: Test suite MUST validate all state transitions (PENDING → IMPLEMENTATION → REVIEW → DONE/REWORK)
- **FR-006**: Test suite MUST test idempotent state transitions (e.g., start_implementation from IMPLEMENTATION state)
- **FR-007**: Test suite MUST validate dependency graph parsing and topological sort
- **FR-008**: Test suite MUST test parallel execution with various dependency patterns
- **FR-009**: Test suite MUST validate resume functionality after interruption at each state
- **FR-010**: Test suite MUST test all 9 agent invokers (Claude, Codex, Copilot, Gemini, Qwen, OpenCode, Kilocode, Augment, Cursor)
- **FR-011**: Test suite MUST validate agent selection, fallback strategies, and retry logic
- **FR-012**: Test suite MUST test failure scenarios (agent crashes, timeouts, rate limits)

**VCS Abstraction Testing**
- **FR-013**: Test suite MUST verify git and jj code paths are isolated (no cross-contamination)
- **FR-014**: Test suite MUST validate that jj detection always returns False (disabled)
- **FR-015**: Test suite MUST verify no jj commands are executed even when jj is installed
- **FR-016**: Test suite MUST test automatic conversion of legacy jj features to git
- **FR-017**: Test suite MUST validate VCS factory selection logic
- **FR-018**: Test suite MUST test mixed features (some git, some legacy jj) in same project

**Data Loss Prevention Testing**
- **FR-019**: Test suite MUST validate worktree cleanup only deletes intended directories
- **FR-020**: Test suite MUST verify main repo kitty-specs usage (not worktree copies)
- **FR-021**: Test suite MUST test merge preflight validation catches all blockers
- **FR-022**: Test suite MUST validate uncommitted changes are preserved during sync
- **FR-023**: Test suite MUST test partial operation failures leave recoverable state
- **FR-024**: Test suite MUST validate status file auto-resolution preserves history

**Stale Detection Testing**
- **FR-025**: Test suite MUST validate staleness calculation with various time thresholds
- **FR-026**: Test suite MUST test stale detection for WPs in "doing" lane only
- **FR-027**: Test suite MUST validate git log parsing for commit timestamps
- **FR-028**: Test suite MUST test graceful handling of missing worktrees or branches
- **FR-029**: Test suite MUST validate JSON output includes stale WP information

**Merge Preflight Testing**
- **FR-030**: Test suite MUST validate preflight detects uncommitted changes in all worktrees
- **FR-031**: Test suite MUST verify preflight detects diverged target branch
- **FR-032**: Test suite MUST test dependency graph validation (including circular dependencies)
- **FR-033**: Test suite MUST validate dry-run conflict prediction
- **FR-034**: Test suite MUST verify merge order follows dependency topological sort

**Agent Invocation Testing**
- **FR-035**: Test suite MUST validate agent alias normalization
- **FR-036**: Test suite MUST test agent detection and availability checking
- **FR-037**: Test suite MUST validate invocation command construction for each agent type
- **FR-038**: Test suite MUST test agent-specific flags (e.g., OpenCode --agent build, Cursor timeout)
- **FR-039**: Test suite MUST validate exit code interpretation and failure handling

**Template and Migration Testing**
- **FR-040**: Test suite MUST verify template files are bundled in wheel
- **FR-041**: Test suite MUST validate template resolution from package site-packages
- **FR-042**: Test suite MUST test all registered migrations execute without error
- **FR-043**: Test suite MUST validate migration registry completeness
- **FR-044**: Test suite MUST test mission-specific template selection

**Backward Compatibility Testing**
- **FR-045**: Test suite MUST validate automatic jj-to-git conversion for legacy features
- **FR-046**: Test suite MUST test agent config migration and alias handling
- **FR-047**: Test suite MUST verify old frontmatter formats are handled gracefully
- **FR-048**: Test suite MUST validate existing features work after upgrade

**Edge Case and Error Handling Testing**
- **FR-049**: Test suite MUST test all edge cases listed in Edge Cases section
- **FR-050**: Test suite MUST validate error messages are clear and actionable
- **FR-051**: Test suite MUST test graceful degradation when non-critical components fail
- **FR-052**: Test suite MUST validate concurrent operation safety (file locking, state conflicts)

**Test Infrastructure Requirements**
- **FR-053**: Test suite MUST use pytest markers to categorize tests (functional, distribution, orchestrator, vcs, etc.)
- **FR-054**: Test suite MUST provide fixtures for common setup (clean env, mock agents, test features)
- **FR-055**: Test suite MUST support parallel test execution where safe
- **FR-056**: Test suite MUST generate coverage reports identifying untested code paths
- **FR-057**: Test suite MUST include integration tests that exercise full workflows end-to-end

### Key Entities

- **TestEnvironment**: Represents isolated test execution context (virtualenv, temp directory, clean git repo). Attributes: env_type (functional/distribution), spec_kitty_path, test_repo_path, env_vars.

- **MockAgent**: Simulated agent for testing orchestrator without real AI agent dependencies. Attributes: agent_id, success_probability, execution_delay, output_pattern.

- **TestFeature**: Prepared test feature with known state. Attributes: feature_number, slug, mission, wp_count, dependency_graph, expected_artifacts.

- **StateSnapshot**: Captured orchestration state at specific point for resume testing. Attributes: timestamp, wp_states, agent_assignments, execution_history.

- **VCSContext**: Test context with specific VCS configuration. Attributes: vcs_type (git/jj), detection_override, command_log, feature_vcs_lock.

- **DistributionPackage**: Built wheel for distribution testing. Attributes: package_path, version, template_manifest, migration_list, installed_path.

- **ConflictScenario**: Pre-configured merge conflict for testing resolution. Attributes: wp_modifications, conflict_type (code/status), expected_resolution, auto_resolvable.

- **StalenessConfig**: Staleness detection test parameters. Attributes: threshold_minutes, wp_lane, last_commit_time, expected_stale_status.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of distribution tests pass on fresh install from wheel without SPEC_KITTY_TEMPLATE_ROOT or repository access (prevents 0.10.8-style catastrophic failures)

- **SC-002**: 100% of orchestrator state transitions are validated with both happy path and failure scenarios (no untested state transition combinations)

- **SC-003**: 100% of VCS code paths (git and jj) are tested in isolation with no cross-contamination detected via instrumentation

- **SC-004**: Zero data loss scenarios pass (all tests attempting to trigger file deletion, corruption, or lost work fail safely with data preserved)

- **SC-005**: All 9 agent invokers pass invocation tests with correct command construction and flag handling

- **SC-006**: 100% of edge cases listed in specification have corresponding test cases with documented expected behavior

- **SC-007**: Test suite completes functional tests in under 10 minutes and distribution tests in under 45 minutes on CI infrastructure

- **SC-008**: Code coverage for changed modules (detection.py, implement.py, orchestrator/*, merge.py, stale_detection.py) exceeds 85%

- **SC-009**: 100% of registered migrations execute successfully in distribution tests without errors or data loss

- **SC-010**: All backward compatibility tests pass for features created with spec-kitty versions 0.11.0, 0.11.1, and 0.11.2

- **SC-011**: Test suite identifies at least 3 real bugs missed by implementation team before code is merged (validates adversarial approach)

- **SC-012**: Zero false negatives in preflight validation tests (all blocker conditions are detected)

## Assumptions

- Test infrastructure has access to build wheel distributions from source
- CI environment supports virtualenv creation and clean environment isolation
- Git is available in test environments (required for spec-kitty operation)
- JJ binary can be optionally installed for jj-disabled validation tests
- Test suite has sufficient timeout allowances for distribution tests (45+ minutes)
- Mock agents can simulate success/failure/timeout behaviors deterministically
- Test fixtures include representative feature structures with various dependency graphs
- Code instrumentation/logging can verify which VCS code paths are executed
- Migration testing can simulate upgrades from previous versions
- Test environments can restrict network access to validate offline operation

## Out of Scope

- Performance benchmarking (covered separately in performance testing suite)
- Security testing (authentication, injection vulnerabilities - separate security audit)
- UI/UX testing for dashboard (no UI changes in this delta)
- Documentation completeness testing (covered by documentation review process)
- Cross-platform testing for Windows/macOS/Linux variations (assumes CI handles platform matrix)
- Load testing for concurrent orchestrator operations (stress testing is separate)
- Agent-specific behavior validation (testing real AI agent output quality - not our responsibility)
- Network failure simulation and retry logic (covered in integration testing, not unit testing)
- Internationalization/localization testing (spec-kitty is English-only)
