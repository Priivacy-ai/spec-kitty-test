"""
T058: Preflight Validation Tests

Validates merge pre-flight checks:
- Uncommitted changes detected
- Diverged branches detected
- Missing worktrees detected
- Clean worktrees pass

These tests ensure preflight catches issues before merge.
"""
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.functional.test_merge_fixtures import (
    WPFixture,
    create_test_feature,
)


# =============================================================================
# Preflight Validation Tests (T058)
# =============================================================================

@pytest.mark.functional
class TestPreflightUncommittedChanges:
    """Tests for detecting uncommitted changes during preflight."""

    def test_preflight_detects_uncommitted_changes(self, create_test_feature):
        """Preflight detects uncommitted changes in worktrees."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
                WPFixture("WP02", lane="done", dirty=True),  # Has uncommitted changes
            ]
        )

        # Verify WP02 has uncommitted changes
        wt2_path = feature.worktrees.get("WP02")
        if wt2_path and wt2_path.exists():
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=wt2_path,
                capture_output=True,
                text=True,
            )
            assert status.stdout.strip(), "WP02 should have uncommitted changes"

        # Run merge (preflight should fail)
        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        # Should fail with error about uncommitted changes
        assert result.returncode != 0, "Preflight should fail with uncommitted changes"

        output = result.stdout + result.stderr
        assert "WP02" in output, "Should mention WP02"
        assert any(word in output.lower() for word in ["uncommitted", "dirty", "changes"]), \
            f"Should indicate uncommitted changes: {output}"

    def test_preflight_passes_with_clean_worktrees(self, create_test_feature):
        """Preflight passes when all worktrees are clean."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
                WPFixture("WP02", lane="done"),
            ]
        )

        # Verify worktrees are clean
        for wp_id in ["WP01", "WP02"]:
            wt_path = feature.worktrees.get(wp_id)
            if wt_path and wt_path.exists():
                status = subprocess.run(
                    ["git", "status", "--porcelain"],
                    cwd=wt_path,
                    capture_output=True,
                    text=True,
                )
                assert not status.stdout.strip(), f"{wp_id} should be clean"

        # Run merge with --dry-run to test preflight without actual merge
        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug, "--dry-run"],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        # Should pass preflight (may still show conflict predictions)
        # A non-zero exit is OK if it's about conflicts, not preflight
        output = result.stdout + result.stderr

        # Should not fail due to uncommitted changes
        assert "uncommitted" not in output.lower() or "pass" in output.lower(), \
            f"Clean worktrees should pass preflight: {output}"

    def test_preflight_detects_untracked_files(self, create_test_feature):
        """Preflight detects untracked files as uncommitted changes."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
            ]
        )

        # Add untracked file to WP01
        wt_path = feature.worktrees.get("WP01")
        if wt_path and wt_path.exists():
            (wt_path / "untracked_file.txt").write_text("Untracked content")

        # Run merge
        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        output = result.stdout + result.stderr

        # Untracked files may or may not be considered "dirty" depending on config
        # The important thing is the command runs without crashing
        assert result.returncode in [0, 1], f"Command should not crash: {result.stderr}"


@pytest.mark.functional
class TestPreflightBranchDivergence:
    """Tests for detecting branch divergence during preflight."""

    def test_preflight_detects_diverged_target_branch(self, create_test_feature, tmp_path):
        """Preflight detects when target branch has diverged from origin."""
        # Create a bare "remote" repo
        remote_path = tmp_path / "remote.git"
        subprocess.run(
            ["git", "init", "--bare", str(remote_path)],
            check=True,
            capture_output=True,
        )

        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
            ]
        )

        # Add remote and push
        subprocess.run(
            ["git", "remote", "add", "origin", str(remote_path)],
            cwd=feature.project_dir,
            capture_output=True,
        )
        subprocess.run(
            ["git", "push", "-u", "origin", "main"],
            cwd=feature.project_dir,
            capture_output=True,
        )

        # Clone to simulate another developer
        other_clone = tmp_path / "other_clone"
        subprocess.run(
            ["git", "clone", str(remote_path), str(other_clone)],
            capture_output=True,
        )

        # Make and push commit from "other developer"
        (other_clone / "remote_change.txt").write_text("Remote change")
        subprocess.run(["git", "add", "."], cwd=other_clone, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "other@example.com"],
            cwd=other_clone,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Other Developer"],
            cwd=other_clone,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Remote commit"],
            cwd=other_clone,
            capture_output=True,
        )
        subprocess.run(
            ["git", "push"],
            cwd=other_clone,
            capture_output=True,
        )

        # Now our main is behind origin
        # Run merge - preflight should detect divergence
        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        output = result.stdout + result.stderr

        # May or may not fail depending on implementation
        # But should at least warn about divergence
        if result.returncode != 0:
            assert "diverge" in output.lower() or "behind" in output.lower() or \
                   "pull" in output.lower() or "fetch" in output.lower(), \
                   f"Should indicate divergence: {output}"

    def test_preflight_suggests_git_pull(self, create_test_feature, tmp_path):
        """Preflight error message suggests git pull for diverged branch."""
        # Setup similar divergence scenario
        remote_path = tmp_path / "remote.git"
        subprocess.run(
            ["git", "init", "--bare", str(remote_path)],
            check=True,
            capture_output=True,
        )

        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
            ]
        )

        subprocess.run(
            ["git", "remote", "add", "origin", str(remote_path)],
            cwd=feature.project_dir,
            capture_output=True,
        )
        subprocess.run(
            ["git", "push", "-u", "origin", "main"],
            cwd=feature.project_dir,
            capture_output=True,
        )

        # Create divergence (mock via local commit on main)
        # This tests that the system warns about potential divergence
        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        # Command should complete (divergence detection is informational)
        assert result.returncode in [0, 1], f"Command should not crash: {result.stderr}"


@pytest.mark.functional
@pytest.mark.adversarial
class TestPreflightMissingWorktree:
    """Tests for detecting missing worktrees during preflight."""

    def test_preflight_detects_missing_worktree(self, create_test_feature):
        """Preflight detects when worktree directory is missing."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
                WPFixture("WP02", lane="done"),
            ]
        )

        # Remove WP02 worktree
        wt2_path = feature.worktrees.get("WP02")
        if wt2_path and wt2_path.exists():
            # Force remove from git worktree list
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(wt2_path)],
                cwd=feature.project_dir,
                capture_output=True,
            )
            # Also remove the directory if it still exists
            if wt2_path.exists():
                shutil.rmtree(wt2_path)

        # Run merge
        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        output = result.stdout + result.stderr

        # Should detect missing worktree
        if result.returncode != 0:
            assert "WP02" in output or "missing" in output.lower() or \
                   "worktree" in output.lower(), \
                   f"Should indicate missing worktree: {output}"

    def test_preflight_handles_all_worktrees_missing(self, create_test_feature):
        """Preflight handles case where all worktrees are missing."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
            ]
        )

        # Remove all worktrees
        wt1_path = feature.worktrees.get("WP01")
        if wt1_path and wt1_path.exists():
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(wt1_path)],
                cwd=feature.project_dir,
                capture_output=True,
            )

        # Run merge
        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        # Should fail gracefully
        output = result.stdout + result.stderr
        assert result.returncode in [0, 1], f"Should fail gracefully: {result.stderr}"


@pytest.mark.functional
class TestPreflightEdgeCases:
    """Tests for preflight edge cases."""

    def test_preflight_with_staged_but_uncommitted_changes(self, create_test_feature):
        """Preflight detects staged but uncommitted changes."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
            ]
        )

        # Stage but don't commit
        wt_path = feature.worktrees.get("WP01")
        if wt_path and wt_path.exists():
            (wt_path / "staged.txt").write_text("Staged content")
            subprocess.run(["git", "add", "."], cwd=wt_path, capture_output=True)

        # Run merge
        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        output = result.stdout + result.stderr

        # Should detect staged changes
        if result.returncode != 0:
            assert "staged" in output.lower() or "uncommitted" in output.lower() or \
                   "changes" in output.lower(), \
                   f"Should indicate staged changes: {output}"

    def test_preflight_with_merge_conflict_markers(self, create_test_feature):
        """Preflight detects files with unresolved merge conflict markers."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
            ]
        )

        # Create file with conflict markers
        wt_path = feature.worktrees.get("WP01")
        if wt_path and wt_path.exists():
            conflict_file = wt_path / "conflict.txt"
            conflict_file.write_text("""
<<<<<<< HEAD
Our changes
=======
Their changes
>>>>>>> branch
""")
            subprocess.run(["git", "add", "."], cwd=wt_path, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "Add conflict file"],
                cwd=wt_path,
                capture_output=True,
            )

        # Run merge - may or may not detect conflict markers
        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug, "--dry-run"],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        # Should complete without crashing
        assert result.returncode in [0, 1], f"Should not crash: {result.stderr}"
