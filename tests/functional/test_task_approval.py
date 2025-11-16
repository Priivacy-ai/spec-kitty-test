"""
Task Approval System Tests

Tests the dedicated task approval command (commit 0f3a16b) that ensures
proper reviewer attribution in frontmatter and activity logs.

Background:
----------
When reviewers approve tasks, the system must record WHO approved the task,
not just that the task was approved. Previously, using the generic `move`
command would inherit the implementer's identity from frontmatter, creating
false audit trails.

The Problem (Before Fix):
------------------------
Agent A implements task → frontmatter: agent=A, shell_pid=12345
Agent B reviews and approves using move command
Result: frontmatter: agent=A, shell_pid=12345 (still implementer!)
Activity log shows implementer approved their own work (impossible to trace reviewer)

The Solution (With approve command):
------------------------------------
Agent A implements task → frontmatter: agent=A, shell_pid=12345
Agent B reviews and approves using approve command
Result: frontmatter: agent=B, shell_pid=88888, review_status="approved", reviewed_by=B
Activity log shows both implementer AND reviewer entries

Test Coverage:
-------------
1. Basic Approval Flow (4 tests)
   - Task moves from for_review → done
   - Reviewer attribution in frontmatter
   - review_status and reviewed_by fields set
   - Activity log includes reviewer entry

2. Validation (3 tests)
   - Task must be in for_review lane
   - Invalid target lanes rejected
   - Work package must exist

3. Reviewer Identity (3 tests)
   - Reviewer agent ID recorded (not implementer's)
   - Reviewer shell PID recorded (not implementer's)
   - Original implementer preserved in activity log

4. Custom Options (3 tests)
   - Custom review status messages
   - Custom target lanes
   - Custom notes in activity log

5. Dry-run Mode (2 tests)
   - Shows plan without modifying files
   - No git operations performed

6. Git Operations (2 tests)
   - Source file removed (git rm)
   - Target file added (git add)
"""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def spec_kitty_repo_root():
    """Get spec-kitty repository root from environment or default location."""
    env_path = os.environ.get('SPEC_KITTY_REPO')
    if env_path:
        return Path(env_path)

    default_path = Path(__file__).parent.parent.parent.parent / 'spec-kitty'
    if default_path.exists():
        return default_path

    raise ValueError(
        "Could not find spec-kitty repository. "
        "Set SPEC_KITTY_REPO environment variable or ensure ../spec-kitty exists"
    )


def create_test_task_in_review(project_path: Path, feature: str, task_id: str) -> Path:
    """
    Create a test task in the for_review lane with implementer attribution.

    Returns path to the task file.
    """
    task_dir = project_path / "kitty-specs" / feature / "tasks" / "for_review"
    task_dir.mkdir(parents=True, exist_ok=True)

    task_file = task_dir / f"{task_id}.md"
    content = f"""---
lane: for_review
work_package_id: {task_id}
title: "Test Task for Review"
agent: implementer-agent
shell_pid: "12345"
assignee: "Original Developer"
---

# Test Task

This task is ready for review.

## Activity

- 2025-11-15T14:00:00Z – implementer-agent – shell_pid=12345 – lane=doing – Started work
- 2025-11-15T16:00:00Z – implementer-agent – shell_pid=12345 – lane=for_review – Completed
"""
    task_file.write_text(content, encoding="utf-8")
    return task_file


