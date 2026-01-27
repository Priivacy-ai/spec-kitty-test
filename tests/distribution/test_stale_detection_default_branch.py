"""
Distribution Test: Stale Detection - Default Branch Detection

Tests get_default_branch() in various git configurations that functional tests miss.

THE ORIGINAL BUG: Hardcoded "main" in merge-base command caused fresh worktrees
on repos with master/develop to be incorrectly flagged as stale.

These tests validate the fix works for all default branch configurations.
"""

import subprocess
import json
from pathlib import Path
import pytest

pytestmark = [pytest.mark.distribution, pytest.mark.adversarial]


def setup_git_repo(repo_path: Path, branch_name: str = "main", with_remote: bool = True):
    """
    Setup a git repository with specified default branch.

    Args:
        repo_path: Path to create repo
        branch_name: Default branch name (main, master, develop)
        with_remote: Whether to setup remote and origin/HEAD
    """
    repo_path.mkdir(parents=True, exist_ok=True)

    subprocess.run(["git", "init"], cwd=repo_path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo_path, capture_output=True)

    # Create initial commit on specified branch
    subprocess.run(["git", "checkout", "-b", branch_name], cwd=repo_path, capture_output=True)
    (repo_path / "README.md").write_text(f"# Test Repo ({branch_name})")
    subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_path, capture_output=True, check=True)

    if with_remote:
        # Setup remote and origin/HEAD
        remote_path = repo_path.parent / f"{repo_path.name}.git"
        subprocess.run(["git", "init", "--bare", str(remote_path)], capture_output=True, check=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote_path)], cwd=repo_path, capture_output=True)
        subprocess.run(["git", "push", "-u", "origin", branch_name], cwd=repo_path, capture_output=True, check=True)


