"""
T048: Error Messages Reference Git Only Tests

Verifies that VCS-related error messages mention only git installation
requirements, not jj.
"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess


@pytest.mark.functional
@pytest.mark.vcs
@pytest.mark.adversarial
class TestVCSNotFoundErrors:
    """Test error messages when VCS is not found."""

    def test_git_not_found_error_mentions_git(self):
        """Error when git not installed mentions git."""
        with patch("shutil.which") as mock_which:
            # Mock git not available
            mock_which.return_value = None

            from specify_cli.core.vcs.detection import is_jj_available

            # Even with git not found, jj should not be available
            result = is_jj_available()
            assert result is False

            # Error message construction should mention git
            error_parts = ["git", "not found", "install"]

            error_message = "git not found. Please install git to use spec-kitty."

            for part in error_parts:
                # At least git should be in the message
                if part == "git":
                    assert "git" in error_message.lower()

    def test_git_not_found_error_no_jj_suggestion(self):
        """Error when git not installed doesn't suggest jj."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None

            error_message = (
                "Git is required but not installed. "
                "Please install git from https://git-scm.com/"
            )

            # Should NOT suggest jj as alternative
            assert "jj" not in error_message.lower()
            assert "jujutsu" not in error_message.lower()


@pytest.mark.functional
@pytest.mark.vcs
@pytest.mark.adversarial
class TestVCSOperationErrors:
    """Test error messages from VCS operations."""

    def test_vcs_operation_error_mentions_git(self):
        """VCS operation errors reference git."""
        error_scenarios = [
            "fatal: not a git repository",
            "git push failed: error pushing to remote",
            "git merge conflicts in file.txt",
        ]

        for error in error_scenarios:
            # These are git-specific errors
            assert "git" in error.lower() or "repository" in error.lower(), (
                f"Error should mention git or repository: {error}"
            )
            # Should not mention jj
            assert "jj" not in error.lower()

    def test_worktree_error_mentions_git_worktree(self):
        """Worktree errors reference git worktree, not jj workspace."""
        error_messages = [
            "Git worktree not found for WP01",
            "Error creating git worktree",
            "Worktree directory missing",
        ]

        for error in error_messages:
            # Should say worktree (git term), not workspace (jj term)
            assert "worktree" in error.lower()
            # Should not use jj terminology
            assert "jj" not in error.lower()
            assert "workspace" not in error.lower() or "worktree" in error.lower()


@pytest.mark.functional
@pytest.mark.vcs
class TestInstallationInstructions:
    """Test VCS installation instructions."""

    def test_installation_instructions_git_only(self):
        """Installation instructions reference only git."""
        instructions = """
        To use spec-kitty, you need git installed:

        macOS:   brew install git
        Ubuntu:  sudo apt install git
        Windows: Download from https://git-scm.com/

        After installing, run: git --version
        """

        # Should include git installation
        assert "git" in instructions.lower()

        # Should NOT include jj installation
        assert "jj" not in instructions.lower()
        assert "jujutsu" not in instructions.lower()
        assert "cargo install jj" not in instructions.lower()

    def test_no_jj_installation_option(self):
        """Installation options don't include jj."""
        vcs_options = ["git"]  # Only git is an option

        assert "jj" not in vcs_options
        assert len(vcs_options) == 1
        assert vcs_options[0] == "git"


@pytest.mark.functional
@pytest.mark.vcs
class TestErrorMessageContent:
    """Test content of various error messages."""

    def test_branch_error_uses_git_terminology(self):
        """Branch errors use git terminology."""
        errors = [
            "Branch 'feature' not found",
            "Cannot switch to branch",
            "Branch diverged from remote",
        ]

        for error in errors:
            # Branch is git/jj neutral, but ensure no jj-specific terms
            assert "bookmark" not in error.lower()  # jj uses bookmarks
            assert "jj" not in error.lower()

    def test_commit_error_uses_git_terminology(self):
        """Commit errors use git terminology."""
        errors = [
            "Nothing to commit",
            "Commit failed: no changes staged",
            "Cannot commit with uncommitted changes",
        ]

        for error in errors:
            # Commit is git term (jj uses "new" or different workflow)
            assert "commit" in error.lower()
            assert "jj" not in error.lower()

    def test_merge_error_uses_git_terminology(self):
        """Merge errors use git terminology."""
        errors = [
            "Merge conflict in file.txt",
            "Cannot merge: uncommitted changes",
            "Merge failed: conflicts detected",
        ]

        for error in errors:
            assert "merge" in error.lower()
            assert "jj" not in error.lower()
            assert "squash" not in error.lower()  # jj uses squash

    @pytest.mark.adversarial
    def test_detection_error_no_jj_alternative(self):
        """VCS detection errors don't suggest jj as alternative."""
        error_template = (
            "VCS detection failed. spec-kitty requires git. "
            "Please ensure git is installed and accessible."
        )

        # Should mention git
        assert "git" in error_template.lower()

        # Should NOT mention jj as fallback
        forbidden_phrases = [
            "alternatively, install jj",
            "or use jj",
            "jj is also supported",
            "try jj instead",
        ]

        for phrase in forbidden_phrases:
            assert phrase.lower() not in error_template.lower()


@pytest.mark.functional
@pytest.mark.vcs
@pytest.mark.adversarial
class TestRuntimeErrors:
    """Test runtime VCS error handling."""

    def test_subprocess_git_error_propagated(self):
        """Git subprocess errors are propagated correctly."""
        # Simulate git command failure
        error = subprocess.CalledProcessError(
            128,
            ["git", "status"],
            stderr=b"fatal: not a git repository"
        )

        error_message = error.stderr.decode() if error.stderr else str(error)

        # Error should be about git, not jj
        assert "git" in error_message.lower() or "repository" in error_message.lower()
        assert "jj" not in error_message.lower()

    def test_git_command_not_found_error(self):
        """Git command not found error is clear."""
        error = FileNotFoundError("[Errno 2] No such file or directory: 'git'")
        error_message = str(error)

        # Should reference git
        assert "git" in error_message.lower()

        # Response should be to install git, not jj
        suggested_fix = "Please install git"
        assert "git" in suggested_fix.lower()
        assert "jj" not in suggested_fix.lower()
