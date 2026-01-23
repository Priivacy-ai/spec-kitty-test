"""
T056: Stale Detection Tests

Validates User Story 6 from Feature 006 spec:
- WPs in "doing" lane with old commits are marked stale
- Other lanes are not checked for staleness
- Stale detection uses git log timestamps

These tests verify stale detection for the orchestrator state machine.

Note: Tests may be skipped if stale detection functionality is not yet implemented.
"""
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pytest

from tests.functional.test_merge_fixtures import (
    MergeTestFeature,
    WPFixture,
    create_test_feature,
)


# =============================================================================
# Skip Marker for Unimplemented Features
# =============================================================================

def stale_detection_available() -> bool:
    """Check if stale detection functionality is available."""
    try:
        # Try importing the stale detection module
        from specify_cli.orchestrator.state import detect_stale_wps
        return True
    except ImportError:
        pass

    # Try CLI command
    result = subprocess.run(
        ["spec-kitty", "agent", "tasks", "status", "--help"],
        capture_output=True,
        text=True,
    )
    return "stale" in result.stdout.lower() or "threshold" in result.stdout.lower()


requires_stale_detection = pytest.mark.skipif(
    not stale_detection_available(),
    reason="Stale detection functionality not yet implemented"
)


# =============================================================================
# Helper Functions
# =============================================================================

def make_old_commit(worktree_path: Path, minutes_ago: int = 15) -> None:
    """Create a commit with a timestamp in the past.

    Args:
        worktree_path: Path to the git worktree
        minutes_ago: How many minutes in the past to date the commit
    """
    past_time = datetime.now() - timedelta(minutes=minutes_ago)
    iso_time = past_time.strftime("%Y-%m-%dT%H:%M:%S")

    test_file = worktree_path / f"old_work_{minutes_ago}.txt"
    test_file.write_text(f"Work from {minutes_ago} minutes ago")

    env = os.environ.copy()
    env["GIT_COMMITTER_DATE"] = iso_time
    env["GIT_AUTHOR_DATE"] = iso_time

    subprocess.run(["git", "add", "."], cwd=worktree_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", f"Old commit from {minutes_ago} min ago", "--date", iso_time],
        cwd=worktree_path,
        check=True,
        capture_output=True,
        env=env,
    )


def make_recent_commit(worktree_path: Path) -> None:
    """Create a commit with the current timestamp.

    Args:
        worktree_path: Path to the git worktree
    """
    test_file = worktree_path / "recent_work.txt"
    test_file.write_text(f"Recent work at {datetime.now().isoformat()}")

    subprocess.run(["git", "add", "."], cwd=worktree_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Recent commit"],
        cwd=worktree_path,
        check=True,
        capture_output=True,
    )


def get_last_commit_age_minutes(worktree_path: Path) -> float:
    """Get the age of the last commit in minutes.

    Args:
        worktree_path: Path to the git worktree

    Returns:
        Age of last commit in minutes
    """
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


def get_lane_from_frontmatter(wp_path: Path) -> Optional[str]:
    """Extract lane from WP frontmatter.

    Args:
        wp_path: Path to WP prompt file

    Returns:
        Lane string or None if not found
    """
    if not wp_path.exists():
        return None

    content = wp_path.read_text()
    for line in content.split("\n"):
        if line.strip().startswith("lane:"):
            return line.split(":", 1)[1].strip().strip('"').strip("'")
    return None


# =============================================================================
# Stale WP Detection Tests (T056)
# =============================================================================

@pytest.mark.functional
class TestStaleWPDetection:
    """Tests for stale work package detection."""

    def test_commit_age_calculation(self, create_test_feature):
        """Verify we can correctly calculate commit age (helper test)."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="doing"),
            ]
        )

        wt_path = feature.worktrees.get("WP01")
        assert wt_path and wt_path.exists(), "Worktree should exist"

        # Make commit 15 minutes in the past
        make_old_commit(wt_path, minutes_ago=15)

        # Verify commit age
        age = get_last_commit_age_minutes(wt_path)
        assert 14 <= age <= 16, f"Commit should be ~15 min old, got {age:.1f} min"

    def test_recent_commit_age(self, create_test_feature):
        """Verify recent commit has low age."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="doing"),
            ]
        )

        wt_path = feature.worktrees.get("WP01")
        assert wt_path and wt_path.exists()

        # Make recent commit
        make_recent_commit(wt_path)

        # Verify commit is recent
        age = get_last_commit_age_minutes(wt_path)
        assert age < 2, f"Commit should be recent, got {age:.1f} min old"

    @requires_stale_detection
    def test_stale_wp_detected_by_old_commit(self, create_test_feature):
        """WP in 'doing' lane with old commit is marked stale."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="doing"),
            ]
        )

        wt_path = feature.worktrees.get("WP01")
        assert wt_path and wt_path.exists(), "Worktree should exist"

        # Make commit 15 minutes in the past
        make_old_commit(wt_path, minutes_ago=15)

        # Test stale detection (implementation-dependent)
        try:
            from specify_cli.orchestrator.state import detect_stale_wps
            stale_wps = detect_stale_wps(
                feature.project_dir,
                feature=feature.feature_slug,
                threshold_minutes=10
            )
            assert "WP01" in stale_wps, "WP01 should be detected as stale"
        except ImportError:
            pytest.skip("Stale detection API not available")

    @requires_stale_detection
    def test_recent_commit_not_stale(self, create_test_feature):
        """WP with recent commit is not marked stale."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="doing"),
            ]
        )

        wt_path = feature.worktrees.get("WP01")
        assert wt_path and wt_path.exists()

        # Make recent commit
        make_recent_commit(wt_path)

        try:
            from specify_cli.orchestrator.state import detect_stale_wps
            stale_wps = detect_stale_wps(
                feature.project_dir,
                feature=feature.feature_slug,
                threshold_minutes=10
            )
            assert "WP01" not in stale_wps, "Recent WP01 should not be stale"
        except ImportError:
            pytest.skip("Stale detection API not available")


