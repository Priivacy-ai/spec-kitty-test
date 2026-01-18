"""
Fixtures and utilities for testing spec-kitty merge features.

These fixtures enable creation of multi-WP features with configurable states
for testing pre-flight validation, conflict forecasting, status resolution,
merge ordering, and resume capabilities.

This module provides:
- MergeTestFeature: Manages a multi-WP feature for merge testing
- WPFixture: Configuration dataclass for a single work package
- MergeStateFixture: Helper for creating/manipulating merge state files
- ConflictFixture: Helper for creating merge conflicts
- create_test_feature: Pytest fixture factory for creating test features
- Cleanup utilities: Ensure test isolation
"""
import json
import os
import re
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
    "cleanup_worktrees",
    "cleanup_branches",
    "cleanup_merge_state",
]


# =============================================================================
# WPFixture Dataclass (T003)
# =============================================================================

@dataclass
class WPFixture:
    """Configuration for a single work package in tests.

    Attributes:
        wp_id: Work package identifier (e.g., "WP01")
        lane: Current lane status ("planned", "doing", "for_review", "done")
        dependencies: List of WP IDs this work package depends on
        dirty: Whether the worktree should have uncommitted changes
        branch_name: Git branch name (computed if not provided)
        worktree_path: Path to the worktree (set after creation)
    """
    wp_id: str
    lane: str = "done"
    dependencies: list[str] = field(default_factory=list)
    dirty: bool = False
    branch_name: str = ""
    worktree_path: Optional[Path] = None
    _feature_slug: str = field(default="", repr=False)

    def __post_init__(self):
        if not self.branch_name and self._feature_slug:
            self.branch_name = f"{self._feature_slug}-{self.wp_id}"

    def get_frontmatter_yaml(self, feature_slug: str) -> str:
        """Generate valid YAML frontmatter for this WP.

        Args:
            feature_slug: The feature slug for path construction

        Returns:
            Complete markdown content with frontmatter for the WP prompt file
        """
        deps = json.dumps(self.dependencies)
        slug = self.wp_id.lower().replace("wp", "wp").replace("WP", "")
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

## Objectives

This is a test work package for merge feature testing.

## Implementation

