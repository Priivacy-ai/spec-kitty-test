---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
  - "T007"
title: "Test Infrastructure & Fixtures"
phase: "Phase 0 - Foundation"
lane: "doing"
assignee: ""
agent: "claude-opus"
shell_pid: "43719"
review_status: ""
reviewed_by: ""
dependencies: []
history:
  - timestamp: "2026-01-18T12:27:56Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Test Infrastructure & Fixtures

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if work is returned.]*

---

## Implementation Command

```bash
spec-kitty implement WP01
```

No dependencies - this is the foundation package.

---

## Objectives & Success Criteria

Create the shared test infrastructure for the merge feature test suite:

1. **MergeTestFeature** class - scaffold multi-WP features with configurable states
2. **WPFixture** dataclass - represent a single work package with all test-relevant properties
3. **MergeStateFixture** helper - create/manipulate `.kittify/merge-state.json`
4. **ConflictFixture** helper - create status file and code file conflicts
5. **Cleanup utilities** - ensure test isolation

**Success**: Running `pytest tests/functional/test_merge_fixtures.py -v` passes and all fixtures are functional.

---

## Context & Constraints

### Related Documents
- Spec: `kitty-specs/003-merge-feature-test-suite/spec.md` (FR-001 to FR-004)
- Existing patterns: `tests/conftest.py` (see `spec_kitty_project` fixture)

### Architectural Decisions
- Use pytest fixtures, not unittest classes
- Session-scope where possible for performance
- Use `tmp_path` for test isolation
- Support both functional (with SPEC_KITTY_TEMPLATE_ROOT) and distribution modes

### Existing Patterns to Follow
```python
# From conftest.py - use this pattern for project creation
@pytest.fixture
def spec_kitty_project(tmp_path):
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    subprocess.run(["git", "init"], cwd=project_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=project_dir, ...)
    subprocess.run(["spec-kitty", "init", "--here", "--force", "--ai", "claude"], cwd=project_dir, ...)
    return project_dir
```

---

## Subtasks & Detailed Guidance

### Subtask T001 – Create test_merge_fixtures.py module structure

**Purpose**: Establish the test file with proper imports and docstrings.

**Steps**:
1. Create `tests/functional/test_merge_fixtures.py`
2. Add module docstring explaining this contains fixtures for merge testing
3. Add imports: `pytest`, `subprocess`, `os`, `shutil`, `json`, `dataclasses`, `pathlib.Path`
4. Add `__all__` export list for public fixtures

**Files**: `tests/functional/test_merge_fixtures.py` (new, ~50 lines)

**Parallel?**: Yes - independent of other subtasks

**Template**:
```python
"""
Fixtures and utilities for testing spec-kitty merge features.

These fixtures enable creation of multi-WP features with configurable states
for testing pre-flight validation, conflict forecasting, status resolution,
merge ordering, and resume capabilities.
"""
import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pytest

__all__ = [
    "MergeTestFeature",
    "WPFixture",
    "MergeStateFixture",
    "ConflictFixture",
    "create_test_feature",
]
```

---

### Subtask T002 – Create MergeTestFeature fixture class

**Purpose**: Main class for creating and managing multi-WP test features.

**Steps**:
1. Create `MergeTestFeature` class with these attributes:
   - `project_dir: Path` - root of the test project
   - `feature_slug: str` - e.g., "001-test-feature"
   - `wp_count: int` - number of work packages
   - `worktrees: dict[str, Path]` - WP ID → worktree path
   - `branches: list[str]` - branch names created
2. Implement `__init__` that takes `project_dir` and `feature_slug`
3. Implement `create_wp(wp_id: str, lane: str, dependencies: list[str])` method
4. Implement `get_worktree_path(wp_id: str) -> Path` method
5. Implement `cleanup()` method for test teardown

**Files**: `tests/functional/test_merge_fixtures.py` (~100 lines addition)

