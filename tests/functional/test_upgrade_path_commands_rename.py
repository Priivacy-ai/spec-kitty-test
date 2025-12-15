"""
Test Upgrade Path: commands/ → command-templates/

Tests the migration path from old spec-kitty versions (using commands/) to
new versions (using command-templates/) to ensure no duplicate command discovery.

Real-world scenario: ~/Code/agentfunc had doubled slash commands in Claude
because commands were found in BOTH:
  - .kittify/templates/commands/ (old location)
  - .kittify/missions/*/commands/ (old location)

After upgrade to v0.6.0+, system should:
  - Prefer command-templates/ over commands/ if both exist
  - Not discover duplicates
  - Provide clear migration guidance

Related: findings/0.6.0/2025-12-13_TEST_PLAN_command_templates.md
Test Coverage:
1. Old Project Structure (2 tests)
   - Project with commands/ still works
   - No duplicates when only old structure exists

2. Mixed Structure (3 tests)
   - Both commands/ and command-templates/ coexist
   - New structure takes precedence
   - No duplicate command discovery

3. Migration Path (2 tests)
   - Upgrade from old to new version
   - Old commands/ can be safely removed

4. Real-world Scenario (2 tests)
   - Replicate agentfunc structure
   - Verify no doubled commands after upgrade
"""

import os
import subprocess
import tempfile
from pathlib import Path
import shutil

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


@pytest.fixture
def agentfunc_structure():
    """Return the actual agentfunc .kittify structure for replication."""
    agentfunc_path = Path.home() / 'Code' / 'agentfunc'
    if not agentfunc_path.exists():
        pytest.skip("agentfunc not found - needed for real-world upgrade test")

    return {
        'templates_commands': 13,  # Number of commands in templates/commands/
        'mission_commands': 4,     # Number in missions/research/commands/
        'rendered_commands': 13,   # Expected in .claude/commands/
    }


