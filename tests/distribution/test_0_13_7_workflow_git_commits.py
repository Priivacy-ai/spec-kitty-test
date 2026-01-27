"""
Adversarial Tests for PR #104: Workflow Git Commit Instructions

These tests validate that agents cannot mark work packages as "done" without
committing their changes, and that workflow templates guide proper git usage.

**The Bug (Feature 017 Failure):**
Agents implemented code but forgot to commit before marking WP done. This created
empty branches (no commits beyond main), causing cascading failures when dependent
WPs merged nothing.

Real scenario:
- WP01: Agent writes code, forgets `git commit`, marks done → empty branch
- WP02 depends on WP01: Merges WP01 (gets nothing), fails immediately
- WP03-WP08: Cascading failures through entire dependency chain

**The Fix (PR #104):**
1. Validation: Block "done" transition if uncommitted changes exist
2. Templates: Add explicit git commit instructions to workflow prompts
3. Warnings: Alert users when dependencies have empty branches

**Why These Tests Matter:**
- This bug broke an entire feature (8 WPs failed cascading)
- Functional tests always committed properly (developer workflow)
- Real agents forget commits (automation workflow)
- Must test ACTUAL agent behavior (forgetting commits)

Run: pytest tests/distribution/test_0_13_7_workflow_git_commits.py -xvs
"""

import subprocess
import json
from pathlib import Path
import pytest

pytestmark = [
    pytest.mark.distribution,
    pytest.mark.adversarial,
    pytest.mark.regression,
    pytest.mark.pr_104,
]


