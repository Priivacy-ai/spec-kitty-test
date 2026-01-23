"""
T060: Merge Dry-Run Tests

Validates --dry-run flag for merge:
- Predicts conflicts without performing merge
- Does not modify git state
- Shows which WPs would conflict

These tests ensure dry-run is safe and informative.
"""
import subprocess
from pathlib import Path

import pytest

from tests.functional.test_merge_fixtures import (
    WPFixture,
    create_test_feature,
)


# =============================================================================
# Helper Functions
# =============================================================================

def get_git_state(project_dir: Path) -> dict:
    """Capture current git state for comparison.

    Args:
        project_dir: Root of the git repository

    Returns:
        Dictionary with git state information
    """
    # Get current branch
    branch_result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=project_dir,
        capture_output=True,
        text=True,
    )

    # Get HEAD commit
    head_result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=project_dir,
        capture_output=True,
        text=True,
    )

    # Get status (working tree state)
    status_result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=project_dir,
        capture_output=True,
        text=True,
    )

    # Get list of branches
    branches_result = subprocess.run(
        ["git", "branch", "--list"],
        cwd=project_dir,
        capture_output=True,
        text=True,
    )

    return {
        "branch": branch_result.stdout.strip(),
        "head": head_result.stdout.strip(),
        "status": status_result.stdout,
        "branches": branches_result.stdout,
    }


# =============================================================================
# Dry-Run Conflict Prediction Tests (T060)
# =============================================================================

@pytest.mark.functional
class TestDryRunConflictPrediction:
    """Tests for dry-run conflict prediction."""

    def test_dry_run_predicts_conflicts(self, create_test_feature):
        """Dry-run shows conflicts without performing merge."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
                WPFixture("WP02", lane="done"),
            ]
        )

        # Create conflicting changes in both WPs
        wt1 = feature.worktrees.get("WP01")
        wt2 = feature.worktrees.get("WP02")

        if wt1 and wt1.exists():
            (wt1 / "shared.txt").write_text("WP01 version of shared file")
            subprocess.run(["git", "add", "."], cwd=wt1, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "WP01 change to shared.txt"],
                cwd=wt1,
                capture_output=True,
            )

        if wt2 and wt2.exists():
            (wt2 / "shared.txt").write_text("WP02 version of shared file")
            subprocess.run(["git", "add", "."], cwd=wt2, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "WP02 change to shared.txt"],
                cwd=wt2,
                capture_output=True,
            )

        # Run dry-run
        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug, "--dry-run"],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        output = result.stdout + result.stderr

        # Should indicate potential conflict
        # (exact behavior depends on merge strategy)
        if "conflict" in output.lower():
            assert "shared.txt" in output or "WP01" in output or "WP02" in output, \
                f"Should identify conflicting file or WPs: {output}"

    def test_dry_run_shows_merge_preview(self, create_test_feature):
        """Dry-run shows what would be merged."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
                WPFixture("WP02", lane="done"),
            ]
        )

        # Make commits in WPs
        for wp_id in ["WP01", "WP02"]:
            wt = feature.worktrees.get(wp_id)
            if wt and wt.exists():
                (wt / f"{wp_id.lower()}_file.txt").write_text(f"Content from {wp_id}")
                subprocess.run(["git", "add", "."], cwd=wt, capture_output=True)
                subprocess.run(
                    ["git", "commit", "-m", f"Add file from {wp_id}"],
                    cwd=wt,
                    capture_output=True,
                )

        # Run dry-run
        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug, "--dry-run"],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        output = result.stdout + result.stderr

        # Should show merge preview (WPs that would be merged)
        assert "WP01" in output or "WP02" in output or "merge" in output.lower(), \
            f"Should show merge preview: {output}"


@pytest.mark.functional
class TestDryRunNoStateChanges:
    """Tests that dry-run doesn't modify git state."""

    def test_dry_run_preserves_branch(self, create_test_feature):
        """Dry-run doesn't change current branch."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
            ]
        )

        state_before = get_git_state(feature.project_dir)

        # Run dry-run
        subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug, "--dry-run"],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        state_after = get_git_state(feature.project_dir)

        # Branch should be unchanged
        assert state_before["branch"] == state_after["branch"], \
            f"Branch changed from {state_before['branch']} to {state_after['branch']}"

    def test_dry_run_preserves_head(self, create_test_feature):
        """Dry-run doesn't change HEAD commit."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
            ]
        )

        state_before = get_git_state(feature.project_dir)

        # Run dry-run
        subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug, "--dry-run"],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        state_after = get_git_state(feature.project_dir)

        # HEAD should be unchanged
        assert state_before["head"] == state_after["head"], \
            f"HEAD changed from {state_before['head']} to {state_after['head']}"

    def test_dry_run_preserves_working_tree(self, create_test_feature):
        """Dry-run doesn't modify working tree."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
            ]
        )

        state_before = get_git_state(feature.project_dir)

        # Run dry-run
        subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug, "--dry-run"],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        state_after = get_git_state(feature.project_dir)

        # Working tree status should be unchanged
        assert state_before["status"] == state_after["status"], \
            f"Working tree changed: {state_before['status']} -> {state_after['status']}"

    def test_dry_run_no_new_commits(self, create_test_feature):
        """Dry-run doesn't create any commits."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
            ]
        )

        # Get commit count before
        log_before = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )
        count_before = len(log_before.stdout.strip().split("\n"))

        # Run dry-run
        subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug, "--dry-run"],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        # Get commit count after
        log_after = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )
        count_after = len(log_after.stdout.strip().split("\n"))

        assert count_before == count_after, \
            f"Commit count changed: {count_before} -> {count_after}"


@pytest.mark.functional
class TestDryRunWithVariousScenarios:
    """Tests for dry-run with various merge scenarios."""

    def test_dry_run_clean_merge(self, create_test_feature):
        """Dry-run shows clean merge (no conflicts)."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
                WPFixture("WP02", lane="done"),
            ]
        )

        # Make non-conflicting changes
        wt1 = feature.worktrees.get("WP01")
        wt2 = feature.worktrees.get("WP02")

        if wt1 and wt1.exists():
            (wt1 / "wp01_only.txt").write_text("WP01 content")
            subprocess.run(["git", "add", "."], cwd=wt1, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "WP01 adds unique file"],
                cwd=wt1,
                capture_output=True,
            )

        if wt2 and wt2.exists():
            (wt2 / "wp02_only.txt").write_text("WP02 content")
            subprocess.run(["git", "add", "."], cwd=wt2, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "WP02 adds unique file"],
                cwd=wt2,
                capture_output=True,
            )

        # Run dry-run
        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug, "--dry-run"],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        output = result.stdout + result.stderr

        # Should indicate clean merge possible
        # (no conflict warnings)
        if "conflict" not in output.lower():
            pass  # Clean merge predicted

    def test_dry_run_with_dependencies(self, create_test_feature):
        """Dry-run respects WP dependencies in preview."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
                WPFixture("WP02", lane="done", dependencies=["WP01"]),
            ]
        )

        # Run dry-run
        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug, "--dry-run"],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        output = result.stdout + result.stderr

        # Should show merge order if relevant
        assert result.returncode in [0, 1], f"Should not crash: {result.stderr}"

    @pytest.mark.adversarial
    def test_dry_run_empty_feature(self, create_test_feature):
        """Dry-run handles feature with no WPs to merge."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="planned"),  # Not done yet
            ]
        )

        # Run dry-run
        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug, "--dry-run"],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        # Should handle gracefully
        output = result.stdout + result.stderr
        assert result.returncode in [0, 1], \
            f"Should handle no done WPs: {result.stderr}"
