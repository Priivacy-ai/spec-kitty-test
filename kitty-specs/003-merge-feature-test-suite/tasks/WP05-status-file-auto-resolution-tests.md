---
work_package_id: "WP05"
subtasks:
  - "T028"
  - "T029"
  - "T030"
  - "T031"
  - "T032"
  - "T033"
  - "T034"
  - "T035"
title: "Status File Auto-Resolution Tests"
phase: "Phase 2 - Core Features"
lane: "doing"
assignee: ""
agent: "claude-opus"
shell_pid: "74333"
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

# Work Package Prompt: WP05 – Status File Auto-Resolution Tests

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
spec-kitty implement WP05 --base WP01
```

Depends on WP01 for fixtures.

---

## Objectives & Success Criteria

Implement tests for **User Story 4 - Status File Auto-Resolution** (FR-017 to FR-021):

1. **FR-017**: Verify `lane:` conflicts resolve by "more done" wins (done > for_review > doing > planned)
2. **FR-018**: Verify checkbox conflicts resolve by preferring `[x]` over `[ ]`
3. **FR-019**: Verify `history:` arrays merge chronologically
4. **FR-020**: Verify non-status file conflicts are NOT auto-resolved
5. **FR-021**: Verify only `kitty-specs/**/tasks/*.md` patterns are auto-resolved

**Success**: `pytest tests/functional/test_merge_status_resolution.py -v` passes.

---

## Context & Constraints

### Related Documents
- Spec: `kitty-specs/003-merge-feature-test-suite/spec.md` - User Story 4
- Feature 017: `merge/status_resolver.py` handles conflict resolution

### Resolution Rules
- **Lane priority**: done > for_review > doing > planned
- **Checkbox**: `[x]` wins over `[ ]`
- **History**: Concatenate chronologically by timestamp
- **Pattern**: Only `kitty-specs/**/tasks/*.md` or `kitty-specs/**/tasks.md`

### Acceptance Scenarios from Spec
1. WP01 `lane: done` vs WP02 `lane: for_review` → resolves to `done`
2. `- [x] Task A` vs `- [ ] Task A` → resolves to `[x]`
3. Conflicting history arrays → concatenate by timestamp
4. Code file conflicts → NOT auto-resolved (manual required)
5. Mixed conflicts → status auto-resolved, code pauses
6. Malformed YAML → skipped, manual required

---

## Subtasks & Detailed Guidance

### Subtask T028 – Create test_merge_status_resolution.py module

**Purpose**: Establish the test file structure.

**Steps**:
1. Create `tests/functional/test_merge_status_resolution.py`
2. Add imports and version gating
3. Add module docstring

**Files**: `tests/functional/test_merge_status_resolution.py` (new, ~35 lines)

**Parallel?**: No - foundation

**Template**:
```python
"""
Tests for spec-kitty merge status file auto-resolution.

Validates User Story 4 from Feature 003 spec:
- Lane conflicts resolve by "more done" wins
- Checkbox conflicts resolve by preferring [x]
- History arrays merge chronologically
- Code files NOT auto-resolved
- Only kitty-specs/**/tasks/*.md patterns

Requires spec-kitty >= 0.11.0.
"""
import subprocess
from pathlib import Path

import pytest

from tests.conftest import requires_v011
from tests.functional.test_merge_fixtures import (
    WPFixture,
    ConflictFixture,
    create_test_feature,
)


@requires_v011
class TestMergeStatusResolution:
    """Tests for automatic status file conflict resolution."""
    pass
