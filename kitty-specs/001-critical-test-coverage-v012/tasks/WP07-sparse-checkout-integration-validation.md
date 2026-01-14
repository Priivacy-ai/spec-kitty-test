---
work_package_id: WP07
title: Sparse-Checkout Integration & Validation
lane: "planned"
dependencies:
- WP02
subtasks:
- T052
- T053
- T054
- T055
- T056
phase: Phase 1 - Sparse-Checkout Track (Final Integration)
assignee: ''
agent: "codex"
shell_pid: "50612"
review_status: "has_feedback"
reviewed_by: "Robert Douglass"
history:
- timestamp: '2026-01-14T20:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP07 – Sparse-Checkout Integration & Validation

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: Update `review_status: acknowledged` in the frontmatter.
- **Report progress**: Update Activity Log explaining changes made.

---

## Review Feedback

**Reviewed by**: Robert Douglass
**Status**: ❌ Changes Requested
**Date**: 2026-01-14

**Issue 1**: Test execution does not meet success criteria. `sparse_checkout_results.txt` shows 38 passed and 8 skipped (not 46/46 pass, zero skips/xfails). Rerun the full suite and make all tests pass without skips, or fix the skips. Evidence: sparse_checkout_results.txt summary line.

**Issue 2**: Suite 5 tests in the results are still the old scenarios (`test_merge_doesnt_restore_excluded_files`, `test_merge_preserves_sparse_checkout_patterns`) instead of the required fast-forward and diverged-merge cases. This indicates the WP07 worktree is not updated to the current WP06 test set (missing FF and merge-commit coverage). Rebase/update and ensure the required tests are present and passing.

**Issue 3**: `findings/test-infrastructure/v0.12.0-bugs-found.md` is inconsistent and incomplete. The summary claims all bugs fixed, but individual bug sections are marked "Not yet fixed". It also documents skipped tests as passing and does not include a complete list from WP02–WP06. Update the bug report to include all bugs with correct status and verification.

**Issue 4**: Performance report required by T053 is missing. Create/update `findings/test-infrastructure/v0.12.0-sparse-checkout-performance.md` with execution time from the full suite and confirm <5 minutes.


## Objectives & Success Criteria

**Primary Objective**: Run full sparse-checkout test suite (46 tests across 6 suites), validate all pass, document all bugs found during WP02-WP06.

**Success Criteria**:
- ✅ All 46 sparse-checkout tests pass: `pytest tests/functional/test_sparse_checkout_infrastructure.py -v` shows 46/46 PASSED
- ✅ Test execution time <5 minutes
- ✅ All test classes have clear docstrings
- ✅ All tests have clear docstrings with implementation references
- ✅ All assertions include contextual debugging information
- ✅ findings/test-infrastructure/v0.12.0-bugs-found.md updated with complete bug list from WP02-WP06
- ✅ All bugs fixed and verified (or documented as deferred with rationale)
- ✅ Zero xfails, zero skips - all tests genuinely pass

**Definition of Complete**: Running full sparse-checkout test suite shows 46/46 PASSED in <5 minutes, all bugs from adversarial testing documented and fixed, sparse-checkout infrastructure validated as production-ready.

---

## Context & Constraints

### Related Documents
- **Spec**: kitty-specs/001-critical-test-coverage-v012/spec.md (SC-001: 46/46 tests passing)
- **Plan**: kitty-specs/001-critical-test-coverage-v012/plan.md (adversarial testing approach)
- **Findings**: findings/test-infrastructure/v0.12.0-bugs-found.md (bug documentation template)

### Test Suite Structure (from WP02-WP06)
- **Suite 1 (WP05)**: Worktree Creation (8 tests) - sparse-checkout configuration
- **Suite 2 (WP06)**: Path Resolution (6 tests) - finding kitty-specs from worktree
- **Suite 3 (WP04)**: Auto-Commit (10 tests) - synchronization mechanism
- **Suite 4 (WP03)**: Multi-Agent (8 tests) - parallel development
- **Suite 5 (WP06)**: Merge Behavior (6 tests) - clean git merges
- **Suite 6 (WP02)**: Edge Cases (8 tests) - error handling, recovery
- **Total**: 46 tests

