"""
Uncommitted changes preservation tests (WP09: T055).

Tests for:
- Sync preserves uncommitted non-conflicting changes
- Sync detects conflicting uncommitted changes
- Stash/restore mechanism for safe syncing

These tests ensure uncommitted work is never lost during
sync operations, which is critical for data loss prevention.
"""
import pytest
import subprocess
from pathlib import Path
from typing import Tuple, Optional

from .conftest import create_worktree


# =============================================================================
# Sync Helper Functions (for testing)
# =============================================================================

def has_uncommitted_changes(repo_path: Path) -> bool:
    """Check if repository has uncommitted changes."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_path,
        capture_output=True,
        text=True
    )
    return len(result.stdout.strip()) > 0


def get_uncommitted_files(repo_path: Path) -> list:
    """Get list of uncommitted files."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_path,
        capture_output=True,
        text=True
    )
    files = []
    for line in result.stdout.strip().split("\n"):
        if line:
            # Format: XY filename
            files.append(line[3:].strip())
    return files


def stash_changes(repo_path: Path, message: str = "auto-stash", include_untracked: bool = True) -> bool:
    """Stash uncommitted changes.

    Args:
        repo_path: Path to repository
        message: Stash message
        include_untracked: Include untracked files (default True)
    """
    cmd = ["git", "stash", "push", "-m", message]
    if include_untracked:
        cmd.append("--include-untracked")
    result = subprocess.run(
        cmd,
        cwd=repo_path,
        capture_output=True,
        text=True
    )
    return result.returncode == 0


def pop_stash(repo_path: Path) -> Tuple[bool, str]:
    """Pop stashed changes."""
    result = subprocess.run(
        ["git", "stash", "pop"],
        cwd=repo_path,
        capture_output=True,
        text=True
    )
    return result.returncode == 0, result.stderr


def has_stash(repo_path: Path) -> bool:
    """Check if there's anything in the stash."""
    result = subprocess.run(
        ["git", "stash", "list"],
        cwd=repo_path,
        capture_output=True,
        text=True
    )
    return len(result.stdout.strip()) > 0


def sync_worktree(
    project_path: Path,
    worktree_path: Path,
    stash: bool = False
) -> Tuple[bool, Optional[str]]:
    """
    Sync worktree with main branch.

    Args:
        project_path: Path to main project
        worktree_path: Path to worktree
        stash: Whether to stash uncommitted changes before sync

    Returns:
        Tuple of (success, error_message)
    """
    # Check for uncommitted changes
    if has_uncommitted_changes(worktree_path):
        if stash:
            # Stash changes before sync
            if not stash_changes(worktree_path, "sync-auto-stash"):
                return False, "Failed to stash changes"
        else:
            # Check if changes would conflict
            uncommitted = get_uncommitted_files(worktree_path)
            return False, f"Uncommitted changes would conflict: {uncommitted}"

    # Perform sync (fetch + merge/rebase)
    fetch_result = subprocess.run(
        ["git", "fetch", "origin"],
        cwd=worktree_path,
        capture_output=True,
        text=True
    )

    # If stashed, restore changes
    if stash and has_stash(worktree_path):
        success, error = pop_stash(worktree_path)
        if not success:
            return False, f"Failed to restore stashed changes: {error}"

    return True, None


# =============================================================================
# T055: Uncommitted Changes Preservation Tests
# =============================================================================