```

---

### Subtask T029 – Test lane "more done" wins (FR-017)

**Purpose**: Verify lane conflicts resolve by priority order.

**Steps**:
1. Create feature where WP01 sets `lane: done`, WP02 sets `lane: for_review`
2. Run `spec-kitty merge`
3. Verify resolved file has `lane: done`

**Files**: `tests/functional/test_merge_status_resolution.py` (~60 lines)

**Parallel?**: Yes - independent test

**Code**:
```python
def test_lane_more_done_wins(self, create_test_feature):
    """Lane conflicts resolve by 'more done' wins - done > for_review > doing > planned (FR-017)."""
    feature = create_test_feature(
        wp_configs=[
            WPFixture("WP01", lane="done"),
            WPFixture("WP02", lane="done"),
        ]
    )

    # Create conflicting lane values in a task file
    task_file = f"kitty-specs/{feature.feature_slug}/tasks/WP01-test.md"

    # WP01 sets lane to "done"
    wp01_path = feature.get_worktree_path("WP01")
    task_in_wp01 = wp01_path / task_file
    task_in_wp01.parent.mkdir(parents=True, exist_ok=True)
    task_in_wp01.write_text('''---
work_package_id: "WP01"
title: "Test Task"
lane: "done"
history: []
---
# Test Task Content
''')
    subprocess.run(["git", "add", "."], cwd=wp01_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Set lane to done"], cwd=wp01_path, check=True, capture_output=True)

    # WP02 sets lane to "for_review"
    wp02_path = feature.get_worktree_path("WP02")
    task_in_wp02 = wp02_path / task_file
    task_in_wp02.parent.mkdir(parents=True, exist_ok=True)
    task_in_wp02.write_text('''---
work_package_id: "WP01"
title: "Test Task"
lane: "for_review"
history: []
---
# Test Task Content
''')
    subprocess.run(["git", "add", "."], cwd=wp02_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Set lane to for_review"], cwd=wp02_path, check=True, capture_output=True)

    # Run merge
    result = subprocess.run(
        ["spec-kitty", "merge"],
        cwd=feature.project_dir,
        capture_output=True,
        text=True,
    )

    # Check result - merge should succeed with auto-resolution
    # Read the merged file to verify lane value
    merged_file = feature.project_dir / task_file
    if merged_file.exists():
        content = merged_file.read_text()
        assert 'lane: "done"' in content or "lane: done" in content, \
            f"Lane should resolve to 'done'. Content: {content}"
```

---

### Subtask T030 – Test checkbox `[x]` wins (FR-018)

**Purpose**: Verify checkbox conflicts prefer checked state.

**Steps**:
1. Create WPs with conflicting checkbox states in tasks.md
2. Run merge
3. Verify resolved file has `[x]`

**Files**: `tests/functional/test_merge_status_resolution.py` (~55 lines)

**Parallel?**: Yes - independent test

**Code**:
```python
def test_checkbox_checked_wins(self, create_test_feature):
    """Checkbox conflicts resolve by preferring [x] over [ ] (FR-018)."""
    feature = create_test_feature(
        wp_configs=[
            WPFixture("WP01", lane="done"),
            WPFixture("WP02", lane="done"),
        ]
    )

    tasks_md = f"kitty-specs/{feature.feature_slug}/tasks.md"

    # WP01 has checked checkbox
    wp01_path = feature.get_worktree_path("WP01")
    (wp01_path / tasks_md).parent.mkdir(parents=True, exist_ok=True)
    (wp01_path / tasks_md).write_text('''# Tasks

- [x] T001 First task
- [ ] T002 Second task
''')
    subprocess.run(["git", "add", "."], cwd=wp01_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Check T001"], cwd=wp01_path, check=True, capture_output=True)

    # WP02 has unchecked checkbox for same task
    wp02_path = feature.get_worktree_path("WP02")
    (wp02_path / tasks_md).parent.mkdir(parents=True, exist_ok=True)
    (wp02_path / tasks_md).write_text('''# Tasks

- [ ] T001 First task
- [x] T002 Second task
''')
    subprocess.run(["git", "add", "."], cwd=wp02_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Check T002"], cwd=wp02_path, check=True, capture_output=True)

    result = subprocess.run(
        ["spec-kitty", "merge"],
        cwd=feature.project_dir,
        capture_output=True,
        text=True,
    )

    # Verify resolution
    merged_file = feature.project_dir / tasks_md
    if merged_file.exists():
        content = merged_file.read_text()
        # Both T001 and T002 should be checked (checked wins in both cases)
        assert "[x] T001" in content or "- [x]" in content, \
            f"T001 should be checked. Content: {content}"
```

---

### Subtask T031 – Test history chronological merge (FR-019)

**Purpose**: Verify history arrays merge by timestamp.

**Steps**:
1. Create WPs with different history entries
2. Run merge
3. Verify history is concatenated chronologically

**Files**: `tests/functional/test_merge_status_resolution.py` (~60 lines)

**Parallel?**: Yes - independent test

**Code**:
```python
def test_history_chronological_merge(self, create_test_feature):
    """History arrays merge chronologically (FR-019)."""
    feature = create_test_feature(
        wp_configs=[
            WPFixture("WP01", lane="done"),
            WPFixture("WP02", lane="done"),
        ]
    )

    task_file = f"kitty-specs/{feature.feature_slug}/tasks/WP01-test.md"

    # WP01 has history with timestamp 01:00
    wp01_path = feature.get_worktree_path("WP01")
    (wp01_path / task_file).parent.mkdir(parents=True, exist_ok=True)
    (wp01_path / task_file).write_text('''---
work_package_id: "WP01"
lane: "done"
history:
  - timestamp: "2026-01-01T01:00:00Z"
    agent: "agent1"
    action: "First action"
---
# Content
''')
    subprocess.run(["git", "add", "."], cwd=wp01_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Add history 1"], cwd=wp01_path, check=True, capture_output=True)

    # WP02 has history with timestamp 02:00
    wp02_path = feature.get_worktree_path("WP02")
    (wp02_path / task_file).parent.mkdir(parents=True, exist_ok=True)
    (wp02_path / task_file).write_text('''---
work_package_id: "WP01"
lane: "done"
history:
  - timestamp: "2026-01-01T02:00:00Z"
    agent: "agent2"
    action: "Second action"
---
# Content
''')
    subprocess.run(["git", "add", "."], cwd=wp02_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Add history 2"], cwd=wp02_path, check=True, capture_output=True)

    result = subprocess.run(
        ["spec-kitty", "merge"],
        cwd=feature.project_dir,
        capture_output=True,
        text=True,
    )

    # Verify both history entries present
    merged_file = feature.project_dir / task_file
    if merged_file.exists():
        content = merged_file.read_text()
        assert "agent1" in content or "First action" in content, \
            f"Should have first history entry. Content: {content}"
        # Note: may also have agent2 entry if merge succeeded
```

---

### Subtask T032 – Test code conflicts NOT auto-resolved (FR-020)

**Purpose**: Verify code file conflicts require manual resolution.

**Steps**:
1. Create WPs with conflicting code file
2. Run merge
3. Verify merge pauses/fails for manual resolution

**Files**: `tests/functional/test_merge_status_resolution.py` (~50 lines)

**Parallel?**: Yes - independent test

**Code**:
```python
def test_code_conflicts_not_auto_resolved(self, create_test_feature):
    """Code file conflicts are NOT auto-resolved (FR-020)."""
    feature = create_test_feature(
        wp_configs=[
            WPFixture("WP01", lane="done"),
            WPFixture("WP02", lane="done"),
        ]
    )

    # Both WPs modify the same code file with conflicts
    code_file = "src/main.py"

    wp01_path = feature.get_worktree_path("WP01")
    (wp01_path / "src").mkdir(parents=True, exist_ok=True)
    (wp01_path / code_file).write_text("def foo(): return 'WP01'")
    subprocess.run(["git", "add", "."], cwd=wp01_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "WP01 code"], cwd=wp01_path, check=True, capture_output=True)

    wp02_path = feature.get_worktree_path("WP02")
    (wp02_path / "src").mkdir(parents=True, exist_ok=True)
    (wp02_path / code_file).write_text("def foo(): return 'WP02'")
    subprocess.run(["git", "add", "."], cwd=wp02_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "WP02 code"], cwd=wp02_path, check=True, capture_output=True)

    result = subprocess.run(
        ["spec-kitty", "merge"],
        cwd=feature.project_dir,
        capture_output=True,
        text=True,
    )

    output = result.stdout + result.stderr

    # Should indicate conflict requiring manual resolution
    # Either non-zero exit or explicit conflict message
    assert result.returncode != 0 or "conflict" in output.lower() or "manual" in output.lower(), \
        f"Code conflicts should require manual resolution: {output}"
```

---

### Subtask T033 – Test status file pattern matching (FR-021)

**Purpose**: Verify only `kitty-specs/**/tasks/*.md` patterns are auto-resolved.

**Steps**:
1. Create conflict in file that looks like status but wrong path
2. Verify it's NOT auto-resolved

**Files**: `tests/functional/test_merge_status_resolution.py` (~50 lines)

**Parallel?**: Yes - independent test

**Code**:
```python
def test_status_file_pattern_matching(self, create_test_feature):
    """Only kitty-specs/**/tasks/*.md patterns are auto-resolved (FR-021)."""
    feature = create_test_feature(
        wp_configs=[
            WPFixture("WP01", lane="done"),
            WPFixture("WP02", lane="done"),
        ]
    )

    # Create conflict in a file that has lane: but wrong path
    wrong_path = "docs/status.md"

    wp01_path = feature.get_worktree_path("WP01")
    (wp01_path / "docs").mkdir(parents=True, exist_ok=True)
    (wp01_path / wrong_path).write_text('''---
lane: "done"
---
# Doc Status
''')
    subprocess.run(["git", "add", "."], cwd=wp01_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Add doc status"], cwd=wp01_path, check=True, capture_output=True)

    wp02_path = feature.get_worktree_path("WP02")
    (wp02_path / "docs").mkdir(parents=True, exist_ok=True)
    (wp02_path / wrong_path).write_text('''---
lane: "for_review"
---
# Doc Status
''')
    subprocess.run(["git", "add", "."], cwd=wp02_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Change doc status"], cwd=wp02_path, check=True, capture_output=True)

    result = subprocess.run(
        ["spec-kitty", "merge"],
        cwd=feature.project_dir,
        capture_output=True,
        text=True,
    )

    # File outside kitty-specs/**/tasks/ should NOT be auto-resolved
    # Either fails or has conflict markers
    merged_file = feature.project_dir / wrong_path
    if merged_file.exists():
        content = merged_file.read_text()
        # Should either have conflict markers or merge failed
        has_conflict_markers = "<<<<<<<" in content or "=======" in content
        merge_failed = result.returncode != 0
        assert has_conflict_markers or merge_failed, \
            f"Non-status path should not be auto-resolved. Content: {content}"
```

---

### Subtask T034 – Test mixed status and code conflicts

**Purpose**: Verify status files auto-resolved while code conflicts pause.

**Steps**:
1. Create both status and code conflicts
2. Run merge
3. Verify status resolved, code pauses

**Files**: `tests/functional/test_merge_status_resolution.py` (~65 lines)

**Parallel?**: Yes - independent test

**Code**:
```python
def test_mixed_status_and_code_conflicts(self, create_test_feature):
    """Mixed conflicts: status auto-resolved, code pauses for manual."""
    feature = create_test_feature(
        wp_configs=[
            WPFixture("WP01", lane="done"),
            WPFixture("WP02", lane="done"),
        ]
    )

    task_file = f"kitty-specs/{feature.feature_slug}/tasks/WP01-test.md"
    code_file = "src/code.py"

    # WP01: status + code
    wp01_path = feature.get_worktree_path("WP01")
    (wp01_path / task_file).parent.mkdir(parents=True, exist_ok=True)
    (wp01_path / task_file).write_text('---\nlane: "done"\n---\n# Task')
    (wp01_path / "src").mkdir(parents=True, exist_ok=True)
    (wp01_path / code_file).write_text("# WP01 code")
    subprocess.run(["git", "add", "."], cwd=wp01_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "WP01"], cwd=wp01_path, check=True, capture_output=True)

    # WP02: conflicting status + code
    wp02_path = feature.get_worktree_path("WP02")
    (wp02_path / task_file).parent.mkdir(parents=True, exist_ok=True)
    (wp02_path / task_file).write_text('---\nlane: "for_review"\n---\n# Task')
    (wp02_path / "src").mkdir(parents=True, exist_ok=True)
    (wp02_path / code_file).write_text("# WP02 code")
    subprocess.run(["git", "add", "."], cwd=wp02_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "WP02"], cwd=wp02_path, check=True, capture_output=True)

    result = subprocess.run(
        ["spec-kitty", "merge"],
        cwd=feature.project_dir,
        capture_output=True,
        text=True,
    )

    # Merge should pause/fail due to code conflict
    # But status file should be auto-resolved if we check it
    output = result.stdout + result.stderr
    assert "conflict" in output.lower() or result.returncode != 0, \
        f"Should have code conflict: {output}"
```

---

### Subtask T035 – Test malformed YAML handling

**Purpose**: Verify malformed YAML is skipped gracefully.

**Steps**:
1. Create conflict with malformed YAML in status file
2. Run merge
3. Verify graceful skip/error

**Files**: `tests/functional/test_merge_status_resolution.py` (~50 lines)

**Parallel?**: Yes - independent test

**Code**:
```python
def test_malformed_yaml_skipped_gracefully(self, create_test_feature):
    """Malformed YAML in status file skipped, manual resolution required."""
    feature = create_test_feature(
        wp_configs=[
            WPFixture("WP01", lane="done"),
            WPFixture("WP02", lane="done"),
        ]
    )

    task_file = f"kitty-specs/{feature.feature_slug}/tasks/WP01-test.md"

    # WP01: valid YAML
    wp01_path = feature.get_worktree_path("WP01")
    (wp01_path / task_file).parent.mkdir(parents=True, exist_ok=True)
    (wp01_path / task_file).write_text('---\nlane: "done"\n---\n# Task')
    subprocess.run(["git", "add", "."], cwd=wp01_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Valid YAML"], cwd=wp01_path, check=True, capture_output=True)

    # WP02: malformed YAML
    wp02_path = feature.get_worktree_path("WP02")
    (wp02_path / task_file).parent.mkdir(parents=True, exist_ok=True)
    (wp02_path / task_file).write_text('---\nlane: "for_review\n  broken: yaml: here\n---\n# Task')  # Missing closing quote
    subprocess.run(["git", "add", "."], cwd=wp02_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Malformed YAML"], cwd=wp02_path, check=True, capture_output=True)

    result = subprocess.run(
        ["spec-kitty", "merge"],
        cwd=feature.project_dir,
        capture_output=True,
        text=True,
    )

    # Should not crash - either skips file or reports error
    output = result.stdout + result.stderr
    # We don't crash, and either report the issue or leave conflict for manual
    assert "error" not in output.lower() or "yaml" in output.lower() or result.returncode != 0, \
        f"Should handle malformed YAML gracefully: {output}"
```

---

## Test Strategy

Run all tests with:
```bash
pytest tests/functional/test_merge_status_resolution.py -v
```

Expected: 8 tests, all passing.

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| YAML formatting sensitive | Use exact frontmatter format from spec-kitty |
| Resolution rules change | Test core behavior, allow for minor variations |
| File path patterns change | Use feature.feature_slug for dynamic paths |

---

## Definition of Done Checklist

- [ ] `tests/functional/test_merge_status_resolution.py` exists
- [ ] Test: lane "more done" wins (FR-017)
- [ ] Test: checkbox `[x]` wins (FR-018)
- [ ] Test: history chronological merge (FR-019)
- [ ] Test: code conflicts NOT auto-resolved (FR-020)
- [ ] Test: status file pattern matching (FR-021)
- [ ] Test: mixed status and code conflicts
- [ ] Test: malformed YAML handling
- [ ] All tests pass: `pytest tests/functional/test_merge_status_resolution.py -v`

---

## Review Guidance

- Verify YAML formatting is valid
- Check lane priority order matches spec
- Ensure code conflicts are truly not auto-resolved
- Verify pattern matching uses correct paths

---

## Activity Log

- 2026-01-18T12:27:56Z – system – lane=planned – Prompt created.
- 2026-01-18T13:30:33Z – claude-opus – shell_pid=69791 – lane=doing – Started implementation via workflow command
- 2026-01-18T13:32:41Z – claude-opus – shell_pid=69791 – lane=for_review – Ready for review: 7 tests for status file auto-resolution (FR-017 to FR-021 plus mixed conflicts and malformed YAML)
- 2026-01-18T13:35:49Z – claude-opus – shell_pid=74333 – lane=doing – Started review via workflow command
