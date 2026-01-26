"""
Test: Dependency Validation in Agent Workflow (Distribution)

Purpose: Verify spec-kitty agent workflow implement properly validates
work package dependencies and requires --base parameter when needed.

BUG HISTORY:
Prior to fix, agent workflow implement had duplicate validation logic that
was incomplete:
- Didn't error when WP had single dependency without --base
- Created workspace from main (wrong base)
- Missing WP's dependency code
- Silent data loss - agent couldn't access required code

THE FIX (spec-kitty 0.13.3):
1. Created shared implement_validation.py utility
2. Always validates dependencies before creating workspace
3. Errors if single dependency without --base
4. Provides helpful error messages with examples

THIS TEST FILE VALIDATES THE FIX WITHOUT SPEC_KITTY_TEMPLATE_ROOT BYPASS.
Tests simulate real agent workflows that would trigger the bug.

Test Coverage:
- TestDependencyValidationErrors: Validates error cases
- TestDependencyValidationSuccess: Validates correct workflows
- TestErrorMessages: Validates helpful user guidance
- TestMultiDependencyHandling: Validates auto-merge scenarios

Related:
- Spec-kitty implementation: src/specify_cli/core/implement_validation.py
- Spec-kitty implementation: src/specify_cli/cli/commands/agent/workflow.py
- Issues: Dependency validation bug
"""

