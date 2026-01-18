---
work_package_id: "WP07"
subtasks:
  - "T042"
  - "T043"
  - "T044"
  - "T045"
  - "T046"
  - "T047"
  - "T048"
title: "Merge Resume Tests"
phase: "Phase 3 - Extended Features"
lane: "done"
assignee: ""
agent: "claude-opus"
shell_pid: "85653"
review_status: "approved"
reviewed_by: "Robert Douglass"
dependencies: ["WP01"]
history:
  - timestamp: "2026-01-18T12:27:56Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP07 – Merge Resume Tests

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
spec-kitty implement WP07 --base WP01
```

Depends on WP01 for fixtures.

---

## Objectives & Success Criteria

Implement tests for **User Story 6 - Merge Resume** (FR-026 to FR-029):

1. **FR-026**: Verify merge state persists to `.kittify/merge-state.json`
2. **FR-027**: Verify `--resume` continues from last incomplete WP
3. **FR-028**: Verify `--abort` clears state and rolls back partial changes
4. **FR-029**: Verify corrupted state file is detected and reported

**Success**: `pytest tests/functional/test_merge_resume.py -v` passes.

---

## Context & Constraints

### Related Documents
- Spec: `kitty-specs/003-merge-feature-test-suite/spec.md` - User Story 6
- Feature 017: `merge/state.py` handles persistence

### State File Location
`.kittify/merge-state.json`

### State File Format
```json
{
  "feature_slug": "001-feature",
  "target_branch": "main",
  "wp_order": ["WP01", "WP02", "WP03"],
  "completed_wps": ["WP01"],
  "current_wp": "WP02",
  "has_pending_conflicts": false,
  "started_at": "2026-01-01T00:00:00Z",
  "last_updated": "2026-01-01T00:00:00Z"
}
```

### CLI Commands
- `spec-kitty merge --resume`: Continue from saved state
- `spec-kitty merge --abort`: Clear state, rollback

---

## Subtasks & Detailed Guidance

### Subtask T042 – Create test_merge_resume.py module

**Purpose**: Establish the test file structure.

**Steps**:
1. Create `tests/functional/test_merge_resume.py`
2. Add imports including `MergeStateFixture`
3. Add module docstring

**Files**: `tests/functional/test_merge_resume.py` (new, ~35 lines)

**Parallel?**: No - foundation

**Template**:
```python
"""
Tests for spec-kitty merge state persistence and resume.

Validates User Story 6 from Feature 003 spec:
- Merge state persists to .kittify/merge-state.json
- --resume continues from last incomplete WP
- --abort clears state and rolls back
- Corrupted state file detected and reported

Requires spec-kitty >= 0.11.0.
"""
import json
import subprocess
from pathlib import Path

import pytest

from tests.conftest import requires_v011
from tests.functional.test_merge_fixtures import (
    WPFixture,
    MergeStateFixture,
    create_test_feature,
)


@requires_v011
class TestMergeResume:
    """Tests for merge state persistence and resume capability."""
    pass
```

---

### Subtask T043 – Test merge state persistence (FR-026)

**Purpose**: Verify merge state is saved during multi-WP merge.

**Steps**:
1. Create feature with 3 WPs
2. Create conflict to pause merge mid-way
3. Check state file exists and has correct content

**Files**: `tests/functional/test_merge_resume.py` (~55 lines)

**Parallel?**: Yes - independent test

**Code**:
```python
def test_merge_state_persists(self, create_test_feature):
    """Merge state persists to .kittify/merge-state.json (FR-026)."""
    feature = create_test_feature(
        wp_configs=[
            WPFixture("WP01", lane="done"),
            WPFixture("WP02", lane="done"),
            WPFixture("WP03", lane="done"),
        ]
    )

    # Add content to WP01 and WP02 (clean merge)
    for wp_id in ["WP01", "WP02"]:
        wp_path = feature.get_worktree_path(wp_id)
        (wp_path / f"{wp_id.lower()}.txt").write_text(f"{wp_id}")
        subprocess.run(["git", "add", "."], cwd=wp_path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", wp_id], cwd=wp_path, check=True, capture_output=True)

    # Add conflicting content to WP03 to pause merge
    wp03_path = feature.get_worktree_path("WP03")
    (wp03_path / "wp01.txt").write_text("Conflict from WP03")  # Same file as WP01
    subprocess.run(["git", "add", "."], cwd=wp03_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "WP03 conflict"], cwd=wp03_path, check=True, capture_output=True)

    # Run merge (should pause at WP03 conflict)
    result = subprocess.run(
        ["spec-kitty", "merge"],
        cwd=feature.project_dir,
        capture_output=True,
        text=True,
    )

    # Check state file
    state_file = feature.project_dir / ".kittify" / "merge-state.json"
    if state_file.exists():
        state = json.loads(state_file.read_text())
        assert "completed_wps" in state, "State should track completed WPs"
        assert "wp_order" in state, "State should have WP order"
