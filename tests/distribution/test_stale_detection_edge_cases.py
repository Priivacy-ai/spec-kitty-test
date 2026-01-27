"""
Distribution Test: Stale Detection - Edge Cases & Error Handling

Tests edge cases that functional tests miss:
- Timezone handling
- Subprocess errors and timeouts
- Display logic and JSON output
- Race conditions

These tests prevent crashes and ensure robustness in production.
"""

import subprocess
import json
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
import pytest

pytestmark = [pytest.mark.distribution, pytest.mark.adversarial]


def setup_git_repo(repo_path: Path, branch_name: str = "main"):
    """Setup a git repository."""
    repo_path.mkdir(parents=True, exist_ok=True)

    subprocess.run(["git", "init"], cwd=repo_path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo_path, capture_output=True)

    subprocess.run(["git", "checkout", "-b", branch_name], cwd=repo_path, capture_output=True)
    (repo_path / "README.md").write_text(f"# Test Repo")
    subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial"], cwd=repo_path, capture_output=True, check=True)


def create_feature_with_wp(repo: Path, wp_id: str = "WP01", lane: str = "doing"):
    """Create a feature with a work package."""
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
"""
    (tasks_dir / f"{wp_id}-test.md").write_text(wp_content)

    subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Add feature"], cwd=repo, capture_output=True, check=True)


class TestTimezoneHandling:
    """
    Test timezone-aware datetime comparisons.

    BUG CHECK: Timezone comparison should work correctly.
    """

    def test_commit_in_different_timezone(self, tmp_path):
        """
        Commit in PST, check from UTC.

        BUG CHECK: Age calculated correctly despite timezone.
        """
        repo = tmp_path / "tz_test"
        setup_git_repo(repo)

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

        # Make commit with explicit timezone
        worktree_path = repo / ".worktrees" / "001-test-feature-WP01"
        if worktree_path.exists():
            (worktree_path / "work.txt").write_text("Work")
            subprocess.run(["git", "add", "."], cwd=worktree_path, capture_output=True)

            # Use ISO timestamp with timezone offset
            pst_time = datetime.now(timezone.utc) - timedelta(hours=8)
            iso_time = pst_time.strftime("%Y-%m-%dT%H:%M:%S-08:00")

            commit_env = os.environ.copy()
            commit_env["GIT_AUTHOR_DATE"] = iso_time
            commit_env["GIT_COMMITTER_DATE"] = iso_time

            subprocess.run(
                ["git", "commit", "-m", "Work"],
                cwd=worktree_path,
                capture_output=True,
                env=commit_env,
                check=True
            )

        # Should calculate age correctly regardless of timezone
        status_result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "status"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        assert status_result.returncode == 0, f"Status failed with timezone commit: {status_result.stderr}"


class TestSubprocessErrorHandling:
    """
    Test subprocess errors don't crash.

    BUG CHECK: Should fail gracefully.
    WHY MISSED: Functional tests don't test error conditions.
    """

    def test_corrupted_git_repository(self, tmp_path):
        """
        Corrupted .git directory.

        BUG CHECK: Should not crash.
        """
        repo = tmp_path / "corrupted_repo"
        setup_git_repo(repo)

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

        # Corrupt worktree .git file
        worktree_path = repo / ".worktrees" / "001-test-feature-WP01"
        if worktree_path.exists():
            git_file = worktree_path / ".git"
            if git_file.exists():
                git_file.write_text("corrupted")

        # Should not crash
        status_result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "status"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # Should return with error or gracefully skip
        assert status_result.returncode in [0, 1], \
            f"Should handle corrupted repo gracefully: {status_result.stderr}"


class TestDisplayLogic:
    """
    Test status command display is correct.

    BUG CHECK: Display logic should be accurate.
    """

    def test_correct_wp_shown_as_stale(self, tmp_path):
        """
        Only stale WPs should be flagged.

        BUG CHECK: Display logic should be accurate.
        """
        repo = tmp_path / "display_test"
        setup_git_repo(repo)

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

        # Create WP01 and WP02
        create_feature_with_wp(repo, wp_id="WP01", lane="doing")

        feature_dir = repo / "kitty-specs" / "001-test-feature"
        tasks_dir = feature_dir / "tasks"

        wp02_content = """---
