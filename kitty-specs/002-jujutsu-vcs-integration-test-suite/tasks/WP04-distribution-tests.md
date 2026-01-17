---
work_package_id: "WP04"
subtasks:
  - "T018"
  - "T019"
  - "T020"
  - "T021"
  - "T022"
title: "Distribution Tests"
phase: "Phase 1 - Foundation"
<<<<<<< HEAD
<<<<<<< HEAD
lane: "done"
assignee: ""
agent: "claude-opus"
shell_pid: "1269"
review_status: "approved"
reviewed_by: "Robert Douglass"
=======
lane: "for_review"
assignee: ""
=======
lane: "for_review"
assignee: ""
>>>>>>> 002-jujutsu-vcs-integration-test-suite-WP06
agent: "__AGENT__"
shell_pid: "71748"
review_status: ""
reviewed_by: ""
>>>>>>> 002-jujutsu-vcs-integration-test-suite-WP05
dependencies: ["WP01"]
history:
  - timestamp: "2026-01-17T16:05:17Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 – Distribution Tests

## Implementation Command

```bash
spec-kitty implement WP04 --base WP01
```

---

## Objectives & Success Criteria

**Goal**: Validate jj features work for PyPI users WITHOUT template bypass.

**CRITICAL**: The 0.10.8 catastrophe happened because tests used SPEC_KITTY_TEMPLATE_ROOT bypass while 100% of PyPI users failed. These tests prevent that.

**Success Criteria**:
1. DIST-001: `spec-kitty init` works without TEMPLATE_ROOT
2. DIST-002: VCS detection works from PyPI
3. DIST-003: jj workspace creation functional
4. DIST-004: Templates use Python CLI (no bash/PowerShell)
5. DIST-005: No import errors in VCS code

---

## Context & Constraints

- **NO SPEC_KITTY_TEMPLATE_ROOT** - use `no_template_bypass` fixture
- Mark all tests `@pytest.mark.distribution`
- Test against INSTALLED package

---

## Subtasks & Detailed Guidance

### Subtask T018 – Test DIST-001: init without TEMPLATE_ROOT

```python
@pytest.mark.distribution
@pytest.mark.jj
def test_dist_001_init_without_bypass(tmp_path, no_template_bypass):
    assert "SPEC_KITTY_TEMPLATE_ROOT" not in os.environ
    project = tmp_path / "project"
    project.mkdir()
    subprocess.run(["git", "init"], cwd=project, check=True)
    result = subprocess.run(["spec-kitty", "init"], cwd=project, capture_output=True, text=True)
    assert result.returncode == 0, f"Failed: {result.stderr}"
```

**Files**: `tests/distribution/test_jj_distribution.py`

---

### Subtask T019 – Test DIST-002: VCS detection from PyPI

Create feature without bypass, verify VCS detected and stored.

**Files**: `tests/distribution/test_jj_distribution.py`

---

### Subtask T020 – Test DIST-003: workspace functional

End-to-end: init → specify → implement without TEMPLATE_ROOT.

**Files**: `tests/distribution/test_jj_distribution.py`

---

### Subtask T021 – Test DIST-004: Python CLI templates

Check bundled templates for bash/PowerShell references - should use Python CLI only.

**Files**: `tests/distribution/test_jj_distribution.py`

---

### Subtask T022 – Test DIST-005: no import errors

Import all VCS modules, verify no ImportError:
- `specify_cli.core.vcs`
- `specify_cli.core.vcs.jujutsu`
- etc.

**Files**: `tests/distribution/test_jj_distribution.py`

---

## Definition of Done Checklist

- [ ] T018-T022: All 5 DIST-* tests implemented
- [ ] All tests use `no_template_bypass` fixture
- [ ] Tests would catch 0.10.8-style bugs

---

## Activity Log

- 2026-01-17T16:05:17Z – system – lane=planned – Prompt created via /spec-kitty.tasks
<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> 002-jujutsu-vcs-integration-test-suite-WP06
- 2026-01-17T16:31:50Z – codex – shell_pid=71748 – lane=doing – Started implementation via workflow command
- 2026-01-17T16:53:32Z – codex – shell_pid=71748 – lane=for_review – Ready for review: add jj distribution tests (init/no bypass, VCS lock, workspace creation, template CLI checks, VCS imports)
- 2026-01-17T17:19:36Z – __AGENT__ – shell_pid=71748 – lane=doing – Started implementation via workflow command
- 2026-01-17T17:20:32Z – __AGENT__ – shell_pid=71748 – lane=for_review – Ready for review: add jj distribution tests (init/no bypass, VCS lock, workspace creation, template CLI checks, VCS imports)
<<<<<<< HEAD
- 2026-01-17T17:43:06Z – claude-opus – shell_pid=1269 – lane=doing – Started review via workflow command
- 2026-01-17T17:44:35Z – claude-opus – shell_pid=1269 – lane=done – Review passed: All 5 DIST tests implemented correctly with no_template_bypass fixture, tests pass, prevents 0.10.8-style bypass bugs
=======
- 2026-01-17T16:31:50Z – __AGENT__ – shell_pid=71748 – lane=doing – Started implementation via workflow command
- 2026-01-17T16:53:32Z – __AGENT__ – shell_pid=71748 – lane=for_review – Ready for review: add jj distribution tests (init/no bypass, VCS lock, workspace creation, template CLI checks, VCS imports)
>>>>>>> 002-jujutsu-vcs-integration-test-suite-WP05
=======
>>>>>>> 002-jujutsu-vcs-integration-test-suite-WP06
