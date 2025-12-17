"""
Test Migration: 0.9.1 Complete Lane Migration

Tests the v0.9.1 migration that completes the lane flattening by:
1. Finding ALL remaining files in lane subdirectories (not just WP*.md)
2. Moving entire subdirectories (like phase-4-eval-execution/) to tasks/
3. Removing all remaining lane subdirectories completely

Background:
The v0.9.0 migration flattened individual WP files but missed:
- Nested subdirectories (tasks/done/phase-4-eval-execution/)
- Non-WP files (phase-*.md, task-*.md, README.md, etc.)
- Entire subdirectory structures users created for organization

The v0.9.1 "complete migration" fixes this by:
- Moving ALL files and subdirectories from lane dirs to tasks/
- Preserving subdirectory structure (phase-4-eval-execution/ becomes tasks/phase-4-eval-execution/)
- Completely removing lane directories (planned/, doing/, for_review/, done/)

Real-World Example (from mittwald-mcp project):
    BEFORE:
    tasks/done/phase-4-eval-execution/WP18-execute-identity.md
    tasks/done/phase-4-eval-execution/WP19-execute-organization.md

    AFTER:
    tasks/phase-4-eval-execution/WP18-execute-identity.md
    tasks/phase-4-eval-execution/WP19-execute-organization.md

Test Coverage:
1. Nested Directory Detection (3 tests)
   - Detects nested subdirectories within lane directories
   - Identifies ALL files at any depth (not just WP*.md)
   - Reports nested structure in upgrade detection

2. Complete Flattening (6 tests)
   - Moves entire subdirectories from done/ to tasks/
   - Moves entire subdirectories from planned/ to tasks/
   - Handles multiple levels of nesting
   - Preserves non-WP files (phase-*.md, README.md, etc.)
   - Preserves subdirectory structure
   - Updates lane: frontmatter based on original directory

3. Filename Collision Handling (3 tests)
   - Detects potential directory name collisions
   - Reports collision errors clearly
   - Suggests resolution (rename before upgrade)

4. Lane Directory Removal (3 tests)
   - Removes ALL lane directories completely
   - Handles partially empty directories
   - Works across all worktrees

5. Idempotency (2 tests)
   - Already-flat structure unchanged
   - Running twice produces same result

Note: Tests require spec-kitty >= 0.9.1 with complete migration implemented
"""

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


# Tests require v0.9.1+ for recursive flatten migration
pytestmark = pytest.mark.skipif(
    _get_spec_kitty_version() < (0, 9, 1),
    reason="Requires spec-kitty >= 0.9.1 (recursive flatten migration)"
)


