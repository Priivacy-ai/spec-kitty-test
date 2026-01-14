# Work Packages: Critical Test Coverage for v0.12.0

**Inputs**: Design documents from `/kitty-specs/001-critical-test-coverage-v012/`
**Prerequisites**: plan.md (adversarial testing approach), spec.md (user stories with 96 tests), data-model.md (test entities), quickstart.md (developer onboarding)

**Testing Philosophy**: Adversarial red team approach - intentionally break spec-kitty to find bugs. Fail-fast: any test failure triggers immediate investigation. Fix bugs in ~/Code/spec-kitty before continuing. Zero tolerance for xfails or workarounds.

**Organization**: 108 fine-grained subtasks roll up into 12 work packages. Two parallel tracks: Track 1 (Sparse-checkout - WP02-WP07) and Track 2 (Documentation mission - WP08-WP10). Risk-first strategy prioritizes edge cases and distribution testing.

**Prompt Files**: Each work package references a matching prompt file in `/tasks/`. Prompts contain detailed implementation guidance, test patterns, and validation criteria.

---

## Work Package WP01: Test Environment Setup (Priority: P0)

**Goal**: Establish test infrastructure, fixtures, and validation tooling for adversarial testing.
**Independent Test**: Environment setup script passes validation, fixtures available, findings directory created.
**Prompt**: `/tasks/WP01-test-environment-setup.md`
**Estimated Size**: ~250 lines (5 subtasks)

### Included Subtasks
- [x] T001: Create scripts/setup-test-env.sh validation script
- [x] T002: Create findings/test-infrastructure/v0.12.0-bugs-found.md template
- [x] T003: Set up test environment (install spec-kitty, validate versions)
- [x] T004: Review existing test patterns (test_comprehensive_workspace_per_wp.py, test_user_experience_simulation.py)
- [x] T005: Create/verify init_spec_kitty_project and clean_environment fixtures

### Implementation Notes
1. Setup script validates: spec-kitty ≥v0.11.0, Git ≥2.25, Python 3.11+, git user config
2. Findings template includes sections: Bug #, Severity, Test, Symptoms, Root Cause, Fix Applied, Verification
3. Fixtures follow existing patterns from conftest.py and distribution tests

### Parallel Opportunities
- T001 and T002 can proceed in parallel (independent)
- T004 and T005 can proceed in parallel after T003

### Dependencies
- None (foundation for all other work)

### Risks & Mitigations
- **Risk**: Environment setup fails on CI/CD (different OS, missing deps)
- **Mitigation**: Test script on macOS and Linux, document platform-specific requirements
- **Risk**: Fixtures break existing tests
- **Mitigation**: Run existing test suite before and after fixture changes

---

## Work Package WP02: Sparse-Checkout Edge Cases (Priority: P1) 🎯 RISK FIRST

**Goal**: Implement Suite 6 edge case tests to surface critical bugs early (corruption, permissions, concurrency).
**Independent Test**: `pytest tests/functional/test_sparse_checkout_infrastructure.py::TestEdgeCases -xvs` shows 8/8 PASSED
**Prompt**: `/tasks/WP02-sparse-checkout-edge-cases.md`
**Estimated Size**: ~480 lines (8 subtasks)

### Included Subtasks
- [x] T006: Test corrupted sparse-checkout file recovery
- [x] T007: Test missing .git/info directory creation
- [x] T008: Test permission errors on auto-commit (clear error messages)
- [x] T009: Test concurrent git commits (locking/retry mechanism)
- [x] T010: Test pre-sparse-checkout worktree migration (fix-worktrees script)
- [x] T011: Test manual kitty-specs/ creation in worktree (ignored by git)
- [x] T012: Test symlink to kitty-specs/ in worktree (detected/removed)
- [x] T013: Test network issues during git operations (retry logic/timeout)

### Implementation Notes
1. Create TestEdgeCases class in tests/functional/test_sparse_checkout_infrastructure.py
2. Each test simulates failure scenario → validates recovery mechanism
3. Tests reference implementation: implement.py:596-642, tasks.py:432-475, workflow.py:236-264
4. Use adversarial approach: EXPECT to find bugs, document in findings/

### Parallel Opportunities
- All 8 tests can be implemented in parallel (test different edge cases)
- Coordinate via findings/ if bugs discovered affect multiple tests

### Dependencies
- Depends on WP01 (test environment and fixtures)

### Risks & Mitigations
- **Risk**: Edge case tests reveal critical sparse-checkout bugs (data corruption risk)
- **Mitigation**: This is EXPECTED and GOOD. Stop immediately, fix in ~/Code/spec-kitty, document in findings/, then continue.
- **Risk**: Tests fail intermittently (race conditions, timing)
- **Mitigation**: Zero tolerance for flaky tests - make fully deterministic with sequential simulation

---

## Work Package WP03: Multi-Agent Synchronization (Priority: P1) 🎯 RISK FIRST

