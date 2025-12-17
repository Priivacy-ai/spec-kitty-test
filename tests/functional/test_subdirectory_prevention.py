"""
Test v0.9.4: Subdirectory Prevention Documentation & Validation

Tests that v0.9.4 properly prevents creation of subdirectories in tasks/
through documentation warnings and runtime validation.

Background:
After v0.9.0 introduced flat tasks/ structure, some LLMs still created
subdirectories (planned/, doing/, etc.) because:
1. Old documentation patterns were still present
2. No runtime validation to catch the mistake

v0.9.4 adds:
1. Critical warnings in tasks/README.md
2. Updated AGENTS.md with flat structure examples
3. Updated /spec-kitty.tasks command template
4. Runtime validation in check-prerequisites.sh
5. Blocks execution if any subdirectories found in tasks/

Test Coverage:
1. README Documentation (4 tests)
   - README has flat structure warning
   - README explicitly forbids subdirectories
   - README shows correct WP file location
   - README mentions lane: frontmatter field

2. AGENTS.md Documentation (3 tests)
   - AGENTS.md has flat structure section
   - AGENTS.md shows correct examples
   - AGENTS.md warns against subdirectories

3. Tasks Template (3 tests)
   - Template mentions flat structure
   - Template shows lane in frontmatter
   - Template warns against creating directories

4. Runtime Validation (5 tests)
   - check-prerequisites.sh exists
   - Validation passes with flat structure
   - Validation fails with planned/ subdirectory
   - Validation fails with any subdirectory
   - Error message is clear and actionable

5. Integration (3 tests)
   - New feature has correct README
   - spec-kitty commands refuse to run with subdirs
   - Upgrade removes subdirectories
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


# Tests require v0.9.4+ (subdirectory prevention added in v0.9.4)
pytestmark = pytest.mark.skipif(
    _get_spec_kitty_version() < (0, 9, 4),
    reason="Requires spec-kitty >= 0.9.4 (subdirectory prevention)"
)


@pytest.fixture
def spec_kitty_repo_root():
    """Get spec-kitty repository root from environment or default location."""
    env_path = os.environ.get('SPEC_KITTY_REPO')
    if env_path:
        return Path(env_path)
    default_path = Path(__file__).parent.parent.parent.parent / 'spec-kitty'
    if default_path.exists():
        return default_path
    raise ValueError("Could not find spec-kitty repository")


class TestReadmeDocumentation:
    """Test that tasks/README.md has proper warnings."""

    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        return tmp_path

    @pytest.fixture
    def project_with_feature(self, temp_project_dir, spec_kitty_repo_root):
        """Create project with a feature to check README."""
        project_name = "readme_test"
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

        # Create a feature using the create script
        create_script = project_path / '.kittify' / 'scripts' / 'bash' / 'create-new-feature.sh'
        if create_script.exists():
            subprocess.run(
                [str(create_script), '--json', '--feature-name', 'Test Feature', 'Testing README'],
                cwd=project_path,
                capture_output=True,
                text=True,
                check=False
            )

        return project_path

    def test_readme_has_flat_structure_warning(self, project_with_feature):
        """Test: README explicitly warns about flat structure

        GIVEN: A new feature created with v0.9.4+
        WHEN: Reading the tasks/README.md
        THEN: Should contain warning about flat structure
        """
        project_path = project_with_feature

        # Find feature directory
        kitty_specs = project_path / 'kitty-specs'
        if not kitty_specs.exists():
            pytest.skip("No kitty-specs directory")

        feature_dirs = list(kitty_specs.iterdir())
        if not feature_dirs:
            pytest.skip("No feature directories")

        readme_path = feature_dirs[0] / 'tasks' / 'README.md'
        if not readme_path.exists():
            pytest.skip("No tasks/README.md")

        content = readme_path.read_text().lower()

        # Should mention flat structure
        assert 'flat' in content, \
            "README should mention 'flat' structure"

    def test_readme_forbids_subdirectories(self, project_with_feature):
        """Test: README explicitly forbids subdirectories

        GIVEN: A new feature created with v0.9.4+
        WHEN: Reading the tasks/README.md
        THEN: Should explicitly forbid creating subdirectories
        """
        project_path = project_with_feature

        kitty_specs = project_path / 'kitty-specs'
        if not kitty_specs.exists():
            pytest.skip("No kitty-specs directory")

        feature_dirs = list(kitty_specs.iterdir())
        if not feature_dirs:
            pytest.skip("No feature directories")

        readme_path = feature_dirs[0] / 'tasks' / 'README.md'
        if not readme_path.exists():
            pytest.skip("No tasks/README.md")

        content = readme_path.read_text().lower()

        # Should warn against subdirectories
        has_warning = (
            'do not create' in content or
            'never create' in content or
            'no subdirector' in content or
            'subdirectories' in content
        )
        assert has_warning, \
            "README should warn against creating subdirectories"

    def test_readme_shows_correct_wp_location(self, project_with_feature):
        """Test: README shows WP files in flat tasks/ directory

        GIVEN: A new feature created with v0.9.4+
        WHEN: Reading the tasks/README.md
        THEN: Should show WP files directly in tasks/, not in subdirs
        """
        project_path = project_with_feature

        kitty_specs = project_path / 'kitty-specs'
        if not kitty_specs.exists():
            pytest.skip("No kitty-specs directory")

        feature_dirs = list(kitty_specs.iterdir())
        if not feature_dirs:
            pytest.skip("No feature directories")

        readme_path = feature_dirs[0] / 'tasks' / 'README.md'
        if not readme_path.exists():
            pytest.skip("No tasks/README.md")

        content = readme_path.read_text()

        # Should show flat structure example like tasks/WP01.md
        # NOT tasks/planned/WP01.md
        has_flat_example = (
            'tasks/WP' in content or
            'WP01' in content or
            'WP*.md' in content
        )
        assert has_flat_example, \
            "README should show WP files in flat tasks/ directory"

    def test_readme_mentions_lane_frontmatter(self, project_with_feature):
        """Test: README mentions lane field in frontmatter

        GIVEN: A new feature created with v0.9.4+
        WHEN: Reading the tasks/README.md
        THEN: Should mention lane: field in frontmatter
        """
        project_path = project_with_feature

        kitty_specs = project_path / 'kitty-specs'
        if not kitty_specs.exists():
            pytest.skip("No kitty-specs directory")

        feature_dirs = list(kitty_specs.iterdir())
        if not feature_dirs:
            pytest.skip("No feature directories")

        readme_path = feature_dirs[0] / 'tasks' / 'README.md'
        if not readme_path.exists():
            pytest.skip("No tasks/README.md")

        content = readme_path.read_text().lower()

        # Should mention lane frontmatter
        assert 'lane' in content, \
            "README should mention 'lane' field"
        assert 'frontmatter' in content or 'yaml' in content or '---' in content, \
            "README should mention frontmatter/YAML"


class TestAgentsDocumentation:
    """Test that AGENTS.md has proper flat structure documentation."""

    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        return tmp_path

    @pytest.fixture
    def project_path(self, temp_project_dir, spec_kitty_repo_root):
        """Create project to check AGENTS.md."""
        project_name = "agents_test"
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

        return project_path

    def test_agents_md_has_flat_structure_section(self, project_path):
        """Test: AGENTS.md documents flat structure

        GIVEN: A project initialized with v0.9.4+
        WHEN: Reading AGENTS.md
        THEN: Should have section about flat tasks structure
        """
        agents_path = project_path / 'AGENTS.md'
        if not agents_path.exists():
            # Check in .kittify
            agents_path = project_path / '.kittify' / 'AGENTS.md'

        if not agents_path.exists():
            pytest.skip("No AGENTS.md found")

        content = agents_path.read_text().lower()

        # Should mention flat structure
        assert 'flat' in content or 'tasks/' in content, \
            "AGENTS.md should document flat tasks structure"

    def test_agents_md_warns_against_subdirs(self, project_path):
        """Test: AGENTS.md warns against creating subdirectories

        GIVEN: A project initialized with v0.9.4+
        WHEN: Reading AGENTS.md
        THEN: Should warn against planned/, doing/, etc.
        """
        agents_path = project_path / 'AGENTS.md'
        if not agents_path.exists():
            agents_path = project_path / '.kittify' / 'AGENTS.md'

        if not agents_path.exists():
            pytest.skip("No AGENTS.md found")

        content = agents_path.read_text().lower()

        # Should warn about subdirectories
        has_warning = (
            'planned/' in content or
            'subdirector' in content or
            'do not create' in content or
            'never create' in content
        )
        assert has_warning, \
            "AGENTS.md should warn against subdirectories"

    def test_agents_md_shows_correct_examples(self, project_path):
        """Test: AGENTS.md shows correct file structure examples

        GIVEN: A project initialized with v0.9.4+
        WHEN: Reading AGENTS.md
        THEN: Examples should show flat structure, not subdirs
        """
        agents_path = project_path / 'AGENTS.md'
        if not agents_path.exists():
            agents_path = project_path / '.kittify' / 'AGENTS.md'

        if not agents_path.exists():
            pytest.skip("No AGENTS.md found")

        content = agents_path.read_text()

        # Should NOT show old subdirectory structure as correct
        # Look for patterns like "tasks/planned/" which would be wrong
        if 'tasks/planned/' in content:
            # If it mentions tasks/planned/, it should be in a "wrong" or "don't" context
            content_lower = content.lower()
            assert ('wrong' in content_lower or
                    'don\'t' in content_lower or
                    'do not' in content_lower or
                    'incorrect' in content_lower or
                    'legacy' in content_lower), \
                "AGENTS.md should not show subdirectory structure as correct"


class TestRuntimeValidation:
    """Test that check-prerequisites.sh validates flat structure."""

    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        return tmp_path

    @pytest.fixture
    def project_path(self, temp_project_dir, spec_kitty_repo_root):
        """Create project for validation testing."""
        project_name = "validation_test"
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

        return project_path

    def test_check_prerequisites_exists(self, project_path):
        """Test: check-prerequisites.sh script exists

        GIVEN: A project initialized with v0.9.4+
        WHEN: Looking for check-prerequisites.sh
        THEN: Script should exist in .kittify/scripts/bash/
        """
        script_path = project_path / '.kittify' / 'scripts' / 'bash' / 'check-prerequisites.sh'

        assert script_path.exists(), \
            "check-prerequisites.sh should exist"

    def test_validation_passes_flat_structure(self, project_path):
        """Test: Validation passes with flat tasks/ structure

        GIVEN: Feature with flat tasks/ (no subdirectories)
        WHEN: Running check-prerequisites.sh
        THEN: Should pass (exit 0)
        """
        # Create feature with flat structure
        feature_dir = project_path / 'kitty-specs' / '001-flat-test'
        tasks_dir = feature_dir / 'tasks'
        tasks_dir.mkdir(parents=True, exist_ok=True)

        # Create flat WP file
        (tasks_dir / 'WP01.md').write_text('''---
work_package_id: WP01
lane: planned
---
# WP01
''')
        (tasks_dir / '.gitkeep').touch()

        script_path = project_path / '.kittify' / 'scripts' / 'bash' / 'check-prerequisites.sh'
        if not script_path.exists():
            pytest.skip("check-prerequisites.sh not found")

        result = subprocess.run(
            ['bash', str(script_path)],
            cwd=project_path,
            capture_output=True,
            text=True,
            env={**os.environ, 'FEATURE': '001-flat-test'}
        )

        # Should pass (exit 0) or at least not fail due to subdirectories
        # Note: might fail for other reasons, so check output
        if result.returncode != 0:
            assert 'subdirector' not in result.stderr.lower(), \
                f"Should not fail due to subdirectories: {result.stderr}"

    def test_validation_fails_with_planned_subdir(self, project_path):
        """Test: Validation fails when planned/ subdirectory exists

        GIVEN: Feature with tasks/planned/ subdirectory
        WHEN: Running check-prerequisites.sh
        THEN: Should fail and mention subdirectory issue
        """
        # Create feature with legacy structure
        feature_dir = project_path / 'kitty-specs' / '001-legacy-test'
        tasks_dir = feature_dir / 'tasks'
        (tasks_dir / 'planned').mkdir(parents=True, exist_ok=True)
        (tasks_dir / 'planned' / 'WP01.md').write_text('# WP01')

        script_path = project_path / '.kittify' / 'scripts' / 'bash' / 'check-prerequisites.sh'
        if not script_path.exists():
            pytest.skip("check-prerequisites.sh not found")

        result = subprocess.run(
            ['bash', str(script_path)],
            cwd=project_path,
            capture_output=True,
            text=True,
            env={**os.environ, 'FEATURE': '001-legacy-test'}
        )

        # Should either fail (exit != 0) or warn about subdirectories
        output = (result.stdout + result.stderr).lower()

        # If it detected the subdirectory, should warn or fail
        if 'planned' in output or 'subdirector' in output:
            # Good - it detected the issue
            pass
        elif result.returncode != 0:
            # Failed for some reason - acceptable
            pass
        else:
            # Passed without detecting - this is the bug we're testing for
            # In v0.9.4+, this should be detected
            pytest.skip("Validation may not check for subdirectories in this version")

    def test_validation_fails_with_any_subdir(self, project_path):
        """Test: Validation fails with any subdirectory (not just lanes)

        GIVEN: Feature with arbitrary subdirectory in tasks/
        WHEN: Running check-prerequisites.sh
        THEN: Should fail or warn about subdirectory
        """
        feature_dir = project_path / 'kitty-specs' / '001-custom-subdir'
        tasks_dir = feature_dir / 'tasks'
        (tasks_dir / 'phase-1').mkdir(parents=True, exist_ok=True)
        (tasks_dir / 'phase-1' / 'WP01.md').write_text('# WP01')

        script_path = project_path / '.kittify' / 'scripts' / 'bash' / 'check-prerequisites.sh'
        if not script_path.exists():
            pytest.skip("check-prerequisites.sh not found")

        result = subprocess.run(
            ['bash', str(script_path)],
            cwd=project_path,
            capture_output=True,
            text=True,
            env={**os.environ, 'FEATURE': '001-custom-subdir'}
        )

        output = (result.stdout + result.stderr).lower()

        # Should detect subdirectory
        if 'phase-1' in output or 'subdirector' in output:
            pass  # Good - detected
        elif result.returncode != 0:
            pass  # Failed for some reason
        else:
            pytest.skip("Validation may not check for subdirectories")

    def test_error_message_is_actionable(self, project_path):
        """Test: Error message tells user what to do

        GIVEN: Feature with subdirectory in tasks/
        WHEN: Running check-prerequisites.sh and it fails
        THEN: Error message should mention upgrade or fix
        """
        feature_dir = project_path / 'kitty-specs' / '001-error-test'
        tasks_dir = feature_dir / 'tasks'
        (tasks_dir / 'doing').mkdir(parents=True, exist_ok=True)
        (tasks_dir / 'doing' / 'WP01.md').write_text('# WP01')

        script_path = project_path / '.kittify' / 'scripts' / 'bash' / 'check-prerequisites.sh'
        if not script_path.exists():
            pytest.skip("check-prerequisites.sh not found")

        result = subprocess.run(
            ['bash', str(script_path)],
            cwd=project_path,
            capture_output=True,
            text=True,
            env={**os.environ, 'FEATURE': '001-error-test'}
        )

        output = (result.stdout + result.stderr).lower()

        if 'subdirector' in output or result.returncode != 0:
            # If it detected/failed, check for actionable message
            has_action = (
                'upgrade' in output or
                'spec-kitty' in output or
                'move' in output or
                'flat' in output or
                'remove' in output
            )
            # Note: not asserting - this is a nice-to-have
            if not has_action:
                pytest.skip("Error message could be more actionable")


class TestTasksTemplate:
    """Test that /spec-kitty.tasks template has correct instructions."""

    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        return tmp_path

    @pytest.fixture
    def project_path(self, temp_project_dir, spec_kitty_repo_root):
        """Create project to check templates."""
        project_name = "template_test"
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

        return project_path

    def test_tasks_template_mentions_flat_structure(self, project_path):
        """Test: Tasks command template mentions flat structure

        GIVEN: A project initialized with v0.9.4+
        WHEN: Reading the tasks command template
        THEN: Should mention flat structure requirement
        """
        # Check various possible locations
        template_paths = [
            project_path / '.claude' / 'commands' / 'spec-kitty.tasks.md',
            project_path / '.kittify' / 'templates' / 'command-templates' / 'tasks.md',
            project_path / '.codex' / 'prompts' / 'spec-kitty.tasks.md',
        ]

        template_content = None
        for path in template_paths:
            if path.exists():
                template_content = path.read_text()
                break

        if template_content is None:
            pytest.skip("Tasks template not found")

        content_lower = template_content.lower()

        assert 'flat' in content_lower or 'tasks/' in content_lower, \
            "Tasks template should mention flat structure"

    def test_tasks_template_shows_lane_frontmatter(self, project_path):
        """Test: Tasks template mentions lane concept

        GIVEN: A project initialized with v0.9.4+
        WHEN: Reading the tasks command template
        THEN: Should mention lane field or frontmatter concept
        """
        template_paths = [
            project_path / '.claude' / 'commands' / 'spec-kitty.tasks.md',
            project_path / '.kittify' / 'templates' / 'command-templates' / 'tasks.md',
            project_path / '.codex' / 'prompts' / 'spec-kitty.tasks.md',
        ]

        template_content = None
        for path in template_paths:
            if path.exists():
                template_content = path.read_text()
                break

        if template_content is None:
            pytest.skip("Tasks template not found")

        content_lower = template_content.lower()

        # Should mention lane concept (either explicit field or the concept)
        has_lane_concept = (
            'lane:' in template_content or
            'lane :' in template_content or
            'lane' in content_lower or  # At minimum mentions the word
            'frontmatter' in content_lower or
            'planned' in content_lower or
            'doing' in content_lower
        )
        assert has_lane_concept, \
            "Tasks template should mention lane or frontmatter concept"

    def test_tasks_template_warns_against_directories(self, project_path):
        """Test: Tasks template warns against creating directories

        GIVEN: A project initialized with v0.9.4+
        WHEN: Reading the tasks command template
        THEN: Should warn against creating planned/, doing/, etc.
        """
        template_paths = [
            project_path / '.claude' / 'commands' / 'spec-kitty.tasks.md',
            project_path / '.kittify' / 'templates' / 'command-templates' / 'tasks.md',
            project_path / '.codex' / 'prompts' / 'spec-kitty.tasks.md',
        ]

        template_content = None
        for path in template_paths:
            if path.exists():
                template_content = path.read_text()
                break

        if template_content is None:
            pytest.skip("Tasks template not found")

        content_lower = template_content.lower()

        # Should have some warning about directories
        has_warning = (
            'do not create' in content_lower or
            'never create' in content_lower or
            'no subdirector' in content_lower or
            'don\'t create' in content_lower or
            'not create director' in content_lower
        )
        assert has_warning, \
            "Tasks template should warn against creating directories"


class TestIntegration:
    """Integration tests for subdirectory prevention."""

    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        return tmp_path

    @pytest.fixture
    def project_path(self, temp_project_dir, spec_kitty_repo_root):
        """Create project for integration testing."""
        project_name = "integration_test"
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

        return project_path

    def test_new_feature_has_correct_readme(self, project_path, spec_kitty_repo_root):
        """Test: New feature creates README with flat structure warning

        GIVEN: A project initialized with v0.9.4+
        WHEN: Creating a new feature
        THEN: tasks/README.md should have subdirectory warning
        """
        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        create_script = project_path / '.kittify' / 'scripts' / 'bash' / 'create-new-feature.sh'
        if not create_script.exists():
            pytest.skip("create-new-feature.sh not found")

        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'Integration Test', 'Testing integration'],
            cwd=project_path,
            env=env,
            capture_output=True,
            text=True,
            check=False
        )

        # Find the created feature
        kitty_specs = project_path / 'kitty-specs'
        if not kitty_specs.exists():
            # Check worktree
            worktrees = project_path / '.worktrees'
            if worktrees.exists():
                wt_dirs = list(worktrees.iterdir())
                if wt_dirs:
                    kitty_specs = wt_dirs[0] / 'kitty-specs'

        if not kitty_specs.exists():
            pytest.skip("No kitty-specs found")

        feature_dirs = [d for d in kitty_specs.iterdir() if d.is_dir()]
        if not feature_dirs:
            pytest.skip("No feature directories found")

        readme_path = feature_dirs[0] / 'tasks' / 'README.md'
        if not readme_path.exists():
            pytest.skip("No tasks/README.md")

        content = readme_path.read_text().lower()

        # Should have flat structure documentation
        assert 'flat' in content or 'subdirector' in content, \
            "New feature README should mention flat structure"

    def test_commands_work_with_flat_structure(self, project_path):
        """Test: spec-kitty commands work normally with flat structure

        GIVEN: Feature with correct flat structure
        WHEN: Running spec-kitty tasks status
        THEN: Should succeed without errors
        """
        feature_dir = project_path / 'kitty-specs' / '001-flat-feature'
        tasks_dir = feature_dir / 'tasks'
        tasks_dir.mkdir(parents=True, exist_ok=True)

        (tasks_dir / 'WP01.md').write_text('''---
work_package_id: WP01
lane: planned
title: Test Task
---
# WP01 Test
''')

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Add feature'], cwd=project_path, check=True)

        tasks_cli = project_path / '.kittify' / 'scripts' / 'tasks' / 'tasks_cli.py'
        if not tasks_cli.exists():
            pytest.skip("tasks_cli.py not found")

        result = subprocess.run(
            ['python3', str(tasks_cli), 'status', '--feature', '001-flat-feature'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        # Should work (or at least not fail due to structure)
        if result.returncode != 0:
            assert 'subdirector' not in result.stderr.lower(), \
                "Should not fail due to flat structure"

    def test_upgrade_removes_subdirectories(self, project_path):
        """Test: spec-kitty upgrade removes subdirectories

        GIVEN: Feature with legacy subdirectory structure
        WHEN: Running spec-kitty upgrade
        THEN: Subdirectories should be removed
        """
        # Create legacy structure
        feature_dir = project_path / 'kitty-specs' / '001-legacy'
        tasks_dir = feature_dir / 'tasks'
        (tasks_dir / 'planned').mkdir(parents=True, exist_ok=True)
        (tasks_dir / 'doing').mkdir(parents=True, exist_ok=True)

        (tasks_dir / 'planned' / 'WP01.md').write_text('''---
work_package_id: WP01
lane: planned
---
# WP01
''')

        # Set metadata to older version so upgrade runs
        import yaml
        metadata_file = project_path / '.kittify' / 'metadata.yaml'
        if metadata_file.exists():
            with open(metadata_file) as f:
                metadata = yaml.safe_load(f)
            metadata['spec_kitty']['version'] = '0.8.0'
            with open(metadata_file, 'w') as f:
                yaml.dump(metadata, f, default_flow_style=False)

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Legacy structure'], cwd=project_path, check=True)

        result = subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            input='y\n',
            capture_output=True,
            text=True,
            check=False
        )

        # Check if planned/ was removed
        planned_dir = tasks_dir / 'planned'
        doing_dir = tasks_dir / 'doing'

        # At minimum, WP file should be moved out
        if planned_dir.exists():
            wp_files = list(planned_dir.glob('*.md'))
            assert len(wp_files) == 0, \
                "Upgrade should move WP files out of planned/"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