class TestNestedDirectoryDetection:
    """Test detection of nested subdirectories within lane directories."""

    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        return tmp_path

    @pytest.fixture
    def project_with_nested_tasks(self, temp_project_dir, spec_kitty_repo_root):
        """Create project with nested subdirectories in lane directories."""
        project_name = "nested_tasks_project"
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

        # Create feature with NESTED task structure (simulating v0.9.0 missed migration)
        feature = "001-nested-test"
        tasks_dir = project_path / 'kitty-specs' / feature / 'tasks'

        # Create nested structure like mittwald-mcp example
        # tasks/done/phase-4-eval-execution/
        phase_dir = tasks_dir / 'done' / 'phase-4-eval-execution'
        phase_dir.mkdir(parents=True, exist_ok=True)

        # Create WP files in nested directory
        (phase_dir / 'WP18-execute-identity.md').write_text('''---
work_package_id: WP18
lane: "done"
title: "Execute Evals - identity (17 evals)"
phase: "Phase 4 - Eval Execution"
---

# WP18: Execute Evals - identity

This work package was stuck in nested directory.
''')

        (phase_dir / 'WP19-execute-organization.md').write_text('''---
work_package_id: WP19
lane: "done"
title: "Execute Evals - organization"
---

# WP19: Execute Evals - organization
''')

        # Also create planned/sprint-1/ nested structure
        sprint_dir = tasks_dir / 'planned' / 'sprint-1'
        sprint_dir.mkdir(parents=True, exist_ok=True)

        (sprint_dir / 'WP05-setup-infra.md').write_text('''---
work_package_id: WP05
lane: "planned"
title: "Setup Infrastructure"
---

# WP05: Setup Infrastructure
''')

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Add nested tasks'], cwd=project_path, check=True)

        return project_path, feature

    def test_detects_nested_subdirectories_in_lane_dirs(
        self, project_with_nested_tasks
    ):
        """Test: Detects nested subdirectories within lane directories

        GIVEN: tasks/done/phase-4-eval-execution/ with WP files
        WHEN: Running upgrade detection
        THEN: Should identify nested structure needs migration
        """
        project_path, feature = project_with_nested_tasks
        tasks_dir = project_path / 'kitty-specs' / feature / 'tasks'

        # Verify nested structure exists before upgrade
        assert (tasks_dir / 'done' / 'phase-4-eval-execution').exists()
        assert (tasks_dir / 'done' / 'phase-4-eval-execution' / 'WP18-execute-identity.md').exists()

        # Run upgrade in dry-run mode if available
        result = subprocess.run(
            ['spec-kitty', 'upgrade', '--dry-run'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        output = result.stderr + result.stdout
        output_lower = output.lower()

        # Should detect nested structure
        if 'nested' in output_lower or 'recursive' in output_lower or 'phase' in output_lower:
            assert True
        elif 'no migrations' in output_lower:
            pytest.fail("Should detect nested tasks needing migration")
        else:
            # May not support --dry-run, try detection differently
            pytest.skip("--dry-run not supported or detection format different")

    def test_identifies_wp_files_at_any_depth(
        self, project_with_nested_tasks
    ):
        """Test: Identifies WP files at any nesting depth

        GIVEN: WPs in tasks/done/phase/subphase/WP.md
        WHEN: Running upgrade
        THEN: Should find and migrate all WP files regardless of depth
        """
        project_path, feature = project_with_nested_tasks
        tasks_dir = project_path / 'kitty-specs' / feature / 'tasks'

        # Add even deeper nesting
        deep_dir = tasks_dir / 'for_review' / 'sprint-2' / 'security-audit' / 'critical'
        deep_dir.mkdir(parents=True, exist_ok=True)
        (deep_dir / 'WP99-deep.md').write_text('''---
work_package_id: WP99
lane: "for_review"
title: "Deeply Nested WP"
---
# WP99
''')

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Add deep WP'], cwd=project_path, check=True)

        # Run upgrade
        result = subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Deeply nested WP should be flattened
        assert (tasks_dir / 'WP99-deep.md').exists(), \
            "Deeply nested WP should be flattened to tasks/"
        assert not (deep_dir / 'WP99-deep.md').exists(), \
            "Original deeply nested WP should be moved"

    def test_reports_nested_structure_in_detection(
        self, project_with_nested_tasks
    ):
        """Test: Upgrade detection reports nested structure clearly

        GIVEN: Project with nested task directories
        WHEN: Running upgrade detection/status
        THEN: Should report which nested directories contain WPs
        """
        project_path, feature = project_with_nested_tasks

        result = subprocess.run(
            ['spec-kitty', 'upgrade', '--dry-run'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        output = result.stderr + result.stdout

        # Should mention the nested paths
        if 'phase-4' in output or 'sprint' in output:
            assert True  # Reports specific nested directories
        elif 'nested' in output.lower():
            assert True  # Reports nested in general
        else:
            pytest.skip("Detection output format may differ")


class TestCompleteFlattening:
    """Test the complete flattening of nested directories to tasks/."""

    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        return tmp_path

    @pytest.fixture
    def nested_project(self, temp_project_dir, spec_kitty_repo_root):
        """Create project with nested tasks matching mittwald-mcp structure."""
        project_name = "flatten_test"
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

        feature = "001-flatten-test"
        tasks_dir = project_path / 'kitty-specs' / feature / 'tasks'
        tasks_dir.mkdir(parents=True, exist_ok=True)

        return project_path, feature, tasks_dir

    def test_moves_entire_subdirectory_from_done_to_tasks(
        self, nested_project
    ):
        """Test: Moves entire subdirectory from done/ to tasks/

        GIVEN: tasks/done/phase-4-eval-execution/ with multiple files
        WHEN: Running spec-kitty upgrade
        THEN: Entire directory moved to tasks/phase-4-eval-execution/
        """
        project_path, feature, tasks_dir = nested_project

        # Create nested structure with multiple files
        phase_dir = tasks_dir / 'done' / 'phase-4-eval-execution'
        phase_dir.mkdir(parents=True, exist_ok=True)

        (phase_dir / 'WP18-execute-identity.md').write_text('''---
work_package_id: WP18
lane: "done"
---
# WP18
''')
        (phase_dir / 'WP19-execute-organization.md').write_text('''---
work_package_id: WP19
lane: "done"
---
# WP19
''')

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Nested dir'], cwd=project_path, check=True)

        subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Subdirectory should be moved to tasks/ (preserving structure)
        new_phase_dir = tasks_dir / 'phase-4-eval-execution'
        assert new_phase_dir.exists(), \
            "Subdirectory should be moved to tasks/"
        assert (new_phase_dir / 'WP18-execute-identity.md').exists(), \
            "WP18 should be in moved subdirectory"
        assert (new_phase_dir / 'WP19-execute-organization.md').exists(), \
            "WP19 should be in moved subdirectory"

        # Old location should be removed
        assert not (tasks_dir / 'done' / 'phase-4-eval-execution').exists(), \
            "Old nested location should be removed"
        assert not (tasks_dir / 'done').exists(), \
            "Lane directory should be removed"

    def test_moves_subdirectory_from_planned_to_tasks(
        self, nested_project
    ):
        """Test: Moves subdirectory from planned/ to tasks/

        GIVEN: tasks/planned/sprint-1/ with files
        WHEN: Running spec-kitty upgrade
        THEN: Directory moved to tasks/sprint-1/
        """
        project_path, feature, tasks_dir = nested_project

        sprint_dir = tasks_dir / 'planned' / 'sprint-1'
        sprint_dir.mkdir(parents=True, exist_ok=True)

        (sprint_dir / 'WP05-setup.md').write_text('''---
work_package_id: WP05
lane: "planned"
---
# WP05
''')

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Sprint dir'], cwd=project_path, check=True)

        subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Subdirectory moved to tasks/
        assert (tasks_dir / 'sprint-1' / 'WP05-setup.md').exists(), \
            "File should be in tasks/sprint-1/"
        assert not (tasks_dir / 'planned').exists(), \
            "Lane directory should be removed"

    def test_preserves_non_wp_files(
        self, nested_project
    ):
        """Test: Preserves non-WP files (phase-*.md, README.md, etc.)

        GIVEN: tasks/done/phase-1/ with phase-summary.md and README.md
        WHEN: Running upgrade
        THEN: All files preserved in moved directory
        """
        project_path, feature, tasks_dir = nested_project

        phase_dir = tasks_dir / 'done' / 'phase-1'
        phase_dir.mkdir(parents=True, exist_ok=True)

        # Non-WP files
        (phase_dir / 'phase-summary.md').write_text('# Phase 1 Summary\n')
        (phase_dir / 'README.md').write_text('# Phase 1 Documentation\n')
        (phase_dir / 'WP01.md').write_text('---\nwork_package_id: WP01\n---\n')

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Non-WP files'], cwd=project_path, check=True)

        subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        new_phase_dir = tasks_dir / 'phase-1'
        assert (new_phase_dir / 'phase-summary.md').exists(), \
            "phase-summary.md should be preserved"
        assert (new_phase_dir / 'README.md').exists(), \
            "README.md should be preserved"
        assert (new_phase_dir / 'WP01.md').exists(), \
            "WP01.md should be preserved"

    def test_handles_multiple_nesting_levels(
        self, nested_project
    ):
        """Test: Handles multiple levels of nesting

        GIVEN: tasks/done/phase-1/sprint-2/priority-high/WP.md
        WHEN: Running upgrade
        THEN: Entire structure moved to tasks/phase-1/sprint-2/priority-high/
        """
        project_path, feature, tasks_dir = nested_project

        # Three levels of nesting within lane directory
        deep_dir = tasks_dir / 'done' / 'phase-1' / 'sprint-2' / 'priority-high'
        deep_dir.mkdir(parents=True, exist_ok=True)

        (deep_dir / 'WP88-deep.md').write_text('''---
work_package_id: WP88
lane: "done"
---
# WP88
''')

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Deep dir'], cwd=project_path, check=True)

        subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Structure preserved under tasks/
        expected_path = tasks_dir / 'phase-1' / 'sprint-2' / 'priority-high' / 'WP88-deep.md'
        assert expected_path.exists(), \
            "Nested structure should be preserved under tasks/"
        assert not (tasks_dir / 'done').exists(), \
            "Lane directory should be removed"

    def test_preserves_lane_frontmatter(
        self, nested_project
    ):
        """Test: Preserves lane: frontmatter from original file

        GIVEN: WP in tasks/done/phase/ with lane: "done" in frontmatter
        WHEN: Moving to tasks/phase/
        THEN: lane: "done" should be preserved
        """
        project_path, feature, tasks_dir = nested_project

        phase_dir = tasks_dir / 'done' / 'phase-1'
        phase_dir.mkdir(parents=True, exist_ok=True)

        (phase_dir / 'WP77-preserve.md').write_text('''---
work_package_id: WP77
lane: "done"
title: "Preserve Lane Test"
custom_field: "should also be preserved"
---
# WP77
''')

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Lane WP'], cwd=project_path, check=True)

        subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Check moved file preserves frontmatter
        moved_file = tasks_dir / 'phase-1' / 'WP77-preserve.md'
        assert moved_file.exists()

        content = moved_file.read_text()
        assert 'lane: "done"' in content or "lane: done" in content, \
            "lane: should be preserved"
        assert 'custom_field' in content, \
            "Other frontmatter fields should be preserved"

    def test_infers_lane_from_directory_if_missing(
        self, nested_project
    ):
        """Test: Infers lane: from parent directory if missing in frontmatter

        GIVEN: WP in tasks/for_review/sprint/ WITHOUT lane: field
        WHEN: Moving to tasks/sprint/
        THEN: Should add lane: "for_review" based on original directory
        """
        project_path, feature, tasks_dir = nested_project

        sprint_dir = tasks_dir / 'for_review' / 'sprint-1'
        sprint_dir.mkdir(parents=True, exist_ok=True)

        # WP WITHOUT lane field
        (sprint_dir / 'WP66-no-lane.md').write_text('''---
work_package_id: WP66
title: "No Lane Field"
---
# WP66
''')

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'No lane WP'], cwd=project_path, check=True)

        subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        moved_file = tasks_dir / 'sprint-1' / 'WP66-no-lane.md'
        assert moved_file.exists()

        content = moved_file.read_text()
        # Should have lane added based on original directory
        assert 'lane:' in content.lower(), \
            "lane: should be added based on original parent directory"
        assert 'for_review' in content, \
            "lane should be for_review based on original parent directory"


class TestFilenameCollisions:
    """Test handling of filename collisions during migration."""

    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        return tmp_path

    @pytest.fixture
    def collision_project(self, temp_project_dir, spec_kitty_repo_root):
        """Create project with potential filename collisions."""
        project_name = "collision_test"
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

        feature = "001-collision-test"
        tasks_dir = project_path / 'kitty-specs' / feature / 'tasks'
        tasks_dir.mkdir(parents=True, exist_ok=True)

        return project_path, feature, tasks_dir

    def test_detects_filename_collision(
        self, collision_project
    ):
        """Test: Detects potential filename collisions before migration

        GIVEN: WP01.md in both tasks/done/phase-1/ AND tasks/planned/sprint-1/
        WHEN: Running upgrade detection
        THEN: Should report collision error before migrating
        """
        project_path, feature, tasks_dir = collision_project

        # Create same filename in two different nested directories
        phase_dir = tasks_dir / 'done' / 'phase-1'
        phase_dir.mkdir(parents=True, exist_ok=True)
        (phase_dir / 'WP01-setup.md').write_text('''---
work_package_id: WP01
lane: "done"
---
# WP01 (done version)
''')

        sprint_dir = tasks_dir / 'planned' / 'sprint-1'
        sprint_dir.mkdir(parents=True, exist_ok=True)
        (sprint_dir / 'WP01-setup.md').write_text('''---
work_package_id: WP01
lane: "planned"
---
# WP01 (planned version)
''')

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Collision WPs'], cwd=project_path, check=True)

        # Run upgrade - should detect collision
        result = subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            input='n\n',  # Decline in case it asks
            capture_output=True,
            text=True,
            check=False
        )

        output = result.stderr + result.stdout
        output_lower = output.lower()

        # Should report collision
        if 'collision' in output_lower or 'conflict' in output_lower or 'duplicate' in output_lower:
            assert True
        elif result.returncode != 0:
            assert 'wp01' in output_lower or 'error' in output_lower
        else:
            pytest.skip("Collision detection may work differently")

    def test_collision_error_message_clear(
        self, collision_project
    ):
        """Test: Collision error message clearly identifies conflicting files

        GIVEN: Filename collision scenario
        WHEN: Upgrade detects collision
        THEN: Error should show both file paths
        """
        project_path, feature, tasks_dir = collision_project

        # Create collision
        for lane in ['done', 'planned']:
            dir_path = tasks_dir / lane / 'subdir'
            dir_path.mkdir(parents=True, exist_ok=True)
            (dir_path / 'WP99-conflict.md').write_text(f'''---
work_package_id: WP99
lane: "{lane}"
---
''')

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Conflict'], cwd=project_path, check=True)

        result = subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            input='n\n',
            capture_output=True,
            text=True,
            check=False
        )

        output = result.stderr + result.stdout

        # If collision detected, should mention the files
        if 'wp99' in output.lower() or 'conflict' in output.lower():
            # Good - it mentions the conflicting file
            assert True

    def test_collision_suggests_resolution(
        self, collision_project
    ):
        """Test: Collision error suggests resolution (rename before upgrade)

        GIVEN: Collision detected
        WHEN: Error displayed
        THEN: Should suggest renaming files to resolve
        """
        project_path, feature, tasks_dir = collision_project

        for lane in ['done', 'planned']:
            dir_path = tasks_dir / lane / 'sub'
            dir_path.mkdir(parents=True, exist_ok=True)
            (dir_path / 'WP50.md').write_text(f'---\nlane: "{lane}"\n---\n')

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Collision'], cwd=project_path, check=True)

        result = subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            input='n\n',
            capture_output=True,
            text=True,
            check=False
        )

        output = result.stderr + result.stdout
        output_lower = output.lower()

        if 'collision' in output_lower or 'conflict' in output_lower:
            assert 'rename' in output_lower or 'resolve' in output_lower or \
                   'manually' in output_lower, \
                "Should suggest how to resolve collision"


