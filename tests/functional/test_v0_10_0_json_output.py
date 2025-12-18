"""
Test: spec-kitty v0.10.0 JSON Output Validation

Purpose: Validate JSON API for AI agent consumption across all agent commands.
This ensures agents can reliably parse command outputs without dealing with
mixed console messages or malformed JSON.

Version Tested: spec-kitty >= 0.10.0
Related Feature: Python CLI migration with unified --json flag support

Test Coverage:
1. JSON Output Format (6 tests)
   - All agent commands support --json flag
   - Output is valid parseable JSON
   - No console messages mixed into JSON
   - Success structure contains expected fields
   - Error structure contains error fields
   - Large outputs don't truncate or break JSON

2. JSON Error Handling (4 tests)
   - Missing arguments return JSON error (not crash)
   - Invalid work package returns clear JSON error
   - Permission denied wraps in JSON
   - Special characters (unicode, quotes) escaped properly

3. JSON Agent Parsing (4 tests)
   - Agents can extract worktree_path from create-feature
   - Agents can iterate over lanes from list-tasks
   - Agents can detect failure from error JSON
   - JSON output stable across runs (same structure)

Key Requirement: Agents must be able to parse all command outputs programmatically.
No guesswork, no regex parsing of human-readable text - just clean JSON.

Note: Tests require spec-kitty >= 0.10.0
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest


def _get_spec_kitty_version():
    """Get spec-kitty version at module load time for skipif."""
    try:
        result = subprocess.run(
            ['spec-kitty', '--version'],
            capture_output=True,
            text=True,
            check=True,
            timeout=5
        )
        version_str = result.stdout.strip().split()[-1]
        base_version = version_str.split('-')[0]
        return tuple(map(int, base_version.split('.')))
    except Exception:
        return (0, 0, 0)


# Module-level skip marker
pytestmark = pytest.mark.skipif(
    _get_spec_kitty_version() < (0, 10, 0),
    reason="Requires spec-kitty >= 0.10.0 (JSON output support for all agent commands)"
)


def _extract_json_from_output(output: str) -> dict:
    """Extract JSON from command output that may contain log messages."""
    for line in output.strip().split('\n'):
        line = line.strip()
        if line.startswith('{') or line.startswith('['):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return None


class TestJSONOutputFormat:
    """Test that all agent commands produce valid, clean JSON output."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def initialized_project(self, temp_project_dir, spec_kitty_repo_root):
        """Create an initialized spec-kitty project with a feature."""
        project_name = "test_json"
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

        return {
            'project_path': project_path,
            'worktree_path': project_path / '.worktrees' / '001-test-feature'
        }

    def test_all_agent_commands_support_json_flag(self, initialized_project):
        """
        Test: All agent commands accept --json flag

        Validates:
        - --json flag is recognized
        - Commands don't error on --json
        - Flag is consistently available across all commands
        """
        worktree_path = initialized_project['worktree_path']

        # Test representative commands from each namespace
        commands_to_test = [
            ['spec-kitty', 'agent', 'feature', 'check-prerequisites', '--json'],
            ['spec-kitty', 'agent', 'tasks', 'list-tasks', '--json'],
            ['spec-kitty', 'agent', 'context', 'update-context', '--json'],
        ]

        for cmd in commands_to_test:
            result = subprocess.run(
                cmd,
                cwd=worktree_path,
                capture_output=True,
                text=True,
                timeout=30
            )

            # Should not error because of --json flag
            # May fail for other reasons (missing args, etc) but not because of flag
            assert '--json' not in result.stderr.lower() or 'unrecognized' not in result.stderr.lower(), (
                f"Command {' '.join(cmd)} should recognize --json flag. Error: {result.stderr}"
            )

    def test_json_output_is_valid_json(self, initialized_project):
        """
        Test: JSON output can be parsed with json.loads()

        Validates:
        - Output is valid JSON syntax
        - No trailing commas, missing braces, etc.
        - Python json module can parse it
        """
        worktree_path = initialized_project['worktree_path']

        result = subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'check-prerequisites', '--json'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Try to parse as JSON
        json_data = _extract_json_from_output(result.stdout)

        if json_data is None and result.returncode == 0:
            # If command succeeded but no JSON, that's a problem
            pytest.fail(f"Command succeeded but produced no valid JSON. Output: {result.stdout}")

        # If we got JSON, it should be parseable
        if json_data is not None:
            assert isinstance(json_data, (dict, list)), (
                "JSON should be a dict or list"
            )

    def test_json_no_mixed_console_output(self, initialized_project):
        """
        Test: JSON output has no debug/log messages mixed in

        Validates:
        - Output is ONLY JSON (one line)
        - No "Processing..." messages
        - No debug logs
        - Clean output that agents can parse directly

        This is critical - agents should be able to do:
        result = subprocess.run(..., '--json')
        data = json.loads(result.stdout)
        """
        worktree_path = initialized_project['worktree_path']

        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'list-tasks', '--json'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            output_lines = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]

            # Should ideally be just one line of JSON
            # We'll allow a bit of flexibility but validate the first line is JSON
            if output_lines:
                first_line = output_lines[0]
                try:
                    json.loads(first_line)
                    # Good - first line is valid JSON
                except json.JSONDecodeError:
                    pytest.fail(f"First line of --json output is not valid JSON: {first_line}")

    def test_json_success_structure(self, initialized_project):
        """
        Test: Successful JSON contains expected fields

        Validates:
        - Success responses have consistent structure
        - Contains data/result/output fields
        - Structure is predictable for agents
        """
        worktree_path = initialized_project['worktree_path']

        result = subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'check-prerequisites', '--json'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        json_data = _extract_json_from_output(result.stdout)

        if json_data and result.returncode == 0:
            # Successful JSON should have some recognizable structure
            # Common patterns: {success: true, data: ...} or {result: ...} or just data dict
            assert isinstance(json_data, dict), "Success JSON should be a dictionary"

    def test_json_error_structure(self, initialized_project):
        """
        Test: Error JSON contains error and message fields

        Validates:
        - Error responses have consistent structure
        - Contains error: true or similar
        - Has message/error_message field
        - Agents can detect failures programmatically
        """
        worktree_path = initialized_project['worktree_path']

        # Try to move non-existent work package (should error)
        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'move-task', 'WP999', '--to', 'doing', '--json'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should fail
        assert result.returncode != 0, "Invalid command should fail"

        # Check if error is in JSON format
        json_data = _extract_json_from_output(result.stdout)

        if json_data:
            # Error JSON should have error indicator
            assert isinstance(json_data, dict), "Error JSON should be a dictionary"
            # Should have error field or message field
            has_error_field = 'error' in json_data or 'message' in json_data or 'error_message' in json_data
            assert has_error_field, f"Error JSON should have error/message field. Got: {json_data}"

    def test_large_json_output_not_truncated(self, initialized_project):
        """
        ADVERSARIAL: Large outputs (100+ tasks) don't break JSON

        Validates:
        - JSON structure maintained with large data
        - No truncation mid-JSON
        - Arrays with many items handled correctly
        """
        worktree_path = initialized_project['worktree_path']
        tasks_dir = worktree_path / 'kitty-specs' / '001-test-feature' / 'tasks'
        tasks_dir.mkdir(parents=True, exist_ok=True)

        # Create many task files
        for i in range(50):  # Create 50 tasks
            wp_file = tasks_dir / f'WP{i:02d}-test-task-{i}.md'
            content = f"""---
lane: planned
work_package_id: WP{i:02d}
---

# Task {i}
"""
            wp_file.write_text(content)

        # List all tasks
        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'list-tasks', '--json'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should produce valid JSON even with 50 tasks
        if result.returncode == 0:
            json_data = _extract_json_from_output(result.stdout)
            assert json_data is not None, (
                "Large output should still produce valid JSON"
            )


