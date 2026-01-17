---
work_package_id: "WP03"
subtasks:
  - "T013"
  - "T014"
  - "T015"
  - "T016"
  - "T017"
title: "VCS Lock Enforcement Tests"
phase: "Phase 1 - Foundation"
lane: "doing"
assignee: ""
agent: "claude-opus"
shell_pid: "71460"
review_status: ""
reviewed_by: ""
dependencies: ["WP01"]
history:
  - timestamp: "2026-01-17T16:05:17Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 – VCS Lock Enforcement Tests

## Implementation Command

```bash
spec-kitty implement WP03 --base WP01
```

---

## Objectives & Success Criteria

**Goal**: Validate per-feature VCS locking prevents mid-feature VCS changes.

**Success Criteria**:
1. LOCK-001: Feature creation stores VCS in meta.json
2. LOCK-002: --vcs=git on jj feature fails
3. LOCK-003: meta.json tampering detected
4. LOCK-004: Deleted meta.json handled gracefully
5. LOCK-005: Two features with different VCS isolated

---

## Context & Constraints

- Use fixtures from WP01
- All tests marked `@pytest.mark.jj`
- Test real meta.json behavior

---

## Subtasks & Detailed Guidance

### Subtask T013 – Test LOCK-001: VCS stored in meta.json

```python
@pytest.mark.jj
def test_lock_001_vcs_in_meta(spec_kitty_project):
    subprocess.run(["spec-kitty", "specify", "lock-test"], cwd=spec_kitty_project, check=True)
    meta = json.load(open(spec_kitty_project / "kitty-specs" / "001-lock-test" / "meta.json"))
    assert meta["vcs"] == "jj"
```

**Files**: `tests/functional/test_jj_vcs_lock.py`

---

### Subtask T014 – Test LOCK-002: VCS change rejected

Create jj feature, try `--vcs=git` operation, verify rejection.

**Files**: `tests/functional/test_jj_vcs_lock.py`

---

### Subtask T015 – Test LOCK-003: tampering detected

Modify meta.json VCS field manually, run command, verify detection/warning.

**Files**: `tests/functional/test_jj_vcs_lock.py`

---

### Subtask T016 – Test LOCK-004: deleted meta.json handled

Delete meta.json, run command, verify graceful error (no crash).

**Files**: `tests/functional/test_jj_vcs_lock.py`

---

### Subtask T017 – Test LOCK-005: mixed VCS isolation

Create jj feature and git feature in same project, verify each uses correct VCS.

**Files**: `tests/functional/test_jj_vcs_lock.py`

---

## Definition of Done Checklist

- [ ] T013-T017: All 5 LOCK-* tests implemented
- [ ] Tests verify meta.json behavior
- [ ] Graceful error handling tested

---

## Activity Log

- 2026-01-17T16:05:17Z – system – lane=planned – Prompt created via /spec-kitty.tasks
- 2026-01-17T16:30:58Z – claude-opus – shell_pid=71460 – lane=doing – Started implementation via workflow command
