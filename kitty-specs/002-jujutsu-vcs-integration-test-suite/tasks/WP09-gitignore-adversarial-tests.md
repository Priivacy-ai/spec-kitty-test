---
work_package_id: "WP09"
subtasks:
  - "T043"
  - "T044"
  - "T045"
  - "T046"
  - "T047"
title: "Gitignore and Adversarial Tests"
phase: "Phase 2 - Core Features"
lane: "for_review"
assignee: ""
agent: "claude-opus"
shell_pid: "14750"
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

# Work Package Prompt: WP09 – Gitignore and Adversarial Tests

## Implementation Command

```bash
spec-kitty implement WP09 --base WP01
```

---

## Objectives & Success Criteria

**Goal**: Validate gitignore handling and adversarial edge cases.

**Bug Context**: The .gitignore template was incorrectly ignoring `kitty-specs/` in main repo - this should NOT happen.

**Success Criteria**:
1. GI-001: Main repo .gitignore does NOT ignore kitty-specs/
2. GI-002: `git add kitty-specs/` succeeds
3. GI-003: Upgrade fixes incorrect gitignore
4. ADV-001: Corrupted meta.json handled
5. ADV-002: Corrupted workspace directory handled

---

## Context & Constraints

- Gitignore tests check content, not just behavior
- Adversarial tests intentionally corrupt files
- Verify graceful error handling (no crashes)

---

## Subtasks & Detailed Guidance

### Subtask T043 – Test GI-001: kitty-specs not ignored

```python
def test_gi_001_kitty_specs_not_ignored(spec_kitty_project):
    gitignore = spec_kitty_project / ".gitignore"
    content = gitignore.read_text()
    # Should NOT contain line that ignores kitty-specs/
    assert "kitty-specs/" not in content or "!kitty-specs/" in content
```

**Files**: `tests/functional/test_jj_gitignore.py`

---

### Subtask T044 – Test GI-002: git add works

```python
def test_gi_002_git_add_kitty_specs(spec_kitty_project):
    result = subprocess.run(
        ["git", "add", "kitty-specs/"],
        cwd=spec_kitty_project, capture_output=True
    )
    assert result.returncode == 0
    # Verify files staged
```

**Files**: `tests/functional/test_jj_gitignore.py`

---

### Subtask T045 – Test GI-003: upgrade fixes gitignore

If gitignore incorrectly ignores kitty-specs/, verify upgrade/init fixes it.

**Files**: `tests/functional/test_jj_gitignore.py`

---

### Subtask T046 – Test ADV-001: corrupted meta.json

```python
@pytest.mark.jj
def test_adv_001_corrupted_meta_json(spec_kitty_project):
    # Create feature
    # Write invalid JSON to meta.json
    # Run command - should not crash
```

**Files**: `tests/functional/test_jj_gitignore.py`

---

### Subtask T047 – Test ADV-002: corrupted workspace

Create workspace directory with missing/corrupted files, verify graceful handling.

**Files**: `tests/functional/test_jj_gitignore.py`

---

## Definition of Done Checklist

- [ ] T043-T047: All 5 tests implemented
- [ ] Gitignore bug tested
- [ ] Adversarial scenarios don't crash

---

## Activity Log

- 2026-01-17T16:05:17Z – system – lane=planned – Prompt created via /spec-kitty.tasks
- 2026-01-17T18:11:09Z – claude-opus – shell_pid=14750 – lane=doing – Started implementation via workflow command
- 2026-01-17T18:13:32Z – claude-opus – shell_pid=14750 – lane=for_review – Ready for review: 14 gitignore and adversarial tests implemented (GI-001 to GI-003 + ADV-001/ADV-002 + edge cases). 13 pass, 1 xfail (GI-003: init doesn't fix bad gitignore). Tests cover gitignore correctness, git add success, corrupted meta.json handling, and corrupted workspace handling.