class TestBasicApprovalFlow:
    """Test basic task approval from for_review to done."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_approve_moves_task_to_done(self, temp_project_dir, spec_kitty_repo_root):
        """Test: approve command moves task from for_review → done"""
        project_name = 'approve_basic'
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Create project
        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Create feature with task in for_review
        feature = "001-test-feature"
        task_file = create_test_task_in_review(project_path, feature, "WP01")

        # Initialize git
        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=project_path, check=True)

        # Get tasks CLI script (approve command is in .kittify)
        tasks_cli = spec_kitty_repo_root / '.kittify' / 'scripts' / 'tasks' / 'tasks_cli.py'

        # Approve the task
        result = subprocess.run(
            [
                'python3', str(tasks_cli), 'approve', feature, 'WP01',
                '--reviewer-agent', 'claude-reviewer',
                '--reviewer-shell-pid', '88888',
                '--review-status', 'approved without changes'
            ],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        # Verify task moved to done
        done_task = project_path / "kitty-specs" / feature / "tasks" / "done" / "WP01.md"
        assert done_task.exists(), "Task should be in done lane"

        # Verify original file removed
        assert not task_file.exists(), "Original task file should be removed"

        # Verify output message
        output = result.stdout
        assert '✅ Approved WP01 → done' in output, "Should show success message"
        assert 'claude-reviewer' in output, "Should show reviewer agent"
        assert '88888' in output, "Should show reviewer shell PID"

    def test_approve_sets_reviewer_frontmatter(self, temp_project_dir, spec_kitty_repo_root):
        """Test: approve sets review_status and reviewed_by frontmatter fields"""
        project_name = 'approve_frontmatter'
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

        feature = "001-frontmatter-test"
        create_test_task_in_review(project_path, feature, "WP02")

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=project_path, check=True)

        tasks_cli = spec_kitty_repo_root / '.kittify' / 'scripts' / 'tasks' / 'tasks_cli.py'

        subprocess.run(
            [
                'python3', str(tasks_cli), 'approve', feature, 'WP02',
                '--reviewer-agent', 'gemini-reviewer',
                '--reviewer-shell-pid', '99999',
                '--review-status', 'approved with minor comments'
            ],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        # Read approved task
        done_task = project_path / "kitty-specs" / feature / "tasks" / "done" / "WP02.md"
        content = done_task.read_text(encoding="utf-8")

        # Verify review-specific fields (YAML may use quotes)
        assert ('review_status: approved with minor comments' in content or
                'review_status: "approved with minor comments"' in content), \
            "Should set review_status field"
        assert ('reviewed_by: gemini-reviewer' in content or
                'reviewed_by: "gemini-reviewer"' in content), \
            "Should set reviewed_by field"

    def test_approve_updates_agent_to_reviewer(self, temp_project_dir, spec_kitty_repo_root):
        """Test: approve updates agent field to reviewer (not implementer)"""
        project_name = 'approve_agent_update'
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

        feature = "001-agent-update-test"
        create_test_task_in_review(project_path, feature, "WP03")

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=project_path, check=True)

        tasks_cli = spec_kitty_repo_root / '.kittify' / 'scripts' / 'tasks' / 'tasks_cli.py'

        subprocess.run(
            [
                'python3', str(tasks_cli), 'approve', feature, 'WP03',
                '--reviewer-agent', 'cursor-reviewer',
                '--reviewer-shell-pid', '77777'
            ],
            cwd=project_path,
            check=True
        )

        done_task = project_path / "kitty-specs" / feature / "tasks" / "done" / "WP03.md"
        content = done_task.read_text(encoding="utf-8")

        # Verify agent updated to reviewer (YAML may use quotes)
        assert ('agent: cursor-reviewer' in content or
                'agent: "cursor-reviewer"' in content), \
            "Agent should be updated to reviewer (not implementer)"
        assert 'shell_pid: "77777"' in content or 'shell_pid: 77777' in content, \
            "Shell PID should be updated to reviewer's PID"

    def test_approve_adds_reviewer_activity_log(self, temp_project_dir, spec_kitty_repo_root):
        """Test: approve adds activity log entry with reviewer's info"""
        project_name = 'approve_activity_log'
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

        feature = "001-activity-log-test"
        create_test_task_in_review(project_path, feature, "WP04")

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=project_path, check=True)

        tasks_cli = spec_kitty_repo_root / '.kittify' / 'scripts' / 'tasks' / 'tasks_cli.py'

        subprocess.run(
            [
                'python3', str(tasks_cli), 'approve', feature, 'WP04',
                '--reviewer-agent', 'windsurf-reviewer',
                '--reviewer-shell-pid', '66666',
                '--review-status', 'approved'
            ],
            cwd=project_path,
            check=True
        )

        done_task = project_path / "kitty-specs" / feature / "tasks" / "done" / "WP04.md"
        content = done_task.read_text(encoding="utf-8")

        # Verify activity log has reviewer entry
        assert 'windsurf-reviewer' in content, "Activity log should mention reviewer"
        assert 'shell_pid=66666' in content, "Activity log should have reviewer's shell PID"
        assert 'lane=done' in content, "Activity log should show done lane"

        # Verify original implementer entries are preserved
        assert 'implementer-agent' in content, "Original implementer entries should be preserved"
        assert 'shell_pid=12345' in content, "Original shell PID should be preserved"


