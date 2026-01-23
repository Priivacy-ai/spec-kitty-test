# Test Data Model

**Feature**: Comprehensive Post-JJ-Rollback Test Suite
**Version**: 1.0.0
**Date**: 2026-01-23

## Overview

This document defines the key entities, fixtures, and data structures used throughout the test suite. These are testing constructs, not production code entities.

## Core Test Entities

### TestEnvironment

Represents an isolated test execution context (virtualenv, temp directory, clean git repo).

**Purpose**: Provide consistent, reproducible test environments that don't interfere with each other.

**Attributes**:
- `env_type`: str - Type of environment ("functional" | "distribution" | "integration")
- `spec_kitty_path`: Path - Path to spec-kitty installation (editable or wheel)
- `test_repo_path`: Path - Temporary git repository for testing
- `env_vars`: dict[str, str] - Environment variables (functional includes SPEC_KITTY_TEMPLATE_ROOT, distribution excludes it)

**Lifecycle**:
- Created via pytest fixture (one per test)
- Automatically cleaned up after test completes
- Git repo initialized with clean history

**Example**:
```python
@pytest.fixture
def test_environment(tmp_path, env_type="functional"):
    env = TestEnvironment(
        env_type=env_type,
        spec_kitty_path=Path("/path/to/spec-kitty"),
        test_repo_path=tmp_path / "test-repo",
        env_vars=_build_env_vars(env_type)
    )
    _initialize_git_repo(env.test_repo_path)
    yield env
    # Cleanup automatic via tmp_path
```

---

### MockAgent

Simulated agent for testing orchestrator without real AI agent dependencies.

**Purpose**: Enable fast, deterministic orchestrator testing without requiring real agent installations.

**Attributes**:
- `agent_id`: str - Agent identifier (e.g., "claude-code", "opencode")
- `success_probability`: float - Probability of successful execution (0.0 to 1.0)
- `execution_delay`: float - Simulated execution time in seconds
- `output_pattern`: str - Pattern for stdout/stderr output
- `exit_code`: int - Exit code to return (0 for success, non-zero for failure)

**Behavior**:
- Responds to invocation with deterministic success/failure
- Simulates timeouts when execution_delay exceeds threshold
- Generates realistic output patterns for parsing tests

**Example**:
```python
# Mock agent that succeeds 80% of the time with 2s delay
mock_claude = MockAgent(
    agent_id="claude-code",
    success_probability=0.8,
    execution_delay=2.0,
    output_pattern="Implementation complete. Files modified: {count}",
    exit_code=0
)

# Mock agent that always times out
mock_timeout = MockAgent(
    agent_id="gemini",
    success_probability=0.0,
    execution_delay=float('inf'),
    output_pattern="",
    exit_code=124  # Timeout exit code
)
```

---

### TestFeature

Prepared test feature with known state for consistent testing.

**Purpose**: Provide pre-configured feature structures for testing various scenarios without manual setup.

**Attributes**:
- `feature_number`: str - Feature number (e.g., "001")
- `slug`: str - Full feature slug (e.g., "001-test-feature")
- `mission`: str - Mission type ("software-dev", "research", "documentation")
- `wp_count`: int - Number of work packages
- `dependency_graph`: dict[str, list[str]] - WP dependencies (e.g., {"WP02": ["WP01"]})
- `expected_artifacts`: list[str] - Expected files after planning (spec.md, plan.md, tasks.md)

**Variants**:
- **Simple feature**: 3 WPs, no dependencies, linear workflow
- **Complex feature**: 10+ WPs, dependency chains, parallel execution
- **Legacy feature**: Contains `"vcs": "jj"` in meta.json for backward compatibility testing

**Example**:
```python
simple_feature = TestFeature(
    feature_number="001",
    slug="001-simple-test",
    mission="software-dev",
    wp_count=3,
    dependency_graph={},  # No dependencies
    expected_artifacts=["spec.md", "plan.md", "tasks.md", "tasks/WP01.md", "tasks/WP02.md", "tasks/WP03.md"]
)

complex_feature = TestFeature(
    feature_number="002",
    slug="002-complex-test",
    mission="software-dev",
    wp_count=10,
    dependency_graph={
        "WP02": ["WP01"],
        "WP03": ["WP01"],
        "WP04": ["WP02", "WP03"],
        "WP05": ["WP04"]
    },
    expected_artifacts=[...]
)
```

---

### StateSnapshot

Captured orchestration state at specific point for resume testing.

**Purpose**: Enable interruption and resume testing by capturing orchestration state at precise moments.

**Attributes**:
- `timestamp`: datetime - When snapshot was taken
- `wp_states`: dict[str, str] - WP execution states (e.g., {"WP01": "DONE", "WP02": "IMPLEMENTATION"})
- `agent_assignments`: dict[str, str] - Which agent is assigned to each WP
- `execution_history`: list[dict] - Ordered list of state transitions