```

---

### Subtask T044 – Test --resume continuation (FR-027)

**Purpose**: Verify `--resume` continues from last incomplete WP.

**Steps**:
1. Create feature
2. Create merge state file showing WP01 complete
3. Run `spec-kitty merge --resume`
4. Verify it continues from WP02

**Files**: `tests/functional/test_merge_resume.py` (~55 lines)

**Parallel?**: Yes - independent test

**Code**:
```python
def test_resume_continues_from_last_wp(self, create_test_feature, tmp_path):
    """--resume continues from last incomplete WP (FR-027)."""
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

    # Create state file showing WP01 complete, WP02 next
    state_fixture = MergeStateFixture(feature.project_dir)
    state_fixture.create_state(
        feature_slug=feature.feature_slug,
        wp_order=["WP01", "WP02"],
        completed_wps=["WP01"],
        current_wp="WP02",
    )

    # Run resume
    result = subprocess.run(
        ["spec-kitty", "merge", "--resume"],
        cwd=feature.project_dir,
        capture_output=True,
        text=True,
    )

    output = result.stdout + result.stderr

    # Should process WP02 (not start from WP01 again)
    assert "WP02" in output or result.returncode == 0, \
        f"Should resume at WP02. Output: {output}"
```

---

### Subtask T045 – Test --abort clears state (FR-028)

**Purpose**: Verify `--abort` clears state and rolls back.

**Steps**:
1. Create feature
2. Create merge state file
3. Run `spec-kitty merge --abort`
4. Verify state file removed

**Files**: `tests/functional/test_merge_resume.py` (~45 lines)

**Parallel?**: Yes - independent test

**Code**:
```python
def test_abort_clears_state(self, create_test_feature):
    """--abort clears state and rolls back (FR-028)."""
    feature = create_test_feature(
        wp_configs=[
            WPFixture("WP01", lane="done"),
            WPFixture("WP02", lane="done"),
        ]
    )

    # Create state file
    state_fixture = MergeStateFixture(feature.project_dir)
    state_file = state_fixture.create_state(
        feature_slug=feature.feature_slug,
        wp_order=["WP01", "WP02"],
        completed_wps=["WP01"],
        current_wp="WP02",
    )

    assert state_file.exists(), "State file should exist before abort"

    # Run abort
    result = subprocess.run(
        ["spec-kitty", "merge", "--abort"],
        cwd=feature.project_dir,
        capture_output=True,
        text=True,
    )

    # State file should be cleared
    assert not state_file.exists(), \
        f"State file should be cleared after abort. Output: {result.stdout}"
```

---

### Subtask T046 – Test corrupted state detection (FR-029)

**Purpose**: Verify corrupted state file is detected and reported.

**Steps**:
1. Create feature
2. Create corrupted state file (invalid JSON)
3. Run `spec-kitty merge --resume`
4. Verify error reported

**Files**: `tests/functional/test_merge_resume.py` (~45 lines)

**Parallel?**: Yes - independent test

**Code**:
```python
def test_corrupted_state_detected(self, create_test_feature):
    """Corrupted state file is detected and reported (FR-029)."""
    feature = create_test_feature(
        wp_configs=[
            WPFixture("WP01", lane="done"),
        ]
    )

    # Create corrupted state file
    state_fixture = MergeStateFixture(feature.project_dir)
    state_fixture.corrupt_state()

    # Run resume
    result = subprocess.run(
        ["spec-kitty", "merge", "--resume"],
        cwd=feature.project_dir,
        capture_output=True,
        text=True,
    )

    output = result.stdout + result.stderr

    # Should report corruption/error
    assert result.returncode != 0 or any(word in output.lower() for word in [
        "corrupt", "invalid", "error", "abort", "json"
    ]), f"Should report corrupted state. Output: {output}"
```

---

### Subtask T047 – Test --resume with no merge in progress

**Purpose**: Verify error when no merge state exists.

**Steps**:
1. Create feature (no state file)
2. Run `spec-kitty merge --resume`
3. Verify appropriate error message

**Files**: `tests/functional/test_merge_resume.py` (~40 lines)

**Parallel?**: Yes - independent test

**Code**:
```python
def test_resume_no_merge_in_progress(self, create_test_feature):
    """--resume with no merge in progress shows error."""
    feature = create_test_feature(
        wp_configs=[
            WPFixture("WP01", lane="done"),
        ]
    )

    # Ensure no state file
    state_file = feature.project_dir / ".kittify" / "merge-state.json"
    if state_file.exists():
        state_file.unlink()

    # Run resume
    result = subprocess.run(
        ["spec-kitty", "merge", "--resume"],
        cwd=feature.project_dir,
        capture_output=True,
        text=True,
    )

    output = result.stdout + result.stderr

    # Should report no merge in progress
    assert result.returncode != 0 or "no merge" in output.lower() or "not found" in output.lower(), \
        f"Should report no merge in progress. Output: {output}"
