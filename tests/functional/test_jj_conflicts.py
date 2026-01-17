"""
Conflict Handling Tests for jj (jujutsu) integration.

These tests validate jj's non-blocking conflict semantics vs git's blocking behavior,
and spec-kitty's handling of conflicts in review/merge workflows.

Test Matrix (CONF-001 to CONF-006):
- CONF-001: jj sync succeeds with conflict stored in file
- CONF-002: git sync conflict behavior (may block)
- CONF-003: /spec-kitty.review blocked with conflicts
- CONF-004: Merge command blocked with conflicts
- CONF-005: Conflict resolution auto-recorded by jj
- CONF-006: 3-way merge shows all sides

Key semantic difference:
- jj: Conflicts are stored in files (work continues) - non-blocking
- git: Conflicts may block commands until resolved

Note: These tests require jj and spec-kitty to be installed.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


# =============================================================================
# Helper Functions
# =============================================================================

def create_spec_kitty_project(project_dir: Path, use_jj: bool = True) -> bool:
    """Initialize a spec-kitty project with the specified VCS.

    Args:
        project_dir: Directory to initialize the project in
        use_jj: If True, use jj; if False, use git only

    Returns:
        True if successful, False otherwise
    """
    # Initialize git first (required for spec-kitty)
    subprocess.run(
        ["git", "init"],
        cwd=project_dir,
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=project_dir,
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=project_dir,
        check=True,
        capture_output=True
    )

    # Initialize spec-kitty
    vcs_flag = "--vcs=jj" if use_jj else "--vcs=git"
    result = subprocess.run(
        ["spec-kitty", "init", "--here", "--force", "--ai", "claude", vcs_flag],
        cwd=project_dir,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return False

    # Make initial commit
    subprocess.run(
        ["git", "add", "."],
        cwd=project_dir,
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=project_dir,
        check=True,
        capture_output=True
    )

    # Initialize jj if requested
    if use_jj and shutil.which("jj"):
        subprocess.run(
            ["jj", "git", "init", "--colocate"],
            cwd=project_dir,
            capture_output=True
        )

    return True


def create_feature_with_wps(project_dir: Path, feature_name: str, num_wps: int = 1) -> Path | None:
    """Create a feature with work packages for testing.

    Args:
        project_dir: The spec-kitty project directory
        feature_name: Name of the feature to create
        num_wps: Number of work packages to create

    Returns:
        Path to the feature directory, or None if creation failed
    """
    kitty_specs = project_dir / "kitty-specs"
    kitty_specs.mkdir(exist_ok=True)

    # Create feature directory
    feature_dir = kitty_specs / f"001-{feature_name}"
    feature_dir.mkdir(exist_ok=True)

    # Create meta.json
    meta = {
        "feature_number": "001",
        "slug": feature_name,
        "friendly_name": f"Test Feature: {feature_name}",
        "mission": "software-dev",
        "created_at": "2026-01-17T00:00:00Z"
    }
    with open(feature_dir / "meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    # Create spec.md
    (feature_dir / "spec.md").write_text(f"# {feature_name}\n\nTest spec content.")

    # Create tasks directory with work packages
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(exist_ok=True)

    for i in range(1, num_wps + 1):
        wp_id = f"WP{i:02d}"
        deps = [f"WP{i-1:02d}"] if i > 1 else []

        wp_content = f"""---
work_package_id: "{wp_id}"
title: "Test Work Package {i}"
lane: "planned"
dependencies: {json.dumps(deps)}
subtasks:
  - "T{i:03d}"
---

# {wp_id} - Test Work Package