**Usage**:
1. Take snapshot during orchestration
2. Simulate interruption (kill process)
3. Restore snapshot and resume
4. Verify continuation from correct state

**Example**:
```python
snapshot = StateSnapshot(
    timestamp=datetime.now(),
    wp_states={
        "WP01": "DONE",
        "WP02": "IMPLEMENTATION",
        "WP03": "PENDING"
    },
    agent_assignments={
        "WP01": "claude-code",
        "WP02": "claude-code",
        "WP03": None
    },
    execution_history=[
        {"wp": "WP01", "from": "PENDING", "to": "IMPLEMENTATION", "timestamp": "..."},
        {"wp": "WP01", "from": "IMPLEMENTATION", "to": "REVIEW", "timestamp": "..."},
        {"wp": "WP01", "from": "REVIEW", "to": "DONE", "timestamp": "..."},
        {"wp": "WP02", "from": "PENDING", "to": "IMPLEMENTATION", "timestamp": "..."}
    ]
)
```

---

### VCSContext

Test context with specific VCS configuration for isolation testing.

**Purpose**: Control VCS detection and command execution for testing git/jj isolation.

**Attributes**:
- `vcs_type`: str - VCS type ("git" | "jj" | "both")
- `detection_override`: dict[str, bool] - Override detection results (e.g., {"jj": False})
- `command_log`: list[tuple[str, list[str]]] - Log of executed commands (binary, args)
- `feature_vcs_lock`: str - Locked VCS from meta.json ("git" | "jj")

**Behavior**:
- Mocks `subprocess.run` to log commands
- Overrides VCS detection when needed
- Validates that correct VCS is used

**Example**:
```python
# Test that jj is never invoked even when installed
vcs_ctx = VCSContext(
    vcs_type="both",  # Both git and jj binaries available
    detection_override={"jj": False},  # Force jj detection to return False
    command_log=[],
    feature_vcs_lock="git"
)

# After test execution, assert no jj commands
assert all(cmd[0] != "jj" for cmd in vcs_ctx.command_log)
assert all(cmd[0] == "git" for cmd in vcs_ctx.command_log if cmd[0] in ["git", "jj"])
```

---

### DistributionPackage

Built wheel for distribution testing with template and migration manifests.

**Purpose**: Represent a spec-kitty distribution package for PyPI user experience testing.

**Attributes**:
- `package_path`: Path - Path to built wheel file
- `version`: str - Package version (e.g., "0.11.2")
- `template_manifest`: list[str] - List of bundled template files
- `migration_list`: list[str] - Registered migrations
- `installed_path`: Path - site-packages installation location after pip install

**Validation**:
- Wheel contains all required template files
- Migrations are registered in __init__.py
- Templates accessible from package without SPEC_KITTY_TEMPLATE_ROOT

**Example**:
```python
pkg = DistributionPackage(
    package_path=Path("dist/spec_kitty_cli-0.11.2-py3-none-any.whl"),
    version="0.11.2",
    template_manifest=[
        ".kittify/missions/software-dev/templates/spec-template.md",
        ".kittify/missions/software-dev/templates/plan-template.md",
        # ... all templates
    ],
    migration_list=[
        "m_0_10_9_repair_templates",
        "m_0_10_14_update_implement_slash_command",
        "m_0_11_1_improved_workflow_templates",
        "m_0_11_2_improved_workflow_templates"
    ],
    installed_path=Path("/venv/lib/python3.11/site-packages/specify_cli")
)

# Validate templates in wheel
with zipfile.ZipFile(pkg.package_path) as zf:
    for template in pkg.template_manifest:
        assert template in zf.namelist(), f"Missing template: {template}"
```

---

### ConflictScenario

Pre-configured merge conflict for testing status file auto-resolution.

**Purpose**: Create deterministic conflict scenarios for testing merge conflict resolution logic.

**Attributes**:
- `wp_modifications`: dict[str, dict] - File modifications by WP (e.g., {"WP01": {"tasks.md": {...}}})
- `conflict_type`: str - Type of conflict ("code" | "status" | "frontmatter")
- `expected_resolution`: str - Expected auto-resolved content
- `auto_resolvable`: bool - Whether conflict should be auto-resolved

**Scenarios**:
1. **Lane conflicts**: WP01 has "done", WP02 has "for_review" → resolve to "done"
2. **Checkbox conflicts**: WP01 has `[x]`, WP02 has `[ ]` → resolve to `[x]`
3. **History conflicts**: Concatenate chronologically
4. **Code conflicts**: NOT auto-resolvable, require manual resolution

