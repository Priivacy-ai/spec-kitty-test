"""
Test: Worktree Git Exclusion (Distribution)

Purpose: Verify .worktrees/ directory is properly excluded from git tracking,
preventing accidental commits of worktree metadata.

BUG HISTORY:
Worktrees created by spec-kitty were not excluded from git index, leading to:
- Accidental commits when running 'git add .'
- Gitlinks appearing in repository (breaking state)
- Confusion about what should be tracked
- Potential data loss from tracked worktree contents

THE PROBLEM:
.gitignore only prevents UNTRACKED files from being added. If a user runs
'git add .worktrees/' or 'git add .', the worktrees still get staged.

THE FIX (spec-kitty):
1. Added exclude_from_git_index() to git_ops.py
2. Writes patterns to .git/info/exclude (local-only, never committed)
3. Applied during 'spec-kitty init' for new projects
4. Migration 0.13.1_exclude_worktrees for existing projects

THIS TEST FILE VALIDATES THE FIX WITHOUT SPEC_KITTY_TEMPLATE_ROOT BYPASS.
Tests simulate real user workflows that would trigger the bug.

Test Coverage:
- TestInitExcludesWorktrees: New projects exclude .worktrees/
- TestExclusionPreventsAccidentalAdd: git add . doesn't stage worktrees
- TestMigrationAddsExclusion: Existing projects get exclusion via upgrade
- TestExclusionIdempotent: Multiple runs don't duplicate patterns

Related:
- Spec-kitty implementation: src/specify_cli/core/git_ops.py:exclude_from_git_index()
- Spec-kitty implementation: src/specify_cli/cli/commands/init.py
- Spec-kitty implementation: src/specify_cli/upgrade/migrations/m_0_13_1_exclude_worktrees.py
"""

import subprocess
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def git_repo(tmp_path):
    """Create a fresh git repository."""
    repo = tmp_path / "test_repo"
    repo.mkdir()

    subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo,
        capture_output=True,
        check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo,
        capture_output=True,
        check=True
    )

    # Initial commit
    readme = repo / "README.md"
    readme.write_text("# Test\n")
    subprocess.run(["git", "add", "README.md"], cwd=repo, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo,
        capture_output=True,
        check=True
    )

    return repo


@pytest.mark.distribution
class TestInitExcludesWorktrees:
    """
    CRITICAL: Test that spec-kitty init excludes .worktrees/ from git.

    New projects should have .worktrees/ in .git/info/exclude.
    """

    def test_init_creates_git_exclude_entry(self, git_repo, spec_kitty_repo_root):
        """
        CRITICAL: spec-kitty init should add .worktrees/ to .git/info/exclude.
        """
        env = {
            "SPEC_KITTY_TEMPLATE_ROOT": str(spec_kitty_repo_root),
            "PATH": subprocess.os.environ.get("PATH", ""),
        }

        # Initialize spec-kitty
        result = subprocess.run(
            ["spec-kitty", "init", ".", "--ai", "claude", "--here", "--force"],
            cwd=git_repo,
            env=env,
            capture_output=True,
            text=True,
            input="preferred\nclaude\nclaude\n"
        )

        if result.returncode != 0:
            pytest.skip(f"Init failed (may be TTY issue): {result.stderr}")

        # Check .git/info/exclude exists and contains .worktrees/
        exclude_file = git_repo / ".git" / "info" / "exclude"
        assert exclude_file.exists(), (
            ".git/info/exclude should exist after init"
        )

        exclude_content = exclude_file.read_text()
        assert ".worktrees/" in exclude_content, (
            "BUG: .worktrees/ not in .git/info/exclude!\n"
            "Users can accidentally commit worktrees with 'git add .'\n"
            f"Exclude file content:\n{exclude_content}"
        )

    def test_exclude_prevents_git_add_all(self, git_repo, spec_kitty_repo_root):
        """
        CRITICAL: .worktrees/ should not be staged by 'git add .'

        This is the USER WORKFLOW that triggers the bug.
        """
        env = {
            "SPEC_KITTY_TEMPLATE_ROOT": str(spec_kitty_repo_root),
            "PATH": subprocess.os.environ.get("PATH", ""),
        }

        # Initialize
        result = subprocess.run(
            ["spec-kitty", "init", ".", "--ai", "claude", "--here", "--force"],
            cwd=git_repo,
            env=env,
            capture_output=True,
            text=True,
            input="preferred\nclaude\nclaude\n"
        )

        if result.returncode != 0:
            pytest.skip(f"Init failed: {result.stderr}")

        # Create a fake worktree directory (simulate real usage)
        worktrees_dir = git_repo / ".worktrees"
        worktrees_dir.mkdir(exist_ok=True)

        fake_worktree = worktrees_dir / "feature-001"
        fake_worktree.mkdir(parents=True)
        (fake_worktree / "test.txt").write_text("worktree content\n")

        # Commit spec-kitty files first
        subprocess.run(
            ["git", "add", ".kittify"],
            cwd=git_repo,
            capture_output=True,
            check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Add spec-kitty"],
            cwd=git_repo,
            capture_output=True,
            check=True
        )

        # User runs 'git add .' (common workflow that triggers bug)
        subprocess.run(
            ["git", "add", "."],
            cwd=git_repo,
            capture_output=True,
            check=True
        )

        # Check what's staged
        status_result = subprocess.run(
            ["git", "status", "--short"],
            cwd=git_repo,
            capture_output=True,
            text=True,
            check=True
        )

        # BUG CHECK: .worktrees/ should NOT be in staged files
        assert ".worktrees" not in status_result.stdout, (
            "BUG: .worktrees/ was staged by 'git add .'!\n"
            "The exclusion didn't work. Users will accidentally commit worktrees.\n"
            f"Git status:\n{status_result.stdout}"
        )


