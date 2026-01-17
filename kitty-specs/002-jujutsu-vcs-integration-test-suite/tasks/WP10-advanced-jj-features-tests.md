---
work_package_id: WP10
title: Advanced jj Features Tests
lane: "doing"
dependencies:
- WP01
subtasks:
- T048
- T049
- T050
- T051
- T052
- T053
phase: Phase 3 - Advanced
assignee: ''
agent: "__AGENT__"
shell_pid: "71748"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-17T16:05:17Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP10 – Advanced jj Features Tests

## Implementation Command

```bash
spec-kitty implement WP10 --base WP06
```

---

## Objectives & Success Criteria

**Goal**: Validate ops log/undo, Change ID stability, and colocated mode.

**Success Criteria**:
1. OPS-001: `spec-kitty ops log` shows jj operation history
2. OPS-002: `spec-kitty ops undo` reverses last operation
3. CHG-001: Change ID stable across 5 rebases
4. COL-001: Colocated - jj changes visible in git log
5. COL-002: Colocated - git changes visible in jj log
6. PURE-001: Pure jj mode (no git) functional

---

## Context & Constraints

- All tests marked `@pytest.mark.jj`
- Change ID test: record ID, rebase 5 times, verify same ID
- Colocated tests: make changes via one tool, verify via other
- Use fresh workspace per test for ops undo

---

## Subtasks & Detailed Guidance

### Subtask T048 – Test OPS-001: ops log

```python
@pytest.mark.jj
def test_ops_001_log(jj_workspace):
    result = subprocess.run(
        ["spec-kitty", "ops", "log"],
        cwd=jj_workspace, capture_output=True, text=True
    )
    assert result.returncode == 0
    # Verify operation history shown
```

**Files**: `tests/functional/test_jj_advanced.py`

---

### Subtask T049 – Test OPS-002: ops undo

Perform operation, undo, verify state restored.

**Files**: `tests/functional/test_jj_advanced.py`

---

### Subtask T050 – Test CHG-001: Change ID stability

```python
@pytest.mark.jj
def test_chg_001_change_id_stable(jj_workspace):
    # Get initial change ID
    # Rebase 5 times
    # Verify same change ID
```

**Files**: `tests/functional/test_jj_advanced.py`

---

### Subtask T051 – Test COL-001: jj→git visibility

Make change via jj, verify visible in `git log`.

**Files**: `tests/functional/test_jj_advanced.py`

---

### Subtask T052 – Test COL-002: git→jj visibility

Make change via git, verify visible in `jj log`.

**Files**: `tests/functional/test_jj_advanced.py`

---

### Subtask T053 – Test PURE-001: pure jj mode

Test workspace without git colocated mode (pure jj).

**Files**: `tests/functional/test_jj_advanced.py`

---

## Definition of Done Checklist

- [ ] T048-T053: All 6 tests implemented
- [ ] Ops log/undo verified
- [ ] Change ID stability across rebases
- [ ] Colocated mode bidirectional sync

---

## Activity Log

- 2026-01-17T16:05:17Z – system – lane=planned – Prompt created via /spec-kitty.tasks
- 2026-01-17T18:43:16Z – __AGENT__ – shell_pid=71748 – lane=doing – Started implementation via workflow command
