---
work_package_id: WP07
title: Conflict Handling Tests
lane: "for_review"
dependencies:
- WP01
subtasks:
- T033
- T034
- T035
- T036
- T037
- T038
phase: Phase 2 - Core Features
assignee: ''
agent: "codex"
shell_pid: "15916"
review_status: "has_feedback"
reviewed_by: "Robert Douglass"
history:
- timestamp: '2026-01-17T16:05:17Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP07 – Conflict Handling Tests

## Implementation Command

```bash
spec-kitty implement WP07 --base WP06
```

---

## Objectives & Success Criteria

**Goal**: Validate jj non-blocking conflicts and review/merge blocking.

**Key semantic difference**: jj stores conflicts in files (work continues), git may block.

**Success Criteria**:
1. CONF-001: jj sync succeeds with conflict stored in file
2. CONF-002: git sync conflict behavior (may block)
3. CONF-003: `/spec-kitty.review` blocked with conflicts
4. CONF-004: Merge command blocked with conflicts
5. CONF-005: Conflict resolution auto-recorded by jj
6. CONF-006: 3-way merge shows all sides

---

## Context & Constraints

- Create conflicts by modifying same file in upstream and workspace
- Test both blocking (review/merge) and non-blocking (sync) behavior
- Verify conflict markers in file content

---

## Subtasks & Detailed Guidance

### Subtask T033 – Test CONF-001: jj conflict stored

```python
@pytest.mark.jj
def test_conf_001_jj_conflict_stored(jj_workspace):
    # Create conflict
    # Run sync - should succeed
    # Verify conflict markers in file
```

**Files**: `tests/functional/test_jj_conflicts.py`

---

### Subtask T034 – Test CONF-002: git conflict behavior

Test git conflict handling - may block or need resolution.

**Files**: `tests/functional/test_jj_conflicts.py`

---

### Subtask T035 – Test CONF-003: review blocked

With conflicts present, `/spec-kitty.review` should be blocked.

**Files**: `tests/functional/test_jj_conflicts.py`

---

### Subtask T036 – Test CONF-004: merge blocked

With conflicts present, merge should be blocked.

**Files**: `tests/functional/test_jj_conflicts.py`

---

### Subtask T037 – Test CONF-005: resolution recorded

Resolve conflict by editing file, verify jj auto-records resolution.

**Files**: `tests/functional/test_jj_conflicts.py`

---

### Subtask T038 – Test CONF-006: 3-way conflict

Create 3-sided conflict scenario, verify all sides visible in markers.

**Files**: `tests/functional/test_jj_conflicts.py`

---

## Definition of Done Checklist

- [ ] T033-T038: All 6 CONF-* tests implemented
- [ ] jj non-blocking conflict verified
- [ ] Review/merge blocking verified

---

## Activity Log

- 2026-01-17T16:05:17Z – system – lane=planned – Prompt created via /spec-kitty.tasks
- 2026-01-17T17:46:00Z – claude-opus – shell_pid=5008 – lane=doing – Started implementation via workflow command
- 2026-01-17T17:49:47Z – claude-opus – shell_pid=5008 – lane=for_review – Ready for review: 9 conflict handling tests implemented (CONF-001 to CONF-006 + 3 edge cases). 8 pass, 1 xfail (git-only test needs workspace support). Tests cover jj non-blocking conflicts, review/merge blocking, resolution auto-recording, and 3-way merge markers.
- 2026-01-17T18:11:31Z – codex – shell_pid=15916 – lane=doing – Started review via workflow command
- 2026-01-17T18:12:56Z – codex – shell_pid=15916 – lane=planned – Moved to planned
- 2026-01-17T18:16:04Z – codex – shell_pid=15916 – lane=doing – Started implementation via workflow command
- 2026-01-17T18:33:40Z – codex – shell_pid=15916 – lane=for_review – Ready for review: use jj rebase + conflicts() to create real conflicts; tighten assertions; adjust jj status/markers handling
