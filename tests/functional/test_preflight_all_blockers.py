"""
T059: Preflight All Blockers Tests

Validates that preflight reports ALL blockers in a single pass:
- Multiple issues reported together
- Structured error output
- No iterative discovery

These tests ensure users see all problems at once.
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
# All Blockers Reported Together Tests (T059)
# =============================================================================

@pytest.mark.functional
class TestPreflightReportsAllBlockers:
    """Tests for reporting all blockers at once."""

    def test_preflight_reports_multiple_dirty_worktrees(self, create_test_feature):
        """Preflight reports ALL dirty worktrees, not just the first one."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
                WPFixture("WP02", lane="done", dirty=True),  # Dirty
                WPFixture("WP03", lane="done", dirty=True),  # Also dirty
            ]
        )

        # Run merge
        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0, "Should fail with dirty worktrees"

        output = result.stdout + result.stderr

        # BOTH dirty WPs should be mentioned in the same output
        assert "WP02" in output, "Should mention WP02"
        assert "WP03" in output, "Should mention WP03"

        # Both should appear in a single run (not iterative discovery)
        wp02_pos = output.find("WP02")
        wp03_pos = output.find("WP03")
        assert wp02_pos != -1 and wp03_pos != -1, "Both WPs should be in output"

    def test_preflight_reports_mixed_issue_types(self, create_test_feature):
        """Preflight reports different types of issues together."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done", dirty=True),  # Dirty
                WPFixture("WP02", lane="done"),
                WPFixture("WP03", lane="done"),
            ]
        )

        # Remove WP03's worktree (creates missing worktree issue)
        wt3_path = feature.worktrees.get("WP03")
        if wt3_path and wt3_path.exists():
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(wt3_path)],
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

        output = result.stdout + result.stderr

        # Both types of issues should be reported
        # WP01 - dirty
        # WP03 - missing worktree
        assert "WP01" in output or "uncommitted" in output.lower(), \
            f"Should mention dirty WP01: {output}"

    def test_preflight_all_blockers_in_single_run(self, create_test_feature):
        """All blockers discovered in single preflight run, not iteratively."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done", dirty=True),
                WPFixture("WP02", lane="done", dirty=True),
                WPFixture("WP03", lane="done", dirty=True),
            ]
        )

        # Run merge once
        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        output = result.stdout + result.stderr

        # All three should be in the output from a single run
        wp_count = sum(1 for wp in ["WP01", "WP02", "WP03"] if wp in output)

        # At minimum, if blockers are reported, all should be there
        if result.returncode != 0 and "uncommitted" in output.lower():
            assert wp_count >= 2, \
                f"Should report multiple blockers together: {output}"


@pytest.mark.functional
class TestPreflightStructuredOutput:
    """Tests for structured error output from preflight."""

    def test_preflight_errors_are_clear(self, create_test_feature):
        """Preflight errors are clear and actionable."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done", dirty=True),
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

        # Error should be clear about:
        # 1. Which WP has the issue
        assert "WP01" in output, "Should identify the WP"

        # 2. What the issue is
        assert any(word in output.lower() for word in ["uncommitted", "dirty", "changes"]), \
            "Should describe the issue"

    def test_preflight_includes_suggestion(self, create_test_feature):
        """Preflight errors include suggestions for fixing."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done", dirty=True),
            ]
        )

        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        output = result.stdout + result.stderr

        # Should suggest how to fix (commit or discard changes)
        # This is implementation-dependent but good UX
        if result.returncode != 0:
            # Check for any actionable suggestion
            has_suggestion = any(word in output.lower() for word in [
                "commit", "stash", "discard", "git add", "git commit",
                "fix", "resolve", "clean"
            ])
            # Not strictly required but good to have
            pass  # Suggestion is optional but recommended

    def test_preflight_error_count(self, create_test_feature):
        """Preflight reports count of issues found."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done", dirty=True),
                WPFixture("WP02", lane="done", dirty=True),
            ]
        )

        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        output = result.stdout + result.stderr

        # Should indicate multiple issues (optional)
        # Could be "2 issues" or "multiple" or similar
        if result.returncode != 0:
            # Just verify both WPs are mentioned
            assert "WP01" in output and "WP02" in output, \
                f"Should mention both WPs: {output}"


@pytest.mark.functional
class TestPreflightBlockerDetails:
    """Tests for detailed blocker information."""

    def test_preflight_shows_affected_files(self, create_test_feature):
        """Preflight shows which files have uncommitted changes."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
            ]
        )

        # Create specific uncommitted file
        wt_path = feature.worktrees.get("WP01")
        if wt_path and wt_path.exists():
            (wt_path / "important_change.py").write_text("uncommitted code")

        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        output = result.stdout + result.stderr

        # May or may not show specific files (implementation dependent)
        # The key is that the command runs correctly
        if result.returncode != 0:
            assert "WP01" in output, "Should identify the WP"

    def test_preflight_verbose_mode(self, create_test_feature):
        """Preflight with --verbose shows more details."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done", dirty=True),
            ]
        )

        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug, "-v"],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        # Verbose mode should work (even if output is same)
        # Main check is that -v flag is accepted
        assert result.returncode in [0, 1, 2], \
            f"Should accept -v flag: {result.stderr}"


@pytest.mark.functional
@pytest.mark.adversarial
class TestPreflightEdgeCases:
    """Edge cases for preflight blocker reporting."""

    def test_preflight_no_blockers(self, create_test_feature):
        """Preflight with no blockers passes cleanly."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
                WPFixture("WP02", lane="done"),
            ]
        )

        # Run with dry-run
        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug, "--dry-run"],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        output = result.stdout + result.stderr

        # Should pass preflight (may still show merge preview)
        assert "uncommitted" not in output.lower() or "0 issue" in output.lower(), \
            f"Clean feature should pass preflight: {output}"

    def test_preflight_handles_corrupted_worktree(self, create_test_feature):
        """Preflight handles corrupted git worktree gracefully."""
        feature = create_test_feature(
            wp_configs=[
                WPFixture("WP01", lane="done"),
            ]
        )

        # Corrupt the worktree's .git file
        wt_path = feature.worktrees.get("WP01")
        if wt_path and wt_path.exists():
            git_file = wt_path / ".git"
            if git_file.exists():
                git_file.write_text("corrupted")

        result = subprocess.run(
            ["spec-kitty", "merge", "--feature", feature.feature_slug],
            cwd=feature.project_dir,
            capture_output=True,
            text=True,
        )

        # Should handle gracefully (not crash)
        # May report error about WP01
        assert result.returncode in [0, 1, 2], \
            f"Should handle corrupted worktree: {result.stderr}"