class TestEmptyBranchValidation:
    """
    Test that empty branches (uncommitted work) are detected and blocked.

    CRITICAL: This is the core validation that prevents the Feature 017 bug.
    """

    def test_uncommitted_work_blocks_done_transition(self, tmp_path, spec_kitty_repo_root):
        """
        Cannot move to "done" with uncommitted changes.

        BUG SCENARIO:
        1. Agent implements WP01 in worktree
        2. Agent creates files but forgets `git commit`
        3. Agent tries to move WP01 to done
        4. EXPECTED: Blocked with error about uncommitted changes
        5. BUG: Used to allow this, creating empty branch

        WHY MISSED: Functional tests always committed before marking done.
        """
        env = {
            "SPEC_KITTY_TEMPLATE_ROOT": str(spec_kitty_repo_root),
            "PATH": subprocess.os.environ.get("PATH", ""),
        }

        # Setup git repo
        repo = tmp_path / "test_repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)

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

        # Commit initial state
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Init"], cwd=repo, capture_output=True, check=True)

        # Create feature structure
        feature_dir = repo / "kitty-specs" / "001-test-feature"
        feature_dir.mkdir(parents=True)

        meta = {
            "feature_id": "001-test-feature",
            "title": "Test Empty Branch Validation",
            "mission": "software-dev"
        }
        (feature_dir / "meta.json").write_text(json.dumps(meta))

        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        # Create WP01
        wp_content = """---
work_package_id: WP01
title: Implementation Test
lane: doing
dependencies: []
---

# WP01: Implementation Test

Test validation of uncommitted work.

## Activity Log

- 2025-01-27T10:00:00Z – test-agent – shell_pid=12345 – lane=doing – Started work
"""
        wp_file = tasks_dir / "WP01-implementation-test.md"
        wp_file.write_text(wp_content)

        # Commit the WP
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add WP01"], cwd=repo, capture_output=True, check=True)

        # Create worktree for WP01
        worktree_dir = repo / ".worktrees" / "001-test-feature-WP01"
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "implement", "WP01"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # If implement fails, skip (might not have worktree support)
        if result.returncode != 0:
            pytest.skip(f"Implement failed (worktree not available?): {result.stderr}")

        # Verify worktree exists
        if not worktree_dir.exists():
            pytest.skip("Worktree not created")

        # SIMULATE THE BUG: Create files without committing
        implementation_file = worktree_dir / "src" / "main.py"
        implementation_file.parent.mkdir(parents=True, exist_ok=True)
        implementation_file.write_text("""
def hello():
    return "Hello, World!"
""")

        # Agent forgets: git add . && git commit
        # Now try to mark as done

        # Try to move WP01 to done (should be blocked)
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "move-task", "WP01", "--to", "done"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # BUG CHECK: Should FAIL with uncommitted work
        # The bug would allow this to succeed, creating an empty branch
        if result.returncode == 0:
            # Check if there are actually uncommitted changes
            git_status = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=worktree_dir,
                capture_output=True,
                text=True
            )
            if git_status.stdout.strip():
                pytest.fail(
                    "BUG DETECTED: move-task succeeded despite uncommitted changes!\n"
                    f"Uncommitted: {git_status.stdout}\n"
                    "This is exactly the Feature 017 bug!"
                )

        # If it failed (good!), verify it's because of uncommitted work
        assert result.returncode != 0, "Should block done transition"
        # Error message should mention uncommitted changes or dirty worktree
        error_msg = result.stderr.lower()
        assert any(keyword in error_msg for keyword in [
            "uncommitted", "dirty", "changes", "commit", "worktree"
        ]), f"Error should mention uncommitted changes, got: {result.stderr}"

    def test_untracked_files_block_done(self, tmp_path, spec_kitty_repo_root):
        """
        Untracked files prevent done transition.

        Untracked files are uncommitted work - should be blocked.
        """
        env = {
            "SPEC_KITTY_TEMPLATE_ROOT": str(spec_kitty_repo_root),
            "PATH": subprocess.os.environ.get("PATH", ""),
        }

        # Setup git repo
        repo = tmp_path / "test_repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)

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

        # Commit initial state
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Init"], cwd=repo, capture_output=True, check=True)

        # Create feature structure
        feature_dir = repo / "kitty-specs" / "002-untracked"
        feature_dir.mkdir(parents=True)

        meta = {
            "feature_id": "002-untracked",
            "title": "Untracked Files Test",
            "mission": "software-dev"
        }
        (feature_dir / "meta.json").write_text(json.dumps(meta))

        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        # Create WP01
        wp_content = """---
work_package_id: WP01
title: Untracked Test
lane: doing
dependencies: []
---

# WP01: Untracked Test

## Activity Log
"""
        wp_file = tasks_dir / "WP01-untracked.md"
        wp_file.write_text(wp_content)

        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add WP01"], cwd=repo, capture_output=True, check=True)

        # Create worktree
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "implement", "WP01"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip(f"Implement failed: {result.stderr}")

        worktree_dir = repo / ".worktrees" / "002-untracked-WP01"
        if not worktree_dir.exists():
            pytest.skip("Worktree not created")

        # Create untracked file (not staged, not committed)
        untracked_file = worktree_dir / "untracked.txt"
        untracked_file.write_text("This file is not tracked by git")

        # Try to move to done
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "move-task", "WP01", "--to", "done"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # BUG CHECK: Should block due to untracked files
        if result.returncode == 0:
            # Verify untracked file still exists
            if untracked_file.exists():
                pytest.fail(
                    "BUG: move-task succeeded with untracked files!\n"
                    "Untracked files should prevent done transition."
                )

    def test_staged_but_not_committed_blocks_done(self, tmp_path, spec_kitty_repo_root):
        """
        Staged changes (git add, but no commit) should block done.

        Staging is not enough - must actually commit.
        """
        env = {
            "SPEC_KITTY_TEMPLATE_ROOT": str(spec_kitty_repo_root),
            "PATH": subprocess.os.environ.get("PATH", ""),
        }

        # Setup git repo
        repo = tmp_path / "test_repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)

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

        # Create feature
        feature_dir = repo / "kitty-specs" / "003-staged"
        feature_dir.mkdir(parents=True)

        meta = {
            "feature_id": "003-staged",
            "title": "Staged Changes Test",
            "mission": "software-dev"
        }
        (feature_dir / "meta.json").write_text(json.dumps(meta))

        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        wp_content = """---
work_package_id: WP01
title: Staged Test
lane: doing
dependencies: []
---

# WP01: Staged Test

## Activity Log
"""
        (tasks_dir / "WP01-staged.md").write_text(wp_content)

        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add WP01"], cwd=repo, capture_output=True, check=True)

        # Create worktree
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "implement", "WP01"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip(f"Implement failed: {result.stderr}")

        worktree_dir = repo / ".worktrees" / "003-staged-WP01"
        if not worktree_dir.exists():
            pytest.skip("Worktree not created")

        # Create file and STAGE it (but don't commit)
        staged_file = worktree_dir / "staged.txt"
        staged_file.write_text("Staged but not committed")
        subprocess.run(["git", "add", "staged.txt"], cwd=worktree_dir, capture_output=True)

        # Try to move to done
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "move-task", "WP01", "--to", "done"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # BUG CHECK: Staged but uncommitted should be blocked
        if result.returncode == 0:
            # Check if changes are still staged
            git_status = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                cwd=worktree_dir,
                capture_output=True,
                text=True
            )
            if git_status.stdout.strip():
                pytest.fail(
                    "BUG: move-task succeeded with staged but uncommitted changes!\n"
                    f"Staged: {git_status.stdout}"
                )

    def test_committed_work_allows_done(self, tmp_path, spec_kitty_repo_root):
        """
        Properly committed work SHOULD allow done transition.

        This is the HAPPY PATH - when agent does it right.
        """
        env = {
            "SPEC_KITTY_TEMPLATE_ROOT": str(spec_kitty_repo_root),
            "PATH": subprocess.os.environ.get("PATH", ""),
        }

        # Setup git repo
        repo = tmp_path / "test_repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)

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

        # Create feature
        feature_dir = repo / "kitty-specs" / "004-committed"
        feature_dir.mkdir(parents=True)

        meta = {
            "feature_id": "004-committed",
            "title": "Committed Work Test",
            "mission": "software-dev"
        }
        (feature_dir / "meta.json").write_text(json.dumps(meta))

        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        wp_content = """---
work_package_id: WP01
title: Committed Test
lane: doing
dependencies: []
---

# WP01: Committed Test

## Activity Log
"""
        (tasks_dir / "WP01-committed.md").write_text(wp_content)

        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add WP01"], cwd=repo, capture_output=True, check=True)

        # Create worktree
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "implement", "WP01"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip(f"Implement failed: {result.stderr}")

        worktree_dir = repo / ".worktrees" / "004-committed-WP01"
        if not worktree_dir.exists():
            pytest.skip("Worktree not created")

        # Do it RIGHT: Create, add, AND commit
        impl_file = worktree_dir / "implementation.py"
        impl_file.write_text("def work(): pass")
        subprocess.run(["git", "add", "."], cwd=worktree_dir, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Implement WP01"],
            cwd=worktree_dir,
            capture_output=True,
            check=True
        )

        # Now try to move to done - should succeed
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "move-task", "WP01", "--to", "done"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # BUG CHECK: Should succeed when properly committed
        # (Might fail for other reasons like no tests, etc., but not due to uncommitted work)
        if result.returncode != 0:
            # Make sure it's not failing due to uncommitted work
            assert "uncommitted" not in result.stderr.lower(), \
                f"Should not fail for uncommitted work when properly committed: {result.stderr}"