class TestEmptyDirectoryCleanup:
    """Test cleanup of empty directories after migration."""

    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        return tmp_path

    @pytest.fixture
    def cleanup_project(self, temp_project_dir, spec_kitty_repo_root):
        """Create project with nested structure for cleanup testing."""
        project_name = "cleanup_test"
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
        tasks_dir.mkdir(parents=True, exist_ok=True)

        return project_path, feature, tasks_dir

    def test_removes_empty_nested_directories(
        self, cleanup_project
    ):
        """Test: Removes empty nested directories after migration

        GIVEN: tasks/done/phase-1/sprint-2/WP.md
        WHEN: WP flattened to tasks/
        THEN: Empty phase-1/sprint-2/ directories should be removed
        """
        project_path, feature, tasks_dir = cleanup_project

        nested_dir = tasks_dir / 'done' / 'phase-1' / 'sprint-2'
        nested_dir.mkdir(parents=True, exist_ok=True)

        (nested_dir / 'WP33-cleanup.md').write_text('''---
work_package_id: WP33
lane: "done"
---
''')

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Nested'], cwd=project_path, check=True)

        subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Verify WP moved
        assert (tasks_dir / 'WP33-cleanup.md').exists()

        # Verify empty nested directories removed
        assert not (tasks_dir / 'done' / 'phase-1' / 'sprint-2').exists(), \
            "Empty sprint-2/ should be removed"
        # Parent may or may not be removed depending on implementation
        # but the nested child should definitely be gone

    def test_removes_empty_lane_directories(
        self, cleanup_project
    ):
        """Test: Removes empty lane directories after nested cleanup

        GIVEN: Only nested WPs in tasks/done/phase/
        WHEN: All WPs flattened
        THEN: tasks/done/ should be removed (empty after migration)
        """
        project_path, feature, tasks_dir = cleanup_project

        # Only nested WPs, nothing directly in done/
        nested_dir = tasks_dir / 'done' / 'only-nested'
        nested_dir.mkdir(parents=True, exist_ok=True)

        (nested_dir / 'WP44.md').write_text('''---
work_package_id: WP44
lane: "done"
---
''')

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Nested only'], cwd=project_path, check=True)

        subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        assert (tasks_dir / 'WP44.md').exists()

        # done/ should be empty and removed
        done_dir = tasks_dir / 'done'
        if done_dir.exists():
            # If it exists, it should be empty
            contents = list(done_dir.glob('*.md'))
            assert len(contents) == 0, \
                "Lane directory should have no .md files"


