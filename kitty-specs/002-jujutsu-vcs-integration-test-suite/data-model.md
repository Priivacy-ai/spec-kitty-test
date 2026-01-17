# Data Model: Jujutsu VCS Integration Test Suite

**Feature**: 002-jujutsu-vcs-integration-test-suite
**Research Date**: 2026-01-17

## Overview

This document defines the test entities and their relationships for validating the jujutsu VCS integration in spec-kitty.

## Test Fixtures

### VCS Availability Fixtures

| Fixture | Purpose | Scope |
|---------|---------|-------|
| `jj_available` | Returns True if jj is installed | session |
| `git_available` | Returns True if git is installed | session |
| `requires_jj` | Skip test if jj not available | function |
| `requires_git` | Skip test if git not available | function |
| `requires_both` | Skip if either tool missing | function |

### Repository Fixtures

| Fixture | Purpose | Cleanup |
|---------|---------|---------|
| `git_repo` | Fresh git repository in tmp_path | auto |
| `jj_repo` | Fresh jj repository in tmp_path | auto |
| `colocated_repo` | Repository with both .git/ and .jj/ | auto |
| `spec_kitty_project` | Initialized spec-kitty project | auto |

### Feature Fixtures

| Fixture | Purpose | VCS |
|---------|---------|-----|
| `git_feature` | Feature created with git backend | git |
| `jj_feature` | Feature created with jj backend | jj |
| `mixed_project` | Project with both git and jj features | both |

### Workspace Fixtures

| Fixture | Purpose | Dependencies |
|---------|---------|--------------|
| `git_workspace` | Git worktree for WP | git_feature |
| `jj_workspace` | jj workspace for WP | jj_feature |
| `stale_workspace` | Workspace needing sync | *_feature |
| `conflicted_workspace` | Workspace with conflicts | *_feature |

## Test Markers

| Marker | Meaning | Usage |
|--------|---------|-------|
| `@pytest.mark.jj` | Requires jj installation | jj-specific tests |
| `@pytest.mark.distribution` | No template bypass | PyPI user tests |
| `@pytest.mark.adversarial` | Edge case/corruption | Robustness tests |
| `@pytest.mark.upgrade` | Version migration | Upgrade path tests |
| `@pytest.mark.slow` | Takes > 30 seconds | Performance tests |

## Test Data Models

### VCSBackend (from spec-kitty)

```python
class VCSBackend(Enum):
    GIT = "git"
    JUJUTSU = "jj"
```

### TestScenario

```python
@dataclass
class TestScenario:
    name: str
    backend: VCSBackend | None  # None = both
    requires_jj: bool
    distribution_test: bool
    setup_steps: list[str]
    expected_outcome: str
```

### ConflictScenario

```python
@dataclass
class ConflictScenario:
    name: str
    conflict_type: str  # "content", "modify_delete", "add_add"
    num_sides: int      # 2 for normal, 3+ for multi-sided
    files: list[str]
    expected_markers: list[str]
```

### UpgradeScenario

```python
@dataclass
class UpgradeScenario:
    name: str
    from_state: str     # e.g., "git_only_v0.10"
    to_state: str       # e.g., "jj_available_v0.12"
    existing_features: int
    existing_worktrees: int
    expected_behavior: str
```

## Entity Relationships

```
TestProject
├── has many Features
│   ├── has one VCSBackend (locked)
│   ├── has one meta.json
│   └── has many Workspaces
│       ├── has one VCSBackend (inherited)
│       ├── may have Conflicts
│       └── may be Stale
├── has one config.yaml
│   └── has VCS preference
└── has one .gitignore
    └── should NOT ignore kitty-specs/
```

## Test Categories

### 1. Detection Tests

**Entities**: VCSBackend, DetectionResult

| Test ID | Scenario | Expected |
|---------|----------|----------|
| DET-001 | jj installed, git installed | jj selected |
| DET-002 | jj not installed, git installed | git selected, jj recommended |
| DET-003 | Neither installed | Error with instructions |
| DET-004 | jj installed, --vcs=git | git selected |
| DET-005 | jj broken/crashes | git fallback with warning |
| DET-006 | jj wrong tool (not jujutsu) | Validation fails |

### 2. VCS Lock Tests

**Entities**: Feature, meta.json, VCSBackend

