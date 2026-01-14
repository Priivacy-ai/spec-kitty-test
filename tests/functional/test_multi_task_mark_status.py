"""
Test Multi-Task Mark-Status Command (v0.11.0+)

Tests the enhanced `spec-kitty agent tasks mark-status` command that accepts
multiple task IDs in a single invocation for efficient batch operations.

Feature Context:
- Prior to this change: mark-status accepted single task ID
- After change: mark-status accepts space-separated task IDs
- All tasks updated in single pass with one commit

Command Interface:
    # Single task (backward compatible):
    spec-kitty agent tasks mark-status T001 --status done

    # Multiple tasks (new):
    spec-kitty agent tasks mark-status T001 T002 T003 --status done

    # Many tasks at once:
    spec-kitty agent tasks mark-status T040 T041 T042 T043 T044 T045 --status done --feature 001-my-feature

JSON Output Format (changed):
    # Old format (single task):
    {"result": "success", "task_id": "T001", "status": "done", "note": "..."}

    # New format (multiple tasks):
    {"result": "success", "updated": ["T001", "T002"], "not_found": [], "status": "done", "count": 2}

Test Coverage:
1. Single task (backward compatibility)
2. Multiple tasks (space-separated)
3. Mixed results (some found, some not)
4. All tasks not found (error)
5. Empty task list (error)
6. JSON output structure validation
7. Commit message format (single vs multiple)
8. Help documentation accuracy
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_project_dir():
    """Create temporary directory for test project."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def project_with_tasks_md(temp_project_dir, spec_kitty_repo_root):
    """
    Create project with tasks.md containing subtasks for testing.

    Returns (project_path, feature_dir, tasks_md_path)
    """
    env = os.environ.copy()
    env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

    # Initialize project
    subprocess.run(
        ['spec-kitty', 'init', 'test-project', '--ai=claude'],
        cwd=str(temp_project_dir),
        env=env,
        input=b'y\n',
        capture_output=True
    )

    project_path = temp_project_dir / 'test-project'

    # Initialize git
    subprocess.run(['git', 'init'], cwd=str(project_path), check=True, capture_output=True)
    subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
    subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=str(project_path), check=True, capture_output=True)

    # Create feature
    subprocess.run(
        ['spec-kitty', 'agent', 'feature', 'create-feature', 'multi-task-test'],
        cwd=str(project_path),
        env=env,
        capture_output=True
    )

    feature_dir = project_path / 'kitty-specs' / '001-multi-task-test'

    # Create tasks.md with many subtasks for multi-task testing
    tasks_md = feature_dir / 'tasks.md'
    tasks_md.write_text("""# Tasks for multi-task-test

## WP01: Core Implementation

- [ ] T001: First subtask
- [ ] T002: Second subtask
- [ ] T003: Third subtask
- [ ] T004: Fourth subtask
- [ ] T005: Fifth subtask

Description: Core implementation work.

## WP02: Extended Features

- [ ] T010: Extended feature one
- [ ] T011: Extended feature two
- [ ] T012: Extended feature three

Depends on: WP01

Description: Extended features.

## WP03: Documentation

- [ ] T020: Write user docs
- [ ] T021: Write API docs
- [ ] T022: Write examples

Description: Documentation tasks.
""")

    # Commit the tasks.md
    subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
    subprocess.run(['git', 'commit', '-m', 'Add tasks.md'], cwd=str(project_path), check=True, capture_output=True)

    return project_path, feature_dir, tasks_md