### Integration Testing Philosophy
- **Validate end-to-end**: Run all 46 tests in single execution
- **Validate test quality**: Review docstrings, assertions, error messages
- **Validate performance**: <5 minutes execution (fast enough for CI/CD)
- **Consolidate findings**: All bugs documented, severity assessed, fixes verified
- **Release readiness**: Zero tolerance for failures - all 46 must pass

---

## Subtasks & Detailed Guidance

### Subtask T052 – Run complete sparse-checkout test suite (all 6 suites, 46 tests)

**Purpose**: Execute full sparse-checkout test suite in single run, validate all tests pass.

**Steps**:

1. Run full test suite:

```bash
pytest tests/functional/test_sparse_checkout_infrastructure.py -v --tb=line > sparse_checkout_results.txt
```

2. Review output for pass/fail status:

```bash
# Check summary line
grep "passed" sparse_checkout_results.txt

# Expected output: "46 passed in X.XXs"
```

3. Validate all test classes executed:

```bash
# Should see all 6 test classes
grep -E "Test(WorktreeCreation|PathResolution|AutoCommitSynchronization|MultiAgentParallel|CleanMergeBehavior|EdgeCases)" sparse_checkout_results.txt
```

4. If ANY test fails:
   - Stop immediately (fail-fast)
   - Investigate failure (read stderr, check file paths, inspect git state)
   - Determine if test bug or implementation bug
   - Fix bug (in test or ~/Code/spec-kitty)
   - Document in findings/test-infrastructure/v0.12.0-bugs-found.md
   - Re-run full suite from step 1

5. Validate zero skips, zero xfails:

```bash
# Should NOT see "skipped" or "xfail" in summary
grep -E "skipped|xfail" sparse_checkout_results.txt
# If found → investigate why test skipped, fix or remove skip
```

6. Capture success metrics:

```python
# Extract from output
# - Total tests: 46
# - Pass rate: 100% (46/46)
# - Execution time: X.XX seconds
# - Zero failures, zero skips, zero xfails
```

**Files**:
- Create: `sparse_checkout_results.txt` (test execution output)
- Update: findings/test-infrastructure/v0.12.0-bugs-found.md (if bugs found)

**Parallel?**: No - Must complete before T053-T056

**Validation**:
- pytest exit code: 0 (success)
- Summary line: "46 passed"
- No "FAILED", "skipped", or "xfailed" in output

**Edge Cases**:
- Test failures: Stop, fix, re-run
- Test hangs (>10 minutes): Kill pytest, investigate hanging test, add timeout
- Flaky tests (intermittent failures): Zero tolerance - make deterministic

---

### Subtask T053 – Validate test execution time <5 minutes

**Purpose**: Ensure sparse-checkout test suite fast enough for CI/CD workflows.

**Steps**:

1. Parse execution time from pytest output:

```bash
# From sparse_checkout_results.txt, extract time
grep "passed in" sparse_checkout_results.txt
# Output: "46 passed in 2.45s" or "46 passed in 3m 22s"
```

2. Validate <5 minutes (300 seconds):

```python
# Parse time
# If format: "X.XXs" → convert to seconds
# If format: "Xm XXs" → convert to seconds (minutes * 60 + seconds)

execution_time_seconds = ...  # Parse from output

assert execution_time_seconds < 300, (
    f"Test execution too slow: {execution_time_seconds}s (limit: 300s)\n"
    f"Target: <5 minutes for CI/CD\n"
    f"If too slow, profile tests with --durations=10"
)
```

3. If execution time >5 minutes, profile slow tests:

```bash
pytest tests/functional/test_sparse_checkout_infrastructure.py -v --durations=10
# Shows 10 slowest tests
```

4. Optimize slow tests:
   - Reduce git operations (use minimal commits)
   - Reduce worktree creation (reuse where possible)
   - Remove unnecessary sleeps or timeouts
   - Parallelize independent operations

5. Document performance:

```markdown
# Sparse-Checkout Test Suite Performance

- Total tests: 46
- Execution time: 2.45s (well under 5-minute target)
- Average per test: 0.05s
- Slowest test: test_three_agents_all_synchronized (0.8s)
- Suite breakdown:
  - Suite 1 (Worktree Creation): 0.4s (8 tests)
  - Suite 2 (Path Resolution): 0.3s (6 tests)
  - Suite 3 (Auto-Commit): 0.6s (10 tests)
  - Suite 4 (Multi-Agent): 0.7s (8 tests)
  - Suite 5 (Merge Behavior): 0.3s (6 tests)
  - Suite 6 (Edge Cases): 0.5s (8 tests)
```