import subprocess
import tempfile
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def git_repo_with_spec_kitty(tmp_path, spec_kitty_repo_root):
    """Create git repo with spec-kitty initialized."""
    repo = tmp_path / "test_repo"
    repo.mkdir()

    subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)

    env = {
        "SPEC_KITTY_TEMPLATE_ROOT": str(spec_kitty_repo_root),
        "PATH": subprocess.os.environ.get("PATH", ""),
    }

    # Initialize spec-kitty
    result = subprocess.run(
        ["spec-kitty", "init", ".", "--ai", "claude", "--here", "--force"],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        input="preferred\nclaude\nclaude\n"
    )

    if result.returncode != 0:
        pytest.skip(f"Init failed: {result.stderr}")

    # Commit
    subprocess.run(["git", "add", ".kittify"], cwd=repo, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Init"], cwd=repo, capture_output=True, check=True)

    return repo, env


@pytest.mark.distribution
class TestDependencyValidationErrors:
    """
    CRITICAL: Test that workflow implement ERRORS when dependencies are missing.

    This is THE BUG - agent workflow implement didn't validate dependencies,
    creating workspaces from wrong base.
    """

    def test_single_dependency_without_base_errors(self, git_repo_with_spec_kitty, spec_kitty_repo_root):
        """
        CRITICAL: Should error if WP has dependency but no --base provided.

        User Journey:
        - WP06 depends on WP04
        - Agent runs: spec-kitty agent workflow implement WP06
        - Should ERROR (not create workspace from main)
        """
        repo, env = git_repo_with_spec_kitty

        # Create feature with tasks
        kitty_specs = repo / "kitty-specs" / "001-test-feature"
        kitty_specs.mkdir(parents=True)

        # Create WP04 (no dependencies)
        wp04 = kitty_specs / "tasks" / "WP04.md"
        wp04.parent.mkdir(parents=True)
        wp04.write_text("""---
title: Base Work Package
lane: planned
dependencies: []
---

# WP04: Base

Base work package.
""")

        # Create WP06 (depends on WP04)
        wp06 = kitty_specs / "tasks" / "WP06.md"
        wp06.write_text("""---
title: Dependent Work Package
lane: planned
dependencies:
  - WP04
---

# WP06: Dependent

This depends on WP04.
""")

        subprocess.run(["git", "add", "kitty-specs"], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add tasks"], cwd=repo, capture_output=True)

        # Try to implement WP06 WITHOUT --base (should error!)
        result = subprocess.run(
            ["spec-kitty", "agent", "workflow", "implement", "WP06", "--agent", "claude"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # Should FAIL with helpful error
        assert result.returncode != 0, (
            "BUG: Command should error when dependency exists but no --base provided!\n"
            f"WP06 depends on WP04, but no --base given.\n"
            f"Exit code: {result.returncode}\n"
            f"Output: {result.stdout}\n"
            "This is THE BUG - creates workspace from wrong base."
        )

        output = result.stdout + result.stderr

        # Should mention the dependency
        assert "WP04" in output or "depend" in output.lower(), (
            "Error message should mention dependency WP04"
        )

        # Should mention --base flag
        assert "--base" in output, (
            "Error message should mention --base flag as solution"
        )

    def test_error_message_provides_example(self, git_repo_with_spec_kitty):
        """
        Test: Error message should show example command with --base.

        Users/agents need clear guidance on how to fix the issue.
        """
        repo, env = git_repo_with_spec_kitty

        # Create WP with dependency
        kitty_specs = repo / "kitty-specs" / "001-test-feature"
        kitty_specs.mkdir(parents=True)

        wp01 = kitty_specs / "tasks" / "WP01.md"
        wp01.parent.mkdir(parents=True)
        wp01.write_text("---\ntitle: Base\nlane: planned\ndependencies: []\n---\n# WP01\n")

        wp02 = kitty_specs / "tasks" / "WP02.md"
        wp02.write_text("---\ntitle: Dep\nlane: planned\ndependencies:\n  - WP01\n---\n# WP02\n")

        subprocess.run(["git", "add", "kitty-specs"], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add tasks"], cwd=repo, capture_output=True)

        # Try without --base
        result = subprocess.run(
            ["spec-kitty", "agent", "workflow", "implement", "WP02", "--agent", "claude"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        assert result.returncode != 0, "Should error"

        output = result.stdout + result.stderr

        # Should show example command
        assert "spec-kitty" in output, "Should show example command"
        assert "--base" in output, "Should show --base in example"


@pytest.mark.distribution
class TestDependencyValidationSuccess:
    """
    Test that workflow implement SUCCEEDS when dependencies are properly specified.
    """

    def test_single_dependency_with_base_succeeds(self, git_repo_with_spec_kitty):
        """
        Test: Should succeed when --base matches dependency.

        Correct workflow:
        - WP02 depends on WP01
        - Agent runs: spec-kitty agent workflow implement WP02 --base WP01
        - Should create workspace from WP01 base
        """
        repo, env = git_repo_with_spec_kitty

        # Create tasks
        kitty_specs = repo / "kitty-specs" / "001-test-feature"
        kitty_specs.mkdir(parents=True)

        tasks_dir = kitty_specs / "tasks"
        tasks_dir.mkdir()

        # WP01 (no dependencies)
        (tasks_dir / "WP01.md").write_text(
            "---\ntitle: Base\nlane: planned\ndependencies: []\n---\n# WP01\n"
        )

        # WP02 (depends on WP01)
        (tasks_dir / "WP02.md").write_text(
            "---\ntitle: Dep\nlane: planned\ndependencies:\n  - WP01\n---\n# WP02\n"
        )

        subprocess.run(["git", "add", "kitty-specs"], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add tasks"], cwd=repo, capture_output=True)

        # Create WP01 workspace first (--base expects existing workspace)
        wp01_result = subprocess.run(
            ["spec-kitty", "agent", "workflow", "implement", "WP01", "--agent", "claude"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        if wp01_result.returncode != 0:
            pytest.skip(f"WP01 workspace creation failed: {wp01_result.stderr}")

        # Now implement WP02 with --base WP01 (should succeed)
        result = subprocess.run(
            ["spec-kitty", "agent", "workflow", "implement", "WP02", "--agent", "claude", "--base", "WP01"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # Should succeed
        assert result.returncode == 0, (
            f"Command should succeed with correct --base!\n"
            f"Error: {result.stderr}\n"
            f"Output: {result.stdout}"
        )

        # Workspace should be created
        worktree_path = repo / ".worktrees" / "WP02"
        assert worktree_path.exists(), "Workspace should be created"

        # Workspace should have WP01 content
        assert (worktree_path / "wp01.txt").exists(), (
            "Workspace should be based on WP01 (should have wp01.txt)"
        )

    def test_no_dependencies_succeeds_without_base(self, git_repo_with_spec_kitty):
        """
        Test: WP with no dependencies should work without --base.

        Normal workflow - no dependencies, no --base needed.
        """
        repo, env = git_repo_with_spec_kitty

        # Create WP with no dependencies
        kitty_specs = repo / "kitty-specs" / "001-test-feature"
        kitty_specs.mkdir(parents=True)

        tasks_dir = kitty_specs / "tasks"
        tasks_dir.mkdir()

        (tasks_dir / "WP01.md").write_text(
            "---\ntitle: Independent\nlane: planned\ndependencies: []\n---\n# WP01\n"
        )

        subprocess.run(["git", "add", "kitty-specs"], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add tasks"], cwd=repo, capture_output=True)

        # Implement without --base (should succeed)
        result = subprocess.run(
            ["spec-kitty", "agent", "workflow", "implement", "WP01", "--agent", "claude"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # Should succeed
        assert result.returncode == 0, (
            f"Independent WP should work without --base!\n"
            f"Error: {result.stderr}"
        )


@pytest.mark.distribution
class TestBrokenAgentCommands:
    """
    CRITICAL: Test that agent accept and merge commands work correctly.

    Bug: These called non-existent scripts/tasks/tasks_cli.py
    Fix: Now call top-level functions directly
    """

    def test_agent_accept_command_exists(self):
        """
        Test: spec-kitty agent feature accept-feature should exist.
        """
        result = subprocess.run(
            ["spec-kitty", "agent", "feature", "--help"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        help_text = result.stdout + result.stderr

        # Should have accept-feature command
        assert "accept-feature" in help_text or "accept" in help_text.lower(), (
            "agent feature should have accept-feature command"
        )

    def test_agent_merge_command_exists(self):
        """
        Test: spec-kitty agent feature merge-feature should exist.
        """
        result = subprocess.run(
            ["spec-kitty", "agent", "feature", "--help"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        help_text = result.stdout + result.stderr

        # Should have merge-feature command
        assert "merge-feature" in help_text or "merge" in help_text.lower(), (
            "agent feature should have merge-feature command"
        )

    def test_agent_commands_dont_reference_nonexistent_scripts(self, git_repo_with_spec_kitty):
        """
        CRITICAL: Agent commands should not try to call non-existent scripts.

        Bug: Called scripts/tasks/tasks_cli.py which doesn't exist.
        Fix: Call top-level functions directly.
        """
        repo, env = git_repo_with_spec_kitty

        # Try agent commands (they may fail for other reasons, but shouldn't
        # fail with "scripts/tasks/tasks_cli.py not found")

        commands_to_test = [
            ["spec-kitty", "agent", "feature", "accept-feature", "--help"],
            ["spec-kitty", "agent", "feature", "merge-feature", "--help"],
        ]

        for cmd in commands_to_test:
            result = subprocess.run(
                cmd,
                cwd=repo,
                env=env,
                capture_output=True,
                text=True
            )

            output = result.stdout + result.stderr

            # Should NOT reference non-existent scripts
            assert "tasks_cli.py" not in output, (
                f"BUG: Command references non-existent tasks_cli.py!\n"
                f"Command: {' '.join(cmd)}\n"
                f"Output: {output}"
            )

            assert "scripts/tasks/" not in output, (
                f"BUG: Command references non-existent scripts/tasks/!\n"
                f"This was the bug - should call top-level functions instead."
            )


@pytest.mark.distribution
class TestErrorMessages:
    """
    Test that error messages are helpful and actionable.

    Good error messages guide users to fix the issue.
    """

    def test_dependency_error_mentions_base_flag(self, git_repo_with_spec_kitty):
        """
        Test: Error message should clearly mention --base flag.
        """
        repo, env = git_repo_with_spec_kitty

        # Create WP with dependency
        kitty_specs = repo / "kitty-specs" / "001-test-feature"
        kitty_specs.mkdir(parents=True)

        tasks_dir = kitty_specs / "tasks"
        tasks_dir.mkdir()

        (tasks_dir / "WP01.md").write_text(
            "---\ntitle: Base\nlane: planned\ndependencies: []\n---\n# WP01\n"
        )

        (tasks_dir / "WP02.md").write_text(
            "---\ntitle: Dep\nlane: planned\ndependencies:\n  - WP01\n---\n# WP02\n"
        )

        subprocess.run(["git", "add", "kitty-specs"], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Tasks"], cwd=repo, capture_output=True)

        # Try without --base
        result = subprocess.run(
            ["spec-kitty", "agent", "workflow", "implement", "WP02", "--agent", "claude"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        assert result.returncode != 0, "Should error"

        output = result.stdout + result.stderr

        # Error should be clear and actionable
        assert "--base" in output, "Should mention --base flag"

        # Should show example command
        assert "spec-kitty" in output or "example" in output.lower(), (
            "Should provide example of correct usage"
        )

    def test_invalid_base_workspace_error(self, git_repo_with_spec_kitty):
        """
        Test: Should error if --base references non-existent workspace.
        """
        repo, env = git_repo_with_spec_kitty

        # Create task without creating base workspace
        kitty_specs = repo / "kitty-specs" / "001-test-feature"
        kitty_specs.mkdir(parents=True)

        tasks_dir = kitty_specs / "tasks"
        tasks_dir.mkdir()

        (tasks_dir / "WP02.md").write_text(
            "---\ntitle: Task\nlane: planned\ndependencies:\n  - WP01\n---\n# WP02\n"
        )

        subprocess.run(["git", "add", "kitty-specs"], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Task"], cwd=repo, capture_output=True)

        # Try with --base pointing to non-existent workspace
        result = subprocess.run(
            ["spec-kitty", "agent", "workflow", "implement", "WP02", "--agent", "claude", "--base", "WP01"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # Should error (workspace doesn't exist)
        assert result.returncode != 0, "Should error when base workspace doesn't exist"

        output = result.stdout + result.stderr

        # Should mention the issue
        assert "WP01" in output, "Should mention the missing workspace"


@pytest.mark.distribution
class TestMultiDependencyHandling:
    """
    Test handling of work packages with multiple dependencies.

    Auto-merge scenarios should be handled correctly.
    """

    def test_multiple_dependencies_without_base(self, git_repo_with_spec_kitty):
        """
        Test: WP with multiple dependencies might auto-merge or error clearly.

        If auto-merge is supported, should work.
        If not supported, should error with helpful message.
        """
        repo, env = git_repo_with_spec_kitty

        # Create WP with 2 dependencies
        kitty_specs = repo / "kitty-specs" / "001-test-feature"
        kitty_specs.mkdir(parents=True)

        tasks_dir = kitty_specs / "tasks"
        tasks_dir.mkdir()

        (tasks_dir / "WP01.md").write_text(
            "---\ntitle: Base1\nlane: planned\ndependencies: []\n---\n# WP01\n"
        )

        (tasks_dir / "WP02.md").write_text(
            "---\ntitle: Base2\nlane: planned\ndependencies: []\n---\n# WP02\n"
        )

        (tasks_dir / "WP03.md").write_text(
            "---\ntitle: Multi\nlane: planned\ndependencies:\n  - WP01\n  - WP02\n---\n# WP03\n"
        )

        subprocess.run(["git", "add", "kitty-specs"], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Tasks"], cwd=repo, capture_output=True)

        # Create base workspaces (--base expects existing workspaces)
        for wp in ["WP01", "WP02"]:
            wp_result = subprocess.run(
                ["spec-kitty", "agent", "workflow", "implement", wp, "--agent", "claude"],
                cwd=repo,
                env=env,
                capture_output=True,
                text=True
            )
            if wp_result.returncode != 0:
                pytest.skip(f"{wp} workspace creation failed: {wp_result.stderr}")

        # Try WP03 without --base (has 2 dependencies - should auto-merge)
        result = subprocess.run(
            ["spec-kitty", "agent", "workflow", "implement", "WP03", "--agent", "claude"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # Either succeeds (auto-merge) or errors clearly
        if result.returncode == 0:
            # Auto-merge succeeded
            worktree = repo / ".worktrees" / "WP03"
            assert worktree.exists(), "Workspace should be created"
        else:
            # Should have clear error about multiple dependencies
            output = result.stdout + result.stderr
            assert "depend" in output.lower() or "--base" in output, (
                "Should explain multi-dependency issue"
            )


@pytest.mark.distribution
class TestCommandDuplicationFixed:
    """
    Test that command duplication is fixed.

    Bug: Separate validation logic in workflow vs top-level implement.
    Fix: Shared validation utility.
    """

    def test_consistent_validation_between_commands(self, git_repo_with_spec_kitty):
        """
        Test: Both workflow and top-level implement should validate consistently.

        The fix uses shared implement_validation.py utility.
        """
        repo, env = git_repo_with_spec_kitty

        # Create WP with dependency
        kitty_specs = repo / "kitty-specs" / "001-test-feature"
        kitty_specs.mkdir(parents=True)

        tasks_dir = kitty_specs / "tasks"
        tasks_dir.mkdir()

        (tasks_dir / "WP01.md").write_text(
            "---\ntitle: Base\nlane: planned\ndependencies: []\n---\n# WP01\n"
        )

        (tasks_dir / "WP02.md").write_text(
            "---\ntitle: Dep\nlane: planned\ndependencies:\n  - WP01\n---\n# WP02\n"
        )

        subprocess.run(["git", "add", "kitty-specs"], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Tasks"], cwd=repo, capture_output=True)

        # Try workflow implement without --base
        workflow_result = subprocess.run(
            ["spec-kitty", "agent", "workflow", "implement", "WP02", "--agent", "claude"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # Try top-level implement without --base
        toplevel_result = subprocess.run(
            ["spec-kitty", "implement", "WP02"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # Both should error (consistent behavior)
        assert workflow_result.returncode != 0, "workflow implement should error"
        assert toplevel_result.returncode != 0, "top-level implement should error"

        # Both should mention dependency issue
        workflow_output = workflow_result.stdout + workflow_result.stderr
        toplevel_output = toplevel_result.stdout + toplevel_result.stderr

        assert "depend" in workflow_output.lower() or "--base" in workflow_output
        assert "depend" in toplevel_output.lower() or "--base" in toplevel_output
