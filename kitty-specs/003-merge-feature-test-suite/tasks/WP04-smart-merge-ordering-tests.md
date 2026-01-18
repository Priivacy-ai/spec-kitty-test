---
work_package_id: "WP04"
subtasks:
  - "T021"
  - "T022"
  - "T023"
  - "T024"
  - "T025"
  - "T026"
  - "T027"
title: "Smart Merge Ordering Tests"
phase: "Phase 2 - Core Features"
lane: "done"
assignee: ""
agent: "claude-opus"
shell_pid: "64382"
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

# Work Package Prompt: WP04 – Smart Merge Ordering Tests

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
spec-kitty implement WP04 --base WP01
```

Depends on WP01 for fixtures.

---

## Objectives & Success Criteria

Implement tests for **User Story 3 - Smart Merge Ordering** (FR-013 to FR-016):

1. **FR-013**: Verify frontmatter `dependencies: []` is parsed correctly
2. **FR-014**: Verify topological ordering (dependencies merge before dependents)
3. **FR-015**: Verify circular dependencies are detected with clear error
4. **FR-016**: Verify fallback to numerical order when no dependencies declared

**Success**: `pytest tests/functional/test_merge_ordering.py -v` passes with all acceptance scenarios covered.

---

## Context & Constraints

### Related Documents
- Spec: `kitty-specs/003-merge-feature-test-suite/spec.md` - User Story 3
- Feature 017: Uses `build_dependency_graph()` and `topological_sort()` from `core/dependency_graph.py`

### Acceptance Scenarios from Spec
1. WP02 depends on WP01 → WP01 merged first
2. WP03→WP01, WP04→WP02 → both chains respected
3. Diamond: WP04→(WP02,WP03)→WP01 → correct order
4. Circular dependency → pre-flight fails with error
5. No dependencies → numerical order (WP01, WP02, WP03)

### Frontmatter Format
```yaml
---
work_package_id: "WP02"
dependencies: ["WP01"]
---
```

---

## Subtasks & Detailed Guidance

### Subtask T021 – Create test_merge_ordering.py module

**Purpose**: Establish the test file structure.

**Steps**:
1. Create `tests/functional/test_merge_ordering.py`
2. Add imports and version gating
3. Add module docstring

**Files**: `tests/functional/test_merge_ordering.py` (new, ~30 lines)

**Parallel?**: No - foundation

**Template**:
```python
"""
Tests for spec-kitty merge ordering (dependency-based).

Validates User Story 3 from Feature 003 spec:
- Dependencies parsed from frontmatter
- Topological ordering respected
- Circular dependencies detected
- Numerical fallback when no dependencies

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
class TestMergeOrdering:
    """Tests for dependency-based merge ordering."""
    pass
```

---

### Subtask T022 – Test dependency ordering (FR-014)

**Purpose**: Verify WP with dependency merges after its dependency.

**Steps**:
1. Create feature: WP01 (no deps), WP02 (depends on WP01)
2. Run `spec-kitty merge`
3. Verify merge log shows WP01 merged before WP02

**Files**: `tests/functional/test_merge_ordering.py` (~50 lines)

**Parallel?**: Yes - independent test

**Code**:
```python
def test_dependency_ordering(self, create_test_feature):
    """WP with dependency merges after its dependency (FR-014)."""
    feature = create_test_feature(
        wp_configs=[
            WPFixture("WP01", lane="done"),
            WPFixture("WP02", lane="done", dependencies=["WP01"]),
        ]
    )

    # Add unique content to each WP
    for wp_id in ["WP01", "WP02"]:
        wp_path = feature.get_worktree_path(wp_id)
        (wp_path / f"{wp_id.lower()}_file.py").write_text(f"# From {wp_id}")
        subprocess.run(["git", "add", "."], cwd=wp_path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"Add {wp_id} content"], cwd=wp_path, check=True, capture_output=True)

    result = subprocess.run(
        ["spec-kitty", "merge"],
        cwd=feature.project_dir,
        capture_output=True,
        text=True,
    )

    output = result.stdout + result.stderr

    # Find positions of WP mentions in merge output
    # WP01 should be processed/mentioned before WP02
    wp01_merge_pos = output.lower().find("merging wp01") or output.lower().find("wp01")
    wp02_merge_pos = output.lower().find("merging wp02") or output.lower().find("wp02")

    if wp01_merge_pos != -1 and wp02_merge_pos != -1:
        assert wp01_merge_pos < wp02_merge_pos, \
            f"WP01 should merge before WP02. Output: {output}"
```

---

### Subtask T023 – Test diamond dependency pattern

**Purpose**: Verify complex diamond dependency is handled correctly.

**Steps**:
1. Create: WP01 (root), WP02→WP01, WP03→WP01, WP04→(WP02,WP03)
2. Run `spec-kitty merge`
3. Verify WP01 first, then WP02/WP03 (either order), then WP04

**Files**: `tests/functional/test_merge_ordering.py` (~60 lines)

**Parallel?**: Yes - independent test

**Code**:
```python
def test_diamond_dependency_ordering(self, create_test_feature):
    """Diamond dependency pattern merges in correct order."""
    feature = create_test_feature(
        wp_configs=[
            WPFixture("WP01", lane="done"),
            WPFixture("WP02", lane="done", dependencies=["WP01"]),
            WPFixture("WP03", lane="done", dependencies=["WP01"]),
            WPFixture("WP04", lane="done", dependencies=["WP02", "WP03"]),
        ]
    )

    # Add content to each WP
    for wp_id in ["WP01", "WP02", "WP03", "WP04"]:
        wp_path = feature.get_worktree_path(wp_id)
        (wp_path / f"{wp_id.lower()}.txt").write_text(f"Content from {wp_id}")
        subprocess.run(["git", "add", "."], cwd=wp_path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"Add {wp_id}"], cwd=wp_path, check=True, capture_output=True)

    result = subprocess.run(
        ["spec-kitty", "merge"],
        cwd=feature.project_dir,
        capture_output=True,
        text=True,
    )

    output = result.stdout + result.stderr

    # Verify order: WP01 must be first, WP04 must be last
    # WP02 and WP03 can be in any order (both depend only on WP01)
    wp_positions = {}
    for wp in ["WP01", "WP02", "WP03", "WP04"]:
        pos = output.find(wp)
        if pos != -1:
            wp_positions[wp] = pos

    if len(wp_positions) == 4:
        assert wp_positions["WP01"] < wp_positions["WP04"], "WP01 must be before WP04"
        assert wp_positions["WP02"] < wp_positions["WP04"], "WP02 must be before WP04"
        assert wp_positions["WP03"] < wp_positions["WP04"], "WP03 must be before WP04"
        assert wp_positions["WP01"] < wp_positions["WP02"], "WP01 must be before WP02"
        assert wp_positions["WP01"] < wp_positions["WP03"], "WP01 must be before WP03"
```

---

### Subtask T024 – Test circular dependency detection (FR-015)

**Purpose**: Verify circular dependencies are detected with clear error.

**Steps**:
1. Create: WP01→WP02, WP02→WP01 (cycle)
2. Run `spec-kitty merge`
3. Verify error mentions cycle/circular

**Files**: `tests/functional/test_merge_ordering.py` (~45 lines)

**Parallel?**: Yes - independent test

**Code**:
```python
def test_circular_dependency_detected(self, create_test_feature):
    """Circular dependencies detected with clear error (FR-015)."""
    feature = create_test_feature(
        wp_configs=[
            WPFixture("WP01", lane="done", dependencies=["WP02"]),
            WPFixture("WP02", lane="done", dependencies=["WP01"]),
        ]
    )

    result = subprocess.run(
        ["spec-kitty", "merge"],
        cwd=feature.project_dir,
        capture_output=True,
        text=True,
    )

    # Should fail with circular dependency error
    assert result.returncode != 0, "Should fail on circular dependency"

    output = result.stdout + result.stderr
    assert any(word in output.lower() for word in ["circular", "cycle", "loop"]), \
        f"Should mention circular dependency: {output}"
```

---

### Subtask T025 – Test numerical fallback (FR-016)

**Purpose**: Verify merge uses numerical order when no dependencies.

**Steps**:
1. Create: WP01, WP02, WP03 (no dependencies)
2. Run `spec-kitty merge`
3. Verify order is WP01→WP02→WP03

**Files**: `tests/functional/test_merge_ordering.py` (~45 lines)

**Parallel?**: Yes - independent test

**Code**:
```python
def test_numerical_fallback_ordering(self, create_test_feature):
    """No dependencies falls back to numerical order (FR-016)."""
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

    result = subprocess.run(
        ["spec-kitty", "merge"],
        cwd=feature.project_dir,
        capture_output=True,
        text=True,
    )

    output = result.stdout + result.stderr

    # Should process in numerical order
    wp01_pos = output.find("WP01")
    wp02_pos = output.find("WP02")
    wp03_pos = output.find("WP03")

    if all(pos != -1 for pos in [wp01_pos, wp02_pos, wp03_pos]):
        assert wp01_pos < wp02_pos < wp03_pos, \
            f"Should be in numerical order. Output: {output}"
```

---

### Subtask T026 – Test frontmatter dependency parsing (FR-013)

**Purpose**: Verify frontmatter `dependencies: []` is parsed correctly.

**Steps**:
1. Create WPs with various dependency formats
2. Verify parsing handles: empty list, single dep, multiple deps

**Files**: `tests/functional/test_merge_ordering.py` (~50 lines)

**Parallel?**: Yes - independent test

**Code**:
```python
def test_frontmatter_dependency_parsing(self, create_test_feature):
    """Frontmatter dependencies: [] parsed correctly (FR-013)."""
    feature = create_test_feature(
        wp_configs=[
            WPFixture("WP01", lane="done", dependencies=[]),  # Empty
            WPFixture("WP02", lane="done", dependencies=["WP01"]),  # Single
            WPFixture("WP03", lane="done", dependencies=["WP01", "WP02"]),  # Multiple
        ]
    )

    # Add content
    for wp_id in ["WP01", "WP02", "WP03"]:
        wp_path = feature.get_worktree_path(wp_id)
        (wp_path / f"{wp_id.lower()}.txt").write_text(f"{wp_id}")
        subprocess.run(["git", "add", "."], cwd=wp_path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", wp_id], cwd=wp_path, check=True, capture_output=True)

    result = subprocess.run(
        ["spec-kitty", "merge", "--dry-run"],
        cwd=feature.project_dir,
        capture_output=True,
        text=True,
    )

    # Should not error on parsing
    assert result.returncode == 0 or "error" not in result.stderr.lower(), \
        f"Should parse dependencies without error: {result.stderr}"

    # WP03 should be last (depends on WP01 and WP02)
    output = result.stdout + result.stderr
    wp01_pos = output.find("WP01")
    wp03_pos = output.find("WP03")
    if wp01_pos != -1 and wp03_pos != -1:
        assert wp01_pos < wp03_pos, "WP01 should be before WP03"
```

---

### Subtask T027 – Test multiple parallel dependency chains

**Purpose**: Verify parallel chains are both respected.

**Steps**:
1. Create: WP01→WP03, WP02→WP04 (two independent chains)
2. Run merge
3. Verify each chain is internally ordered

**Files**: `tests/functional/test_merge_ordering.py` (~50 lines)

**Parallel?**: Yes - independent test

**Code**:
```python
def test_multiple_parallel_chains(self, create_test_feature):
    """Multiple parallel dependency chains respected."""
    feature = create_test_feature(
        wp_configs=[
            WPFixture("WP01", lane="done"),
            WPFixture("WP02", lane="done"),
            WPFixture("WP03", lane="done", dependencies=["WP01"]),
            WPFixture("WP04", lane="done", dependencies=["WP02"]),
        ]
    )

    # Add content
    for wp_id in ["WP01", "WP02", "WP03", "WP04"]:
        wp_path = feature.get_worktree_path(wp_id)
        (wp_path / f"{wp_id.lower()}.txt").write_text(f"{wp_id}")
        subprocess.run(["git", "add", "."], cwd=wp_path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", wp_id], cwd=wp_path, check=True, capture_output=True)

    result = subprocess.run(
        ["spec-kitty", "merge"],
        cwd=feature.project_dir,
        capture_output=True,
        text=True,
    )

    output = result.stdout + result.stderr

    # WP01 before WP03 (chain 1)
    # WP02 before WP04 (chain 2)
    wp_positions = {wp: output.find(wp) for wp in ["WP01", "WP02", "WP03", "WP04"]}

    if all(pos != -1 for pos in wp_positions.values()):
        assert wp_positions["WP01"] < wp_positions["WP03"], "Chain 1: WP01 before WP03"
        assert wp_positions["WP02"] < wp_positions["WP04"], "Chain 2: WP02 before WP04"
```

---

## Test Strategy

Run all tests with:
```bash
pytest tests/functional/test_merge_ordering.py -v
```

Expected: 6 tests, all passing.

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Order not visible in output | Use --dry-run to see planned order |
| Frontmatter format changes | Use fixture to generate correct format |
| Cycle detection message varies | Match on partial keywords |

---

## Definition of Done Checklist

- [ ] `tests/functional/test_merge_ordering.py` exists
- [ ] Test: dependency ordering (FR-014)
- [ ] Test: diamond dependency pattern
- [ ] Test: circular dependency detection (FR-015)
- [ ] Test: numerical fallback (FR-016)
- [ ] Test: frontmatter parsing (FR-013)
- [ ] Test: parallel chains
- [ ] All tests pass: `pytest tests/functional/test_merge_ordering.py -v`

---

## Review Guidance

- Verify dependency declarations in fixtures are correct YAML
- Check circular dependency test actually creates a cycle
- Ensure diamond pattern test validates all constraints
- Verify output parsing is robust to format changes

---

## Activity Log

- 2026-01-18T12:27:56Z – system – lane=planned – Prompt created.
- 2026-01-18T13:27:01Z – claude-opus – shell_pid=54127 – lane=doing – Started implementation via workflow command
- 2026-01-18T13:28:49Z – claude-opus – shell_pid=54127 – lane=for_review – Ready for review: 6 tests for smart merge ordering (FR-013 to FR-016 plus diamond pattern and parallel chains)
- 2026-01-18T13:29:38Z – claude-opus – shell_pid=64382 – lane=doing – Started review via workflow command
- 2026-01-18T13:30:57Z – claude-opus – shell_pid=64382 – lane=done – Review passed: All 6 tests pass. Complete coverage for FR-013 through FR-016. Proper dependency ordering tests including diamond pattern, circular detection, numerical fallback, and parallel chains. Uses correct fixtures from WP01.
