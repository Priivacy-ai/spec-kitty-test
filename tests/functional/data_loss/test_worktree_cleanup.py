"""
Worktree cleanup boundary tests (WP09: T051).

Tests for:
- Cleanup only deletes WP worktrees, never main repo or other features
- Nested directories are cleaned up correctly
- Symlinks are not followed during cleanup
- Cleanup handles various edge cases safely

These tests ensure worktree cleanup operations never accidentally
delete user data outside the target worktrees.
"""
import pytest
import subprocess
import os
import shutil
from pathlib import Path

from .conftest import create_worktree


# =============================================================================
# T051: Cleanup Boundary Tests
# =============================================================================

class TestWorktreeCleanupBoundaries:
    """Test worktree cleanup only affects target worktrees."""

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_cleanup_only_deletes_wp_worktrees(self, multi_feature_project):
        """Cleanup deletes only WP worktrees, not main repo or other features."""
        project = multi_feature_project

        # Create worktrees for feature 001
        wt1 = create_worktree(project, "001-feature-001", "WP01")
        wt2 = create_worktree(project, "001-feature-001", "WP02")

        # Create worktree for feature 002 (should not be touched)
        wt3 = create_worktree(project, "002-feature-002", "WP01")

        # Create marker files in each worktree
        (wt1 / "marker1.txt").write_text("WP01 data")
        (wt2 / "marker2.txt").write_text("WP02 data")
        (wt3 / "marker3.txt").write_text("Other feature data")

        # Create marker in main repo (should never be touched)
        main_marker = project / "main-repo-marker.txt"
        main_marker.write_text("Main repo data - MUST NOT DELETE")

        # Verify all exist
        assert wt1.exists()
        assert wt2.exists()
        assert wt3.exists()
        assert main_marker.exists()

        # Manually cleanup worktrees for feature 001
        for wp_id in ["WP01", "WP02"]:
            wt_path = project / ".worktrees" / f"001-feature-001-{wp_id}"
            if wt_path.exists():
                subprocess.run(
                    ["git", "worktree", "remove", "--force", str(wt_path)],
                    cwd=project,
                    capture_output=True
                )

        # Feature 001 worktrees should be deleted
        assert not wt1.exists(), "WP01 worktree should be deleted"
        assert not wt2.exists(), "WP02 worktree should be deleted"

        # Other feature and main repo should be untouched
        assert wt3.exists(), "Other feature worktree incorrectly deleted"
        assert (wt3 / "marker3.txt").exists(), "Other feature data incorrectly deleted"
        assert main_marker.exists(), "Main repo file incorrectly deleted"
        assert main_marker.read_text() == "Main repo data - MUST NOT DELETE"

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_cleanup_nested_directories(self, multi_feature_project):
        """Cleanup handles nested directory structures correctly."""
        project = multi_feature_project

        # Create worktree with nested structure
        wt = create_worktree(project, "001-feature-001", "WP01")

        # Create deeply nested files
        nested = wt / "deeply" / "nested" / "directory" / "structure"
        nested.mkdir(parents=True)
        (nested / "file.txt").write_text("Nested data")
        (nested / "another.txt").write_text("More data")

        # Create files at various levels
        (wt / "deeply" / "level1.txt").write_text("Level 1")
        (wt / "deeply" / "nested" / "level2.txt").write_text("Level 2")

        # Verify nested structure exists
        assert (nested / "file.txt").exists()
        assert (wt / "deeply" / "level1.txt").exists()

        # Cleanup worktree
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(wt)],
            cwd=project,
            capture_output=True
        )

        # Entire worktree should be deleted including nested structure
        assert not wt.exists(), "Worktree not fully deleted"
        assert not nested.exists(), "Nested directories not deleted"

    @pytest.mark.functional
    @pytest.mark.data_loss
    @pytest.mark.adversarial
    def test_cleanup_does_not_follow_symlinks(self, multi_feature_project, tmp_path):
        """Cleanup doesn't follow symlinks outside worktree (security)."""
        project = multi_feature_project

        # Create worktree
        wt = create_worktree(project, "001-feature-001", "WP01")

        # Create external file outside the project (simulating external data)
        external_dir = tmp_path / "external-data"
        external_dir.mkdir()
        external_file = external_dir / "important-data.txt"
        external_file.write_text("CRITICAL: External data that must never be deleted")

        # Create symlink in worktree pointing to external file
        symlink = wt / "link-to-external"
        try:
            symlink.symlink_to(external_file)
        except OSError:
            # Symlinks might not be supported on some systems/configs
            pytest.skip("Symlinks not supported on this system")

        # Verify setup
        assert external_file.exists()
        assert symlink.exists()
        assert symlink.is_symlink()

        # Cleanup worktree
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(wt)],
            cwd=project,
            capture_output=True
        )

        # Worktree deleted, but external file MUST be preserved
        assert not wt.exists(), "Worktree not deleted"
        assert external_file.exists(), "External file incorrectly deleted via symlink!"
        assert external_file.read_text() == "CRITICAL: External data that must never be deleted"

    @pytest.mark.functional
    @pytest.mark.data_loss
    @pytest.mark.adversarial
    def test_cleanup_does_not_follow_symlinked_directories(
        self, multi_feature_project, tmp_path
    ):
        """Cleanup doesn't follow symlinked directories."""
        project = multi_feature_project

        # Create worktree
        wt = create_worktree(project, "001-feature-001", "WP01")

        # Create external directory with data
        external_dir = tmp_path / "external-important-dir"
        external_dir.mkdir()
        (external_dir / "file1.txt").write_text("External file 1")
        (external_dir / "file2.txt").write_text("External file 2")

        # Symlink external directory into worktree
        symlink_dir = wt / "external-link"
        try:
            symlink_dir.symlink_to(external_dir)
        except OSError:
            pytest.skip("Symlinks not supported on this system")

        # Verify setup
        assert (external_dir / "file1.txt").exists()
        assert symlink_dir.exists()

        # Cleanup worktree
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(wt)],
            cwd=project,
            capture_output=True
        )

        # External directory MUST be preserved
        assert not wt.exists()
        assert external_dir.exists(), "External directory incorrectly deleted!"
        assert (external_dir / "file1.txt").exists()
        assert (external_dir / "file2.txt").exists()

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_cleanup_preserves_kitty_specs_in_main_repo(self, multi_feature_project):
        """Cleanup never touches kitty-specs in main repo."""
        project = multi_feature_project

        # Create worktree
        wt = create_worktree(project, "001-feature-001", "WP01")

        # Get paths to main repo kitty-specs
        main_specs = project / "kitty-specs"
        main_feature = main_specs / "001-feature-001"
        main_tasks = main_feature / "tasks.md"

        # Record original content
        original_content = main_tasks.read_text()

        # Modify file in worktree (if it exists there)
        # Note: worktrees share the same content, this tests the path handling
        wt_marker = wt / "worktree-marker.txt"
        wt_marker.write_text("Worktree-specific file")

        # Cleanup worktree
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(wt)],
            cwd=project,
            capture_output=True
        )

        # Main repo kitty-specs must be completely intact
        assert main_specs.exists()
        assert main_feature.exists()
        assert main_tasks.exists()
        assert main_tasks.read_text() == original_content

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_cleanup_multiple_worktrees_independently(self, multi_feature_project):
        """Cleanup of one worktree doesn't affect siblings."""
        project = multi_feature_project

        # Create multiple worktrees for same feature
        wt1 = create_worktree(project, "001-feature-001", "WP01")
        wt2 = create_worktree(project, "001-feature-001", "WP02")
        wt3 = create_worktree(project, "001-feature-001", "WP03")

        # Create unique content in each
        (wt1 / "wp01-data.txt").write_text("WP01 unique data")
        (wt2 / "wp02-data.txt").write_text("WP02 unique data")
        (wt3 / "wp03-data.txt").write_text("WP03 unique data")

        # Cleanup only WP02
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(wt2)],
            cwd=project,
            capture_output=True
        )

        # WP02 should be gone
        assert not wt2.exists()

        # WP01 and WP03 should be intact
        assert wt1.exists()
        assert wt3.exists()
        assert (wt1 / "wp01-data.txt").read_text() == "WP01 unique data"
        assert (wt3 / "wp03-data.txt").read_text() == "WP03 unique data"

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_cleanup_nonexistent_worktree_is_safe(self, multi_feature_project):
        """Cleanup of nonexistent worktree doesn't cause errors."""
        project = multi_feature_project

        # Try to cleanup worktree that doesn't exist
        fake_wt = project / ".worktrees" / "001-feature-001-WP99"
        assert not fake_wt.exists()

        # This should not raise an error
        result = subprocess.run(
            ["git", "worktree", "remove", "--force", str(fake_wt)],
            cwd=project,
            capture_output=True,
            text=True
        )

        # It's OK if this returns non-zero (worktree doesn't exist)
        # The important thing is it doesn't delete anything else
        assert project.exists()
        assert (project / "kitty-specs").exists()

    @pytest.mark.functional
    @pytest.mark.data_loss
    @pytest.mark.adversarial
    def test_cleanup_with_hidden_files(self, multi_feature_project):
        """Cleanup properly removes hidden files (dotfiles)."""
        project = multi_feature_project

        # Create worktree
        wt = create_worktree(project, "001-feature-001", "WP01")

        # Create hidden files
        (wt / ".hidden-file").write_text("Hidden data")
        hidden_dir = wt / ".hidden-dir"
        hidden_dir.mkdir()
        (hidden_dir / "nested-hidden.txt").write_text("Nested hidden")

        # Verify hidden files exist
        assert (wt / ".hidden-file").exists()
        assert (hidden_dir / "nested-hidden.txt").exists()

        # Cleanup
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(wt)],
            cwd=project,
            capture_output=True
        )

        # Everything including hidden files should be gone
        assert not wt.exists()
        assert not (wt / ".hidden-file").exists()
        assert not hidden_dir.exists()

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_worktree_path_validation(self, multi_feature_project):
        """Worktree paths must be within .worktrees directory."""
        project = multi_feature_project

        # Valid worktree path
        valid_wt = project / ".worktrees" / "001-feature-001-WP01"

        # These paths should NOT be treated as valid worktrees
        invalid_paths = [
            project / "kitty-specs",  # Main repo directory
            project / ".kittify",  # Config directory
            project,  # Project root
            project.parent,  # Parent directory
        ]

        for invalid_path in invalid_paths:
            # Attempting to remove these as worktrees should fail
            # or not actually delete them
            if invalid_path.exists():
                original_exists = invalid_path.exists()
                result = subprocess.run(
                    ["git", "worktree", "remove", "--force", str(invalid_path)],
                    cwd=project,
                    capture_output=True,
                    text=True
                )
                # Either command fails, or if it "succeeds" the path should still exist
                # because it's not actually a worktree
                # Note: git worktree remove will fail for non-worktree paths
                assert invalid_path.exists(), f"Path {invalid_path} was incorrectly deleted!"
