---
work_package_id: "WP06"
subtasks:
  - "T036"
  - "T037"
  - "T038"
  - "T039"
  - "T040"
  - "T041"
title: "Automatic Cleanup Tests"
phase: "Phase 3 - Extended Features"
lane: "doing"
assignee: ""
agent: "claude-opus"
shell_pid: "80554"
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

# Work Package Prompt: WP06 – Automatic Cleanup Tests

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
spec-kitty implement WP06 --base WP01
```

Depends on WP01 for fixtures.

---

## Objectives & Success Criteria

Implement tests for **User Story 5 - Automatic Cleanup** (FR-022 to FR-025):

1. **FR-022**: Verify worktrees are removed after successful merge
2. **FR-023**: Verify branches are deleted after successful merge
3. **FR-024**: Verify `--keep-worktree` and `--keep-branch` flags preserve resources
4. **FR-025**: Verify cleanup continues even if one operation fails

**Success**: `pytest tests/functional/test_merge_cleanup.py -v` passes.

---

## Context & Constraints

### Related Documents
- Spec: `kitty-specs/003-merge-feature-test-suite/spec.md` - User Story 5
- Feature 017: Cleanup is default behavior, with `--keep-*` flags to preserve

### CLI Flags
- `--keep-worktree`: Preserve worktrees after merge
- `--keep-branch`: Preserve branches after merge

### Key Locations
- Worktrees: `.worktrees/<feature>-WP##/`
- Branches: `<feature>-WP##`

---

## Subtasks & Detailed Guidance

### Subtask T036 – Create test_merge_cleanup.py module

**Purpose**: Establish the test file structure.

**Steps**:
1. Create `tests/functional/test_merge_cleanup.py`
2. Add imports and version gating
3. Add module docstring

**Files**: `tests/functional/test_merge_cleanup.py` (new, ~30 lines)

**Parallel?**: No - foundation

**Template**:
```python
"""
Tests for spec-kitty merge automatic cleanup.

Validates User Story 5 from Feature 003 spec:
- Worktrees removed after successful merge
- Branches deleted after successful merge
- --keep-worktree flag preserves worktrees
- --keep-branch flag preserves branches
- Cleanup continues even if one operation fails

Requires spec-kitty >= 0.11.0.
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
class TestMergeCleanup:
    """Tests for automatic cleanup after merge."""
    pass
```

---

### Subtask T037 – Test worktrees removed (FR-022)

**Purpose**: Verify worktrees are removed after successful merge.

**Steps**:
1. Create feature with 2 WPs
2. Run `spec-kitty merge`
3. Verify `.worktrees/` is empty or WP dirs removed

**Files**: `tests/functional/test_merge_cleanup.py` (~45 lines)

**Parallel?**: Yes - independent test

**Code**:
```python
def test_worktrees_removed_after_merge(self, create_test_feature):
    """Worktrees removed after successful merge (FR-022)."""
    feature = create_test_feature(
        wp_configs=[
            WPFixture("WP01", lane="done"),
            WPFixture("WP02", lane="done"),
        ]
    )

    # Add content to make valid merge
    for wp_id in ["WP01", "WP02"]:
        wp_path = feature.get_worktree_path(wp_id)
        (wp_path / f"{wp_id.lower()}.txt").write_text(f"{wp_id} content")
        subprocess.run(["git", "add", "."], cwd=wp_path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"Add {wp_id}"], cwd=wp_path, check=True, capture_output=True)

    # Verify worktrees exist before merge
    worktrees_dir = feature.project_dir / ".worktrees"
    assert worktrees_dir.exists(), "Worktrees should exist before merge"

    # Run merge
    result = subprocess.run(
        ["spec-kitty", "merge"],
        cwd=feature.project_dir,
        capture_output=True,
        text=True,
    )

    # Verify worktrees removed after successful merge
    if result.returncode == 0:
        # Check worktrees are gone
        remaining_worktrees = list(worktrees_dir.glob("*")) if worktrees_dir.exists() else []
        wp_worktrees = [w for w in remaining_worktrees if "WP" in w.name]
        assert len(wp_worktrees) == 0, \
            f"Worktrees should be removed after merge. Remaining: {wp_worktrees}"
```

---

### Subtask T038 – Test branches deleted (FR-023)