**Files**:
- Update: findings/test-infrastructure/v0.12.0-sparse-checkout-performance.md (performance report)

**Parallel?**: Yes [P] - Can proceed in parallel with T054-T055

**Validation**:
- Execution time <5 minutes
- If slow, profile and optimize

**Edge Cases**:
- CI/CD slower than local (acceptable if <5min)
- Parallel pytest (pytest-xdist) if needed for speed

---

### Subtask T054 – Verify all tests have clear docstrings

**Purpose**: Validate test quality - every test has docstring explaining what/why/reference.

**Steps**:

1. Read test file and verify docstring format:

```bash
# Extract all test docstrings
grep -A 10 "def test_" tests/functional/test_sparse_checkout_infrastructure.py | grep '"""'
```

2. Validate docstring structure for each test:

```python
# Expected format:
"""
Test: <what is being tested>

Why: <why this test matters - business/technical justification>

Reference: <file.py:lines - implementation code location>
Related: <related concepts, issues, or tests>
"""
```

3. Check completeness:
   - All 46 tests have docstrings (not just first few)
   - Each docstring has "Test:" line (what)
   - Each docstring has "Why:" line (justification)
   - Each docstring has "Reference:" line (implementation code)
   - Class docstrings explain test category

4. Read random sample (10 tests) for quality:
   - Docstring explains behavior being tested
   - "Why" explains business or technical importance
   - Reference points to actual implementation code location
   - No generic/placeholder docstrings

5. Document findings:

```markdown
## Test Documentation Quality

- Total tests with docstrings: 46/46 (100%)
- Docstring format compliance: 46/46 (100%)
- Implementation references: 46/46 (100%)
- Sample quality review: 10/10 tests have clear, specific docstrings

### Example (high quality):
```python
def test_kitty_specs_excluded_from_worktree(self, ...):
    """
    Test: kitty-specs/ excluded from worktree working directory

    Why: Core requirement of sparse-checkout - kitty-specs/ should NOT
    appear in worktree. Prevents agents from modifying specs in worktree,
    ensuring single source of truth in main repo.

    Reference: implement.py:596-642 (sparse-checkout setup)
    Related: Data integrity, state divergence prevention
    """
```
```

**Files**:
- Review: tests/functional/test_sparse_checkout_infrastructure.py (all test docstrings)

**Parallel?**: Yes [P] - Can proceed in parallel with T053, T055

**Validation**:
- All 46 tests have docstrings
- Docstrings follow format (Test, Why, Reference)
- Quality spot-check passes

---

### Subtask T055 – Verify all assertions include context

**Purpose**: Validate assertion quality - every assertion has debugging context in failure message.

**Steps**:

1. Search for assertions in test file:

```bash
# Find all assert statements
grep "assert " tests/functional/test_sparse_checkout_infrastructure.py | wc -l
# Expected: ~100-150 assertions across 46 tests
```

2. Validate assertion format:

```python
# GOOD assertion (has context):
assert result.returncode == 0, (
    f"Worktree creation failed\n"
    f"Error: {result.stderr}\n"
    f"Command: spec-kitty implement WP01\n"
    f"If error mentions sparse-checkout, configuration failed"
)

# BAD assertion (no context):
assert result.returncode == 0

# BAD assertion (minimal context):
assert result.returncode == 0, "Command failed"
```

3. Check sample assertions (20 random assertions):
   - Assertion includes failure message
   - Message includes relevant variables (stderr, stdout, paths, git state)
   - Message explains what to check if assertion fails
   - Message provides debugging guidance

4. Validate critical assertions have extra context:
   - File existence checks: Include file path, parent directory contents
   - Command failures: Include stderr, stdout, command executed
   - Content checks: Include snippet of actual content vs. expected
   - Git operations: Include git log, status, branch info

5. Document findings:

```markdown
## Assertion Quality

- Total assertions: ~120
- Assertions with context: ~110/120 (92%)
- High-quality context (vars + guidance): ~90/120 (75%)

### Good examples:
- test_kitty_specs_excluded_from_worktree: Assertion includes worktree path, kitty-specs path, explanation of data integrity bug
- test_move_task_commits_specific_file_only: Assertion shows committed files list, explains "too broad" bug

### Areas for improvement:
- 5 assertions in edge case tests could add git state context
- 3 assertions in merge tests could show branch names in error
```

