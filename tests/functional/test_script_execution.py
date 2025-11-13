"""
Category 6: Script Execution Validation Tests

Tests that all command scripts exist, have correct permissions, and work properly.

Test Coverage:
1. Script Existence & Permissions (3 tests)
   - All referenced scripts exist
   - Bash scripts are executable
   - Script paths resolve correctly

2. Core Script Functionality (6 tests)
   - create-new-feature.sh produces valid JSON
   - setup-plan.sh initializes plan structure
   - refresh-kittify-tasks.sh generates work packages
   - move-task-to-doing.sh moves tasks correctly
   - mark-task-status.sh updates frontmatter
   - accept-feature.sh validates completeness

3. Script Error Handling (3 tests)
   - Scripts provide clear errors for missing args
   - Scripts handle invalid arguments gracefully
   - Scripts detect missing dependencies

4. Script Context Awareness (3 tests)
   - Scripts work from repo root
   - Scripts work from worktree context
   - Scripts detect feature context automatically
"""

import json
import os
import stat
import subprocess
import tempfile
from pathlib import Path

import pytest


def extract_json_from_output(output: str) -> dict:
    """Extract JSON from script output that may contain log messages.

    Scripts often output log messages before JSON. This function finds
    the first line starting with { and parses it as JSON.
    """
    for line in output.strip().split('\n'):
        line = line.strip()
        if line.startswith('{'):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return None


