"""
Distribution tests for done transition validation (Issue #72).

CRITICAL: These tests validate the fix for Issue #72 where agents marked WPs as "done"
without committing their implementation, causing empty branches and broken dependencies.

Tests validate that:
1. Uncommitted changes block done transitions
2. --force flag bypasses validation
3. Error messages are helpful
4. Validation doesn't break valid workflows
5. for_review validation still works
"""

import subprocess
from pathlib import Path
import pytest

pytestmark = [pytest.mark.distribution, pytest.mark.adversarial, pytest.mark.regression]


class TestDoneValidationErrors:
    """Test that uncommitted work BLOCKS done transition."""

    def test_uncommitted_files_block_done_transition(self, tmp_path):
        """
        CRITICAL: Can't move to done with uncommitted files.

        BUG CHECK:
        - Might still allow transition (validation not working)
        - Might only check for_review, not done
        - Might have typo in error message (says "for_review" instead of "done")
        """
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Initialize git repo first
        subprocess.run(["git", "init"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=project_root, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=project_root, capture_output=True)

        # Initialize spec-kitty project
        subprocess.run(
            ["spec-kitty", "init", "--here", "--force", "--ai", "claude"],
            cwd=project_root,
            check=True,
            capture_output=True
        )

        # Create a feature
        subprocess.run(
            ["spec-kitty", "specify", "Test Feature", "--accept-all"],
            cwd=project_root,
            check=True,
            capture_output=True
        )

        # Generate tasks (single WP for simplicity)
        feature_dir = list((project_root / "kitty-specs").glob("*"))[0]
        tasks_md = feature_dir / "tasks.md"
        tasks_md.write_text("""
# Test Feature Tasks

## WP01: Test Work Package

- [x] T001: Create test file
""")

        subprocess.run(
            ["spec-kitty", "tasks"],
            cwd=project_root,
            check=True,
            capture_output=True
        )

        # Implement WP01
        result = subprocess.run(
            ["spec-kitty", "implement", "WP01"],
            cwd=project_root,
            check=True,
            capture_output=True,
            text=True
        )

        # Find worktree path from output
        worktree_path = None
        for line in result.stdout.split('\n'):
            if '.worktrees' in line and 'cd' in line:
                # Extract path from cd command
                parts = line.split()
                for part in parts:
                    if '.worktrees' in part:
                        worktree_path = project_root / part.strip('`')
                        break

        assert worktree_path and worktree_path.exists(), "Worktree not created"

        # Create uncommitted file in worktree
        (worktree_path / "test_file.py").write_text("# Test file\nprint('hello')\n")

        # Try to move to done WITHOUT committing (should FAIL)
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "move-task", "WP01", "--to", "done"],
            cwd=project_root,
            capture_output=True,
            text=True
        )

        # BUG CHECK: Should fail, not succeed
        assert result.returncode != 0, "Done transition should be blocked with uncommitted files!"

        # BUG CHECK: Error should mention "done" not "for_review"
        error_output = result.stdout + result.stderr
        assert "Cannot move WP01 to done" in error_output, "Error should mention 'done'"
        assert "test_file.py" in error_output or "Uncommitted" in error_output, \
            "Error should mention uncommitted files"

        # BUG CHECK: Error should suggest git commit
        assert "git commit" in error_output, "Error should suggest committing"

    def test_untracked_files_block_done_transition(
        self, tmp_path
    ):
        """
        Untracked files should also block done.

        BUG CHECK:
        - Might only check modified files, not untracked
        - git status --porcelain shows untracked with "??"
        """
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Setup (same as above)
        subprocess.run(["spec-kitty", "init"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(
            ["spec-kitty", "specify", "Test Feature", "--accept-all"],
            cwd=project_root, check=True, capture_output=True
        )

        feature_dir = list((project_root / "kitty-specs").glob("*"))[0]
        (feature_dir / "tasks.md").write_text("""
# Test Feature Tasks

## WP01: Test Work Package

- [x] T001: Create test file
""")

        subprocess.run(["spec-kitty", "tasks"], cwd=project_root, check=True, capture_output=True)
        result = subprocess.run(
            ["spec-kitty", "implement", "WP01"],
            cwd=project_root, check=True, capture_output=True, text=True
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

        # Create NEW untracked file (git status shows as "??")
        (worktree_path / "new_file.py").write_text("# New file\n")

        # Try to move to done (should FAIL)
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "move-task", "WP01", "--to", "done"],
            cwd=project_root,
            capture_output=True,
            text=True
        )

        # BUG CHECK: Should catch untracked files too
        assert result.returncode != 0, "Should block done with untracked files"
        assert "new_file.py" in (result.stdout + result.stderr) or \
               "Uncommitted" in (result.stdout + result.stderr), \
               "Should mention untracked file"

    def test_staged_but_not_committed_blocks_done(
        self, tmp_path
    ):
        """
        Files staged but not committed should block.

        BUG CHECK:
        - Might think staged = committed
        - Need to check for commits, not just staged files
        """
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Setup
        subprocess.run(["spec-kitty", "init"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(
            ["spec-kitty", "specify", "Test Feature", "--accept-all"],
            cwd=project_root, check=True, capture_output=True
        )

        feature_dir = list((project_root / "kitty-specs").glob("*"))[0]
        (feature_dir / "tasks.md").write_text("""
# Test Feature Tasks

## WP01: Test Work Package

- [x] T001: Create test file
""")

        subprocess.run(["spec-kitty", "tasks"], cwd=project_root, check=True, capture_output=True)
        result = subprocess.run(
            ["spec-kitty", "implement", "WP01"],
            cwd=project_root, check=True, capture_output=True, text=True
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

        # Create and STAGE file, but DON'T commit
        (worktree_path / "staged_file.py").write_text("# Staged\n")
        subprocess.run(
            ["git", "add", "staged_file.py"],
            cwd=worktree_path,
            check=True
        )

        # Try to move to done (should FAIL)
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "move-task", "WP01", "--to", "done"],
            cwd=project_root,
            capture_output=True,
            text=True
        )

        # BUG CHECK: Staged ≠ committed
        assert result.returncode != 0, "Should block done with staged but uncommitted files"
        error_output = result.stdout + result.stderr
        assert "Staged" in error_output or "uncommitted" in error_output or \
               "staged_file.py" in error_output, \
               "Should mention staged files need committing"

    def test_force_flag_bypasses_done_validation(
        self, tmp_path
    ):
        """
        --force should allow done despite uncommitted files.

        BUG CHECK:
        - --force might not work for done (only for_review)
        - Might have condition: if not force and target == "for_review"
        - Should be: if not force and target in ("for_review", "done")
        """
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Setup
        subprocess.run(["spec-kitty", "init"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(
            ["spec-kitty", "specify", "Test Feature", "--accept-all"],
            cwd=project_root, check=True, capture_output=True
        )

        feature_dir = list((project_root / "kitty-specs").glob("*"))[0]
        (feature_dir / "tasks.md").write_text("""
# Test Feature Tasks

## WP01: Test Work Package

- [x] T001: Create test file
""")

        subprocess.run(["spec-kitty", "tasks"], cwd=project_root, check=True, capture_output=True)
        result = subprocess.run(
            ["spec-kitty", "implement", "WP01"],
            cwd=project_root, check=True, capture_output=True, text=True
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

        # Create uncommitted file
        (worktree_path / "test_file.py").write_text("# Test\n")

        # Try with --force (should SUCCEED)
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "move-task", "WP01", "--to", "done", "--force"],
            cwd=project_root,
            capture_output=True,
            text=True
        )

        # BUG CHECK: --force should work for done too
        assert result.returncode == 0, "--force should bypass done validation"

        # Verify WP is actually in done lane
        wp_file = list((feature_dir / "tasks").glob("WP01*.md"))[0]
        wp_content = wp_file.read_text()
        assert 'lane: "done"' in wp_content or "lane: done" in wp_content, \
            "WP should be moved to done with --force"

    def test_error_message_mentions_uncommitted_files(
        self, tmp_path
    ):
        """
        Error should list specific uncommitted files.

        BUG CHECK:
        - Generic error, not actionable
        - Doesn't list files
        - Doesn't show git commit command
        """
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Setup
        subprocess.run(["spec-kitty", "init"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(
            ["spec-kitty", "specify", "Test Feature", "--accept-all"],
            cwd=project_root, check=True, capture_output=True
        )

        feature_dir = list((project_root / "kitty-specs").glob("*"))[0]
        (feature_dir / "tasks.md").write_text("""
# Test Feature Tasks

## WP01: Test Work Package

- [x] T001: Create test file
""")

        subprocess.run(["spec-kitty", "tasks"], cwd=project_root, check=True, capture_output=True)
        result = subprocess.run(
            ["spec-kitty", "implement", "WP01"],
            cwd=project_root, check=True, capture_output=True, text=True
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

        # Create file with specific name for testing
        (worktree_path / "my_feature.py").write_text("# My feature\n")

        # Try to move to done
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "move-task", "WP01", "--to", "done"],
            cwd=project_root,
            capture_output=True,
            text=True
        )

        error_output = result.stdout + result.stderr

        # BUG CHECK: Error should be actionable
        assert "my_feature.py" in error_output or "Modified files" in error_output, \
            "Error should list specific files"
        assert "git add" in error_output or "git commit" in error_output, \
            "Error should show git commands"
        assert "cd .worktrees" in error_output or worktree_path.name in error_output, \
            "Error should show worktree path"


class TestDoneValidationSuccess:
    """Test that valid workflows still work."""

    def test_committed_work_allows_done_transition(
        self, tmp_path
    ):
        """
        Properly committed work should allow done.

        BUG CHECK:
        - Validation too strict, blocks valid workflow
        - Might require files even when none needed
        """
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Setup
        subprocess.run(["spec-kitty", "init"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(
            ["spec-kitty", "specify", "Test Feature", "--accept-all"],
            cwd=project_root, check=True, capture_output=True
        )

        feature_dir = list((project_root / "kitty-specs").glob("*"))[0]
        (feature_dir / "tasks.md").write_text("""
# Test Feature Tasks

## WP01: Test Work Package

- [x] T001: Create test file
""")

        subprocess.run(["spec-kitty", "tasks"], cwd=project_root, check=True, capture_output=True)
        result = subprocess.run(
            ["spec-kitty", "implement", "WP01"],
            cwd=project_root, check=True, capture_output=True, text=True
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

        # Create file and COMMIT it
        (worktree_path / "feature.py").write_text("# Feature\ndef hello():\n    return 'world'\n")
        subprocess.run(["git", "add", "feature.py"], cwd=worktree_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "feat(WP01): Add feature"],
            cwd=worktree_path,
            check=True
        )

        # Try to move to done (should SUCCEED)
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "move-task", "WP01", "--to", "done"],
            cwd=project_root,
            capture_output=True,
            text=True
        )

        # BUG CHECK: Should succeed with committed work
        assert result.returncode == 0, f"Should allow done with committed work. Error: {result.stderr}"

        # Verify WP is in done lane
        wp_file = list((feature_dir / "tasks").glob("WP01*.md"))[0]
        wp_content = wp_file.read_text()
        assert 'lane: "done"' in wp_content or "lane: done" in wp_content, \
            "WP should be in done lane"

    def test_for_review_then_done_without_new_commits(
        self, tmp_path
    ):
        """
        If WP passed for_review, done shouldn't require new commits.

        BUG CHECK:
        - Might require commits between for_review and done
        - Should only validate when moving FROM planned/doing
        """
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Setup
        subprocess.run(["spec-kitty", "init"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(
            ["spec-kitty", "specify", "Test Feature", "--accept-all"],
            cwd=project_root, check=True, capture_output=True
        )

        feature_dir = list((project_root / "kitty-specs").glob("*"))[0]
        (feature_dir / "tasks.md").write_text("""
# Test Feature Tasks

## WP01: Test Work Package

- [x] T001: Create test file
""")

        subprocess.run(["spec-kitty", "tasks"], cwd=project_root, check=True, capture_output=True)
        result = subprocess.run(
            ["spec-kitty", "implement", "WP01"],
            cwd=project_root, check=True, capture_output=True, text=True
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

        # Commit work
        (worktree_path / "feature.py").write_text("# Feature\n")
        subprocess.run(["git", "add", "feature.py"], cwd=worktree_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "feat(WP01): Add feature"],
            cwd=worktree_path,
            check=True
        )

        # Move to for_review (validates commits)
        subprocess.run(
            ["spec-kitty", "agent", "tasks", "move-task", "WP01", "--to", "for_review"],
            cwd=project_root,
            check=True,
            capture_output=True
        )

        # Later move to done WITHOUT new commits (should SUCCEED)
        # Because validation already passed during for_review
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "move-task", "WP01", "--to", "done"],
            cwd=project_root,
            capture_output=True,
            text=True
        )

        # BUG CHECK: Should succeed (already validated)
        assert result.returncode == 0, \
            "Should allow for_review → done without new commits (already validated)"


class TestBackwardCompatibility:
    """Test that existing workflows aren't broken."""

    def test_for_review_validation_still_works(
        self, tmp_path
    ):
        """
        Existing for_review validation should be unchanged.

        BUG CHECK:
        - Might accidentally remove for_review validation
        - Should still block for_review with uncommitted
        """
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Setup
        subprocess.run(["spec-kitty", "init"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(
            ["spec-kitty", "specify", "Test Feature", "--accept-all"],
            cwd=project_root, check=True, capture_output=True
        )

        feature_dir = list((project_root / "kitty-specs").glob("*"))[0]
        (feature_dir / "tasks.md").write_text("""
# Test Feature Tasks

## WP01: Test Work Package

- [x] T001: Create test file
""")

        subprocess.run(["spec-kitty", "tasks"], cwd=project_root, check=True, capture_output=True)
        result = subprocess.run(
            ["spec-kitty", "implement", "WP01"],
            cwd=project_root, check=True, capture_output=True, text=True
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

        # Create uncommitted file
        (worktree_path / "test.py").write_text("# Test\n")

        # Try: move to for_review with uncommitted (should still error)
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "move-task", "WP01", "--to", "for_review"],
            cwd=project_root,
            capture_output=True,
            text=True
        )

        # BUG CHECK: for_review validation not broken
        assert result.returncode != 0, "for_review validation should still work"
        assert "Cannot move WP01 to for_review" in (result.stdout + result.stderr), \
            "Error should mention for_review"


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_no_commits_at_all_blocks_done(
        self, tmp_path
    ):
        """
        WP with NO commits beyond main should be blocked.

        This is the original Issue #72 scenario.
        """
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Setup
        subprocess.run(["spec-kitty", "init"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(
            ["spec-kitty", "specify", "Test Feature", "--accept-all"],
            cwd=project_root, check=True, capture_output=True
        )

        feature_dir = list((project_root / "kitty-specs").glob("*"))[0]
        (feature_dir / "tasks.md").write_text("""
# Test Feature Tasks

## WP01: Test Work Package

- [x] T001: Create test file
""")

        subprocess.run(["spec-kitty", "tasks"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(
            ["spec-kitty", "implement", "WP01"],
            cwd=project_root, check=True, capture_output=True
        )

        # DON'T create any files, DON'T commit anything
        # Try to move to done immediately
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "move-task", "WP01", "--to", "done"],
            cwd=project_root,
            capture_output=True,
            text=True
        )

        # Should FAIL - this is exactly Issue #72
        assert result.returncode != 0, "Should block done with no commits"
        error_output = result.stdout + result.stderr
        assert "No implementation commits" in error_output or \
               "no commits" in error_output.lower(), \
               "Should mention missing commits"