**Parallel?**: No - T003 depends on this

**Code Structure**:
```python
class MergeTestFeature:
    """Manages a multi-WP feature for merge testing."""

    def __init__(self, project_dir: Path, feature_slug: str):
        self.project_dir = project_dir
        self.feature_slug = feature_slug
        self.worktrees: dict[str, Path] = {}
        self.branches: list[str] = []
        self._feature_dir = project_dir / "kitty-specs" / feature_slug

    def create_wp(
        self,
        wp_id: str,
        lane: str = "done",
        dependencies: list[str] | None = None,
        dirty: bool = False,
    ) -> Path:
        """Create a work package with worktree and optional dirty state."""
        # 1. Create WP prompt file in feature_dir/tasks/
        # 2. Run spec-kitty implement {wp_id} to create worktree
        # 3. If dirty, add uncommitted changes to worktree
        # 4. Track in self.worktrees and self.branches
        ...

    def get_worktree_path(self, wp_id: str) -> Path:
        """Get the worktree path for a WP."""
        return self.worktrees.get(wp_id)

    def cleanup(self):
        """Remove all worktrees and branches."""
        for wp_id, worktree_path in self.worktrees.items():
            if worktree_path.exists():
                subprocess.run(
                    ["git", "worktree", "remove", "--force", str(worktree_path)],
                    cwd=self.project_dir,
                    capture_output=True
                )
        for branch in self.branches:
            subprocess.run(
                ["git", "branch", "-D", branch],
                cwd=self.project_dir,
                capture_output=True
            )
```

---

### Subtask T003 – Create WPFixture dataclass

**Purpose**: Represent a single work package's test configuration.

**Steps**:
1. Create `@dataclass` with fields:
   - `wp_id: str` - e.g., "WP01"
   - `lane: str` - "planned", "doing", "for_review", "done"
   - `dependencies: list[str]` - WP IDs this depends on
   - `dirty: bool` - whether worktree has uncommitted changes
   - `branch_name: str` - computed git branch name
   - `worktree_path: Path | None` - path to worktree if created
2. Add `@property` for `frontmatter_yaml()` that returns valid YAML string

**Files**: `tests/functional/test_merge_fixtures.py` (~40 lines addition)

**Parallel?**: No - needed by T006

**Code**:
```python
@dataclass
class WPFixture:
    """Configuration for a single work package in tests."""
    wp_id: str
    lane: str = "done"
    dependencies: list[str] = field(default_factory=list)
    dirty: bool = False
    branch_name: str = ""
    worktree_path: Path | None = None

    def __post_init__(self):
        if not self.branch_name:
            # e.g., "001-test-feature-WP01"
            self.branch_name = f"{{feature_slug}}-{self.wp_id}"

    @property
    def frontmatter_yaml(self) -> str:
        """Generate valid YAML frontmatter for this WP."""
        deps = json.dumps(self.dependencies)
        return f'''---
work_package_id: "{self.wp_id}"
title: "Test Work Package {self.wp_id}"
lane: "{self.lane}"
dependencies: {deps}
subtasks: []
history:
  - timestamp: "2026-01-01T00:00:00Z"
    lane: "{self.lane}"
    agent: "test"
    action: "Created for testing"
---

# Test Work Package {self.wp_id}

Test content for merge testing.
'''
```

---

### Subtask T004 – Create MergeStateFixture helper

**Purpose**: Create and manipulate `.kittify/merge-state.json` for resume testing.

**Steps**:
1. Create `MergeStateFixture` class
2. Implement `create_state()` that writes merge state JSON
3. Implement `corrupt_state()` that writes invalid JSON
4. Implement `clear_state()` that removes the file

**Files**: `tests/functional/test_merge_fixtures.py` (~60 lines addition)

**Parallel?**: Yes - independent module