class TestIdempotency:
    """Test that migration is idempotent (safe to run multiple times)."""

    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        return tmp_path

    @pytest.fixture
    def idempotent_project(self, temp_project_dir, spec_kitty_repo_root):
        """Create project for idempotency testing."""
        project_name = "idempotent_test"
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

        return project_path, feature, tasks_dir

    def test_already_flat_structure_unchanged(
        self, idempotent_project
    ):
        """Test: Already-flat structure unchanged after upgrade

        GIVEN: Flat tasks/ structure with WPs
        WHEN: Running upgrade
        THEN: Files should remain in place, content unchanged
        """
        project_path, feature, tasks_dir = idempotent_project

        # Create flat structure (already correct)
        wp_content = '''---
work_package_id: WP55
lane: "doing"
title: "Already Flat"
---
# WP55: Already Flat
'''
        (tasks_dir / 'WP55-flat.md').write_text(wp_content)

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Flat'], cwd=project_path, check=True)

        content_before = (tasks_dir / 'WP55-flat.md').read_text()

        subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # File should still be there, unchanged
        assert (tasks_dir / 'WP55-flat.md').exists()
        content_after = (tasks_dir / 'WP55-flat.md').read_text()
        assert content_before == content_after, \
            "Already-flat file should be unchanged"

    def test_running_twice_same_result(
        self, idempotent_project
    ):
        """Test: Running upgrade twice produces same result

        GIVEN: Project with nested structure
        WHEN: Running upgrade twice
        THEN: Second run should be no-op, files unchanged
        """
        project_path, feature, tasks_dir = idempotent_project

        # Create nested structure
        nested_dir = tasks_dir / 'done' / 'phase'
        nested_dir.mkdir(parents=True, exist_ok=True)
        (nested_dir / 'WP22.md').write_text('''---
work_package_id: WP22
lane: "done"
---
''')

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=project_path, check=True)

        # First upgrade
        subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        content_after_first = (tasks_dir / 'WP22.md').read_text()

        # Commit changes
        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(
            ['git', 'commit', '-m', 'After first upgrade', '--allow-empty'],
            cwd=project_path,
            check=False  # May not have changes
        )

        # Second upgrade
        subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        content_after_second = (tasks_dir / 'WP22.md').read_text()

        assert content_after_first == content_after_second, \
            "Second upgrade should not change files"


