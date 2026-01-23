"""
Fixtures for data loss prevention tests (WP09: T050).

Provides fixtures for:
- Multi-feature project setup with worktrees
- Conflict scenario creation and validation
- File modification tracking
- File locking simulation
"""
import pytest
import tempfile
import json
import os
import stat
import time
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any


# =============================================================================
# T050: Project and Worktree Fixtures
# =============================================================================

@pytest.fixture
def multi_feature_project(tmp_path):
    """
    Create a project with multiple features and worktree support.

    Creates:
    - Git repository initialized
    - .kittify/ directory structure
    - kitty-specs/ with 3 features (001, 002, 003)
    - .worktrees/ directory for worktree storage
    """
    project_path = tmp_path / "test-project"
    project_path.mkdir()

    # Initialize git repo
    subprocess.run(
        ["git", "init"],
        cwd=project_path,
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=project_path,
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=project_path,
        check=True,
        capture_output=True
    )

    # Create .kittify structure
    kittify = project_path / ".kittify"
    kittify.mkdir()
    (kittify / "config.yaml").write_text("version: 1\n")

    # Create main repo kitty-specs
    kitty_specs = project_path / "kitty-specs"
    kitty_specs.mkdir()

    # Create multiple features
    for feature_num in ["001", "002", "003"]:
        feature_dir = kitty_specs / f"{feature_num}-feature-{feature_num}"
        feature_dir.mkdir()
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        # Create meta.json
        meta = {
            "feature_number": feature_num,
            "slug": f"{feature_num}-feature-{feature_num}",
            "vcs": "git",
            "created_at": datetime.now().isoformat()
        }
        (feature_dir / "meta.json").write_text(json.dumps(meta, indent=2))

        # Create spec.md
        (feature_dir / "spec.md").write_text(f"# Feature {feature_num}\n\nTest feature.")

        # Create tasks.md
        tasks_content = f"""---
lane: planned
feature_id: "{feature_num}-feature-{feature_num}"
---

# Tasks for Feature {feature_num}

## Work Packages

- [ ] WP01 - First work package
- [ ] WP02 - Second work package
"""
        (feature_dir / "tasks.md").write_text(tasks_content)

        # Create sample WP file
        wp_content = """---
work_package_id: "WP01"
title: "First Work Package"
lane: "planned"
dependencies: []
history:
  - timestamp: "2026-01-23T10:00:00Z"
    lane: "planned"
    agent: "system"
    action: "Created"
---

# WP01 - First Work Package

Test work package content.
"""
        (tasks_dir / "WP01-first-work-package.md").write_text(wp_content)

    # Create worktrees directory
    worktrees = project_path / ".worktrees"
    worktrees.mkdir()

    # Initial commit
    subprocess.run(["git", "add", "."], cwd=project_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=project_path,
        check=True,
        capture_output=True
    )

    return project_path


def create_worktree(project_path: Path, feature: str, wp_id: str) -> Path:
    """
    Create a git worktree for testing.

    Args:
        project_path: Path to main project
        feature: Feature slug (e.g., "001-feature-001")
        wp_id: Work package ID (e.g., "WP01")

    Returns:
        Path to created worktree
    """
    worktree_path = project_path / ".worktrees" / f"{feature}-{wp_id}"
    branch_name = f"{feature}/{wp_id}"

    # Create worktree with new branch
    result = subprocess.run(
        ["git", "worktree", "add", "-b", branch_name, str(worktree_path)],
        cwd=project_path,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(f"Failed to create worktree: {result.stderr}")

    return worktree_path


@pytest.fixture
def worktree_factory(multi_feature_project):
    """Factory fixture for creating worktrees."""
    created_worktrees = []

    def _create(feature: str, wp_id: str) -> Path:
        wt = create_worktree(multi_feature_project, feature, wp_id)
        created_worktrees.append(wt)
        return wt

    yield _create

    # Cleanup: remove worktrees
    for wt in created_worktrees:
        if wt.exists():
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(wt)],
                cwd=multi_feature_project,
                capture_output=True
            )


# =============================================================================
# Conflict Scenario Fixtures
# =============================================================================

@pytest.fixture
def conflict_scenario_factory():
    """Factory for creating conflict scenarios."""

    class ConflictScenario:
        """Represents a merge conflict scenario for testing."""

        LANE_PRECEDENCE = {
            "planned": 0,
            "doing": 1,
            "for_review": 2,
            "done": 3
        }

        def __init__(self, conflict_type: str):
            self.conflict_type = conflict_type
            self.wp_modifications: Dict[str, Dict[str, Any]] = {}
            self.expected_resolution: str = ""
            self.auto_resolvable: bool = True

        def add_modification(
            self,
            wp_id: str,
            file_path: str,
            content: Dict[str, Any]
        ):
            """Add a modification for a WP."""
            if wp_id not in self.wp_modifications:
                self.wp_modifications[wp_id] = {}
            self.wp_modifications[wp_id][file_path] = content

        def apply_to_feature(self, feature_path: Path):
            """Apply modifications to create conflict scenario."""
            for wp_id, files in self.wp_modifications.items():
                for file_path, content in files.items():
                    full_path = feature_path / file_path
                    full_path.parent.mkdir(parents=True, exist_ok=True)

                    if isinstance(content, dict):
                        # YAML frontmatter update
                        import yaml
                        frontmatter = f"---\n{yaml.dump(content, default_flow_style=False)}---\n"
                        full_path.write_text(frontmatter)
                    else:
                        full_path.write_text(str(content))

        def validate_resolution(self, merged_content: str) -> bool:
            """Validate conflict was resolved correctly."""
            return self.expected_resolution in merged_content

        @classmethod
        def get_more_done_lane(cls, lane1: str, lane2: str) -> str:
            """Return the more-done lane."""
            p1 = cls.LANE_PRECEDENCE.get(lane1, 0)
            p2 = cls.LANE_PRECEDENCE.get(lane2, 0)
            return lane1 if p1 >= p2 else lane2

    return ConflictScenario