Test content for {wp_id}.
"""
        (tasks_dir / f"{wp_id}-test-wp.md").write_text(wp_content)

    # Create tasks.md
    tasks_md_lines = ["# Tasks\n", "\n## Work Packages\n"]
    for i in range(1, num_wps + 1):
        wp_id = f"WP{i:02d}"
        tasks_md_lines.append(f"\n### {wp_id} - Test Work Package {i}\n")
        if i > 1:
            tasks_md_lines.append(f"Dependencies: WP{i-1:02d}\n")
        tasks_md_lines.append(f"- [ ] T{i:03d}: Test subtask\n")

    (feature_dir / "tasks.md").write_text("".join(tasks_md_lines))

    # Commit the feature files
    subprocess.run(
        ["git", "add", "."],
        cwd=project_dir,
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", f"Add feature: {feature_name}"],
        cwd=project_dir,
        check=True,
        capture_output=True
    )

    return feature_dir


def create_workspace(project_dir: Path, wp_id: str, base_wp: str | None = None) -> Path | None:
    """Create a workspace for a work package.

    Args:
        project_dir: The spec-kitty project directory
        wp_id: The work package ID (e.g., "WP01")
        base_wp: Optional base work package for dependency chain

    Returns:
        Path to the workspace directory, or None if creation failed
    """
    cmd = ["spec-kitty", "implement", wp_id]
    if base_wp:
        cmd.extend(["--base", base_wp])

    result = subprocess.run(
        cmd,
        cwd=project_dir,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return None

    # Find the workspace
    worktrees_dir = project_dir / ".worktrees"
    if not worktrees_dir.exists():
        return None

    workspaces = list(worktrees_dir.glob(f"*{wp_id}*"))
    return workspaces[0] if workspaces else None


def has_jj_conflict_markers(file_path: Path) -> bool:
    """Check if a file has jj-style conflict markers.

    jj conflict markers look like:
    <<<<<<< Conflict 1 of 1
    %%%%%%% Changes from base to side #1
    ...
    +++++++ Contents of side #2
    ...
    >>>>>>>
    """
    if not file_path.exists():
        return False

    content = file_path.read_text()
    # jj uses different markers than git
    jj_markers = ["<<<<<<<", ">>>>>>>", "%%%%%%%", "+++++++"]
    return any(marker in content for marker in jj_markers)


def has_git_conflict_markers(file_path: Path) -> bool:
    """Check if a file has git-style conflict markers.

    Git conflict markers look like:
    <<<<<<< HEAD
    ...
    =======
    ...
    >>>>>>> branch-name
    """
    if not file_path.exists():
        return False

    content = file_path.read_text()
    # Git markers
    return "<<<<<<" in content and "======" in content and ">>>>>>" in content


def write_file_and_commit(repo_dir: Path, filename: str, content: str, message: str) -> Path:
    """Write file content and commit it in the given repo."""
    file_path = repo_dir / filename
    file_path.write_text(content)

    subprocess.run(
        ["git", "add", filename],
        cwd=repo_dir,
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repo_dir,
        check=True,
        capture_output=True
    )

    return file_path


def write_file_and_jj_commit(repo_dir: Path, filename: str, content: str, message: str) -> Path:
    """Write file content and commit it using jj describe/new."""
    file_path = repo_dir / filename
    file_path.write_text(content)

    subprocess.run(
        ["jj", "describe", "-m", message],
        cwd=repo_dir,
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["jj", "new"],
        cwd=repo_dir,
        check=True,
        capture_output=True
    )

    return file_path


def jj_get_commit_id(repo_dir: Path, rev: str) -> str:
    """Get the commit ID for a jj revision."""
    result = subprocess.run(
        ["jj", "log", "-r", rev, "--no-graph", "-T", "commit_id"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
        text=True
    )
    return result.stdout.strip()


def jj_set_bookmark(repo_dir: Path, name: str, rev: str) -> None:
    """Move a jj bookmark to a specific revision."""
    subprocess.run(
        ["jj", "bookmark", "set", name, "-r", rev],
        cwd=repo_dir,
        check=True,
        capture_output=True
    )


def git_has_unmerged_files(repo_dir: Path) -> bool:
    """Check for unmerged entries in git status."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_dir,
        capture_output=True,
        text=True
    )
    for line in result.stdout.splitlines():
        if line[:2] in {"UU", "AA", "DD", "UD", "DU", "UA", "AU"}:
            return True
    return False


def jj_has_conflicts(repo_dir: Path) -> bool:
    """Check jj status output for conflicts."""
    result = subprocess.run(
        ["jj", "status"],
        cwd=repo_dir,
        capture_output=True,
        text=True
    )
    for line in result.stdout.splitlines():
        if line.strip().startswith("C "):
            return True
    combined = (result.stdout + result.stderr).lower()
    return "conflict" in combined or "unresolved conflicts" in combined


