---
work_package_id: "WP08"
subtasks:
  - "T039"
  - "T040"
  - "T041"
  - "T042"
title: "Upgrade Path Tests"
phase: "Phase 2 - Core Features"
lane: "done"
assignee: ""
agent: "claude-opus"
shell_pid: "29108"
review_status: "has_feedback"
reviewed_by: "Robert Douglass"
dependencies: ["WP01"]
history:
  - timestamp: "2026-01-17T16:05:17Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP08 – Upgrade Path Tests

## Implementation Command

```bash
spec-kitty implement WP08 --base WP01
```

---

## Objectives & Success Criteria

**Goal**: Validate git-only to jj migration works safely.

**Success Criteria**:
1. UPG-001: git-only project + jj install → new features use jj
2. UPG-002: Existing git WPs continue working
3. UPG-003: jj uninstalled → clear error on jj features
4. UPG-004: Mixed git/jj project coexistence

---

## Context & Constraints

- Use PATH manipulation to simulate jj install/uninstall
- Create git features first, then "install" jj
- Mark `@pytest.mark.jj` and `@pytest.mark.upgrade`

---

## Subtasks & Detailed Guidance

### Subtask T039 – Test UPG-001: git + jj install

```python
@pytest.mark.jj
@pytest.mark.upgrade
def test_upg_001_git_to_jj(spec_kitty_project, monkeypatch):
    # Create git feature (simulate no jj via PATH)
    # "Install" jj (restore PATH)
    # Create new feature - should use jj
```

**Files**: `tests/distribution/test_jj_upgrade_paths.py`

---

### Subtask T040 – Test UPG-002: existing git WPs work

After jj installed, existing git workspaces should continue functioning.

**Files**: `tests/distribution/test_jj_upgrade_paths.py`

---

### Subtask T041 – Test UPG-003: jj uninstalled error

Create jj feature, "uninstall" jj, verify clear error message.

**Files**: `tests/distribution/test_jj_upgrade_paths.py`

---

### Subtask T042 – Test UPG-004: mixed coexistence

Project with both git and jj features works correctly.

**Files**: `tests/distribution/test_jj_upgrade_paths.py`

---

## Definition of Done Checklist

- [ ] T039-T042: All 4 UPG-* tests implemented
- [ ] PATH manipulation reliable
- [ ] Both directions tested (add jj, remove jj)

---

## Activity Log

- 2026-01-17T16:05:17Z – system – lane=planned – Prompt created via /spec-kitty.tasks
- 2026-01-17T17:50:17Z – claude-opus – shell_pid=9135 – lane=doing – Started implementation via workflow command
- 2026-01-17T17:57:11Z – claude-opus – shell_pid=9135 – lane=for_review – Ready for review: All 4 UPG tests implemented (git-to-jj upgrade, existing git WPs work, jj uninstalled error, mixed coexistence). Tests use PATH manipulation to simulate jj install/uninstall. All tests pass.
- 2026-01-17T18:10:24Z – __AGENT__ – shell_pid=71748 – lane=doing – Started review via workflow command
- 2026-01-17T18:12:03Z – __AGENT__ – shell_pid=71748 – lane=planned – Moved to planned
- 2026-01-17T18:16:01Z – __AGENT__ – shell_pid=71748 – lane=for_review – Ready for review: All 4 UPG tests implemented. Tests use PATH manipulation to simulate jj install/uninstall. All tests pass.
- 2026-01-17T18:33:36Z – claude-opus – shell_pid=29108 – lane=doing – Started review via workflow command
- 2026-01-17T18:34:23Z – claude-opus – shell_pid=29108 – lane=done – Review passed: All 4 UPG tests implemented (git-to-jj upgrade, existing git WPs work, jj uninstalled error, mixed coexistence). Tests use PATH manipulation, no template bypass. All 4 tests pass.