**Code**:
```python
class MergeStateFixture:
    """Helper for creating and manipulating merge state files."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.state_file = project_dir / ".kittify" / "merge-state.json"

    def create_state(
        self,
        feature_slug: str,
        wp_order: list[str],
        completed_wps: list[str],
        current_wp: str | None = None,
        has_pending_conflicts: bool = False,
        target_branch: str = "main",
    ) -> Path:
        """Create a merge state file."""
        state = {
            "feature_slug": feature_slug,
            "target_branch": target_branch,
            "wp_order": wp_order,
            "completed_wps": completed_wps,
            "current_wp": current_wp,
            "has_pending_conflicts": has_pending_conflicts,
            "started_at": "2026-01-01T00:00:00Z",
            "last_updated": "2026-01-01T00:00:00Z",
        }
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(state, indent=2))
        return self.state_file

    def corrupt_state(self) -> Path:
        """Write corrupted JSON to test error handling."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text("{invalid json content")
        return self.state_file

    def clear_state(self):
        """Remove merge state file if it exists."""
        if self.state_file.exists():
            self.state_file.unlink()
```

---

### Subtask T005 – Create ConflictFixture helper

**Purpose**: Create status file and code file conflicts for testing resolution.

**Steps**:
1. Create `ConflictFixture` class
2. Implement `create_lane_conflict()` - different lane values in WPs
3. Implement `create_checkbox_conflict()` - different checkbox states
4. Implement `create_history_conflict()` - different history entries
5. Implement `create_code_conflict()` - actual code file conflicts

**Files**: `tests/functional/test_merge_fixtures.py` (~80 lines addition)

**Parallel?**: Yes - independent module

**Code**:
```python
class ConflictFixture:
    """Helper for creating merge conflicts in test features."""

    def __init__(self, feature: MergeTestFeature):
        self.feature = feature

    def create_lane_conflict(
        self,
        wp1_id: str,
        wp2_id: str,
        task_file: str,
        wp1_lane: str = "done",
        wp2_lane: str = "for_review",
    ):
        """Create conflicting lane values in a task file."""
        # Modify the same task file in both worktrees with different lanes
        wp1_path = self.feature.get_worktree_path(wp1_id)
        wp2_path = self.feature.get_worktree_path(wp2_id)

        # Write lane: done in WP1
        task_path_1 = wp1_path / "kitty-specs" / self.feature.feature_slug / "tasks" / task_file
        self._update_lane_in_file(task_path_1, wp1_lane)
        self._commit_in_worktree(wp1_path, f"Update lane to {wp1_lane}")

        # Write lane: for_review in WP2
        task_path_2 = wp2_path / "kitty-specs" / self.feature.feature_slug / "tasks" / task_file
        self._update_lane_in_file(task_path_2, wp2_lane)
        self._commit_in_worktree(wp2_path, f"Update lane to {wp2_lane}")

    def create_code_conflict(
        self,
        wp1_id: str,
        wp2_id: str,
        file_path: str,
        wp1_content: str,
        wp2_content: str,
    ):
        """Create a code file conflict (non-status file)."""
        wp1_path = self.feature.get_worktree_path(wp1_id)
        wp2_path = self.feature.get_worktree_path(wp2_id)

        # Write different content to same file in both worktrees
        (wp1_path / file_path).parent.mkdir(parents=True, exist_ok=True)
        (wp1_path / file_path).write_text(wp1_content)
        self._commit_in_worktree(wp1_path, "Add code file")

        (wp2_path / file_path).parent.mkdir(parents=True, exist_ok=True)
        (wp2_path / file_path).write_text(wp2_content)
        self._commit_in_worktree(wp2_path, "Add conflicting code file")

    def _update_lane_in_file(self, file_path: Path, lane: str):
        """Update lane value in a task file's frontmatter."""
        # Read, modify lane, write back
        ...

    def _commit_in_worktree(self, worktree_path: Path, message: str):
        """Create a commit in the worktree."""
        subprocess.run(["git", "add", "."], cwd=worktree_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=worktree_path,
            check=True,
            capture_output=True
        )
```