**Goal**: Implement Suite 4 tests validating parallel agent synchronization via auto-commit to main.
**Independent Test**: `pytest tests/functional/test_sparse_checkout_infrastructure.py::TestMultiAgentParallel -xvs` shows 8/8 PASSED
**Prompt**: `/tasks/WP03-multi-agent-synchronization.md`
**Estimated Size**: ~460 lines (8 subtasks)

### Included Subtasks
- [x] T014: Test Agent A claims WP01, Agent B claims WP02 → both see each other's status
- [x] T015: Test Agent A marks subtask done → Agent B sees change immediately
- [x] T016: Test Agent A moves WP to for_review → Agent B sees lane change
- [x] T017: Test three agents on WP01/02/03 → all synchronized via main
- [x] T018: Test agent claims WP with dependencies → validates base workspace exists
- [x] T019: Test review feedback auto-inserted via --review-feedback-file
- [x] T020: Test PID tracking captured in frontmatter (via os.getppid())
- [x] T021: Test PID tracking in activity log (format: timestamp – agent – shell_pid=PID – lane=X – note)

### Implementation Notes
1. Create TestMultiAgentParallel class in tests/functional/test_sparse_checkout_infrastructure.py
2. Use sequential simulation (deterministic): Agent A action → verify commit → Agent B action → verify sees it
3. Validate synchronization mechanism: auto-commit to main + read from main (not worktree copy)
4. Reference: workflow.py:217-218 (PID capture), tasks_support.py:201-222 (activity log parsing)

### Parallel Opportunities
- Tests T014-T017 can be implemented in parallel (similar synchronization patterns)
- Tests T019-T021 can be implemented in parallel (different features)

### Dependencies
- Depends on WP01 (test environment)
- Implicitly depends on WP02 findings (if auto-commit bugs found)

### Risks & Mitigations
- **Risk**: Auto-commit fails silently → agents see divergent state
- **Mitigation**: Tests will catch this - fix auto-commit implementation, document in findings/
- **Risk**: PID tracking fails → audit trail incomplete
- **Mitigation**: Validate PID format, ensure captured before commit

---

## Work Package WP04: Auto-Commit Core Functionality (Priority: P1)

**Goal**: Implement Suite 3 tests validating auto-commit synchronization for move-task, mark-status, workflow commands.
**Independent Test**: `pytest tests/functional/test_sparse_checkout_infrastructure.py::TestAutoCommitSynchronization -xvs` shows 10/10 PASSED
**Prompt**: `/tasks/WP04-auto-commit-core-functionality.md`
**Estimated Size**: ~520 lines (10 subtasks)

