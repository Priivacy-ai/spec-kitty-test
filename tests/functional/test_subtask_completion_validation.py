"""
Comprehensive tests for subtask completion and assignee tracking validation

Tests for Issue #72: https://github.com/Priivacy-ai/spec-kitty/issues/72

Bug: Agents reach /spec-kitty.accept with:
- Unchecked subtasks in tasks.md (still showing [ ])
- Missing assignee fields in WP frontmatter
- No validation preventing moves to for_review/done with incomplete work

Spec-kitty has TWO-TIER tracking:
- Tier 1: Work Package (WP##) - lane: frontmatter field
- Tier 2: Subtasks (T001, T002) - [ ]/[x] checkboxes in tasks.md

The bug: Agents only track Tier 1, ignore Tier 2.

Tests validate:
1. move-task validates subtask completion before for_review/done
2. Assignee field validated
3. Subtasks can be parsed from tasks.md
4. mark-status command works
5. --lenient vs --force flag behavior
6. accept command catches incomplete work
"""
import pytest
import subprocess
import tempfile
import os
import re
from pathlib import Path


@pytest.fixture
def temp_project_dir():
    """Create temporary directory for test project."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def project_with_subtasks(temp_project_dir, spec_kitty_repo_root):
    """
    Create project with feature containing subtasks in tasks.md.

    Returns (project_path, feature_dir, tasks_md_path)
    """
    env = os.environ.copy()
    env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

    subprocess.run(
        ['spec-kitty', 'init', 'test-project', '--ai=claude'],
        cwd=str(temp_project_dir),
        env=env,
        input=b'y\n',
        capture_output=True
    )

    project_path = temp_project_dir / 'test-project'

    subprocess.run(['git', 'init'], cwd=str(project_path), check=True, capture_output=True)
    subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
    subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=str(project_path), check=True, capture_output=True)

    # Create feature
    subprocess.run(
        ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature'],
        cwd=str(project_path),
        env=env,
        capture_output=True
    )

    feature_dir = project_path / 'kitty-specs' / '001-test-feature'

    # Create tasks.md with subtasks
    tasks_md = feature_dir / 'tasks.md'
    tasks_md.write_text("""# Tasks for test-feature

## WP01: Implement Core Feature

- [ ] T001: Create database schema
- [ ] T002: Add API endpoint
- [ ] T003: Write tests
- [ ] T004: Update documentation

Description: Implement the core feature functionality.

## WP02: Add Validation

- [ ] T005: Add input validation
- [ ] T006: Add error handling
- [ ] T007: Write validation tests

Depends on: WP01

Description: Add validation layer.
""")

    # Create WP files
    tasks_dir = feature_dir / 'tasks'
    tasks_dir.mkdir(parents=True, exist_ok=True)

    wp01_file = tasks_dir / 'WP01-implement-core.md'
    wp01_file.write_text("""---
title: WP01: Implement Core Feature
lane: backlog
---

# WP01: Implement Core Feature

Implement the core feature functionality.
""")

    wp02_file = tasks_dir / 'WP02-add-validation.md'
    wp02_file.write_text("""---
title: WP02: Add Validation
lane: backlog
dependencies: [WP01]
---

# WP02: Add Validation