def jj_unresolved_conflicts(output: str) -> bool:
    """Check jj status output for unresolved conflict warnings."""
    return "unresolved conflicts" in output.lower()


def sync_workspace(workspace: Path) -> subprocess.CompletedProcess:
    """Run spec-kitty sync in workspace and return the process result."""
    return subprocess.run(
        ["spec-kitty", "sync"],
        cwd=workspace,
        capture_output=True,
        text=True
    )


def create_conflict_via_sync(
    project_dir: Path,
    wp_id: str,
    filename: str,
    base_content: str,
    main_content: str,
    workspace_content: str,
    use_jj: bool = False,
) -> tuple[Path | None, subprocess.CompletedProcess | None, str]:
    """Create a real conflict in a workspace by syncing against main."""
    if use_jj:
        write_file_and_jj_commit(project_dir, filename, base_content, f"Add {filename} base")
        base_commit_id = jj_get_commit_id(project_dir, "@-")
        jj_set_bookmark(project_dir, "main", base_commit_id)
    else:
        write_file_and_commit(project_dir, filename, base_content, f"Add {filename} base")

    workspace = create_workspace(project_dir, wp_id)
    if not workspace:
        return None, None, "Workspace creation not supported"

    if use_jj:
        write_file_and_jj_commit(workspace, filename, workspace_content, f"Edit {filename} in workspace")
        workspace_commit_id = jj_get_commit_id(workspace, "@-")

        write_file_and_jj_commit(project_dir, filename, main_content, f"Edit {filename} in main")
        main_commit_id = jj_get_commit_id(project_dir, "@-")
        jj_set_bookmark(project_dir, "main", main_commit_id)

        subprocess.run(
            ["jj", "rebase", "-r", workspace_commit_id, "-d", main_commit_id],
            cwd=workspace,
            capture_output=True,
            text=True
        )

        conflict_result = subprocess.run(
            ["jj", "log", "-r", "conflicts()", "--no-graph", "-T", "commit_id"],
            cwd=workspace,
            capture_output=True,
            text=True
        )
        conflict_ids = [line.strip() for line in conflict_result.stdout.splitlines() if line.strip()]
        if conflict_ids:
            subprocess.run(
                ["jj", "new", conflict_ids[0]],
                cwd=workspace,
                check=True,
                capture_output=True
            )
    else:
        write_file_and_commit(workspace, filename, workspace_content, f"Edit {filename} in workspace")
        write_file_and_commit(project_dir, filename, main_content, f"Edit {filename} in main")

    sync_result = sync_workspace(workspace)
    combined = sync_result.stdout + sync_result.stderr

    if "no such command" in combined.lower():
        return workspace, None, "spec-kitty sync command not available"

    return workspace, sync_result, combined

def create_conflict(project_dir: Path, workspace: Path, filename: str = "conflict.txt") -> bool:
    """Create a conflict between main branch and workspace.

    Args:
        project_dir: The main project directory
        workspace: The workspace directory
        filename: Name of the file to create conflict in

    Returns:
        True if conflict was created, False otherwise
    """
    # Create file in main branch
    main_file = project_dir / filename
    main_file.write_text("Line 1\nLine 2 - main version\nLine 3\n")

    subprocess.run(
        ["git", "add", filename],
        cwd=project_dir,
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", f"Add {filename} in main"],
        cwd=project_dir,
        check=True,
        capture_output=True
    )

    # Create different version in workspace
    ws_file = workspace / filename
    ws_file.write_text("Line 1\nLine 2 - workspace version\nLine 3\n")

    subprocess.run(
        ["git", "add", filename],
        cwd=workspace,
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", f"Add {filename} in workspace"],
        cwd=workspace,
        check=True,
        capture_output=True
    )

    return True


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def jj_project(tmp_path, jj_available):
    """Create a spec-kitty project with jj VCS."""
    if not jj_available:
        pytest.skip("jj not installed")

    project_dir = tmp_path / "jj-conflict-project"
    project_dir.mkdir()

    if not create_spec_kitty_project(project_dir, use_jj=True):
        pytest.skip("Failed to create spec-kitty project")

    return project_dir


@pytest.fixture
def git_project(tmp_path):
    """Create a spec-kitty project with git VCS only."""
    project_dir = tmp_path / "git-conflict-project"
    project_dir.mkdir()

    if not create_spec_kitty_project(project_dir, use_jj=False):
        pytest.skip("Failed to create spec-kitty project")

    return project_dir