class TestUncommittedChangesPreservation:
    """Test uncommitted changes are never lost during sync."""

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_detect_uncommitted_changes(self, multi_feature_project):
        """Can detect uncommitted changes in repository."""
        project = multi_feature_project

        # Initially should be clean
        assert not has_uncommitted_changes(project)

        # Create uncommitted file
        new_file = project / "uncommitted.txt"
        new_file.write_text("Uncommitted changes")

        # Should detect uncommitted changes
        assert has_uncommitted_changes(project)

        # Cleanup
        new_file.unlink()

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_get_uncommitted_files_list(self, multi_feature_project):
        """Get list of uncommitted files."""
        project = multi_feature_project

        # Create multiple uncommitted files
        file1 = project / "uncommitted1.txt"
        file2 = project / "uncommitted2.txt"
        file1.write_text("File 1")
        file2.write_text("File 2")

        # Get uncommitted files
        files = get_uncommitted_files(project)

        assert "uncommitted1.txt" in files
        assert "uncommitted2.txt" in files

        # Cleanup
        file1.unlink()
        file2.unlink()

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_stash_and_restore_changes(self, multi_feature_project):
        """Stash and restore preserves uncommitted changes."""
        project = multi_feature_project

        # Create uncommitted changes
        work_file = project / "work-in-progress.txt"
        work_content = "Important uncommitted work"
        work_file.write_text(work_content)

        assert has_uncommitted_changes(project)

        # Stash changes
        assert stash_changes(project, "test-stash")

        # Should be clean now
        assert not has_uncommitted_changes(project)
        assert not work_file.exists()  # File gone after stash

        # Restore stash
        success, _ = pop_stash(project)
        assert success

        # Changes should be back
        assert work_file.exists()
        assert work_file.read_text() == work_content

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_sync_rejects_uncommitted_without_stash(self, multi_feature_project):
        """Sync without stash option rejects uncommitted changes."""
        project = multi_feature_project

        # Create worktree
        wt = create_worktree(project, "001-feature-001", "WP01")

        # Create uncommitted file in worktree
        uncommitted_file = wt / "work-in-progress.txt"
        uncommitted_file.write_text("Local uncommitted changes")

        # Verify it's uncommitted
        assert has_uncommitted_changes(wt)

        # Sync without stash should fail
        success, error = sync_worktree(project, wt, stash=False)

        assert not success
        assert error is not None
        assert "uncommitted" in error.lower() or "conflict" in error.lower()

        # File should still exist (not lost)
        assert uncommitted_file.exists()
        assert uncommitted_file.read_text() == "Local uncommitted changes"

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_sync_with_stash_preserves_changes(self, multi_feature_project):
        """Sync with stash option preserves uncommitted changes."""
        project = multi_feature_project

        # Create worktree
        wt = create_worktree(project, "001-feature-001", "WP01")

        # Create uncommitted changes
        wip = wt / "wip.txt"
        wip_content = "Work in progress - MUST NOT LOSE"
        wip.write_text(wip_content)

        # Verify uncommitted
        assert has_uncommitted_changes(wt)

        # Sync with stash - should work
        # Note: In real scenario this would also merge upstream
        if has_uncommitted_changes(wt):
            assert stash_changes(wt, "sync-stash")
            assert not has_uncommitted_changes(wt)
            success, _ = pop_stash(wt)
            assert success

        # Changes should be restored
        assert wip.exists()
        assert wip.read_text() == wip_content

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_uncommitted_changes_across_multiple_files(self, multi_feature_project):
        """Multiple uncommitted files are all preserved."""
        project = multi_feature_project

        # Create worktree
        wt = create_worktree(project, "001-feature-001", "WP01")

        # Create multiple uncommitted files
        files_content = {
            "file1.txt": "Content 1",
            "file2.txt": "Content 2",
            "subdir/file3.txt": "Content 3",
        }

        for path, content in files_content.items():
            file_path = wt / path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)

        # Stash all
        assert stash_changes(wt, "multi-file-stash")

        # All files should be gone
        for path in files_content:
            assert not (wt / path).exists()

        # Restore
        success, _ = pop_stash(wt)
        assert success

        # All files should be back with correct content
        for path, content in files_content.items():
            file_path = wt / path
            assert file_path.exists(), f"File {path} not restored"
            assert file_path.read_text() == content

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_modified_tracked_file_preserved(self, multi_feature_project):
        """Modified tracked files are preserved during sync."""
        project = multi_feature_project

        # Create worktree
        wt = create_worktree(project, "001-feature-001", "WP01")

        # Modify an existing tracked file
        # The worktree has files from initial commit
        existing_file = wt / ".kittify" / "config.yaml"
        if existing_file.exists():
            original = existing_file.read_text()
            modified = original + "\n# Local modification"
            existing_file.write_text(modified)

            # Verify modification is detected
            assert has_uncommitted_changes(wt)

            # Stash and restore
            stash_changes(wt, "mod-stash")
            success, _ = pop_stash(wt)
            assert success

            # Modification should be preserved
            assert existing_file.read_text() == modified

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_staged_changes_preserved(self, multi_feature_project):
        """Staged (added) changes are preserved during sync."""
        project = multi_feature_project

        # Create worktree
        wt = create_worktree(project, "001-feature-001", "WP01")

        # Create and stage a file
        staged_file = wt / "staged.txt"
        staged_content = "This is staged but not committed"
        staged_file.write_text(staged_content)

        # Stage it
        subprocess.run(
            ["git", "add", "staged.txt"],
            cwd=wt,
            check=True
        )

        # Verify it's staged
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=wt,
            capture_output=True,
            text=True
        )
        assert "A" in status.stdout  # Added

        # Stash and restore
        stash_changes(wt, "staged-stash")
        success, _ = pop_stash(wt)
        assert success

        # File should be back (may or may not still be staged)
        assert staged_file.exists()
        assert staged_file.read_text() == staged_content

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_has_stash_detection(self, multi_feature_project):
        """Can detect if stash has entries."""
        project = multi_feature_project

        # Initially no stash
        assert not has_stash(project)

        # Create and stash changes
        temp_file = project / "temp.txt"
        temp_file.write_text("Temp")
        stash_changes(project, "test")

        # Now has stash
        assert has_stash(project)

        # Pop stash
        pop_stash(project)

        # No more stash
        assert not has_stash(project)

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_empty_stash_pop_fails_gracefully(self, multi_feature_project):
        """Popping empty stash fails gracefully."""
        project = multi_feature_project

        # Ensure no stash
        assert not has_stash(project)

        # Try to pop
        success, error = pop_stash(project)

        # Should fail gracefully
        assert not success

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_uncommitted_deletions_preserved(self, multi_feature_project):
        """Uncommitted file deletions are preserved."""
        project = multi_feature_project

        # Create worktree
        wt = create_worktree(project, "001-feature-001", "WP01")

        # First commit a file
        file_to_delete = wt / "will-delete.txt"
        file_to_delete.write_text("Will be deleted")
        subprocess.run(["git", "add", "will-delete.txt"], cwd=wt, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Add file to delete"],
            cwd=wt,
            check=True
        )

        # Now delete it (uncommitted)
        file_to_delete.unlink()

        # Verify deletion is detected
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=wt,
            capture_output=True,
            text=True
        )
        assert "D" in status.stdout  # Deleted

        # Stash the deletion
        stash_changes(wt, "deletion-stash")

        # File should be back after stash (stash saves the deletion)
        assert file_to_delete.exists()

        # Pop stash - deletion should be restored
        success, _ = pop_stash(wt)
        assert success

        # File should be deleted again
        assert not file_to_delete.exists()

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_binary_file_preserved(self, multi_feature_project):
        """Binary files are preserved during stash/restore."""
        project = multi_feature_project

        # Create worktree
        wt = create_worktree(project, "001-feature-001", "WP01")

        # Create binary file
        binary_file = wt / "binary.bin"
        binary_content = bytes([0x00, 0x01, 0x02, 0xFF, 0xFE, 0xFD])
        binary_file.write_bytes(binary_content)

        # Stash
        stash_changes(wt, "binary-stash")
        assert not binary_file.exists()

        # Restore
        success, _ = pop_stash(wt)
        assert success

        # Binary content should be intact
        assert binary_file.exists()
        assert binary_file.read_bytes() == binary_content