class TestApprovalValidation:
    """Test validation rules for task approval."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_approve_requires_for_review_lane(self, temp_project_dir, spec_kitty_repo_root):
        """Test: approve rejects tasks not in for_review lane"""
        project_name = 'approve_validation_lane'
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

        feature = "001-validation-test"

        # Create task in 'doing' lane (not for_review)
        task_dir = project_path / "kitty-specs" / feature / "tasks" / "doing"
        task_dir.mkdir(parents=True, exist_ok=True)

        task_file = task_dir / "WP05.md"
        task_file.write_text("""---
lane: doing
work_package_id: WP05
agent: implementer-agent
---

# Task still in progress
""", encoding="utf-8")

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=project_path, check=True)

        tasks_cli = spec_kitty_repo_root / '.kittify' / 'scripts' / 'tasks' / 'tasks_cli.py'

        # Try to approve task in wrong lane
        result = subprocess.run(
            [
                'python3', str(tasks_cli), 'approve', feature, 'WP05',
                '--reviewer-agent', 'reviewer'
            ],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        # Should fail
        assert result.returncode != 0, "Should reject task not in for_review lane"
        assert "must be in 'for_review' lane" in result.stderr, \
            "Error message should explain lane requirement"
        assert "doing" in result.stderr, "Error should show current lane"

    def test_approve_rejects_invalid_target_lane(self, temp_project_dir, spec_kitty_repo_root):
        """Test: approve rejects invalid target lanes"""
        project_name = 'approve_invalid_target'
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

        feature = "001-invalid-target-test"
        create_test_task_in_review(project_path, feature, "WP06")

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=project_path, check=True)

        tasks_cli = spec_kitty_repo_root / '.kittify' / 'scripts' / 'tasks' / 'tasks_cli.py'

        # Try to approve to invalid lane
        result = subprocess.run(
            [
                'python3', str(tasks_cli), 'approve', feature, 'WP06',
                '--target-lane', 'invalid_lane',
                '--reviewer-agent', 'reviewer'
            ],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        # Should fail
        assert result.returncode != 0, "Should reject invalid target lane"
        assert "Invalid target lane" in result.stderr or "invalid_lane" in result.stderr, \
            "Error should mention invalid lane"

    def test_approve_handles_missing_work_package(self, temp_project_dir, spec_kitty_repo_root):
        """Test: approve gives clear error for non-existent work package"""
        project_name = 'approve_missing_wp'
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

        feature = "001-missing-wp-test"

        # Create tasks directory structure but with no WP99
        task_dir = project_path / "kitty-specs" / feature / "tasks" / "for_review"
        task_dir.mkdir(parents=True, exist_ok=True)

        # Create a different task (WP01) so directory exists
        dummy_task = task_dir / "WP01.md"
        dummy_task.write_text("""---