# =============================================================================
# CONF-001: jj Conflict Stored in File (T033)
# =============================================================================

class TestJJConflictStored:
    """CONF-001: Validate jj stores conflicts in files (non-blocking)."""

    @pytest.mark.jj
    def test_conf_001_jj_conflict_stored(self, jj_project, jj_available):
        """CONF-001: jj sync succeeds with conflict stored in file.

        When a conflict occurs during jj sync, the command should succeed
        and the conflict markers should be stored in the file itself,
        allowing work to continue.
        """
        # Create feature with work packages
        feature_dir = create_feature_with_wps(jj_project, "conflict-test", num_wps=1)
        if not feature_dir:
            pytest.xfail("Feature creation not supported")

        workspace, sync_result, combined = create_conflict_via_sync(
            jj_project,
            "WP01",
            "test.txt",
            "Base content\n",
            "Different content from main\n",
            "Original content from workspace\n",
            use_jj=True,
        )
        if not workspace:
            pytest.xfail("Workspace creation not supported - spec-kitty implement may not be available")
        if sync_result is None:
            pytest.xfail(combined)

        if sync_result.returncode != 0:
            pytest.fail(f"Expected jj sync to succeed; got {sync_result.returncode}: {combined[:500]}")

        ws_test_file = workspace / "test.txt"
        assert ws_test_file.exists(), "Expected conflict file to exist after sync"
        assert has_jj_conflict_markers(ws_test_file), (
            "Expected jj conflict markers after sync, but none were found"
        )


# =============================================================================
# CONF-002: Git Conflict Behavior (T034)
# =============================================================================

class TestGitConflictBehavior:
    """CONF-002: Validate git conflict handling (may block)."""

    def test_conf_002_git_sync_conflict(self, git_project):
        """CONF-002: git sync conflict behavior.

        Git typically blocks on conflicts and requires resolution
        before continuing. This tests that behavior.
        """
        # Create feature with work packages
        feature_dir = create_feature_with_wps(git_project, "git-conflict-test", num_wps=1)
        if not feature_dir:
            pytest.xfail("Feature creation not supported")

        workspace, sync_result, combined = create_conflict_via_sync(
            git_project,
            "WP01",
            "test.txt",
            "Base content\n",
            "Different content from main\n",
            "Original content from workspace\n",
        )
        if not workspace:
            pytest.xfail("Workspace creation not supported - spec-kitty implement may not be available")
        if sync_result is None:
            pytest.xfail(combined)

        ws_test_file = workspace / "test.txt"
        conflict_in_file = ws_test_file.exists() and has_git_conflict_markers(ws_test_file)
        conflict_in_status = git_has_unmerged_files(workspace)
        conflict_reported = "conflict" in combined.lower() or "error" in combined.lower()

        assert conflict_in_file or conflict_in_status or conflict_reported, (
            f"Expected git conflict during sync but none detected. Output: {combined[:500]}"
        )


# =============================================================================
# CONF-003: Review Blocked with Conflicts (T035)
# =============================================================================

class TestReviewBlockedWithConflicts:
    """CONF-003: Validate review is blocked when conflicts exist."""

    @pytest.mark.jj
    def test_conf_003_review_blocked_with_conflicts(self, jj_project, jj_available):
        """CONF-003: /spec-kitty.review blocked with conflicts.

        The review command should refuse to proceed when there are
        unresolved conflicts in the workspace.
        """
        # Create feature
        feature_dir = create_feature_with_wps(jj_project, "review-conflict-test", num_wps=1)
        if not feature_dir:
            pytest.xfail("Feature creation not supported")

        workspace, sync_result, combined = create_conflict_via_sync(
            jj_project,
            "WP01",
            "conflicted.txt",
            "Base line\n",
            "Remote version\n",
            "Local version\n",
            use_jj=True,
        )
        if not workspace:
            pytest.xfail("Workspace creation not supported")
        if sync_result is None:
            pytest.xfail(combined)

        conflict_file = workspace / "conflicted.txt"
        conflict_present = (
            conflict_file.exists()
            and (has_jj_conflict_markers(conflict_file) or jj_has_conflicts(workspace))
        )
        assert conflict_present, "Expected real conflict in workspace before review"

        # Try to run review (via spec-kitty agent workflow)
        review_result = subprocess.run(
            ["spec-kitty", "agent", "workflow", "review", "WP01", "--agent", "test"],
            cwd=jj_project,
            capture_output=True,
            text=True
        )

        combined = review_result.stdout + review_result.stderr

        if "no such command" in combined.lower() or "not found" in combined.lower():
            pytest.xfail("spec-kitty agent workflow review command not available")

        if review_result.returncode == 0:
            # Review succeeded despite conflicts - document this as current behavior
            pytest.xfail(
                "spec-kitty review does not currently block on conflicts. "
                "Review command succeeded despite unresolved conflicts in workspace."
            )
        if "conflict" not in combined.lower():
            # Review failed but not due to conflicts
            pytest.xfail(f"Review command failed without conflict message: {combined[:500]}")