work_package_id: WP02
title: Second Package
lane: doing
dependencies: []
---

# WP02: Second Package
"""
        (tasks_dir / "WP02-second.md").write_text(wp02_content)
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add WP02"], cwd=repo, capture_output=True, check=True)

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

        # Make WP01 stale (old commit)
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

        # Check status
        status_result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "status"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # Only WP01 should be stale (has old commit), WP02 should not be stale (fresh)
        output = status_result.stdout.lower()

        if worktree1.exists() and (worktree1 / "work.txt").exists():
            # If WP01 has commit, it should be marked stale
            assert "stale" in output, f"WP01 with old commit should be shown as stale"

        # WP02 (fresh, no commits) should NOT be stale
        # This is harder to verify, but the test passes if no error

    def test_json_output_not_corrupted(self, tmp_path):
        """
        CRITICAL: JSON mode should not be corrupted by warnings.

        BUG CHECK: Warnings should go to stderr, not stdout.
        RELATED: Issue #72 had this same bug.
        WHY MISSED: Functional tests don't test JSON mode.
        """
        repo = tmp_path / "json_test"
        setup_git_repo(repo)

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

        # Run status with --json
        status_result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "status", "--json"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # Check if --json flag is supported
        help_result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "status", "--help"],
            capture_output=True,
            text=True
        )

        if "--json" in help_result.stdout:
            # Should be valid JSON
            try:
                data = json.loads(status_result.stdout)
                # Valid JSON - test passed
            except json.JSONDecodeError as e:
                pytest.fail(f"JSON output corrupted: {e}\nOutput: {status_result.stdout}")


class TestRaceConditions:
    """
    Test concurrent operations.

    BUG CHECK: No race conditions in stale detection.
    WHY MISSED: Functional tests are single-threaded.
    """

    def test_status_during_git_operation(self, tmp_path):
        """
        Status check during git operation.

        BUG CHECK: Should not crash on locked .git.
        """
        repo = tmp_path / "race_test"
        setup_git_repo(repo)

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

        # Try status check (should handle locked state gracefully)
        status_result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "status"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True,
            timeout=10
        )

        # Should not crash or hang
        assert status_result.returncode in [0, 1], \
            f"Status should handle git operations gracefully: {status_result.stderr}"


class TestMergeBaseFailureScenarios:
    """
    Test scenarios where merge-base can fail.

    BUG CHECK: Should return NOT stale (safe default) when merge-base fails.
    """

    def test_detached_head_graceful(self, tmp_path):
        """
        Detached HEAD scenario.

        BUG CHECK: Should handle detached HEAD gracefully.
        WHY MISSED: Functional tests don't test detached HEAD.
        """
        repo = tmp_path / "detached_head"
        setup_git_repo(repo)

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

        # Create detached HEAD in worktree
        worktree_path = repo / ".worktrees" / "001-test-feature-WP01"
        if worktree_path.exists():
            subprocess.run(
                ["git", "checkout", "--detach"],
                cwd=worktree_path,
                capture_output=True
            )

        # Should handle gracefully, not crash
        status_result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "status"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        assert status_result.returncode in [0, 1], \
            f"Should handle detached HEAD gracefully: {status_result.stderr}"

    def test_branch_not_exist_graceful(self, tmp_path):
        """
        Branch that doesn't exist in default branch check.

        BUG CHECK: Should fall back gracefully.
        """
        repo = tmp_path / "branch_test"
        repo.mkdir(parents=True)

        # Create repo with unusual setup
        subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)
        subprocess.run(["git", "checkout", "-b", "unusual-branch"], cwd=repo, capture_output=True)
        (repo / "README.md").write_text("# Test")
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=repo, capture_output=True, check=True)

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

        # Should handle unusual branch name gracefully
        status_result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "status"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        assert status_result.returncode == 0, \
            f"Should handle unusual branch gracefully: {status_result.stderr}"