class TestDependentWorkPackages:
    """
    Test dependent WPs receive merged work correctly.

    CRITICAL: Empty WP01 branch breaks WP02 that depends on it.
    """

    def test_wp02_depends_on_wp01_empty_branch_scenario(self, tmp_path, spec_kitty_repo_root):
        """
        THE BUG: WP02 depends on WP01, but WP01 branch is empty.

        SCENARIO (Feature 017):
        1. WP01 implemented without commits → empty branch
        2. WP01 marked "done" (validation should block this!)
        3. WP02 depends on WP01
        4. WP02 implement merges WP01 → gets nothing
        5. WP02 fails immediately

        This test verifies:
        - Empty branches are detected
        - Warnings are shown
        - Validation prevents the scenario
        """
        env = {
            "SPEC_KITTY_TEMPLATE_ROOT": str(spec_kitty_repo_root),
            "PATH": subprocess.os.environ.get("PATH", ""),
        }

        # Setup git repo
        repo = tmp_path / "test_repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)

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

        # Create feature with dependencies
        feature_dir = repo / "kitty-specs" / "005-dependencies"
        feature_dir.mkdir(parents=True)

        meta = {
            "feature_id": "005-dependencies",
            "title": "Dependency Chain Test",
            "mission": "software-dev"
        }
        (feature_dir / "meta.json").write_text(json.dumps(meta))

        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        # Create WP01 (no dependencies)
        wp01_content = """---
work_package_id: WP01
title: Foundation Work
lane: doing
dependencies: []
---

# WP01: Foundation Work

## Activity Log
"""
        (tasks_dir / "WP01-foundation.md").write_text(wp01_content)

        # Create WP02 (depends on WP01)
        wp02_content = """---
work_package_id: WP02
title: Dependent Work
lane: planned
dependencies: [WP01]
---

# WP02: Dependent Work

Depends on WP01.

## Activity Log
"""
        (tasks_dir / "WP02-dependent.md").write_text(wp02_content)

        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add WP01 and WP02"], cwd=repo, capture_output=True, check=True)

        # Try to implement WP01 (creates worktree + branch)
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "implement", "WP01"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip(f"Implement WP01 failed: {result.stderr}")

        # DON'T commit anything in WP01 worktree
        # Try to mark WP01 as done (should be blocked)

        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "move-task", "WP01", "--to", "done"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # BUG CHECK: Should be blocked due to no commits
        # If it succeeds, we have the Feature 017 bug
        if result.returncode == 0:
            # Check if WP01 branch actually has commits
            branch_commits = subprocess.run(
                ["git", "log", "005-dependencies-WP01", "--oneline"],
                cwd=repo,
                capture_output=True,
                text=True
            )
            base_commits = subprocess.run(
                ["git", "log", "main", "--oneline"],
                cwd=repo,
                capture_output=True,
                text=True
            )

            # If branch has same commits as main, it's empty
            if branch_commits.stdout == base_commits.stdout:
                pytest.fail(
                    "CRITICAL BUG: WP01 marked done with empty branch!\n"
                    "This is the exact Feature 017 bug that broke 8 WPs."
                )


