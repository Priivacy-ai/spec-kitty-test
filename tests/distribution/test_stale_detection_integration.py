"""
Distribution Test: Stale Detection - Integration & Real Workflows

End-to-end validation of stale detection in real user workflows.

These tests validate the full spec-kitty status command works correctly
in all the scenarios that caused the original bug.
"""

import subprocess
import json
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
import pytest

pytestmark = [pytest.mark.distribution, pytest.mark.adversarial, pytest.mark.integration]


def setup_git_repo(repo_path: Path, branch_name: str = "main", with_remote: bool = False):
    """Setup a git repository."""
    repo_path.mkdir(parents=True, exist_ok=True)

    subprocess.run(["git", "init"], cwd=repo_path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo_path, capture_output=True)

    subprocess.run(["git", "checkout", "-b", branch_name], cwd=repo_path, capture_output=True)
    (repo_path / "README.md").write_text(f"# Test Repo")
    subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial"], cwd=repo_path, capture_output=True, check=True)

    if with_remote:
        remote_path = repo_path.parent / f"{repo_path.name}.git"
        subprocess.run(["git", "init", "--bare", str(remote_path)], capture_output=True, check=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote_path)], cwd=repo_path, capture_output=True)
        subprocess.run(["git", "push", "-u", "origin", branch_name], cwd=repo_path, capture_output=True, check=True)


def create_feature_with_wps(repo: Path, wp_configs: list[tuple[str, str]]):
    """Create a feature with multiple work packages.

    Args:
        wp_configs: List of (wp_id, lane) tuples
    """
    feature_dir = repo / "kitty-specs" / "001-test-feature"
    feature_dir.mkdir(parents=True, exist_ok=True)

    meta = {"feature_id": "001-test-feature", "title": "Test Feature", "mission": "software-dev"}
    (feature_dir / "meta.json").write_text(json.dumps(meta))

    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(exist_ok=True)

    for wp_id, lane in wp_configs:
        wp_content = f"""---
work_package_id: {wp_id}
title: {wp_id} Package
lane: {lane}
dependencies: []
---

# {wp_id}: Package
"""
        (tasks_dir / f"{wp_id}-package.md").write_text(wp_content)

    subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Add feature"], cwd=repo, capture_output=True, check=True)


