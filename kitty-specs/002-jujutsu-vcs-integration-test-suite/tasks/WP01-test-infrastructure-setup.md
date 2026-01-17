---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
title: "Test Infrastructure Setup"
phase: "Phase 1 - Foundation"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: []
history:
  - timestamp: "2026-01-17T16:05:17Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Test Infrastructure Setup

## Implementation Command

```bash
spec-kitty implement WP01
```

---

## Objectives & Success Criteria

**Goal**: Establish pytest fixtures, markers, and shared utilities for jj testing.

**Success Criteria**:
1. `pytest --collect-only` shows `@pytest.mark.jj` marker registered
2. `pytest --collect-only` shows `@pytest.mark.distribution` marker registered
3. `jj_available` fixture returns True/False based on jj installation
4. Tests marked `@pytest.mark.jj` auto-skip when jj unavailable
5. `spec_kitty_project` fixture creates isolated test project
6. `no_template_bypass` fixture unsets SPEC_KITTY_TEMPLATE_ROOT

---

## Context & Constraints

**Reference Documents**:
- `kitty-specs/002-jujutsu-vcs-integration-test-suite/spec.md` - User stories
- `kitty-specs/002-jujutsu-vcs-integration-test-suite/plan.md` - Architecture decisions
- `kitty-specs/002-jujutsu-vcs-integration-test-suite/data-model.md` - Fixture specifications

**Constraints**:
- **EXTEND** existing `tests/conftest.py` - do NOT replace
- Use session scope for `jj_available` (performance)
- Use `shutil.which("jj")` for detection, validate with `jj --version`

---

## Subtasks & Detailed Guidance

### Subtask T001 – Add `@pytest.mark.jj` marker registration

**Purpose**: Register the `jj` marker so pytest recognizes it without warnings.

**Steps**:
1. Open `tests/conftest.py`
2. Add to `pytest_configure`:
   ```python
   config.addinivalue_line("markers", "jj: tests requiring jujutsu VCS")
   ```

**Files**: `tests/conftest.py`

---

### Subtask T002 – Implement `jj_available` session-scoped fixture

**Purpose**: Check if jj is installed and functional.

**Steps**:
```python
@pytest.fixture(scope="session")
def jj_available():
    """Check if jj (jujutsu) is installed and functional."""
    if shutil.which("jj") is None:
        return False
    try:
        result = subprocess.run(["jj", "--version"], capture_output=True, timeout=10)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False
```

**Files**: `tests/conftest.py`

---

### Subtask T003 – Implement `pytest_collection_modifyitems` for auto-skip

**Purpose**: Automatically skip `@pytest.mark.jj` tests when jj unavailable.

**Steps**:
```python
def pytest_collection_modifyitems(config, items):
    """Auto-skip @pytest.mark.jj tests when jj unavailable."""
    if shutil.which("jj") is None:
        skip_jj = pytest.mark.skip(reason="jj not installed")
        for item in items:
            if "jj" in item.keywords:
                item.add_marker(skip_jj)
```

**Files**: `tests/conftest.py`

---

### Subtask T004 – Add `@pytest.mark.distribution` marker registration

**Purpose**: Register the `distribution` marker for PyPI user tests.

**Steps**: Add to `pytest_configure`:
```python
config.addinivalue_line("markers", "distribution: tests validating PyPI user experience")
```

**Files**: `tests/conftest.py`

---

### Subtask T005 – Create `spec_kitty_project` fixture

**Purpose**: Create isolated spec-kitty project for tests.

**Steps**:
```python
@pytest.fixture
def spec_kitty_project(tmp_path, clean_env):
    """Create an initialized spec-kitty project."""
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    subprocess.run(["git", "init"], cwd=project_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=project_dir, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=project_dir, check=True)
    subprocess.run(["spec-kitty", "init"], cwd=project_dir, check=True, capture_output=True)
    return project_dir
```

**Files**: `tests/conftest.py`

---

### Subtask T006 – Create `no_template_bypass` fixture

**Purpose**: Ensure distribution tests run without SPEC_KITTY_TEMPLATE_ROOT.

**Steps**:
```python
@pytest.fixture
def no_template_bypass(monkeypatch):
    """Ensure no template bypass for distribution tests."""
    monkeypatch.delenv("SPEC_KITTY_TEMPLATE_ROOT", raising=False)
    monkeypatch.delenv("SPEC_KITTY_REPO", raising=False)
    yield
```

**Files**: `tests/conftest.py`

---

## Definition of Done Checklist

- [ ] T001: `@pytest.mark.jj` registered
- [ ] T002: `jj_available` fixture works
- [ ] T003: Auto-skip works for jj tests
- [ ] T004: `@pytest.mark.distribution` registered
- [ ] T005: `spec_kitty_project` creates isolated project
- [ ] T006: `no_template_bypass` removes env vars

---

## Activity Log

- 2026-01-17T16:05:17Z – system – lane=planned – Prompt created via /spec-kitty.tasks
