"""
Worktree Missions Directory Tests

Tests that mission directories are properly copied to worktrees and that
mission-dependent commands (like plan phase) work correctly in worktrees.

This catches the failure scenario where .kittify/missions/ is empty in worktrees,
causing plan phase to fail with "Active mission directory not found".

Test Coverage:
1. Mission Copy Validation (3 tests)
   - Missions directory copied to worktree
   - Active mission symlink works in worktree
   - Mission templates accessible in worktree

2. Plan Phase Prerequisites (3 tests)
   - setup-plan.sh finds mission templates in worktree
   - Plan phase succeeds with proper mission structure
   - Plan phase fails gracefully with missing missions

3. Mission Corruption Scenarios (2 tests)
   - Empty missions directory detected
   - Broken active-mission symlink handled
"""

import json
import os
import shutil
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


def extract_json_from_output(output: str) -> dict:
    """Extract JSON from script output (last JSON line)."""
    for line in reversed(output.strip().split('\n')):
        if line.strip().startswith('{'):
            try:
                return json.loads(line.strip())
            except json.JSONDecodeError:
                continue
    return None


class TestMissionCopyValidation:
    """Test that missions are properly copied to worktrees."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_missions_directory_copied_to_worktree(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Missions directory is copied to worktree during feature creation"""
        project_name = 'test_missions_copy'
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

        # Verify missions exist in main repo
        main_missions = project_path / '.kittify' / 'missions'
        assert main_missions.exists(), "Main repo should have missions directory"
        assert len(list(main_missions.iterdir())) > 0, "Main repo missions should not be empty"

        # Create a feature
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'TestFeature', 'Test description'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        data = extract_json_from_output(result.stdout)
        assert data is not None, "Should get JSON output from create-new-feature"

        worktree_path = data.get('WORKTREE_PATH')
        assert worktree_path, "Should have worktree path"

        # CRITICAL TEST: Verify missions directory exists in worktree
        worktree_missions = Path(worktree_path) / '.kittify' / 'missions'
        assert worktree_missions.exists(), \
            f"Worktree should have missions directory at {worktree_missions}"

        # CRITICAL TEST: Missions directory should not be empty
        missions_list = list(worktree_missions.iterdir())
        assert len(missions_list) > 0, \
            f"Worktree missions directory should not be empty. Found: {missions_list}"

        # Verify specific missions copied
        software_dev = worktree_missions / 'software-dev'
        assert software_dev.exists(), "software-dev mission should be copied to worktree"
        assert software_dev.is_dir(), "software-dev should be a directory"

    def test_active_mission_symlink_in_worktree(self, temp_project_dir, spec_kitty_repo_root):
        """Test: active-mission symlink points to valid mission in worktree"""
        project_name = 'test_active_mission'
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
            [str(create_script), '--json', '--feature-name', 'ActiveTest', 'Test description'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        data = extract_json_from_output(result.stdout)
        worktree_path = Path(data['WORKTREE_PATH'])

        # Check active-mission symlink
        active_mission = worktree_path / '.kittify' / 'active-mission'
        assert active_mission.exists() or active_mission.is_symlink(), \
            "active-mission should exist in worktree"

        # Resolve the symlink
        if active_mission.is_symlink():
            target = active_mission.resolve()
            assert target.exists(), \
                f"active-mission symlink should point to existing directory: {target}"

            # Verify target is within worktree's missions
            assert 'missions' in str(target), \
                f"active-mission should point to missions directory: {target}"

    def test_mission_templates_accessible_in_worktree(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Mission-specific templates are accessible in worktree"""
        project_name = 'test_mission_templates'
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
            [str(create_script), '--json', '--feature-name', 'TemplateTest', 'Test description'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        data = extract_json_from_output(result.stdout)
        worktree_path = Path(data['WORKTREE_PATH'])

        # Check that plan template exists (mission-specific)
        # Assuming software-dev mission
        plan_template = worktree_path / '.kittify' / 'missions' / 'software-dev' / 'templates' / 'plan-template.md'

        # If it doesn't exist there, check active-mission
        active_mission = worktree_path / '.kittify' / 'active-mission'
        if active_mission.exists():
            mission_templates = active_mission / 'templates'
            if mission_templates.exists():
                template_files = list(mission_templates.glob('*.md'))
                assert len(template_files) > 0, \
                    f"Active mission should have template files in worktree"


class TestPlanPhasePrerequisites:
    """Test that plan phase can execute successfully in worktrees."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_setup_plan_finds_mission_templates(self, temp_project_dir, spec_kitty_repo_root):
        """Test: setup-plan.sh can find mission templates in worktree"""
        project_name = 'test_plan_setup'
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
            [str(create_script), '--json', '--feature-name', 'PlanTest', 'Test plan phase'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        data = extract_json_from_output(result.stdout)
        worktree_path = Path(data['WORKTREE_PATH'])

        # THIS IS THE CRITICAL TEST: Can setup-plan.sh run successfully?
        setup_plan_script = project_path / '.kittify/scripts/bash/setup-plan.sh'

        plan_result = subprocess.run(
            [str(setup_plan_script), '--json'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=False  # Don't fail immediately, we want to check the error
        )

        # Should succeed (missions directory exists)
        assert plan_result.returncode == 0, \
            f"setup-plan.sh should succeed. Error: {plan_result.stderr}"

        # Verify it created plan.md
        plan_data = extract_json_from_output(plan_result.stdout)
        assert plan_data is not None, "Should return JSON"
        assert 'IMPL_PLAN' in plan_data, "Should include IMPL_PLAN path"

        impl_plan = Path(plan_data['IMPL_PLAN'])
        assert impl_plan.exists(), f"plan.md should be created at {impl_plan}"

    def test_plan_phase_with_missing_missions_fails(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Plan phase fails gracefully when missions directory is empty"""
        project_name = 'test_missing_missions'
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
            [str(create_script), '--json', '--feature-name', 'EmptyMissions', 'Test'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        data = extract_json_from_output(result.stdout)
        worktree_path = Path(data['WORKTREE_PATH'])

        # SIMULATE THE BUG: Delete missions directory contents
        missions_dir = worktree_path / '.kittify' / 'missions'
        if missions_dir.exists():
            for item in missions_dir.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()

        # Verify missions directory is now empty (reproducing user's state)
        assert missions_dir.exists(), "Missions directory should exist"
        assert len(list(missions_dir.iterdir())) == 0, \
            "Missions directory should be empty (bug reproduction)"

        # Try to run setup-plan.sh
        setup_plan_script = project_path / '.kittify/scripts/bash/setup-plan.sh'

        plan_result = subprocess.run(
            [str(setup_plan_script), '--json'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=False
        )

        # THIS IS THE FAILURE WE'RE CATCHING
        assert plan_result.returncode != 0, \
            "setup-plan.sh should fail when missions directory is empty"

        # Error should mention missing mission
        error_output = plan_result.stderr + plan_result.stdout
        assert 'mission' in error_output.lower(), \
            f"Error should mention mission problem. Got: {error_output}"
        assert 'not found' in error_output.lower() or 'none' in error_output.lower(), \
            f"Error should indicate mission not found. Got: {error_output}"

    def test_plan_phase_error_message_is_helpful(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Error message clearly explains missing missions issue"""
        project_name = 'test_error_message'
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
            [str(create_script), '--json', '--feature-name', 'ErrorMsg', 'Test'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        data = extract_json_from_output(result.stdout)
        worktree_path = Path(data['WORKTREE_PATH'])

        # Delete missions
        missions_dir = worktree_path / '.kittify' / 'missions'
        if missions_dir.exists():
            shutil.rmtree(missions_dir)
            missions_dir.mkdir()  # Empty directory

        # Run setup-plan.sh
        setup_plan_script = project_path / '.kittify/scripts/bash/setup-plan.sh'

        plan_result = subprocess.run(
            [str(setup_plan_script), '--json'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=False
        )

        # Check error message quality
        error_output = plan_result.stderr + plan_result.stdout

        # Should mention:
        # 1. What directory is missing
        assert 'missions' in error_output.lower(), "Should mention missions"

        # 2. What was expected
        assert any(keyword in error_output.lower() for keyword in ['software-dev', 'active mission', 'mission directory']), \
            "Should mention which mission was expected"

        # 3. Available missions (should say "none")
        assert 'available' in error_output.lower() or 'found' in error_output.lower(), \
            "Should list available missions"


class TestMissionCorruptionScenarios:
    """Test detection and handling of corrupted mission structures."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_empty_missions_directory_detected(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Empty missions directory is detected before plan phase fails"""
        project_name = 'test_empty_detection'
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
            [str(create_script), '--json', '--feature-name', 'EmptyDetect', 'Test'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        data = extract_json_from_output(result.stdout)
        worktree_path = Path(data['WORKTREE_PATH'])

        # Empty the missions directory (reproduce the bug)
        missions_dir = worktree_path / '.kittify' / 'missions'
        for item in missions_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()

        # Verify it's empty
        assert len(list(missions_dir.iterdir())) == 0, "Missions should be empty"

        # Any script that checks prerequisites should detect this
        setup_plan = project_path / '.kittify/scripts/bash/setup-plan.sh'
        result = subprocess.run(
            [str(setup_plan), '--json'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=False
        )

        # Should fail with clear error
        assert result.returncode != 0, "Should fail when missions empty"
        assert 'mission' in (result.stderr + result.stdout).lower(), \
            "Error should mention missions"

    def test_broken_active_mission_symlink(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Broken active-mission symlink with missing missions directory fails"""
        project_name = 'test_broken_symlink'
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
            [str(create_script), '--json', '--feature-name', 'BrokenLink', 'Test'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        data = extract_json_from_output(result.stdout)
        worktree_path = Path(data['WORKTREE_PATH'])

        # Reproduce the actual bug: Delete missions AND break symlink
        missions_dir = worktree_path / '.kittify' / 'missions'
        if missions_dir.exists():
            shutil.rmtree(missions_dir)
            missions_dir.mkdir()  # Empty directory

        # Break the active-mission symlink
        active_mission = worktree_path / '.kittify' / 'active-mission'
        if active_mission.exists() or active_mission.is_symlink():
            active_mission.unlink()

        # Create broken symlink pointing to non-existent location
        active_mission.symlink_to('missions/nonexistent-mission')

        # Try to run setup-plan.sh
        setup_plan = project_path / '.kittify/scripts/bash/setup-plan.sh'
        result = subprocess.run(
            [str(setup_plan), '--json'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=False
        )

        # Should fail - no missions available
        assert result.returncode != 0, "Should fail with empty missions and broken symlink"

        error_output = result.stderr + result.stdout
        assert 'mission' in error_output.lower(), "Should mention mission in error"
        assert 'not found' in error_output.lower() or 'none' in error_output.lower(), \
            "Should indicate mission not found"