# =============================================================================
# File Modification Tracking Fixtures
# =============================================================================

@pytest.fixture
def file_modification_tracker():
    """Track file modification times for path resolution tests."""

    class ModificationTracker:
        """Tracks file modification times to detect changes."""

        def __init__(self):
            self.timestamps: Dict[Path, float] = {}
            self.contents: Dict[Path, str] = {}

        def record(self, path: Path):
            """Record file state."""
            if path.exists():
                self.timestamps[path] = path.stat().st_mtime
                if path.is_file():
                    try:
                        self.contents[path] = path.read_text()
                    except Exception:
                        self.contents[path] = ""

        def was_modified(self, path: Path) -> bool:
            """Check if file was modified since recording."""
            if path not in self.timestamps:
                return False
            if not path.exists():
                return True  # Deleted = modified
            return path.stat().st_mtime > self.timestamps[path]

        def assert_modified(self, path: Path, message: str = ""):
            """Assert file was modified since recording."""
            assert path in self.timestamps, f"Path {path} was not tracked"
            msg = message or f"File {path} was not modified"

            # Check mtime
            if path.exists():
                current_mtime = path.stat().st_mtime
                if current_mtime > self.timestamps[path]:
                    return  # Modified via mtime

                # Also check content
                if path.is_file():
                    try:
                        current_content = path.read_text()
                        if current_content != self.contents.get(path, ""):
                            return  # Modified via content
                    except Exception:
                        pass

            assert False, msg

        def assert_not_modified(self, path: Path, message: str = ""):
            """Assert file was NOT modified since recording."""
            assert path in self.timestamps, f"Path {path} was not tracked"
            assert path.exists(), f"File {path} was deleted"

            current_mtime = path.stat().st_mtime
            msg = message or f"File {path} was unexpectedly modified"

            # Check mtime
            if current_mtime != self.timestamps[path]:
                assert False, msg

            # Also check content
            if path.is_file() and path in self.contents:
                try:
                    current_content = path.read_text()
                    if current_content != self.contents[path]:
                        assert False, msg
                except Exception:
                    pass

    return ModificationTracker()


# =============================================================================
# File Locking Fixtures
# =============================================================================

@pytest.fixture
def locked_file_simulator():
    """Simulate file locking scenarios."""

    class FileLock:
        """Context manager to simulate file locking via permissions."""

        def __init__(self, file_path: Path):
            self.file_path = file_path
            self.original_mode = None

        def __enter__(self):
            if self.file_path.exists():
                self.original_mode = self.file_path.stat().st_mode
                # Make file read-only to simulate lock
                os.chmod(self.file_path, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
            return self

        def __exit__(self, *args):
            if self.file_path.exists() and self.original_mode is not None:
                # Restore original permissions
                os.chmod(self.file_path, self.original_mode)

    return FileLock


@pytest.fixture
def locked_directory_simulator():
    """Simulate directory locking scenarios."""

    class DirectoryLock:
        """Context manager to simulate directory locking via permissions."""

        def __init__(self, dir_path: Path):
            self.dir_path = dir_path
            self.original_mode = None

        def __enter__(self):
            if self.dir_path.exists():
                self.original_mode = self.dir_path.stat().st_mode
                # Make directory read-only (no write/execute)
                os.chmod(self.dir_path, stat.S_IRUSR | stat.S_IRGRP)
            return self

        def __exit__(self, *args):
            if self.dir_path.exists() and self.original_mode is not None:
                os.chmod(self.dir_path, self.original_mode)

    return DirectoryLock


# =============================================================================
# Cleanup Result Fixtures
# =============================================================================

@pytest.fixture
def cleanup_result_factory():
    """Factory for creating cleanup result objects."""

    class CleanupResult:
        """Represents the result of a cleanup operation."""

        def __init__(self):
            self.succeeded: List[str] = []
            self.failed: List[str] = []
            self.errors: Dict[str, str] = {}

        def add_success(self, wp_id: str):
            self.succeeded.append(wp_id)

        def add_failure(self, wp_id: str, error: str):
            self.failed.append(wp_id)
            self.errors[wp_id] = error

        @property
        def all_succeeded(self) -> bool:
            return len(self.failed) == 0

        def summary(self) -> str:
            return f"Succeeded: {len(self.succeeded)}, Failed: {len(self.failed)}"

    return CleanupResult