lane: for_review
work_package_id: WP01
---
# Dummy task
""", encoding="utf-8")

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=project_path, check=True)

        tasks_cli = spec_kitty_repo_root / '.kittify' / 'scripts' / 'tasks' / 'tasks_cli.py'

        # Try to approve non-existent work package
        result = subprocess.run(
            [
                'python3', str(tasks_cli), 'approve', feature, 'WP99',
                '--reviewer-agent', 'reviewer'
            ],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        # Should fail with clear error
        assert result.returncode != 0, "Should fail for non-existent work package"
        output = result.stdout + result.stderr
        assert 'WP99' in output or 'not found' in output.lower() or 'No match' in output or 'no tasks directory' in output.lower(), \
            f"Error should mention the missing work package or directory. Got: {output}"


class TestReviewerIdentityPreservation:
    """Test that reviewer identity is properly preserved (not implementer's)."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_reviewer_agent_recorded_not_implementer(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Reviewer's agent ID is recorded, not implementer's"""
        project_name = 'reviewer_identity'
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

        feature = "001-identity-test"
        create_test_task_in_review(project_path, feature, "WP07")

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=project_path, check=True)

        tasks_cli = spec_kitty_repo_root / '.kittify' / 'scripts' / 'tasks' / 'tasks_cli.py'

        subprocess.run(
            [
                'python3', str(tasks_cli), 'approve', feature, 'WP07',
                '--reviewer-agent', 'DIFFERENT-REVIEWER',
                '--reviewer-shell-pid', '55555'
            ],
            cwd=project_path,
            check=True
        )

        done_task = project_path / "kitty-specs" / feature / "tasks" / "done" / "WP07.md"
        content = done_task.read_text(encoding="utf-8")

        # Verify reviewer's identity is recorded (YAML may use quotes)
        assert ('agent: DIFFERENT-REVIEWER' in content or
                'agent: "DIFFERENT-REVIEWER"' in content), \
            "Agent should be reviewer (not implementer-agent)"
        assert ('reviewed_by: DIFFERENT-REVIEWER' in content or
                'reviewed_by: "DIFFERENT-REVIEWER"' in content), \
            "reviewed_by should be set to reviewer"

    def test_reviewer_shell_pid_recorded_not_implementer(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Reviewer's shell PID is recorded, not implementer's"""
        project_name = 'reviewer_pid'
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

        feature = "001-pid-test"
        create_test_task_in_review(project_path, feature, "WP08")

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=project_path, check=True)

        tasks_cli = spec_kitty_repo_root / '.kittify' / 'scripts' / 'tasks' / 'tasks_cli.py'

        subprocess.run(
            [
                'python3', str(tasks_cli), 'approve', feature, 'WP08',
                '--reviewer-agent', 'reviewer',
                '--reviewer-shell-pid', '44444'
            ],
            cwd=project_path,
            check=True
        )

        done_task = project_path / "kitty-specs" / feature / "tasks" / "done" / "WP08.md"
        content = done_task.read_text(encoding="utf-8")

        # Verify reviewer's shell PID is recorded (not implementer's 12345)
        assert 'shell_pid: "44444"' in content or 'shell_pid: 44444' in content, \
            "Shell PID should be reviewer's (44444), not implementer's (12345)"

    def test_implementer_preserved_in_activity_log(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Original implementer entries are preserved in activity log"""
        project_name = 'implementer_preserved'
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

        feature = "001-preserve-test"
        create_test_task_in_review(project_path, feature, "WP09")

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=project_path, check=True)

        tasks_cli = spec_kitty_repo_root / '.kittify' / 'scripts' / 'tasks' / 'tasks_cli.py'

        subprocess.run(
            [
                'python3', str(tasks_cli), 'approve', feature, 'WP09',
                '--reviewer-agent', 'reviewer-B',
                '--reviewer-shell-pid', '99999'
            ],
            cwd=project_path,
            check=True
        )

        done_task = project_path / "kitty-specs" / feature / "tasks" / "done" / "WP09.md"
        content = done_task.read_text(encoding="utf-8")

        # Verify BOTH implementer and reviewer in activity log
        assert 'implementer-agent' in content, \
            "Implementer should still be in activity log"
        assert 'shell_pid=12345' in content, \
            "Implementer's shell PID should be preserved"
        assert 'reviewer-B' in content, \
            "Reviewer should be added to activity log"
        assert 'shell_pid=99999' in content, \
            "Reviewer's shell PID should be in activity log"