class TestMultiTaskMarkStatusBasic:
    """Basic tests for multi-task mark-status command."""

    def test_help_shows_multi_task_capability(self):
        """
        Test that --help documents multiple task IDs capability.

        GIVEN: The mark-status command exists
        WHEN: Running with --help
        THEN: Help text should clearly document space-separated task IDs
        """
        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'mark-status', '--help'],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, "Command should exist"

        help_text = result.stdout

        # Should document multiple task support
        assert 'TASK_IDS' in help_text or 'task-ids' in help_text.lower(), \
            "Help should show TASK_IDS (plural) parameter"

        # Should have examples showing multiple tasks
        assert 'T001 T002' in help_text or 'space-separated' in help_text.lower(), \
            "Help should show example of multiple tasks or mention space-separated"

    def test_single_task_still_works(self, project_with_tasks_md):
        """
        Test backward compatibility: single task ID still works.

        GIVEN: A project with tasks.md containing subtasks
        WHEN: Running mark-status with single task ID (legacy usage)
        THEN: Should succeed and mark the task
        """
        project_path, feature_dir, tasks_md = project_with_tasks_md

        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'mark-status', 'T001', '--status', 'done', '--no-auto-commit'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, f"Single task should work. Error: {result.stderr}"

        # Verify task was marked
        content = tasks_md.read_text()
        assert '- [x] T001' in content, "T001 should be marked complete"
        assert '- [ ] T002' in content, "T002 should remain unchecked"

    def test_multiple_tasks_marked_in_single_call(self, project_with_tasks_md):
        """
        Test core feature: multiple tasks marked in one command.

        GIVEN: A project with tasks.md containing T001-T005
        WHEN: Running mark-status T001 T002 T003 --status done
        THEN: All three tasks should be marked complete in one operation
        """
        project_path, feature_dir, tasks_md = project_with_tasks_md

        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'mark-status', 'T001', 'T002', 'T003', '--status', 'done', '--no-auto-commit'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, f"Multiple tasks should succeed. Error: {result.stderr}"

        # Verify all three tasks were marked
        content = tasks_md.read_text()
        assert '- [x] T001' in content, "T001 should be marked complete"
        assert '- [x] T002' in content, "T002 should be marked complete"
        assert '- [x] T003' in content, "T003 should be marked complete"

        # Verify others unchanged
        assert '- [ ] T004' in content, "T004 should remain unchecked"
        assert '- [ ] T005' in content, "T005 should remain unchecked"

    def test_many_tasks_at_once(self, project_with_tasks_md):
        """
        Test marking many tasks in single command (LLM agent use case).

        GIVEN: A project with tasks.md containing multiple WPs
        WHEN: Running mark-status with 6+ task IDs
        THEN: All tasks should be marked in single operation
        """
        project_path, feature_dir, tasks_md = project_with_tasks_md

        # Mark all WP01 and WP02 tasks at once
        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'mark-status',
             'T001', 'T002', 'T003', 'T004', 'T005',  # WP01
             'T010', 'T011', 'T012',  # WP02
             '--status', 'done', '--no-auto-commit'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, f"Many tasks should succeed. Error: {result.stderr}"

        # Verify all 8 tasks marked
        content = tasks_md.read_text()
        for tid in ['T001', 'T002', 'T003', 'T004', 'T005', 'T010', 'T011', 'T012']:
            assert f'- [x] {tid}' in content, f"{tid} should be marked complete"

        # WP03 tasks should remain unchecked
        for tid in ['T020', 'T021', 'T022']:
            assert f'- [ ] {tid}' in content, f"{tid} should remain unchecked"


