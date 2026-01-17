---
work_package_id: WP06
title: Sync Command Tests
lane: planned
dependencies:
- WP01
subtasks:
- T028
- T029
- T030
- T031
- T032
phase: Phase 2 - Core Features
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-17T16:05:17Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP06 – Sync Command Tests

## Implementation Command

```bash
spec-kitty implement WP06 --base WP05
```

---

## Objectives & Success Criteria

**Goal**: Validate `spec-kitty sync` works for both VCS backends.

**Success Criteria**:
1. SYNC-001: jj stale workspace syncs via `jj workspace update-stale`
2. SYNC-002: git stale workspace syncs via git rebase
3. SYNC-003: Up-to-date workspace reports "already up to date"
4. SYNC-004: Sync with conflicts lists conflicted files
5. SYNC-005: Dependency chain propagates to downstream

---

## Context & Constraints

- Use workspace fixtures from WP05
- Create stale state by modifying upstream after workspace creation
- Parametrize for git/jj parity

---

## Subtasks & Detailed Guidance

### Subtask T028 – Test SYNC-001: jj stale sync

```python
@pytest.mark.jj
def test_sync_001_jj_stale_workspace(jj_workspace):
    # Modify upstream (main branch)
    # Run spec-kitty sync
    # Verify workspace updated
```

**Files**: `tests/functional/test_jj_sync.py`

---

### Subtask T029 – Test SYNC-002: git stale sync

Same as SYNC-001 but for git worktree - verify git rebase used.

**Files**: `tests/functional/test_jj_sync.py`

---

### Subtask T030 – Test SYNC-003: up-to-date message

Run sync on already current workspace, verify "already up to date" message.

**Files**: `tests/functional/test_jj_sync.py`

---

### Subtask T031 – Test SYNC-004: conflicts listed

Create conflicting changes in upstream and workspace, sync, verify conflicts reported.

**Files**: `tests/functional/test_jj_sync.py`

---

### Subtask T032 – Test SYNC-005: chain propagation

Create WP01 → WP02 chain, modify main, sync WP01, verify WP02 also updated.

**Files**: `tests/functional/test_jj_sync.py`

---

## Definition of Done Checklist

- [ ] T028-T032: All 5 SYNC-* tests implemented
- [ ] Both git and jj sync paths tested
- [ ] Conflict reporting verified

---

## Activity Log

- 2026-01-17T16:05:17Z – system – lane=planned – Prompt created via /spec-kitty.tasks