**Files**:
- Review: tests/functional/test_sparse_checkout_infrastructure.py (all assertions)

**Parallel?**: Yes [P] - Can proceed in parallel with T053, T054

**Validation**:
- >90% assertions have contextual messages
- Critical assertions (file existence, command failures) have detailed context

---

### Subtask T056 – Update findings/test-infrastructure/v0.12.0-bugs-found.md with complete bug list

**Purpose**: Consolidate all bugs found during WP02-WP06 adversarial testing into comprehensive bug report.

**Steps**:

1. Review findings from each work package:
   - WP02 (Edge Cases): Likely found corruption handling bugs, permission errors
   - WP03 (Multi-Agent): Likely found synchronization bugs, PID tracking gaps
   - WP04 (Auto-Commit): Likely found broad commit bugs, message format issues
   - WP05 (Worktree Creation): Likely found config bugs, sparse-checkout setup issues
   - WP06 (Path Resolution & Merge): Likely found path resolution bugs, merge issues

2. Consolidate bugs into findings/test-infrastructure/v0.12.0-bugs-found.md:

```markdown
# Bugs Found During v0.12.0 Adversarial Testing

**Testing Period**: 2026-01-14 to 2026-01-15
**Tracks**: Sparse-checkout infrastructure (46 tests)
**Philosophy**: Fail-fast, zero tolerance, fix before continuing

## Summary

Total bugs found: 12
- Critical: 3 (data corruption, silent failures, broad commits)
- High: 5 (synchronization issues, path resolution)
- Medium: 3 (error messages unclear, PID tracking gaps)
- Low: 1 (performance optimization)

**All bugs fixed and verified** (except 1 deferred - see Bug #8)

---

## Bug #1: Auto-commit commits entire working tree (not specific file)

**Test**: test_move_task_commits_specific_file_only (WP04)
**Severity**: CRITICAL
**Found**: 2026-01-14
**Fixed**: 2026-01-14

**Symptoms**:
- move-task committed all staged files, not just WP prompt file
- Test created unrelated staged file (notes.txt), it was committed
- User's work-in-progress code at risk of accidental commits

**Root Cause**:
- tasks.py:450 used `git add .` instead of `git add <specific_wp_file>`
- Broad git add committed entire working tree

**Fix Applied**:
- Changed to `git add {wp_file_path}` (specific file only)
- File: ~/Code/spec-kitty/src/specify_cli/cli/commands/agent/tasks.py
- Lines: 448-452
- Commit: abc123def

**Verification**:
- Test now passes: move-task commits only WP file
- Created 3 additional tests for mark-status, workflow implement/review
- All targeted commit tests pass (4/4)

---

## Bug #2: Synchronization reads from worktree copy (not main repo)

**Test**: test_parallel_agents_see_each_others_status (WP03)
**Severity**: CRITICAL
**Found**: 2026-01-14
**Fixed**: 2026-01-14

**Symptoms**:
- Agent A moved WP01 to for_review
- Agent B's task list still showed WP01 as "doing"
- Agents saw divergent state (synchronization broken)

**Root Cause**:
- tasks.py:120 read tasks.md from current directory
- In worktree, read stale worktree copy of tasks.md
- Should read from main repo (single source of truth)

**Fix Applied**:
- Changed to always read from main repo: `_get_main_repo_root() / 'kitty-specs' / ...`
- File: ~/Code/spec-kitty/src/specify_cli/cli/commands/agent/tasks.py
- Lines: 118-125
- Commit: def456ghi

**Verification**:
- Test now passes: Agent B sees Agent A's changes
- Created 5 additional synchronization tests
- All multi-agent tests pass (8/8)

---

[Continue for all 12 bugs found...]
```

3. Validate bug documentation completeness:
   - Each bug has all required fields (Test, Severity, Found, Fixed, Symptoms, Root Cause, Fix Applied, Verification)
   - Severity correctly assessed (CRITICAL for data corruption/divergence)
   - Fix commits referenced (commit hash or file:line)
   - Verification shows test now passes

4. Validate all bugs fixed:
   - Count bugs with "Fixed: YYYY-MM-DD" vs. "Not yet fixed"
   - Should be 100% fixed (or 1-2 deferred with clear rationale)
   - Deferred bugs must have mitigation plan

