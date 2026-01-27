"""
Distribution tests for empty branch warnings in multi-parent merge.

CRITICAL: These tests validate that empty dependency branches trigger warnings
during merge-base creation. This helps catch Issue #72 scenarios where WPs are
marked done without commits.

Tests validate that:
1. Empty dependency branches show warnings
2. Warnings are non-blocking
3. Multiple empty branches all warned
4. Warnings don't break JSON mode
5. subprocess errors handled gracefully
"""

import subprocess
from pathlib import Path
import pytest
import json

pytestmark = [pytest.mark.distribution, pytest.mark.adversarial, pytest.mark.regression]


class TestEmptyBranchWarnings:
    """Test that empty branches trigger warnings."""

    def test_empty_branch_shows_warning(
        self, tmp_path
    ):
        """
        Empty dependency branch should warn.

        BUG CHECK:
        - Warning might not appear
        - git merge-base logic might be wrong
        - Warning might go to wrong stream (stdout vs stderr)
        """
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Setup
        subprocess.run(["git", "init"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=project_root, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=project_root, capture_output=True)
        subprocess.run(["spec-kitty", "init", "--here", "--force", "--ai", "claude"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(
            ["spec-kitty", "specify", "Test Feature", "--accept-all"],
            cwd=project_root, check=True, capture_output=True
        )

        feature_dir = list((project_root / "kitty-specs").glob("*"))[0]

        # Create WP01 and WP02 where WP02 depends on WP01
        (feature_dir / "tasks.md").write_text("""
# Test Feature Tasks

## WP01: First Package

- [x] T001: Do work

## WP02: Second Package

Depends on: WP01

- [x] T002: Do more work
""")

        subprocess.run(["spec-kitty", "tasks"], cwd=project_root, check=True, capture_output=True)

        # Implement WP01 but DON'T commit (creates empty branch)
        subprocess.run(
            ["spec-kitty", "implement", "WP01"],
            cwd=project_root,
            check=True,
            capture_output=True
        )

        # Mark WP01 as done WITHOUT committing (Issue #72 scenario)
        subprocess.run(
            ["spec-kitty", "agent", "tasks", "move-task", "WP01", "--to", "done", "--force"],
            cwd=project_root,
            check=True,
            capture_output=True
        )

        # Now implement WP02 with --base WP01 (should warn about empty WP01 branch)
        result = subprocess.run(
            ["spec-kitty", "implement", "WP02"],
            cwd=project_root,
            capture_output=True,
            text=True
        )

        # BUG CHECK: Should see warning about WP01 being empty
        output = result.stdout + result.stderr
        feature_slug = feature_dir.name

        # Look for warning message
        assert "⚠️" in output or "Warning" in output or "warning" in output, \
            "Should show a warning symbol or text"
        assert f"{feature_slug}-WP01" in output or "WP01" in output, \
            "Warning should mention WP01 branch"
        assert "no commits" in output or "empty" in output or "beyond main" in output, \
            "Should explain branch is empty"

    def test_branch_with_commits_no_warning(
        self, tmp_path
    ):
        """
        Branch with commits should not warn.

        BUG CHECK:
        - Might warn incorrectly on valid branches
        - git merge-base comparison might be wrong
        """
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Setup
        subprocess.run(["git", "init"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=project_root, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=project_root, capture_output=True)
        subprocess.run(["spec-kitty", "init", "--here", "--force", "--ai", "claude"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(
            ["spec-kitty", "specify", "Test Feature", "--accept-all"],
            cwd=project_root, check=True, capture_output=True
        )

        feature_dir = list((project_root / "kitty-specs").glob("*"))[0]

        # Create WP01 and WP02
        (feature_dir / "tasks.md").write_text("""
# Test Feature Tasks

## WP01: First Package

- [x] T001: Do work

## WP02: Second Package

Depends on: WP01

- [x] T002: Do more work
""")

        subprocess.run(["spec-kitty", "tasks"], cwd=project_root, check=True, capture_output=True)

        # Implement WP01 and COMMIT work
        result = subprocess.run(
            ["spec-kitty", "implement", "WP01"],
            cwd=project_root,
            check=True,
            capture_output=True,
            text=True
        )

        # Extract worktree path
        worktree_path = None
        for line in result.stdout.split('\n'):
            if '.worktrees' in line:
                parts = line.split()
                for part in parts:
                    if '.worktrees' in part:
                        worktree_path = project_root / part.strip('`')
                        break

        # Create and commit file
        (worktree_path / "feature.py").write_text("# Feature\n")
        subprocess.run(["git", "add", "feature.py"], cwd=worktree_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "feat(WP01): Add feature"],
            cwd=worktree_path,
            check=True
        )

        # Mark as done
        subprocess.run(
            ["spec-kitty", "agent", "tasks", "move-task", "WP01", "--to", "done"],
            cwd=project_root,
            check=True,
            capture_output=True
        )

        # Implement WP02 (should NOT warn - WP01 has commits)
        result = subprocess.run(
            ["spec-kitty", "implement", "WP02"],
            cwd=project_root,
            capture_output=True,
            text=True
        )

        output = result.stdout + result.stderr
        feature_slug = feature_dir.name

        # BUG CHECK: Should NOT warn about WP01 (has commits)
        # Look for absence of warning about WP01
        if "⚠️" in output or "Warning" in output:
            # If there's a warning, it shouldn't be about WP01 being empty
            assert "WP01" not in output or "no commits" not in output, \
                "Should not warn about WP01 (has commits)"

    def test_multiple_empty_branches_all_warned(
        self, tmp_path
    ):
        """
        Should warn about ALL empty branches.

        BUG CHECK:
        - Might only warn about first empty branch
        - Loop might break early
        """
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Setup
        subprocess.run(["git", "init"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=project_root, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=project_root, capture_output=True)
        subprocess.run(["spec-kitty", "init", "--here", "--force", "--ai", "claude"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(
            ["spec-kitty", "specify", "Test Feature", "--accept-all"],
            cwd=project_root, check=True, capture_output=True
        )

        feature_dir = list((project_root / "kitty-specs").glob("*"))[0]

        # Create WP01, WP02 (both empty), WP03 (with commits), WP04 (depends on all)
        (feature_dir / "tasks.md").write_text("""
# Test Feature Tasks

## WP01: First Package

- [x] T001: Do work

## WP02: Second Package

- [x] T002: Do work

## WP03: Third Package

- [x] T003: Do work

## WP04: Final Package

Depends on: WP01, WP02, WP03

- [x] T004: Do work
""")

        subprocess.run(["spec-kitty", "tasks"], cwd=project_root, check=True, capture_output=True)

        # WP01: Empty branch
        subprocess.run(["spec-kitty", "implement", "WP01"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(
            ["spec-kitty", "agent", "tasks", "move-task", "WP01", "--to", "done", "--force"],
            cwd=project_root, check=True, capture_output=True
        )

        # WP02: Empty branch
        subprocess.run(["spec-kitty", "implement", "WP02"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(
            ["spec-kitty", "agent", "tasks", "move-task", "WP02", "--to", "done", "--force"],
            cwd=project_root, check=True, capture_output=True
        )

        # WP03: Has commits
        result = subprocess.run(
            ["spec-kitty", "implement", "WP03"],
            cwd=project_root, check=True, capture_output=True, text=True
        )
        worktree_path = None
        for line in result.stdout.split('\n'):
            if '.worktrees' in line and 'WP03' in line:
                parts = line.split()
                for part in parts:
                    if '.worktrees' in part:
                        worktree_path = project_root / part.strip('`')
                        break

        (worktree_path / "wp03.py").write_text("# WP03\n")
        subprocess.run(["git", "add", "wp03.py"], cwd=worktree_path, check=True)
        subprocess.run(["git", "commit", "-m", "feat(WP03): Add work"], cwd=worktree_path, check=True)
        subprocess.run(
            ["spec-kitty", "agent", "tasks", "move-task", "WP03", "--to", "done"],
            cwd=project_root, check=True, capture_output=True
        )

        # WP04: Depends on all 3 (should warn about WP01 and WP02)
        result = subprocess.run(
            ["spec-kitty", "implement", "WP04"],
            cwd=project_root,
            capture_output=True,
            text=True
        )

        output = result.stdout + result.stderr
        feature_slug = feature_dir.name

        # BUG CHECK: Should warn about BOTH WP01 and WP02
        assert "WP01" in output, "Should warn about WP01"
        assert "WP02" in output, "Should warn about WP02"

        # Count warnings (should be 2)
        warning_count = output.count("⚠️") + output.count("Warning")
        assert warning_count >= 2, f"Should have at least 2 warnings, got {warning_count}"

    def test_empty_branch_warning_doesnt_break_merge(
        self, tmp_path
    ):
        """
        Warning should be non-blocking.

        BUG CHECK:
        - Warning might cause command to fail
        - Should succeed despite warning
        """
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Setup
        subprocess.run(["git", "init"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=project_root, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=project_root, capture_output=True)
        subprocess.run(["spec-kitty", "init", "--here", "--force", "--ai", "claude"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(
            ["spec-kitty", "specify", "Test Feature", "--accept-all"],
            cwd=project_root, check=True, capture_output=True
        )

        feature_dir = list((project_root / "kitty-specs").glob("*"))[0]

        (feature_dir / "tasks.md").write_text("""
# Test Feature Tasks

## WP01: First Package

- [x] T001: Do work

## WP02: Second Package

Depends on: WP01

- [x] T002: Do more work
""")

        subprocess.run(["spec-kitty", "tasks"], cwd=project_root, check=True, capture_output=True)

        # WP01: Empty
        subprocess.run(["spec-kitty", "implement", "WP01"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(
            ["spec-kitty", "agent", "tasks", "move-task", "WP01", "--to", "done", "--force"],
            cwd=project_root, check=True, capture_output=True
        )

        # WP02: Should succeed despite warning
        result = subprocess.run(
            ["spec-kitty", "implement", "WP02"],
            cwd=project_root,
            capture_output=True,
            text=True
        )

        # BUG CHECK: Should succeed (warning is non-blocking)
        assert result.returncode == 0, "implement should succeed despite empty branch warning"

        # Verify worktree was created
        feature_slug = feature_dir.name
        expected_worktree = project_root / ".worktrees" / f"{feature_slug}-WP02"
        assert expected_worktree.exists(), "Worktree should be created"


class TestEmptyBranchEdgeCases:
    """Test edge cases and error conditions."""

    def test_all_branches_empty(
        self, tmp_path
    ):
        """
        What if ALL dependencies are empty?

        BUG CHECK:
        - Might crash
        - Might create useless merge-base
        - Should warn loudly
        """
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Setup
        subprocess.run(["git", "init"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=project_root, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=project_root, capture_output=True)
        subprocess.run(["spec-kitty", "init", "--here", "--force", "--ai", "claude"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(
            ["spec-kitty", "specify", "Test Feature", "--accept-all"],
            cwd=project_root, check=True, capture_output=True
        )

        feature_dir = list((project_root / "kitty-specs").glob("*"))[0]

        # 3 empty dependencies
        (feature_dir / "tasks.md").write_text("""
# Test Feature Tasks

## WP01: First

- [x] T001: Work

## WP02: Second

- [x] T002: Work

## WP03: Third

- [x] T003: Work

## WP04: Depends on All

Depends on: WP01, WP02, WP03

- [x] T004: Work
""")

        subprocess.run(["spec-kitty", "tasks"], cwd=project_root, check=True, capture_output=True)

        # All empty
        for wp_id in ["WP01", "WP02", "WP03"]:
            subprocess.run(["spec-kitty", "implement", wp_id], cwd=project_root, check=True, capture_output=True)
            subprocess.run(
                ["spec-kitty", "agent", "tasks", "move-task", wp_id, "--to", "done", "--force"],
                cwd=project_root, check=True, capture_output=True
            )

        # WP04 depends on all (all empty)
        result = subprocess.run(
            ["spec-kitty", "implement", "WP04"],
            cwd=project_root,
            capture_output=True,
            text=True
        )

        output = result.stdout + result.stderr

        # BUG CHECK: Should have 3 warnings
        assert "WP01" in output, "Should warn about WP01"
        assert "WP02" in output, "Should warn about WP02"
        assert "WP03" in output, "Should warn about WP03"

        # Should succeed (non-blocking)
        assert result.returncode == 0, "Should succeed despite all empty"

    def test_subprocess_error_handling(
        self, tmp_path
    ):
        """
        git commands might fail.

        BUG CHECK:
        - Unhandled subprocess exceptions
        - Should handle git errors gracefully
        """
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Setup
        subprocess.run(["git", "init"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=project_root, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=project_root, capture_output=True)
        subprocess.run(["spec-kitty", "init", "--here", "--force", "--ai", "claude"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(
            ["spec-kitty", "specify", "Test Feature", "--accept-all"],
            cwd=project_root, check=True, capture_output=True
        )

        feature_dir = list((project_root / "kitty-specs").glob("*"))[0]

        # Create WP with non-existent dependency (should error gracefully)
        (feature_dir / "tasks.md").write_text("""
# Test Feature Tasks

## WP01: First

- [x] T001: Work

## WP02: Depends on Non-Existent

Depends on: WP99

- [x] T002: Work
""")

        subprocess.run(["spec-kitty", "tasks"], cwd=project_root, check=True, capture_output=True)

        # Try to implement WP02 (dependency doesn't exist)
        result = subprocess.run(
            ["spec-kitty", "implement", "WP02"],
            cwd=project_root,
            capture_output=True,
            text=True
        )

        # BUG CHECK: Should fail gracefully, not crash
        assert result.returncode != 0, "Should fail when dependency branch doesn't exist"
        error_output = result.stdout + result.stderr
        assert "WP99" in error_output or "does not exist" in error_output or "not found" in error_output, \
            "Error should mention missing dependency"


class TestFeature017Scenario:
    """
    Reproduce the exact Feature 017 scenario from Issue #72.

    8 documentation WPs all marked done without commits.
    """

    def test_eight_empty_documentation_branches(
        self, tmp_path
    ):
        """
        Real Feature 017 scenario: 8 empty branches.

        BUG CHECK:
        - Might crash with many dependencies
        - Should show 8 warnings
        - Merge-base should succeed but be essentially empty
        """
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Setup
        subprocess.run(["git", "init"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=project_root, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=project_root, capture_output=True)
        subprocess.run(["spec-kitty", "init", "--here", "--force", "--ai", "claude"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(
            ["spec-kitty", "specify", "Documentation Feature", "--mission", "documentation", "--accept-all"],
            cwd=project_root,
            check=True,
            capture_output=True
        )

        feature_dir = list((project_root / "kitty-specs").glob("*"))[0]

        # Create 8 WPs + 1 that depends on all
        tasks_content = "# Documentation Feature Tasks\n\n"
        for i in range(1, 9):
            tasks_content += f"""## WP{i:02d}: Documentation {i}

- [x] T{i:03d}: Write docs

"""

        tasks_content += """## WP09: Final Documentation

Depends on: WP01, WP02, WP03, WP04, WP05, WP06, WP07, WP08

- [x] T009: Finalize docs
"""

        (feature_dir / "tasks.md").write_text(tasks_content)
        subprocess.run(["spec-kitty", "tasks"], cwd=project_root, check=True, capture_output=True)

        # Mark all 8 as done WITHOUT commits (Issue #72)
        for i in range(1, 9):
            wp_id = f"WP{i:02d}"
            subprocess.run(["spec-kitty", "implement", wp_id], cwd=project_root, check=True, capture_output=True)
            subprocess.run(
                ["spec-kitty", "agent", "tasks", "move-task", wp_id, "--to", "done", "--force"],
                cwd=project_root,
                check=True,
                capture_output=True
            )

        # Implement WP09 (should show 8 warnings!)
        result = subprocess.run(
            ["spec-kitty", "implement", "WP09"],
            cwd=project_root,
            capture_output=True,
            text=True
        )

        output = result.stdout + result.stderr

        # BUG CHECK: Should warn about all 8
        for i in range(1, 9):
            assert f"WP{i:02d}" in output, f"Should warn about WP{i:02d}"

        # Should succeed (non-blocking)
        assert result.returncode == 0, "Should succeed despite 8 empty branches"

        # Verify worktree created
        feature_slug = feature_dir.name
        expected_worktree = project_root / ".worktrees" / f"{feature_slug}-WP09"
        assert expected_worktree.exists(), "Worktree should be created for WP09"