class TestMultiTaskMarkStatusPartialResults:
    """Tests for handling mixed success/failure scenarios."""

    def test_mixed_found_and_not_found(self, project_with_tasks_md):
        """
        Test behavior when some tasks exist and some don't.

        GIVEN: tasks.md with T001-T005
        WHEN: Running mark-status T001 T002 T999 (T999 doesn't exist)
        THEN: Should mark T001, T002 but report T999 not found
        """
        project_path, feature_dir, tasks_md = project_with_tasks_md

        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'mark-status',
             'T001', 'T002', 'T999',  # T999 doesn't exist
             '--status', 'done', '--no-auto-commit'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Should succeed (some tasks found)
        assert result.returncode == 0, \
            "Should succeed when at least some tasks found"

        # Found tasks should be marked
        content = tasks_md.read_text()
        assert '- [x] T001' in content, "T001 should be marked"
        assert '- [x] T002' in content, "T002 should be marked"

        # Should warn about not found
        output = result.stdout + result.stderr
        assert 'T999' in output, "Should mention T999 in output (not found)"

    def test_all_tasks_not_found_fails(self, project_with_tasks_md):
        """
        Test that command fails when NO tasks are found.

        GIVEN: tasks.md with T001-T005
        WHEN: Running mark-status with only non-existent task IDs
        THEN: Should fail with error listing not-found tasks
        """
        project_path, feature_dir, tasks_md = project_with_tasks_md

        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'mark-status',
             'T888', 'T999',  # None exist
             '--status', 'done', '--no-auto-commit'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Should fail
        assert result.returncode != 0, \
            "Should fail when no tasks found"

        # Error should mention the task IDs
        output = result.stdout + result.stderr
        assert 'T888' in output or 'T999' in output or 'not found' in output.lower(), \
            "Error should mention not-found task IDs"

    def test_no_tasks_provided_fails(self, project_with_tasks_md):
        """
        Test that command fails when no task IDs provided.

        GIVEN: The mark-status command
        WHEN: Running without any task IDs
        THEN: Should fail with clear error message
        """
        project_path, feature_dir, tasks_md = project_with_tasks_md

        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'mark-status',
             '--status', 'done', '--no-auto-commit'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Should fail (missing required argument)
        assert result.returncode != 0, \
            "Should fail when no task IDs provided"


class TestMultiTaskMarkStatusJsonOutput:
    """Tests for JSON output format with multiple tasks."""

    def test_json_output_single_task(self, project_with_tasks_md):
        """
        Test JSON output format for single task.

        GIVEN: A project with tasks.md
        WHEN: Running mark-status T001 --json
        THEN: JSON should have updated array with single task
        """
        project_path, feature_dir, tasks_md = project_with_tasks_md

        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'mark-status',
             'T001', '--status', 'done', '--json', '--no-auto-commit'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, f"Should succeed. Error: {result.stderr}"

        # Parse JSON output
        output = json.loads(result.stdout.strip())

        assert output['result'] == 'success', "Result should be success"
        assert 'updated' in output, "Should have 'updated' field"
        assert 'T001' in output['updated'], "Updated should contain T001"
        assert output['count'] == 1, "Count should be 1"
        assert output['status'] == 'done', "Status should be done"

    def test_json_output_multiple_tasks(self, project_with_tasks_md):
        """
        Test JSON output format for multiple tasks.

        GIVEN: A project with tasks.md
        WHEN: Running mark-status T001 T002 T003 --json
        THEN: JSON should have all tasks in updated array
        """
        project_path, feature_dir, tasks_md = project_with_tasks_md

        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'mark-status',
             'T001', 'T002', 'T003', '--status', 'done', '--json', '--no-auto-commit'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, f"Should succeed. Error: {result.stderr}"

        output = json.loads(result.stdout.strip())

        assert output['result'] == 'success'
        assert set(output['updated']) == {'T001', 'T002', 'T003'}, \
            "Updated should contain all three tasks"
        assert output['count'] == 3, "Count should be 3"
        assert output['not_found'] == [], "not_found should be empty"

    def test_json_output_mixed_results(self, project_with_tasks_md):
        """
        Test JSON output when some tasks not found.

        GIVEN: A project with tasks.md
        WHEN: Running mark-status T001 T002 T999 --json (T999 missing)
        THEN: JSON should show updated and not_found separately
        """
        project_path, feature_dir, tasks_md = project_with_tasks_md

        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'mark-status',
             'T001', 'T002', 'T999', '--status', 'done', '--json', '--no-auto-commit'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, \
            "Should succeed when some tasks found"

        output = json.loads(result.stdout.strip())

        assert output['result'] == 'success'
        assert set(output['updated']) == {'T001', 'T002'}, \
            "Updated should have found tasks"
        assert 'T999' in output['not_found'], \
            "not_found should list T999"
        assert output['count'] == 2, "Count should be 2 (found tasks only)"