| Test ID | Scenario | Expected |
|---------|----------|----------|
| LOCK-001 | Create feature with jj | meta.json has vcs: jj |
| LOCK-002 | Attempt --vcs=git on jj feature | Error: VCS locked |
| LOCK-003 | Tamper meta.json vcs field | Detection + warning |
| LOCK-004 | Delete meta.json, re-run | Graceful handling |
| LOCK-005 | Two features, different VCS | Each uses own VCS |

### 3. Workspace Tests

**Entities**: Workspace, WorkspaceInfo, Feature

| Test ID | Scenario | Expected |
|---------|----------|----------|
| WS-001 | Create jj workspace | .worktrees/###-WP01/ exists |
| WS-002 | Colocated mode | Both .jj/ and .git/ |
| WS-003 | --base flag | WP02 sees WP01 changes |
| WS-004 | Sparse-checkout | kitty-specs/ excluded |
| WS-005 | Remove workspace | Directory cleaned |

### 4. Sync Tests

**Entities**: Workspace, SyncResult, ConflictInfo

| Test ID | Scenario | Expected |
|---------|----------|----------|
| SYNC-001 | Stale jj workspace | Updates via jj workspace update-stale |
| SYNC-002 | Stale git workspace | Updates via git rebase |
| SYNC-003 | Up to date | "already up to date" |
| SYNC-004 | Sync with conflicts | Conflicts listed |
| SYNC-005 | Dependency chain sync | All downstream updated |

### 5. Conflict Tests

**Entities**: ConflictInfo, SyncResult, Workspace

| Test ID | Scenario | Expected |
|---------|----------|----------|
| CONF-001 | jj sync with conflict | Succeeds, conflict stored |
| CONF-002 | git sync with conflict | May block |
| CONF-003 | Review with conflicts | BLOCKED |
| CONF-004 | Merge with conflicts | BLOCKED |
| CONF-005 | Resolve conflict | jj auto-records |
| CONF-006 | 3-way conflict | All sides visible |

### 6. Distribution Tests

**Entities**: PyPIInstallation, Template, Command

| Test ID | Scenario | Expected |
|---------|----------|----------|
| DIST-001 | Init without TEMPLATE_ROOT | Works correctly |
| DIST-002 | VCS detection from PyPI | Correct detection |
| DIST-003 | Workspace from PyPI | Fully functional |
| DIST-004 | Templates use Python CLI | No bash/PowerShell refs |

### 7. Upgrade Tests

**Entities**: Project, Version, VCSBackend

| Test ID | Scenario | Expected |
|---------|----------|----------|
| UPG-001 | Git-only + jj install | New features use jj |
| UPG-002 | Existing git WPs | Continue working |
| UPG-003 | jj uninstalled | Clear error on jj features |
| UPG-004 | Mixed git/jj project | Coexist without interference |

### 8. Gitignore Tests

**Entities**: .gitignore, kitty-specs/

| Test ID | Scenario | Expected |
|---------|----------|----------|
| GI-001 | Main repo .gitignore | kitty-specs/ NOT ignored |
| GI-002 | git add kitty-specs/ | Files added |
| GI-003 | Upgrade fixes gitignore | kitty-specs/ tracked |

## Test File Organization

```
tests/
├── functional/
│   ├── test_jj_vcs_detection.py       # DET-*
│   ├── test_jj_vcs_lock.py            # LOCK-*
│   ├── test_jj_workspace.py           # WS-*
│   ├── test_jj_sync.py                # SYNC-*
│   ├── test_jj_conflicts.py           # CONF-*
│   └── test_jj_gitignore.py           # GI-*
├── distribution/
│   ├── test_jj_distribution.py        # DIST-*
│   └── test_jj_upgrade_paths.py       # UPG-*
└── conftest.py                        # Shared fixtures
```

## Parametrization Strategy

### Backend Parity Tests

```python
@pytest.mark.parametrize("backend", [
    "git",
    pytest.param("jj", marks=pytest.mark.jj)
])
def test_workspace_creation(backend, spec_kitty_project):
    ...
```

### Conflict Type Tests

```python
@pytest.mark.parametrize("conflict_type", [
    "content",
    "modify_delete",
    "add_add",
    "rename_rename",
])
def test_conflict_detection(conflict_type, conflicted_workspace):
    ...
```

## Evidence Tracking

All test findings should be logged to:
- `research/evidence-log.csv` - Test results and observations
- `research/source-register.csv` - Referenced files and versions
