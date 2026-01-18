---
work_package_id: "WP02"
subtasks:
  - "T008"
  - "T009"
  - "T010"
  - "T011"
  - "T012"
  - "T013"
  - "T014"
title: "Pre-flight Validation Tests"
phase: "Phase 1 - MVP"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP01"]
history:
  - timestamp: "2026-01-18T12:27:56Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 – Pre-flight Validation Tests

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if work is returned.]*

---

## Implementation Command

```bash
spec-kitty implement WP02 --base WP01
```

Depends on WP01 for fixtures.

---

## Objectives & Success Criteria

Implement tests for **User Story 1 - Pre-flight Validation** (FR-005 to FR-008):

1. **FR-005**: Verify uncommitted changes in worktrees are detected and reported
2. **FR-006**: Verify target branch divergence is detected and reported
3. **FR-007**: Verify all issues are collected and displayed together (not one-at-a-time)
4. **FR-008**: Verify pre-flight failure exits with non-zero code without modifying branches

**Success**: `pytest tests/functional/test_merge_preflight.py -v` passes with all acceptance scenarios covered.

---

## Context & Constraints

### Related Documents
- Spec: `kitty-specs/003-merge-feature-test-suite/spec.md` - User Story 1
- Feature 017 Spec: `/Users/robert/Code/spec-kitty/kitty-specs/017-smarter-feature-merge-with-preflight/spec.md`

### Acceptance Scenarios from Spec
1. Feature with 3 WP worktrees where 2 have uncommitted changes → lists all 3 WPs with status
2. Target branch diverged from origin → reports divergence and suggests remediation
3. All worktrees clean + target up-to-date → pre-flight passes
4. Deleted worktree but branch exists → detects inconsistency

### Key Behaviors to Test
- Pre-flight runs BEFORE any merge operation
- All blockers reported in one output (not discovered one-by-one)
- Exit code is non-zero when pre-flight fails
- No branch modifications on failure

---

## Subtasks & Detailed Guidance

### Subtask T008 – Create test_merge_preflight.py module

**Purpose**: Establish the test file structure.

**Steps**:
1. Create `tests/functional/test_merge_preflight.py`
2. Add imports for fixtures from `test_merge_fixtures.py`
3. Add module docstring
4. Add `requires_v011` marker for version gating

**Files**: `tests/functional/test_merge_preflight.py` (new, ~30 lines initially)

**Parallel?**: No - foundation for other subtasks

**Template**:
```python
"""
Tests for spec-kitty merge pre-flight validation.

Validates User Story 1 from Feature 003 spec:
- Dirty worktrees detected and reported
- Target branch divergence detected
- All issues reported together
- Non-zero exit without branch modifications

Requires spec-kitty >= 0.11.0 (workspace-per-WP).
"""
import subprocess
from pathlib import Path

import pytest

from tests.conftest import requires_v011
from tests.functional.test_merge_fixtures import (
    WPFixture,
    create_test_feature,
)


@requires_v011
class TestMergePreflightValidation:
    """Tests for pre-flight validation before merge."""
    pass
```

---

### Subtask T009 – Test dirty worktrees are detected (FR-005)

**Purpose**: Verify uncommitted changes in worktrees are detected and reported.

**Steps**:
1. Create feature with 2 WPs, one with dirty worktree
2. Run `spec-kitty merge`
3. Assert output contains WP status indicators
4. Assert exit code is non-zero

**Files**: `tests/functional/test_merge_preflight.py` (~40 lines)

**Parallel?**: Yes - independent test

**Code**:
```python
def test_dirty_worktree_detected(self, create_test_feature):
    """Pre-flight detects uncommitted changes in worktrees (FR-005)."""
    feature = create_test_feature(
        wp_configs=[
            WPFixture("WP01", lane="done"),
            WPFixture("WP02", lane="done", dirty=True),  # Has uncommitted changes
        ]
    )

    result = subprocess.run(
        ["spec-kitty", "merge"],
        cwd=feature.project_dir,
        capture_output=True,
        text=True,
    )

    # Pre-flight should fail
    assert result.returncode != 0, f"Expected non-zero exit, got: {result.stdout}"

    # Output should mention dirty/uncommitted
    output = result.stdout + result.stderr
    assert "WP02" in output, "Should mention the dirty WP"
    assert any(word in output.lower() for word in ["uncommitted", "dirty", "changes"]), \
        f"Should indicate uncommitted changes: {output}"
```