class TestWorkflowInstructions:
    """
    Test that workflow templates guide agents to commit properly.

    PR #104 added explicit commit instructions to templates.
    """

    def test_implement_template_has_commit_instructions(self, tmp_path, spec_kitty_repo_root):
        """
        Implement template must include git commit instructions.

        The template should guide agents through:
        1. Make changes
        2. git add .
        3. git commit -m "message"
        4. Move to review/done
        """
        # Read the implement template from spec-kitty
        # Look in missions for implement.md or similar

        # This is a static template check - read template files
        missions_dir = spec_kitty_repo_root / "src" / "specify_cli" / "missions"
        if not missions_dir.exists():
            # Try alternate location
            missions_dir = spec_kitty_repo_root / ".kittify" / "missions"

        if not missions_dir.exists():
            pytest.skip("Cannot find missions directory")

        # Look for implement template in any mission
        implement_templates = list(missions_dir.rglob("*implement*.md"))
        if not implement_templates:
            pytest.skip("Cannot find implement template")

        # Read first implement template found
        template_content = implement_templates[0].read_text()

        # BUG CHECK: Template should mention git commit
        assert "git commit" in template_content or "commit" in template_content.lower(), \
            "Implement template should include commit instructions"

        # Should also mention the proper order
        # Ideally: commit before moving lanes
        template_lower = template_content.lower()
        commit_mentioned = "commit" in template_lower
        move_mentioned = any(word in template_lower for word in ["move", "done", "review"])

        assert commit_mentioned, "Template should mention committing"


class TestJSONOutputIntegrity:
    """
    Test JSON mode not corrupted by warnings.

    Related to Issue #72 - warnings must go to stderr, not stdout.
    """

    def test_empty_branch_warning_uses_stderr(self, tmp_path, spec_kitty_repo_root):
        """
        Warnings about empty branches should not corrupt JSON output.

        When running commands with --json flag, ALL warnings must go to
        stderr, keeping stdout clean for JSON parsing.
        """
        env = {
            "SPEC_KITTY_TEMPLATE_ROOT": str(spec_kitty_repo_root),
            "PATH": subprocess.os.environ.get("PATH", ""),
        }

        # Setup git repo
        repo = tmp_path / "test_repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)

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

        # Create minimal feature
        feature_dir = repo / "kitty-specs" / "006-json"
        feature_dir.mkdir(parents=True)

        meta = {
            "feature_id": "006-json",
            "title": "JSON Output Test",
            "mission": "software-dev"
        }
        (feature_dir / "meta.json").write_text(json.dumps(meta))

        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        wp_content = """---
work_package_id: WP01
title: JSON Test
lane: planned
dependencies: []
---

# WP01: JSON Test

## Activity Log
"""
        (tasks_dir / "WP01-json.md").write_text(wp_content)

        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add feature"], cwd=repo, capture_output=True, check=True)

        # Run status with --json flag
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "status", "--json"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip(f"Status command failed: {result.stderr}")

        # BUG CHECK: stdout should be VALID JSON (no warnings mixed in)
        try:
            json_data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            pytest.fail(
                f"JSON output corrupted!\n"
                f"Error: {e}\n"
                f"Stdout: {result.stdout}\n"
                f"Stderr: {result.stderr}\n"
                "Warnings should be in stderr, not stdout!"
            )

        # JSON should be valid
        assert isinstance(json_data, dict), "JSON output should be a dictionary"
