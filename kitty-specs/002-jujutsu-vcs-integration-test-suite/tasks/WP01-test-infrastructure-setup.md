---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
  - "T054"
title: "Test Infrastructure Setup"
phase: "Phase 1 - Foundation"
lane: "for_review"
assignee: ""
agent: "claude-opus"
shell_pid: "67125"
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
7. `requires_spec_kitty_version` fixture enables version-gated tests (TR-013)

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

### Subtask T054 – Create `requires_spec_kitty_version` fixture (TR-013)

**Purpose**: Enable version-gated tests that only run on specific spec-kitty versions.

**Rationale**: Per TR-013, tests must support version gating using `requires_v*` fixtures. This allows tests to be written for features that only exist in certain versions.

**Steps**:
```python
import subprocess
from packaging import version

def get_spec_kitty_version():
    """Get installed spec-kitty version."""
    result = subprocess.run(
        ["spec-kitty", "--version"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return None
    # Parse version from output (e.g., "spec-kitty 0.12.0")
    output = result.stdout.strip()
    parts = output.split()
    return parts[-1] if parts else None

@pytest.fixture
def spec_kitty_version():
    """Return the installed spec-kitty version as a string."""
    return get_spec_kitty_version()

def requires_spec_kitty_version(min_version):
    """Decorator to skip test if spec-kitty version is below minimum.

    Usage:
        @requires_spec_kitty_version("0.12.0")
        def test_new_feature():
            ...
    """
    current = get_spec_kitty_version()
    if current is None:
        return pytest.mark.skip(reason="spec-kitty not installed")
    if version.parse(current) < version.parse(min_version):
        return pytest.mark.skip(reason=f"Requires spec-kitty >= {min_version}, got {current}")
    return pytest.mark.parametrize([], [])  # No-op marker

# Convenience markers for common versions
requires_v0_11 = requires_spec_kitty_version("0.11.0")
requires_v0_12 = requires_spec_kitty_version("0.12.0")
```

**Files**: `tests/conftest.py`

**Usage Example**:
```python
@requires_v0_12
@pytest.mark.jj
def test_jj_feature_only_in_v012(spec_kitty_project):
    """This test only runs on spec-kitty 0.12.0+."""
    ...
```

---

## Definition of Done Checklist

- [ ] T001: `@pytest.mark.jj` registered
- [ ] T002: `jj_available` fixture works
- [ ] T003: Auto-skip works for jj tests
- [ ] T004: `@pytest.mark.distribution` registered
- [ ] T005: `spec_kitty_project` creates isolated project
- [ ] T006: `no_template_bypass` removes env vars
- [ ] T054: `requires_spec_kitty_version` fixture and convenience markers work

---

## Activity Log

- 2026-01-17T16:05:17Z – system – lane=planned – Prompt created via /spec-kitty.tasks
- 2026-01-17T16:19:39Z – claude-opus – shell_pid=67125 – lane=doing – Started implementation via workflow command
- 2026-01-17T16:24:58Z – claude-opus – shell_pid=67125 – lane=for_review – Ready for review: All 7 subtasks implemented. 12/12 verification tests pass. Infrastructure includes: jj/distribution markers, jj_available/jj_version fixtures, auto-skip for jj tests, spec_kitty_project fixture, no_template_bypass fixture, and requires_spec_kitty_version version-gating utilities.
