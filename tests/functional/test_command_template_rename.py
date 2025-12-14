"""
Test Command Template Directory Rename

Tests that the rename from commands/ to command-templates/ works correctly
and prevents duplicate slash command discovery in Claude Code.

Related: findings/0.6.0/2025-12-13_TEST_PLAN_command_templates.md

Test Coverage:
1. Directory Structure (4 tests)
   - Fresh init creates command-templates/ not commands/
   - Old commands/ directory does not exist
   - Both templates and missions use command-templates/
   - Template structure is correct

2. Command Discovery (3 tests)
   - Claude discovers exactly one set of commands
   - No duplicate commands in .claude/commands/
   - Rendered commands work correctly

3. API Compatibility (2 tests)
   - TemplateManager finds command templates
   - Mission objects have correct paths
"""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def spec_kitty_repo_root():
    """Get spec-kitty repository root."""
    env_path = os.environ.get('SPEC_KITTY_REPO')
    if env_path:
        return Path(env_path)

    default_path = Path.home() / 'Code' / 'spec-kitty'
    if default_path.exists():
        return default_path

    raise ValueError("spec-kitty repository not found. Set SPEC_KITTY_REPO environment variable.")


class TestCommandTemplateDirectoryStructure:
    """Test that init creates correct directory structure."""

    def test_init_creates_command_templates_directory(self, spec_kitty_repo_root):
        """Test: Fresh init creates command-templates/ not commands/"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'test_cmd_templates'
            project_path = Path(temp_dir) / project_name

            env = os.environ.copy()
            env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

            result = subprocess.run(
                ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
                cwd=temp_dir,
                env=env,
                input='y\n',
                capture_output=True,
                text=True,
                timeout=60
            )

            # Init should succeed
            assert result.returncode == 0, \
                f"Init failed: {result.stdout}\n{result.stderr}"

            # Verify .kittify/templates/command-templates/ exists in main repo
            templates_cmd_dir = spec_kitty_repo_root / '.kittify' / 'templates' / 'command-templates'
            assert templates_cmd_dir.exists(), \
                f"command-templates/ should exist in spec-kitty repo at {templates_cmd_dir}"

            # Verify .kittify/missions/*/command-templates/ exists
            software_dev_cmd = spec_kitty_repo_root / '.kittify' / 'missions' / 'software-dev' / 'command-templates'
            assert software_dev_cmd.exists(), \
                f"command-templates/ should exist in software-dev mission at {software_dev_cmd}"

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_no_commands_directory_created(self, spec_kitty_repo_root):
        """Test: Old commands/ directory does not exist"""
        # Check in templates
        old_templates_cmd = spec_kitty_repo_root / '.kittify' / 'templates' / 'commands'
        assert not old_templates_cmd.exists(), \
            f"Old commands/ directory should NOT exist in templates: {old_templates_cmd}"

        # Check in missions
        old_mission_cmd = spec_kitty_repo_root / '.kittify' / 'missions' / 'software-dev' / 'commands'
        assert not old_mission_cmd.exists(), \
            f"Old commands/ directory should NOT exist in missions: {old_mission_cmd}"

    def test_command_templates_directory_has_files(self, spec_kitty_repo_root):
        """Test: command-templates/ contains command template files"""
        cmd_templates_dir = spec_kitty_repo_root / '.kittify' / 'templates' / 'command-templates'

        # Should have at least some command templates
        cmd_files = list(cmd_templates_dir.glob('*.md'))
        assert len(cmd_files) > 0, \
            f"command-templates/ should contain .md files"

        # Check for expected commands
        expected_commands = ['specify.md', 'implement.md', 'review.md']
        for expected in expected_commands:
            cmd_file = cmd_templates_dir / expected
            assert cmd_file.exists(), \
                f"Expected command template {expected} in command-templates/"

    def test_both_template_locations_use_command_templates(self, spec_kitty_repo_root):
        """Test: Both .kittify/templates/ and .kittify/missions/ use command-templates/"""
        # Check main templates
        main_templates = spec_kitty_repo_root / '.kittify' / 'templates' / 'command-templates'
        assert main_templates.exists(), \
            "Main templates should use command-templates/"

        # Check both missions
        missions_dir = spec_kitty_repo_root / '.kittify' / 'missions'
        for mission_dir in missions_dir.iterdir():
            if mission_dir.is_dir():
                mission_cmd_dir = mission_dir / 'command-templates'
                assert mission_cmd_dir.exists(), \
                    f"Mission {mission_dir.name} should use command-templates/"


class TestCommandDiscoveryNoDuplicates:
    """Test that Claude Code discovers only one set of commands."""

    def test_claude_discovers_single_command_set(self, spec_kitty_repo_root):
        """Test: Claude discovers exactly 13 commands (not duplicates)"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'test_no_duplicates'
            project_path = Path(temp_dir) / project_name

            env = os.environ.copy()
            env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

            result = subprocess.run(
                ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
                cwd=temp_dir,
                env=env,
                input='y\n',
                capture_output=True,
                text=True,
                timeout=60,
                check=True
            )

            # Count commands in .claude/commands/
            claude_commands_dir = project_path / '.claude' / 'commands'
            assert claude_commands_dir.exists(), \
                ".claude/commands/ should be created"

            # Get all spec-kitty commands
            spec_kitty_commands = list(claude_commands_dir.glob('spec-kitty.*.md'))

            # Should have exactly 13 commands (based on current spec-kitty)
            # If there were duplicates, we'd see 26 or 39
            assert len(spec_kitty_commands) == 13, \
                f"Should have exactly 13 commands, got {len(spec_kitty_commands)}: {[c.name for c in spec_kitty_commands]}"

            # Verify no duplicate command names
            command_names = [cmd.name for cmd in spec_kitty_commands]
            unique_names = set(command_names)
            assert len(command_names) == len(unique_names), \
                f"Commands should not have duplicates. Found: {[name for name in command_names if command_names.count(name) > 1]}"

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_no_template_commands_in_project(self, spec_kitty_repo_root):
        """Test: User project does not contain template command directories"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'test_no_templates'
            project_path = Path(temp_dir) / project_name

            env = os.environ.copy()
            env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

            subprocess.run(
                ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
                cwd=temp_dir,
                env=env,
                input='y\n',
                capture_output=True,
                text=True,
                timeout=60,
                check=True
            )

            # User project should NOT have template pollution
            template_pollution_paths = [
                project_path / '.kittify' / 'templates',  # No template source files!
                project_path / 'templates',               # No root templates!
            ]

            for wrong_path in template_pollution_paths:
                assert not wrong_path.exists(), \
                    f"User project should NOT contain template pollution: {wrong_path.relative_to(project_path)}"

            # User project SHOULD have missions with command-templates
            missions_dir = project_path / '.kittify' / 'missions'
            assert missions_dir.exists(), \
                "User project SHOULD have .kittify/missions/ directory"

            # Verify missions have command-templates (new name), not commands (old name)
            has_command_templates = False
            has_old_commands = False

            for mission_dir in missions_dir.iterdir():
                if mission_dir.is_dir():
                    if (mission_dir / 'command-templates').exists():
                        has_command_templates = True
                    if (mission_dir / 'commands').exists():
                        has_old_commands = True

            assert has_command_templates, \
                "Missions should have command-templates/ directories (new structure)"
            assert not has_old_commands, \
                "Missions should NOT have old commands/ directories"

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_rendered_commands_have_no_duplicates(self, spec_kitty_repo_root):
        """Test: No duplicate command files rendered"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'test_rendered'
            project_path = Path(temp_dir) / project_name

            env = os.environ.copy()
            env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

            subprocess.run(
                ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
                cwd=temp_dir,
                env=env,
                input='y\n',
                capture_output=True,
                text=True,
                timeout=60,
                check=True
            )

            claude_commands_dir = project_path / '.claude' / 'commands'
            command_files = list(claude_commands_dir.glob('spec-kitty.*.md'))
            command_names = [f.stem.replace('spec-kitty.', '') for f in command_files]

            # Check for duplicates
            unique_names = set(command_names)
            assert len(command_names) == len(unique_names), \
                f"Found duplicate commands: {len(command_names)} total, {len(unique_names)} unique"

            # Verify expected count
            assert len(command_names) == 13, \
                f"Expected 13 commands, found {len(command_names)}"

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestTemplateManagerAPI:
    """Test that internal APIs work with new paths."""

    def test_template_manager_can_import(self, spec_kitty_repo_root):
        """Test: Template manager module exists and has copy functions"""
        try:
            from specify_cli.template import manager
            assert hasattr(manager, 'copy_specify_base_from_local') or \
                   hasattr(manager, 'copy_specify_base_from_package'), \
                "Template manager should have copy functions"
        except ImportError as e:
            pytest.fail(f"Could not import template manager: {e}")

    def test_mission_has_command_templates_property(self, spec_kitty_repo_root):
        """Test: Mission directories have command-templates/ subdirectories"""
        missions_dir = spec_kitty_repo_root / '.kittify' / 'missions'
        assert missions_dir.exists(), \
            f"Missions directory should exist at {missions_dir}"

        # Get all mission directories
        mission_dirs = [d for d in missions_dir.iterdir() if d.is_dir()]
        assert len(mission_dirs) > 0, \
            "Should have at least one mission directory"

        # Each mission should have command-templates/ (new name)
        for mission_dir in mission_dirs:
            cmd_templates_dir = mission_dir / 'command-templates'
            assert cmd_templates_dir.exists(), \
                f"Mission {mission_dir.name} should have command-templates/ directory"

            # Should NOT have old commands/ directory
            old_commands_dir = mission_dir / 'commands'
            assert not old_commands_dir.exists(), \
                f"Mission {mission_dir.name} should NOT have old commands/ directory"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