**Example**:
```python
# Lane conflict: more-done wins
lane_conflict = ConflictScenario(
    wp_modifications={
        "WP01": {"tasks/WP01.md": {"lane": "done"}},
        "WP02": {"tasks/WP01.md": {"lane": "for_review"}}
    },
    conflict_type="status",
    expected_resolution="lane: done",
    auto_resolvable=True
)

# Code conflict: not auto-resolvable
code_conflict = ConflictScenario(
    wp_modifications={
        "WP01": {"src/main.py": {"line_10": "return True"}},
        "WP02": {"src/main.py": {"line_10": "return False"}}
    },
    conflict_type="code",
    expected_resolution=None,  # Requires manual resolution
    auto_resolvable=False
)
```

---

### StalenessConfig

Staleness detection test parameters for validating WP staleness calculation.

**Purpose**: Configure staleness detection tests with precise timing and expected outcomes.

**Attributes**:
- `threshold_minutes`: int - Staleness threshold in minutes (default: 10)
- `wp_lane`: str - WP lane status ("doing" | "planned" | "done")
- `last_commit_time`: datetime - Time of last commit in WP worktree
- `expected_stale_status`: bool - Whether WP should be marked stale

**Test Logic**:
```
stale = (wp_lane == "doing") AND (now - last_commit_time > threshold_minutes)
```

**Example**:
```python
# WP should be stale: in "doing" lane, no commits for 15 minutes, threshold 10
stale_config = StalenessConfig(
    threshold_minutes=10,
    wp_lane="doing",
    last_commit_time=datetime.now() - timedelta(minutes=15),
    expected_stale_status=True
)

# WP should NOT be stale: in "done" lane (even though old)
not_stale_config = StalenessConfig(
    threshold_minutes=10,
    wp_lane="done",
    last_commit_time=datetime.now() - timedelta(minutes=30),
    expected_stale_status=False  # Done lane never marked stale
)
```

---

## Fixture Relationships

```
test_environment (base)
    ├── spec_kitty_project (extends test_environment)
    │   └── Feature creation, initialization
    │
    ├── spec_kitty_git_test (points to external test harness)
    │   └── reset_test_harness (cleanup before test)
    │       └── Real orchestration integration tests
    │
    └── no_template_bypass (modifies env_vars)
        └── Distribution tests
```

## State Machine States

Orchestrator WP execution states (from spec-kitty orchestrator):

```
PENDING → IMPLEMENTATION → REVIEW → DONE
                ↓            ↓
                ↓            ↓
                ↓        REWORK → (back to IMPLEMENTATION)
                ↓
            FAILED (terminal)
            BLOCKED (waiting on dependencies)
```

**Idempotent Transitions**:
- `IMPLEMENTATION + start_implementation()` → `IMPLEMENTATION` (no error)
- `REVIEW + start_review()` → `REVIEW` (no error)

**Invalid Transitions**:
- `PENDING → REVIEW` (must go through IMPLEMENTATION)
- `DONE → IMPLEMENTATION` (terminal state)

## Validation Schemas

### orchestration-state.json Schema

```json
{
  "feature": "string",
  "started_at": "ISO datetime",
  "completed_at": "ISO datetime | null",
  "status": "running | completed | failed",
  "wps": {
    "WP01": {
      "state": "PENDING | IMPLEMENTATION | REVIEW | DONE | REWORK | FAILED | BLOCKED",
      "assigned_agent": "string | null",
      "started_at": "ISO datetime | null",
      "completed_at": "ISO datetime | null",
      "retry_count": "integer"
    }
  },
  "dependency_graph": {
    "WP02": ["WP01"]
  }
}
```

### meta.json VCS Lock Schema

```json
{
  "feature_number": "string",
  "slug": "string",
  "vcs": "git | jj",  // Always "git" after jj rollback
  "created_at": "ISO datetime"
}
```

## Implementation Notes

### Fixture Naming Convention

- `test_*`: Regular pytest fixtures
- `mock_*`: Mocked components (subprocess, agents, etc.)
- `*_context`: Context managers for test setup/teardown
- `requires_*`: Fixtures that skip tests when conditions not met

### Marker Naming Convention

- `@pytest.mark.functional` - Fast functional tests
- `@pytest.mark.integration` - Real orchestration tests
- `@pytest.mark.distribution` - PyPI install tests
- `@pytest.mark.requires_agent("name")` - Requires specific agent installed
- `@pytest.mark.orchestrator` - Orchestrator-specific tests
- `@pytest.mark.vcs` - VCS abstraction tests
- `@pytest.mark.adversarial` - Edge case and corruption tests

### Test Data Location

- Fixtures: `tests/{tier}/conftest.py`
- Mock data: `tests/fixtures/` (new directory)
- Test features: Created dynamically in tmp_path
- Integration harness: `/Users/robert/Code/spec-kitty-git-test` (external)