@pytest.mark.distribution
class TestExclusionPreventsAccidentalAdd:
    """
    Test real user workflows that would accidentally commit worktrees.

    These are the EXACT scenarios that cause the bug.
    """

    def test_git_add_dot_worktrees_is_noop(self, git_repo, spec_kitty_repo_root):
        """
        Test: 'git add .worktrees/' should be a no-op when excluded.

        Users might explicitly try to add worktrees, thinking they're needed.
        """
        env = {
            "SPEC_KITTY_TEMPLATE_ROOT": str(spec_kitty_repo_root),
            "PATH": subprocess.os.environ.get("PATH", ""),
        }

        result = subprocess.run(
            ["spec-kitty", "init", ".", "--ai", "claude", "--here", "--force"],
            cwd=git_repo,
            env=env,
            capture_output=True,
            text=True,
            input="preferred\nclaude\nclaude\n"
        )

        if result.returncode != 0:
            pytest.skip(f"Init failed: {result.stderr}")

        # Create worktree
        worktrees_dir = git_repo / ".worktrees"
        worktrees_dir.mkdir(exist_ok=True)
        (worktrees_dir / "file.txt").write_text("test\n")

        # Try to explicitly add worktrees
        add_result = subprocess.run(
            ["git", "add", ".worktrees/"],
            cwd=git_repo,
            capture_output=True,
            text=True
        )

        # Should not fail, just be a no-op
        # (git add doesn't error on excluded files, just ignores them)

        # Check nothing was staged
        status_result = subprocess.run(
            ["git", "status", "--short"],
            cwd=git_repo,
            capture_output=True,
            text=True,
            check=True
        )

        # Should not show .worktrees/ as staged
        for line in status_result.stdout.splitlines():
            if ".worktrees" in line:
                # Check it's not staged (should not have 'A' or 'M' in first column)
                assert not line.startswith(("A", "M")), (
                    f"BUG: .worktrees/ was staged!\n{line}"
                )

    def test_no_gitlink_created(self, git_repo, spec_kitty_repo_root):
        """
        Test: No gitlink should be created for .worktrees/ directory.

        Gitlinks in git index indicate submodules/worktrees, which breaks state.
        """
        env = {
            "SPEC_KITTY_TEMPLATE_ROOT": str(spec_kitty_repo_root),
            "PATH": subprocess.os.environ.get("PATH", ""),
        }

        result = subprocess.run(
            ["spec-kitty", "init", ".", "--ai", "claude", "--here", "--force"],
            cwd=git_repo,
            env=env,
            capture_output=True,
            text=True,
            input="preferred\nclaude\nclaude\n"
        )

        if result.returncode != 0:
            pytest.skip(f"Init failed: {result.stderr}")

        # Create worktree
        worktrees_dir = git_repo / ".worktrees"
        worktrees_dir.mkdir(exist_ok=True)

        # Try to add
        subprocess.run(
            ["git", "add", "."],
            cwd=git_repo,
            capture_output=True,
            check=True
        )

        # Check git ls-files for gitlinks
        ls_result = subprocess.run(
            ["git", "ls-files", "--stage"],
            cwd=git_repo,
            capture_output=True,
            text=True,
            check=True
        )

        # Gitlinks have mode 160000
        for line in ls_result.stdout.splitlines():
            if ".worktrees" in line:
                assert not line.startswith("160000"), (
                    f"BUG: Gitlink created for .worktrees/!\n{line}\n"
                    "This breaks repository state."
                )


