"""
Distribution Test: Stale Detection - Fresh Worktree Detection

CRITICAL: Fresh worktrees must NEVER be flagged as stale.

THE ORIGINAL BUG:
- Symptom: Fresh worktree (just created, no commits) flagged as "stale (idle for ~11.5 hours)"
- Root Cause: Hardcoded "main" in merge-base failed on master/develop repos
- Result: Code fell through to `git log -1` which returned parent branch's old commit

These tests ensure fresh worktrees are NEVER incorrectly flagged.
"""

import subprocess
import json
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
import pytest

pytestmark = [pytest.mark.distribution, pytest.mark.adversarial, pytest.mark.critical]


def setup_git_repo(repo_path: Path, branch_name: str = "main"):
    """Setup a git repository with specified default branch."""
    repo_path.mkdir(parents=True, exist_ok=True)

    subprocess.run(["git", "init"], cwd=repo_path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo_path, capture_output=True)

    subprocess.run(["git", "checkout", "-b", branch_name], cwd=repo_path, capture_output=True)
    (repo_path / "README.md").write_text(f"# Test Repo ({branch_name})")
    subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_path, capture_output=True, check=True)


def create_feature_with_wp(repo: Path, wp_id: str = "WP01", lane: str = "doing"):
    """Create a feature with a single work package."""
    feature_dir = repo / "kitty-specs" / "001-test-feature"
    feature_dir.mkdir(parents=True, exist_ok=True)

    meta = {"feature_id": "001-test-feature", "title": "Test Feature", "mission": "software-dev"}
    (feature_dir / "meta.json").write_text(json.dumps(meta))

    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(exist_ok=True)

    wp_content = f"""---
work_package_id: {wp_id}
title: Test Package
lane: {lane}
dependencies: []
---

# {wp_id}: Test Package

Work package for testing.
"""
    (tasks_dir / f"{wp_id}-test.md").write_text(wp_content)

    subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Add feature"], cwd=repo, capture_output=True, check=True)


