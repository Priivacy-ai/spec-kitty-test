---
work_package_id: WP05
title: Workspace Creation Tests
lane: planned
dependencies:
- WP01
subtasks:
- T023
- T024
- T025
- T026
- T027
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

# Work Package Prompt: WP05 – Workspace Creation Tests

## Implementation Command

```bash
spec-kitty implement WP05 --base WP02
```

---

## Objectives & Success Criteria

**Goal**: Validate jj workspace creation matches git worktree functionality.

**Success Criteria**:
1. WS-001: jj workspace creates `.worktrees/###-feature-WP01/`
2. WS-002: Colocated mode creates both `.jj/` and `.git/`
3. WS-003: `--base` flag creates dependent workspace
4. WS-004: Sparse-checkout excludes kitty-specs/
5. WS-005: Workspace removal cleans directory

---

## Context & Constraints

- Use fixtures from WP01
- Mark all `@pytest.mark.jj`
- Test both `spec-kitty implement WP01` and `--base WP01`

---

## Subtasks & Detailed Guidance

### Subtask T023 – Test WS-001: jj workspace structure

```python
@pytest.mark.jj
def test_ws_001_jj_workspace_structure(spec_kitty_project):
    # Create feature with tasks
    # Run spec-kitty implement WP01
    # Verify .worktrees/###-feature-WP01/ exists
```

**Files**: `tests/functional/test_jj_workspace.py`

---

### Subtask T024 – Test WS-002: colocated mode

Verify workspace has both `.jj/` and `.git/` directories for git compatibility.

**Files**: `tests/functional/test_jj_workspace.py`

---

### Subtask T025 – Test WS-003: --base flag

Create WP01 workspace, then WP02 with `--base WP01`, verify dependency chain.

**Files**: `tests/functional/test_jj_workspace.py`

---

### Subtask T026 – Test WS-004: sparse-checkout

Verify kitty-specs/ excluded from workspace (not duplicated in worktree).

**Files**: `tests/functional/test_jj_workspace.py`

---

### Subtask T027 – Test WS-005: workspace removal

Create workspace, run removal command, verify directory cleaned.

**Files**: `tests/functional/test_jj_workspace.py`

---

## Definition of Done Checklist

- [ ] T023-T027: All 5 WS-* tests implemented
- [ ] Directory structures verified
- [ ] Both git and jj parity tested where applicable

---

## Activity Log

- 2026-01-17T16:05:17Z – system – lane=planned – Prompt created via /spec-kitty.tasks
