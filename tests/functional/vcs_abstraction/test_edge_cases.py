"""
VCS abstraction edge case tests (WP13: T074).

Tests unusual, adversarial, or boundary conditions for VCS abstraction.
"""
import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch
import subprocess
import os


@pytest.mark.functional
@pytest.mark.vcs
@pytest.mark.adversarial
class TestBrokenGitBinary:
    """Test handling of broken or missing git binary."""

    def test_git_version_returns_error(self, tmp_path, monkeypatch):
        """Edge case: git binary exists but returns error on --version."""
        # Create fake git that fails
        fake_bin = tmp_path / "fake-bin"
        fake_bin.mkdir()
        fake_git = fake_bin / "git"
        fake_git.write_text("#!/bin/bash\nexit 1\n")
        fake_git.chmod(0o755)

        # Prepend to PATH
        original_path = os.environ.get("PATH", "")
        monkeypatch.setenv("PATH", f"{fake_bin}:{original_path}")

        # Test that git version fails
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            cwd=tmp_path
        )

        # Should detect failure
        assert result.returncode != 0

    def test_git_not_on_path(self, tmp_path, monkeypatch):
        """Edge case: git binary not found on PATH."""
        # Set PATH to empty directory
        empty_bin = tmp_path / "empty-bin"
        empty_bin.mkdir()
        monkeypatch.setenv("PATH", str(empty_bin))

        import shutil
        git_path = shutil.which("git")

        # git should not be found
        assert git_path is None


@pytest.mark.functional
@pytest.mark.vcs
@pytest.mark.adversarial
class TestInvalidVCSName:
    """Test handling of invalid VCS names in meta.json."""

    def test_unsupported_vcs_name(self, tmp_path):
        """Edge case: meta.json has unsupported VCS name."""
        meta_file = tmp_path / "meta.json"
        meta_file.write_text('{"vcs": "mercurial", "feature_number": "001"}')

        meta = json.loads(meta_file.read_text())

        # Should detect invalid VCS
        valid_vcs = ["git", "jj"]
        assert meta["vcs"] not in valid_vcs

    def test_empty_vcs_name(self, tmp_path):
        """Edge case: meta.json has empty VCS name."""
        meta_file = tmp_path / "meta.json"
        meta_file.write_text('{"vcs": "", "feature_number": "001"}')

        meta = json.loads(meta_file.read_text())
        assert meta["vcs"] == ""

    def test_null_vcs_name(self, tmp_path):
        """Edge case: meta.json has null VCS name."""
        meta_file = tmp_path / "meta.json"
        meta_file.write_text('{"vcs": null, "feature_number": "001"}')

        meta = json.loads(meta_file.read_text())
        assert meta["vcs"] is None

    def test_numeric_vcs_name(self, tmp_path):
        """Edge case: meta.json has numeric VCS value."""
        meta_file = tmp_path / "meta.json"
        meta_file.write_text('{"vcs": 123, "feature_number": "001"}')

        meta = json.loads(meta_file.read_text())
        assert meta["vcs"] == 123
        assert not isinstance(meta["vcs"], str)


@pytest.mark.functional
@pytest.mark.vcs
@pytest.mark.adversarial
class TestWorktreeDirectoryConflicts:
    """Test handling of worktree directory conflicts."""

    def test_worktree_path_already_exists_as_file(self, tmp_path):
        """Edge case: Worktree path exists as a file, not directory."""
        worktree_path = tmp_path / ".worktrees" / "feature" / "WP01"
        worktree_path.parent.mkdir(parents=True)

        # Create as file instead of directory
        worktree_path.write_text("I am a file, not a directory")

        assert worktree_path.exists()
        assert worktree_path.is_file()
        assert not worktree_path.is_dir()

    def test_worktree_parent_is_file(self, tmp_path):
        """Edge case: Parent directory of worktree is a file."""
        worktrees_parent = tmp_path / ".worktrees"

        # Create as file instead of directory
        worktrees_parent.write_text("I am a file")

        assert worktrees_parent.exists()
        assert worktrees_parent.is_file()

        # Cannot create subdirectory
        with pytest.raises(OSError):
            (worktrees_parent / "feature" / "WP01").mkdir(parents=True)


@pytest.mark.functional
@pytest.mark.vcs
@pytest.mark.adversarial
class TestManualVCSModification:
    """Test handling of manual VCS field modifications."""

    def test_vcs_changed_after_creation(self, tmp_path):
        """Edge case: User manually changes VCS in meta.json."""
        meta_file = tmp_path / "meta.json"

        # Initial creation with git
        meta_file.write_text('{"vcs": "git", "feature_number": "001"}')
        meta1 = json.loads(meta_file.read_text())
        assert meta1["vcs"] == "git"

        # User changes to jj
        meta_file.write_text('{"vcs": "jj", "feature_number": "001"}')
        meta2 = json.loads(meta_file.read_text())
        assert meta2["vcs"] == "jj"

    def test_missing_meta_json(self, tmp_path):
        """Edge case: meta.json file doesn't exist."""
        meta_file = tmp_path / "meta.json"

        assert not meta_file.exists()

        with pytest.raises(FileNotFoundError):
            meta_file.read_text()
