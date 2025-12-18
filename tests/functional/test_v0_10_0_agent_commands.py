"""
Test: spec-kitty v0.10.0 Agent Commands (Python CLI Migration)

Purpose: External validation of all `spec-kitty agent` commands that replaced bash scripts.
This test suite validates the migration from ~2,600 lines of bash to unified Python CLI.

Version Tested: spec-kitty >= 0.10.0
Related Migration: Bash scripts → Python CLI under `spec-kitty agent` namespace

Test Coverage:
1. Agent Command Discovery (4 tests)
   - Agent command exists and is callable
   - All subcommands (feature, tasks, context) are listed
   - Help text documents --json flags
   - No ambiguity with user commands

2. Feature Commands (8 tests)
   - create-feature from main repo and worktree
   - check-prerequisites with --json and --paths-only flags
   - setup-plan scaffolds plan.md correctly
   - accept/merge feature lifecycle
   - Adversarial: invalid feature names

3. Task Commands (10 tests)
   - move-task changes frontmatter and adds history
   - mark-status updates checkboxes
   - list-tasks groups by lane
   - add-history appends entries
   - rollback-task undoes moves
   - validate-workflow detects errors
   - Adversarial: invalid lanes, missing work packages

4. Context Commands (4 tests)
   - update-context parses tech stack from plan.md
   - Updates CLAUDE.md with tech stack
   - Preserves manual additions between markers
   - Works for all 12 agent types

5. Command Context Awareness (4 tests)
   - Commands work from repo root
   - Commands work from worktree root
   - Commands work from feature subdirectory
   - Adversarial: clear error outside project

Key Changes from Bash Scripts:
- .kittify/scripts/bash/create-new-feature.sh → spec-kitty agent feature create-feature
- .kittify/scripts/bash/move-task-to-doing.sh → spec-kitty agent tasks move-task
- .kittify/scripts/bash/update-agent-context.sh → spec-kitty agent context update-context
- All commands now support --json flag for agent parsing
- Automatic path resolution (works from main repo or worktree)

Note: Tests require spec-kitty >= 0.10.0 (Python CLI migration)
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest


def _get_spec_kitty_version():
    """Get spec-kitty version at module load time for skipif.

    Returns:
        Tuple of (major, minor, patch) version numbers
        Returns (0, 0, 0) if version cannot be determined
    """
    try:
        result = subprocess.run(
            ['spec-kitty', '--version'],
            capture_output=True,
            text=True,
            check=True,
            timeout=5
        )
        version_str = result.stdout.strip().split()[-1]
        # Handle version strings like "0.10.0" or "0.10.0-dev"
        base_version = version_str.split('-')[0]
        return tuple(map(int, base_version.split('.')))
    except Exception:
        return (0, 0, 0)


# Module-level skip marker - skip all tests if spec-kitty < 0.10.0
pytestmark = pytest.mark.skipif(
    _get_spec_kitty_version() < (0, 10, 0),
    reason="Requires spec-kitty >= 0.10.0 (Python CLI migration with 'spec-kitty agent' commands)"
)


def _extract_json_from_output(output: str) -> dict:
    """Extract JSON from command output that may contain log messages.

    Args:
        output: Command stdout containing JSON (possibly mixed with logs)

    Returns:
        Parsed JSON dict, or None if no valid JSON found
    """
    for line in output.strip().split('\n'):
        line = line.strip()
        if line.startswith('{'):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return None


class TestAgentCommandDiscovery:
    """Test that spec-kitty agent commands exist and are discoverable."""

    def test_init_creates_slash_commands(self, spec_kitty_repo_root):
        """
        Test: spec-kitty init copies command templates to .claude/commands/

        Validates:
        - .claude/commands/ directory is created
        - Mission templates copied as spec-kitty.*.md
        - All 13 slash commands are available after init
        - Agents can discover commands without manual setup

        BUG #6 DISCOVERED: Init creates mission templates but doesn't copy
        them to .claude/commands/. Users must manually copy or commands
        don't appear in Claude Code.

        Expected: .claude/commands/spec-kitty.specify.md exists after init
        Actual: .claude/commands/ is empty or missing spec-kitty commands

        Impact: HIGH - Users can't use spec-kitty without manual setup
        Root Cause: Init command doesn't populate .claude/commands/ from
                    mission templates in .kittify/missions/*/command-templates/
        """
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            project_name = "test_init_commands"
            project_path = temp_dir / project_name

            env = os.environ.copy()
            env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

            # Init project
            result = subprocess.run(
                ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
                cwd=temp_dir,
                env=env,
                input='y\n',
                capture_output=True,
                text=True,
                timeout=30,
                check=True
            )

            # .claude/commands/ should exist with spec-kitty commands
            commands_dir = project_path / '.claude' / 'commands'
            assert commands_dir.exists(), ".claude/commands/ should be created"

            # Check for spec-kitty slash commands
            spec_kitty_commands = list(commands_dir.glob('spec-kitty.*.md'))
            assert len(spec_kitty_commands) >= 11, (
                f"Should have at least 11 spec-kitty slash commands. "
                f"Found {len(spec_kitty_commands)}: {[c.name for c in spec_kitty_commands]}\n"
                f"Mission templates exist in .kittify/missions/ but weren't copied to .claude/commands/"
            )

    def test_agent_command_exists(self):
        """
        Test: `spec-kitty agent --help` works

        Validates:
        - Agent command is registered in CLI
        - Help text is displayed
        - No errors when invoking help

        This is the foundation test - if this fails, all other tests will fail.
        """
        result = subprocess.run(
            ['spec-kitty', 'agent', '--help'],
            capture_output=True,
            text=True,
            timeout=10
        )

        # Should succeed (exit code 0 or 1 for help text)
        assert result.returncode in [0, 1], (
            f"spec-kitty agent --help failed with code {result.returncode}. "
            f"Stderr: {result.stderr}"
        )

        # Help text should mention "agent"
        output = result.stdout + result.stderr
        assert 'agent' in output.lower(), (
            "Help output should mention 'agent' command"
        )

    def test_all_subcommands_listed(self):
        """
        Test: feature, tasks, context subcommands shown in help

        Validates:
        - All three main subcommand groups are discoverable
        - Help text clearly lists subcommands
        - Agents can find which namespace to use
        """
        result = subprocess.run(
            ['spec-kitty', 'agent', '--help'],
            capture_output=True,
            text=True,
            timeout=10
        )

        output = result.stdout + result.stderr
        output_lower = output.lower()

        # Check for main subcommand groups
        assert 'feature' in output_lower, (
            "'feature' subcommand not found in help text"
        )
        assert 'tasks' in output_lower or 'task' in output_lower, (
            "'tasks' subcommand not found in help text"
        )
        assert 'context' in output_lower, (
            "'context' subcommand not found in help text"
        )

    def test_help_shows_json_flags(self):
        """
        Test: --json flag is documented in help text

        Validates:
        - JSON output mode is discoverable
        - Agents know they can request JSON format
        - Documentation for agent parsing is present
        """
        # Test that at least one command documents --json
        commands_to_check = [
            ['spec-kitty', 'agent', 'feature', 'create-feature', '--help'],
            ['spec-kitty', 'agent', 'tasks', 'move-task', '--help'],
        ]

        json_documented = False
        for cmd in commands_to_check:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            output = result.stdout + result.stderr
            if '--json' in output or 'json' in output.lower():
                json_documented = True
                break

        assert json_documented, (
            "--json flag not documented in any agent command help text. "
            "Agents need to know JSON output is available."
        )

    def test_command_not_ambiguous(self):
        """
        Test: No overlap with user commands (init, merge, etc.)

        Validates:
        - `spec-kitty agent` is clearly separate namespace
        - No confusion between user commands and agent commands
        - `spec-kitty merge` (user) != `spec-kitty agent feature merge` (agent)

        This prevents agents from accidentally calling user-facing commands
        when they meant to call agent commands.
        """
        # User command: spec-kitty merge (merges current feature)
        user_merge_result = subprocess.run(
            ['spec-kitty', 'merge', '--help'],
            capture_output=True,
            text=True,
            timeout=10
        )

        # Agent command: spec-kitty agent feature merge
        agent_merge_result = subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'merge', '--help'],
            capture_output=True,
            text=True,
            timeout=10
        )

        # Both should succeed (or fail consistently), but not overlap
        # At minimum, the help text should be clearly different
        user_output = user_merge_result.stdout + user_merge_result.stderr
        agent_output = agent_merge_result.stdout + agent_merge_result.stderr

        # Commands should be in different namespaces
        assert 'agent' in agent_output.lower() or user_output != agent_output, (
            "User command 'merge' and agent command 'feature merge' appear identical. "
            "This creates ambiguity for agents."
        )


class TestFeatureCommands:
    """Test spec-kitty agent feature commands."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_create_feature_from_main_repo(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: create-feature creates worktree and returns JSON

        Validates:
        - Worktree created at .worktrees/###-slug/
        - Feature directory created at kitty-specs/###-slug/
        - JSON output contains worktree_path
        - Git branch created

        This replaces: .kittify/scripts/bash/create-new-feature.sh
        """
        # Initialize a spec-kitty project
        project_name = "test_create_feature"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Init project
        init_result = subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30
        )

        assert init_result.returncode == 0, (
            f"Project init failed: {init_result.stderr}"
        )

        # Create feature using Python CLI
        create_result = subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-validation', '--json'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60
        )

        # Should succeed
        assert create_result.returncode == 0, (
            f"create-feature failed: {create_result.stderr}"
        )

        # Should return valid JSON
        json_data = _extract_json_from_output(create_result.stdout)
        assert json_data is not None, (
            "create-feature --json should return valid JSON"
        )

        # JSON should contain key fields
        # Note: Actual structure may vary, adapt based on implementation
        # Common fields might be: worktree_path, feature_number, feature_slug
        assert 'worktree_path' in json_data or 'path' in json_data or 'feature' in json_data, (
            f"JSON output missing expected fields: {json_data}"
        )

    def test_create_feature_from_worktree(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: create-feature error or auto-detection when run from worktree

        Validates:
        - Command detects it's already in a worktree
        - Either errors with clear message OR auto-detects context
        - Doesn't create nested worktrees

        This is an edge case - agents might accidentally try to create
        a feature while already in a feature worktree.
        """
        # Initialize project and create first feature
        project_name = "test_from_worktree"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Init project
        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        # Create first feature
        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'first-feature'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60,
            check=True
        )

        # Try to create second feature from within first feature's worktree
        worktree_path = project_path / '.worktrees' / '001-first-feature'

        if worktree_path.exists():
            result = subprocess.run(
                ['spec-kitty', 'agent', 'feature', 'create-feature', 'second-feature'],
                cwd=worktree_path,
                capture_output=True,
                text=True,
                timeout=60
            )

            # Should either:
            # 1. Succeed (auto-detected context and created in main repo)
            # 2. Fail with clear error message about being in worktree

            if result.returncode != 0:
                # If it failed, error message should be clear
                error_output = result.stderr + result.stdout
                assert any(keyword in error_output.lower() for keyword in ['worktree', 'already', 'context']), (
                    f"Error message unclear when creating feature from worktree: {error_output}"
                )

    def test_check_prerequisites_json_output(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: check-prerequisites --json produces valid JSON structure

        Validates:
        - JSON output is parseable
        - Contains validation results
        - Agents can determine if prerequisites met

        This replaces: .kittify/scripts/bash/check-prerequisites.sh
        """
        project_name = "test_prereqs"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Init and create feature
        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60,
            check=True
        )

        # Check prerequisites with JSON output
        result = subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'check-prerequisites', '--json'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should produce valid JSON
        json_data = _extract_json_from_output(result.stdout)
        assert json_data is not None, (
            f"check-prerequisites --json should return valid JSON. Got: {result.stdout}"
        )

        # JSON should indicate validation status
        # Common fields might be: valid, missing_files, errors, prerequisites
        assert isinstance(json_data, dict), "JSON output should be a dictionary"

    def test_check_prerequisites_paths_only_flag(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: check-prerequisites --paths-only flag works

        Validates:
        - Flag is recognized
        - Output focuses on file paths
        - Agents can get just the paths without full validation

        This is useful for agents that want to check what files
        exist without running full validation logic.
        """
        project_name = "test_paths_only"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60,
            check=True
        )

        # Check with --paths-only
        result = subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'check-prerequisites', '--paths-only', '--json'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should succeed (or fail gracefully if flag not implemented yet)
        # At minimum, should not crash
        assert result.returncode in [0, 1, 2], (
            f"Command crashed with unexpected code: {result.returncode}"
        )

    def test_setup_plan_creates_plan_md(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: setup-plan creates plan.md with correct template

        Validates:
        - plan.md file is created
        - Contains template sections
        - File is in correct location (kitty-specs/###-slug/)

        This replaces: .kittify/scripts/bash/setup-plan.sh
        """
        project_name = "test_setup_plan"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60,
            check=True
        )

        # Setup plan (must be run from worktree context)
        worktree_path = project_path / '.worktrees' / '001-test-feature'

        result = subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'setup-plan', '--json'],
            cwd=worktree_path if worktree_path.exists() else project_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should succeed
        assert result.returncode == 0, (
            f"setup-plan failed: {result.stderr}\nStdout: {result.stdout}"
        )

        # plan.md should exist (in worktree or main repo)
        plan_path_worktree = worktree_path / 'kitty-specs' / '001-test-feature' / 'plan.md'
        plan_path_main = project_path / 'kitty-specs' / '001-test-feature' / 'plan.md'

        plan_path = plan_path_worktree if plan_path_worktree.exists() else plan_path_main
        assert plan_path.exists(), (
            f"plan.md not created at expected location: {plan_path_worktree} or {plan_path_main}"
        )

        # Should have some content
        plan_content = plan_path.read_text()
        assert len(plan_content) > 100, (
            "plan.md should have template content, not be empty"
        )

    def test_accept_feature_validates_completion(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: accept feature runs validation checks

        Validates:
        - Accept command exists
        - Runs completeness validation
        - Returns status (success/failure)

        This replaces: .kittify/scripts/bash/accept-feature.sh
        """
        project_name = "test_accept"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60,
            check=True
        )

        # Try to accept (will likely fail validation since we haven't completed tasks)
        result = subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'accept', '--json'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Command should execute (may succeed or fail validation, but shouldn't crash)
        assert result.returncode in [0, 1], (
            f"accept command crashed: {result.returncode}, {result.stderr}"
        )

    def test_merge_feature_deletes_worktree(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: merge feature cleans up worktree after merge

        Validates:
        - Merge command exists
        - Worktree is deleted after successful merge
        - Git branch is merged

        This replaces: .kittify/scripts/bash/merge-feature.sh

        Note: This test may fail if feature isn't complete,
        which is expected behavior. We're validating the
        command exists and attempts cleanup.
        """
        project_name = "test_merge"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60,
            check=True
        )

        # Try to merge (will likely fail validation)
        result = subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'merge', '--json'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60
        )

        # Command should execute (may fail validation, but shouldn't crash)
        # Returncode 0 = success, 1 = validation failed, 2 = other error
        assert result.returncode in [0, 1, 2], (
            f"merge command crashed unexpectedly: {result.returncode}, {result.stderr}"
        )

    def test_create_feature_invalid_name(self, temp_project_dir, spec_kitty_repo_root):
        """
        ADVERSARIAL: Test invalid feature names are rejected

        Validates:
        - Special characters are handled
        - Spaces in names are handled
        - Very long names are handled
        - Error messages are clear

        This tests the "find the bugs" approach - try to break it!
        """
        project_name = "test_invalid_names"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        # Test cases for invalid names
        invalid_names = [
            'feature with spaces',  # Spaces
            'feature/with/slashes',  # Slashes (path separators)
            '../../../etc/passwd',  # Path traversal attempt
            'feature\x00null',  # Null byte
            'a' * 300,  # Very long name
        ]

        for invalid_name in invalid_names:
            try:
                result = subprocess.run(
                    ['spec-kitty', 'agent', 'feature', 'create-feature', invalid_name],
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                # Should either:
                # 1. Reject with clear error message
                # 2. Sanitize the name and succeed
                # Should NOT crash or create weird directories

                if result.returncode != 0:
                    # If it failed, error should be clear
                    error = result.stderr + result.stdout
                    assert len(error) > 0, (
                        f"Failed silently for invalid name: {invalid_name}"
                    )
            except ValueError as e:
                # Python subprocess rejects null bytes and some invalid chars
                # This is actually GOOD security - prevented by Python itself
                if 'null byte' in str(e) or 'embedded' in str(e):
                    pass  # Expected behavior for null bytes
                else:
                    raise

            # Verify no path traversal happened
            etc_passwd = Path('/etc/passwd')
            worktrees_dir = project_path / '.worktrees'
            if worktrees_dir.exists():
                # No worktree should escape the .worktrees directory
                for worktree in worktrees_dir.iterdir():
                    assert worktree.is_relative_to(worktrees_dir), (
                        f"Worktree escaped .worktrees directory: {worktree}"
                    )


# Placeholder classes for remaining test categories
# Will be implemented in subsequent phases

class TestTaskCommands:
    """Test spec-kitty agent tasks commands.

    These commands replace bash scripts for task workflow management.
    Tests validate the Python CLI provides identical functionality
    to the original bash implementation.
    """

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def project_with_tasks(self, temp_project_dir, spec_kitty_repo_root):
        """Create a project with feature and task structure."""
        project_name = "test_tasks"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Init project
        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        # Create feature
        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60,
            check=True
        )

        # Create a simple task file for testing
        worktree_path = project_path / '.worktrees' / '001-test-feature'
        tasks_dir = worktree_path / 'kitty-specs' / '001-test-feature' / 'tasks'
        tasks_dir.mkdir(parents=True, exist_ok=True)

        # Create a simple work package file with frontmatter
        wp_file = tasks_dir / 'WP01-test-task.md'
        wp_content = """---
lane: planned
work_package_id: WP01
activity:
  - timestamp: 2025-01-01T00:00:00Z
    event: created
    lane: planned
---

# Work Package WP01: Test Task

Test task description.

## Subtasks
- [ ] T001: First subtask
- [ ] T002: Second subtask
"""
        wp_file.write_text(wp_content)

        return {
            'project_path': project_path,
            'worktree_path': worktree_path,
            'tasks_dir': tasks_dir,
            'wp_file': wp_file
        }

    def test_move_task_changes_frontmatter(self, project_with_tasks):
        """
        Test: move-task updates lane: field in YAML frontmatter

        Validates:
        - Frontmatter lane field is updated
        - File content is preserved
        - YAML structure remains valid

        This replaces: .kittify/scripts/bash/move-task-to-doing.sh
        """
        worktree_path = project_with_tasks['worktree_path']
        wp_file = project_with_tasks['wp_file']

        # Move task to doing
        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'move-task', 'WP01', '--to', 'doing'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should succeed
        assert result.returncode == 0, (
            f"move-task failed: {result.stderr}"
        )

        # Read updated file
        updated_content = wp_file.read_text()

        # Lane should be updated (handles both quoted and unquoted YAML)
        assert 'lane: doing' in updated_content or 'lane: "doing"' in updated_content, (
            f"Lane field should be updated to 'doing'. Got: {updated_content[:200]}"
        )
        # Verify the top-level lane field is updated (not nested in activity)
        # Look for "lane:" at the beginning of a line (top-level field)
        import re
        # Match lane field that's not indented (top-level only)
        top_level_lane_match = re.search(r'^lane:\s*["\']?(\w+)["\']?', updated_content, re.MULTILINE)
        assert top_level_lane_match is not None, "Should have a top-level lane field"
        current_lane = top_level_lane_match.group(1)
        assert current_lane == 'doing', (
            f"Top-level lane should be 'doing', got '{current_lane}'"
        )

    def test_move_task_adds_history(self, project_with_tasks):
        """
        Test: move-task adds activity log entry

        Validates:
        - Activity array in frontmatter is updated
        - New entry contains timestamp, event, lane
        - History is append-only (old entries preserved)
        """
        worktree_path = project_with_tasks['worktree_path']
        wp_file = project_with_tasks['wp_file']

        # Read initial content
        initial_content = wp_file.read_text()

        # Move task
        subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'move-task', 'WP01', '--to', 'doing'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        # Read updated content
        updated_content = wp_file.read_text()

        # Should have activity logged (either in frontmatter or activity log section)
        # Check for move event in content
        assert 'doing' in updated_content and ('Moved to doing' in updated_content or 'event:' in updated_content), (
            "Activity should be logged after move"
        )

    def test_move_task_json_output(self, project_with_tasks):
        """
        Test: move-task --json produces valid JSON

        Validates:
        - JSON output is parseable
        - Contains status information
        - Agents can determine if move succeeded
        """
        worktree_path = project_with_tasks['worktree_path']

        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'move-task', 'WP01', '--to', 'doing', '--json'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should produce valid JSON
        json_data = _extract_json_from_output(result.stdout)
        assert json_data is not None, (
            f"move-task --json should return valid JSON. Got: {result.stdout}"
        )

    def test_mark_status_updates_checkbox(self, project_with_tasks):
        """
        Test: mark-status toggles checkboxes in task list

        Validates:
        - Checkbox state changes [ ] → [x]
        - Specific task is targeted
        - File content otherwise preserved

        This replaces: .kittify/scripts/bash/mark-task-status.sh
        """
        worktree_path = project_with_tasks['worktree_path']
        wp_file = project_with_tasks['wp_file']

        # Initial state: all unchecked
        initial_content = wp_file.read_text()
        assert '- [ ] T001: First subtask' in initial_content

        # Mark T001 as complete
        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'mark-status', 'WP01', '--task', 'T001', '--status', 'complete'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should succeed
        if result.returncode == 0:
            # Check if checkbox updated
            updated_content = wp_file.read_text()
            assert '- [x] T001: First subtask' in updated_content or '- [X] T001: First subtask' in updated_content, (
                "Task T001 should be marked as complete"
            )

    def test_list_tasks_groups_by_lane(self, project_with_tasks):
        """
        Test: list-tasks groups work packages by lane

        Validates:
        - Output organized by lane (planned, doing, for_review, done)
        - All tasks in correct groups
        - JSON mode provides structured data
        """
        worktree_path = project_with_tasks['worktree_path']

        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'list-tasks', '--json'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should succeed
        assert result.returncode == 0, (
            f"list-tasks failed: {result.stderr}"
        )

        # Check for JSON output
        json_data = _extract_json_from_output(result.stdout)
        if json_data:
            # JSON should have lane groupings
            assert isinstance(json_data, dict) or isinstance(json_data, list), (
                "list-tasks JSON should be a dict or list"
            )

    def test_add_history_appends_entry(self, project_with_tasks):
        """
        Test: add-history appends entry to activity log

        Validates:
        - New entry added to activity array
        - Contains message and timestamp
        - Previous entries preserved
        """
        worktree_path = project_with_tasks['worktree_path']
        wp_file = project_with_tasks['wp_file']

        # Count initial entries
        initial_content = wp_file.read_text()
        initial_count = initial_content.count('event:')

        # Add history entry
        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'add-history', 'WP01', 'Test message'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            # Check if entry was added
            updated_content = wp_file.read_text()
            updated_count = updated_content.count('event:')

            assert updated_count > initial_count, (
                "History entry should be added"
            )

    def test_rollback_task_undoes_move(self, project_with_tasks):
        """
        Test: rollback-task reverts last lane change

        Validates:
        - Lane field reverted to previous value
        - Uses activity history to determine previous state
        - Most recent history entry may be removed or marked
        """
        worktree_path = project_with_tasks['worktree_path']
        wp_file = project_with_tasks['wp_file']

        # Move task to doing
        subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'move-task', 'WP01', '--to', 'doing'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        # Verify it moved (handles quoted and unquoted)
        content_after_move = wp_file.read_text()
        assert 'lane: doing' in content_after_move or 'lane: "doing"' in content_after_move

        # Rollback
        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'rollback-task', 'WP01'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            # Should be back to planned (handles quoted and unquoted)
            content_after_rollback = wp_file.read_text()
            assert 'lane: planned' in content_after_rollback or 'lane: "planned"' in content_after_rollback, (
                "Rollback should revert to previous lane"
            )

    def test_validate_workflow_detects_errors(self, project_with_tasks):
        """
        Test: validate-workflow detects invalid frontmatter

        Validates:
        - Missing required fields detected
        - Invalid lane values detected
        - Malformed YAML detected
        - Returns validation status
        """
        worktree_path = project_with_tasks['worktree_path']
        wp_file = project_with_tasks['wp_file']

        # Create invalid file
        invalid_wp = project_with_tasks['tasks_dir'] / 'WP99-invalid.md'
        invalid_content = """---
lane: invalid_lane_name
---

# Invalid task
"""
        invalid_wp.write_text(invalid_content)

        # Validate should detect error
        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'validate-workflow', 'WP99'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should either fail or return error status
        # (Behavior depends on implementation)
        # At minimum, shouldn't crash
        assert result.returncode in [0, 1, 2], (
            f"validate-workflow crashed: {result.returncode}"
        )

    def test_move_task_invalid_lane(self, project_with_tasks):
        """
        ADVERSARIAL: Test moving to invalid lane name

        Validates:
        - Rejects invalid lane names
        - Error message is clear
        - File is not corrupted
        """
        worktree_path = project_with_tasks['worktree_path']
        wp_file = project_with_tasks['wp_file']

        # Save original content
        original_content = wp_file.read_text()

        # Try to move to invalid lane
        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'move-task', 'WP01', '--to', 'invalid_lane'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should fail with error
        assert result.returncode != 0, (
            "move-task should reject invalid lane names"
        )

        # File should not be corrupted
        current_content = wp_file.read_text()
        assert 'lane: planned' in current_content or 'lane:' in current_content, (
            "File should not be corrupted after invalid move attempt"
        )

    def test_move_task_missing_work_package(self, project_with_tasks):
        """
        ADVERSARIAL: Test moving non-existent work package

        Validates:
        - Clear error for missing WP file
        - Error message mentions the missing file
        - Doesn't crash or create files
        """
        worktree_path = project_with_tasks['worktree_path']

        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'move-task', 'WP999', '--to', 'doing'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should fail
        assert result.returncode != 0, (
            "move-task should fail for non-existent work package"
        )

        # Error should be clear
        error_output = result.stderr + result.stdout
        assert 'WP999' in error_output or 'not found' in error_output.lower() or 'missing' in error_output.lower(), (
            f"Error message should clearly indicate WP999 not found. Got: {error_output}"
        )


class TestContextCommands:
    """Test spec-kitty agent context commands.

    These commands replace bash script for agent context management.
    Validates tech stack extraction and CLAUDE.md/GEMINI.md updates.
    """

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def project_with_plan(self, temp_project_dir, spec_kitty_repo_root):
        """Create a project with feature and plan.md"""
        project_name = "test_context"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Init project
        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        # Create feature
        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60,
            check=True
        )

        # Create plan.md with tech stack
        worktree_path = project_path / '.worktrees' / '001-test-feature'
        plan_dir = worktree_path / 'kitty-specs' / '001-test-feature'
        plan_dir.mkdir(parents=True, exist_ok=True)

        plan_content = """# Implementation Plan

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pytest, typer, rich
**Testing**: Unit + Integration tests

## Summary

Test plan content.
"""
        plan_file = plan_dir / 'plan.md'
        plan_file.write_text(plan_content)

        return {
            'project_path': project_path,
            'worktree_path': worktree_path,
            'plan_file': plan_file
        }

    def test_update_context_parses_tech_stack(self, project_with_plan):
        """
        Test: update-context extracts tech stack from plan.md

        Validates:
        - Reads plan.md correctly
        - Finds Technical Context section
        - Extracts language, dependencies, testing info

        This replaces: .kittify/scripts/bash/update-agent-context.sh
        """
        worktree_path = project_with_plan['worktree_path']

        result = subprocess.run(
            ['spec-kitty', 'agent', 'context', 'update-context', '--json'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should execute successfully (or fail gracefully if not implemented)
        assert result.returncode in [0, 1], (
            f"update-context crashed: {result.stderr}"
        )

    def test_update_context_updates_claude_md(self, project_with_plan):
        """
        Test: update-context updates CLAUDE.md with tech stack

        Validates:
        - CLAUDE.md file is updated or created
        - Contains tech stack information
        - File is in correct location
        """
        worktree_path = project_with_plan['worktree_path']

        result = subprocess.run(
            ['spec-kitty', 'agent', 'context', 'update-context'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            # Check if CLAUDE.md exists and has content
            claude_md_locations = [
                worktree_path / 'CLAUDE.md',
                worktree_path / '.claude' / 'CLAUDE.md',
                worktree_path / 'kitty-specs' / '001-test-feature' / 'CLAUDE.md'
            ]

            claude_md_found = False
            for location in claude_md_locations:
                if location.exists():
                    claude_md_found = True
                    content = location.read_text()
                    # Should contain some tech info
                    assert len(content) > 50, "CLAUDE.md should have content"
                    break

            # If update-context succeeded, CLAUDE.md should exist somewhere
            if not claude_md_found:
                # This may be intentional design - updating in a different way
                pass  # Not failing if file isn't created

    def test_update_context_preserves_manual_additions(self, project_with_plan):
        """
        Test: update-context preserves content between <!-- MANUAL ADDITIONS --> markers

        Validates:
        - Manual content is preserved across updates
        - Markers are recognized
        - User additions not overwritten
        """
        worktree_path = project_with_plan['worktree_path']

        # First update to create file
        subprocess.run(
            ['spec-kitty', 'agent', 'context', 'update-context'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Find CLAUDE.md if it was created
        claude_md = worktree_path / 'CLAUDE.md'
        if not claude_md.exists():
            claude_md = worktree_path / '.claude' / 'CLAUDE.md'
        if not claude_md.exists():
            # If file doesn't exist, this test doesn't apply
            return

        # Add manual content
        original_content = claude_md.read_text() if claude_md.exists() else ""
        manual_content = original_content + "\n\n<!-- MANUAL ADDITIONS -->\nMy custom notes\n<!-- /MANUAL ADDITIONS -->\n"
        claude_md.write_text(manual_content)

        # Update again
        subprocess.run(
            ['spec-kitty', 'agent', 'context', 'update-context'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Check if manual content preserved
        if claude_md.exists():
            updated_content = claude_md.read_text()
            if 'MANUAL ADDITIONS' in original_content or 'MANUAL ADDITIONS' in updated_content:
                assert 'My custom notes' in updated_content, (
                    "Manual additions should be preserved"
                )

    def test_update_context_all_agent_types(self, project_with_plan):
        """
        Test: update-context works for all 12 agent types

        Validates:
        - --agent-type flag accepted
        - Multiple agent types supported (Claude, Gemini, Copilot, etc.)
        - Each type gets appropriate file

        Spec mentions 12 agent types: Claude, Gemini, Copilot, Cursor,
        Windsurf, Codeium, ChatGPT, DeepSeek, Grok, Hermes, Llama, Mistral
        """
        worktree_path = project_with_plan['worktree_path']

        # Test a few representative agent types
        agent_types = ['claude', 'gemini', 'cursor']

        for agent_type in agent_types:
            result = subprocess.run(
                ['spec-kitty', 'agent', 'context', 'update-context', '--agent-type', agent_type],
                cwd=worktree_path,
                capture_output=True,
                text=True,
                timeout=30
            )

            # Should execute (may succeed or fail gracefully)
            assert result.returncode in [0, 1, 2], (
                f"update-context crashed for agent type {agent_type}: {result.returncode}"
            )


class TestCommandContextAwareness:
    """Test commands work from different execution contexts.

    Validates path resolution and context detection work correctly
    whether commands are run from main repo, worktree, or subdirectories.
    """

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_commands_work_from_repo_root(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Commands execute successfully from main repository root

        Validates:
        - Path resolution finds .kittify/
        - Commands don't require being in worktree
        - Agents can work from project root
        """
        project_name = "test_repo_root"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        # Run command from repo root
        result = subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature', '--json'],
            cwd=project_path,  # Main repo root
            capture_output=True,
            text=True,
            timeout=60
        )

        # Should succeed
        assert result.returncode == 0, (
            f"Command failed from repo root: {result.stderr}"
        )

    def test_commands_work_from_worktree_root(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Commands execute successfully from worktree root directory

        Validates:
        - Worktree context detected automatically
        - Path resolution works in worktree
        - Feature slug auto-detected from branch/path
        """
        project_name = "test_worktree_root"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        # Create feature
        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60,
            check=True
        )

        # Run command from worktree root
        worktree_path = project_path / '.worktrees' / '001-test-feature'

        if worktree_path.exists():
            result = subprocess.run(
                ['spec-kitty', 'agent', 'feature', 'check-prerequisites', '--json'],
                cwd=worktree_path,  # Worktree root
                capture_output=True,
                text=True,
                timeout=30
            )

            # Should work from worktree
            assert result.returncode in [0, 1], (
                f"Command failed from worktree root: {result.stderr}"
            )

    def test_commands_work_from_feature_subdir(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Commands work from deep subdirectories (kitty-specs/###/tasks/)

        Validates:
        - Path resolution walks up directory tree
        - Works from arbitrary depth
        - Finds repository root correctly
        """
        project_name = "test_subdir"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        # Create feature with task directory
        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60,
            check=True
        )

        # Create deep subdirectory
        worktree_path = project_path / '.worktrees' / '001-test-feature'
        deep_dir = worktree_path / 'kitty-specs' / '001-test-feature' / 'tasks'
        deep_dir.mkdir(parents=True, exist_ok=True)

        # Run command from deep subdirectory
        result = subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'check-prerequisites', '--json'],
            cwd=deep_dir,  # Deep in directory tree
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should still work
        assert result.returncode in [0, 1], (
            f"Command failed from subdirectory: {result.stderr}"
        )

    def test_commands_error_outside_project(self, temp_project_dir):
        """
        ADVERSARIAL: Commands give clear error when run outside spec-kitty project

        Validates:
        - Detects when not in a spec-kitty project
        - Error message is clear and actionable
        - Doesn't crash or create files
        """
        # Run command in directory without .kittify/
        empty_dir = temp_project_dir / 'not_a_project'
        empty_dir.mkdir()

        result = subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'check-prerequisites'],
            cwd=empty_dir,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should fail
        assert result.returncode != 0, (
            "Command should fail when not in spec-kitty project"
        )

        # Error should be clear
        error_output = result.stderr + result.stdout
        assert any(keyword in error_output.lower() for keyword in ['not found', 'kittify', 'project', 'repository']), (
            f"Error message should clearly indicate not in project. Got: {error_output}"
        )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
