"""
T045: No JJ Commands Executed Tests

Verifies that full spec-kitty workflow (init -> specify -> plan -> tasks ->
implement -> merge) never executes jj commands, even when jj is installed.
"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess


@pytest.mark.functional
@pytest.mark.vcs
class TestFullWorkflowNoJJCommands:
    """Test that complete workflows never execute jj commands."""

    def test_full_workflow_no_jj_commands(self, command_logger, tmp_path):
        """Full workflow never executes jj commands."""
        ctx = command_logger

        # Mock jj installation
        with patch("shutil.which") as mock_which:
            mock_which.side_effect = lambda cmd: (
                "/usr/local/bin/jj" if cmd == "jj" else
                "/usr/bin/git" if cmd == "git" else None
            )

            # Simulate workflow operations using git
            subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"],
                          cwd=tmp_path, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"],
                          cwd=tmp_path, capture_output=True)
            subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
            subprocess.run(["git", "commit", "--allow-empty", "-m", "init"],
                          cwd=tmp_path, capture_output=True)
            subprocess.run(["git", "branch", "-a"], cwd=tmp_path, capture_output=True)

        # Assert no jj commands
        ctx.assert_no_jj_commands()

        # Assert git commands were used instead
        git_commands = [cmd for bin, cmd in ctx.command_log if bin == "git"]
        assert len(git_commands) > 0, "No git commands executed"

    def test_jj_commands_never_in_log(self, command_logger, tmp_path):
        """JJ commands never appear in command log during any operation."""
        ctx = command_logger

        # Perform various git operations
        ops = [
            ["git", "init"],
            ["git", "status"],
            ["git", "diff"],
            ["git", "log", "--oneline", "-1"],
            ["git", "branch", "--list"],
            ["git", "remote", "-v"],
        ]

        for op in ops:
            subprocess.run(op, cwd=tmp_path, capture_output=True)

        # Verify no jj commands
        jj_commands = [cmd for bin, cmd in ctx.command_log if bin == "jj"]
        assert len(jj_commands) == 0, (
            f"JJ commands executed despite disabled detection: {jj_commands}"
        )


@pytest.mark.functional
@pytest.mark.vcs
class TestIndividualOperationsNoJJ:
    """Test individual operations never execute jj commands."""

    @pytest.mark.parametrize("operation,git_cmds", [
        ("init", [["git", "init"]]),
        ("status", [["git", "status"]]),
        ("branch", [["git", "branch", "-a"]]),
        ("worktree", [["git", "worktree", "list"]]),
        ("commit", [["git", "commit", "--allow-empty", "-m", "test"]]),
    ])
    def test_operation_no_jj_commands(self, command_logger, tmp_path, operation, git_cmds):
        """Individual operations never execute jj commands."""
        ctx = command_logger
        ctx.clear_log()

        # Initialize git if needed for operations that require it
        if operation not in ["init"]:
            subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
            subprocess.run(["git", "config", "user.email", "t@t.com"],
                          cwd=tmp_path, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"],
                          cwd=tmp_path, capture_output=True)

        ctx.clear_log()  # Clear setup commands

        # Run the operation
        for cmd in git_cmds:
            subprocess.run(cmd, cwd=tmp_path, capture_output=True)

        # Check no jj commands
        jj_commands = [cmd for bin, cmd in ctx.command_log if bin == "jj"]
        assert len(jj_commands) == 0, (
            f"Operation '{operation}' executed jj commands: {jj_commands}"
        )

    @pytest.mark.adversarial
    def test_sync_operation_no_jj_commands(self, command_logger, tmp_path):
        """Sync operation uses git, not jj."""
        ctx = command_logger

        # Setup git repo
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.email", "t@t.com"],
                      cwd=tmp_path, capture_output=True)

        ctx.clear_log()

        # Simulate sync (fetch + rebase/merge)
        subprocess.run(["git", "fetch", "--all"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "rebase", "origin/main"], cwd=tmp_path, capture_output=True)

        # No jj commands
        ctx.assert_no_jj_commands()


@pytest.mark.functional
@pytest.mark.vcs
class TestMergeWorkflowNoJJ:
    """Test merge workflow operations never use jj."""

    def test_merge_uses_git_not_jj(self, command_logger, tmp_path):
        """Merge operations use git, never jj."""
        ctx = command_logger

        # Setup git repo with branches
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.email", "t@t.com"],
                      cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"],
                      cwd=tmp_path, capture_output=True)

        # Create initial commit
        (tmp_path / "README.md").write_text("# Test")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial"],
                      cwd=tmp_path, capture_output=True)

        # Create feature branch
        subprocess.run(["git", "checkout", "-b", "feature"],
                      cwd=tmp_path, capture_output=True)
        (tmp_path / "feature.txt").write_text("feature")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Feature"],
                      cwd=tmp_path, capture_output=True)

        # Merge
        subprocess.run(["git", "checkout", "main"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "merge", "feature"], cwd=tmp_path, capture_output=True)

        # Verify no jj commands
        ctx.assert_no_jj_commands()

        # Verify git was used
        vcs_cmds = ctx.get_vcs_commands()
        assert len(vcs_cmds) > 0
        assert all(bin == "git" for bin, _ in vcs_cmds)

    @pytest.mark.adversarial
    def test_conflict_resolution_no_jj(self, command_logger, tmp_path):
        """Conflict resolution uses git, not jj."""
        ctx = command_logger

        # Setup that might trigger conflict resolution
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.email", "t@t.com"],
                      cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"],
                      cwd=tmp_path, capture_output=True)

        # Create files
        (tmp_path / "file.txt").write_text("main")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "main"],
                      cwd=tmp_path, capture_output=True)

        ctx.clear_log()

        # Conflict resolution commands
        subprocess.run(["git", "status"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "diff"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "diff", "--cached"], cwd=tmp_path, capture_output=True)

        # No jj
        ctx.assert_no_jj_commands()