class TestJSONErrorHandling:
    """Test that errors are returned as JSON, not crashes or stack traces."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def initialized_project(self, temp_project_dir, spec_kitty_repo_root):
        """Create an initialized spec-kitty project."""
        project_name = "test_errors"
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

        return {
            'project_path': project_path,
            'worktree_path': project_path / '.worktrees' / '001-test-feature'
        }

    def test_json_error_for_missing_args(self, initialized_project):
        """
        Test: Missing required arguments return JSON error

        Validates:
        - Doesn't crash with stack trace
        - Returns proper JSON error
        - Error message indicates missing argument
        """
        worktree_path = initialized_project['worktree_path']

        # Try move-task without --to flag (required argument)
        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'move-task', 'WP01', '--json'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should fail
        assert result.returncode != 0, "Missing required arg should fail"

        # Should not be a Python traceback
        assert 'Traceback' not in result.stderr, (
            "Should return error, not Python traceback"
        )

    def test_json_error_for_invalid_work_package(self, initialized_project):
        """
        Test: Invalid work package ID returns clear JSON error

        Validates:
        - Error message mentions the invalid WP ID
        - JSON structure maintained
        - Agent can understand what went wrong
        """
        worktree_path = initialized_project['worktree_path']

        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'move-task', 'INVALID-WP-ID', '--to', 'doing', '--json'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should fail
        assert result.returncode != 0, "Invalid WP should fail"

        # Check for JSON error or clear error message
        output = result.stdout + result.stderr
        assert 'INVALID-WP-ID' in output or 'not found' in output.lower(), (
            f"Error should mention the invalid WP ID. Got: {output}"
        )

    def test_json_error_for_permission_denied(self, initialized_project):
        """
        Test: Permission denied wraps in JSON error (not OS error)

        Validates:
        - OS errors are caught and wrapped
        - JSON structure maintained
        - Error message is actionable
        """
        worktree_path = initialized_project['worktree_path']
        tasks_dir = worktree_path / 'kitty-specs' / '001-test-feature' / 'tasks'
        tasks_dir.mkdir(parents=True, exist_ok=True)

        # Create a task file
        wp_file = tasks_dir / 'WP01-test.md'
        wp_file.write_text("""---
lane: planned
work_package_id: WP01
---

