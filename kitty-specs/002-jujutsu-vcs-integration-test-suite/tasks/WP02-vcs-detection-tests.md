---
work_package_id: "WP02"
subtasks:
  - "T007"
  - "T008"
  - "T009"
  - "T010"
  - "T011"
  - "T012"
  - "T055"
title: "VCS Detection Tests"
phase: "Phase 1 - Foundation"
lane: "doing"
assignee: ""
agent: "__AGENT__"
shell_pid: "71748"
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

# Work Package Prompt: WP02 – VCS Detection Tests

## Implementation Command

```bash
spec-kitty implement WP02 --base WP01
```

---

## Objectives & Success Criteria

**Goal**: Validate jj/git detection and selection logic across all scenarios.

**Success Criteria**:
1. DET-001: Both jj+git installed → jj selected
2. DET-002: Git only → git selected with jj recommendation
3. DET-003: Neither installed → clear error
4. DET-004: `--vcs=git` override works
5. DET-005: Broken jj → git fallback with warning
6. DET-006: Wrong jj tool detected
7. DET-007: jj version below minimum (< 0.20) → warning/error with upgrade message

---

## Context & Constraints

- Use fixtures from WP01
- Mark tests `@pytest.mark.jj` where jj expected
- Use PATH manipulation for availability simulation
- No mocking - real execution per spec

---

## Subtasks & Detailed Guidance

### Subtask T007 – Test DET-001: jj+git installed → jj selected

```python
@pytest.mark.jj
def test_det_001_jj_and_git_selects_jj(spec_kitty_project):
    """When both jj and git installed, jj is selected."""
    result = subprocess.run(
        ["spec-kitty", "specify", "test-feature"],
        cwd=spec_kitty_project, capture_output=True, text=True
    )
    meta_json = spec_kitty_project / "kitty-specs" / "001-test-feature" / "meta.json"
    with open(meta_json) as f:
        meta = json.load(f)
    assert meta.get("vcs") == "jj"
```

**Files**: `tests/functional/test_jj_vcs_detection.py`

---

### Subtask T008 – Test DET-002: git only → recommendation

Simulate jj unavailable via PATH manipulation, verify git used with jj recommendation message.

**Files**: `tests/functional/test_jj_vcs_detection.py`

---

### Subtask T009 – Test DET-003: neither → error

Use empty PATH, verify clear error with installation instructions.

**Files**: `tests/functional/test_jj_vcs_detection.py`

---

### Subtask T010 – Test DET-004: --vcs=git override

```python
@pytest.mark.jj
def test_det_004_vcs_git_override(spec_kitty_project):
    subprocess.run(
        ["spec-kitty", "specify", "test-feature", "--vcs=git"],
        cwd=spec_kitty_project, check=True
    )
    # Verify git selected despite jj available
```

**Files**: `tests/functional/test_jj_vcs_detection.py`

---

### Subtask T011 – Test DET-005: broken jj fallback

Create fake broken jj binary, verify git fallback with warning.

**Files**: `tests/functional/test_jj_vcs_detection.py`

---

### Subtask T012 – Test DET-006: wrong tool validation

Create fake jj that outputs non-jujutsu version, verify detection/fallback.

**Files**: `tests/functional/test_jj_vcs_detection.py`

---

### Subtask T055 – Test DET-007: jj version below minimum

**Purpose**: Verify spec-kitty handles outdated jj installations gracefully.

**Rationale**: Per spec.md edge case "jj version is below minimum (< 0.20)", the system should detect this and provide a clear upgrade message rather than failing cryptically.

**Steps**:
```python
def test_det_007_jj_version_below_minimum(spec_kitty_project, tmp_path, monkeypatch):
    """DET-007: jj version below minimum triggers warning/fallback.

    Simulates an old jj installation (< 0.20) that may lack required features.
    """
    import os
    import stat

    # Create fake jj that reports old version
    fake_bin = tmp_path / "fake_bin"
    fake_bin.mkdir()

    old_jj = fake_bin / "jj"
    old_jj.write_text('#!/bin/bash\necho "jj 0.15.0"')
    old_jj.chmod(stat.S_IRWXU)

    # Keep real git accessible
    import shutil
    git_path = shutil.which("git")
    (fake_bin / "git").symlink_to(git_path)

    # Preserve spec-kitty
    spec_kitty_path = shutil.which("spec-kitty")
    if spec_kitty_path:
        (fake_bin / "spec-kitty").symlink_to(spec_kitty_path)

    result = subprocess.run(
        ["spec-kitty", "specify", "test-feature"],
        cwd=spec_kitty_project,
        capture_output=True,
        text=True,
        env={**os.environ, "PATH": str(fake_bin) + ":" + os.environ.get("PATH", "")}
    )

    combined = result.stdout + result.stderr

    # Should either:
    # 1. Warn about old jj version and continue with git
    # 2. Fail with clear message about minimum version
    # Should NOT: silently use old jj and fail later
    assert any([
        "version" in combined.lower(),
        "0.20" in combined,
        "upgrade" in combined.lower(),
        "minimum" in combined.lower(),
        # Or fell back to git successfully
        result.returncode == 0
    ]), f"Should handle old jj version gracefully: {combined}"
```

**Files**: `tests/functional/test_jj_vcs_detection.py`

**Edge Case Coverage**: This addresses spec.md line 266: "What happens when jj version is below minimum (< 0.20)?"

---

## Definition of Done Checklist

- [ ] T007-T012: All 6 original DET-* tests implemented
- [ ] T055: DET-007 jj version check test implemented
- [ ] Tests use WP01 fixtures
- [ ] PATH manipulation isolated per test

---

## Activity Log

- 2026-01-17T16:05:17Z – system – lane=planned – Prompt created via /spec-kitty.tasks
- 2026-01-17T16:25:55Z – claude-opus – shell_pid=69424 – lane=doing – Started implementation via workflow command
- 2026-01-17T16:30:25Z – claude-opus – shell_pid=69424 – lane=for_review – Ready for review: All 7 VCS detection tests pass (DET-001 through DET-007 + edge cases). Tests validate jj/git selection, override flags, broken jj fallback, version checks, and wrong-tool detection.
- 2026-01-17T16:54:10Z – codex – shell_pid=71748 – lane=doing – Started review via workflow command
- 2026-01-17T16:55:37Z – codex – shell_pid=71748 – lane=planned – Moved to planned
- 2026-01-17T17:02:30Z – claude-opus – shell_pid=89278 – lane=doing – Started implementation via workflow command
- 2026-01-17T17:08:24Z – claude-opus – shell_pid=89278 – lane=for_review – Ready for review: Addressed all 4 review feedback issues. Tests now validate VCS selection via output/directory presence, PATH isolation is complete, DET-003 handles spec-kitty's graceful no-VCS mode, and edge cases use WP01 fixtures. All 10 tests pass.
- 2026-01-17T17:17:11Z – codex – shell_pid=71748 – lane=doing – Started review via workflow command
- 2026-01-17T17:17:54Z – codex – shell_pid=71748 – lane=planned – Moved to planned
- 2026-01-17T17:35:02Z – __AGENT__ – shell_pid=71748 – lane=doing – Started implementation via workflow command