Placeholder content for testing purposes.
'''


# =============================================================================
# MergeTestFeature Class (T002)
# =============================================================================

class MergeTestFeature:
    """Manages a multi-WP feature for merge testing.

    This class handles the creation of a complete spec-kitty feature with
    multiple work packages, including worktrees and branches.

    Attributes:
        project_dir: Root directory of the test project
        feature_slug: The feature identifier (e.g., "001-test-feature")
        worktrees: Dictionary mapping WP IDs to worktree paths
        branches: List of branch names created
    """

    def __init__(self, project_dir: Path, feature_slug: str, env: Optional[dict] = None):
        """Initialize a test feature.

        Args:
            project_dir: Root directory of the test project
            feature_slug: The feature identifier
            env: Optional environment variables for subprocess calls
        """
        self.project_dir = project_dir
        self.feature_slug = feature_slug
        self.worktrees: dict[str, Path] = {}
        self.branches: list[str] = []
        self._feature_dir = project_dir / "kitty-specs" / feature_slug
        self._env = env or os.environ.copy()
        self._wp_counter = 0

    def _ensure_feature_structure(self):
        """Ensure the feature directory structure exists."""
        tasks_dir = self._feature_dir / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)

        # Create minimal spec.md if it doesn't exist
        spec_file = self._feature_dir / "spec.md"
        if not spec_file.exists():
            spec_file.write_text(f"""# Test Feature: {self.feature_slug}

**Created**: 2026-01-01
**Status**: Draft

## Overview

Test feature for merge testing.
""")

        # Create minimal tasks.md if it doesn't exist
        tasks_md = self._feature_dir / "tasks.md"
        if not tasks_md.exists():
            tasks_md.write_text(f"""# Work Packages: {self.feature_slug}

Test feature work packages.
""")

        # Commit the feature structure
        subprocess.run(
            ["git", "add", "."],
            cwd=self.project_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", f"Add feature {self.feature_slug} structure", "--allow-empty"],
            cwd=self.project_dir,
            capture_output=True,
        )

    def create_wp(
        self,
        wp_id: str,
        lane: str = "done",
        dependencies: Optional[list[str]] = None,
        dirty: bool = False,
    ) -> Path:
        """Create a work package with worktree and optional dirty state.

        Args:
            wp_id: Work package identifier (e.g., "WP01")
            lane: Lane status for the WP
            dependencies: List of WP IDs this depends on
            dirty: Whether to add uncommitted changes

        Returns:
            Path to the created worktree
        """
        dependencies = dependencies or []
        self._wp_counter += 1

        # Ensure feature structure exists
        self._ensure_feature_structure()

        # Create WP prompt file
        wp_fixture = WPFixture(
            wp_id=wp_id,
            lane=lane,
            dependencies=dependencies,
            dirty=dirty,
        )
        wp_slug = f"{wp_id.lower()}-test"
        prompt_file = self._feature_dir / "tasks" / f"{wp_id}-test.md"
        prompt_file.write_text(wp_fixture.get_frontmatter_yaml(self.feature_slug))

        # Commit the WP prompt file
        subprocess.run(
            ["git", "add", str(prompt_file)],
            cwd=self.project_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", f"Add {wp_id} prompt file"],
            cwd=self.project_dir,
            check=True,
            capture_output=True,
        )

        # Create branch for the WP
        branch_name = f"{self.feature_slug}-{wp_id}"
        subprocess.run(
            ["git", "branch", branch_name],
            cwd=self.project_dir,
            check=True,
            capture_output=True,
        )
        self.branches.append(branch_name)

        # Create worktree
        worktrees_dir = self.project_dir / ".worktrees"
        worktrees_dir.mkdir(exist_ok=True)
        worktree_path = worktrees_dir / f"{self.feature_slug}-{wp_id}"

        subprocess.run(
            ["git", "worktree", "add", str(worktree_path), branch_name],
            cwd=self.project_dir,
            check=True,
            capture_output=True,
        )

        self.worktrees[wp_id] = worktree_path
        wp_fixture.worktree_path = worktree_path
        wp_fixture.branch_name = branch_name

        # If dirty, add uncommitted changes
        if dirty:
            dirty_file = worktree_path / "dirty_file.txt"
            dirty_file.write_text(f"Uncommitted changes in {wp_id}")

        return worktree_path

    def get_worktree_path(self, wp_id: str) -> Optional[Path]:
        """Get the worktree path for a WP.

        Args:
            wp_id: Work package identifier

        Returns:
            Path to the worktree, or None if not found
        """
        return self.worktrees.get(wp_id)

    def cleanup(self):
        """Remove all worktrees and branches created by this feature."""
        # Remove worktrees first
        for wp_id, worktree_path in list(self.worktrees.items()):
            if worktree_path and worktree_path.exists():
                subprocess.run(
                    ["git", "worktree", "remove", "--force", str(worktree_path)],
                    cwd=self.project_dir,
                    capture_output=True,
                )
        self.worktrees.clear()

        # Prune worktrees
        subprocess.run(
            ["git", "worktree", "prune"],
            cwd=self.project_dir,
            capture_output=True,
        )

        # Remove branches
        for branch in self.branches:
            subprocess.run(
                ["git", "branch", "-D", branch],
                cwd=self.project_dir,
                capture_output=True,
            )
        self.branches.clear()


# =============================================================================
# MergeStateFixture Class (T004)
# =============================================================================

class MergeStateFixture:
    """Helper for creating and manipulating merge state files.

    This class provides methods to create, corrupt, and clear merge state
    files for testing the resume/abort functionality.
    """

    def __init__(self, project_dir: Path):
        """Initialize the fixture.

        Args:
            project_dir: Root directory of the test project
        """
        self.project_dir = project_dir
        self.state_file = project_dir / ".kittify" / "merge-state.json"

    def create_state(
        self,
        feature_slug: str,
        wp_order: list[str],
        completed_wps: list[str],
        current_wp: Optional[str] = None,
        has_pending_conflicts: bool = False,
        target_branch: str = "main",
        strategy: str = "merge",
    ) -> Path:
        """Create a merge state file.

        Args:
            feature_slug: The feature being merged
            wp_order: Ordered list of WP IDs to merge
            completed_wps: List of already-merged WP IDs
            current_wp: Currently in-progress WP (or None)
            has_pending_conflicts: Whether there are unresolved conflicts
            target_branch: Target branch for merge
            strategy: Merge strategy ("merge" or "rebase")

        Returns:
            Path to the created state file
        """
        state = {
            "feature_slug": feature_slug,
            "target_branch": target_branch,
            "strategy": strategy,
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
        """Write corrupted JSON to test error handling.

        Returns:
            Path to the corrupted state file
        """
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text("{invalid json content")
        return self.state_file

    def clear_state(self):
        """Remove merge state file if it exists."""
        if self.state_file.exists():
            self.state_file.unlink()

    def get_state(self) -> Optional[dict]:
        """Read and return the current state.

        Returns:
            State dictionary, or None if file doesn't exist or is invalid
        """
        if not self.state_file.exists():
            return None
        try:
            return json.loads(self.state_file.read_text())
        except json.JSONDecodeError:
            return None


# =============================================================================
# ConflictFixture Class (T005)
# =============================================================================

class ConflictFixture:
    """Helper for creating merge conflicts in test features.

    This class provides methods to create various types of conflicts:
    - Lane conflicts (status file auto-resolution)
    - Checkbox conflicts (tasks.md)
    - History array conflicts
    - Code file conflicts (manual resolution required)
    """

    def __init__(self, feature: MergeTestFeature):
        """Initialize the fixture.

        Args:
            feature: The MergeTestFeature instance to create conflicts in
        """
        self.feature = feature

    def create_lane_conflict(
        self,
        wp1_id: str,
        wp2_id: str,
        task_file: str = "shared-task.md",
        wp1_lane: str = "done",
        wp2_lane: str = "for_review",
    ):
        """Create conflicting lane values in a task file.

        Args:
            wp1_id: First WP ID
            wp2_id: Second WP ID
            task_file: Name of the task file to create
            wp1_lane: Lane value for WP1
            wp2_lane: Lane value for WP2
        """
        wp1_path = self.feature.get_worktree_path(wp1_id)
        wp2_path = self.feature.get_worktree_path(wp2_id)

        if not wp1_path or not wp2_path:
            raise ValueError(f"Worktrees not found for {wp1_id} or {wp2_id}")

        task_content_template = '''---