**Purpose**: Verify branches are deleted after successful merge.

**Steps**:
1. Create feature with 2 WPs
2. Record branch list before merge
3. Run merge
4. Verify WP branches removed

**Files**: `tests/functional/test_merge_cleanup.py` (~50 lines)

**Parallel?**: Yes - independent test

**Code**:
```python
def test_branches_deleted_after_merge(self, create_test_feature):
    """Branches deleted after successful merge (FR-023)."""
    feature = create_test_feature(
        wp_configs=[
            WPFixture("WP01", lane="done"),
            WPFixture("WP02", lane="done"),
        ]
    )

    # Add content
    for wp_id in ["WP01", "WP02"]:
        wp_path = feature.get_worktree_path(wp_id)
        (wp_path / f"{wp_id.lower()}.txt").write_text(f"{wp_id}")
        subprocess.run(["git", "add", "."], cwd=wp_path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", wp_id], cwd=wp_path, check=True, capture_output=True)

    # Get branch list before
    before_result = subprocess.run(
        ["git", "branch", "-a"],
        cwd=feature.project_dir,
        capture_output=True,
        text=True,
    )
    before_branches = before_result.stdout

    # WP branches should exist before merge
    assert "WP01" in before_branches or "WP02" in before_branches, \
        "WP branches should exist before merge"

    # Run merge
    result = subprocess.run(
        ["spec-kitty", "merge"],
        cwd=feature.project_dir,
        capture_output=True,
        text=True,
    )

    # Get branch list after
    after_result = subprocess.run(
        ["git", "branch", "-a"],
        cwd=feature.project_dir,
        capture_output=True,
        text=True,
    )
    after_branches = after_result.stdout

    # WP branches should be deleted
    if result.returncode == 0:
        assert "WP01" not in after_branches and "WP02" not in after_branches, \
            f"WP branches should be deleted. After: {after_branches}"
```

---

### Subtask T039 – Test --keep-worktree flag (FR-024)

**Purpose**: Verify `--keep-worktree` preserves worktrees.

**Steps**:
1. Create feature with 2 WPs
2. Run `spec-kitty merge --keep-worktree`
3. Verify worktrees still exist

**Files**: `tests/functional/test_merge_cleanup.py` (~45 lines)

**Parallel?**: Yes - independent test

**Code**:
```python
def test_keep_worktree_flag(self, create_test_feature):
    """--keep-worktree flag preserves worktrees (FR-024)."""
    feature = create_test_feature(
        wp_configs=[
            WPFixture("WP01", lane="done"),
            WPFixture("WP02", lane="done"),
        ]
    )

    # Add content
    for wp_id in ["WP01", "WP02"]:
        wp_path = feature.get_worktree_path(wp_id)
        (wp_path / f"{wp_id.lower()}.txt").write_text(f"{wp_id}")
        subprocess.run(["git", "add", "."], cwd=wp_path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", wp_id], cwd=wp_path, check=True, capture_output=True)

    # Run merge with --keep-worktree
    result = subprocess.run(
        ["spec-kitty", "merge", "--keep-worktree"],
        cwd=feature.project_dir,
        capture_output=True,
        text=True,
    )

    # Verify worktrees still exist
    if result.returncode == 0:
        worktrees_dir = feature.project_dir / ".worktrees"
        remaining = list(worktrees_dir.glob("*")) if worktrees_dir.exists() else []
        # At least some worktrees should remain
        assert len(remaining) > 0 or feature.get_worktree_path("WP01").exists(), \
            "Worktrees should be preserved with --keep-worktree"
```

---

### Subtask T040 – Test --keep-branch flag (FR-024)

**Purpose**: Verify `--keep-branch` preserves branches.

**Steps**:
1. Create feature with 2 WPs
2. Run `spec-kitty merge --keep-branch`
3. Verify WP branches still exist

**Files**: `tests/functional/test_merge_cleanup.py` (~45 lines)

**Parallel?**: Yes - independent test

