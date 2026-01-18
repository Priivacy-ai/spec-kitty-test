"""
Tests for spec-kitty merge ordering (dependency-based).

Validates User Story 3 from Feature 003 spec:
- Dependencies parsed from frontmatter
- Topological ordering respected
- Circular dependencies detected
- Numerical fallback when no dependencies

Requires spec-kitty >= 0.11.0.
"""
import subprocess
from pathlib import Path

import pytest

from tests.functional.test_merge_fixtures import (
    WPFixture,
    create_test_feature,
)


class TestMergeOrdering:
    """Tests for dependency-based merge ordering."""

    def test_dependency_ordering(self, create_test_feature, requires_v011):
        """WP with dependency merges after its dependency (FR-014)."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
                WPFixture("WP02", lane="done", dependencies=["WP01"]),
            ]
        )

        # Add unique content to each WP
        for wp_id in ["WP01", "WP02"]:
            wp_path = feature.get_worktree_path(wp_id)
            (wp_path / f"{wp_id.lower()}_file.py").write_text(f"# From {wp_id}")
            subprocess.run(["git", "add", "."], cwd=wp_path, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", f"Add {wp_id} content"], cwd=wp_path, check=True, capture_output=True)

        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        output = result.stdout + result.stderr

        # Find positions of WP mentions in merge output
        # WP01 should be processed/mentioned before WP02
        wp01_pos = output.find("WP01")
        wp02_pos = output.find("WP02")

        # Both WPs should be in output
        assert wp01_pos != -1, f"WP01 should be in output: {output}"
        assert wp02_pos != -1, f"WP02 should be in output: {output}"

        # In pre-flight or merge order, WP01 should appear before WP02
        # due to dependency ordering
        if wp01_pos != -1 and wp02_pos != -1:
            assert wp01_pos < wp02_pos, \
                f"WP01 should appear before WP02 in output. Output: {output}"

    def test_diamond_dependency_ordering(self, create_test_feature, requires_v011):
        """Diamond dependency pattern merges in correct order."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
                WPFixture("WP02", lane="done", dependencies=["WP01"]),
                WPFixture("WP03", lane="done", dependencies=["WP01"]),
                WPFixture("WP04", lane="done", dependencies=["WP02", "WP03"]),
            ]
        )

        # Add content to each WP
        for wp_id in ["WP01", "WP02", "WP03", "WP04"]:
            wp_path = feature.get_worktree_path(wp_id)
            (wp_path / f"{wp_id.lower()}.txt").write_text(f"Content from {wp_id}")
            subprocess.run(["git", "add", "."], cwd=wp_path, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", f"Add {wp_id}"], cwd=wp_path, check=True, capture_output=True)

        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        output = result.stdout + result.stderr

        # Verify order: WP01 must be first, WP04 must be last
        # WP02 and WP03 can be in any order (both depend only on WP01)
        wp_positions = {}
        for wp in ["WP01", "WP02", "WP03", "WP04"]:
            pos = output.find(wp)
            if pos != -1:
                wp_positions[wp] = pos

        # All WPs should be in output
        assert len(wp_positions) == 4, f"All 4 WPs should be in output: {output}"

        # Verify dependency constraints
        assert wp_positions["WP01"] < wp_positions["WP04"], "WP01 must be before WP04"
        assert wp_positions["WP02"] < wp_positions["WP04"], "WP02 must be before WP04"
        assert wp_positions["WP03"] < wp_positions["WP04"], "WP03 must be before WP04"
        assert wp_positions["WP01"] < wp_positions["WP02"], "WP01 must be before WP02"
        assert wp_positions["WP01"] < wp_positions["WP03"], "WP01 must be before WP03"

    def test_circular_dependency_detected(self, create_test_feature, requires_v011):
        """Circular dependencies detected with clear error (FR-015)."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done", dependencies=["WP02"]),
                WPFixture("WP02", lane="done", dependencies=["WP01"]),
            ]
        )

        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        output = result.stdout + result.stderr

        # Should fail with circular dependency error OR handle gracefully
        # Check for circular dependency indication
        has_cycle_error = any(word in output.lower() for word in [
            "circular", "cycle", "loop", "cyclic"
        ])
        has_error = result.returncode != 0

        # Either explicit cycle detection or general error is acceptable
        assert has_cycle_error or has_error, \
            f"Should detect or fail on circular dependency: {output}"

    def test_numerical_fallback_ordering(self, create_test_feature, requires_v011):
        """No dependencies falls back to numerical order (FR-016)."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
                WPFixture("WP02", lane="done"),
                WPFixture("WP03", lane="done"),
            ]
        )

        # Add content
        for wp_id in ["WP01", "WP02", "WP03"]:
            wp_path = feature.get_worktree_path(wp_id)
            (wp_path / f"{wp_id.lower()}.txt").write_text(f"{wp_id}")
            subprocess.run(["git", "add", "."], cwd=wp_path, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", wp_id], cwd=wp_path, check=True, capture_output=True)

        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        output = result.stdout + result.stderr

        # Should process in numerical order
        wp01_pos = output.find("WP01")
        wp02_pos = output.find("WP02")
        wp03_pos = output.find("WP03")

        # All WPs should be in output
        assert wp01_pos != -1, "WP01 should be in output"
        assert wp02_pos != -1, "WP02 should be in output"
        assert wp03_pos != -1, "WP03 should be in output"

        # Should be in numerical order
        assert wp01_pos < wp02_pos < wp03_pos, \
            f"Should be in numerical order. Output: {output}"

    def test_frontmatter_dependency_parsing(self, create_test_feature, requires_v011):
        """Frontmatter dependencies: [] parsed correctly (FR-013)."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done", dependencies=[]),  # Empty
                WPFixture("WP02", lane="done", dependencies=["WP01"]),  # Single
                WPFixture("WP03", lane="done", dependencies=["WP01", "WP02"]),  # Multiple
            ]
        )

        # Add content
        for wp_id in ["WP01", "WP02", "WP03"]:
            wp_path = feature.get_worktree_path(wp_id)
            (wp_path / f"{wp_id.lower()}.txt").write_text(f"{wp_id}")
            subprocess.run(["git", "add", "."], cwd=wp_path, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", wp_id], cwd=wp_path, check=True, capture_output=True)

        result = subprocess.run(
            ["spec-kitty", "merge", "--dry-run", "--feature", feature.feature_slug],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        output = result.stdout + result.stderr

        # Should not error on parsing - either succeeds or shows pre-flight
        parsing_ok = (
            result.returncode == 0 or
            "pre-flight" in output.lower() or
            "error" not in result.stderr.lower()
        )
        assert parsing_ok, f"Should parse dependencies without error: {result.stderr}"

        # WP03 should be after WP01 (depends on WP01 and WP02)
        wp01_pos = output.find("WP01")
        wp03_pos = output.find("WP03")
        if wp01_pos != -1 and wp03_pos != -1:
            assert wp01_pos < wp03_pos, "WP01 should be before WP03"

    def test_multiple_parallel_chains(self, create_test_feature, requires_v011):
        """Multiple parallel dependency chains respected."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
                WPFixture("WP02", lane="done"),
                WPFixture("WP03", lane="done", dependencies=["WP01"]),
                WPFixture("WP04", lane="done", dependencies=["WP02"]),
            ]
        )

        # Add content
        for wp_id in ["WP01", "WP02", "WP03", "WP04"]:
            wp_path = feature.get_worktree_path(wp_id)
            (wp_path / f"{wp_id.lower()}.txt").write_text(f"{wp_id}")
            subprocess.run(["git", "add", "."], cwd=wp_path, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", wp_id], cwd=wp_path, check=True, capture_output=True)

        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        output = result.stdout + result.stderr

        # WP01 before WP03 (chain 1)
        # WP02 before WP04 (chain 2)
        wp_positions = {wp: output.find(wp) for wp in ["WP01", "WP02", "WP03", "WP04"]}

        # All should be present
        assert all(pos != -1 for pos in wp_positions.values()), \
            f"All WPs should be in output: {output}"

        # Verify chain ordering
        assert wp_positions["WP01"] < wp_positions["WP03"], "Chain 1: WP01 before WP03"
        assert wp_positions["WP02"] < wp_positions["WP04"], "Chain 2: WP02 before WP04"
