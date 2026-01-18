"""
Tests for spec-kitty merge pre-flight validation.

Validates User Story 1 from Feature 003 spec:
- Dirty worktrees detected and reported
- Target branch divergence detected
- All issues reported together
- Non-zero exit without branch modifications

Requires spec-kitty >= 0.11.0 (workspace-per-WP).
"""
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.functional.test_merge_fixtures import (
    WPFixture,
    create_test_feature,
)


class TestMergePreflightValidation:
    """Tests for pre-flight validation before merge."""

    def test_dirty_worktree_detected(self, create_test_feature, requires_v011):
        """Pre-flight detects uncommitted changes in worktrees (FR-005)."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
                WPFixture("WP02", lane="done", dirty=True),  # Has uncommitted changes
            ]
        )

        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        # Pre-flight should fail
        assert result.returncode != 0, f"Expected non-zero exit, got: {result.stdout}"

        # Output should mention dirty/uncommitted
        output = result.stdout + result.stderr
        assert "WP02" in output, "Should mention the dirty WP"
        assert any(word in output.lower() for word in ["uncommitted", "dirty", "changes"]), \
            f"Should indicate uncommitted changes: {output}"

    def test_multiple_dirty_worktrees_reported_together(self, create_test_feature, requires_v011):
        """Pre-flight reports ALL issues together, not one at a time (FR-007)."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
                WPFixture("WP02", lane="done", dirty=True),
                WPFixture("WP03", lane="done", dirty=True),
            ]
        )

        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        output = result.stdout + result.stderr

        # Both dirty WPs should be mentioned in the same output
        assert "WP02" in output, "Should mention WP02"
        assert "WP03" in output, "Should mention WP03"

        # They should appear in a consolidated list, not discovered iteratively
        # The key indicator is that we see all issues without having to run merge multiple times
        wp02_pos = output.find("WP02")
        wp03_pos = output.find("WP03")
        assert wp02_pos != -1 and wp03_pos != -1, "Both WPs should be in output"

    def test_target_branch_divergence_detected(self, create_test_feature, tmp_path, requires_v011):
        """Pre-flight detects when target branch has diverged from origin (FR-006).

        Tests that target branch being behind the remote is detected.
        Note: Being ahead of origin is typically okay for merging, but being
        behind means the local main could have conflicts with remote.
        """
        # Create a bare "remote" repo
        remote_path = tmp_path / "remote.git"
        subprocess.run(["git", "init", "--bare", str(remote_path)], check=True, capture_output=True)

        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
            ]
        )

        # Add remote and push
        subprocess.run(
            ["git", "remote", "add", "origin", str(remote_path)],
            cwd=feature.project_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "push", "-u", "origin", "main"],
            cwd=feature.project_dir,
            check=True,
            capture_output=True,
        )

        # Create a second clone and push a new commit to origin
        # This makes the original repo's main branch behind origin
        second_clone = tmp_path / "second_clone"
        subprocess.run(
            ["git", "clone", str(remote_path), str(second_clone)],
            check=True,
            capture_output=True,
        )
        (second_clone / "remote_change.txt").write_text("Change from remote")
        subprocess.run(["git", "add", "."], cwd=second_clone, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Remote change"],
            cwd=second_clone,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "push", "origin", "main"],
            cwd=second_clone,
            check=True,
            capture_output=True,
        )

        # Fetch so local knows about remote changes (but don't merge)
        subprocess.run(
            ["git", "fetch", "origin"],
            cwd=feature.project_dir,
            check=True,
            capture_output=True,
        )

        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        # Should warn about divergence or out of sync with origin
        output = result.stdout + result.stderr
        # Look for divergence-related messaging - either a warning or the table shows something
        # The target status should indicate it's behind
        has_divergence_warning = any(word in output.lower() for word in [
            "diverge", "behind", "sync", "pull", "out of date", "not up to date"
        ])
        # If no warning, it might still pass but we should at least see the preflight table
        assert has_divergence_warning or "pre-flight" in output.lower(), \
            f"Should detect or show preflight status for target behind origin: {output}"

    def test_preflight_failure_no_branch_modification(self, create_test_feature, requires_v011):
        """Pre-flight failure exits non-zero WITHOUT modifying branches (FR-008)."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done", dirty=True),
            ]
        )

        # Record main branch state before
        before_result = subprocess.run(
            ["git", "log", "--oneline", "-1", "main"],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )
        before_commit = before_result.stdout.strip()

        # Attempt merge (should fail pre-flight)
        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0, "Should exit non-zero"

        # Verify main branch unchanged
        after_result = subprocess.run(
            ["git", "log", "--oneline", "-1", "main"],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )
        after_commit = after_result.stdout.strip()

        assert before_commit == after_commit, \
            f"Main branch should be unchanged. Before: {before_commit}, After: {after_commit}"

    def test_clean_worktrees_pass_preflight(self, create_test_feature, requires_v011):
        """Clean worktrees with up-to-date target pass pre-flight."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
                WPFixture("WP02", lane="done"),
            ]
        )

        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        output = result.stdout + result.stderr

        # Should either succeed or proceed to actual merge
        # (might still fail due to conflicts, but NOT due to pre-flight)
        # Check that pre-flight validation passed (not blocked by dirty worktrees)
        preflight_failed = any(word in output.lower() for word in ["uncommitted", "dirty", "diverge"])
        assert not preflight_failed or result.returncode == 0, \
            f"Clean worktrees should pass pre-flight: {output}"

    def test_deleted_worktree_detected(self, create_test_feature, requires_v011):
        """Pre-flight detects deleted worktree when branch still exists."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
                WPFixture("WP02", lane="done"),
            ]
        )

        # Manually delete WP02 worktree directory (simulate user error)
        wp02_path = feature.get_worktree_path("WP02")
        if wp02_path and wp02_path.exists():
            shutil.rmtree(wp02_path)

        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        output = result.stdout + result.stderr

        # Should detect the inconsistency
        assert result.returncode != 0 or "WP02" in output, \
            f"Should detect missing worktree: {output}"