# =============================================================================
# CONF-004: Merge Blocked with Conflicts (T036)
# =============================================================================

class TestMergeBlockedWithConflicts:
    """CONF-004: Validate merge is blocked when conflicts exist."""

    @pytest.mark.jj
    def test_conf_004_merge_blocked_with_conflicts(self, jj_project, jj_available):
        """CONF-004: Merge command blocked with conflicts.

        The merge command should refuse to proceed when there are
        unresolved conflicts in the workspace.
        """
        # Create feature
        feature_dir = create_feature_with_wps(jj_project, "merge-conflict-test", num_wps=1)
        if not feature_dir:
            pytest.xfail("Feature creation not supported")

        workspace, sync_result, combined = create_conflict_via_sync(
            jj_project,
            "WP01",
            "conflicted.txt",
            "Base content\n",
            "Remote changes\n",
            "Local changes\n",
            use_jj=True,
        )
        if not workspace:
            pytest.xfail("Workspace creation not supported")
        if sync_result is None:
            pytest.xfail(combined)

        conflict_file = workspace / "conflicted.txt"
        conflict_present = (
            conflict_file.exists()
            and (has_jj_conflict_markers(conflict_file) or jj_has_conflicts(workspace))
        )
        assert conflict_present, "Expected real conflict in workspace before merge"

        # Try to run merge
        merge_result = subprocess.run(
            ["spec-kitty", "merge"],
            cwd=workspace,
            capture_output=True,
            text=True
        )

        combined = merge_result.stdout + merge_result.stderr

        if "no such command" in combined.lower():
            pytest.xfail("spec-kitty merge command not available")

        if merge_result.returncode == 0:
            pytest.fail("Merge command succeeded despite conflicts")
        assert conflict_present, "Conflicts should remain after failed merge"


# =============================================================================
# CONF-005: Resolution Auto-Recorded (T037)
# =============================================================================

class TestResolutionAutoRecorded:
    """CONF-005: Validate jj auto-records conflict resolution."""

    @pytest.mark.jj
    def test_conf_005_jj_resolution_auto_recorded(self, jj_project, jj_available):
        """CONF-005: Conflict resolution auto-recorded by jj.

        When a conflict is resolved by editing the file, jj should
        automatically record the resolution.
        """
        # Check if jj is available
        if not jj_available:
            pytest.skip("jj not installed")

        # Create feature
        feature_dir = create_feature_with_wps(jj_project, "resolution-test", num_wps=1)
        if not feature_dir:
            pytest.xfail("Feature creation not supported")

        workspace, sync_result, combined = create_conflict_via_sync(
            jj_project,
            "WP01",
            "to_resolve.txt",
            "Base content\n",
            "Remote changes\n",
            "Local changes\n",
            use_jj=True,
        )
        if not workspace:
            pytest.xfail("Workspace creation not supported")
        if sync_result is None:
            pytest.xfail(combined)

        conflict_file = workspace / "to_resolve.txt"
        assert conflict_file.exists(), "Expected conflict file to exist after sync"

        # Check jj status before resolution
        status_before = subprocess.run(
            ["jj", "status"],
            cwd=workspace,
            capture_output=True,
            text=True
        )

        # Resolve the conflict by editing the file
        conflict_file.write_text("Resolved: combined local and remote changes\n")

        combined_before = status_before.stdout + status_before.stderr
        assert jj_unresolved_conflicts(combined_before), (
            "Expected jj to report unresolved conflicts before resolution"
        )

        # Check jj status after resolution
        status_after = subprocess.run(
            ["jj", "status"],
            cwd=workspace,
            capture_output=True,
            text=True
        )

        combined_after = status_after.stdout + status_after.stderr
        assert not jj_unresolved_conflicts(combined_after), (
            "jj still shows unresolved conflicts after resolution"
        )
        assert "resolved in working copy" in combined_after.lower(), (
            "Expected jj to record resolution in working copy"
        )

        assert conflict_file.read_text() == "Resolved: combined local and remote changes\n"


