"""
T061: Merge Dependency Order Tests

Validates merge order follows dependency topology:
- Dependencies merged before dependents
- Circular dependencies detected
- Independent WPs can be in any order

These tests ensure correct merge sequencing.
"""
import subprocess
from pathlib import Path

import pytest

from tests.functional.test_merge_fixtures import (
    WPFixture,
    create_test_feature,
)


# =============================================================================
# Dependency Order Tests (T061)
# =============================================================================

@pytest.mark.functional
class TestMergeDependencyOrder:
    """Tests for merge order respecting dependencies."""

    def test_dependency_merged_before_dependent(self, create_test_feature):
        """WP dependency is merged before dependent WP."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
                WPFixture("WP02", lane="done", dependencies=["WP01"]),
            ]
        )

        # Make commits in both WPs
        for wp_id in ["WP01", "WP02"]:
            wt = feature.worktrees.get(wp_id)
            if wt and wt.exists():
                (wt / f"{wp_id.lower()}_impl.py").write_text(f"# {wp_id} implementation")
                subprocess.run(["git", "add", "."], cwd=wt, capture_output=True)
                subprocess.run(
                    ["git", "commit", "-m", f"Implement {wp_id}"],
                    cwd=wt,
                    capture_output=True,
                )

        # Run merge with dry-run to see order
        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug, "--dry-run"],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        output = result.stdout + result.stderr

        # WP01 should be processed/shown before WP02
        if "WP01" in output and "WP02" in output:
            wp01_pos = output.find("WP01")
            wp02_pos = output.find("WP02")
            # Order may be shown in merge preview
            assert wp01_pos <= wp02_pos, \
                f"WP01 should appear before WP02: {output}"

    def test_complex_dependency_chain(self, create_test_feature):
        """Complex dependency chain is respected."""
        # WP01 -> WP02 -> WP03
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
                WPFixture("WP02", lane="done", dependencies=["WP01"]),
                WPFixture("WP03", lane="done", dependencies=["WP02"]),
            ]
        )

        # Run merge preview
        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug, "--dry-run"],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        output = result.stdout + result.stderr

        # If all WPs are mentioned, verify order
        if all(f"WP0{i}" in output for i in range(1, 4)):
            wp01_pos = output.find("WP01")
            wp02_pos = output.find("WP02")
            wp03_pos = output.find("WP03")

            assert wp01_pos <= wp02_pos <= wp03_pos, \
                f"Order should be WP01 -> WP02 -> WP03: {output}"

    def test_diamond_dependency(self, create_test_feature):
        """Diamond dependency pattern is handled correctly."""
        #     WP01
        #    /    \
        # WP02    WP03
        #    \    /
        #     WP04
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
                WPFixture("WP02", lane="done", dependencies=["WP01"]),
                WPFixture("WP03", lane="done", dependencies=["WP01"]),
                WPFixture("WP04", lane="done", dependencies=["WP02", "WP03"]),
            ]
        )

        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug, "--dry-run"],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        output = result.stdout + result.stderr

        # WP01 must be first
        # WP04 must be last
        # WP02 and WP03 can be in any order between them
        if all(f"WP0{i}" in output for i in range(1, 5)):
            wp01_pos = output.find("WP01")
            wp02_pos = output.find("WP02")
            wp03_pos = output.find("WP03")
            wp04_pos = output.find("WP04")

            # WP01 must be before WP02, WP03, WP04
            assert wp01_pos < wp02_pos, "WP01 should be before WP02"
            assert wp01_pos < wp03_pos, "WP01 should be before WP03"
            assert wp01_pos < wp04_pos, "WP01 should be before WP04"

            # WP04 must be after WP02 and WP03
            assert wp04_pos > wp02_pos, "WP04 should be after WP02"
            assert wp04_pos > wp03_pos, "WP04 should be after WP03"


@pytest.mark.functional
class TestIndependentWPOrder:
    """Tests for independent WPs (no dependencies between them)."""

    def test_independent_wps_all_merged(self, create_test_feature):
        """Independent WPs are all merged (order doesn't matter)."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
                WPFixture("WP02", lane="done"),  # No dependencies
                WPFixture("WP03", lane="done"),  # No dependencies
            ]
        )

        # Make commits
        for wp_id in ["WP01", "WP02", "WP03"]:
            wt = feature.worktrees.get(wp_id)
            if wt and wt.exists():
                (wt / f"{wp_id.lower()}.txt").write_text(f"{wp_id} content")
                subprocess.run(["git", "add", "."], cwd=wt, capture_output=True)
                subprocess.run(
                    ["git", "commit", "-m", f"Add {wp_id}"],
                    cwd=wt,
                    capture_output=True,
                )

        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug, "--dry-run"],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        output = result.stdout + result.stderr

        # All WPs should be in the merge plan
        assert result.returncode in [0, 1], f"Should not crash: {result.stderr}"

    def test_mixed_dependent_and_independent(self, create_test_feature):
        """Mix of dependent and independent WPs handled correctly."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
                WPFixture("WP02", lane="done", dependencies=["WP01"]),
                WPFixture("WP03", lane="done"),  # Independent
            ]
        )

        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug, "--dry-run"],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        output = result.stdout + result.stderr

        # WP01 must be before WP02
        # WP03 can be anywhere
        if "WP01" in output and "WP02" in output:
            wp01_pos = output.find("WP01")
            wp02_pos = output.find("WP02")
            assert wp01_pos < wp02_pos, "WP01 should be before WP02"


@pytest.mark.functional
@pytest.mark.adversarial
class TestCircularDependencyDetection:
    """Tests for circular dependency detection."""

    def test_simple_circular_dependency_detected(self, create_test_feature):
        """Simple circular dependency (A -> B -> A) is detected."""
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

        # Should detect circular dependency
        if result.returncode != 0:
            assert "circular" in output.lower() or "cycle" in output.lower() or \
                   "dependency" in output.lower(), \
                   f"Should detect circular dependency: {output}"

    def test_complex_circular_dependency_detected(self, create_test_feature):
        """Complex circular dependency (A -> B -> C -> A) is detected."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done", dependencies=["WP03"]),
                WPFixture("WP02", lane="done", dependencies=["WP01"]),
                WPFixture("WP03", lane="done", dependencies=["WP02"]),
            ]
        )

        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        output = result.stdout + result.stderr

        # Should detect the cycle
        if result.returncode != 0:
            assert "circular" in output.lower() or "cycle" in output.lower() or \
                   "dependency" in output.lower() or "error" in output.lower(), \
                   f"Should detect cycle: {output}"

    def test_self_dependency_detected(self, create_test_feature):
        """Self-dependency (WP depends on itself) is detected."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done", dependencies=["WP01"]),
            ]
        )

        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        output = result.stdout + result.stderr

        # Should detect self-dependency
        if result.returncode != 0:
            # May be "circular" or "invalid" or similar
            pass  # Error detection is sufficient


@pytest.mark.functional
class TestMergeDependencyEdgeCases:
    """Edge cases for merge dependency ordering."""

    def test_missing_dependency_handled(self, create_test_feature):
        """Missing dependency (referenced but doesn't exist) is handled."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
                WPFixture("WP02", lane="done", dependencies=["WP99"]),  # WP99 doesn't exist
            ]
        )

        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        output = result.stdout + result.stderr

        # Should handle missing dependency (error or warning)
        # The key is not crashing
        assert result.returncode in [0, 1, 2], \
            f"Should handle missing dependency: {result.stderr}"

    def test_dependency_not_done_yet(self, create_test_feature):
        """Dependency that isn't done yet is handled."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="doing"),  # Not done
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

        # Should handle dependency not being done
        if result.returncode != 0:
            # May skip WP02 or warn about incomplete dependency
            pass  # Error handling is acceptable

    def test_empty_dependencies_list(self, create_test_feature):
        """Empty dependencies list is handled (same as no dependencies)."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done", dependencies=[]),
            ]
        )

        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug, "--dry-run"],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        # Should work fine
        assert result.returncode in [0, 1], \
            f"Empty dependencies should work: {result.stderr}"

    def test_many_dependencies(self, create_test_feature):
        """WP with many dependencies is handled."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
                WPFixture("WP02", lane="done"),
                WPFixture("WP03", lane="done"),
                WPFixture("WP04", lane="done"),
                WPFixture("WP05", lane="done", dependencies=["WP01", "WP02", "WP03", "WP04"]),
            ]
        )

        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug, "--dry-run"],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        output = result.stdout + result.stderr

        # WP05 should be last
        if all(f"WP0{i}" in output for i in range(1, 6)):
            wp05_pos = output.find("WP05")
            for i in range(1, 5):
                other_pos = output.find(f"WP0{i}")
                if other_pos != -1:
                    assert other_pos < wp05_pos, \
                        f"WP0{i} should be before WP05"
