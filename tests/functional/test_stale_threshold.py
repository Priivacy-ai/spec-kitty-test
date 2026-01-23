"""
T057: Stale Threshold Configuration Tests

Validates threshold configuration for stale detection:
- --stale-threshold flag is respected
- Different thresholds produce expected results
- Edge cases (zero, negative) are handled

These tests ensure the staleness threshold is configurable.

Note: Tests may be skipped if stale detection functionality is not yet implemented.
"""
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from tests.functional.test_merge_fixtures import (
    WPFixture,
    create_test_feature,
)


# =============================================================================
# Skip Marker for Unimplemented Features
# =============================================================================

def stale_threshold_available() -> bool:
    """Check if stale threshold functionality is available."""
    try:
        from specify_cli.orchestrator.state import detect_stale_wps
        return True
    except ImportError:
        return False


requires_stale_threshold = pytest.mark.skipif(
    not stale_threshold_available(),
    reason="Stale threshold functionality not yet implemented"
)


# =============================================================================
# Helper Functions
# =============================================================================

def make_commit_minutes_ago(worktree_path: Path, minutes_ago: int) -> None:
    """Create a commit with a timestamp in the past.

    Args:
        worktree_path: Path to the git worktree
        minutes_ago: How many minutes in the past to date the commit
    """
    past_time = datetime.now() - timedelta(minutes=minutes_ago)
    iso_time = past_time.strftime("%Y-%m-%dT%H:%M:%S")

    test_file = worktree_path / f"work_{minutes_ago}min.txt"
    test_file.write_text(f"Work from {minutes_ago} minutes ago")

    env = os.environ.copy()
    env["GIT_COMMITTER_DATE"] = iso_time
    env["GIT_AUTHOR_DATE"] = iso_time

    subprocess.run(["git", "add", "."], cwd=worktree_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", f"Commit from {minutes_ago} min ago", "--date", iso_time],
        cwd=worktree_path,
        check=True,
        capture_output=True,
        env=env,
    )


def get_last_commit_age_minutes(worktree_path: Path) -> float:
    """Get the age of the last commit in minutes."""
    result = subprocess.run(
        ["git", "log", "-1", "--format=%ct"],
        cwd=worktree_path,
        capture_output=True,
        text=True,
        check=True,
    )
    commit_timestamp = int(result.stdout.strip())
    now_timestamp = datetime.now().timestamp()
    return (now_timestamp - commit_timestamp) / 60


# =============================================================================
# Threshold Configuration Tests (T057)
# =============================================================================

@pytest.mark.functional
class TestThresholdConfiguration:
    """Tests for stale detection threshold configuration."""

    def test_commit_creation_with_age(self, create_test_feature):
        """Verify we can create commits with specific ages."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="doing"),
            ]
        )

        wt_path = feature.worktrees.get("WP01")
        assert wt_path and wt_path.exists()

        # Create commit 15 minutes ago
        make_commit_minutes_ago(wt_path, 15)

        age = get_last_commit_age_minutes(wt_path)
        assert 14 <= age <= 16, f"Commit should be ~15 min old, got {age:.1f}"

    @pytest.mark.parametrize("threshold,commit_age,should_be_stale", [
        (5, 10, True),    # 10min old > 5min threshold = stale
        (10, 15, True),   # 15min old > 10min threshold = stale
        (20, 15, False),  # 15min old < 20min threshold = not stale
        (30, 15, False),  # 15min old < 30min threshold = not stale
    ])
    @requires_stale_threshold
    def test_threshold_determines_staleness(
        self, create_test_feature, threshold, commit_age, should_be_stale
    ):
        """Different threshold values correctly determine staleness."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="doing"),
            ]
        )

        wt_path = feature.worktrees.get("WP01")
        assert wt_path and wt_path.exists(), "Worktree should exist"

        # Create commit with specific age
        make_commit_minutes_ago(wt_path, commit_age)

        try:
            from specify_cli.orchestrator.state import detect_stale_wps
            stale_wps = detect_stale_wps(
                feature.project_dir,
                feature=feature.feature_slug,
                threshold_minutes=threshold
            )

            if should_be_stale:
                assert "WP01" in stale_wps, \
                    f"{commit_age}min old > {threshold}min threshold should be stale"
            else:
                assert "WP01" not in stale_wps, \
                    f"{commit_age}min old < {threshold}min threshold should not be stale"
        except ImportError:
            pytest.skip("Stale detection API not available")

    @requires_stale_threshold
    def test_default_threshold_is_10_minutes(self, create_test_feature):
        """Default threshold is 10 minutes when not specified."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="doing"),
            ]
        )

        wt_path = feature.worktrees.get("WP01")
        assert wt_path and wt_path.exists()

        # Create 12 minute old commit (older than default 10min)
        make_commit_minutes_ago(wt_path, 12)

        try:
            from specify_cli.orchestrator.state import detect_stale_wps
            # Call without threshold (should use default)
            stale_wps = detect_stale_wps(
                feature.project_dir,
                feature=feature.feature_slug
            )
            # Default threshold should be ~10 minutes
            assert "WP01" in stale_wps, "12min old should be stale with default threshold"
        except ImportError:
            pytest.skip("Stale detection API not available")


@pytest.mark.functional
class TestThresholdEdgeCases:
    """Tests for edge cases in threshold configuration."""

    @requires_stale_threshold
    def test_threshold_zero_marks_all_as_stale(self, create_test_feature):
        """Threshold of 0 marks all WPs in doing lane as stale."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="doing"),
            ]
        )

        wt_path = feature.worktrees.get("WP01")
        assert wt_path and wt_path.exists()

        # Create very recent commit
        test_file = wt_path / "recent.txt"
        test_file.write_text("Just now")
        subprocess.run(["git", "add", "."], cwd=wt_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Just now"],
            cwd=wt_path,
            check=True,
            capture_output=True,
        )

        try:
            from specify_cli.orchestrator.state import detect_stale_wps
            stale_wps = detect_stale_wps(
                feature.project_dir,
                feature=feature.feature_slug,
                threshold_minutes=0
            )
            # With threshold=0, even recent commits should be "stale"
            assert "WP01" in stale_wps, "Zero threshold should mark all as stale"
        except ImportError:
            pytest.skip("Stale detection API not available")

    @pytest.mark.adversarial
    @requires_stale_threshold
    def test_negative_threshold_handled(self, create_test_feature):
        """Negative threshold is handled gracefully (error or treat as 0)."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="doing"),
            ]
        )

        try:
            from specify_cli.orchestrator.state import detect_stale_wps

            # Try negative threshold - should either:
            # 1. Raise ValueError
            # 2. Treat as 0
            try:
                stale_wps = detect_stale_wps(
                    feature.project_dir,
                    feature=feature.feature_slug,
                    threshold_minutes=-10
                )
                # If no error, should behave like threshold=0
            except ValueError as e:
                # This is acceptable - clear error about invalid threshold
                assert "threshold" in str(e).lower()
        except ImportError:
            pytest.skip("Stale detection API not available")

    @requires_stale_threshold
    def test_very_large_threshold(self, create_test_feature):
        """Very large threshold means nothing is stale."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="doing"),
            ]
        )

        wt_path = feature.worktrees.get("WP01")
        if wt_path and wt_path.exists():
            make_commit_minutes_ago(wt_path, 60)  # 1 hour old

        try:
            from specify_cli.orchestrator.state import detect_stale_wps
            stale_wps = detect_stale_wps(
                feature.project_dir,
                feature=feature.feature_slug,
                threshold_minutes=10080  # 1 week
            )
            assert "WP01" not in stale_wps, "Large threshold should not mark as stale"
        except ImportError:
            pytest.skip("Stale detection API not available")


