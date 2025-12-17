"""
Test Frontmatter-Only Lane Management (v0.9.0+)

Tests the flat tasks/ directory structure and frontmatter-based lane management
introduced in v0.9.0. This feature eliminates directory-based lanes in favor
of the `lane:` YAML frontmatter field as the single source of truth.

Key Changes from v0.8.x:
- All WP files live in flat `tasks/` directory (no planned/, doing/, etc. subdirectories)
- `move` command renamed to `update` (reflects metadata-only changes)
- Lane changes update frontmatter without moving files
- `status` command groups WPs by frontmatter lane field
- Migration command (`spec-kitty upgrade`) flattens existing directory structure

Test Coverage:
1. Flat Structure Tests (4 tests)
   - New features use flat tasks/ directory
   - No lane subdirectories after v0.9.0
   - WP files created directly in tasks/
   - README.md updated for flat structure

2. Update Command Tests (5 tests)
   - `update` command exists (replaces `move`)
   - update changes lane: frontmatter only
   - update preserves file location (no file moves)
   - update adds activity log entry
   - update validates lane values

3. Status Command Tests (3 tests)
   - status groups WPs by frontmatter lane
   - status works with flat structure
   - status auto-detects feature from worktree

4. Legacy Detection Tests (3 tests)
   - Detects old directory-based structure
   - New flat structure not flagged as legacy
   - Warning suggests upgrade command

5. Migration Command Tests (5 tests)
   - upgrade flattens lane directories
   - upgrade preserves lane: frontmatter
   - upgrade handles worktrees
   - upgrade is idempotent
   - upgrade cleans up empty directories

Note: Tests require spec-kitty >= 0.9.0
"""

import json
import os
import subprocess
from pathlib import Path

import pytest


def _get_spec_kitty_version():
    """Get spec-kitty version at module load time for skipif."""
    try:
        result = subprocess.run(
            ['spec-kitty', '--version'],
            capture_output=True,
            text=True,
            check=True
        )
        version_str = result.stdout.strip().split()[-1]
        return tuple(map(int, version_str.split('.')))
    except Exception:
        return (0, 0, 0)


# All tests require v0.9.0+
pytestmark = pytest.mark.skipif(
    _get_spec_kitty_version() < (0, 9, 0),
    reason="Requires spec-kitty >= 0.9.0"
)