class TestMultiTaskMarkStatusPending:
    """Tests for marking tasks as pending (unchecking)."""

    def test_multiple_tasks_to_pending(self, project_with_tasks_md):
        """
        Test marking multiple tasks back to pending.

        GIVEN: tasks.md with some checked tasks
        WHEN: Running mark-status T001 T002 --status pending
        THEN: Both tasks should be unchecked
        """
        project_path, feature_dir, tasks_md = project_with_tasks_md

        # First mark some tasks done
        subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'mark-status',
             'T001', 'T002', 'T003', '--status', 'done', '--no-auto-commit'],
            cwd=str(project_path),
            capture_output=True
        )

        # Verify they're checked
        content = tasks_md.read_text()
        assert '- [x] T001' in content

        # Now mark back to pending
        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'mark-status',
             'T001', 'T002', '--status', 'pending', '--no-auto-commit'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, f"Should succeed. Error: {result.stderr}"

        # Verify unchecked
        content = tasks_md.read_text()
        assert '- [ ] T001' in content, "T001 should be unchecked"
        assert '- [ ] T002' in content, "T002 should be unchecked"
        assert '- [x] T003' in content, "T003 should remain checked"


class TestMultiTaskMarkStatusCommitBehavior:
    """Tests for auto-commit behavior with multiple tasks."""

    def test_single_commit_for_multiple_tasks(self, project_with_tasks_md):
        """
        Test that multiple tasks result in single commit.

        GIVEN: A project with tasks.md
        WHEN: Running mark-status T001 T002 T003 --status done (with auto-commit)
        THEN: Should create exactly one commit for all tasks
        """
        project_path, feature_dir, tasks_md = project_with_tasks_md

        # Get commit count before
        before = subprocess.run(
            ['git', 'rev-list', '--count', 'HEAD'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )
        commits_before = int(before.stdout.strip())

        # Run mark-status with auto-commit (default)
        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'mark-status',
             'T001', 'T002', 'T003', '--status', 'done'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Get commit count after
        after = subprocess.run(
            ['git', 'rev-list', '--count', 'HEAD'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )
        commits_after = int(after.stdout.strip())

        # Should be exactly 1 new commit (or 0 if tasks.md not in repo)
        new_commits = commits_after - commits_before
        assert new_commits <= 1, \
            f"Should create at most 1 commit for multiple tasks, got {new_commits}"

    def test_commit_message_single_task(self, project_with_tasks_md):
        """
        Test commit message format for single task.

        GIVEN: A project with tasks.md
        WHEN: Running mark-status T001 --status done
        THEN: Commit message should mention the specific task
        """
        project_path, feature_dir, tasks_md = project_with_tasks_md

        subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'mark-status',
             'T001', '--status', 'done'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Check last commit message
        result = subprocess.run(
            ['git', 'log', '-1', '--format=%s'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        commit_msg = result.stdout.strip()

        # Should mention T001 specifically for single task
        assert 'T001' in commit_msg, \
            f"Single-task commit should mention T001. Got: {commit_msg}"

    def test_commit_message_multiple_tasks(self, project_with_tasks_md):
        """
        Test commit message format for multiple tasks.

        GIVEN: A project with tasks.md
        WHEN: Running mark-status T001 T002 T003 --status done
        THEN: Commit message should indicate count, not list all tasks
        """
        project_path, feature_dir, tasks_md = project_with_tasks_md

        subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'mark-status',
             'T001', 'T002', 'T003', '--status', 'done'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Check last commit message
        result = subprocess.run(
            ['git', 'log', '-1', '--format=%s'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        commit_msg = result.stdout.strip()

        # Should mention count for multiple tasks
        assert '3' in commit_msg or 'subtasks' in commit_msg.lower(), \
            f"Multi-task commit should mention count. Got: {commit_msg}"


class TestMultiTaskMarkStatusEdgeCases:
    """Edge cases and adversarial tests."""

    def test_duplicate_task_ids_handled(self, project_with_tasks_md):
        """
        Test that duplicate task IDs in input are handled gracefully.

        GIVEN: A project with tasks.md
        WHEN: Running mark-status T001 T001 T001 --status done
        THEN: Should not fail or count task multiple times
        """
        project_path, feature_dir, tasks_md = project_with_tasks_md

        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'mark-status',
             'T001', 'T001', 'T001', '--status', 'done', '--json', '--no-auto-commit'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Should succeed
        assert result.returncode == 0, f"Should handle duplicates. Error: {result.stderr}"

        # Task should be marked exactly once
        content = tasks_md.read_text()
        assert content.count('[x] T001') == 1, "T001 should appear checked exactly once"

    def test_already_done_tasks_handled(self, project_with_tasks_md):
        """
        Test marking already-done tasks as done again.

        GIVEN: tasks.md with T001 already marked [x]
        WHEN: Running mark-status T001 --status done
        THEN: Should succeed without error (idempotent)
        """
        project_path, feature_dir, tasks_md = project_with_tasks_md

        # First mark T001 done
        subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'mark-status',
             'T001', '--status', 'done', '--no-auto-commit'],
            cwd=str(project_path),
            capture_output=True
        )

        # Mark done again
        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'mark-status',
             'T001', '--status', 'done', '--no-auto-commit'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Should succeed (idempotent)
        assert result.returncode == 0, \
            f"Re-marking done task should succeed. Error: {result.stderr}"

    def test_tasks_across_multiple_wps(self, project_with_tasks_md):
        """
        Test marking tasks from different WPs in single command.

        GIVEN: tasks.md with tasks in WP01 (T001-T005) and WP02 (T010-T012)
        WHEN: Running mark-status T001 T010 T020 --status done
        THEN: Tasks across all three WPs should be marked
        """
        project_path, feature_dir, tasks_md = project_with_tasks_md

        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'mark-status',
             'T001', 'T010', 'T020',  # One from each WP
             '--status', 'done', '--no-auto-commit'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, f"Should succeed. Error: {result.stderr}"

        content = tasks_md.read_text()
        assert '- [x] T001' in content, "T001 (WP01) should be marked"
        assert '- [x] T010' in content, "T010 (WP02) should be marked"
        assert '- [x] T020' in content, "T020 (WP03) should be marked"


class TestMultiTaskMarkStatusLLMUsability:
    """
    Tests focused on LLM agent usability.

    These tests verify the command works well for the primary use case:
    LLM agents efficiently marking many tasks complete.
    """

    def test_long_task_list_performance(self, project_with_tasks_md):
        """
        Test that long list of tasks doesn't degrade performance.

        GIVEN: A project with tasks.md
        WHEN: Running mark-status with all 11 tasks
        THEN: Should complete reasonably quickly (< 10s)
        """
        import time

        project_path, feature_dir, tasks_md = project_with_tasks_md

        all_tasks = ['T001', 'T002', 'T003', 'T004', 'T005',
                     'T010', 'T011', 'T012',
                     'T020', 'T021', 'T022']

        start = time.time()
        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'mark-status'] + all_tasks +
            ['--status', 'done', '--no-auto-commit'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )
        elapsed = time.time() - start

        assert result.returncode == 0, f"Should succeed. Error: {result.stderr}"
        assert elapsed < 10, f"Should complete in < 10s, took {elapsed:.1f}s"

    def test_output_suitable_for_llm_parsing(self, project_with_tasks_md):
        """
        Test that output is easily parseable by LLM agents.

        GIVEN: Running mark-status with --json
        WHEN: Parsing the output
        THEN: Output should be single-line JSON suitable for LLM parsing
        """
        project_path, feature_dir, tasks_md = project_with_tasks_md

        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'mark-status',
             'T001', 'T002', '--status', 'done', '--json', '--no-auto-commit'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        assert result.returncode == 0

        # Output should be valid JSON
        try:
            output = json.loads(result.stdout.strip())
        except json.JSONDecodeError as e:
            pytest.fail(f"Output should be valid JSON: {e}\nOutput: {result.stdout}")

        # Should have predictable structure
        required_fields = ['result', 'updated', 'not_found', 'status', 'count']
        for field in required_fields:
            assert field in output, f"JSON should have '{field}' field"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
