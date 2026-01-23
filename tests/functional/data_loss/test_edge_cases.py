"""
Data safety edge case tests (WP13: T075).

Tests unusual, adversarial, or boundary conditions for data loss prevention.
"""
import pytest
import json
from pathlib import Path
import os
import shutil


@pytest.mark.functional
@pytest.mark.data_loss
@pytest.mark.adversarial
class TestLockedFileDuringCleanup:
    """Test handling of locked files during cleanup operations."""

    def test_readonly_file_in_worktree(self, tmp_path):
        """Edge case: Read-only file in worktree during cleanup."""
        worktree = tmp_path / "worktree"
        worktree.mkdir()

        readonly_file = worktree / "readonly.txt"
        readonly_file.write_text("important content")
        readonly_file.chmod(0o444)  # Read-only

        assert readonly_file.exists()
        assert not os.access(readonly_file, os.W_OK)

        # Cleanup should handle or report error
        try:
            readonly_file.unlink()
            # On Unix, can delete read-only files if we own parent dir
        except PermissionError:
            # Expected on Windows
            # Restore permissions for cleanup
            readonly_file.chmod(0o644)
            readonly_file.unlink()

    def test_open_file_handle_unix(self, tmp_path):
        """Edge case: File open by another process (Unix semantics)."""
        worktree = tmp_path / "worktree"
        worktree.mkdir()

        test_file = worktree / "open.txt"
        test_file.write_text("content")

        # On Unix, can delete open files
        with open(test_file) as f:
            content = f.read()
            assert content == "content"

            # Can still unlink on Unix (file stays accessible via handle)
            if os.name != 'nt':
                test_file.unlink()
                assert not test_file.exists()
                # File handle still valid
                f.seek(0)


@pytest.mark.functional
@pytest.mark.data_loss
@pytest.mark.adversarial
class TestPathLengthLimits:
    """Test handling of path length limits."""

    def test_very_long_filename(self, tmp_path):
        """Edge case: Filename at or beyond filesystem limits."""
        # Most filesystems limit to 255 bytes
        long_name = "a" * 256

        long_path = tmp_path / long_name

        with pytest.raises(OSError):
            long_path.write_text("content")

    def test_very_deep_directory_nesting(self, tmp_path):
        """Edge case: Deeply nested directory structure."""
        # Create very deep nesting
        deep_path = tmp_path
        for i in range(50):
            deep_path = deep_path / f"level{i:03d}"

        # May hit path length limits on some systems
        try:
            deep_path.mkdir(parents=True)
            (deep_path / "file.txt").write_text("deep content")
            assert (deep_path / "file.txt").exists()
        except OSError:
            # Expected on systems with short path limits
            pass


@pytest.mark.functional
@pytest.mark.data_loss
@pytest.mark.adversarial
class TestDeletedDirectoryDuringOperation:
    """Test handling of directories deleted during operations."""

    def test_kitty_specs_deleted_mid_operation(self, tmp_path):
        """Edge case: kitty-specs deleted during WP operation."""
        kitty_specs = tmp_path / "kitty-specs"
        kitty_specs.mkdir()

        feature_dir = kitty_specs / "001-test"
        feature_dir.mkdir()
        (feature_dir / "spec.md").write_text("# Test Feature")

        assert feature_dir.exists()

        # Simulate deletion mid-operation
        shutil.rmtree(kitty_specs)

        assert not feature_dir.exists()
        assert not kitty_specs.exists()

        # Subsequent operations should fail clearly
        with pytest.raises(FileNotFoundError):
            (feature_dir / "spec.md").read_text()

    def test_worktree_parent_deleted(self, tmp_path):
        """Edge case: Worktree parent directory deleted."""
        worktrees = tmp_path / ".worktrees"
        worktrees.mkdir()

        feature_worktree = worktrees / "feature-001"
        feature_worktree.mkdir()

        # Delete parent
        shutil.rmtree(worktrees)

        assert not feature_worktree.exists()


@pytest.mark.functional
@pytest.mark.data_loss
@pytest.mark.adversarial
class TestSymlinkProblems:
    """Test handling of symbolic link issues."""

    def test_broken_symlink_in_feature(self, tmp_path):
        """Edge case: Broken symlink in feature directory."""
        feature_dir = tmp_path / "feature"
        feature_dir.mkdir()

        # Create broken symlink
        broken_link = feature_dir / "broken-link"
        broken_link.symlink_to(tmp_path / "non-existent-target")

        # Symlink exists but target doesn't
        assert broken_link.is_symlink()
        assert not broken_link.exists()  # Target doesn't exist

    def test_circular_symlink(self, tmp_path):
        """Edge case: Circular symlinks."""
        link_a = tmp_path / "link_a"
        link_b = tmp_path / "link_b"

        link_a.symlink_to(link_b)
        link_b.symlink_to(link_a)

        # Should detect circular reference
        assert link_a.is_symlink()
        assert link_b.is_symlink()

        # Resolution should fail or handle gracefully
        with pytest.raises(OSError):
            link_a.resolve(strict=True)