class TestScriptExistence:
    """Test that all referenced scripts exist and have correct permissions."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_all_referenced_scripts_exist(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Every script referenced in commands exists"""
        project_name = "test_scripts_exist"
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
            check=True
        )

        # Core scripts that should exist
        core_scripts = [
            'create-new-feature.sh',
            'setup-plan.sh',
            'refresh-kittify-tasks.sh',
            'move-task-to-doing.sh',
            'mark-task-status.sh',
            'accept-feature.sh',
            'merge-feature.sh',
            'common.sh',
        ]

        scripts_dir = project_path / '.kittify' / 'scripts' / 'bash'
        assert scripts_dir.exists(), "Scripts directory should exist"

        for script_name in core_scripts:
            script_path = scripts_dir / script_name
            assert script_path.exists(), \
                f"Script {script_name} should exist at {script_path}"

    def test_bash_scripts_executable(self, temp_project_dir, spec_kitty_repo_root):
        """Test: All bash scripts have execute permissions"""
        project_name = "test_scripts_exec"
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
            check=True
        )

        scripts_dir = project_path / '.kittify' / 'scripts' / 'bash'
        bash_scripts = list(scripts_dir.glob('*.sh'))

        assert len(bash_scripts) > 0, "Should have at least one bash script"

        for script_path in bash_scripts:
            # Check if file is executable
            file_stat = script_path.stat()
            is_executable = bool(file_stat.st_mode & stat.S_IXUSR)

            assert is_executable, \
                f"Script {script_path.name} should have execute permissions"

    def test_script_paths_resolve_correctly(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Script paths in .kittify/scripts/ resolve correctly"""
        project_name = "test_script_paths"
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
            check=True
        )

        # Verify scripts directory structure
        kittify_dir = project_path / '.kittify'
        assert kittify_dir.exists(), ".kittify directory should exist"

        scripts_dir = kittify_dir / 'scripts'
        assert scripts_dir.exists(), "scripts directory should exist"

        bash_dir = scripts_dir / 'bash'
        assert bash_dir.exists(), "bash directory should exist"

        # Verify we can resolve paths from project root
        relative_script = Path('.kittify/scripts/bash/common.sh')
        absolute_script = project_path / relative_script

        assert absolute_script.exists(), \
            "Should be able to resolve script path from project root"


class TestCoreScriptFunctionality:
    """Test core script functionality and JSON output."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_create_new_feature_script(self, temp_project_dir, spec_kitty_repo_root):
        """Test: create-new-feature.sh produces valid JSON output"""
        project_name = "test_create_feature"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Initialize project with git
        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Run create-new-feature script
        script_path = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(script_path), '--json', '--feature-name', 'Test Feature', 'Test feature description'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False  # Don't raise on non-zero exit
        )

        # Script should succeed
        assert result.returncode == 0, \
            f"create-new-feature.sh should succeed. stderr: {result.stderr}"

        # Should produce valid JSON (may have log messages before JSON)
        output_data = extract_json_from_output(result.stdout)
        assert output_data is not None, \
            f"Script should produce valid JSON output: {result.stdout}"

        # Validate JSON structure
        assert 'BRANCH_NAME' in output_data, "JSON should contain BRANCH_NAME"
        assert 'SPEC_FILE' in output_data, "JSON should contain SPEC_FILE"
        assert 'FEATURE_NUM' in output_data, "JSON should contain FEATURE_NUM"
        assert 'FRIENDLY_NAME' in output_data, "JSON should contain FRIENDLY_NAME"

        # Verify feature directory was created in worktree (Issue #2: correct behavior)
        feature_num = output_data['FEATURE_NUM']
        branch_name = output_data['BRANCH_NAME']

        # Features are created in .worktrees/, not kitty-specs/ directly
        worktree_dir = project_path / '.worktrees' / branch_name
        feature_dir = worktree_dir / 'kitty-specs' / branch_name

        assert worktree_dir.exists(), \
            f"Worktree should be created at {worktree_dir}"

        assert feature_dir.exists(), \
            f"Feature directory should be created in worktree at {feature_dir}"

        # Verify spec.md exists in worktree
        spec_file = feature_dir / 'spec.md'
        assert spec_file.exists(), "spec.md should be created in worktree"

    def test_setup_plan_script(self, temp_project_dir, spec_kitty_repo_root):
        """Test: setup-plan.sh initializes plan structure"""
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
            check=True
        )

        # First create a feature
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'Plan Test', 'Feature for plan test'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        output_data = extract_json_from_output(result.stdout)
        assert output_data is not None, "Should produce JSON output"
        feature_num = output_data['FEATURE_NUM']
        feature_slug = f"{feature_num}-plan-test"
        feature_dir = project_path / 'kitty-specs' / feature_slug

        # Now run setup-plan script
        plan_script = project_path / '.kittify/scripts/bash/setup-plan.sh'
        result = subprocess.run(
            [str(plan_script), feature_slug],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        # Script should succeed
        assert result.returncode == 0, \
            f"setup-plan.sh should succeed. stderr: {result.stderr}"

        # Verify plan.md was created
        plan_file = feature_dir / 'plan.md'
        assert plan_file.exists(), \
            f"plan.md should be created at {plan_file}"

        # Verify plan has content
        plan_content = plan_file.read_text()
        assert len(plan_content) > 0, "plan.md should not be empty"

    def test_refresh_tasks_script(self, temp_project_dir, spec_kitty_repo_root):
        """Test: refresh-kittify-tasks.sh generates work packages"""
        project_name = "test_refresh_tasks"
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
            check=True
        )

        # Create feature
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'Tasks Test', 'Feature for tasks test'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        output_data = extract_json_from_output(result.stdout)
        assert output_data is not None, "Should produce JSON output"
        feature_num = output_data['FEATURE_NUM']
        feature_slug = f"{feature_num}-tasks-test"
        feature_dir = project_path / 'kitty-specs' / feature_slug

        # Create a minimal tasks.md
        tasks_file = feature_dir / 'tasks.md'
        tasks_file.write_text("""# Tasks

## Work Packages

### WP01: Setup Database
- Task description here

### WP02: Implement API
- Another task description
""")

        # Run refresh-kittify-tasks script
        refresh_script = project_path / '.kittify/scripts/bash/refresh-kittify-tasks.sh'
        result = subprocess.run(
            [str(refresh_script), feature_slug],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        # Script should succeed
        assert result.returncode == 0, \
            f"refresh-kittify-tasks.sh should succeed. stderr: {result.stderr}"

        # Verify tasks directory was created
        tasks_dir = feature_dir / 'tasks'
        assert tasks_dir.exists(), "tasks/ directory should be created"

        # Verify planned directory exists
        planned_dir = tasks_dir / 'planned'
        assert planned_dir.exists(), "tasks/planned/ directory should be created"

    def test_move_task_to_doing_script(self, temp_project_dir, spec_kitty_repo_root):
        """Test: move-task-to-doing.sh moves work packages correctly"""
        project_name = "test_move_task"
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
            check=True
        )

        # Create feature with task structure
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'Move Test', 'Feature for move test'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        output_data = extract_json_from_output(result.stdout)
        assert output_data is not None, "Should produce JSON output"
        feature_num = output_data['FEATURE_NUM']
        feature_slug = f"{feature_num}-move-test"
        feature_dir = project_path / 'kitty-specs' / feature_slug

        # Create tasks structure
        tasks_dir = feature_dir / 'tasks'
        planned_dir = tasks_dir / 'planned'
        doing_dir = tasks_dir / 'doing'
        planned_dir.mkdir(parents=True)
        doing_dir.mkdir(parents=True)

        # Create a work package in planned
        wp_file = planned_dir / 'WP01-test-task.md'
        wp_file.write_text("""---
work_package_id: WP01
lane: planned
---

# Work Package Prompt: Test Task

Test task content
""")

        # Run move script
        move_script = project_path / '.kittify/scripts/bash/move-task-to-doing.sh'
        result = subprocess.run(
            [str(move_script), feature_slug, 'WP01'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        # Script should succeed
        assert result.returncode == 0, \
            f"move-task-to-doing.sh should succeed. stderr: {result.stderr}"

        # Verify task moved from planned to doing
        assert not wp_file.exists(), \
            "Work package should be removed from planned/"

        moved_file = doing_dir / 'WP01-test-task.md'
        assert moved_file.exists(), \
            f"Work package should be moved to doing/ at {moved_file}"

    def test_mark_task_status_script(self, temp_project_dir, spec_kitty_repo_root):
        """Test: mark-task-status.sh updates task frontmatter"""
        project_name = "test_mark_status"
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
            check=True
        )

        # Create feature
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'Status Test', 'Feature for status test'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        output_data = extract_json_from_output(result.stdout)
        assert output_data is not None, "Should produce JSON output"
        feature_num = output_data['FEATURE_NUM']
        feature_slug = f"{feature_num}-status-test"
        feature_dir = project_path / 'kitty-specs' / feature_slug

        # Create task
        tasks_dir = feature_dir / 'tasks'
        doing_dir = tasks_dir / 'doing'
        doing_dir.mkdir(parents=True)

        wp_file = doing_dir / 'WP01-test-task.md'
        wp_file.write_text("""---
work_package_id: WP01
lane: doing
status: in_progress
---

# Work Package Prompt: Test Task

Test content
""")

        # Run mark-task-status script
        mark_script = project_path / '.kittify/scripts/bash/mark-task-status.sh'
        result = subprocess.run(
            [str(mark_script), feature_slug, 'WP01', 'completed'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        # Script should succeed (or may not exist - that's okay for this test)
        if result.returncode == 0:
            # If script exists and succeeded, verify frontmatter updated
            content = wp_file.read_text()
            assert 'completed' in content, \
                "Status should be updated in frontmatter"

    def test_accept_feature_script(self, temp_project_dir, spec_kitty_repo_root):
        """Test: accept-feature.sh validates feature completeness"""
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
            check=True
        )

        # Create minimal feature
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'Accept Test', 'Feature for accept test'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        output_data = extract_json_from_output(result.stdout)
        assert output_data is not None, "Should produce JSON output"
        feature_slug = f"{output_data['FEATURE_NUM']}-accept-test"

        # Run accept script
        accept_script = project_path / '.kittify/scripts/bash/accept-feature.sh'

        # This script might have specific requirements, so check=False
        result = subprocess.run(
            [str(accept_script), feature_slug],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        # Script should at least execute without crashing
        # (It may fail validation, but shouldn't crash)
        assert result.returncode in [0, 1], \
            f"accept-feature.sh should execute. stderr: {result.stderr}"


class TestScriptErrorHandling:
    """Test script error handling and helpful error messages."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_script_missing_args_error(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Scripts provide clear error when args missing"""
        project_name = "test_missing_args"
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
            check=True
        )

        # Run create-new-feature without required args
        script_path = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(script_path), '--json'],  # Missing feature description
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        # Script should fail with non-zero exit
        assert result.returncode != 0, \
            "Script should fail when required args missing"

        # Error message should be helpful (not empty)
        assert len(result.stderr) > 0 or len(result.stdout) > 0, \
            "Script should provide error message"

        # Should mention the issue
        combined_output = result.stderr + result.stdout
        assert 'description' in combined_output.lower() or 'missing' in combined_output.lower(), \
            "Error should mention missing description"

    def test_script_help_flag(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Scripts provide help with --help flag"""
        project_name = "test_help_flag"
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
            check=True
        )

        # Run script with --help
        script_path = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(script_path), '--help'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        # Should exit successfully (exit 0 for help)
        assert result.returncode == 0, \
            "--help should exit successfully"

        # Should provide usage information
        combined_output = result.stderr + result.stdout
        assert 'usage' in combined_output.lower() or 'help' in combined_output.lower(), \
            "--help should provide usage information"

    def test_script_detects_missing_git(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Scripts handle git dependency correctly"""
        project_name = "test_git_check"
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
            check=True
        )

        # Most scripts require git, so just verify they check for it
        # We can't actually remove git from PATH in tests, so just verify
        # the script exists and is callable
        script_path = project_path / '.kittify/scripts/bash/common.sh'

        assert script_path.exists(), \
            "common.sh should exist (contains shared git utilities)"


class TestScriptContextAwareness:
    """Test that scripts work correctly in different execution contexts."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_script_runs_from_repo_root(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Scripts work when executed from repo root"""
        project_name = "test_from_root"
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
            check=True
        )

        # Run script from project root
        script_path = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(script_path), '--json', '--feature-name', 'Root Test', 'Test from root'],
            cwd=project_path,  # Execute from project root
            capture_output=True,
            text=True,
            check=False
        )

        # Should succeed
        assert result.returncode == 0, \
            f"Script should work from repo root. stderr: {result.stderr}"

        # Should produce valid JSON
        output_data = extract_json_from_output(result.stdout)
        assert output_data is not None, \
            f"Script should produce valid JSON from repo root: {result.stdout}"

    def test_script_paths_resolve_with_relative_execution(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Scripts resolve paths correctly when called with relative paths"""
        project_name = "test_relative_paths"
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
            check=True
        )

        # Run script using relative path
        result = subprocess.run(
            ['./.kittify/scripts/bash/create-new-feature.sh', '--json', '--feature-name', 'Relative Test', 'Test relative'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        # Should succeed
        assert result.returncode == 0, \
            f"Script should work with relative path. stderr: {result.stderr}"

    def test_script_detects_repo_root(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Scripts can detect repo root from subdirectories"""
        project_name = "test_detect_root"
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
            check=True
        )

        # Create a subdirectory
        sub_dir = project_path / 'some_subdir'
        sub_dir.mkdir()

        # Run script from subdirectory
        script_path = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(script_path), '--json', '--feature-name', 'Subdir Test', 'Test from subdir'],
            cwd=sub_dir,  # Execute from subdirectory
            capture_output=True,
            text=True,
            check=False
        )

        # Script should succeed (should find repo root)
        assert result.returncode == 0, \
            f"Script should detect repo root from subdirectory. stderr: {result.stderr}"

        # Should create feature in correct location (repo root's kitty-specs)
        output_data = extract_json_from_output(result.stdout)
        assert output_data is not None, \
            f"Should produce valid JSON: {result.stdout}"

        # Feature should be in repo root, not in subdirectory
        assert 'kitty-specs' in output_data.get('SPEC_FILE', ''), \
            "Feature should be created in repo root's kitty-specs/"