class TestFreshWorktreeNeverStale:
    """
    CRITICAL: Fresh worktrees must NEVER be flagged as stale.

    This is THE BUG that shipped to users.
    """

    def test_just_created_worktree_not_stale(self, tmp_path):
        """
        Fresh worktree (0 commits) should not be stale.

        BUG CHECK: Fresh worktrees should be safe.
        """
        repo = tmp_path / "test_repo"
        setup_git_repo(repo, branch_name="main")

        env = {"PATH": subprocess.os.environ.get("PATH", "")}
        env.pop("SPEC_KITTY_TEMPLATE_ROOT", None)

        # Initialize spec-kitty
        result = subprocess.run(
            ["spec-kitty", "init", ".", "--ai", "claude", "--here", "--force"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip(f"Init failed: {result.stderr}")

        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Init"], cwd=repo, capture_output=True, check=True)

        create_feature_with_wp(repo, wp_id="WP01", lane="doing")

        # Implement WP01 (creates fresh worktree with 0 commits)
        impl_result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "implement", "WP01"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # Check status immediately - fresh worktree should NOT be stale
        status_result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "status"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        assert status_result.returncode == 0, f"Status command failed: {status_result.stderr}"
        assert "stale" not in status_result.stdout.lower() or "WP01" not in status_result.stdout, \
            f"Fresh worktree (0 commits) should NOT be stale: {status_result.stdout}"

    def test_fresh_worktree_on_main_branch(self, tmp_path):
        """
        Fresh worktree on main branch.

        BUG CHECK: Baseline - should work.
        """
        repo = tmp_path / "main_repo"
        setup_git_repo(repo, branch_name="main")

        env = {"PATH": subprocess.os.environ.get("PATH", "")}
        env.pop("SPEC_KITTY_TEMPLATE_ROOT", None)

        result = subprocess.run(
            ["spec-kitty", "init", ".", "--ai", "claude", "--here", "--force"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip(f"Init failed: {result.stderr}")

        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Init"], cwd=repo, capture_output=True, check=True)

        create_feature_with_wp(repo)

        # Create fresh worktree
        subprocess.run(
            ["spec-kitty", "agent", "tasks", "implement", "WP01"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        status_result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "status"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        assert "stale" not in status_result.stdout.lower() or "WP01" not in status_result.stdout, \
            f"Fresh worktree on 'main' should NOT be stale: {status_result.stdout}"

    def test_fresh_worktree_on_master_branch(self, tmp_path):
        """
        THE ORIGINAL BUG: Fresh worktree on master

        BUG CHECK: This scenario caused the bug.
        WHY MISSED: Functional tests don't test master repos.
        """
        repo = tmp_path / "master_repo"
        setup_git_repo(repo, branch_name="master")

        env = {"PATH": subprocess.os.environ.get("PATH", "")}
        env.pop("SPEC_KITTY_TEMPLATE_ROOT", None)

        result = subprocess.run(
            ["spec-kitty", "init", ".", "--ai", "claude", "--here", "--force"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip(f"Init failed: {result.stderr}")

        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Init"], cwd=repo, capture_output=True, check=True)

        create_feature_with_wp(repo)

        # Create fresh worktree on master-based repo
        subprocess.run(
            ["spec-kitty", "agent", "tasks", "implement", "WP01"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # THE BUG TEST
        status_result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "status"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # CRITICAL: Before fix, this would show "idle for ~11.5 hours"
        assert "stale" not in status_result.stdout.lower() or "WP01" not in status_result.stdout, \
            f"REGRESSION: Fresh worktree on 'master' flagged as stale (THE ORIGINAL BUG): {status_result.stdout}"

    def test_fresh_worktree_on_develop_branch(self, tmp_path):
        """
        THE ORIGINAL BUG: Fresh worktree on develop

        BUG CHECK: Another scenario that caused the bug.
        WHY MISSED: Functional tests don't test develop repos.
        """
        repo = tmp_path / "develop_repo"
        setup_git_repo(repo, branch_name="develop")

        env = {"PATH": subprocess.os.environ.get("PATH", "")}
        env.pop("SPEC_KITTY_TEMPLATE_ROOT", None)

        result = subprocess.run(
            ["spec-kitty", "init", ".", "--ai", "claude", "--here", "--force"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip(f"Init failed: {result.stderr}")

        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Init"], cwd=repo, capture_output=True, check=True)

        create_feature_with_wp(repo)

        # Create fresh worktree on develop-based repo
        subprocess.run(
            ["spec-kitty", "agent", "tasks", "implement", "WP01"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        status_result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "status"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        assert "stale" not in status_result.stdout.lower() or "WP01" not in status_result.stdout, \
            f"REGRESSION: Fresh worktree on 'develop' flagged as stale: {status_result.stdout}"

    def test_fresh_worktree_no_origin_head(self, tmp_path):
        """
        EXACT USER SCENARIO: Fresh worktree, no origin/HEAD set

        BUG CHECK: User's exact scenario from bug report.
        WHY MISSED: Functional tests always configure origin/HEAD.
        """
        repo = tmp_path / "no_origin_head"
        repo.mkdir(parents=True)

        subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)
        subprocess.run(["git", "checkout", "-b", "main"], cwd=repo, capture_output=True)
        (repo / "README.md").write_text("# Test")
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=repo, capture_output=True, check=True)

        # Add remote but DON'T set origin/HEAD (user's scenario)
        remote_path = tmp_path / "remote.git"
        subprocess.run(["git", "init", "--bare", str(remote_path)], capture_output=True, check=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote_path)], cwd=repo, capture_output=True)

        env = {"PATH": subprocess.os.environ.get("PATH", "")}
        env.pop("SPEC_KITTY_TEMPLATE_ROOT", None)

        result = subprocess.run(
            ["spec-kitty", "init", ".", "--ai", "claude", "--here", "--force"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip(f"Init failed: {result.stderr}")

        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Init"], cwd=repo, capture_output=True, check=True)

        create_feature_with_wp(repo)

        subprocess.run(
            ["spec-kitty", "agent", "tasks", "implement", "WP01"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # USER'S EXACT SCENARIO
        status_result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "status"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        assert status_result.returncode == 0, f"Crashed without origin/HEAD: {status_result.stderr}"
        assert "stale" not in status_result.stdout.lower() or "WP01" not in status_result.stdout, \
            f"USER'S EXACT BUG: Fresh worktree without origin/HEAD should NOT be stale: {status_result.stdout}"


class TestWorktreeWithCommits:
    """
    Worktrees WITH commits should be evaluated correctly.
    """

    def test_recent_commit_not_stale(self, tmp_path):
        """
        Worktree with commit 1 minute ago.

        BUG CHECK: Should respect threshold.
        """
        repo = tmp_path / "recent_commit"
        setup_git_repo(repo, branch_name="main")

        env = {"PATH": subprocess.os.environ.get("PATH", "")}
        env.pop("SPEC_KITTY_TEMPLATE_ROOT", None)

        result = subprocess.run(
            ["spec-kitty", "init", ".", "--ai", "claude", "--here", "--force"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip(f"Init failed: {result.stderr}")

        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Init"], cwd=repo, capture_output=True, check=True)

        create_feature_with_wp(repo)

        subprocess.run(
            ["spec-kitty", "agent", "tasks", "implement", "WP01"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # Make a recent commit in the worktree
        worktree_path = repo / ".worktrees" / "001-test-feature-WP01"
        if worktree_path.exists():
            (worktree_path / "work.txt").write_text("Recent work")
            subprocess.run(["git", "add", "."], cwd=worktree_path, capture_output=True)

            # Commit 2 minutes ago
            recent_timestamp = str(int((datetime.now(timezone.utc) - timedelta(minutes=2)).timestamp()))
            commit_env = os.environ.copy()
            commit_env["GIT_AUTHOR_DATE"] = f"@{recent_timestamp}"
            commit_env["GIT_COMMITTER_DATE"] = f"@{recent_timestamp}"

            subprocess.run(
                ["git", "commit", "-m", "Recent work"],
                cwd=worktree_path,
                capture_output=True,
                env=commit_env,
                check=True
            )

        # Should NOT be stale (2 min < 10 min threshold)
        status_result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "status"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        assert "stale" not in status_result.stdout.lower() or "WP01" not in status_result.stdout, \
            f"Recent commit (2 min ago) should NOT be stale: {status_result.stdout}"

    def test_old_commit_is_stale(self, tmp_path):
        """
        Worktree with commit 12 hours ago.

        BUG CHECK: Should correctly flag old worktrees.
        """
        repo = tmp_path / "old_commit"
        setup_git_repo(repo, branch_name="main")

        env = {"PATH": subprocess.os.environ.get("PATH", "")}
        env.pop("SPEC_KITTY_TEMPLATE_ROOT", None)

        result = subprocess.run(
            ["spec-kitty", "init", ".", "--ai", "claude", "--here", "--force"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip(f"Init failed: {result.stderr}")

        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Init"], cwd=repo, capture_output=True, check=True)

        create_feature_with_wp(repo)

        subprocess.run(
            ["spec-kitty", "agent", "tasks", "implement", "WP01"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # Make an old commit in the worktree
        worktree_path = repo / ".worktrees" / "001-test-feature-WP01"
        if worktree_path.exists():
            (worktree_path / "work.txt").write_text("Old work")
            subprocess.run(["git", "add", "."], cwd=worktree_path, capture_output=True)

            # Commit 12 hours ago
            old_timestamp = str(int((datetime.now(timezone.utc) - timedelta(hours=12)).timestamp()))
            commit_env = os.environ.copy()
            commit_env["GIT_AUTHOR_DATE"] = f"@{old_timestamp}"
            commit_env["GIT_COMMITTER_DATE"] = f"@{old_timestamp}"

            subprocess.run(
                ["git", "commit", "-m", "Old work"],
                cwd=worktree_path,
                capture_output=True,
                env=commit_env,
                check=True
            )

        # Should BE stale (12 hours > 10 min threshold)
        status_result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "status"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # Old commit SHOULD be flagged as stale
        if worktree_path.exists():
            assert "stale" in status_result.stdout.lower() and "WP01" in status_result.stdout, \
                f"Old commit (12 hours ago) SHOULD be stale: {status_result.stdout}"

    def test_threshold_respected(self, tmp_path):
        """
        Custom threshold should be respected.

        BUG CHECK: Threshold parameter should work.
        """
        repo = tmp_path / "threshold_test"
        setup_git_repo(repo, branch_name="main")

        env = {"PATH": subprocess.os.environ.get("PATH", "")}
        env.pop("SPEC_KITTY_TEMPLATE_ROOT", None)

        result = subprocess.run(
            ["spec-kitty", "init", ".", "--ai", "claude", "--here", "--force"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip(f"Init failed: {result.stderr}")

        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Init"], cwd=repo, capture_output=True, check=True)

        create_feature_with_wp(repo)

        subprocess.run(
            ["spec-kitty", "agent", "tasks", "implement", "WP01"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # Make commit 15 minutes ago
        worktree_path = repo / ".worktrees" / "001-test-feature-WP01"
        if worktree_path.exists():
            (worktree_path / "work.txt").write_text("Work")
            subprocess.run(["git", "add", "."], cwd=worktree_path, capture_output=True)

            timestamp = str(int((datetime.now(timezone.utc) - timedelta(minutes=15)).timestamp()))
            commit_env = os.environ.copy()
            commit_env["GIT_AUTHOR_DATE"] = f"@{timestamp}"
            commit_env["GIT_COMMITTER_DATE"] = f"@{timestamp}"

            subprocess.run(
                ["git", "commit", "-m", "Work"],
                cwd=worktree_path,
                capture_output=True,
                env=commit_env,
                check=True
            )

        # Check with threshold=30 (15 min < 30 min, should NOT be stale)
        status_result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "status", "--stale-threshold", "30"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # 15 min commit with 30 min threshold should NOT be stale
        if "--stale-threshold" in subprocess.run(
            ["spec-kitty", "agent", "tasks", "status", "--help"],
            capture_output=True,
            text=True
        ).stdout:
            assert "stale" not in status_result.stdout.lower() or "WP01" not in status_result.stdout, \
                f"Commit (15 min) with threshold 30 should NOT be stale: {status_result.stdout}"