class TestDefaultBranchDetection:
    """
    Test get_default_branch() in various configurations.

    WHY MISSED: Functional tests only test repos with 'main' as default.
    """

    def test_detects_main_as_default(self, tmp_path):
        """
        Standard: origin/HEAD -> origin/main

        BUG CHECK: Should handle standard case.
        """
        repo = tmp_path / "main_repo"
        setup_git_repo(repo, branch_name="main", with_remote=True)

        # Initialize spec-kitty
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

        # Commit to avoid uncommitted changes
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Init"], cwd=repo, capture_output=True, check=True)

        # Test: Create fresh worktree
        feature_dir = repo / "kitty-specs" / "001-test-feature"
        feature_dir.mkdir(parents=True, exist_ok=True)

        meta = {"feature_id": "001-test-feature", "title": "Test", "mission": "software-dev"}
        (feature_dir / "meta.json").write_text(json.dumps(meta))

        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(exist_ok=True)

        wp_content = """---
work_package_id: WP01
title: Test Package
lane: doing
dependencies: []
---

# WP01: Test Package
"""
        (tasks_dir / "WP01-test.md").write_text(wp_content)

        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add feature"], cwd=repo, capture_output=True, check=True)

        # Implement WP01 (creates fresh worktree)
        result = subprocess.run(
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

        # Should NOT show "stale" for WP01
        assert "stale" not in status_result.stdout.lower() or "WP01" not in status_result.stdout, \
            f"Fresh worktree on 'main' should not be stale: {status_result.stdout}"

    def test_detects_master_as_default(self, tmp_path):
        """
        THE ORIGINAL BUG: Legacy repos with origin/HEAD -> origin/master

        BUG CHECK: Should support legacy repos without hardcoding "main".
        WHY MISSED: Functional tests don't test master repos.
        """
        repo = tmp_path / "master_repo"
        setup_git_repo(repo, branch_name="master", with_remote=True)

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

        # Create feature
        feature_dir = repo / "kitty-specs" / "001-test-feature"
        feature_dir.mkdir(parents=True, exist_ok=True)

        meta = {"feature_id": "001-test-feature", "title": "Test", "mission": "software-dev"}
        (feature_dir / "meta.json").write_text(json.dumps(meta))

        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(exist_ok=True)

        wp_content = """---
work_package_id: WP01
title: Test Package
lane: doing
dependencies: []
---

# WP01: Test Package
"""
        (tasks_dir / "WP01-test.md").write_text(wp_content)

        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add feature"], cwd=repo, capture_output=True, check=True)

        # Implement WP01 (creates fresh worktree)
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "implement", "WP01"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # THE BUG TEST: Check status immediately
        status_result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "status"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # CRITICAL: Fresh worktree should NOT be stale
        # Before fix: Would show "idle for ~11.5 hours" because merge-base with hardcoded "main" failed
        assert "stale" not in status_result.stdout.lower() or "WP01" not in status_result.stdout, \
            f"REGRESSION: Fresh worktree on 'master' flagged as stale (THE ORIGINAL BUG): {status_result.stdout}"

    def test_detects_develop_as_default(self, tmp_path):
        """
        THE ORIGINAL BUG: Custom repos with origin/HEAD -> origin/develop

        BUG CHECK: Should support custom default branches.
        WHY MISSED: Functional tests don't test develop repos.
        """
        repo = tmp_path / "develop_repo"
        setup_git_repo(repo, branch_name="develop", with_remote=True)

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

        # Create feature
        feature_dir = repo / "kitty-specs" / "001-test-feature"
        feature_dir.mkdir(parents=True, exist_ok=True)

        meta = {"feature_id": "001-test-feature", "title": "Test", "mission": "software-dev"}
        (feature_dir / "meta.json").write_text(json.dumps(meta))

        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(exist_ok=True)

        wp_content = """---
work_package_id: WP01
title: Test Package
lane: doing
dependencies: []
---

# WP01: Test Package
"""
        (tasks_dir / "WP01-test.md").write_text(wp_content)

        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add feature"], cwd=repo, capture_output=True, check=True)

        # Implement WP01
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "implement", "WP01"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # Check status
        status_result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "status"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        assert "stale" not in status_result.stdout.lower() or "WP01" not in status_result.stdout, \
            f"REGRESSION: Fresh worktree on 'develop' flagged as stale: {status_result.stdout}"

    def test_no_remote_origin(self, tmp_path):
        """
        CRITICAL: Repository with NO remote origin

        BUG CHECK: Should not crash when origin doesn't exist.
        WHY MISSED: Functional tests always create remotes.
        """
        repo = tmp_path / "no_remote_repo"
        setup_git_repo(repo, branch_name="main", with_remote=False)

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

        # Create feature
        feature_dir = repo / "kitty-specs" / "001-test-feature"
        feature_dir.mkdir(parents=True, exist_ok=True)

        meta = {"feature_id": "001-test-feature", "title": "Test", "mission": "software-dev"}
        (feature_dir / "meta.json").write_text(json.dumps(meta))

        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(exist_ok=True)

        wp_content = """---
work_package_id: WP01
title: Test Package
lane: doing
dependencies: []
---

# WP01: Test Package
"""
        (tasks_dir / "WP01-test.md").write_text(wp_content)

        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add feature"], cwd=repo, capture_output=True, check=True)

        # Implement WP01
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "implement", "WP01"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # Should not crash
        status_result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "status"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        assert status_result.returncode == 0, f"Status command crashed without remote: {status_result.stderr}"
        assert "stale" not in status_result.stdout.lower() or "WP01" not in status_result.stdout, \
            f"Fresh worktree without remote should not be stale: {status_result.stdout}"

    def test_remote_exists_but_no_head_set(self, tmp_path):
        """
        CRITICAL: Remote exists but origin/HEAD not set

        BUG CHECK: This is the EXACT user scenario from bug report.
        WHY MISSED: Functional tests always configure origin/HEAD.
        """
        repo = tmp_path / "no_origin_head_repo"
        repo.mkdir(parents=True)

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
        # Note: NOT running "git remote set-head origin main"

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

        # Create feature
        feature_dir = repo / "kitty-specs" / "001-test-feature"
        feature_dir.mkdir(parents=True, exist_ok=True)

        meta = {"feature_id": "001-test-feature", "title": "Test", "mission": "software-dev"}
        (feature_dir / "meta.json").write_text(json.dumps(meta))

        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(exist_ok=True)

        wp_content = """---
work_package_id: WP01
title: Test Package
lane: doing
dependencies: []
---

# WP01: Test Package
"""
        (tasks_dir / "WP01-test.md").write_text(wp_content)

        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add feature"], cwd=repo, capture_output=True, check=True)

        # Implement WP01
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "implement", "WP01"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # THE CRITICAL TEST: User's exact scenario
        status_result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "status"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        assert status_result.returncode == 0, f"Status crashed without origin/HEAD: {status_result.stderr}"
        assert "stale" not in status_result.stdout.lower() or "WP01" not in status_result.stdout, \
            f"USER'S BUG SCENARIO: Fresh worktree with no origin/HEAD should not be stale: {status_result.stdout}"