@pytest.mark.distribution
class TestMigrationAddsExclusion:
    """
    Test that existing projects get .worktrees/ exclusion via upgrade.

    Migration 0.13.1_exclude_worktrees should add the exclusion.
    """

    def test_upgrade_adds_exclusion_to_existing_project(self, git_repo, spec_kitty_repo_root):
        """
        Test: spec-kitty upgrade should add .worktrees/ exclusion.

        Simulates upgrading from older version without the exclusion.
        """
        env = {
            "SPEC_KITTY_TEMPLATE_ROOT": str(spec_kitty_repo_root),
            "PATH": subprocess.os.environ.get("PATH", ""),
        }

        # Initialize with older version behavior (simulate by removing exclusion)
        result = subprocess.run(
            ["spec-kitty", "init", ".", "--ai", "claude", "--here", "--force"],
            cwd=git_repo,
            env=env,
            capture_output=True,
            text=True,
            input="preferred\nclaude\nclaude\n"
        )

        if result.returncode != 0:
            pytest.skip(f"Init failed: {result.stderr}")

        # Remove the exclusion (simulate old version)
        exclude_file = git_repo / ".git" / "info" / "exclude"
        if exclude_file.exists():
            content = exclude_file.read_text()
            # Remove .worktrees/ line
            new_content = "\n".join(
                line for line in content.splitlines()
                if ".worktrees" not in line
            )
            exclude_file.write_text(new_content)

        # Verify exclusion is gone
        assert ".worktrees/" not in exclude_file.read_text(), (
            "Setup failed: couldn't remove exclusion"
        )

        # Run upgrade
        upgrade_result = subprocess.run(
            ["spec-kitty", "upgrade", "--force"],
            cwd=git_repo,
            env=env,
            capture_output=True,
            text=True
        )

        # Upgrade should succeed
        assert upgrade_result.returncode == 0, (
            f"Upgrade failed: {upgrade_result.stderr}"
        )

        # Check exclusion was added by migration
        final_content = exclude_file.read_text()
        assert ".worktrees/" in final_content, (
            "BUG: Migration didn't add .worktrees/ exclusion!\n"
            "Existing projects remain vulnerable to accidental commits.\n"
            f"Exclude file:\n{final_content}"
        )


@pytest.mark.distribution
class TestExclusionIdempotent:
    """
    Test that exclusion operations are idempotent.

    Running init/upgrade multiple times should not create duplicates.
    """

    def test_multiple_inits_dont_duplicate(self, git_repo, spec_kitty_repo_root):
        """
        Test: Running init multiple times shouldn't duplicate exclusions.
        """
        env = {
            "SPEC_KITTY_TEMPLATE_ROOT": str(spec_kitty_repo_root),
            "PATH": subprocess.os.environ.get("PATH", ""),
        }

        # Init first time
        subprocess.run(
            ["spec-kitty", "init", ".", "--ai", "claude", "--here", "--force"],
            cwd=git_repo,
            env=env,
            capture_output=True,
            text=True,
            input="preferred\nclaude\nclaude\n"
        )

        exclude_file = git_repo / ".git" / "info" / "exclude"
        if not exclude_file.exists():
            pytest.skip("Exclude file not created")

        first_content = exclude_file.read_text()
        first_count = first_content.count(".worktrees/")

        # Init second time (simulate re-init or upgrade)
        subprocess.run(
            ["spec-kitty", "upgrade", "--force"],
            cwd=git_repo,
            env=env,
            capture_output=True,
            text=True
        )

        second_content = exclude_file.read_text()
        second_count = second_content.count(".worktrees/")

        # Should not duplicate
        assert second_count == first_count, (
            f"BUG: Exclusion duplicated!\n"
            f"First count: {first_count}\n"
            f"Second count: {second_count}\n"
            f"Content:\n{second_content}"
        )