---

### Subtask T010 – Test multiple dirty worktrees reported together (FR-007)

**Purpose**: Verify all issues are collected and displayed together, not one at a time.

**Steps**:
1. Create feature with 3 WPs, 2 with dirty worktrees
2. Run `spec-kitty merge`
3. Assert BOTH dirty WPs mentioned in single output
4. Assert both appear before any "fix and retry" message

**Files**: `tests/functional/test_merge_preflight.py` (~45 lines)

**Parallel?**: Yes - independent test

**Code**:
```python
def test_multiple_dirty_worktrees_reported_together(self, create_test_feature):
    """Pre-flight reports ALL issues together, not one at a time (FR-007)."""
    feature = create_test_feature(
        wp_configs=[
            WPFixture("WP01", lane="done"),
            WPFixture("WP02", lane="done", dirty=True),
            WPFixture("WP03", lane="done", dirty=True),
        ]
    )

    result = subprocess.run(
        ["spec-kitty", "merge"],
        cwd=feature.project_dir,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    output = result.stdout + result.stderr

    # Both dirty WPs should be mentioned in the same output
    assert "WP02" in output, "Should mention WP02"
    assert "WP03" in output, "Should mention WP03"

    # They should appear in a consolidated list, not discovered iteratively
    # The key indicator is that we see all issues without having to run merge multiple times
    wp02_pos = output.find("WP02")
    wp03_pos = output.find("WP03")
    assert wp02_pos != -1 and wp03_pos != -1, "Both WPs should be in output"
```

---

### Subtask T011 – Test target branch divergence detected (FR-006)

**Purpose**: Verify target branch divergence from origin is detected.

**Steps**:
1. Create feature with clean worktrees
2. Simulate target branch divergence (add commit to main not on origin)
3. Run `spec-kitty merge`
4. Assert output mentions divergence/sync issue

**Files**: `tests/functional/test_merge_preflight.py` (~50 lines)

**Parallel?**: Yes - independent test

**Note**: This test may need a remote (bare repo) to test origin divergence. Alternative: skip if no remote configured and document.

**Code**:
```python
def test_target_branch_divergence_detected(self, create_test_feature, tmp_path):
    """Pre-flight detects when target branch has diverged from origin (FR-006)."""
    # Create a bare "remote" repo
    remote_path = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(remote_path)], check=True, capture_output=True)

    feature = create_test_feature(
        wp_configs=[
            WPFixture("WP01", lane="done"),
        ]
    )

    # Add remote and push
    subprocess.run(
        ["git", "remote", "add", "origin", str(remote_path)],
        cwd=feature.project_dir,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "push", "-u", "origin", "main"],
        cwd=feature.project_dir,
        check=True,
        capture_output=True,
    )

    # Make local commit that diverges from origin
    (feature.project_dir / "diverge.txt").write_text("local only")
    subprocess.run(["git", "add", "."], cwd=feature.project_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Local divergence"],
        cwd=feature.project_dir,
        check=True,
        capture_output=True,
    )

    result = subprocess.run(
        ["spec-kitty", "merge"],
        cwd=feature.project_dir,
        capture_output=True,
        text=True,
    )

    # Should warn about divergence (may or may not fail depending on implementation)
    output = result.stdout + result.stderr
    # Look for divergence-related messaging
    assert any(word in output.lower() for word in ["diverge", "ahead", "sync", "pull"]), \
        f"Should mention branch divergence: {output}"
```

---

### Subtask T012 – Test non-zero exit without branch modification (FR-008)

**Purpose**: Verify pre-flight failure doesn't modify any branches.

**Steps**:
1. Create feature with dirty worktree
2. Record branch state (git log) before merge
3. Run `spec-kitty merge` (should fail)
4. Verify branch state unchanged

**Files**: `tests/functional/test_merge_preflight.py` (~45 lines)

**Parallel?**: Yes - independent test