class TestCustomApprovalOptions:
    """Test custom review statuses, target lanes, and notes."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_custom_review_status(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Custom review status messages are recorded"""
        project_name = 'custom_status'
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

        feature = "001-custom-status-test"
        create_test_task_in_review(project_path, feature, "WP10")

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=project_path, check=True)

        tasks_cli = spec_kitty_repo_root / '.kittify' / 'scripts' / 'tasks' / 'tasks_cli.py'

        subprocess.run(
            [
                'python3', str(tasks_cli), 'approve', feature, 'WP10',
                '--reviewer-agent', 'reviewer',
                '--review-status', 'approved with suggestions for future work'
            ],
            cwd=project_path,
            check=True
        )

        done_task = project_path / "kitty-specs" / feature / "tasks" / "done" / "WP10.md"
        content = done_task.read_text(encoding="utf-8")

        # Verify custom review status (YAML may use quotes)
        assert ('review_status: approved with suggestions for future work' in content or
                'review_status: "approved with suggestions for future work"' in content), \
            "Custom review status should be recorded"

    def test_custom_target_lane(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Tasks can be approved to custom target lanes"""
        project_name = 'custom_target'
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

        feature = "001-target-lane-test"
        create_test_task_in_review(project_path, feature, "WP11")

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=project_path, check=True)

        tasks_cli = spec_kitty_repo_root / '.kittify' / 'scripts' / 'tasks' / 'tasks_cli.py'

        # Approve to 'doing' instead of 'done' (e.g., needs more work after review)
        subprocess.run(
            [
                'python3', str(tasks_cli), 'approve', feature, 'WP11',
                '--reviewer-agent', 'reviewer',
                '--target-lane', 'doing',
                '--review-status', 'needs rework'
            ],
            cwd=project_path,
            check=True
        )

        # Should be in doing lane
        doing_task = project_path / "kitty-specs" / feature / "tasks" / "doing" / "WP11.md"
        assert doing_task.exists(), "Task should be in custom target lane (doing)"

        content = doing_task.read_text(encoding="utf-8")
        # YAML may use quotes
        assert ('lane: doing' in content or 'lane: "doing"' in content), \
            "Lane should be updated to target"
        assert ('review_status: needs rework' in content or
                'review_status: "needs rework"' in content), \
            "Review status should be recorded"

    def test_custom_activity_note(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Custom notes are included in activity log"""
        project_name = 'custom_note'
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

        feature = "001-note-test"
        create_test_task_in_review(project_path, feature, "WP12")

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=project_path, check=True)

        tasks_cli = spec_kitty_repo_root / '.kittify' / 'scripts' / 'tasks' / 'tasks_cli.py'

        subprocess.run(
            [
                'python3', str(tasks_cli), 'approve', feature, 'WP12',
                '--reviewer-agent', 'reviewer',
                '--note', 'Excellent implementation, well tested'
            ],
            cwd=project_path,
            check=True
        )

        done_task = project_path / "kitty-specs" / feature / "tasks" / "done" / "WP12.md"
        content = done_task.read_text(encoding="utf-8")

        assert 'Excellent implementation, well tested' in content, \
            "Custom note should appear in activity log"