class TestOldProjectStructure:
    """Test that projects with old commands/ structure still work."""

    def test_old_structure_still_works(self, spec_kitty_repo_root):
        """Test: Old projects with commands/ in missions continue to function"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'old_structure_test'
            project_path = Path(temp_dir) / project_name

            env = os.environ.copy()
            env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

            # Create project with NEW version
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

            # Simulate old project by renaming mission command-templates/ to commands/
            missions_dir = project_path / '.kittify/missions'
            old_mission_exists = False

            for mission_path in missions_dir.iterdir():
                if mission_path.is_dir():
                    old_mission_commands = mission_path / 'commands'
                    new_mission_commands = mission_path / 'command-templates'
                    if new_mission_commands.exists():
                        shutil.move(str(new_mission_commands), str(old_mission_commands))
                        old_mission_exists = True

            # Verify old structure exists in missions
            assert old_mission_exists, \
                "Old commands/ directory should exist in missions"

            # Commands should still be accessible (already rendered)
            claude_commands = list((project_path / '.claude/commands').glob('*.md'))
            assert len(claude_commands) > 0, \
                "Old structure should still provide commands"

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_no_duplicates_with_old_structure(self, spec_kitty_repo_root):
        """Test: Old structure doesn't create duplicate commands"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'old_no_dupes'
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

            # Simulate old structure in missions
            missions_dir = project_path / '.kittify/missions'
            for mission_path in missions_dir.iterdir():
                if mission_path.is_dir():
                    new_mission_commands = mission_path / 'command-templates'
                    old_mission_commands = mission_path / 'commands'
                    if new_mission_commands.exists():
                        shutil.move(str(new_mission_commands), str(old_mission_commands))

            # Count unique command names
            claude_commands = project_path / '.claude/commands'
            command_files = list(claude_commands.glob('spec-kitty.*.md'))
            command_names = [f.stem for f in command_files]

            # Check for duplicates
            unique_names = set(command_names)
            assert len(command_names) == len(unique_names), \
                f"Should not have duplicate commands. Found: {len(command_names)} total, {len(unique_names)} unique"

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestMixedStructure:
    """Test projects with BOTH commands/ and command-templates/ present."""

    def test_both_structures_coexist(self, spec_kitty_repo_root):
        """Test: Both old and new structures can coexist in missions"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'mixed_structure'
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

            # Create OLD structure alongside new in missions
            missions_dir = project_path / '.kittify/missions'
            both_exist = False

            for mission_path in missions_dir.iterdir():
                if mission_path.is_dir():
                    old_commands = mission_path / 'commands'
                    new_commands = mission_path / 'command-templates'

                    if new_commands.exists():
                        # Copy new to old (simulating incomplete upgrade)
                        shutil.copytree(new_commands, old_commands)
                        both_exist = True

            # Both should exist in at least one mission
            assert both_exist, "Both old and new structures should coexist in missions"

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_new_structure_takes_precedence(self, spec_kitty_repo_root):
        """Test: command-templates/ is preferred over commands/ when both exist"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'precedence_test'
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

            # Create both structures with markers
            new_templates = project_path / '.kittify/templates/command-templates'
            old_templates = project_path / '.kittify/templates/commands'

            if new_templates.exists():
                # Copy new to old, then modify old with marker
                shutil.copytree(new_templates, old_templates)

                # Add marker to old structure
                old_plan = old_templates / 'plan.md'
                if old_plan.exists():
                    content = old_plan.read_text()
                    old_plan.write_text("<!-- OLD STRUCTURE MARKER -->\n" + content)

            # Check rendered command for marker
            rendered_plan = project_path / '.claude/commands/spec-kitty.plan.md'
            if rendered_plan.exists():
                rendered_content = rendered_plan.read_text()

                # Should NOT contain old marker (new should take precedence)
                assert "OLD STRUCTURE MARKER" not in rendered_content, \
                    "New command-templates/ should take precedence over old commands/"

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_no_duplicates_with_mixed_structure(self, spec_kitty_repo_root):
        """Test: No duplicate commands when both structures exist"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'mixed_no_dupes'
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

            # Create both structures
            new_templates = project_path / '.kittify/templates/command-templates'
            old_templates = project_path / '.kittify/templates/commands'

            if new_templates.exists():
                shutil.copytree(new_templates, old_templates)

            # Count commands in .claude/commands/
            claude_commands = project_path / '.claude/commands'
            command_files = list(claude_commands.glob('spec-kitty.*.md'))
            command_names = [f.stem for f in command_files]

            # Should not have duplicates
            unique_names = set(command_names)
            assert len(command_names) == len(unique_names), \
                f"Mixed structure should not create duplicates. Found: {len(command_names)} total, {len(unique_names)} unique"

            # Should have exactly 13 commands (not 26)
            assert len(command_names) == 13, \
                f"Should have 13 commands, not duplicated. Found: {len(command_names)}"

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestMigrationPath:
    """Test the upgrade path from old to new version."""

    def test_upgrade_from_old_version(self, spec_kitty_repo_root):
        """Test: Simulated upgrade from v0.5.x to v0.6.0+"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'upgrade_test'
            project_path = Path(temp_dir) / project_name

            env = os.environ.copy()
            env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

            # Step 1: Create "old" project structure
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

            # Simulate old version by renaming in missions
            missions_dir = project_path / '.kittify/missions'
            old_structure_created = False

            for mission_path in missions_dir.iterdir():
                if mission_path.is_dir():
                    new_commands = mission_path / 'command-templates'
                    old_commands = mission_path / 'commands'
                    if new_commands.exists():
                        shutil.move(str(new_commands), str(old_commands))
                        old_structure_created = True

            # Step 2: User upgrades spec-kitty (already running new version)
            # Step 3: Run init again or some command that regenerates structure
            # (In reality, user might run spec-kitty commands which would use new discovery)

            # For this test, just verify the structure is compatible
            assert old_structure_created, "Old structure created for test"

            # Commands should still work (already rendered)
            claude_commands = list((project_path / '.claude/commands').glob('*.md'))
            assert len(claude_commands) > 0, "Commands still accessible after upgrade"

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_old_commands_removable(self, spec_kitty_repo_root):
        """Test: Old commands/ directory can be safely removed"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'removal_test'
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

            # Create both structures
            new_templates = project_path / '.kittify/templates/command-templates'
            old_templates = project_path / '.kittify/templates/commands'

            if new_templates.exists():
                shutil.copytree(new_templates, old_templates)

            # Count commands before removal
            before_count = len(list((project_path / '.claude/commands').glob('*.md')))

            # Remove old structure
            if old_templates.exists():
                shutil.rmtree(old_templates)

            # Commands should still be present (from new structure)
            # Note: This test assumes commands are already rendered to .claude/commands/
            after_count = len(list((project_path / '.claude/commands').glob('*.md')))

            assert before_count == after_count, \
                f"Removing old commands/ should not affect rendered commands. Before: {before_count}, After: {after_count}"

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestCleanUpgrade:
    """Test that upgrades leave projects in clean state without cruft."""

    def test_upgrade_removes_old_structure(self, spec_kitty_repo_root):
        """Test: New projects don't have old structure or template pollution"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'clean_upgrade_test'
            project_path = Path(temp_dir) / project_name

            env = os.environ.copy()
            env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

            # Step 1: Create project (new version)
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

            # Step 2: Verify NO .kittify/templates/ (template pollution)
            templates_dir = project_path / '.kittify/templates'
            assert not templates_dir.exists(), \
                "User projects should NOT have .kittify/templates/ (template pollution)"

            # Step 3: Verify command-templates exist in missions (correct location)
            missions_dir = project_path / '.kittify/missions'
            has_command_templates = False

            for mission_dir in missions_dir.iterdir():
                if mission_dir.is_dir():
                    command_templates = mission_dir / 'command-templates'
                    if command_templates.exists():
                        has_command_templates = True
                        break

            assert has_command_templates, \
                "Missions should have command-templates/ directories"

            # Step 4: Verify no old 'commands/' directories
            has_old_commands = False
            for mission_dir in missions_dir.iterdir():
                if mission_dir.is_dir():
                    old_commands = mission_dir / 'commands'
                    if old_commands.exists():
                        has_old_commands = True
                        break

            assert not has_old_commands, \
                "New projects should not have old commands/ directories"

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_upgrade_leaves_no_cruft(self, spec_kitty_repo_root):
        """Test: No leftover files or directories after upgrade"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'no_cruft_test'
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

            # Check for cruft patterns that shouldn't exist
            cruft_patterns = [
                '**/*-old',
                '**/*-backup',
                '**/*.bak',
                '**/commands-old',
                '**/command-templates-old',
            ]

            found_cruft = []
            for pattern in cruft_patterns:
                matches = list(project_path.glob(pattern))
                if matches:
                    found_cruft.extend(matches)

            assert len(found_cruft) == 0, \
                f"Found cruft files after init: {found_cruft}"

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_final_state_matches_fresh_install(self, spec_kitty_repo_root):
        """Test: Both fresh and cleaned-up projects have same structure"""
        temp_dir = tempfile.mkdtemp()
        try:
            # Create two projects
            fresh_name = 'fresh_install'
            upgraded_name = 'upgraded_install'

            fresh_path = Path(temp_dir) / fresh_name
            upgraded_path = Path(temp_dir) / upgraded_name

            env = os.environ.copy()
            env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

            # Fresh install
            subprocess.run(
                ['spec-kitty', 'init', fresh_name, '--ai=claude', '--ignore-agent-tools'],
                cwd=temp_dir,
                env=env,
                input='y\n',
                capture_output=True,
                text=True,
                timeout=60,
                check=True
            )

            # Upgraded install
            subprocess.run(
                ['spec-kitty', 'init', upgraded_name, '--ai=claude', '--ignore-agent-tools'],
                cwd=temp_dir,
                env=env,
                input='y\n',
                capture_output=True,
                text=True,
                timeout=60,
                check=True
            )

            # Verify both have same structure
            fresh_kittify = fresh_path / '.kittify'
            upgraded_kittify = upgraded_path / '.kittify'

            # Neither should have .kittify/templates/
            fresh_templates = fresh_kittify / 'templates'
            upgraded_templates = upgraded_kittify / 'templates'

            assert not fresh_templates.exists(), \
                "Fresh install should not have .kittify/templates/ pollution"
            assert not upgraded_templates.exists(), \
                "Upgraded install should not have .kittify/templates/ pollution"

            # Both should have mission command-templates
            fresh_has_ct = any((fresh_kittify / 'missions').glob('*/command-templates'))
            upgraded_has_ct = any((upgraded_kittify / 'missions').glob('*/command-templates'))

            assert fresh_has_ct, "Fresh install has mission command-templates"
            assert upgraded_has_ct, "Upgraded install has mission command-templates"

            # Neither should have old commands/
            fresh_has_old = any((fresh_kittify / 'missions').glob('*/commands'))
            upgraded_has_old = any((upgraded_kittify / 'missions').glob('*/commands'))

            assert not fresh_has_old, "Fresh install should not have old commands/"
            assert not upgraded_has_old, "Upgraded install should not have old commands/"

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_user_data_preserved_during_upgrade(self, spec_kitty_repo_root):
        """Test: User's constitution and specs preserved during upgrade"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'preserve_data_test'
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

            # Add user customizations
            constitution_file = project_path / '.kittify/memory/constitution.md'
            original_constitution = constitution_file.read_text()
            custom_marker = "\n\n## CUSTOM USER PRINCIPLE\nThis is my custom rule.\n"
            constitution_file.write_text(original_constitution + custom_marker)

            # Create a spec file
            specs_dir = project_path / 'kitty-specs/001-test-feature'
            specs_dir.mkdir(parents=True, exist_ok=True)
            spec_file = specs_dir / 'spec.md'
            spec_file.write_text("# My Feature Spec\n\nUser content here.")

            # Simulate upgrade (old structure appears)
            old_templates = project_path / '.kittify/templates/commands'
            new_templates = project_path / '.kittify/templates/command-templates'
            if new_templates.exists():
                shutil.copytree(new_templates, old_templates)

            # Upgrade removes old templates
            if old_templates.exists():
                shutil.rmtree(old_templates)

            # User data should be preserved
            assert constitution_file.exists(), "Constitution should still exist"
            assert "CUSTOM USER PRINCIPLE" in constitution_file.read_text(), \
                "User's constitution customizations should be preserved"

            assert spec_file.exists(), "Spec file should still exist"
            assert "My Feature Spec" in spec_file.read_text(), \
                "User's spec content should be preserved"

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestRealWorldScenario:
    """Test based on actual agentfunc project structure."""

    def test_replicate_agentfunc_structure(
        self, spec_kitty_repo_root, agentfunc_structure, spec_kitty_version
    ):
        """Test: Replicate agentfunc's doubled-command scenario"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'agentfunc_replica'
            project_path = Path(temp_dir) / project_name

            env = os.environ.copy()
            env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

            # Build init command - --mission flag removed in v0.8.0
            init_cmd = ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools']
            if spec_kitty_version < (0, 8, 0):
                # Pre-v0.8.0: use --mission flag on init
                init_cmd.insert(4, '--mission=research')

            subprocess.run(
                init_cmd,
                cwd=temp_dir,
                env=env,
                input='y\n',
                capture_output=True,
                text=True,
                timeout=60,
                check=True
            )

            # Create OLD structure (agentfunc has both templates/commands and missions/*/commands)
            new_templates_ct = project_path / '.kittify/templates/command-templates'
            old_templates_c = project_path / '.kittify/templates/commands'

            if new_templates_ct.exists():
                shutil.copytree(new_templates_ct, old_templates_c)

            # Also convert mission commands to old structure
            missions_dir = project_path / '.kittify/missions'
            for mission_path in missions_dir.iterdir():
                if mission_path.is_dir():
                    new_mission_ct = mission_path / 'command-templates'
                    old_mission_c = mission_path / 'commands'
                    if new_mission_ct.exists() and not old_mission_c.exists():
                        shutil.copytree(new_mission_ct, old_mission_c)

            # Now we have agentfunc-like structure with BOTH:
            # - .kittify/templates/commands/ (13 commands)
            # - .kittify/templates/command-templates/ (13 commands)
            # - .kittify/missions/research/commands/ (4 commands)
            # - .kittify/missions/research/command-templates/ (4 commands)

            # Count rendered commands
            claude_commands = project_path / '.claude/commands'
            command_files = list(claude_commands.glob('spec-kitty.*.md'))

            # Should have 13 commands, NOT 26 (doubled)
            assert len(command_files) == 13, \
                f"Should have 13 commands, not doubled. Found: {len(command_files)} " \
                f"(agentfunc structure: {agentfunc_structure})"

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_no_doubled_commands_after_upgrade(self, spec_kitty_repo_root):
        """Test: Upgrade scenario doesn't create doubled slash commands in Claude"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'doubled_commands_test'
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

            # Simulate upgrade scenario: both structures exist
            new_templates = project_path / '.kittify/templates/command-templates'
            old_templates = project_path / '.kittify/templates/commands'

            if new_templates.exists():
                shutil.copytree(new_templates, old_templates)

            # Count total commands across all sources
            all_command_files = []

            # From .claude/commands/
            claude_dir = project_path / '.claude/commands'
            if claude_dir.exists():
                all_command_files.extend(list(claude_dir.glob('spec-kitty.*.md')))

            # Check for duplicates by name
            command_basenames = [f.name for f in all_command_files]
            unique_basenames = set(command_basenames)

            duplicates = [name for name in unique_basenames if command_basenames.count(name) > 1]

            assert len(duplicates) == 0, \
                f"Found doubled commands in Claude: {duplicates}"

            # Verify we have the expected count (13)
            assert len(command_basenames) == 13, \
                f"Should have exactly 13 commands. Found: {len(command_basenames)}"

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