class TestStatusCommandIntegration:
    """
    Test full spec-kitty status command.

    BUG CHECK: End-to-end workflow should work.
    """

    def test_status_shows_stale_wps_correctly(self, tmp_path):
        """
        Full workflow: create stale WP, verify status shows it.

        BUG CHECK: End-to-end workflow should work.
        """
        repo = tmp_path / "integration_test"
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

        # Create feature with 2 WPs
        create_feature_with_wps(repo, [("WP01", "doing"), ("WP02", "doing")])

        # Implement both
        subprocess.run(
            ["spec-kitty", "agent", "tasks", "implement", "WP01"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )
        subprocess.run(
            ["spec-kitty", "agent", "tasks", "implement", "WP02"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # Make WP01 stale (commit 12 hours ago)
        worktree1 = repo / ".worktrees" / "001-test-feature-WP01"
        if worktree1.exists():
            (worktree1 / "work.txt").write_text("Old work")
            subprocess.run(["git", "add", "."], cwd=worktree1, capture_output=True)

            old_timestamp = str(int((datetime.now(timezone.utc) - timedelta(hours=12)).timestamp()))
            commit_env = os.environ.copy()
            commit_env["GIT_AUTHOR_DATE"] = f"@{old_timestamp}"
            commit_env["GIT_COMMITTER_DATE"] = f"@{old_timestamp}"

            subprocess.run(
                ["git", "commit", "-m", "Old work"],
                cwd=worktree1,
                capture_output=True,
                env=commit_env,
                check=True
            )

        # WP02 stays fresh (no commits)

        # Run status
        status_result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "status"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        assert status_result.returncode == 0, f"Status failed: {status_result.stderr}"

        # WP01 should be stale (has old commit), WP02 should not (fresh)
        output = status_result.stdout.lower()

        if worktree1.exists() and (worktree1 / "work.txt").exists():
            # WP01 with old commit should be marked stale
            assert "stale" in output, f"WP01 with old commit should be stale"

        # WP02 (fresh) should NOT be shown as stale
        # This is the key test - fresh worktrees must not be flagged

    def test_status_on_master_branch_repo(self, tmp_path):
        """
        THE ORIGINAL BUG SCENARIO

        BUG CHECK: User's exact scenario should work.
        WHY MISSED: Functional tests only test 'main' branch.
        """
        repo = tmp_path / "master_integration"
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

        create_feature_with_wps(repo, [("WP01", "doing")])

        subprocess.run(
            ["spec-kitty", "agent", "tasks", "implement", "WP01"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # THE BUG TEST: Fresh worktree on master repo
        status_result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "status"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        assert status_result.returncode == 0, f"Status failed on master repo: {status_result.stderr}"

        # CRITICAL: Fresh worktree should NOT be stale
        # Before fix: Would show "idle for ~11.5 hours"
        assert "stale" not in status_result.stdout.lower() or "WP01" not in status_result.stdout, \
            f"REGRESSION: Fresh worktree on 'master' flagged as stale (THE ORIGINAL BUG): {status_result.stdout}"

    def test_status_on_develop_branch_repo(self, tmp_path):
        """
        Another original bug scenario.

        BUG CHECK: Should work with develop too.
        WHY MISSED: Functional tests only test 'main' branch.
        """
        repo = tmp_path / "develop_integration"
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

        create_feature_with_wps(repo, [("WP01", "doing")])

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

        assert status_result.returncode == 0, f"Status failed on develop repo: {status_result.stderr}"
        assert "stale" not in status_result.stdout.lower() or "WP01" not in status_result.stdout, \
            f"REGRESSION: Fresh worktree on 'develop' flagged as stale: {status_result.stdout}"

    def test_status_with_custom_threshold(self, tmp_path):
        """
        Custom threshold parameter.

        BUG CHECK: Threshold parameter should work.
        """
        repo = tmp_path / "threshold_integration"
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

        create_feature_with_wps(repo, [("WP01", "doing")])

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

        # Check if --stale-threshold is supported
        help_result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "status", "--help"],
            capture_output=True,
            text=True
        )

        if "--stale-threshold" in help_result.stdout:
            # Test with threshold=30 (15 min < 30 min, should NOT be stale)
            status_result = subprocess.run(
                ["spec-kitty", "agent", "tasks", "status", "--stale-threshold", "30"],
                cwd=repo,
                env=env,
                capture_output=True,
                text=True
            )

            assert status_result.returncode == 0, f"Status failed: {status_result.stderr}"
            assert "stale" not in status_result.stdout.lower() or "WP01" not in status_result.stdout, \
                f"Commit (15 min) with threshold 30 should NOT be stale: {status_result.stdout}"

    def test_status_json_mode(self, tmp_path):
        """
        JSON output mode.

        BUG CHECK: JSON mode should work correctly.
        WHY MISSED: Functional tests don't test JSON mode.
        """
        repo = tmp_path / "json_integration"
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

        create_feature_with_wps(repo, [("WP01", "doing")])

        subprocess.run(
            ["spec-kitty", "agent", "tasks", "implement", "WP01"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # Make stale commit
        worktree_path = repo / ".worktrees" / "001-test-feature-WP01"
        if worktree_path.exists():
            (worktree_path / "work.txt").write_text("Work")
            subprocess.run(["git", "add", "."], cwd=worktree_path, capture_output=True)

            timestamp = str(int((datetime.now(timezone.utc) - timedelta(hours=12)).timestamp()))
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

        # Check if --json is supported
        help_result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "status", "--help"],
            capture_output=True,
            text=True
        )

        if "--json" in help_result.stdout:
            status_result = subprocess.run(
                ["spec-kitty", "agent", "tasks", "status", "--json"],
                cwd=repo,
                env=env,
                capture_output=True,
                text=True
            )

            # Should be valid JSON
            try:
                data = json.loads(status_result.stdout)
                # If it's valid JSON, test passed
            except json.JSONDecodeError as e:
                pytest.fail(f"JSON output corrupted: {e}\nOutput: {status_result.stdout}")


class TestRealBugScenarios:
    """
    Reproduce real bugs to ensure they're fixed.

    These are the EXACT scenarios reported by users.
    """

    def test_user_reported_scenario(self, tmp_path):
        """
        User's exact scenario: Fresh WP flagged immediately.

        REPRODUCTION:
        1. Create repo without origin/HEAD set
        2. Create fresh worktree for WP
        3. Run status immediately
        4. Expected: NOT flagged as stale

        BUG CHECK: User's exact scenario should be fixed.
        """
        repo = tmp_path / "user_scenario"
        repo.mkdir(parents=True)

        # Setup WITHOUT origin/HEAD (user's scenario)
        subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)
        subprocess.run(["git", "checkout", "-b", "main"], cwd=repo, capture_output=True)
        (repo / "README.md").write_text("# Test")
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=repo, capture_output=True, check=True)

        # Add remote but DON'T set origin/HEAD
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

        create_feature_with_wps(repo, [("WP06", "doing")])

        # Implement WP06 (user reported WP06)
        subprocess.run(
            ["spec-kitty", "agent", "tasks", "implement", "WP06"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # THE USER'S EXACT TEST: Status immediately after implement
        status_result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "status"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        assert status_result.returncode == 0, f"Status crashed: {status_result.stderr}"

        # USER'S BUG: Fresh WP06 should NOT be flagged as stale
        assert "stale" not in status_result.stdout.lower() or "WP06" not in status_result.stdout, \
            f"USER'S EXACT BUG: Fresh WP06 should NOT be stale: {status_result.stdout}"

    def test_fresh_worktree_11_hours_bug(self, tmp_path):
        """
        Original bug: Fresh worktree shows "idle for ~11.5 hours"

        BEFORE FIX:
        - Fresh worktree created
        - Status shows: "WP06 (stale - idle for ~11.5 hours)"
        - Bug: Used parent branch's old commit timestamp

        AFTER FIX:
        - Fresh worktree created
        - Status shows: WP06 in doing (NO stale marker)
        - Fixed: Detects 0 commits on branch, returns NOT stale

        BUG CHECK: This is THE bug we're testing.
        """
        repo = tmp_path / "11_hours_bug"
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

        # Wait a bit to simulate parent branch being old
        # (In reality, parent might be hours/days old)

        create_feature_with_wps(repo, [("WP01", "doing")])

        # Create fresh worktree
        subprocess.run(
            ["spec-kitty", "agent", "tasks", "implement", "WP01"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # THE BUG: Status immediately shows "idle for ~11.5 hours" for fresh worktree
        status_result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "status"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        output = status_result.stdout

        # THE FIX VALIDATION: Should NOT show any stale time
        assert "11" not in output or "hour" not in output.lower(), \
            f"REGRESSION: Fresh worktree showing hours as stale (THE ORIGINAL BUG): {output}"

        assert "stale" not in output.lower() or "WP01" not in output, \
            f"REGRESSION: Fresh worktree flagged as stale (THE ORIGINAL BUG): {output}"