### Included Subtasks
- [x] T022: Test move-task commits WP file to main (specific file, not all changes)
- [x] T023: Test mark-status commits tasks.md to main
- [x] T024: Test workflow implement commits status change when claiming WP
- [x] T025: Test workflow review commits status change when claiming WP
- [x] T026: Test commit messages include agent name (format: "chore: Action [agent]")
- [x] T027: Test commit messages include ISO 8601 UTC timestamp
- [x] T028: Test multiple agents working in parallel → all commits visible to each other
- [x] T029: Test auto-commit failure handled gracefully (clear error, doesn't crash)
- [x] T030: Test git user.name and user.email configuration respected in commits
- [x] T031: Test commit history clean (no duplicate commits for same change)

### Implementation Notes
1. Create TestAutoCommitSynchronization class in tests/functional/test_sparse_checkout_infrastructure.py
2. Validate commit format: message includes agent name, timestamp, correct chore prefix
3. Test auto-commit robustness: handles failures, doesn't corrupt state
4. Reference: tasks.py:432-475 (move-task), tasks.py:557-592 (mark-status), workflow.py:236-264 (implement), workflow.py:516-544 (review)

### Parallel Opportunities
- Tests T022-T025 can be implemented in parallel (different commands)
- Tests T026-T031 can be implemented in parallel (different validation aspects)

### Dependencies
- Depends on WP01 (test environment)
- Builds on WP02 and WP03 findings (auto-commit bugs discovered there)

### Risks & Mitigations
- **Risk**: Auto-commit commits unintended files (full working tree instead of specific file)
- **Mitigation**: Tests validate ONLY target file committed, not other modified files
- **Risk**: Commit message format inconsistent
- **Mitigation**: Parse commit messages, validate format matches spec

---

## Work Package WP05: Worktree Creation & Config (Priority: P1)

**Goal**: Implement Suite 1 tests validating sparse-checkout configuration during worktree creation.
**Independent Test**: `pytest tests/functional/test_sparse_checkout_infrastructure.py::TestWorktreeCreation -xvs` shows 8/8 PASSED
**Prompt**: `/tasks/WP05-worktree-creation-and-config.md`
**Estimated Size**: ~420 lines (8 subtasks)

### Included Subtasks
- [x] T032: Test kitty-specs/ excluded from worktree working directory
- [x] T033: Test .git/info/sparse-checkout file created with patterns (`/*`, `!/kitty-specs/`, `!/kitty-specs/**`)
- [x] T034: Test git config core.sparseCheckout = true
- [x] T035: Test git config core.sparseCheckoutCone = false (explicitly disabled)
- [x] T036: Test worktree directory doesn't contain kitty-specs/ (validate absence)
- [x] T037: Test main repository still has kitty-specs/ (not affected by sparse-checkout)
- [x] T038: Test multiple worktrees all exclude kitty-specs/ independently
- [x] T039: Test error handling when sparse-checkout configuration fails

### Implementation Notes
1. Create TestWorktreeCreation class in tests/functional/test_sparse_checkout_infrastructure.py
2. Validate behavior, not implementation: check kitty-specs/ absent + git ls-files empty
3. Don't read .git/info/sparse-checkout directly - test observable outcomes
4. Reference: implement.py:596-642 (sparse-checkout configuration)

### Parallel Opportunities
- Tests T032-T037 validate different aspects of same worktree (implement together)
- Test T038 (multiple worktrees) and T039 (error handling) can be separate

### Dependencies
- Depends on WP01 (test environment)
- Benefits from WP02-WP04 findings (if sparse-checkout bugs discovered)

### Risks & Mitigations
- **Risk**: Sparse-checkout not applied (kitty-specs/ present in worktree)
- **Mitigation**: This is CRITICAL BUG - data divergence risk. Fix immediately, document.
- **Risk**: Sparse-checkout breaks worktree creation entirely
- **Mitigation**: Test graceful degradation, clear error messages

---

## Work Package WP06: Path Resolution & Merge Tests (Priority: P1)

**Goal**: Implement Suite 2 (path resolution) and Suite 5 (merge behavior) tests.
**Independent Test**: `pytest tests/functional/test_sparse_checkout_infrastructure.py::TestPathResolution -xvs` and `::TestCleanMergeBehavior -xvs` show 6/6 + 6/6 PASSED
**Prompt**: `/tasks/WP06-path-resolution-and-merge-tests.md`
**Estimated Size**: ~480 lines (12 subtasks)

### Included Subtasks

**Suite 2: Path Resolution (6 subtasks)**
- [x] T040: Test tasks command finds kitty-specs in main repo (not worktree copy)
- [x] T041: Test move-task finds WP file in main repo
- [x] T042: Test workflow finds WP file in main repo
- [x] T043: Test feature slug detection strips -WPxx suffix (e.g., 012-docs-WP04 → 012-docs)
- [x] T044: Test _get_main_repo_root() detects worktree vs main correctly
- [ ] T045: Test absolute paths work from nested directories in worktree

**Suite 5: Clean Merge Behavior (6 subtasks)**
- [ ] T046: Test merge WP branch to main → no kitty-specs/ conflicts
- [ ] T047: Test merge multiple WP branches sequentially → no conflicts between them
- [ ] T048: Test merge WP branch with only src/ changes → clean fast-forward merge
- [ ] T049: Test cherry-pick src/ changes from WP branch without kitty-specs/ interference
- [ ] T050: Test rebase WP branch onto updated main → no sparse-checkout issues
- [ ] T051: Test fast-forward merge possible when worktree branch has no conflicts

### Implementation Notes
1. Create TestPathResolution and TestCleanMergeBehavior classes
2. Path resolution: Validate commands find files in main repo (absolute paths from worktree)
3. Merge tests: Validate sparse-checkout doesn't cause git conflicts during merges
4. Reference: tasks.py:39-68 (_get_main_repo_root), paths.py:74-94 (is_worktree_context), tasks_support.py:266-288 (locate_work_package)

### Parallel Opportunities
- Suite 2 (T040-T045) and Suite 5 (T046-T051) can be implemented in parallel (independent concerns)
- Within each suite, tests can be parallelized (different commands/merge scenarios)

### Dependencies
- Depends on WP01 (test environment)
- Depends on WP05 (worktree creation working)

### Risks & Mitigations
- **Risk**: Path resolution fails → agents can't find kitty-specs in main
- **Mitigation**: Tests catch this immediately. Fix path resolution logic.
- **Risk**: Merge conflicts from sparse-checkout → blocks integration
- **Mitigation**: Validate clean merges. If conflicts, fix sparse-checkout patterns.

---

## Work Package WP07: Sparse-Checkout Integration & Validation (Priority: P1)

**Goal**: Run full sparse-checkout test suite, validate 46/46 tests pass, document all bugs found.
**Independent Test**: `pytest tests/functional/test_sparse_checkout_infrastructure.py -v` shows 46/46 PASSED in <5 minutes
**Prompt**: `/tasks/WP07-sparse-checkout-integration-validation.md`
**Estimated Size**: ~320 lines (5 subtasks)

### Included Subtasks
- [ ] T052: Run complete sparse-checkout test suite (all 6 suites, 46 tests)
- [ ] T053: Validate test execution time <5 minutes
- [ ] T054: Verify all tests have clear docstrings (what tested, why matters, implementation reference)
- [ ] T055: Verify all assertions include context (stderr, stdout, file paths, git state)
- [ ] T056: Update findings/test-infrastructure/v0.12.0-bugs-found.md with complete bug list

### Implementation Notes
1. Execute full suite validation: pytest tests/functional/test_sparse_checkout_infrastructure.py -v
2. Review test quality: docstrings complete, assertions contextual, no flaky tests
3. Consolidate findings from WP02-WP06: all bugs documented, all fixes verified
4. Verify zero xfails, zero skips - all 46 tests genuinely pass

### Parallel Opportunities
- T052 (run tests) must complete before T053-T055 (validation)
- T054 and T055 (quality checks) can proceed in parallel

### Dependencies
- Depends on WP02-WP06 (all sparse-checkout test suites implemented)

### Risks & Mitigations
- **Risk**: Integration reveals new bugs (interaction between suites)
- **Mitigation**: Fix immediately, document in findings/, re-run full suite
- **Risk**: Test execution too slow (>5 minutes)
- **Mitigation**: Profile slow tests, optimize or parallelize with pytest-xdist

---

## Work Package WP08: Doc Generators Distribution Tests (Priority: P1) 🎯 RISK FIRST

**Goal**: Implement test_doc_generators_distribution.py (15 tests) validating generators load from pip package.
**Independent Test**: `pytest tests/distribution/test_doc_generators_distribution.py -xvs` shows 15/15 PASSED
**Prompt**: `/tasks/WP08-doc-generators-distribution-tests.md`
**Estimated Size**: ~480 lines (15 subtasks)

### Included Subtasks
- [x] T057: Test JSDoc generator detects JavaScript/TypeScript projects (package.json, .js/.ts files)
- [x] T058: Test JSDoc configuration template accessible from pip package
- [x] T059: Test JSDoc creates valid jsdoc.json configuration
- [x] T060: Test Sphinx generator detects Python projects (setup.py, pyproject.toml, .py files)
- [x] T061: Test Sphinx configuration template accessible from pip package
- [x] T062: Test Sphinx creates valid conf.py with correct extensions
- [x] T063: Test rustdoc generator detects Rust projects (Cargo.toml, .rs files)
- [x] T064: Test rustdoc configuration template accessible from pip package
- [x] T065: Test rustdoc creates rustdoc-config.md instructions
- [x] T066: Test all generators accessible via importlib (no SPEC_KITTY_TEMPLATE_ROOT)
- [x] T067: Test generator detection works without development env vars
- [x] T068: Test generator configs use relative paths (no local repo references)
- [x] T069: Test multi-language project detection (Python + JavaScript both detected)
- [x] T070: Test generator error handling (clear messages, installation URLs)
- [x] T071: Test no template path leakage in generated configurations

### Implementation Notes
1. Create tests/distribution/test_doc_generators_distribution.py with 3 test classes:
   - TestJSDocGenerator (T057-T059)
   - TestSphinxGenerator (T060-T062)
   - TestRustdocGenerator (T063-T065)
   - TestGeneratorIntegration (T066-T071)
2. CRITICAL: All tests use clean_environment fixture (removes SPEC_KITTY_TEMPLATE_ROOT)
3. Tests would catch Issues #62-64 pattern (local works, package fails)
4. Reference: doc_generators.py (JSDocGenerator, SphinxGenerator, RustdocGenerator classes)

### Parallel Opportunities
- JSDoc tests (T057-T059), Sphinx tests (T060-T062), rustdoc tests (T063-T065) can be implemented in parallel
- Integration tests (T066-T071) can proceed in parallel after generator-specific tests

### Dependencies
- Depends on WP01 (test environment, clean_environment fixture)
- Independent from WP02-WP07 (different track - documentation mission)

### Risks & Mitigations
- **Risk**: Templates not bundled in package → generators fail (Issues #62-64 repeat)
- **Mitigation**: This is EXACTLY what tests catch. Fix pyproject.toml, validate packaging.
- **Risk**: Generator detection fails in clean environment
- **Mitigation**: Fix generator code to not depend on SPEC_KITTY_TEMPLATE_ROOT

---

## Work Package WP09: Documentation Mission Distribution Tests (Priority: P1)

**Goal**: Implement test_documentation_mission_distribution.py (20 tests) validating mission loads from pip package.
**Independent Test**: `pytest tests/distribution/test_documentation_mission_distribution.py -xvs` shows 20/20 PASSED
**Prompt**: `/tasks/WP09-documentation-mission-distribution-tests.md`
**Estimated Size**: ~580 lines (20 subtasks)

### Included Subtasks
- [x] T072: Test documentation mission loads from pip package (no SPEC_KITTY_TEMPLATE_ROOT)
- [x] T073: Test mission.yaml accessible and parses correctly
- [x] T074: Test mission name "Documentation Kitty" version 1.0.0
- [x] T075: Test 6 workflow phases in correct order (discover, audit, design, generate, validate, publish)
- [x] T076: Test required artifacts defined (spec.md, plan.md, tasks.md, gap-analysis.md)
- [x] T077: Test optional artifacts defined (divio-templates/, generator-configs/, audit-report.md, research.md, release.md)
- [x] T078: Test workspace conventions correct (workspace="docs/", deliverables="docs/output/", documentation="docs/")
- [x] T079: Test specify command template accessible and non-empty
- [x] T080: Test plan command template accessible and non-empty
- [x] T081: Test tasks command template accessible and non-empty
- [x] T082: Test implement command template accessible and non-empty
- [x] T083: Test review command template accessible and non-empty
- [x] T084: Test all templates have expected structure (frontmatter, sections, instructions)
- [x] T085: Test templates load via importlib.resources (from package, not local repo)
- [x] T086: Test no template path leakage (no references to local ~/Code/spec-kitty paths)
- [x] T087: Test mission registered in mission registry after installation
- [x] T088: Test mission metadata correct (name, domain, version)
- [x] T089: Test get_mission_by_name("documentation") returns valid Mission object
- [x] T090: Test mission validation passes pydantic checks
- [x] T091: Test all 4 Divio templates present (tutorial, howto, reference, explanation)

### Implementation Notes
1. Create tests/distribution/test_documentation_mission_distribution.py with 4 test classes:
   - TestMissionLoading (T072-T078)
   - TestCommandTemplates (T079-T084)
   - TestTemplatePackaging (T085-T086)
   - TestMissionRegistry (T087-T091)
2. CRITICAL: All tests use clean_environment fixture
3. Tests simulate EXACT PyPI user environment (would catch Issues #62-64)
4. Reference: missions/documentation/mission.yaml, missions/documentation/command-templates/*.md

### Parallel Opportunities
- All 4 test classes can be implemented in parallel (independent validation aspects)
- Within each class, tests can be parallelized

### Dependencies
- Depends on WP01 (test environment, clean_environment fixture)
- Independent from WP02-WP07 (different track)
- Can proceed in parallel with WP08

### Risks & Mitigations
- **Risk**: Mission not found in package → critical packaging failure
- **Mitigation**: Tests fail loudly with "DO NOT SHIP v0.12.0" message. Fix pyproject.toml.
- **Risk**: Templates accessible but content wrong (outdated)
- **Mitigation**: Tests validate content structure, catch stale templates

---

## Work Package WP10: Documentation Mission End-to-End Tests (Priority: P1)

**Goal**: Implement test_documentation_mission_end_to_end.py (15 tests) validating full workflow.
**Independent Test**: `pytest tests/functional/test_documentation_mission_end_to_end.py -xvs` shows 15/15 PASSED
**Prompt**: `/tasks/WP10-documentation-mission-end-to-end-tests.md`
**Estimated Size**: ~520 lines (15 subtasks)

### Included Subtasks
- [x] T092: Test initial mode workflow (specify → plan → tasks phases)
- [x] T093: Test initial mode stores state in meta.json (documentation_state field)
- [x] T094: Test gap-filling mode runs gap analysis automatically
- [x] T095: Test gap-filling mode classifies existing docs by Divio type
- [x] T096: Test framework detection (Sphinx, MkDocs, Docusaurus, Jekyll, Hugo, plain markdown)
- [x] T097: Test Divio classification (tutorial, how-to, reference, explanation via heuristics)
- [x] T098: Test coverage matrix shows gaps (project_areas × divio_types grid)
- [x] T099: Test gap prioritization (HIGH for missing tutorials/reference, MEDIUM for how-tos, LOW for explanations)
- [x] T100: Test state persistence across git commit/checkout (meta.json survives)
- [x] T101: Test divio templates accessible during workflow
- [x] T102: Test generators configured correctly (JSDoc, Sphinx, rustdoc)
- [x] T103: Test migration installs documentation mission to .kittify/missions/
- [x] T104: Test migration idempotent (safe to run multiple times, detect() returns False after apply())
- [x] T105: Test backward compatibility (old features without documentation_state handled gracefully)
- [x] T106: Test state validation (invalid iteration_mode, divio_types, generators rejected with clear errors)

### Implementation Notes
1. Create tests/functional/test_documentation_mission_end_to_end.py with 5 test classes:
   - TestInitialMode (T092-T093)
   - TestGapFillingMode (T094-T099)
   - TestStatePersistence (T100-T102)
   - TestMigration (T103-T104)
   - TestValidation (T105-T106)
2. Tests use functional approach (SPEC_KITTY_TEMPLATE_ROOT set for development testing)
3. Tests validate complete workflow: specify → plan → tasks → implement → review
4. Reference: gap_analysis.py, doc_state.py, upgrade/migrations/m_0_12_0_documentation_mission.py

### Parallel Opportunities
- Test classes can be implemented in parallel (independent workflow phases)
- Within classes, tests can be parallelized

### Dependencies
- Depends on WP01 (test environment)
- Can proceed in parallel with WP08 and WP09

### Risks & Mitigations
- **Risk**: Workflow breaks at any phase → documentation mission unusable
- **Mitigation**: Tests catch phase transitions. Fix workflow logic.
- **Risk**: State persistence fails → users lose progress
- **Mitigation**: Validate meta.json survives git operations. Fix state management.

---

## Work Package WP11: Documentation Mission Integration & Validation (Priority: P1)

**Goal**: Run full documentation mission test suite (50 tests), validate all pass, consolidate findings.
**Independent Test**: All 3 documentation test files pass (15+20+15 = 50 tests total)
**Prompt**: `/tasks/WP11-documentation-mission-integration-validation.md`
**Estimated Size**: ~360 lines (6 subtasks)

### Included Subtasks
- [x] T107: Run test_doc_generators_distribution.py → 15/15 PASSED
- [x] T108: Run test_documentation_mission_distribution.py → 20/20 PASSED
- [x] T109: Run test_documentation_mission_end_to_end.py → 15/15 PASSED
- [x] T110: Validate distribution tests use clean_environment (no SPEC_KITTY_TEMPLATE_ROOT)
- [x] T111: Verify test execution time <5 minutes total (distribution <3min, end-to-end <2min)
- [x] T112: Update findings/test-infrastructure/v0.12.0-bugs-found.md with documentation mission bugs

### Implementation Notes
1. Execute full documentation mission validation:
   - pytest tests/distribution/test_doc_generators_distribution.py -v
   - pytest tests/distribution/test_documentation_mission_distribution.py -v
   - pytest tests/functional/test_documentation_mission_end_to_end.py -v
2. Verify test quality: distribution tests truly simulate PyPI users
3. Consolidate findings from WP08-WP10: packaging bugs documented, template issues fixed
4. Verify zero xfails, zero skips - all 50 tests genuinely pass

### Parallel Opportunities
- T107-T109 (test execution) can run in parallel
- T110-T111 (validation) proceed after test execution

### Dependencies
- Depends on WP08-WP10 (all documentation mission tests implemented)
- Independent from WP02-WP07 (different track)

### Risks & Mitigations
- **Risk**: Distribution tests reveal packaging issues (templates missing from package)
- **Mitigation**: Fix pyproject.toml, rebuild package, validate templates accessible
- **Risk**: End-to-end tests reveal workflow bugs
- **Mitigation**: Fix workflow logic, validate phase transitions work

---

## Work Package WP12: Regression Testing & Final Integration (Priority: P1)

**Goal**: Run full test suite (546 tests), achieve ≥95% pass rate, validate v0.12.0 release readiness.
**Independent Test**: `pytest tests/ -v` shows ≥519/546 PASSED (95%+ pass rate), execution <15 minutes
**Prompt**: `/tasks/WP12-regression-testing-final-integration.md`
**Estimated Size**: ~380 lines (7 subtasks)

### Included Subtasks
- [ ] T113: Run full test suite: pytest tests/ -v --tb=line > regression_results.txt
- [ ] T114: Analyze pass rate: (passed / total) ≥ 0.95 (≥519/546 tests)
- [ ] T115: Categorize failures: expected (v0.12.0 behavior changes) vs unexpected (bugs)
- [ ] T116: Document known failures in findings/test-infrastructure/v0.12.0-known-failures.md
- [ ] T117: Verify test execution time <15 minutes on CI/CD
- [ ] T118: Verify all 96 new tests pass (46 sparse-checkout + 50 documentation mission)
- [ ] T119: Finalize findings/test-infrastructure/v0.12.0-bugs-found.md with complete bug list and fixes

### Implementation Notes
1. Execute full regression test suite including existing 450 tests + new 96 tests
2. Categorize failures:
   - Expected: Template format changes, command syntax updates → document in findings/
   - Unexpected: Real bugs → fix or escalate
3. Validate release criteria:
   - All 96 new tests: 100% pass (46/46 sparse-checkout, 50/50 documentation)
   - Existing tests: ≥95% pass (≥427/450)
   - Overall: ≥95% pass rate (≥519/546)
4. Consolidate findings from both tracks: complete bug list, all fixes verified

### Parallel Opportunities
- T113 (test execution) must complete first
- T114-T116 (analysis) can proceed in parallel after test execution
- T117-T119 (validation) can proceed in parallel

### Dependencies
- Depends on WP07 (sparse-checkout track complete)
- Depends on WP11 (documentation mission track complete)
- Final integration of both parallel tracks

### Risks & Mitigations
- **Risk**: Pass rate <95% (too many failures)
- **Mitigation**: Analyze failures, fix critical bugs, document expected behavior changes
- **Risk**: New tests reveal additional spec-kitty bugs
- **Mitigation**: Fix immediately, re-run regression suite, update findings/
- **Risk**: Test execution too slow (>15 minutes)
- **Mitigation**: Optimize slow tests or use pytest-xdist for parallelization

---

## Dependency & Execution Summary

### Sequence
```
WP01 (Setup)
  ├─→ WP02 (Edge Cases) → WP03 (Multi-Agent) → WP04 (Auto-Commit) → WP05 (Worktree) → WP06 (Path/Merge) → WP07 (Integration)
  └─→ WP08 (Doc Generators) ⎤
       WP09 (Doc Mission)    ⎬→ WP11 (Doc Integration)
       WP10 (Doc E2E)        ⎦

WP07 + WP11 → WP12 (Final Regression)
```

### Parallelization Opportunities
- **Track 1 (WP02-WP07) and Track 2 (WP08-WP11) are FULLY PARALLEL** after WP01
- Within Track 1: WP02-WP06 have internal parallelization (subtasks can be split)
- Within Track 2: WP08, WP09, WP10 can proceed simultaneously
- Final integration (WP12) requires both tracks complete

### MVP Scope
**Work Packages 01-07 (Sparse-Checkout Track)** constitute MVP for unblocking workspace-per-WP architecture.
- Validates sparse-checkout infrastructure (foundation)
- Validates auto-commit synchronization (critical for multi-agent)
- Validates edge cases (data corruption prevention)

**Work Packages 08-11 (Documentation Mission Track)** required to ship v0.12.0 without repeating Issues #62-64.
- Validates distribution packaging (no template divergence)
- Validates PyPI user experience (prevent 100% user failure)

**Work Package 12 (Regression)** is MANDATORY before release (validates no regressions, ≥95% pass rate).

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Create scripts/setup-test-env.sh | WP01 | P0 | [P] |
| T002 | Create findings template | WP01 | P0 | [P] |
| T003 | Set up test environment | WP01 | P0 | - |
| T004 | Review existing test patterns | WP01 | P0 | [P] |
| T005 | Create/verify fixtures | WP01 | P0 | [P] |
| T006 | Test corrupted sparse-checkout recovery | WP02 | P1 | [P] |
| T007 | Test missing .git/info directory | WP02 | P1 | [P] |
| T008 | Test permission errors | WP02 | P1 | [P] |
| T009 | Test concurrent commits | WP02 | P1 | [P] |
| T010 | Test worktree migration | WP02 | P1 | [P] |
| T011 | Test manual kitty-specs/ creation | WP02 | P1 | [P] |
| T012 | Test symlink detection | WP02 | P1 | [P] |
| T013 | Test network issues | WP02 | P1 | [P] |
| T014 | Test Agent A/B see each other's status | WP03 | P1 | [P] |
| T015 | Test Agent A marks done → B sees | WP03 | P1 | [P] |
| T016 | Test lane change visibility | WP03 | P1 | [P] |
| T017 | Test three agents synchronized | WP03 | P1 | [P] |
| T018 | Test dependency validation | WP03 | P1 | [P] |
| T019 | Test review feedback insertion | WP03 | P1 | [P] |
| T020 | Test PID in frontmatter | WP03 | P1 | [P] |
| T021 | Test PID in activity log | WP03 | P1 | [P] |
| T022 | Test move-task commits | WP04 | P1 | [P] |
| T023 | Test mark-status commits | WP04 | P1 | [P] |
| T024 | Test workflow implement commits | WP04 | P1 | [P] |
| T025 | Test workflow review commits | WP04 | P1 | [P] |
| T026 | Test commit message agent name | WP04 | P1 | [P] |
| T027 | Test commit message timestamp | WP04 | P1 | [P] |
| T028 | Test parallel agents visibility | WP04 | P1 | [P] |
| T029 | Test auto-commit failure handling | WP04 | P1 | [P] |
| T030 | Test git user config respected | WP04 | P1 | [P] |
| T031 | Test commit history clean | WP04 | P1 | [P] |
| T032 | Test kitty-specs/ excluded | WP05 | P1 | [P] |
| T033 | Test sparse-checkout file patterns | WP05 | P1 | [P] |
| T034 | Test core.sparseCheckout config | WP05 | P1 | [P] |
| T035 | Test core.sparseCheckoutCone config | WP05 | P1 | [P] |
| T036 | Test worktree directory clean | WP05 | P1 | [P] |
| T037 | Test main repo unchanged | WP05 | P1 | [P] |
| T038 | Test multiple worktrees | WP05 | P1 | [P] |
| T039 | Test error handling | WP05 | P1 | [P] |
| T040 | Test tasks finds kitty-specs | WP06 | P1 | [P] |
| T041 | Test move-task finds WP | WP06 | P1 | [P] |
| T042 | Test workflow finds WP | WP06 | P1 | [P] |
| T043 | Test slug strips -WPxx | WP06 | P1 | [P] |
| T044 | Test main repo detection | WP06 | P1 | [P] |
| T045 | Test nested directory paths | WP06 | P1 | [P] |
| T046 | Test merge no conflicts | WP06 | P1 | [P] |
| T047 | Test sequential merges | WP06 | P1 | [P] |
| T048 | Test fast-forward merge | WP06 | P1 | [P] |
| T049 | Test cherry-pick | WP06 | P1 | [P] |
| T050 | Test rebase | WP06 | P1 | [P] |
| T051 | Test merge conditions | WP06 | P1 | [P] |
| T052 | Run sparse-checkout suite | WP07 | P1 | - |
| T053 | Validate execution time | WP07 | P1 | [P] |
| T054 | Verify docstrings | WP07 | P1 | [P] |
| T055 | Verify assertions | WP07 | P1 | [P] |
| T056 | Update findings doc | WP07 | P1 | - |
| T057 | Test JSDoc detection | WP08 | P1 | [P] |
| T058 | Test JSDoc template | WP08 | P1 | [P] |
| T059 | Test JSDoc config | WP08 | P1 | [P] |
| T060 | Test Sphinx detection | WP08 | P1 | [P] |
| T061 | Test Sphinx template | WP08 | P1 | [P] |
| T062 | Test Sphinx config | WP08 | P1 | [P] |
| T063 | Test rustdoc detection | WP08 | P1 | [P] |
| T064 | Test rustdoc template | WP08 | P1 | [P] |
| T065 | Test rustdoc config | WP08 | P1 | [P] |
| T066 | Test importlib access | WP08 | P1 | [P] |
| T067 | Test clean environment | WP08 | P1 | [P] |
| T068 | Test relative paths | WP08 | P1 | [P] |
| T069 | Test multi-language | WP08 | P1 | [P] |
| T070 | Test error handling | WP08 | P1 | [P] |
| T071 | Test no path leakage | WP08 | P1 | [P] |
| T072 | Test mission loads | WP09 | P1 | [P] |
| T073 | Test mission.yaml | WP09 | P1 | [P] |
| T074 | Test mission metadata | WP09 | P1 | [P] |
| T075 | Test workflow phases | WP09 | P1 | [P] |
| T076 | Test required artifacts | WP09 | P1 | [P] |
| T077 | Test optional artifacts | WP09 | P1 | [P] |
| T078 | Test workspace conventions | WP09 | P1 | [P] |
| T079 | Test specify template | WP09 | P1 | [P] |
| T080 | Test plan template | WP09 | P1 | [P] |
| T081 | Test tasks template | WP09 | P1 | [P] |
| T082 | Test implement template | WP09 | P1 | [P] |
| T083 | Test review template | WP09 | P1 | [P] |
| T084 | Test template structure | WP09 | P1 | [P] |
| T085 | Test importlib loading | WP09 | P1 | [P] |
| T086 | Test no path leakage | WP09 | P1 | [P] |
| T087 | Test registry | WP09 | P1 | [P] |
| T088 | Test metadata | WP09 | P1 | [P] |
| T089 | Test get_mission | WP09 | P1 | [P] |
| T090 | Test validation | WP09 | P1 | [P] |
| T091 | Test Divio templates | WP09 | P1 | [P] |
| T092 | Test initial mode | WP10 | P1 | [P] |
| T093 | Test state storage | WP10 | P1 | [P] |
| T094 | Test gap analysis | WP10 | P1 | [P] |
| T095 | Test classification | WP10 | P1 | [P] |
| T096 | Test framework detection | WP10 | P1 | [P] |
| T097 | Test Divio classification | WP10 | P1 | [P] |
| T098 | Test coverage matrix | WP10 | P1 | [P] |
| T099 | Test gap priority | WP10 | P1 | [P] |
| T100 | Test state persistence | WP10 | P1 | [P] |
| T101 | Test divio access | WP10 | P1 | [P] |
| T102 | Test generator config | WP10 | P1 | [P] |
| T103 | Test migration install | WP10 | P1 | [P] |
| T104 | Test migration idempotent | WP10 | P1 | [P] |
| T105 | Test backward compat | WP10 | P1 | [P] |
| T106 | Test validation | WP10 | P1 | [P] |
| T107 | Run doc generators tests | WP11 | P1 | [P] |
| T108 | Run mission tests | WP11 | P1 | [P] |
| T109 | Run end-to-end tests | WP11 | P1 | [P] |
| T110 | Verify clean env usage | WP11 | P1 | [P] |
| T111 | Validate execution time | WP11 | P1 | [P] |
| T112 | Update findings | WP11 | P1 | - |
| T113 | Run full test suite | WP12 | P1 | - |
| T114 | Analyze pass rate | WP12 | P1 | - |
| T115 | Categorize failures | WP12 | P1 | - |
| T116 | Document known failures | WP12 | P1 | - |
| T117 | Verify execution time | WP12 | P1 | [P] |
| T118 | Verify new tests | WP12 | P1 | [P] |
| T119 | Finalize findings | WP12 | P1 | - |