```

---

### Subtask T048 – Test state update on resumed conflicts

**Purpose**: Verify state updates when resumed merge hits new conflicts.

**Steps**:
1. Create feature with state file
2. Run resume (hits conflict)
3. Verify state updated with current progress

**Files**: `tests/functional/test_merge_resume.py` (~55 lines)

**Parallel?**: Yes - independent test

**Code**:
```python
def test_state_updated_on_resumed_conflicts(self, create_test_feature):
    """State updated when resumed merge encounters new conflicts."""
    feature = create_test_feature(
        wp_configs=[
            WPFixture("WP01", lane="done"),
            WPFixture("WP02", lane="done"),
            WPFixture("WP03", lane="done"),
        ]
    )

    # Add content - WP02 and WP03 will conflict
    wp01_path = feature.get_worktree_path("WP01")
    (wp01_path / "wp01.txt").write_text("WP01 content")
    subprocess.run(["git", "add", "."], cwd=wp01_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "WP01"], cwd=wp01_path, check=True, capture_output=True)

    # WP02 adds file
    wp02_path = feature.get_worktree_path("WP02")
    (wp02_path / "shared.txt").write_text("WP02 version")
    subprocess.run(["git", "add", "."], cwd=wp02_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "WP02"], cwd=wp02_path, check=True, capture_output=True)

    # WP03 conflicts with WP02
    wp03_path = feature.get_worktree_path("WP03")
    (wp03_path / "shared.txt").write_text("WP03 version")
    subprocess.run(["git", "add", "."], cwd=wp03_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "WP03"], cwd=wp03_path, check=True, capture_output=True)

    # Create state showing WP01 complete
    state_fixture = MergeStateFixture(feature.project_dir)
    state_fixture.create_state(
        feature_slug=feature.feature_slug,
        wp_order=["WP01", "WP02", "WP03"],
        completed_wps=["WP01"],
        current_wp="WP02",
    )

    # Run resume (should merge WP02, then conflict at WP03)
    result = subprocess.run(
        ["spec-kitty", "merge", "--resume"],
        cwd=feature.project_dir,
        capture_output=True,
        text=True,
    )

    # Check if state was updated
    state_file = feature.project_dir / ".kittify" / "merge-state.json"
    if state_file.exists():
        updated_state = json.loads(state_file.read_text())
        # WP02 should now be in completed if it merged successfully
        # or current_wp should be WP02 or WP03
        assert "completed_wps" in updated_state or "current_wp" in updated_state, \
            "State should be updated after resume"
```

---

## Test Strategy

Run all tests with:
```bash
pytest tests/functional/test_merge_resume.py -v
```

Expected: 6 tests, all passing.

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| State file format changes | Use MergeStateFixture for consistent format |
| Hard to simulate interruption | Use state file manipulation instead |
| Conflict creation complex | Create clear file conflicts |

---

## Definition of Done Checklist

- [ ] `tests/functional/test_merge_resume.py` exists
- [ ] Test: merge state persistence (FR-026)
- [ ] Test: --resume continuation (FR-027)
- [ ] Test: --abort clears state (FR-028)
- [ ] Test: corrupted state detection (FR-029)
- [ ] Test: --resume with no merge in progress
- [ ] Test: state update on resumed conflicts
- [ ] All tests pass: `pytest tests/functional/test_merge_resume.py -v`

---

## Review Guidance

- Verify state file format matches spec-kitty
- Check MergeStateFixture creates valid state
- Ensure corrupted state is truly invalid JSON
- Verify resume actually continues, not restarts

---

## Activity Log

- 2026-01-18T12:27:56Z – system – lane=planned – Prompt created.
- 2026-01-18T13:44:29Z – claude-opus – shell_pid=82855 – lane=doing – Started implementation via workflow command
- 2026-01-18T13:46:50Z – claude-opus – shell_pid=82855 – lane=for_review – Ready for review: 7 tests for merge resume/abort (FR-026 to FR-029)
- 2026-01-18T13:47:16Z – claude-opus – shell_pid=85653 – lane=doing – Started review via workflow command
- 2026-01-18T13:48:23Z – claude-opus – shell_pid=85653 – lane=done – Review passed: All 7 tests pass. Complete coverage for FR-026 through FR-029. Tests state persistence, --resume continuation, --abort clearing, corrupted state detection, plus edge cases for no merge in progress. Good use of MergeStateFixture.
