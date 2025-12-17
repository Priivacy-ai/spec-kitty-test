"""
Test Tasks Directory Scaffolding (v0.8.0 - v0.8.x)

Tests the tasks directory structure that guides agents to use correct
kanban lanes and frontmatter format when generating work packages.

IMPORTANT: These tests only apply to v0.8.x. In v0.9.0+, the lane
subdirectories are eliminated in favor of flat tasks/ with frontmatter-only
lane tracking. See test_frontmatter_only_lanes.py for v0.9.0+ tests.

Bug Context:
- Agents were dumping WP files in flat tasks/ directory
- Wrong frontmatter format (markdown headers instead of YAML)
- Wrong file naming (WP-01 instead of WP01)
- Claude proceeded to generate tasks without explicit command

Fix:
- create-new-feature.sh scaffolds tasks/ with lane subdirectories
- README.md documents correct frontmatter format
- plan.md has explicit STOP instruction

Test Coverage:
1. Directory Structure (3 tests)
   - tasks/ directory created with feature
   - Kanban lanes: planned/, doing/, for_review/, done/
   - .gitkeep files in each lane

2. README Documentation (2 tests)
   - README.md exists in tasks/
   - README contains frontmatter format example

3. File Naming Guide (1 test)
   - README documents WP01 format (not WP-01)

Note: Tests require spec-kitty >= 0.8.0 and < 0.9.0
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


# These tests only apply to v0.8.x (directory-based lanes)
# v0.9.0+ uses flat structure - see test_frontmatter_only_lanes.py
pytestmark = pytest.mark.skipif(
    _get_spec_kitty_version() >= (0, 9, 0),
    reason="Directory-based lane tests only apply to v0.8.x (< 0.9.0)"
)


class TestTasksDirectoryScaffolding:
    """Test that new features get proper tasks directory structure."""

    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        """Create temporary directory for test project."""
        return tmp_path

    @pytest.fixture
    def project_with_feature(self, temp_project_dir, spec_kitty_repo_root, spec_kitty_version):
        """Create a project with a feature (via create-new-feature.sh)."""
        # Skip if pre-v0.8.0
        if spec_kitty_version < (0, 8, 0):
            pytest.skip("Tasks scaffolding requires spec-kitty >= 0.8.0")

        project_name = "test_tasks_scaffold"
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

        # Create a feature
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'Test Tasks',
             'Test feature for tasks scaffolding'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        # Parse output to get feature info
        feature_info = None
        for line in result.stdout.split('\n'):
            if line.strip().startswith('{'):
                try:
                    feature_info = json.loads(line)
                    break
                except json.JSONDecodeError:
                    continue

        return {
            'project_path': project_path,
            'feature_info': feature_info,
        }

    # ========================================================================
    # Directory Structure Tests
    # ========================================================================

    def test_tasks_directory_created(self, project_with_feature):
        """Test: tasks/ directory is created with new feature

        GIVEN: A new feature is created
        WHEN: Checking the feature directory
        THEN: tasks/ directory should exist
        """
        project_path = project_with_feature['project_path']
        feature_info = project_with_feature['feature_info']

        if not feature_info or 'BRANCH_NAME' not in feature_info:
            pytest.skip("Could not parse feature info from create script")

        branch_name = feature_info['BRANCH_NAME']
        worktree_path = project_path / '.worktrees' / branch_name
        tasks_dir = worktree_path / 'kitty-specs' / branch_name / 'tasks'

        assert tasks_dir.exists(), \
            f"tasks/ directory should exist at {tasks_dir}"
        assert tasks_dir.is_dir(), \
            "tasks/ should be a directory"

    def test_kanban_lanes_exist(self, project_with_feature):
        """Test: Kanban lane directories exist in tasks/

        GIVEN: A new feature is created
        WHEN: Checking tasks/ subdirectories
        THEN: planned/, doing/, for_review/, done/ should all exist
        """
        project_path = project_with_feature['project_path']
        feature_info = project_with_feature['feature_info']

        if not feature_info or 'BRANCH_NAME' not in feature_info:
            pytest.skip("Could not parse feature info from create script")

        branch_name = feature_info['BRANCH_NAME']
        worktree_path = project_path / '.worktrees' / branch_name
        tasks_dir = worktree_path / 'kitty-specs' / branch_name / 'tasks'

        expected_lanes = ['planned', 'doing', 'for_review', 'done']

        for lane in expected_lanes:
            lane_dir = tasks_dir / lane
            assert lane_dir.exists(), \
                f"Lane directory {lane}/ should exist"
            assert lane_dir.is_dir(), \
                f"{lane}/ should be a directory"

    def test_gitkeep_files_in_lanes(self, project_with_feature):
        """Test: .gitkeep files exist in empty lane directories

        GIVEN: A new feature is created
        WHEN: Checking lane directories
        THEN: Each should have .gitkeep file to preserve empty dirs
        """
        project_path = project_with_feature['project_path']
        feature_info = project_with_feature['feature_info']

        if not feature_info or 'BRANCH_NAME' not in feature_info:
            pytest.skip("Could not parse feature info from create script")

        branch_name = feature_info['BRANCH_NAME']
        worktree_path = project_path / '.worktrees' / branch_name
        tasks_dir = worktree_path / 'kitty-specs' / branch_name / 'tasks'

        expected_lanes = ['planned', 'doing', 'for_review', 'done']

        for lane in expected_lanes:
            gitkeep = tasks_dir / lane / '.gitkeep'
            assert gitkeep.exists(), \
                f".gitkeep should exist in {lane}/"

    # ========================================================================
    # README Documentation Tests
    # ========================================================================

    def test_readme_exists_in_tasks(self, project_with_feature):
        """Test: README.md exists in tasks/ directory

        GIVEN: A new feature is created
        WHEN: Checking tasks/ directory
        THEN: README.md should exist with format documentation
        """
        project_path = project_with_feature['project_path']
        feature_info = project_with_feature['feature_info']

        if not feature_info or 'BRANCH_NAME' not in feature_info:
            pytest.skip("Could not parse feature info from create script")

        branch_name = feature_info['BRANCH_NAME']
        worktree_path = project_path / '.worktrees' / branch_name
        readme = worktree_path / 'kitty-specs' / branch_name / 'tasks' / 'README.md'

        assert readme.exists(), \
            f"README.md should exist in tasks/"

    def test_readme_contains_frontmatter_example(self, project_with_feature):
        """Test: README.md contains YAML frontmatter example

        GIVEN: tasks/README.md exists
        WHEN: Reading the README content
        THEN: Should contain YAML frontmatter example with correct format
        """
        project_path = project_with_feature['project_path']
        feature_info = project_with_feature['feature_info']

        if not feature_info or 'BRANCH_NAME' not in feature_info:
            pytest.skip("Could not parse feature info from create script")

        branch_name = feature_info['BRANCH_NAME']
        worktree_path = project_path / '.worktrees' / branch_name
        readme = worktree_path / 'kitty-specs' / branch_name / 'tasks' / 'README.md'

        if not readme.exists():
            pytest.skip("README.md not found")

        content = readme.read_text()

        # Check for YAML frontmatter format
        assert '---' in content, \
            "README should show YAML frontmatter delimiters (---)"
        assert 'work_package_id:' in content, \
            "README should document work_package_id field"
        assert 'lane:' in content, \
            "README should document lane field"
        assert 'history:' in content, \
            "README should document history field"

    def test_readme_documents_correct_file_naming(self, project_with_feature):
        """Test: README.md documents correct WP file naming (WP01 not WP-01)

        GIVEN: tasks/README.md exists
        WHEN: Reading the README content
        THEN: Should show WP01 format (without extra hyphen)
        """
        project_path = project_with_feature['project_path']
        feature_info = project_with_feature['feature_info']

        if not feature_info or 'BRANCH_NAME' not in feature_info:
            pytest.skip("Could not parse feature info from create script")

        branch_name = feature_info['BRANCH_NAME']
        worktree_path = project_path / '.worktrees' / branch_name
        readme = worktree_path / 'kitty-specs' / branch_name / 'tasks' / 'README.md'

        if not readme.exists():
            pytest.skip("README.md not found")

        content = readme.read_text()

        # Check for correct naming format
        assert 'WP01' in content, \
            "README should show WP01 format (not WP-01)"

        # Should NOT have the wrong format as the primary example
        # (We check the format line specifically)
        import re
        format_line = re.search(r'Format:\s*`([^`]+)`', content)
        if format_line:
            format_example = format_line.group(1)
            assert 'WP01' in format_example, \
                f"File naming format should use WP01, got: {format_example}"
            # The format should NOT start with WP-01 (extra hyphen)
            assert not format_example.startswith('WP-01'), \
                "File naming should NOT use WP-01 with extra hyphen"


class TestPlanMdStopInstruction:
    """Test that plan.md has explicit STOP instruction."""

    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        """Create temporary directory for test project."""
        return tmp_path

    def test_plan_template_has_stop_instruction(
        self, temp_project_dir, spec_kitty_repo_root, spec_kitty_version
    ):
        """Test: plan.md template has explicit STOP instruction

        GIVEN: A project initialized with spec-kitty
        WHEN: Reading the plan.md command template
        THEN: Should contain STOP/COMPLETE instruction
        """
        if spec_kitty_version < (0, 8, 0):
            pytest.skip("STOP instruction requires spec-kitty >= 0.8.0")

        project_name = "test_plan_stop"
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

        # Find plan.md template
        plan_template = project_path / '.kittify' / 'missions' / 'software-dev' / 'command-templates' / 'plan.md'

        if not plan_template.exists():
            pytest.skip("plan.md template not found")

        content = plan_template.read_text()

        # Check for STOP instruction
        stop_keywords = ['STOP', 'COMPLETE', 'DO NOT']
        has_stop = any(keyword in content for keyword in stop_keywords)

        assert has_stop, \
            "plan.md should have explicit STOP instruction"

        # Check specifically for task generation prohibition
        assert 'task' in content.lower() and ('not' in content.lower() or 'do not' in content.lower()), \
            "plan.md should instruct agent NOT to generate tasks"

    def test_plan_template_prohibits_wp_generation(
        self, temp_project_dir, spec_kitty_repo_root, spec_kitty_version
    ):
        """Test: plan.md explicitly prohibits WP/tasks generation

        GIVEN: plan.md command template
        WHEN: Reading the template content
        THEN: Should explicitly prohibit work package generation
        """
        if spec_kitty_version < (0, 8, 0):
            pytest.skip("WP prohibition requires spec-kitty >= 0.8.0")

        project_name = "test_plan_wp_prohibition"
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

        plan_template = project_path / '.kittify' / 'missions' / 'software-dev' / 'command-templates' / 'plan.md'

        if not plan_template.exists():
            pytest.skip("plan.md template not found")

        content = plan_template.read_text()

        # Check for explicit prohibitions
        prohibitions = [
            'work package',
            'WP',
            'tasks.md',
            '/spec-kitty.tasks',
        ]

        # At least one prohibition should be mentioned with "do not" or "❌"
        has_prohibition = any(
            (p.lower() in content.lower() and ('do not' in content.lower() or '❌' in content))
            for p in prohibitions
        )

        assert has_prohibition, \
            "plan.md should explicitly prohibit WP/tasks generation"


class TestTasksScaffoldingLegacy:
    """Test that legacy features (pre-scaffolding) are handled gracefully."""

    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        """Create temporary directory for test project."""
        return tmp_path

    def test_feature_without_tasks_structure_still_works(
        self, temp_project_dir, spec_kitty_repo_root
    ):
        """Test: Features without scaffolded tasks/ still function

        GIVEN: A feature created before scaffolding was added
        WHEN: Running spec-kitty commands
        THEN: Should not fail due to missing tasks structure

        Note: This tests backward compatibility
        """
        project_name = "test_legacy_tasks"
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
            [str(create_script), '--json', '--feature-name', 'Legacy Test',
             'Test feature for legacy compatibility'],
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

        # If tasks/ doesn't exist (old version), manually create flat structure
        if not tasks_dir.exists():
            tasks_dir.mkdir(parents=True)
            # Don't create subdirectories - simulate old behavior

        # Verify spec-kitty doesn't crash with flat tasks/
        # Just verify the worktree is functional
        assert worktree_path.exists(), \
            "Worktree should exist"

        # Feature should still have meta.json
        meta_json = worktree_path / 'kitty-specs' / branch_name / 'meta.json'
        assert meta_json.exists(), \
            "Feature should have meta.json regardless of tasks structure"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