class TestDryRunMode:
    """Test dry-run mode for approve command."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_dry_run_shows_plan_without_modifying_files(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Dry-run shows approval plan without modifying files"""
        project_name = 'dry_run_test'
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

        feature = "001-dry-run-test"
        task_file = create_test_task_in_review(project_path, feature, "WP13")

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=project_path, check=True)

        tasks_cli = spec_kitty_repo_root / '.kittify' / 'scripts' / 'tasks' / 'tasks_cli.py'

        result = subprocess.run(
            [
                'python3', str(tasks_cli), 'approve', feature, 'WP13',
                '--reviewer-agent', 'reviewer',
                '--dry-run'
            ],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        # Verify output shows plan
        output = result.stdout
        assert '[dry-run]' in output, "Should show dry-run prefix"
        assert 'Would approve WP13' in output, "Should show what would happen"
        assert 'reviewer' in output, "Should show reviewer identity"

        # Verify files not modified
        assert task_file.exists(), "Original task should still exist"
        done_dir = project_path / "kitty-specs" / feature / "tasks" / "done"
        if done_dir.exists():
            done_files = list(done_dir.glob("*.md"))
            assert len(done_files) == 0, "No files should be created in dry-run"

    def test_dry_run_no_git_operations(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Dry-run doesn't perform git operations"""
        project_name = 'dry_run_git_test'
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

        feature = "001-dry-run-git-test"
        create_test_task_in_review(project_path, feature, "WP14")

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=project_path, check=True)

        # Capture initial git status
        status_before = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        ).stdout

        tasks_cli = spec_kitty_repo_root / '.kittify' / 'scripts' / 'tasks' / 'tasks_cli.py'

        subprocess.run(
            [
                'python3', str(tasks_cli), 'approve', feature, 'WP14',
                '--reviewer-agent', 'reviewer',
                '--dry-run'
            ],
            cwd=project_path,
            check=True
        )

        # Verify git status unchanged
        status_after = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        ).stdout

        assert status_before == status_after, \
            "Git status should be unchanged in dry-run mode"


class TestGitOperations:
    """Test git operations during approval."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_approve_removes_source_file(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Approval removes source file from for_review"""
        project_name = 'git_remove_test'
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

        feature = "001-git-remove-test"
        task_file = create_test_task_in_review(project_path, feature, "WP15")

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=project_path, check=True)

        tasks_cli = spec_kitty_repo_root / '.kittify' / 'scripts' / 'tasks' / 'tasks_cli.py'

        subprocess.run(
            [
                'python3', str(tasks_cli), 'approve', feature, 'WP15',
                '--reviewer-agent', 'reviewer'
            ],
            cwd=project_path,
            check=True
        )

        # Verify source file removed
        assert not task_file.exists(), "Source file should be removed"

        # Verify git registered the operation
        status = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        ).stdout

        # Git may show as 'R' (rename) or 'D' (delete) + 'A' (add)
        source_path = f"kitty-specs/{feature}/tasks/for_review/WP15.md"
        target_path = f"kitty-specs/{feature}/tasks/done/WP15.md"

        # Either renamed or deleted
        assert (('R' in status and source_path in status) or
                ('D' in status and source_path in status)), \
            f"Git should show file move/delete. Got: {status}"

    def test_approve_adds_target_file(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Approval adds target file to done lane"""
        project_name = 'git_add_test'
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

        feature = "001-git-add-test"
        create_test_task_in_review(project_path, feature, "WP16")

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=project_path, check=True)

        tasks_cli = spec_kitty_repo_root / '.kittify' / 'scripts' / 'tasks' / 'tasks_cli.py'

        subprocess.run(
            [
                'python3', str(tasks_cli), 'approve', feature, 'WP16',
                '--reviewer-agent', 'reviewer'
            ],
            cwd=project_path,
            check=True
        )

        # Verify target file exists
        done_task = project_path / "kitty-specs" / feature / "tasks" / "done" / "WP16.md"
        assert done_task.exists(), "Target file should be created in done lane"

        # Verify git registered the operation
        status = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        ).stdout

        # Git may show as 'R' (rename) or 'A' (add)
        target_path = f"kitty-specs/{feature}/tasks/done/WP16.md"

        assert (('R' in status and target_path in status) or
                ('A' in status and target_path in status)), \
            f"Git should show file added/renamed. Got: {status}"