work_package_id: "shared"
title: "Shared Task"
lane: "{lane}"
history:
  - timestamp: "2026-01-01T00:00:00Z"
    lane: "{lane}"
    agent: "{wp_id}"
    action: "Set lane"
---

# Shared Task

Content modified by {wp_id}.
'''

        # Write WP1 version
        task_path_1 = wp1_path / "kitty-specs" / self.feature.feature_slug / "tasks" / task_file
        task_path_1.parent.mkdir(parents=True, exist_ok=True)
        task_path_1.write_text(task_content_template.format(lane=wp1_lane, wp_id=wp1_id))
        self._commit_in_worktree(wp1_path, f"Set lane to {wp1_lane}")

        # Write WP2 version
        task_path_2 = wp2_path / "kitty-specs" / self.feature.feature_slug / "tasks" / task_file
        task_path_2.parent.mkdir(parents=True, exist_ok=True)
        task_path_2.write_text(task_content_template.format(lane=wp2_lane, wp_id=wp2_id))
        self._commit_in_worktree(wp2_path, f"Set lane to {wp2_lane}")

    def create_checkbox_conflict(
        self,
        wp1_id: str,
        wp2_id: str,
        task_name: str = "T001",
        wp1_checked: bool = True,
        wp2_checked: bool = False,
    ):
        """Create conflicting checkbox states in tasks.md.

        Args:
            wp1_id: First WP ID
            wp2_id: Second WP ID
            task_name: Task identifier for the checkbox
            wp1_checked: Whether checkbox is checked in WP1
            wp2_checked: Whether checkbox is checked in WP2
        """
        wp1_path = self.feature.get_worktree_path(wp1_id)
        wp2_path = self.feature.get_worktree_path(wp2_id)

        if not wp1_path or not wp2_path:
            raise ValueError(f"Worktrees not found for {wp1_id} or {wp2_id}")

        wp1_check = "[x]" if wp1_checked else "[ ]"
        wp2_check = "[x]" if wp2_checked else "[ ]"

        tasks_md = f"kitty-specs/{self.feature.feature_slug}/tasks.md"

        # Write WP1 version
        tasks_path_1 = wp1_path / tasks_md
        tasks_path_1.parent.mkdir(parents=True, exist_ok=True)
        tasks_path_1.write_text(f"""# Work Packages

## Subtasks

- {wp1_check} {task_name} First task
- [ ] T002 Second task
""")
        self._commit_in_worktree(wp1_path, f"Update {task_name} checkbox")

        # Write WP2 version
        tasks_path_2 = wp2_path / tasks_md
        tasks_path_2.parent.mkdir(parents=True, exist_ok=True)
        tasks_path_2.write_text(f"""# Work Packages

## Subtasks

- {wp2_check} {task_name} First task
- [x] T002 Second task
""")
        self._commit_in_worktree(wp2_path, f"Update {task_name} checkbox")

    def create_history_conflict(
        self,
        wp1_id: str,
        wp2_id: str,
        task_file: str = "history-task.md",
    ):
        """Create conflicting history arrays in task frontmatter.

        Args:
            wp1_id: First WP ID
            wp2_id: Second WP ID
            task_file: Name of the task file to create
        """
        wp1_path = self.feature.get_worktree_path(wp1_id)
        wp2_path = self.feature.get_worktree_path(wp2_id)

        if not wp1_path or not wp2_path:
            raise ValueError(f"Worktrees not found for {wp1_id} or {wp2_id}")

        wp1_content = '''---