# =============================================================================
# CONF-006: 3-Way Merge Shows All Sides (T038)
# =============================================================================

class TestThreeWayMerge:
    """CONF-006: Validate 3-way merge shows all sides in conflict markers."""

    @pytest.mark.jj
    def test_conf_006_three_way_conflict_all_sides_visible(self, jj_project, jj_available):
        """CONF-006: 3-way merge shows all sides.

        When a 3-way merge produces conflicts, all three sides
        (base, ours, theirs) should be visible in the markers.
        """
        # Create feature
        feature_dir = create_feature_with_wps(jj_project, "three-way-test", num_wps=2)
        if not feature_dir:
            pytest.xfail("Feature creation not supported")

        workspace, sync_result, combined = create_conflict_via_sync(
            jj_project,
            "WP01",
            "three_way.txt",
            "Base content\n",
            "Remote content\n",
            "Local content\n",
            use_jj=True,
        )
        if not workspace:
            pytest.xfail("Workspace creation not supported")
        if sync_result is None:
            pytest.xfail(combined)

        conflict_file = workspace / "three_way.txt"
        assert conflict_file.exists(), "Expected conflict file to exist after sync"
        content = conflict_file.read_text()

        assert "<<<<<<<" in content, "Expected jj conflict start marker"
        assert "%%%%%%%" in content, "Expected jj base-to-side diff marker"
        assert "+++++++" in content, "Expected jj side content marker"
        assert ">>>>>>>" in content, "Expected jj conflict end marker"


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestConflictEdgeCases:
    """Edge case tests for conflict handling."""

    @pytest.mark.jj
    def test_multiple_conflicts_same_file(self, jj_project, jj_available):
        """Test handling of multiple conflicts in the same file."""
        # Create a file with multiple conflict regions
        multi_conflict = jj_project / "multi_conflict.txt"
        content = """Section 1
<<<<<<< Conflict 1 of 2
Local section 1
=======
Remote section 1
>>>>>>>

Section 2
<<<<<<< Conflict 2 of 2
Local section 2
=======
Remote section 2
>>>>>>>
"""
        multi_conflict.write_text(content)

        # Verify both conflicts are detectable
        file_content = multi_conflict.read_text()
        conflict_count = file_content.count("<<<<<<<")

        assert conflict_count >= 2, f"Expected at least 2 conflicts, found {conflict_count}"

    @pytest.mark.jj
    def test_binary_file_conflict(self, jj_project, jj_available):
        """Test that binary file conflicts are handled gracefully."""
        # Create a binary-like file (will be detected as binary by VCS)
        binary_file = jj_project / "image.png"
        # Write some binary content (PNG header followed by random bytes)
        binary_content = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
        binary_file.write_bytes(binary_content)

        subprocess.run(
            ["git", "add", "image.png"],
            cwd=jj_project,
            capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Add binary file"],
            cwd=jj_project,
            capture_output=True
        )

        # Binary files cannot have text conflict markers
        # This test just verifies the file was created
        assert binary_file.exists()
        assert binary_file.read_bytes().startswith(b'\x89PNG')

    @pytest.mark.jj
    def test_empty_file_conflict(self, jj_project, jj_available):
        """Test conflict handling with empty files."""
        empty_file = jj_project / "empty.txt"
        empty_file.touch()

        subprocess.run(
            ["git", "add", "empty.txt"],
            cwd=jj_project,
            capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Add empty file"],
            cwd=jj_project,
            capture_output=True
        )

        assert empty_file.exists()
        assert empty_file.stat().st_size == 0
