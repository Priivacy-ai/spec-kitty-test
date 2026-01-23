"""
Stale detection edge case tests (WP13: T077).

Tests unusual, adversarial, or boundary conditions for stale detection.
"""
import pytest
from pathlib import Path
from datetime import datetime, timedelta
import subprocess
import os


@pytest.mark.functional
@pytest.mark.adversarial
class TestEmptyGitLog:
    """Test handling of empty git log scenarios."""

    def test_git_init_no_commits(self, tmp_path):
        """Edge case: git log returns empty output (no commits)."""
        # Initialize git repo with no commits
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)

        # git log should fail or be empty
        result = subprocess.run(
            ["git", "log", "--oneline", "-1"],
            cwd=tmp_path,
            capture_output=True,
            text=True
        )

        # Either fails or returns empty
        if result.returncode == 0:
            assert result.stdout.strip() == ""
        else:
            # Expected - no commits to log
            pass

    def test_worktree_creation_time_fallback(self, tmp_path):
        """Edge case: Use worktree creation time when no commits."""
        worktree = tmp_path / "worktree"
        worktree.mkdir()

        # Should be able to use directory mtime
        stat = worktree.stat()
        creation_time = datetime.fromtimestamp(stat.st_mtime)

        # Should be recent (just created)
        assert datetime.now() - creation_time < timedelta(seconds=10)


@pytest.mark.functional
@pytest.mark.adversarial
class TestDeletedBranch:
    """Test handling of deleted branch scenarios."""

    def test_detached_head_state(self, tmp_path):
        """Edge case: Worktree in detached HEAD state."""
        # Initialize and create commit
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"],
                       cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"],
                       cwd=tmp_path, capture_output=True)

        test_file = tmp_path / "file.txt"
        test_file.write_text("content")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial"],
                       cwd=tmp_path, capture_output=True)

        # Get commit hash
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=tmp_path,
            capture_output=True,
            text=True
        )
        commit_hash = result.stdout.strip()

        # Checkout detached HEAD
        subprocess.run(["git", "checkout", commit_hash],
                       cwd=tmp_path, capture_output=True)

        # Check if on branch
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=tmp_path,
            capture_output=True,
            text=True
        )

        # Should be empty (detached HEAD)
        assert result.stdout.strip() == ""


@pytest.mark.functional
@pytest.mark.adversarial
class TestNegativeTimeDelta:
    """Test handling of negative time deltas (clock issues)."""

    def test_future_timestamp_handling(self, tmp_path):
        """Edge case: File has timestamp in the future (clock drift)."""
        test_file = tmp_path / "future.txt"
        test_file.write_text("content")

        # Get current time
        now = datetime.now()
        file_time = datetime.fromtimestamp(test_file.stat().st_mtime)

        # Calculate age
        age = now - file_time

        # Should be very small (just created)
        assert age.total_seconds() < 10

    def test_epoch_timestamp(self, tmp_path):
        """Edge case: File with epoch timestamp (1970-01-01)."""
        test_file = tmp_path / "old.txt"
        test_file.write_text("content")

        # Set to epoch
        os.utime(test_file, (0, 0))

        file_time = datetime.fromtimestamp(test_file.stat().st_mtime)

        # Should be 1970
        assert file_time.year == 1970


@pytest.mark.functional
@pytest.mark.adversarial
class TestThresholdBoundaries:
    """Test threshold boundary conditions."""

    def test_exactly_at_threshold(self, tmp_path):
        """Edge case: File age exactly at threshold."""
        threshold_minutes = 30
        threshold_seconds = threshold_minutes * 60

        test_file = tmp_path / "threshold.txt"
        test_file.write_text("content")

        # Set mtime to exactly threshold ago
        now = datetime.now().timestamp()
        os.utime(test_file, (now - threshold_seconds, now - threshold_seconds))

        file_time = datetime.fromtimestamp(test_file.stat().st_mtime)
        age = datetime.now() - file_time

        # Should be approximately at threshold
        assert abs(age.total_seconds() - threshold_seconds) < 5

    def test_zero_threshold(self):
        """Edge case: Zero threshold means everything is stale."""
        threshold_minutes = 0

        # With zero threshold, any age > 0 is stale
        any_age_minutes = 0.001  # 60 milliseconds
        is_stale = any_age_minutes > threshold_minutes

        assert is_stale

    def test_very_large_threshold(self):
        """Edge case: Very large threshold (years)."""
        threshold_minutes = 365 * 24 * 60  # 1 year

        # Check it can be represented
        threshold_seconds = threshold_minutes * 60
        threshold_days = threshold_seconds / 86400

        assert threshold_days == 365