@pytest.mark.functional
class TestStaleDetectionLaneFiltering:
    """Tests that stale detection only applies to 'doing' lane."""

    def test_lane_extraction_from_fixture(self, create_test_feature):
        """Verify fixture creates WPs with correct lanes."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="doing"),
                WPFixture("WP02", lane="planned"),
                WPFixture("WP03", lane="for_review"),
                WPFixture("WP04", lane="done"),
            ]
        )

        # Verify WPs were created
        for wp_id in ["WP01", "WP02", "WP03", "WP04"]:
            wt_path = feature.worktrees.get(wp_id)
            assert wt_path is not None, f"{wp_id} should have a worktree"

    @pytest.mark.parametrize("lane", ["planned", "for_review", "done"])
    @requires_stale_detection
    def test_non_doing_lane_not_checked(self, create_test_feature, lane):
        """WPs not in 'doing' lane are not checked for staleness."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane=lane),
            ]
        )

        wt_path = feature.worktrees.get("WP01")
        if wt_path and wt_path.exists():
            make_old_commit(wt_path, minutes_ago=30)

        try:
            from specify_cli.orchestrator.state import detect_stale_wps
            stale_wps = detect_stale_wps(
                feature.project_dir,
                feature=feature.feature_slug,
                threshold_minutes=10
            )
            assert "WP01" not in stale_wps, f"WP in '{lane}' should not be stale"
        except ImportError:
            pytest.skip("Stale detection API not available")


@pytest.mark.functional
class TestStaleDetectionMultipleWPs:
    """Tests for stale detection with multiple work packages."""

    def test_multiple_wps_created(self, create_test_feature):
        """Verify fixture can create multiple WPs correctly."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="doing"),
                WPFixture("WP02", lane="doing"),
                WPFixture("WP03", lane="doing"),
            ]
        )

        # All three should exist
        for wp_id in ["WP01", "WP02", "WP03"]:
            wt_path = feature.worktrees.get(wp_id)
            assert wt_path is not None, f"{wp_id} should exist"
            assert wt_path.exists(), f"{wp_id} worktree should exist"

    def test_commit_ages_can_differ(self, create_test_feature):
        """Verify we can create WPs with different commit ages."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="doing"),
                WPFixture("WP02", lane="doing"),
            ]
        )

        wt1 = feature.worktrees.get("WP01")
        wt2 = feature.worktrees.get("WP02")

        if wt1 and wt1.exists():
            make_old_commit(wt1, minutes_ago=20)

        if wt2 and wt2.exists():
            make_recent_commit(wt2)

        age1 = get_last_commit_age_minutes(wt1)
        age2 = get_last_commit_age_minutes(wt2)

        assert age1 > 15, "WP01 should have old commit"
        assert age2 < 2, "WP02 should have recent commit"

    @requires_stale_detection
    def test_multiple_stale_wps_detected(self, create_test_feature):
        """Multiple stale WPs are all detected."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="doing"),
                WPFixture("WP02", lane="doing"),
                WPFixture("WP03", lane="doing"),
            ]
        )

        # Make old commits in WP01 and WP02
        for wp_id in ["WP01", "WP02"]:
            wt_path = feature.worktrees.get(wp_id)
            if wt_path and wt_path.exists():
                make_old_commit(wt_path, minutes_ago=20)

        # Make recent commit in WP03
        wt_path3 = feature.worktrees.get("WP03")
        if wt_path3 and wt_path3.exists():
            make_recent_commit(wt_path3)

        try:
            from specify_cli.orchestrator.state import detect_stale_wps
            stale_wps = detect_stale_wps(
                feature.project_dir,
                feature=feature.feature_slug,
                threshold_minutes=10
            )
            assert "WP01" in stale_wps, "WP01 should be stale"
            assert "WP02" in stale_wps, "WP02 should be stale"
            assert "WP03" not in stale_wps, "WP03 should not be stale"
        except ImportError:
            pytest.skip("Stale detection API not available")