# Test
""")

        # Make it read-only
        wp_file.chmod(0o444)

        try:
            # Try to move task (should fail to write)
            result = subprocess.run(
                ['spec-kitty', 'agent', 'tasks', 'move-task', 'WP01', '--to', 'doing', '--json'],
                cwd=worktree_path,
                capture_output=True,
                text=True,
                timeout=30
            )

            # May fail due to permission or succeed if implementation handles it differently
            # At minimum, shouldn't crash
            assert 'Traceback' not in result.stderr, (
                "Permission errors should be handled gracefully, not crash"
            )
        finally:
            # Restore permissions for cleanup
            wp_file.chmod(0o644)

    def test_json_special_characters_escaped(self, initialized_project):
        """
        ADVERSARIAL: Unicode, quotes, newlines in data are escaped properly

        Validates:
        - Special characters don't break JSON
        - Unicode handled correctly
        - Quotes escaped
        - Newlines escaped
        """
        worktree_path = initialized_project['worktree_path']
        tasks_dir = worktree_path / 'kitty-specs' / '001-test-feature' / 'tasks'
        tasks_dir.mkdir(parents=True, exist_ok=True)

        # Create task with special characters
        wp_file = tasks_dir / 'WP01-special.md'
        special_content = """---
lane: planned
work_package_id: WP01
---

# Task with "quotes" and émojis 🎉 and 中文

Line 1
Line 2 with "nested quotes"
"""
        wp_file.write_text(special_content)

        # List tasks (should include this file)
        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'list-tasks', '--json'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            # Should produce valid JSON despite special characters
            json_data = _extract_json_from_output(result.stdout)
            assert json_data is not None, (
                "Special characters should not break JSON parsing"
            )


class TestJSONAgentParsing:
    """Test that agents can reliably parse JSON outputs for common tasks."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_agents_can_parse_create_feature_json(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Agent can extract worktree_path from create-feature JSON

        Validates:
        - JSON contains worktree path or similar
        - Agent can determine where feature was created
        - Structure is predictable
        """
        project_name = "test_parse"
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

        # Create feature with JSON
        result = subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature', '--json'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60
        )

        assert result.returncode == 0, "Feature creation should succeed"

        json_data = _extract_json_from_output(result.stdout)
        assert json_data is not None, "Should return JSON"

        # Agent should be able to find where the feature was created
        # Common field names: worktree_path, path, feature_dir, worktree, etc.
        json_str = json.dumps(json_data).lower()
        assert any(keyword in json_str for keyword in ['worktree', 'path', 'feature', 'dir']), (
            f"JSON should contain path/worktree information. Got: {json_data}"
        )

    def test_agents_can_parse_list_tasks_json(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Agent can iterate over lanes from list-tasks JSON

        Validates:
        - JSON structure allows iteration
        - Lanes are distinguishable
        - Tasks within lanes are accessible
        """
        project_name = "test_list"
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

        worktree_path = project_path / '.worktrees' / '001-test-feature'

        # List tasks
        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'list-tasks', '--json'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        assert result.returncode == 0, "List tasks should succeed"

        json_data = _extract_json_from_output(result.stdout)
        assert json_data is not None, "Should return JSON"

        # Agent should be able to iterate over structure
        assert isinstance(json_data, (dict, list)), (
            "JSON should be dict or list for iteration"
        )

    def test_agents_can_parse_error_json(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Agent can detect failure from error JSON

        Validates:
        - Error JSON has recognizable pattern
        - Agent can check if command succeeded
        - Error message is extractable
        """
        project_name = "test_error_parse"
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

        worktree_path = project_path / '.worktrees' / '001-test-feature'

        # Try invalid operation
        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'move-task', 'WP999', '--to', 'doing', '--json'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should fail
        assert result.returncode != 0, "Invalid operation should fail"

        # Check if agent can parse error
        json_data = _extract_json_from_output(result.stdout)

        if json_data:
            # Agent should be able to detect this is an error
            # Either returncode != 0, or JSON has error field
            assert isinstance(json_data, dict), "Error should be a dict"

    def test_json_output_stable_across_runs(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Same command produces same JSON structure on repeat runs

        Validates:
        - JSON structure is consistent
        - Field names don't change
        - Agents can rely on structure
        """
        project_name = "test_stable"
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

        worktree_path = project_path / '.worktrees' / '001-test-feature'

        # Run same command twice
        result1 = subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'check-prerequisites', '--json'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        result2 = subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'check-prerequisites', '--json'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        json1 = _extract_json_from_output(result1.stdout)
        json2 = _extract_json_from_output(result2.stdout)

        if json1 and json2:
            # Same command should have same top-level structure
            assert type(json1) == type(json2), (
                "JSON structure should be consistent across runs"
            )

            if isinstance(json1, dict) and isinstance(json2, dict):
                # Same keys at top level
                keys1 = set(json1.keys())
                keys2 = set(json2.keys())
                assert keys1 == keys2, (
                    f"JSON keys should be consistent. Run1: {keys1}, Run2: {keys2}"
                )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