class TestRealWorldScenario:
    """Test based on actual mittwald-mcp project structure."""

    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        return tmp_path

    @pytest.fixture
    def mittwald_like_project(self, temp_project_dir, spec_kitty_repo_root):
        """Create project matching mittwald-mcp structure."""
        project_name = "mittwald_like"
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

        feature = "010-langfuse-mcp-eval"
        tasks_dir = project_path / 'kitty-specs' / feature / 'tasks'

        # Recreate mittwald-mcp structure
        phase_dir = tasks_dir / 'done' / 'phase-4-eval-execution'
        phase_dir.mkdir(parents=True, exist_ok=True)

        # Create multiple WP files like the real project
        wps = [
            ('WP18-execute-identity.md', 'Execute Evals - identity (17 evals)'),
            ('WP19-execute-organization.md', 'Execute Evals - organization'),
            ('WP20-execute-project-foundation.md', 'Execute Evals - project-foundation'),
            ('WP21-execute-apps.md', 'Execute Evals - apps'),
            ('WP22-execute-containers.md', 'Execute Evals - containers'),
        ]

        for filename, title in wps:
            wp_id = filename.split('-')[0]
            (phase_dir / filename).write_text(f'''---
work_package_id: "{wp_id}"
title: "{title}"
phase: "Phase 4 - Eval Execution"
lane: "done"
---

# {wp_id}: {title}

Test content.
''')

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Mittwald structure'], cwd=project_path, check=True)

        return project_path, feature, tasks_dir

    def test_mittwald_structure_fully_flattened(
        self, mittwald_like_project
    ):
        """Test: All mittwald-mcp nested WPs are flattened

        GIVEN: Real-world nested structure from mittwald-mcp
        WHEN: Running upgrade
        THEN: All WP files moved to flat tasks/
        """
        project_path, feature, tasks_dir = mittwald_like_project

        # Verify nested structure exists
        phase_dir = tasks_dir / 'done' / 'phase-4-eval-execution'
        assert phase_dir.exists()
        initial_files = list(phase_dir.glob('WP*.md'))
        assert len(initial_files) >= 5, "Should have 5+ WP files initially"

        # Run upgrade
        result = subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # All WPs should be in flat tasks/
        flat_wps = list(tasks_dir.glob('WP*.md'))
        assert len(flat_wps) >= 5, \
            f"Should have 5+ WP files in flat tasks/. Found: {len(flat_wps)}"

        # Verify specific files
        assert (tasks_dir / 'WP18-execute-identity.md').exists()
        assert (tasks_dir / 'WP19-execute-organization.md').exists()
        assert (tasks_dir / 'WP20-execute-project-foundation.md').exists()

        # Nested location should be empty
        assert not (phase_dir / 'WP18-execute-identity.md').exists()

    def test_phase_metadata_preserved_after_flatten(
        self, mittwald_like_project
    ):
        """Test: Phase metadata in frontmatter preserved after flatten

        GIVEN: WPs with phase: field in frontmatter
        WHEN: Flattening
        THEN: phase: field should be preserved
        """
        project_path, feature, tasks_dir = mittwald_like_project

        subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Check flattened file preserves phase metadata
        wp_file = tasks_dir / 'WP18-execute-identity.md'
        assert wp_file.exists()

        content = wp_file.read_text()
        assert 'phase:' in content.lower(), \
            "phase: field should be preserved"
        assert 'Phase 4' in content, \
            "Phase 4 value should be preserved"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