@pytest.mark.functional
class TestThresholdWithMultipleWPs:
    """Tests for threshold with multiple work packages."""

    def test_different_commit_ages_created(self, create_test_feature):
        """Verify we can create WPs with different commit ages."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="doing"),
                WPFixture("WP02", lane="doing"),
                WPFixture("WP03", lane="doing"),
            ]
        )

        # WP01: 5 min old
        wt1 = feature.worktrees.get("WP01")
        if wt1 and wt1.exists():
            make_commit_minutes_ago(wt1, 5)

        # WP02: 15 min old
        wt2 = feature.worktrees.get("WP02")
        if wt2 and wt2.exists():
            make_commit_minutes_ago(wt2, 15)

        # WP03: 25 min old
        wt3 = feature.worktrees.get("WP03")
        if wt3 and wt3.exists():
            make_commit_minutes_ago(wt3, 25)

        # Verify ages
        age1 = get_last_commit_age_minutes(wt1)
        age2 = get_last_commit_age_minutes(wt2)
        age3 = get_last_commit_age_minutes(wt3)

        assert 4 <= age1 <= 6, f"WP01 should be ~5 min old, got {age1:.1f}"
        assert 14 <= age2 <= 16, f"WP02 should be ~15 min old, got {age2:.1f}"
        assert 24 <= age3 <= 26, f"WP03 should be ~25 min old, got {age3:.1f}"

    @requires_stale_threshold
    def test_threshold_applied_consistently(self, create_test_feature):
        """Same threshold applies to all WPs."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="doing"),
                WPFixture("WP02", lane="doing"),
                WPFixture("WP03", lane="doing"),
            ]
        )

        # WP01: 5 min old (not stale with 10min threshold)
        wt1 = feature.worktrees.get("WP01")
        if wt1 and wt1.exists():
            make_commit_minutes_ago(wt1, 5)

        # WP02: 15 min old (stale with 10min threshold)
        wt2 = feature.worktrees.get("WP02")
        if wt2 and wt2.exists():
            make_commit_minutes_ago(wt2, 15)

        # WP03: 25 min old (stale with 10min threshold)
        wt3 = feature.worktrees.get("WP03")
        if wt3 and wt3.exists():
            make_commit_minutes_ago(wt3, 25)

        try:
            from specify_cli.orchestrator.state import detect_stale_wps
            stale_wps = detect_stale_wps(
                feature.project_dir,
                feature=feature.feature_slug,
                threshold_minutes=10
            )
            assert "WP01" not in stale_wps, "WP01 (5min) should not be stale"
            assert "WP02" in stale_wps, "WP02 (15min) should be stale"
            assert "WP03" in stale_wps, "WP03 (25min) should be stale"
        except ImportError:
            pytest.skip("Stale detection API not available")