---

### Subtask T006 – Implement create_test_feature() fixture factory

**Purpose**: Main pytest fixture for creating test features.

**Steps**:
1. Create `@pytest.fixture` named `create_test_feature`
2. Accept `tmp_path` as dependency
3. Return a factory function that creates `MergeTestFeature` instances
4. Handle cleanup in fixture teardown

**Files**: `tests/functional/test_merge_fixtures.py` (~50 lines addition)

**Parallel?**: No - needs T002, T003

**Code**:
```python
@pytest.fixture
def create_test_feature(tmp_path, spec_kitty_repo_root):
    """Factory fixture for creating test features with multiple WPs.

    Usage:
        def test_something(create_test_feature):
            feature = create_test_feature(
                wp_configs=[
                    WPFixture("WP01", lane="done"),
                    WPFixture("WP02", lane="done", dependencies=["WP01"]),
                    WPFixture("WP03", lane="done", dirty=True),
                ]
            )
            # feature.project_dir, feature.worktrees, etc.
    """
    created_features: list[MergeTestFeature] = []

    def _create(
        wp_configs: list[WPFixture],
        feature_slug: str = "001-test-feature",
    ) -> MergeTestFeature:
        # 1. Create project directory
        project_dir = tmp_path / f"project-{len(created_features)}"
        project_dir.mkdir()

        # 2. Initialize git repo
        subprocess.run(["git", "init"], cwd=project_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=project_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=project_dir, check=True, capture_output=True)

        # 3. Initialize spec-kitty
        env = os.environ.copy()
        env["SPEC_KITTY_TEMPLATE_ROOT"] = str(spec_kitty_repo_root)
        subprocess.run(
            ["spec-kitty", "init", "--here", "--force", "--ai", "claude"],
            cwd=project_dir,
            check=True,
            capture_output=True,
            env=env,
        )

        # 4. Create feature
        feature = MergeTestFeature(project_dir, feature_slug)

        # 5. Create each WP
        for wp_config in wp_configs:
            feature.create_wp(
                wp_id=wp_config.wp_id,
                lane=wp_config.lane,
                dependencies=wp_config.dependencies,
                dirty=wp_config.dirty,
            )

        created_features.append(feature)
        return feature

    yield _create

    # Cleanup all created features
    for feature in created_features:
        feature.cleanup()
```

---

### Subtask T007 – Add cleanup utilities

**Purpose**: Ensure test isolation by providing cleanup helpers.

**Steps**:
1. Add `cleanup_worktrees(project_dir: Path)` function
2. Add `cleanup_branches(project_dir: Path, pattern: str)` function
3. Add `cleanup_merge_state(project_dir: Path)` function
4. Ensure these are called in fixture teardown

**Files**: `tests/functional/test_merge_fixtures.py` (~40 lines addition)

**Parallel?**: No - final assembly

**Code**:
```python
def cleanup_worktrees(project_dir: Path):
    """Remove all worktrees from a project."""
    worktrees_dir = project_dir / ".worktrees"
    if worktrees_dir.exists():
        # List and remove each worktree
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=project_dir,
            capture_output=True,
            text=True,
        )
        for line in result.stdout.split("\n"):
            if line.startswith("worktree ") and ".worktrees" in line:
                worktree_path = line.split(" ", 1)[1]
                subprocess.run(
                    ["git", "worktree", "remove", "--force", worktree_path],
                    cwd=project_dir,
                    capture_output=True,
                )


def cleanup_branches(project_dir: Path, pattern: str = "*-WP*"):
    """Remove branches matching pattern."""
    result = subprocess.run(
        ["git", "branch", "--list", pattern],
        cwd=project_dir,
        capture_output=True,
        text=True,
    )
    for branch in result.stdout.strip().split("\n"):
        branch = branch.strip().lstrip("* ")
        if branch:
            subprocess.run(
                ["git", "branch", "-D", branch],
                cwd=project_dir,
                capture_output=True,
            )


def cleanup_merge_state(project_dir: Path):
    """Remove merge state file."""
    state_file = project_dir / ".kittify" / "merge-state.json"
    if state_file.exists():
        state_file.unlink()
```