**Code**:
```python
def test_preflight_failure_no_branch_modification(self, create_test_feature):
    """Pre-flight failure exits non-zero WITHOUT modifying branches (FR-008)."""
    feature = create_test_feature(
        wp_configs=[
            WPFixture("WP01", lane="done", dirty=True),
        ]
    )

    # Record main branch state before
    before_result = subprocess.run(
        ["git", "log", "--oneline", "-1", "main"],
        cwd=feature.project_dir,
        capture_output=True,
        text=True,
    )
    before_commit = before_result.stdout.strip()

    # Attempt merge (should fail pre-flight)
    result = subprocess.run(
        ["spec-kitty", "merge"],
        cwd=feature.project_dir,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0, "Should exit non-zero"

    # Verify main branch unchanged
    after_result = subprocess.run(
        ["git", "log", "--oneline", "-1", "main"],
        cwd=feature.project_dir,
        capture_output=True,
        text=True,
    )
    after_commit = after_result.stdout.strip()

    assert before_commit == after_commit, \
        f"Main branch should be unchanged. Before: {before_commit}, After: {after_commit}"
```

---

### Subtask T013 – Test clean worktrees pass pre-flight

**Purpose**: Verify happy path - clean worktrees with up-to-date target passes.

**Steps**:
1. Create feature with all clean worktrees
2. Run `spec-kitty merge`
3. Assert merge proceeds (exit code 0 or merge-related output)

**Files**: `tests/functional/test_merge_preflight.py` (~35 lines)

**Parallel?**: Yes - independent test

**Code**:
```python
def test_clean_worktrees_pass_preflight(self, create_test_feature):
    """Clean worktrees with up-to-date target pass pre-flight."""
    feature = create_test_feature(
        wp_configs=[
            WPFixture("WP01", lane="done"),
            WPFixture("WP02", lane="done"),
        ]
    )

    result = subprocess.run(
        ["spec-kitty", "merge"],
        cwd=feature.project_dir,
        capture_output=True,
        text=True,
    )

    output = result.stdout + result.stderr

    # Should either succeed or proceed to actual merge
    # (might still fail due to conflicts, but NOT due to pre-flight)
    assert "pre-flight" not in output.lower() or "passed" in output.lower() or result.returncode == 0, \
        f"Clean worktrees should pass pre-flight: {output}"
```

---

### Subtask T014 – Test deleted worktree detection

**Purpose**: Verify detection of deleted worktree when branch still exists.

**Steps**:
1. Create feature with 2 WPs
2. Manually delete one worktree directory (but keep branch)
3. Run `spec-kitty merge`
4. Assert inconsistency is detected

**Files**: `tests/functional/test_merge_preflight.py` (~45 lines)

**Parallel?**: Yes - independent test

**Code**:
```python
def test_deleted_worktree_detected(self, create_test_feature):
    """Pre-flight detects deleted worktree when branch still exists."""
    feature = create_test_feature(
        wp_configs=[
            WPFixture("WP01", lane="done"),
            WPFixture("WP02", lane="done"),
        ]
    )

    # Manually delete WP02 worktree directory (simulate user error)
    wp02_path = feature.get_worktree_path("WP02")
    if wp02_path and wp02_path.exists():
        import shutil
        shutil.rmtree(wp02_path)

    result = subprocess.run(
        ["spec-kitty", "merge"],
        cwd=feature.project_dir,
        capture_output=True,
        text=True,
    )

    output = result.stdout + result.stderr

    # Should detect the inconsistency
    assert result.returncode != 0 or "WP02" in output, \
        f"Should detect missing worktree: {output}"
```

---

## Test Strategy

Run all tests with:
```bash
pytest tests/functional/test_merge_preflight.py -v
```

Expected: 6 tests, all passing.

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Output format varies by version | Use flexible assertions (contains, not exact match) |
| Remote/origin testing complex | Use local bare repo as simulated remote |
| Dirty state detection flaky | Use explicit `git status --porcelain` verification |

---

## Definition of Done Checklist

- [ ] `tests/functional/test_merge_preflight.py` exists
- [ ] Test: dirty worktree detected (FR-005)
- [ ] Test: multiple issues reported together (FR-007)
- [ ] Test: target divergence detected (FR-006)
- [ ] Test: non-zero exit without branch modification (FR-008)
- [ ] Test: clean worktrees pass pre-flight
- [ ] Test: deleted worktree detected
- [ ] All tests pass: `pytest tests/functional/test_merge_preflight.py -v`

---

## Review Guidance

- Verify tests actually exercise spec-kitty merge command
- Check assertions are meaningful (not just "doesn't crash")
- Ensure tests are isolated (no shared state between tests)
- Verify FR coverage is complete

---

## Activity Log

- 2026-01-18T12:27:56Z – system – lane=planned – Prompt created.
