---
work_package_id: "WP02"
subtasks:
  - "T007"
  - "T008"
  - "T009"
  - "T010"
  - "T011"
  - "T012"
title: "VCS Detection Tests"
phase: "Phase 1 - Foundation"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
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

## Definition of Done Checklist

- [ ] T007-T012: All 6 DET-* tests implemented
- [ ] Tests use WP01 fixtures
- [ ] PATH manipulation isolated per test

---

## Activity Log

- 2026-01-17T16:05:17Z – system – lane=planned – Prompt created via /spec-kitty.tasks