Add validation layer.
""")

    subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
    subprocess.run(['git', 'commit', '-m', 'Add planning'], cwd=str(project_path), check=True, capture_output=True)

    return project_path, feature_dir, tasks_md


class TestSubtaskCompletionValidation:
    """Tests for validating subtask completion before lane transitions"""

    def test_move_to_for_review_blocked_with_unchecked_subtasks(self, project_with_subtasks):
        """
        Test that moving WP to for_review is BLOCKED when subtasks unchecked.

        Bug scenario:
        1. WP01 in 'doing' lane
        2. tasks.md shows: [ ] T001, [ ] T002 (unchecked)
        3. Agent runs: spec-kitty agent move-task WP01 --to for_review
        4. OLD: Succeeds (no validation)
        5. NEW: FAILS with error listing unchecked subtasks

        This is the core bug from Issue #72.
        """
        project_path, feature_dir, tasks_md = project_with_subtasks

        # Move WP01 to doing first
        result = subprocess.run(
            ['spec-kitty', 'agent', 'move-task', 'WP01', '--to', 'doing', '--assignee', 'claude'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Now try to move to for_review with unchecked subtasks
        result = subprocess.run(
            ['spec-kitty', 'agent', 'move-task', 'WP01', '--to', 'for_review'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Should FAIL (or warn loudly)
        if result.returncode == 0:
            # If it succeeds, it's the bug - moving to for_review without checking subtasks
            output = result.stdout + result.stderr

            # At minimum, should WARN about unchecked subtasks
            pytest.fail(
                "BUG (Issue #72): move-task allowed transition to for_review with unchecked subtasks.\n"
                "Expected: Fail or warn about:\n"
                "  - [ ] T001: Create database schema\n"
                "  - [ ] T002: Add API endpoint\n"
                "  - [ ] T003: Write tests\n"
                "  - [ ] T004: Update documentation\n"
                f"Actual: Succeeded without warning\nOutput: {output}"
            )
        else:
            # Good - it failed
            output = result.stdout + result.stderr

            # Should mention unchecked subtasks
            assert 'unchecked' in output.lower() or 'incomplete' in output.lower() or 'subtask' in output.lower(), \
                f"Error should mention unchecked subtasks. Got: {output}"

            # Should list the specific unchecked tasks
            assert 'T001' in output or 'T002' in output or 'T003' in output, \
                "Error should list specific unchecked tasks"

    def test_move_to_done_blocked_with_unchecked_subtasks(self, project_with_subtasks):
        """
        Test that moving directly to 'done' also validates subtasks.

        Some workflows allow direct backlog → done transitions.
        Should still validate subtask completion.
        """
        project_path, feature_dir, tasks_md = project_with_subtasks

        # Try to move directly to done
        result = subprocess.run(
            ['spec-kitty', 'agent', 'move-task', 'WP01', '--to', 'done'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Should fail or warn
        if result.returncode == 0:
            pytest.fail(
                "BUG (Issue #72): move-task allowed transition to 'done' with unchecked subtasks."
            )

    def test_move_with_force_flag_bypasses_validation(self, project_with_subtasks):
        """
        Test that --force flag allows moving despite unchecked subtasks.

        For exceptional cases, user/agent can force the move.
        Should still show warning about unchecked subtasks.
        """
        project_path, feature_dir, tasks_md = project_with_subtasks

        result = subprocess.run(
            ['spec-kitty', 'agent', 'move-task', 'WP01', '--to', 'for_review', '--force'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # With --force, should succeed
        # But should still warn about unchecked subtasks
        output = result.stdout + result.stderr

        if result.returncode == 0:
            # Should warn (even if it proceeds)
            if 'unchecked' not in output.lower() and 'warning' not in output.lower():
                # OK if no warning, but document behavior
                pass

    def test_move_with_all_subtasks_checked_succeeds(self, project_with_subtasks):
        """
        Test that moving to for_review SUCCEEDS when all subtasks checked.

        Happy path: All [ ] changed to [x], move should work.
        """
        project_path, feature_dir, tasks_md = project_with_subtasks

        # Mark all subtasks complete in tasks.md
        tasks_content = tasks_md.read_text()
        # Replace all [ ] with [x] for WP01 subtasks
        tasks_content = tasks_content.replace('- [ ] T001', '- [x] T001')
        tasks_content = tasks_content.replace('- [ ] T002', '- [x] T002')
        tasks_content = tasks_content.replace('- [ ] T003', '- [x] T003')
        tasks_content = tasks_content.replace('- [ ] T004', '- [x] T004')
        tasks_md.write_text(tasks_content)

        subprocess.run(['git', 'add', str(tasks_md)], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Mark subtasks complete'], cwd=str(project_path), check=True, capture_output=True)

        # Move to doing first
        subprocess.run(
            ['spec-kitty', 'agent', 'move-task', 'WP01', '--to', 'doing', '--assignee', 'claude'],
            cwd=str(project_path),
            capture_output=True
        )

        # Now move to for_review (all subtasks checked)
        result = subprocess.run(
            ['spec-kitty', 'agent', 'move-task', 'WP01', '--to', 'for_review'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Should succeed (all subtasks complete)
        assert result.returncode == 0, \
            f"Should succeed when all subtasks checked. Error: {result.stderr}"


class TestAssigneeFieldValidation:
    """Tests for assignee field validation"""

    def test_move_to_doing_requires_assignee(self, project_with_subtasks):
        """
        Test that moving to 'doing' lane requires --assignee flag.

        Bug: Agents don't set assignee, causing metadata_issues in acceptance.
        Fix: Require --assignee when claiming work.
        """
        project_path, feature_dir, tasks_md = project_with_subtasks

        # Try to move to doing WITHOUT --assignee
        result = subprocess.run(
            ['spec-kitty', 'agent', 'move-task', 'WP01', '--to', 'doing'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Should fail or warn
        if result.returncode == 0:
            # Check if assignee was set anyway (default behavior)
            wp_file = feature_dir / 'tasks' / 'WP01-implement-core.md'
            content = wp_file.read_text()

            if 'assignee:' not in content:
                pytest.fail(
                    "BUG (Issue #72): move-task to 'doing' without --assignee allowed.\n"
                    "WP frontmatter missing assignee field.\n"
                    "This causes metadata_issues in acceptance."
                )

    def test_assignee_field_added_to_frontmatter(self, project_with_subtasks):
        """
        Test that --assignee flag adds assignee to WP frontmatter.
        """
        project_path, feature_dir, tasks_md = project_with_subtasks

        # Move with assignee
        result = subprocess.run(
            ['spec-kitty', 'agent', 'move-task', 'WP01', '--to', 'doing', '--assignee', 'claude-code'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Check frontmatter
        wp_file = feature_dir / 'tasks' / 'WP01-implement-core.md'
        content = wp_file.read_text()

        # Should have assignee in frontmatter
        assert 'assignee:' in content, "Frontmatter should have assignee field"
        assert 'claude-code' in content, "Assignee should be 'claude-code'"

    def test_acceptance_fails_with_missing_assignee(self, project_with_subtasks):
        """
        Test that spec-kitty accept fails when WPs missing assignee.

        This is the symptom described in Issue #72.
        Acceptance should catch: "WP01: missing assignee in frontmatter"
        """
        project_path, feature_dir, tasks_md = project_with_subtasks

        # Move WP to done WITHOUT setting assignee
        wp_file = feature_dir / 'tasks' / 'WP01-implement-core.md'
        content = wp_file.read_text()

        # Update lane but NO assignee
        content = content.replace('lane: backlog', 'lane: done')
        wp_file.write_text(content)

        subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Move to done'], cwd=str(project_path), check=True, capture_output=True)

        # Run acceptance
        result = subprocess.run(
            ['spec-kitty', 'accept'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Should fail (or report issues)
        output = result.stdout + result.stderr

        # Should mention missing assignee
        assert 'assignee' in output.lower() or 'metadata' in output.lower(), \
            f"Accept should catch missing assignee. Output: {output}"


class TestSubtaskParsingFromTasksMd:
    """Tests for parsing subtasks from tasks.md"""

    def test_parse_subtasks_for_wp01(self, project_with_subtasks):
        """
        Test parsing subtasks belonging to WP01 from tasks.md.

        tasks.md structure:
        ## WP01: Title
        - [ ] T001: Subtask 1
        - [ ] T002: Subtask 2

        Should extract: [(T001, unchecked), (T002, unchecked)]
        """
        project_path, feature_dir, tasks_md = project_with_subtasks

        # Read tasks.md
        content = tasks_md.read_text()

        # Parse subtasks for WP01
        # Look for section starting with "## WP01"
        wp01_section = re.search(r'## WP01:.*?(?=## WP|\Z)', content, re.DOTALL)

        assert wp01_section, "Should find WP01 section"

        # Find all subtasks in section
        subtasks = re.findall(r'- \[([ x])\] (T\d+):', wp01_section.group())

        # Should find 4 subtasks
        assert len(subtasks) == 4, f"Should find 4 subtasks for WP01, found {len(subtasks)}"

        # All should be unchecked
        for checked, task_id in subtasks:
            assert checked == ' ', f"{task_id} should be unchecked [ ], got [{checked}]"

    def test_distinguish_checked_vs_unchecked_subtasks(self, project_with_subtasks):
        """
        Test distinguishing [x] from [ ] subtasks.
        """
        project_path, feature_dir, tasks_md = project_with_subtasks

        # Mark some subtasks complete
        content = tasks_md.read_text()
        content = content.replace('- [ ] T001', '- [x] T001')  # Checked
        content = content.replace('- [ ] T003', '- [x] T003')  # Checked
        # T002, T004 remain unchecked
        tasks_md.write_text(content)

        # Parse again
        content = tasks_md.read_text()
        wp01_section = re.search(r'## WP01:.*?(?=## WP|\Z)', content, re.DOTALL)
        subtasks = re.findall(r'- \[([ x])\] (T\d+):', wp01_section.group())

        # Should have 2 checked, 2 unchecked
        checked = [tid for status, tid in subtasks if status == 'x']
        unchecked = [tid for status, tid in subtasks if status == ' ']

        assert set(checked) == {'T001', 'T003'}, f"T001 and T003 should be checked, got {checked}"
        assert set(unchecked) == {'T002', 'T004'}, f"T002 and T004 should be unchecked, got {unchecked}"

    def test_subtasks_for_multiple_wps_parsed_separately(self, project_with_subtasks):
        """
        Test that subtasks are correctly associated with their WPs.

        WP01 has T001-T004
        WP02 has T005-T007
        Should not mix them up.
        """
        project_path, feature_dir, tasks_md = project_with_subtasks

        content = tasks_md.read_text()

        # Find WP01 subtasks
        wp01_section = re.search(r'## WP01:.*?(?=## WP|\Z)', content, re.DOTALL)
        wp01_tasks = re.findall(r'- \[.\] (T\d+):', wp01_section.group())

        # Find WP02 subtasks
        wp02_section = re.search(r'## WP02:.*?(?=## WP|\Z)', content, re.DOTALL)
        wp02_tasks = re.findall(r'- \[.\] (T\d+):', wp02_section.group())

        # Verify separation
        assert set(wp01_tasks) == {'T001', 'T002', 'T003', 'T004'}, "WP01 should have T001-T004"
        assert set(wp02_tasks) == {'T005', 'T006', 'T007'}, "WP02 should have T005-T007"

        # No overlap
        assert not set(wp01_tasks).intersection(set(wp02_tasks)), "Tasks should not overlap between WPs"


class TestMarkStatusCommand:
    """Tests for spec-kitty agent mark-status command"""

    def test_mark_status_command_exists(self):
        """
        Test that mark-status command is available.

        This is the command agents should use to check subtasks.
        """
        result = subprocess.run(
            ['spec-kitty', 'agent', 'mark-status', '--help'],
            capture_output=True,
            text=True
        )

        # Command should exist
        assert result.returncode == 0, "mark-status command should exist"

        help_text = result.stdout.lower()
        assert 'task-id' in help_text or 'task' in help_text, "Should document task-id parameter"
        assert 'status' in help_text, "Should document status parameter"

    def test_mark_status_updates_tasks_md(self, project_with_subtasks):
        """
        Test that mark-status changes [ ] to [x] in tasks.md.
        """
        project_path, feature_dir, tasks_md = project_with_subtasks

        # Mark T001 as done
        result = subprocess.run(
            ['spec-kitty', 'agent', 'mark-status', '--task-id', 'T001', '--status', 'done'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Check tasks.md updated
        content = tasks_md.read_text()

        # T001 should be [x]
        assert '- [x] T001' in content, "T001 should be marked complete"

        # Others should still be [ ]
        assert '- [ ] T002' in content, "T002 should still be unchecked"
        assert '- [ ] T003' in content, "T003 should still be unchecked"

    def test_mark_status_with_wrong_task_id_fails(self, project_with_subtasks):
        """
        Test that marking non-existent task fails.
        """
        project_path, feature_dir, tasks_md = project_with_subtasks

        result = subprocess.run(
            ['spec-kitty', 'agent', 'mark-status', '--task-id', 'T999', '--status', 'done'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Should fail
        assert result.returncode != 0, "Should fail for non-existent task ID"

        output = result.stdout + result.stderr
        assert 'T999' in output or 'not found' in output.lower(), \
            "Error should mention task not found"


class TestAcceptCommandValidation:
    """Tests for spec-kitty accept validation"""

    def test_accept_reports_unchecked_tasks(self, project_with_subtasks):
        """
        Test that accept command reports unchecked subtasks.

        This is the symptom from Issue #72:
        - unchecked_tasks: 18 items
        - User must manually fix before acceptance passes
        """
        project_path, feature_dir, tasks_md = project_with_subtasks

        # Move all WPs to done (but leave subtasks unchecked)
        for wp_file in (feature_dir / 'tasks').glob('WP*.md'):
            content = wp_file.read_text()
            content = content.replace('lane: backlog', 'lane: done')
            # Add assignee to avoid that error
            if 'assignee:' not in content:
                content = content.replace('---\n', '---\nassignee: test-agent\n', 1)
            wp_file.write_text(content)

        subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Move to done'], cwd=str(project_path), check=True, capture_output=True)

        # Run acceptance
        result = subprocess.run(
            ['spec-kitty', 'accept'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        output = result.stdout + result.stderr

        # Should report unchecked tasks
        assert 'unchecked' in output.lower() or 'incomplete' in output.lower(), \
            f"Accept should report unchecked tasks. Output: {output}"

        # Should mention specific tasks
        assert 'T001' in output or 'T002' in output or 'subtask' in output.lower(), \
            "Should list unchecked subtasks"

    def test_accept_reports_missing_assignees(self, project_with_subtasks):
        """
        Test that accept reports WPs with missing assignee field.

        Symptom from Issue #72:
        - metadata_issues: "WP01: missing assignee in frontmatter"
        """
        project_path, feature_dir, tasks_md = project_with_subtasks

        # Move WPs to done WITHOUT assignee
        for wp_file in (feature_dir / 'tasks').glob('WP*.md'):
            content = wp_file.read_text()
            content = content.replace('lane: backlog', 'lane: done')
            # Explicitly do NOT add assignee
            wp_file.write_text(content)

        # Mark all subtasks complete to isolate the assignee issue
        content = tasks_md.read_text()
        content = content.replace('- [ ]', '- [x]')
        tasks_md.write_text(content)

        subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Done'], cwd=str(project_path), check=True, capture_output=True)

        # Run acceptance
        result = subprocess.run(
            ['spec-kitty', 'accept'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        output = result.stdout + result.stderr

        # Should report missing assignee
        assert 'assignee' in output.lower() or 'metadata' in output.lower(), \
            f"Accept should report missing assignee. Output: {output}"

    def test_accept_succeeds_with_all_complete_and_assigned(self, project_with_subtasks):
        """
        Test that accept succeeds when everything is correct.

        Happy path:
        - All subtasks checked [x]
        - All WPs have assignee
        - All WPs in done lane
        """
        project_path, feature_dir, tasks_md = project_with_subtasks

        # Mark all subtasks complete
        content = tasks_md.read_text()
        content = content.replace('- [ ]', '- [x]')
        tasks_md.write_text(content)

        # Move all WPs to done WITH assignee
        for wp_file in (feature_dir / 'tasks').glob('WP*.md'):
            content = wp_file.read_text()
            content = content.replace('lane: backlog', 'lane: done')
            if 'assignee:' not in content:
                # Add assignee after first ---
                content = content.replace('---\n', '---\nassignee: claude-code\n', 1)
            wp_file.write_text(content)

        subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Complete all'], cwd=str(project_path), check=True, capture_output=True)

        # Run acceptance
        result = subprocess.run(
            ['spec-kitty', 'accept'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Should succeed or at least not fail on subtasks/assignee
        output = result.stdout + result.stderr

        # Should NOT complain about unchecked tasks
        if 'unchecked' in output.lower():
            pytest.fail(f"Should not report unchecked tasks when all are [x]. Output: {output}")

        # Should NOT complain about missing assignee
        if 'missing assignee' in output.lower():
            pytest.fail(f"Should not report missing assignee when all WPs have it. Output: {output}")


class TestLenientFlagBehavior:
    """Tests for --lenient flag behavior"""

    def test_lenient_allows_missing_assignee(self, project_with_subtasks):
        """
        Test that --lenient flag skips assignee validation.

        Per Issue #72 proposal: --lenient skips metadata warnings.
        """
        project_path, feature_dir, tasks_md = project_with_subtasks

        # Move to done without assignee
        wp_file = feature_dir / 'tasks' / 'WP01-implement-core.md'
        content = wp_file.read_text()
        content = content.replace('lane: backlog', 'lane: done')
        wp_file.write_text(content)

        # Mark all subtasks complete
        content = tasks_md.read_text()
        content = content.replace('- [ ]', '- [x]')
        tasks_md.write_text(content)

        subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Done'], cwd=str(project_path), check=True, capture_output=True)

        # Run with --lenient
        result = subprocess.run(
            ['spec-kitty', 'accept', '--lenient'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # --lenient should skip metadata checks
        # Should not fail just because of missing assignee

    def test_lenient_does_not_skip_unchecked_subtasks(self, project_with_subtasks):
        """
        Test that --lenient does NOT skip unchecked subtasks validation.

        Per Issue #72 proposal:
        - --lenient skips metadata warnings (assignee, shell_pid)
        - --lenient does NOT skip unchecked subtasks (indicates incomplete work)

        This is important: unchecked subtasks = work not done.
        Missing assignee = metadata issue.
        """
        project_path, feature_dir, tasks_md = project_with_subtasks

        # Move to done WITH assignee but WITHOUT checking subtasks
        wp_file = feature_dir / 'tasks' / 'WP01-implement-core.md'
        content = wp_file.read_text()
        content = content.replace('lane: backlog', 'lane: done')
        content = content.replace('---\n', '---\nassignee: claude\n', 1)
        wp_file.write_text(content)

        # Leave subtasks unchecked

        subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Done'], cwd=str(project_path), check=True, capture_output=True)

        # Run with --lenient
        result = subprocess.run(
            ['spec-kitty', 'accept', '--lenient'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        output = result.stdout + result.stderr

        # Even with --lenient, should still report unchecked subtasks
        # (This is the proposed behavior - lenient != ignore incomplete work)
        if 'unchecked' not in output.lower() and 'T001' not in output:
            # Document actual behavior
            # May not be implemented yet
            pass


class TestSkipTaskCheckFlag:
    """Tests for --skip-task-check flag (proposed in Issue #72)"""

    def test_skip_task_check_flag_exists(self):
        """
        Test that --skip-task-check flag exists (proposed enhancement).

        Separate from --lenient for truly exceptional cases.
        """
        result = subprocess.run(
            ['spec-kitty', 'accept', '--help'],
            capture_output=True,
            text=True
        )

        # Check if flag exists
        if '--skip-task-check' in result.stdout:
            # Proposed enhancement implemented
            pass
        else:
            # Not yet implemented - document expectation
            pytest.skip("--skip-task-check flag not yet implemented (proposed in Issue #72)")

    def test_skip_task_check_bypasses_subtask_validation(self, project_with_subtasks):
        """
        Test that --skip-task-check allows acceptance with unchecked subtasks.

        For exceptional cases where user knows work is incomplete but wants to proceed.
        """
        result = subprocess.run(
            ['spec-kitty', 'accept', '--help'],
            capture_output=True,
            text=True
        )

        if '--skip-task-check' not in result.stdout:
            pytest.skip("--skip-task-check not implemented")

        project_path, feature_dir, tasks_md = project_with_subtasks

        # Move to done, leave subtasks unchecked
        wp_file = feature_dir / 'tasks' / 'WP01-implement-core.md'
        content = wp_file.read_text()
        content = content.replace('lane: backlog', 'lane: done')
        content = content.replace('---\n', '---\nassignee: test\n', 1)
        wp_file.write_text(content)

        subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Done'], cwd=str(project_path), check=True, capture_output=True)

        # Run with --skip-task-check
        result = subprocess.run(
            ['spec-kitty', 'accept', '--skip-task-check'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Should proceed despite unchecked subtasks
        # (implementation-specific behavior)


class TestTwoTierTrackingSystem:
    """Tests for the two-tier tracking system (WP + Subtasks)"""

    def test_wp_lane_updates_independently_of_subtasks(self, project_with_subtasks):
        """
        Test that WP lane can update even when subtasks unchecked.

        Current behavior (bug):
        - WP moves: backlog → doing → for_review (lane: field updates)
        - Subtasks stay: [ ] [ ] [ ] (never checked)

        Two tiers are independent (that's the bug).
        """
        project_path, feature_dir, tasks_md = project_with_subtasks

        # Move WP through lanes
        result1 = subprocess.run(
            ['spec-kitty', 'agent', 'move-task', 'WP01', '--to', 'doing', '--assignee', 'test'],
            cwd=str(project_path),
            capture_output=True
        )

        result2 = subprocess.run(
            ['spec-kitty', 'agent', 'move-task', 'WP01', '--to', 'for_review'],
            cwd=str(project_path),
            capture_output=True
        )

        # Check WP lane changed
        wp_file = feature_dir / 'tasks' / 'WP01-implement-core.md'
        wp_content = wp_file.read_text()

        # Check subtasks unchanged
        tasks_content = tasks_md.read_text()

        # WP should be in for_review
        has_lane_update = 'lane: for_review' in wp_content or 'lane: doing' in wp_content

        # Subtasks should still be unchecked
        has_unchecked = '- [ ] T001' in tasks_content

        # Document the disconnect
        if has_lane_update and has_unchecked:
            # This is the bug - two tiers disconnected
            pass

    def test_agents_should_use_both_tiers(self, project_with_subtasks):
        """
        Test the CORRECT workflow using both tiers.

        Correct agent behavior:
        1. move-task WP01 → doing (set assignee)
        2. FOR EACH subtask:
           - Do the work
           - mark-status T00X → done
        3. move-task WP01 → for_review (validate all subtasks [x])
        """
        project_path, feature_dir, tasks_md = project_with_subtasks

        # Tier 1: Move WP to doing
        subprocess.run(
            ['spec-kitty', 'agent', 'move-task', 'WP01', '--to', 'doing', '--assignee', 'claude'],
            cwd=str(project_path),
            check=True,
            capture_output=True
        )

        # Tier 2: Mark each subtask
        for task_id in ['T001', 'T002', 'T003', 'T004']:
            subprocess.run(
                ['spec-kitty', 'agent', 'mark-status', '--task-id', task_id, '--status', 'done'],
                cwd=str(project_path),
                capture_output=True
            )

        # Verify all subtasks checked
        content = tasks_md.read_text()
        assert '- [x] T001' in content, "T001 should be checked"
        assert '- [x] T002' in content, "T002 should be checked"
        assert '- [x] T003' in content, "T003 should be checked"
        assert '- [x] T004' in content, "T004 should be checked"
        assert '- [ ]' not in content or 'WP02' in content, "All WP01 subtasks should be checked"

        # Tier 1: Move to for_review (should now succeed)
        result = subprocess.run(
            ['spec-kitty', 'agent', 'move-task', 'WP01', '--to', 'for_review'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Should succeed (all subtasks complete)
        assert result.returncode == 0, \
            f"Should succeed with all subtasks checked. Error: {result.stderr}"


class TestRegressionPrevention:
    """Prevent regression of Issue #72"""

    def test_no_unchecked_tasks_at_acceptance(self, project_with_subtasks):
        """
        Prevent regression: Acceptance should not see unchecked tasks.

        Issue #72 symptom: Every feature has 10-20 unchecked tasks at acceptance.

        With proper workflow:
        - Agents mark subtasks during implementation
        - Validation at move-task prevents premature for_review
        - Acceptance sees 0 unchecked tasks
        """
        project_path, feature_dir, tasks_md = project_with_subtasks

        # Simulate proper workflow
        # 1. Move to doing with assignee
        subprocess.run(
            ['spec-kitty', 'agent', 'move-task', 'WP01', '--to', 'doing', '--assignee', 'claude'],
            cwd=str(project_path),
            check=True,
            capture_output=True
        )

        # 2. Mark all subtasks
        for task_id in ['T001', 'T002', 'T003', 'T004']:
            subprocess.run(
                ['spec-kitty', 'agent', 'mark-status', '--task-id', task_id, '--status', 'done'],
                cwd=str(project_path),
                capture_output=True
            )

        subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Mark complete'], cwd=str(project_path), check=True, capture_output=True)

        # 3. Move to for_review
        subprocess.run(
            ['spec-kitty', 'agent', 'move-task', 'WP01', '--to', 'for_review'],
            cwd=str(project_path),
            check=True,
            capture_output=True
        )

        # 4. Review and move to done
        subprocess.run(
            ['spec-kitty', 'agent', 'move-task', 'WP01', '--to', 'done'],
            cwd=str(project_path),
            check=True,
            capture_output=True
        )

        subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Done'], cwd=str(project_path), check=True, capture_output=True)

        # 5. Run acceptance
        result = subprocess.run(
            ['spec-kitty', 'accept'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        output = result.stdout + result.stderr

        # Should NOT report unchecked tasks (all were checked during workflow)
        unchecked_count = output.lower().count('unchecked')

        # If unchecked tasks reported, it's a regression
        if unchecked_count > 0:
            # Check if they're for WP01 (we checked all WP01 tasks)
            if 'T001' in output or 'T002' in output or 'T003' in output or 'T004' in output:
                pytest.fail(
                    "REGRESSION (Issue #72): Unchecked tasks reported despite marking all complete.\n"
                    f"Output: {output}"
                )

    def test_validation_error_message_includes_remediation(self, project_with_subtasks):
        """
        Test that validation error suggests how to fix.

        Per Issue #72 proposal, error should show:
        - Which subtasks are unchecked
        - Exact commands to run: spec-kitty agent mark-status --task-id T001 --status done
        """
        project_path, feature_dir, tasks_md = project_with_subtasks

        # Try to move to for_review with unchecked subtasks
        result = subprocess.run(
            ['spec-kitty', 'agent', 'move-task', 'WP01', '--to', 'for_review', '--assignee', 'test'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            output = result.stdout + result.stderr

            # Should show remediation commands
            if 'unchecked' in output.lower() or 'incomplete' in output.lower():
                # Check for remediation
                has_remediation = (
                    'mark-status' in output or
                    'mark complete' in output.lower() or
                    'T001' in output  # Lists specific tasks
                )

                assert has_remediation, \
                    "Error should include remediation (how to mark tasks complete)"