---

## Test Strategy

This WP creates fixtures, so testing is via usage:

```python
# Add these tests at the bottom of test_merge_fixtures.py

class TestMergeFixtures:
    """Verify fixtures work correctly."""

    def test_create_test_feature_basic(self, create_test_feature):
        """Can create a simple 2-WP feature."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
                WPFixture("WP02", lane="done"),
            ]
        )
        assert feature.project_dir.exists()
        assert len(feature.worktrees) == 2
        assert feature.get_worktree_path("WP01").exists()

    def test_create_test_feature_with_dependencies(self, create_test_feature):
        """Can create WPs with dependency declarations."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
                WPFixture("WP02", lane="done", dependencies=["WP01"]),
            ]
        )
        # Verify frontmatter contains dependency
        wp02_prompt = feature.get_worktree_path("WP02").parent.parent / "kitty-specs" / feature.feature_slug / "tasks" / "WP02-test.md"
        # (actual path depends on implementation)

    def test_create_test_feature_with_dirty_worktree(self, create_test_feature):
        """Can create a WP with uncommitted changes."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done", dirty=True),
            ]
        )
        # Verify worktree has uncommitted changes
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=feature.get_worktree_path("WP01"),
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip()  # Has uncommitted changes

    def test_merge_state_fixture(self, tmp_path):
        """MergeStateFixture creates valid state files."""
        fixture = MergeStateFixture(tmp_path)
        state_file = fixture.create_state(
            feature_slug="001-test",
            wp_order=["WP01", "WP02"],
            completed_wps=["WP01"],
            current_wp="WP02",
        )
        assert state_file.exists()
        state = json.loads(state_file.read_text())
        assert state["completed_wps"] == ["WP01"]
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Fixture complexity grows unwieldy | Start simple, add features incrementally |
| Test isolation failures | Use unique tmp directories; clean up in fixture teardown |
| spec-kitty CLI changes break fixtures | Use version-checking fixtures from conftest.py |
| Performance with many WPs | Session-scope where safe; parallelize independent ops |

---

## Definition of Done Checklist

- [ ] `tests/functional/test_merge_fixtures.py` exists with all classes/fixtures
- [ ] `MergeTestFeature` can create multi-WP features
- [ ] `WPFixture` dataclass works with all lane states
- [ ] `MergeStateFixture` creates valid and corrupted state files
- [ ] `ConflictFixture` can create lane, checkbox, and code conflicts
- [ ] `create_test_feature` fixture factory works in tests
- [ ] All fixture self-tests pass: `pytest tests/functional/test_merge_fixtures.py -v`
- [ ] Cleanup works - no leftover worktrees/branches after tests

---

## Review Guidance

- Verify fixtures follow existing patterns in `conftest.py`
- Check that all helpers are importable and documented
- Ensure cleanup is thorough - no resource leaks
- Verify fixtures work with both functional and distribution modes

---

## Activity Log

- 2026-01-18T12:27:56Z – system – lane=planned – Prompt created.
- 2026-01-18T13:12:51Z – claude-opus – shell_pid=41754 – lane=doing – Started implementation via workflow command
- 2026-01-18T13:16:56Z – claude-opus – shell_pid=41754 – lane=for_review – Ready for review: Created MergeTestFeature, WPFixture, MergeStateFixture, ConflictFixture, create_test_feature factory, and cleanup utilities with 12 passing self-tests
- 2026-01-18T13:16:56Z – claude-opus – shell_pid=43719 – lane=doing – Started review via workflow command