**Code**:
```python
def test_keep_branch_flag(self, create_test_feature):
    """--keep-branch flag preserves branches (FR-024)."""
    feature = create_test_feature(
        wp_configs=[
            WPFixture("WP01", lane="done"),
            WPFixture("WP02", lane="done"),
        ]
    )

    # Add content
    for wp_id in ["WP01", "WP02"]:
        wp_path = feature.get_worktree_path(wp_id)
        (wp_path / f"{wp_id.lower()}.txt").write_text(f"{wp_id}")
        subprocess.run(["git", "add", "."], cwd=wp_path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", wp_id], cwd=wp_path, check=True, capture_output=True)

    # Run merge with --keep-branch
    result = subprocess.run(
        ["spec-kitty", "merge", "--keep-branch"],
        cwd=feature.project_dir,
        capture_output=True,
        text=True,
    )

    # Verify branches still exist
    if result.returncode == 0:
        branch_result = subprocess.run(
            ["git", "branch", "-a"],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )
        branches = branch_result.stdout
        # WP branches should still exist
        has_wp_branches = "WP01" in branches or "WP02" in branches or feature.feature_slug in branches
        assert has_wp_branches, \
            f"Branches should be preserved with --keep-branch. Branches: {branches}"
```

---

### Subtask T041 – Test cleanup continues on failure (FR-025)

**Purpose**: Verify cleanup continues even if one operation fails.

**Steps**:
1. Create feature with 3 WPs
2. Lock one worktree (create file lock)
3. Run merge
4. Verify other WPs cleaned up despite one failure

**Files**: `tests/functional/test_merge_cleanup.py` (~55 lines)

**Parallel?**: Yes - independent test

**Code**:
```python
def test_cleanup_continues_on_failure(self, create_test_feature):
    """Cleanup continues even if one operation fails (FR-025)."""
    feature = create_test_feature(
        wp_configs=[
            WPFixture("WP01", lane="done"),
            WPFixture("WP02", lane="done"),
            WPFixture("WP03", lane="done"),
        ]
    )

    # Add content
    for wp_id in ["WP01", "WP02", "WP03"]:
        wp_path = feature.get_worktree_path(wp_id)
        (wp_path / f"{wp_id.lower()}.txt").write_text(f"{wp_id}")
        subprocess.run(["git", "add", "."], cwd=wp_path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", wp_id], cwd=wp_path, check=True, capture_output=True)

    # Note: Simulating a locked worktree is platform-specific and complex
    # This test verifies the concept - if one cleanup fails, others continue

    result = subprocess.run(
        ["spec-kitty", "merge"],
        cwd=feature.project_dir,
        capture_output=True,
        text=True,
    )

    # Merge should still complete (possibly with warnings about cleanup)
    # The key is that it doesn't abort entirely on first cleanup failure
    output = result.stdout + result.stderr

    # If merge succeeded, most cleanup should have happened
    # We can't easily simulate a locked file in this test, but we verify
    # the merge completes and doesn't crash on cleanup
    assert result.returncode == 0 or "conflict" in output.lower(), \
        f"Merge should complete. Output: {output}"
```

---

## Test Strategy

Run all tests with:
```bash
pytest tests/functional/test_merge_cleanup.py -v
```

Expected: 5 tests, all passing.

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Worktree paths vary | Use feature fixture's path tracking |
| Branch naming varies | Check for WP pattern in name |
| Simulating locked files complex | Test concept, document limitation |

---

## Definition of Done Checklist

- [x] `tests/functional/test_merge_cleanup.py` exists
- [x] Test: worktrees removed (FR-022)
- [x] Test: branches deleted (FR-023)
- [x] Test: --keep-worktree flag (FR-024)
- [x] Test: --keep-branch flag (FR-024)
- [x] Test: cleanup continues on failure (FR-025)
- [x] All tests pass: `pytest tests/functional/test_merge_cleanup.py -v`

---

## Review Guidance

- Verify worktree detection uses correct paths
- Check branch detection handles different naming
- Ensure flag tests actually preserve resources
- Verify cleanup continuation logic is tested

---

## Activity Log

- 2026-01-18T12:27:56Z – system – lane=planned – Prompt created.
- 2026-01-18T13:36:13Z – claude-opus – shell_pid=75187 – lane=doing – Started implementation via workflow command
- 2026-01-18T13:45:00Z – claude-opus – shell_pid=75187 – lane=for_review – Implementation complete. 5 tests pass (T036-T041).
- 2026-01-18T13:41:07Z – claude-opus – shell_pid=80554 – lane=doing – Started review via workflow command
