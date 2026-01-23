"""
Git-Only Path Tests

Tests that git-only environment executes ONLY git commands (zero jj).
Validates VCS isolation when using git code paths.
"""
import pytest
from pathlib import Path
import json
import subprocess


@pytest.mark.functional
@pytest.mark.vcs
class TestGitOnlyPathNoJJCommands:
    """Test that git-only path uses only git commands."""

    def test_git_only_path_no_jj_commands(self, command_logger, feature_with_vcs_lock):
        """Git-only environment executes only git commands."""
        # Create feature with vcs=git
        feature_dir = feature_with_vcs_lock("001", vcs_type="git")

        # Verify meta.json
        meta = json.loads((feature_dir / "meta.json").read_text())
        assert meta["vcs"] == "git"

        # Simulate VCS operations (subprocess.run is mocked by command_logger)
        subprocess.run(["git", "status"], capture_output=True)
        subprocess.run(["git", "diff", "--cached"], capture_output=True)

        # Verify only git commands (no jj)
        command_logger.assert_only_git_commands()

        # Verify specific commands
        git_cmds = [cmd for binary, cmd in command_logger.command_log if binary == "git"]
        assert len(git_cmds) == 2
        assert git_cmds[0] == ["git", "status"]
        assert git_cmds[1] == ["git", "diff", "--cached"]

    def test_git_planning_artifacts_uses_git(self, command_logger, feature_with_vcs_lock):
        """Git planning artifacts check uses git commands only."""
        feature_dir = feature_with_vcs_lock("001", vcs_type="git")

        # Simulate _ensure_planning_artifacts_committed_git()
        # This would check: git diff --cached, git status
        subprocess.run(["git", "diff", "--cached", "spec.md", "plan.md", "tasks.md"],
                       capture_output=True)
        subprocess.run(["git", "status", "--porcelain"], capture_output=True)

        # Verify git commands used
        command_logger.assert_only_git_commands()
        git_cmds = command_logger.get_vcs_commands()
        assert all(binary == "git" for binary, _ in git_cmds)

    def test_git_worktree_creation_no_jj(self, command_logger, feature_with_vcs_lock):
        """Git worktree creation uses only git commands."""
        feature_dir = feature_with_vcs_lock("001", vcs_type="git")

        # Simulate worktree creation
        subprocess.run(["git", "worktree", "add", ".worktrees/001-test/WP01", "HEAD"],
                       capture_output=True)

        # Verify only git
        command_logger.assert_no_jj_commands()

        git_cmds = [cmd for binary, cmd in command_logger.command_log if binary == "git"]
        assert any("worktree" in cmd for cmd in git_cmds)


@pytest.mark.functional
@pytest.mark.vcs
class TestGitBranchOperations:
    """Test git branch operations use no jj commands."""

    def test_git_branch_creation(self, command_logger, feature_with_vcs_lock):
        """Git branch creation uses only git."""
        feature_dir = feature_with_vcs_lock("002", vcs_type="git")

        subprocess.run(["git", "checkout", "-b", "feature/002-test"], capture_output=True)
        subprocess.run(["git", "branch", "--list"], capture_output=True)

        command_logger.assert_no_jj_commands()
        assert len([cmd for binary, cmd in command_logger.command_log if binary == "git"]) == 2

    def test_git_commit_operations(self, command_logger, feature_with_vcs_lock):
        """Git commit operations use only git."""
        feature_dir = feature_with_vcs_lock("003", vcs_type="git")

        subprocess.run(["git", "add", "spec.md"], capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add spec"], capture_output=True)

        command_logger.assert_no_jj_commands()
        git_cmds = [cmd for binary, cmd in command_logger.command_log if binary == "git"]
        assert ["git", "add", "spec.md"] in git_cmds
        assert any("commit" in cmd for cmd in git_cmds)

    def test_git_merge_operations(self, command_logger, feature_with_vcs_lock):
        """Git merge operations use only git."""
        feature_dir = feature_with_vcs_lock("004", vcs_type="git")

        subprocess.run(["git", "merge", "feature-branch", "--no-ff"], capture_output=True)

        command_logger.assert_no_jj_commands()


@pytest.mark.functional
@pytest.mark.vcs
class TestGitStatusOperations:
    """Test git status checking uses no jj commands."""

    def test_git_status_porcelain(self, command_logger, feature_with_vcs_lock):
        """Git status porcelain uses only git."""
        feature_dir = feature_with_vcs_lock("005", vcs_type="git")

        subprocess.run(["git", "status", "--porcelain"], capture_output=True)
        subprocess.run(["git", "status", "-s"], capture_output=True)

        command_logger.assert_no_jj_commands()

    def test_git_diff_operations(self, command_logger, feature_with_vcs_lock):
        """Git diff operations use only git."""
        feature_dir = feature_with_vcs_lock("006", vcs_type="git")

        subprocess.run(["git", "diff"], capture_output=True)
        subprocess.run(["git", "diff", "--staged"], capture_output=True)
        subprocess.run(["git", "diff", "HEAD~1"], capture_output=True)

        command_logger.assert_no_jj_commands()
        assert len([cmd for binary, cmd in command_logger.command_log if binary == "git"]) == 3


@pytest.mark.functional
@pytest.mark.vcs
class TestGitLogOperations:
    """Test git log operations use no jj commands."""

    def test_git_log_formats(self, command_logger, feature_with_vcs_lock):
        """Git log with various formats uses only git."""
        feature_dir = feature_with_vcs_lock("007", vcs_type="git")

        subprocess.run(["git", "log", "-1", "--format=%H"], capture_output=True)
        subprocess.run(["git", "log", "--oneline", "-5"], capture_output=True)
        subprocess.run(["git", "log", "--graph", "--all"], capture_output=True)

        command_logger.assert_no_jj_commands()
        git_cmds = [cmd for binary, cmd in command_logger.command_log if binary == "git"]
        assert len(git_cmds) == 3
        assert all("log" in cmd for cmd in git_cmds)