5. Update summary metrics:
   ```markdown
   ## Summary

   Total bugs found: 12
   - Critical: 3 (all fixed)
   - High: 5 (all fixed)
   - Medium: 3 (all fixed)
   - Low: 1 (deferred - performance optimization, not blocking)

   **Release readiness**: All critical and high bugs fixed. Sparse-checkout infrastructure production-ready.
   ```

**Files**:
- Update: `findings/test-infrastructure/v0.12.0-bugs-found.md` (complete bug report)

**Parallel?**: No - Depends on T052 (all tests passing)

**Validation**:
- All bugs documented with complete information
- All critical/high bugs fixed
- Test results confirm fixes work

---

## Test Strategy

**Integration Testing Approach**:
1. Run full suite (T052): Validate 46/46 pass
2. Performance check (T053): Validate <5 minutes
3. Quality review (T054-T055): Validate documentation and assertions
4. Consolidate findings (T056): Document all bugs found

**Success Metrics**:
- Pass rate: 100% (46/46)
- Execution time: <5 minutes
- Documentation: 100% (all tests have docstrings)
- Bug fixes: 100% critical/high bugs fixed

---

## Risks & Mitigations

**Risk 1: Integration reveals new bugs (test interaction)**
- **Likelihood**: MEDIUM (integration often surfaces new issues)
- **Impact**: HIGH (blocks release)
- **Mitigation**: EXPECTED - fix immediately, re-run full suite, document in findings

**Risk 2: Test execution >5 minutes (too slow for CI/CD)**
- **Likelihood**: LOW (individual tests fast)
- **Impact**: MEDIUM (slower CI/CD)
- **Mitigation**: Profile with --durations=10, optimize slow tests, use pytest-xdist

**Risk 3: Bugs not fully fixed (tests still failing)**
- **Likelihood**: LOW (incremental testing during WP02-WP06)
- **Impact**: HIGH (blocks release)
- **Mitigation**: Zero tolerance - all tests must pass before WP07 complete

---

## Definition of Done Checklist

- [ ] Full sparse-checkout test suite executed: `pytest tests/functional/test_sparse_checkout_infrastructure.py -v`
- [ ] Test results: 46/46 PASSED (100% pass rate)
- [ ] Execution time: <5 minutes (documented)
- [ ] Zero skips, zero xfails (all tests genuinely pass)
- [ ] All test docstrings complete (Test, Why, Reference)
- [ ] All assertions have contextual messages (>90%)
- [ ] findings/test-infrastructure/v0.12.0-bugs-found.md updated with complete bug list
- [ ] All critical and high severity bugs fixed
- [ ] All bug fixes verified (tests pass)
- [ ] Sparse-checkout infrastructure validated as production-ready

---

## Review Guidance

**For Reviewer**:

1. **Validate test execution**:
   ```bash
   pytest tests/functional/test_sparse_checkout_infrastructure.py -v --tb=line
   ```
   - Should see 46/46 PASSED
   - Execution time <5 minutes
   - No failures, skips, or xfails

2. **Validate test quality**:
   - Spot-check 10 random test docstrings (complete and clear)
   - Spot-check 10 random assertions (have context)
   - Read class docstrings (explain test category)

3. **Validate bug documentation**:
   - Read findings/test-infrastructure/v0.12.0-bugs-found.md
   - All bugs have complete information
   - All critical/high bugs marked as fixed
   - Verify fixes by reviewing test results

4. **Validate release readiness**:
   - All 46 tests pass
   - All critical bugs fixed
   - Test suite fast enough for CI/CD
   - Documentation complete

**Key Questions**:
- Do all 46 tests genuinely pass (not xfail or skip)?
- Are all critical bugs fixed and verified?
- Is test suite fast enough for CI/CD (<5 minutes)?
- Is documentation complete (docstrings, assertions, bug reports)?

---

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-01-14T20:00:00Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-14T16:26:51Z – claude-opus – shell_pid=52131 – lane=doing – Started implementation via workflow command
- 2026-01-14T16:33:38Z – claude-opus – shell_pid=52131 – lane=for_review – Moved to for_review
- 2026-01-14T16:34:14Z – codex – shell_pid=50612 – lane=doing – Started review via workflow command
- 2026-01-14T16:34:55Z – codex – shell_pid=50612 – lane=planned – Moved to planned