work_package_id: "history-test"
lane: "done"
history:
  - timestamp: "2026-01-01T01:00:00Z"
    agent: "agent1"
    action: "First action from WP1"
---

# History Test Task

Content for history conflict testing.
'''

        wp2_content = '''---
work_package_id: "history-test"
lane: "done"
history:
  - timestamp: "2026-01-01T02:00:00Z"
    agent: "agent2"
    action: "Second action from WP2"
---

# History Test Task

Content for history conflict testing.
'''

        # Write WP1 version
        task_path_1 = wp1_path / "kitty-specs" / self.feature.feature_slug / "tasks" / task_file
        task_path_1.parent.mkdir(parents=True, exist_ok=True)
        task_path_1.write_text(wp1_content)
        self._commit_in_worktree(wp1_path, "Add history entry 1")

        # Write WP2 version
        task_path_2 = wp2_path / "kitty-specs" / self.feature.feature_slug / "tasks" / task_file
        task_path_2.parent.mkdir(parents=True, exist_ok=True)
        task_path_2.write_text(wp2_content)
        self._commit_in_worktree(wp2_path, "Add history entry 2")

    def create_code_conflict(
        self,
        wp1_id: str,
        wp2_id: str,
        file_path: str,
        wp1_content: str,
        wp2_content: str,
    ):
        """Create a code file conflict (non-status file).

        Args:
            wp1_id: First WP ID
            wp2_id: Second WP ID
            file_path: Relative path to the code file
            wp1_content: Content for WP1's version
            wp2_content: Content for WP2's version
        """
        wp1_path = self.feature.get_worktree_path(wp1_id)
        wp2_path = self.feature.get_worktree_path(wp2_id)

        if not wp1_path or not wp2_path:
            raise ValueError(f"Worktrees not found for {wp1_id} or {wp2_id}")

        # Write WP1 version
        code_path_1 = wp1_path / file_path
        code_path_1.parent.mkdir(parents=True, exist_ok=True)
        code_path_1.write_text(wp1_content)
        self._commit_in_worktree(wp1_path, f"Add {file_path} from {wp1_id}")

        # Write WP2 version
        code_path_2 = wp2_path / file_path
        code_path_2.parent.mkdir(parents=True, exist_ok=True)
        code_path_2.write_text(wp2_content)
        self._commit_in_worktree(wp2_path, f"Add {file_path} from {wp2_id}")

    def _commit_in_worktree(self, worktree_path: Path, message: str):
        """Create a commit in the worktree.

        Args:
            worktree_path: Path to the worktree
            message: Commit message
        """
        subprocess.run(
            ["git", "add", "."],
            cwd=worktree_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=worktree_path,
            check=True,
            capture_output=True,
        )


# =============================================================================
# Cleanup Utilities (T007)
# =============================================================================

def cleanup_worktrees(project_dir: Path):
    """Remove all worktrees from a project.

    Args:
        project_dir: Root directory of the project
    """
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

        # Prune any stale worktree entries
        subprocess.run(
            ["git", "worktree", "prune"],
            cwd=project_dir,
            capture_output=True,
        )


def cleanup_branches(project_dir: Path, pattern: str = "*-WP*"):
    """Remove branches matching pattern.

    Args:
        project_dir: Root directory of the project
        pattern: Glob pattern for branch names to delete
    """
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
    """Remove merge state file.

    Args:
        project_dir: Root directory of the project
    """
    state_file = project_dir / ".kittify" / "merge-state.json"
    if state_file.exists():
        state_file.unlink()


# =============================================================================
# Pytest Fixture Factory (T006)
# =============================================================================

@pytest.fixture
def create_test_feature(tmp_path, spec_kitty_repo_root):
    """Factory fixture for creating test features with multiple WPs.

    This fixture provides a factory function that creates fully-initialized
    spec-kitty features with configurable work packages.

    Usage:
        def test_something(create_test_feature):
            feature = create_test_feature(
                wp_configs=[
                    WPFixture("WP01", lane="done"),
                    WPFixture("WP02", lane="done", dependencies=["WP01"]),
                    WPFixture("WP03", lane="done", dirty=True),
                ]
            )
            # Access: feature.project_dir, feature.worktrees, etc.

    Args:
        tmp_path: Pytest built-in fixture for temporary directories
        spec_kitty_repo_root: Fixture providing path to spec-kitty repo

    Yields:
        Factory function that creates MergeTestFeature instances
    """
    created_features: list[MergeTestFeature] = []

    def _create(
        wp_configs: list[WPFixture],
        feature_slug: str = "001-test-feature",
    ) -> MergeTestFeature:
        """Create a test feature with specified work packages.

        Args:
            wp_configs: List of WPFixture configurations for each WP
            feature_slug: Feature identifier (default: "001-test-feature")

        Returns:
            Configured MergeTestFeature instance
        """
        # 1. Create unique project directory
        project_dir = tmp_path / f"project-{len(created_features)}"
        project_dir.mkdir()

        # 2. Initialize git repo
        subprocess.run(
            ["git", "init"],
            cwd=project_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=project_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=project_dir,
            check=True,
            capture_output=True,
        )

        # Create initial commit
        (project_dir / "README.md").write_text("# Test Project\n")
        subprocess.run(
            ["git", "add", "."],
            cwd=project_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=project_dir,
            check=True,
            capture_output=True,
        )

        # 3. Initialize spec-kitty
        env = os.environ.copy()
        env["SPEC_KITTY_TEMPLATE_ROOT"] = str(spec_kitty_repo_root)

        result = subprocess.run(
            ["spec-kitty", "init", "--here", "--force", "--ai", "claude"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            env=env,
        )
        # Note: init may fail if spec-kitty isn't installed, but we continue

        # Commit any changes from init
        subprocess.run(
            ["git", "add", "."],
            cwd=project_dir,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Initialize spec-kitty", "--allow-empty"],
            cwd=project_dir,
            capture_output=True,
        )

        # 4. Create feature
        feature = MergeTestFeature(project_dir, feature_slug, env)

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
        try:
            feature.cleanup()
        except Exception:
            pass  # Best effort cleanup


# =============================================================================
# Self-Tests for Fixtures
# =============================================================================

class TestMergeFixtures:
    """Verify fixtures work correctly."""

    def test_wp_fixture_frontmatter(self):
        """WPFixture generates valid YAML frontmatter."""
        wp = WPFixture("WP01", lane="done", dependencies=["WP00"])
        frontmatter = wp.get_frontmatter_yaml("001-test")

        assert 'work_package_id: "WP01"' in frontmatter
        assert 'lane: "done"' in frontmatter
        assert 'dependencies: ["WP00"]' in frontmatter

    def test_wp_fixture_defaults(self):
        """WPFixture has sensible defaults."""
        wp = WPFixture("WP01")

        assert wp.lane == "done"
        assert wp.dependencies == []
        assert wp.dirty is False

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
        assert state["feature_slug"] == "001-test"
        assert state["completed_wps"] == ["WP01"]
        assert state["current_wp"] == "WP02"

    def test_merge_state_fixture_corrupt(self, tmp_path):
        """MergeStateFixture can create corrupted state."""
        fixture = MergeStateFixture(tmp_path)
        state_file = fixture.corrupt_state()

        assert state_file.exists()
        content = state_file.read_text()
        assert "invalid" in content.lower() or not content.startswith("{")

        # get_state should return None for corrupted state
        assert fixture.get_state() is None

    def test_merge_state_fixture_clear(self, tmp_path):
        """MergeStateFixture can clear state."""
        fixture = MergeStateFixture(tmp_path)
        fixture.create_state(
            feature_slug="001-test",
            wp_order=["WP01"],
            completed_wps=[],
        )
        assert fixture.state_file.exists()

        fixture.clear_state()
        assert not fixture.state_file.exists()

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
        assert feature.get_worktree_path("WP01") is not None
        assert feature.get_worktree_path("WP01").exists()
        assert feature.get_worktree_path("WP02") is not None
        assert feature.get_worktree_path("WP02").exists()

    def test_create_test_feature_with_dependencies(self, create_test_feature):
        """Can create WPs with dependency declarations."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
                WPFixture("WP02", lane="done", dependencies=["WP01"]),
            ]
        )

        assert len(feature.worktrees) == 2
        assert len(feature.branches) == 2

        # Verify WP02 prompt file contains dependency
        wp02_prompt = feature._feature_dir / "tasks" / "WP02-test.md"
        assert wp02_prompt.exists()
        content = wp02_prompt.read_text()
        assert "WP01" in content

    def test_create_test_feature_with_dirty_worktree(self, create_test_feature):
        """Can create a WP with uncommitted changes."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done", dirty=True),
            ]
        )

        wp_path = feature.get_worktree_path("WP01")
        assert wp_path is not None

        # Verify worktree has uncommitted changes
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=wp_path,
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip()  # Has uncommitted changes
        assert "dirty_file.txt" in result.stdout

    def test_conflict_fixture_lane(self, create_test_feature):
        """ConflictFixture can create lane conflicts."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
                WPFixture("WP02", lane="done"),
            ]
        )

        conflict = ConflictFixture(feature)
        conflict.create_lane_conflict(
            "WP01", "WP02",
            task_file="conflict-task.md",
            wp1_lane="done",
            wp2_lane="for_review",
        )

        # Verify both worktrees have the task file with different lanes
        wp1_task = feature.get_worktree_path("WP01") / "kitty-specs" / feature.feature_slug / "tasks" / "conflict-task.md"
        wp2_task = feature.get_worktree_path("WP02") / "kitty-specs" / feature.feature_slug / "tasks" / "conflict-task.md"

        assert wp1_task.exists()
        assert wp2_task.exists()
        assert 'lane: "done"' in wp1_task.read_text()
        assert 'lane: "for_review"' in wp2_task.read_text()

    def test_conflict_fixture_code(self, create_test_feature):
        """ConflictFixture can create code file conflicts."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
                WPFixture("WP02", lane="done"),
            ]
        )

        conflict = ConflictFixture(feature)
        conflict.create_code_conflict(
            "WP01", "WP02",
            file_path="src/shared.py",
            wp1_content="def foo(): return 'WP01'",
            wp2_content="def foo(): return 'WP02'",
        )

        # Verify both worktrees have the code file with different content
        wp1_code = feature.get_worktree_path("WP01") / "src" / "shared.py"
        wp2_code = feature.get_worktree_path("WP02") / "src" / "shared.py"

        assert wp1_code.exists()
        assert wp2_code.exists()
        assert "WP01" in wp1_code.read_text()
        assert "WP02" in wp2_code.read_text()

    def test_cleanup_utilities(self, tmp_path):
        """Cleanup utilities work correctly."""
        # Create a test git repo
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True, capture_output=True)

        # Create initial commit
        (tmp_path / "README.md").write_text("# Test")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=tmp_path, check=True, capture_output=True)

        # Create a branch matching pattern
        subprocess.run(["git", "branch", "test-WP01"], cwd=tmp_path, check=True, capture_output=True)

        # Verify branch exists
        result = subprocess.run(
            ["git", "branch", "--list", "*-WP*"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )
        assert "test-WP01" in result.stdout

        # Cleanup branches
        cleanup_branches(tmp_path, "*-WP*")

        # Verify branch removed
        result = subprocess.run(
            ["git", "branch", "--list", "*-WP*"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )
        assert "test-WP01" not in result.stdout

    def test_feature_cleanup(self, create_test_feature):
        """Feature cleanup removes worktrees and branches."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
                WPFixture("WP02", lane="done"),
            ]
        )

        # Store paths before cleanup
        wp1_path = feature.get_worktree_path("WP01")
        wp2_path = feature.get_worktree_path("WP02")
        branches = list(feature.branches)

        assert wp1_path.exists()
        assert wp2_path.exists()
        assert len(branches) == 2

        # Cleanup
        feature.cleanup()

        # Verify cleanup
        assert not wp1_path.exists()
        assert not wp2_path.exists()
        assert len(feature.worktrees) == 0
        assert len(feature.branches) == 0

        # Verify branches removed
        result = subprocess.run(
            ["git", "branch", "--list"],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )
        for branch in branches:
            assert branch not in result.stdout