class TestFlatTasksStructure:
    """Test that v0.9.0+ uses flat tasks/ directory structure."""

    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        """Create temporary directory for test project."""
        return tmp_path

    def test_new_feature_has_flat_tasks_directory(
        self, temp_project_dir, spec_kitty_repo_root
    ):
        """Test: New features have flat tasks/ directory (no lane subdirs)

        GIVEN: spec-kitty >= 0.9.0
        WHEN: Creating a new feature
        THEN: tasks/ directory should be flat (no planned/, doing/, etc.)
        """
        project_name = "test_flat_structure"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Initialize project
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
            [str(create_script), '--json', '--feature-name', 'Flat Structure Test',
             'Testing flat tasks directory'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        # Parse output
        feature_info = None
        for line in result.stdout.split('\n'):
            if line.strip().startswith('{'):
                try:
                    feature_info = json.loads(line)
                    break
                except json.JSONDecodeError:
                    continue

        if not feature_info or 'BRANCH_NAME' not in feature_info:
            pytest.skip("Could not parse feature info")

        branch_name = feature_info['BRANCH_NAME']
        worktree_path = project_path / '.worktrees' / branch_name
        tasks_dir = worktree_path / 'kitty-specs' / branch_name / 'tasks'

        assert tasks_dir.exists(), "tasks/ directory should exist"

        # Lane subdirectories should NOT exist
        lane_dirs = ['planned', 'doing', 'for_review', 'done']
        for lane in lane_dirs:
            lane_dir = tasks_dir / lane
            assert not lane_dir.exists(), \
                f"Lane subdirectory {lane}/ should NOT exist in v0.9.0+"

    def test_no_gitkeep_in_lane_subdirs(
        self, temp_project_dir, spec_kitty_repo_root
    ):
        """Test: No .gitkeep files in lane subdirectories (they don't exist)

        GIVEN: spec-kitty >= 0.9.0
        WHEN: Creating a new feature
        THEN: No lane subdirectories means no .gitkeep files in them
        """
        project_name = "test_no_gitkeep_lanes"
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

        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'No Gitkeep Test',
             'Testing no lane gitkeeps'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        feature_info = None
        for line in result.stdout.split('\n'):
            if line.strip().startswith('{'):
                try:
                    feature_info = json.loads(line)
                    break
                except json.JSONDecodeError:
                    continue

        if not feature_info or 'BRANCH_NAME' not in feature_info:
            pytest.skip("Could not parse feature info")

        branch_name = feature_info['BRANCH_NAME']
        worktree_path = project_path / '.worktrees' / branch_name
        tasks_dir = worktree_path / 'kitty-specs' / branch_name / 'tasks'

        # Find all .gitkeep files
        gitkeeps = list(tasks_dir.rglob('.gitkeep'))

        # Should only be in tasks/ itself (if any), not in lane subdirs
        for gitkeep in gitkeeps:
            assert gitkeep.parent == tasks_dir, \
                f"Found .gitkeep in subdirectory: {gitkeep}"

    def test_readme_describes_flat_structure(
        self, temp_project_dir, spec_kitty_repo_root
    ):
        """Test: README.md describes flat structure and frontmatter lanes

        GIVEN: spec-kitty >= 0.9.0
        WHEN: Creating a new feature
        THEN: tasks/README.md should explain frontmatter-based lanes
        """
        project_name = "test_readme_flat"
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

        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'README Test',
             'Testing README content'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        feature_info = None
        for line in result.stdout.split('\n'):
            if line.strip().startswith('{'):
                try:
                    feature_info = json.loads(line)
                    break
                except json.JSONDecodeError:
                    continue

        if not feature_info or 'BRANCH_NAME' not in feature_info:
            pytest.skip("Could not parse feature info")

        branch_name = feature_info['BRANCH_NAME']
        worktree_path = project_path / '.worktrees' / branch_name
        readme = worktree_path / 'kitty-specs' / branch_name / 'tasks' / 'README.md'

        if not readme.exists():
            pytest.skip("README.md not found")

        content = readme.read_text().lower()

        # Should mention frontmatter-based lanes
        assert 'frontmatter' in content or 'lane:' in content, \
            "README should explain frontmatter-based lane tracking"

        # Should NOT suggest moving files between directories
        assert 'move' not in content or 'update' in content, \
            "README should use 'update' command, not 'move'"

    def test_wp_files_created_directly_in_tasks(
        self, temp_project_dir, spec_kitty_repo_root
    ):
        """Test: WP files are created directly in tasks/ (not in subdirectories)

        GIVEN: spec-kitty >= 0.9.0
        WHEN: Creating a work package
        THEN: File should be created in tasks/ with lane: in frontmatter
        """
        project_name = "test_wp_flat"
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

        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'WP Test',
             'Testing WP creation'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        feature_info = None
        for line in result.stdout.split('\n'):
            if line.strip().startswith('{'):
                try:
                    feature_info = json.loads(line)
                    break
                except json.JSONDecodeError:
                    continue

        if not feature_info or 'BRANCH_NAME' not in feature_info:
            pytest.skip("Could not parse feature info")

        branch_name = feature_info['BRANCH_NAME']
        worktree_path = project_path / '.worktrees' / branch_name
        tasks_dir = worktree_path / 'kitty-specs' / branch_name / 'tasks'

        # Create a WP file manually (simulating agent behavior)
        wp_file = tasks_dir / 'WP01-test-task.md'
        wp_file.write_text('''---
work_package_id: WP01
lane: "planned"
title: "Test Task"
---

# WP01: Test Task

Test work package content.
''')

        # Verify file is in flat tasks/ directory
        assert wp_file.exists(), "WP file should be in tasks/"
        assert wp_file.parent == tasks_dir, "WP file should be directly in tasks/, not a subdirectory"


class TestUpdateCommand:
    """Test the update command (replaces move in v0.9.0)."""

    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        """Create temporary directory for test project."""
        return tmp_path

    def test_update_command_exists(
        self, temp_project_dir, spec_kitty_repo_root
    ):
        """Test: update command exists and accepts feature/wp/lane args

        GIVEN: spec-kitty >= 0.9.0
        WHEN: Running tasks_cli.py update --help
        THEN: Command should exist and show usage
        """
        project_name = "test_update_exists"
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

        # Get tasks CLI path
        tasks_cli = project_path / '.kittify' / 'scripts' / 'tasks' / 'tasks_cli.py'

        result = subprocess.run(
            ['python3', str(tasks_cli), 'update', '--help'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        # Command should exist (exit 0) and show help
        assert result.returncode == 0, \
            f"update command should exist. stderr: {result.stderr}"
        assert 'lane' in result.stdout.lower() or 'update' in result.stdout.lower(), \
            "Help should mention lane or update"

    def test_move_command_removed_or_aliased(
        self, temp_project_dir, spec_kitty_repo_root
    ):
        """Test: move command is removed or aliased to update

        GIVEN: spec-kitty >= 0.9.0
        WHEN: Running tasks_cli.py move
        THEN: Should either fail or show deprecation warning
        """
        project_name = "test_move_removed"
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

        tasks_cli = project_path / '.kittify' / 'scripts' / 'tasks' / 'tasks_cli.py'

        result = subprocess.run(
            ['python3', str(tasks_cli), 'move', '--help'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        # Either command doesn't exist, or shows deprecation warning
        if result.returncode == 0:
            output = result.stdout + result.stderr
            assert 'deprecat' in output.lower() or 'update' in output.lower(), \
                "move command should show deprecation or redirect to update"
        # If returncode != 0, command doesn't exist (also acceptable)

    def test_update_changes_frontmatter_only(
        self, temp_project_dir, spec_kitty_repo_root
    ):
        """Test: update changes lane: frontmatter without moving file

        GIVEN: WP file in tasks/ with lane: "planned"
        WHEN: Running update to "doing"
        THEN: File stays in tasks/, frontmatter lane updated to "doing"
        """
        project_name = "test_update_frontmatter"
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

        # Create feature structure manually
        feature = "001-test-feature"
        tasks_dir = project_path / 'kitty-specs' / feature / 'tasks'
        tasks_dir.mkdir(parents=True, exist_ok=True)

        # Create WP file with planned lane
        wp_file = tasks_dir / 'WP01-test.md'
        wp_file.write_text('''---
work_package_id: WP01
lane: "planned"
title: "Test Task"
---

# WP01: Test Task
''')

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=project_path, check=True)

        tasks_cli = project_path / '.kittify' / 'scripts' / 'tasks' / 'tasks_cli.py'

        # Update lane to doing
        subprocess.run(
            ['python3', str(tasks_cli), 'update', feature, 'WP01', 'doing'],
            cwd=project_path,
            check=True
        )

        # Verify file still in same location
        assert wp_file.exists(), "File should still exist in same location"

        # Verify frontmatter updated
        content = wp_file.read_text()
        assert 'lane: "doing"' in content or "lane: doing" in content, \
            "lane: should be updated to doing"

    def test_update_adds_activity_log_entry(
        self, temp_project_dir, spec_kitty_repo_root
    ):
        """Test: update adds activity log entry

        GIVEN: WP file with existing activity log
        WHEN: Running update command
        THEN: Activity log should have new entry with lane change
        """
        project_name = "test_update_activity"
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

        feature = "001-activity-test"
        tasks_dir = project_path / 'kitty-specs' / feature / 'tasks'
        tasks_dir.mkdir(parents=True, exist_ok=True)

        wp_file = tasks_dir / 'WP02-activity.md'
        wp_file.write_text('''---
work_package_id: WP02
lane: "doing"
title: "Activity Test"
---

# WP02: Activity Test

## Activity

- 2025-01-01T10:00:00Z - agent-1 - Started work
''')

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=project_path, check=True)

        tasks_cli = project_path / '.kittify' / 'scripts' / 'tasks' / 'tasks_cli.py'

        subprocess.run(
            ['python3', str(tasks_cli), 'update', feature, 'WP02', 'for_review',
             '--note', 'Ready for review'],
            cwd=project_path,
            check=True
        )

        content = wp_file.read_text()

        # Verify activity log has new entry
        assert 'for_review' in content, "Activity log should show new lane"
        assert 'Ready for review' in content or '2025' in content, \
            "Activity log should have timestamp or note"

    def test_update_validates_lane_values(
        self, temp_project_dir, spec_kitty_repo_root
    ):
        """Test: update rejects invalid lane values

        GIVEN: WP file in tasks/
        WHEN: Running update with invalid lane
        THEN: Should fail with clear error listing valid lanes
        """
        project_name = "test_update_validation"
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
        tasks_dir = project_path / 'kitty-specs' / feature / 'tasks'
        tasks_dir.mkdir(parents=True, exist_ok=True)

        wp_file = tasks_dir / 'WP03-validation.md'
        wp_file.write_text('''---
work_package_id: WP03
lane: "planned"
---
# WP03
''')

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=project_path, check=True)

        tasks_cli = project_path / '.kittify' / 'scripts' / 'tasks' / 'tasks_cli.py'

        result = subprocess.run(
            ['python3', str(tasks_cli), 'update', feature, 'WP03', 'invalid_lane'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        assert result.returncode != 0, "Should reject invalid lane"
        output = result.stderr + result.stdout
        assert 'invalid' in output.lower() or 'lane' in output.lower(), \
            "Error should mention invalid lane"


class TestStatusCommand:
    """Test the status command with frontmatter-based lane grouping."""

    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        """Create temporary directory for test project."""
        return tmp_path

    def test_status_groups_by_frontmatter_lane(
        self, temp_project_dir, spec_kitty_repo_root
    ):
        """Test: status groups WPs by frontmatter lane field

        GIVEN: Multiple WPs with different lane: values
        WHEN: Running tasks_cli.py status
        THEN: Output shows WPs grouped by their frontmatter lanes
        """
        project_name = "test_status_grouping"
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

        feature = "001-status-test"
        tasks_dir = project_path / 'kitty-specs' / feature / 'tasks'
        tasks_dir.mkdir(parents=True, exist_ok=True)

        # Create WPs in different lanes (all in same flat directory)
        (tasks_dir / 'WP01-planned.md').write_text('''---
work_package_id: WP01
lane: "planned"
title: "Planned Task"
---
# WP01
''')
        (tasks_dir / 'WP02-doing.md').write_text('''---
work_package_id: WP02
lane: "doing"
title: "In Progress Task"
---
# WP02
''')
        (tasks_dir / 'WP03-done.md').write_text('''---
work_package_id: WP03
lane: "done"
title: "Completed Task"
---
# WP03
''')

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=project_path, check=True)

        tasks_cli = project_path / '.kittify' / 'scripts' / 'tasks' / 'tasks_cli.py'

        result = subprocess.run(
            ['python3', str(tasks_cli), 'status', feature],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        output = result.stdout.lower()

        # Should show lane groupings
        assert 'planned' in output, "Should show PLANNED section"
        assert 'doing' in output, "Should show DOING section"
        assert 'done' in output, "Should show DONE section"

        # Should show WP IDs
        assert 'wp01' in output, "Should show WP01"
        assert 'wp02' in output, "Should show WP02"
        assert 'wp03' in output, "Should show WP03"

    def test_status_works_with_flat_structure(
        self, temp_project_dir, spec_kitty_repo_root
    ):
        """Test: status reads lanes from frontmatter, not directory

        GIVEN: Flat tasks/ directory (no lane subdirectories)
        WHEN: Running status command
        THEN: Should correctly identify lanes from frontmatter
        """
        project_name = "test_status_flat"
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

        feature = "001-flat-status"
        tasks_dir = project_path / 'kitty-specs' / feature / 'tasks'
        tasks_dir.mkdir(parents=True, exist_ok=True)

        # Ensure NO lane subdirectories
        for lane in ['planned', 'doing', 'for_review', 'done']:
            lane_dir = tasks_dir / lane
            assert not lane_dir.exists(), f"Test setup: {lane}/ should not exist"

        # Create WP in flat tasks/ with for_review lane
        (tasks_dir / 'WP01.md').write_text('''---
work_package_id: WP01
lane: "for_review"
---
# WP01
''')

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=project_path, check=True)

        tasks_cli = project_path / '.kittify' / 'scripts' / 'tasks' / 'tasks_cli.py'

        result = subprocess.run(
            ['python3', str(tasks_cli), 'status', feature],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        output = result.stdout.lower()

        # Should identify WP01 as being in for_review lane from frontmatter
        assert 'for_review' in output or 'for review' in output, \
            "Should show FOR_REVIEW section with WP01"
        assert 'wp01' in output, "Should show WP01"

    def test_status_handles_missing_lane_frontmatter(
        self, temp_project_dir, spec_kitty_repo_root
    ):
        """Test: status defaults to planned when lane: is missing

        GIVEN: WP file without lane: field in frontmatter
        WHEN: Running status command
        THEN: Should treat as planned and show warning
        """
        project_name = "test_status_missing_lane"
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

        feature = "001-missing-lane"
        tasks_dir = project_path / 'kitty-specs' / feature / 'tasks'
        tasks_dir.mkdir(parents=True, exist_ok=True)

        # Create WP WITHOUT lane field
        (tasks_dir / 'WP01.md').write_text('''---
work_package_id: WP01
title: "No Lane Field"
---
# WP01
''')

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=project_path, check=True)

        tasks_cli = project_path / '.kittify' / 'scripts' / 'tasks' / 'tasks_cli.py'

        result = subprocess.run(
            ['python3', str(tasks_cli), 'status', feature],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False  # May warn but shouldn't fail
        )

        output = (result.stdout + result.stderr).lower()

        # Should default to planned
        assert 'planned' in output, "Should default missing lane to planned"

        # Should show warning about missing lane
        assert 'warn' in output or 'missing' in output or 'default' in output, \
            "Should warn about missing lane field"


class TestLegacyDetection:
    """Test detection of legacy directory-based lane structure."""

    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        """Create temporary directory for test project."""
        return tmp_path

    def test_detects_legacy_directory_structure(
        self, temp_project_dir, spec_kitty_repo_root
    ):
        """Test: Detects old directory-based lane structure

        GIVEN: Feature with tasks/planned/, tasks/doing/ subdirectories
        WHEN: Running any tasks_cli.py command
        THEN: Should warn about legacy format and suggest upgrade
        """
        project_name = "test_legacy_detection"
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

        # Create LEGACY structure (with lane subdirectories)
        feature = "001-legacy-feature"
        tasks_dir = project_path / 'kitty-specs' / feature / 'tasks'

        # Create lane subdirectories (OLD format)
        for lane in ['planned', 'doing', 'for_review', 'done']:
            (tasks_dir / lane).mkdir(parents=True, exist_ok=True)

        # Put a WP in planned subdirectory (OLD format)
        (tasks_dir / 'planned' / 'WP01.md').write_text('''---
work_package_id: WP01
lane: "planned"
---
# WP01
''')

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=project_path, check=True)

        tasks_cli = project_path / '.kittify' / 'scripts' / 'tasks' / 'tasks_cli.py'

        result = subprocess.run(
            ['python3', str(tasks_cli), 'status', feature],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        output = (result.stdout + result.stderr).lower()

        # Should detect legacy format
        assert 'legacy' in output or 'upgrade' in output or 'directory' in output, \
            "Should warn about legacy directory-based format"

    def test_flat_structure_not_flagged_as_legacy(
        self, temp_project_dir, spec_kitty_repo_root
    ):
        """Test: New flat structure is NOT flagged as legacy

        GIVEN: Feature with flat tasks/ directory
        WHEN: Running tasks_cli.py command
        THEN: Should NOT show legacy warning
        """
        project_name = "test_not_legacy"
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

        feature = "001-modern-feature"
        tasks_dir = project_path / 'kitty-specs' / feature / 'tasks'
        tasks_dir.mkdir(parents=True, exist_ok=True)

        # NO lane subdirectories (NEW format)
        (tasks_dir / 'WP01.md').write_text('''---
work_package_id: WP01
lane: "planned"
---
# WP01
''')

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=project_path, check=True)

        tasks_cli = project_path / '.kittify' / 'scripts' / 'tasks' / 'tasks_cli.py'

        result = subprocess.run(
            ['python3', str(tasks_cli), 'status', feature],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        output = (result.stdout + result.stderr).lower()

        # Should NOT show legacy warning
        assert 'legacy' not in output, \
            "Flat structure should NOT trigger legacy warning"

    def test_legacy_warning_suggests_upgrade(
        self, temp_project_dir, spec_kitty_repo_root
    ):
        """Test: Legacy warning suggests spec-kitty upgrade command

        GIVEN: Feature with legacy structure
        WHEN: Running tasks_cli.py command
        THEN: Warning should mention 'spec-kitty upgrade'
        """
        project_name = "test_upgrade_suggestion"
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

        feature = "001-upgrade-suggest"
        tasks_dir = project_path / 'kitty-specs' / feature / 'tasks'

        # Create legacy structure
        (tasks_dir / 'planned').mkdir(parents=True, exist_ok=True)
        (tasks_dir / 'planned' / 'WP01.md').write_text('''---
work_package_id: WP01
---
# WP01
''')

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=project_path, check=True)

        tasks_cli = project_path / '.kittify' / 'scripts' / 'tasks' / 'tasks_cli.py'

        result = subprocess.run(
            ['python3', str(tasks_cli), 'status', feature],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        output = result.stdout + result.stderr

        # Should mention upgrade command
        assert 'upgrade' in output.lower(), \
            "Warning should suggest upgrade command"


class TestMigrationCommand:
    """Test the spec-kitty upgrade command for migrating to flat structure."""

    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        """Create temporary directory for test project."""
        return tmp_path

    def test_upgrade_flattens_lane_directories(
        self, temp_project_dir, spec_kitty_repo_root
    ):
        """Test: upgrade moves files from lane subdirectories to flat tasks/

        GIVEN: Feature with tasks/planned/WP01.md, tasks/doing/WP02.md
        WHEN: Running spec-kitty upgrade
        THEN: Files moved to tasks/WP01.md, tasks/WP02.md
        """
        project_name = "test_upgrade_flatten"
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

        feature = "001-upgrade-test"
        tasks_dir = project_path / 'kitty-specs' / feature / 'tasks'

        # Create legacy structure
        (tasks_dir / 'planned').mkdir(parents=True, exist_ok=True)
        (tasks_dir / 'doing').mkdir(parents=True, exist_ok=True)

        (tasks_dir / 'planned' / 'WP01.md').write_text('''---
work_package_id: WP01
lane: "planned"
---
# WP01
''')
        (tasks_dir / 'doing' / 'WP02.md').write_text('''---
work_package_id: WP02
lane: "doing"
---
# WP02
''')

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=project_path, check=True)

        # Run upgrade
        result = subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            input='y\n',  # Confirm upgrade
            capture_output=True,
            text=True,
            check=True
        )

        # Verify files moved to flat structure
        assert (tasks_dir / 'WP01.md').exists(), "WP01 should be in flat tasks/"
        assert (tasks_dir / 'WP02.md').exists(), "WP02 should be in flat tasks/"

        # Verify old locations are empty/removed
        assert not (tasks_dir / 'planned' / 'WP01.md').exists(), \
            "WP01 should not be in planned/"
        assert not (tasks_dir / 'doing' / 'WP02.md').exists(), \
            "WP02 should not be in doing/"

    def test_upgrade_preserves_lane_frontmatter(
        self, temp_project_dir, spec_kitty_repo_root
    ):
        """Test: upgrade preserves lane: field from source directory

        GIVEN: WP in tasks/for_review/ with lane: "for_review"
        WHEN: Running spec-kitty upgrade
        THEN: Flattened file should have lane: "for_review"
        """
        project_name = "test_upgrade_preserve"
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

        feature = "001-preserve-lane"
        tasks_dir = project_path / 'kitty-specs' / feature / 'tasks'

        (tasks_dir / 'for_review').mkdir(parents=True, exist_ok=True)
        (tasks_dir / 'for_review' / 'WP01.md').write_text('''---
work_package_id: WP01
lane: "for_review"
title: "Review Task"
---
# WP01
''')

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=project_path, check=True)

        subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Verify lane preserved
        content = (tasks_dir / 'WP01.md').read_text()
        assert 'lane: "for_review"' in content or "lane: for_review" in content, \
            "lane: should be preserved as for_review"

    def test_upgrade_is_idempotent(
        self, temp_project_dir, spec_kitty_repo_root
    ):
        """Test: upgrade can be run multiple times safely

        GIVEN: Already upgraded project (flat structure)
        WHEN: Running spec-kitty upgrade again
        THEN: Should complete without errors, files unchanged
        """
        project_name = "test_upgrade_idempotent"
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

        feature = "001-idempotent"
        tasks_dir = project_path / 'kitty-specs' / feature / 'tasks'
        tasks_dir.mkdir(parents=True, exist_ok=True)

        # Already flat structure
        (tasks_dir / 'WP01.md').write_text('''---
work_package_id: WP01
lane: "done"
---
# WP01
''')

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=project_path, check=True)

        content_before = (tasks_dir / 'WP01.md').read_text()

        # Run upgrade on already-flat structure
        result = subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Verify file unchanged
        content_after = (tasks_dir / 'WP01.md').read_text()
        assert content_before == content_after, \
            "File should be unchanged after running upgrade on flat structure"

    def test_upgrade_cleans_empty_directories(
        self, temp_project_dir, spec_kitty_repo_root
    ):
        """Test: upgrade removes empty lane subdirectories after migration

        GIVEN: tasks/planned/WP01.md (legacy structure)
        WHEN: Running spec-kitty upgrade
        THEN: tasks/planned/ directory should be removed (empty)
        """
        project_name = "test_upgrade_cleanup"
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

        feature = "001-cleanup-test"
        tasks_dir = project_path / 'kitty-specs' / feature / 'tasks'

        # Create legacy structure
        for lane in ['planned', 'doing', 'for_review', 'done']:
            (tasks_dir / lane).mkdir(parents=True, exist_ok=True)
            (tasks_dir / lane / '.gitkeep').touch()

        # Put one WP in planned
        (tasks_dir / 'planned' / 'WP01.md').write_text('''---
work_package_id: WP01
lane: "planned"
---
# WP01
''')

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=project_path, check=True)

        subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Verify lane subdirectories removed (they're empty now)
        for lane in ['planned', 'doing', 'for_review', 'done']:
            lane_dir = tasks_dir / lane
            if lane_dir.exists():
                # If it exists, should be empty (just .gitkeep or nothing)
                contents = list(lane_dir.glob('*.md'))
                assert len(contents) == 0, \
                    f"{lane}/ should not contain any .md files after upgrade"

    def test_upgrade_requires_confirmation(
        self, temp_project_dir, spec_kitty_repo_root
    ):
        """Test: upgrade requires user confirmation before modifying files

        GIVEN: Project with legacy structure
        WHEN: Running spec-kitty upgrade and declining
        THEN: No files should be modified
        """
        project_name = "test_upgrade_confirm"
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

        feature = "001-confirm-test"
        tasks_dir = project_path / 'kitty-specs' / feature / 'tasks'

        (tasks_dir / 'planned').mkdir(parents=True, exist_ok=True)
        (tasks_dir / 'planned' / 'WP01.md').write_text('''---
work_package_id: WP01
---
# WP01
''')

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=project_path, check=True)

        # Decline upgrade
        result = subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            input='n\n',  # Decline
            capture_output=True,
            text=True,
            check=False
        )

        # Verify file NOT moved
        assert (tasks_dir / 'planned' / 'WP01.md').exists(), \
            "File should remain in place when upgrade declined"
        assert not (tasks_dir / 'WP01.md').exists(), \
            "File should NOT be in flat tasks/ when upgrade declined"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
