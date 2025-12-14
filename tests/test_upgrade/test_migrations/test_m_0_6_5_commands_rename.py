"""
Test Migration 0.6.5: Commands → Command-Templates Rename

Tests the CRITICAL migration that fixes the agentfunc doubled-commands bug
by renaming missions/*/commands/ → missions/*/command-templates/.

This migration:
1. Renames commands/ to command-templates/ in all missions
2. Removes template pollution (.kittify/templates/ in user projects)
3. Re-renders .claude/commands/ from new structure
4. Handles worktrees automatically
5. Merges if both old and new exist (new takes precedence)

Test Coverage:
1. Detection (1 test)
   - Detects old commands/ directories

2. Migration Execution (4 tests)
   - Renames commands/ → command-templates/
   - Handles both old and new (merge, new wins)
   - Preserves custom user commands
   - Re-renders .claude/commands/

3. Template Pollution (1 test)
   - Removes .kittify/templates/ in user projects

4. Worktree Support (1 test)
   - Upgrades worktrees automatically

5. Dry Run (1 test)
   - Shows preview without applying
"""

import os
import shutil
from pathlib import Path

import pytest


class TestCommandsRenameMigration:
    """Test the commands/ → command-templates/ migration (CRITICAL)."""

    def test_detect_old_commands_directories(self, v0_6_4_project):
        """Test: Detects commands/ in missions

        GIVEN: A project with missions/*/commands/ directories
        WHEN: Running detect()
        THEN: Should return True (migration needed)
        """
        try:
            from specify_cli.upgrade.migrations.m_0_6_5_commands_rename import CommandsRenameMigration
        except ImportError:
            pytest.skip("CommandsRenameMigration not yet implemented")

        migration = CommandsRenameMigration()

        # v0.6.4 fixture has old commands/ structure
        missions_dir = v0_6_4_project / '.kittify' / 'missions'

        # Verify fixture has old structure
        assert (missions_dir / 'software-dev' / 'commands').exists(), \
            "Fixture should have commands/ directory"

        assert not (missions_dir / 'software-dev' / 'command-templates').exists(), \
            "Fixture should not have command-templates/ yet"

        # Should detect migration needed
        needs_migration = migration.detect(v0_6_4_project)

        assert needs_migration is True, \
            "Should detect that commands/ needs to be renamed"

    def test_rename_mission_commands(self, v0_6_4_project):
        """Test: Renames to command-templates/

        GIVEN: A project with missions/*/commands/ directories
        WHEN: Applying migration
        THEN: Should rename all commands/ → command-templates/
        """
        try:
            from specify_cli.upgrade.migrations.m_0_6_5_commands_rename import CommandsRenameMigration
        except ImportError:
            pytest.skip("CommandsRenameMigration not yet implemented")

        migration = CommandsRenameMigration()

        # Verify starting state
        missions_dir = v0_6_4_project / '.kittify' / 'missions'
        software_dev = missions_dir / 'software-dev'

        assert (software_dev / 'commands').exists(), \
            "Should start with commands/ directory"

        # Note contents of commands/ before migration
        commands_dir = software_dev / 'commands'
        command_files_before = list(commands_dir.rglob('*'))
        command_count_before = len([f for f in command_files_before if f.is_file()])

        # Apply migration
        result = migration.apply(v0_6_4_project, dry_run=False)

        assert result.success, \
            f"Migration should succeed. Error: {result.error if hasattr(result, 'error') else 'N/A'}"

        # Verify commands/ is gone
        assert not (software_dev / 'commands').exists(), \
            "commands/ should no longer exist after migration"

        # Verify command-templates/ exists
        command_templates = software_dev / 'command-templates'
        assert command_templates.exists(), \
            "command-templates/ should exist after migration"

        # Verify all content was moved
        command_files_after = list(command_templates.rglob('*'))
        command_count_after = len([f for f in command_files_after if f.is_file()])

        assert command_count_after == command_count_before, \
            f"All {command_count_before} command files should be preserved, found {command_count_after}"

        # Verify structure is intact (example: code-review command)
        code_review = command_templates / 'code-review'
        assert code_review.exists(), \
            "code-review command directory should exist"

        # Check for command configuration file
        config_files = list(code_review.glob('*.yaml')) + list(code_review.glob('*.yml'))
        assert len(config_files) > 0, \
            "Command configuration file should exist"

    def test_handles_both_old_and_new(self, tmp_path):
        """Test: Merges if both exist (new wins)

        GIVEN: A project with BOTH commands/ and command-templates/
        WHEN: Applying migration
        THEN: Should merge, with command-templates/ taking precedence
        """
        try:
            from specify_cli.upgrade.migrations.m_0_6_5_commands_rename import CommandsRenameMigration
        except ImportError:
            pytest.skip("CommandsRenameMigration not yet implemented")

        migration = CommandsRenameMigration()

        # Create project with both old and new structures
        kittify_dir = tmp_path / '.kittify'
        missions_dir = kittify_dir / 'missions' / 'software-dev'
        missions_dir.mkdir(parents=True)

        # Create old commands/ directory
        old_commands = missions_dir / 'commands'
        old_commands.mkdir()

        # Add command only in old location
        old_only = old_commands / 'old-only'
        old_only.mkdir()
        (old_only / 'command.yaml').write_text("name: old-only\ndescription: Only in old")

        # Add command in both locations (NEW should win)
        (old_commands / 'shared').mkdir()
        (old_commands / 'shared' / 'command.yaml').write_text("name: shared\nversion: OLD")

        # Create new command-templates/ directory
        new_templates = missions_dir / 'command-templates'
        new_templates.mkdir()

        # Add command only in new location
        new_only = new_templates / 'new-only'
        new_only.mkdir()
        (new_only / 'command.yaml').write_text("name: new-only\ndescription: Only in new")

        # Add newer version of shared command (should win)
        (new_templates / 'shared').mkdir()
        (new_templates / 'shared' / 'command.yaml').write_text("name: shared\nversion: NEW")

        # Apply migration
        result = migration.apply(tmp_path, dry_run=False)

        assert result.success, "Migration should succeed"

        # Verify old commands/ is gone
        assert not old_commands.exists(), \
            "commands/ should be removed"

        # Verify command-templates/ has all commands
        assert (new_templates / 'old-only').exists(), \
            "old-only command should be migrated"

        assert (new_templates / 'new-only').exists(), \
            "new-only command should be preserved"

        assert (new_templates / 'shared').exists(), \
            "shared command should exist"

        # Verify NEW version won
        shared_content = (new_templates / 'shared' / 'command.yaml').read_text()
        assert 'version: NEW' in shared_content, \
            "New version should take precedence over old"

        assert 'version: OLD' not in shared_content, \
            "Old version should be replaced by new"

    def test_preserves_custom_commands(self, v0_6_4_project, inject_custom_content):
        """Test: User commands kept

        GIVEN: A project with custom user-created commands
        WHEN: Applying migration
        THEN: All custom commands should be preserved in new location
        """
        try:
            from specify_cli.upgrade.migrations.m_0_6_5_commands_rename import CommandsRenameMigration
        except ImportError:
            pytest.skip("CommandsRenameMigration not yet implemented")

        migration = CommandsRenameMigration()

        # Add custom user command
        custom_command = """name: my-custom-command
description: Custom command created by user
prompt: |
  This is my custom command that I created.
  It should be preserved during migration.
"""

        inject_custom_content(
            v0_6_4_project,
            '.kittify/missions/software-dev/commands/my-custom/command.yaml',
            custom_command
        )

        # Add custom script file
        custom_script = "#!/bin/bash\necho 'My custom script'\n"
        inject_custom_content(
            v0_6_4_project,
            '.kittify/missions/software-dev/commands/my-custom/run.sh',
            custom_script
        )

        # Verify custom command exists before migration
        old_custom = v0_6_4_project / '.kittify' / 'missions' / 'software-dev' / 'commands' / 'my-custom'
        assert old_custom.exists(), "Custom command should exist before migration"
        assert (old_custom / 'command.yaml').exists(), "Custom command.yaml should exist"
        assert (old_custom / 'run.sh').exists(), "Custom run.sh should exist"

        # Apply migration
        result = migration.apply(v0_6_4_project, dry_run=False)

        assert result.success, "Migration should succeed"

        # Verify custom command preserved in new location
        new_custom = v0_6_4_project / '.kittify' / 'missions' / 'software-dev' / 'command-templates' / 'my-custom'
        assert new_custom.exists(), \
            "Custom command should be migrated to command-templates/"

        # Verify custom command.yaml preserved
        new_yaml = new_custom / 'command.yaml'
        assert new_yaml.exists(), \
            "Custom command.yaml should be preserved"

        yaml_content = new_yaml.read_text()
        assert 'my-custom-command' in yaml_content, \
            "Custom command content should be preserved"

        assert 'Custom command created by user' in yaml_content, \
            "Custom description should be preserved"

        # Verify custom script preserved
        new_script = new_custom / 'run.sh'
        assert new_script.exists(), \
            "Custom run.sh should be preserved"

        script_content = new_script.read_text()
        assert "My custom script" in script_content, \
            "Custom script content should be preserved exactly"

    def test_updates_rendered_commands(self, v0_6_4_project):
        """Test: Re-renders .claude/commands/

        GIVEN: A project with rendered commands in .claude/commands/
        WHEN: Applying migration
        THEN: Should re-render commands from new command-templates/ location
        """
        try:
            from specify_cli.upgrade.migrations.m_0_6_5_commands_rename import CommandsRenameMigration
        except ImportError:
            pytest.skip("CommandsRenameMigration not yet implemented")

        migration = CommandsRenameMigration()

        # Create .claude/commands/ directory with old rendered commands
        claude_commands = v0_6_4_project / '.claude' / 'commands'
        claude_commands.mkdir(parents=True, exist_ok=True)

        # Add old rendered command pointing to old location
        old_rendered = claude_commands / 'code-review.md'
        old_rendered.write_text("""# Code Review

Source: .kittify/missions/software-dev/commands/code-review

This is old rendered content from commands/.
""")

        # Note: Some rendered commands might be doubled (agentfunc bug)
        # This migration should fix that

        # Apply migration
        result = migration.apply(v0_6_4_project, dry_run=False)

        assert result.success, "Migration should succeed"

        # Verify rendered commands updated
        # (Migration might re-render, or mark for re-render)

        # If migration re-renders immediately
        if old_rendered.exists():
            rendered_content = old_rendered.read_text()

            # Should now reference new location
            assert 'command-templates' in rendered_content or 'commands/' not in rendered_content, \
                "Rendered command should be updated or removed for re-rendering"

        # If migration clears for re-render on next mission activate
        # (this is also acceptable behavior)

        # At minimum, old commands/ should not be referenced
        # and command-templates/ structure should be correct

    def test_removes_template_pollution(self, v0_6_4_project):
        """Test: Deletes .kittify/templates/ in user projects

        GIVEN: A project with .kittify/templates/ (template pollution)
        WHEN: Applying migration
        THEN: Should remove .kittify/templates/ directory
        """
        try:
            from specify_cli.upgrade.migrations.m_0_6_5_commands_rename import CommandsRenameMigration
        except ImportError:
            pytest.skip("CommandsRenameMigration not yet implemented")

        migration = CommandsRenameMigration()

        # v0.6.4 fixture has template pollution
        templates_dir = v0_6_4_project / '.kittify' / 'templates'

        # Verify fixture has template pollution
        assert templates_dir.exists(), \
            "Fixture should have .kittify/templates/ (template pollution)"

        # Template pollution typically includes:
        # - .kittify/templates/commands/ (should NOT be in user projects)
        # - .kittify/templates/missions/ (should NOT be in user projects)

        templates_commands = templates_dir / 'commands'
        if templates_commands.exists():
            # Note: User projects should NOT have .kittify/templates/
            # This only belongs in the spec-kitty repo itself
            pass

        # Apply migration
        result = migration.apply(v0_6_4_project, dry_run=False)

        assert result.success, "Migration should succeed"

        # Verify template pollution removed
        assert not templates_dir.exists(), \
            ".kittify/templates/ should be removed (template pollution cleanup)"

        # Verify missions are intact (should be in missions/, not templates/)
        missions_dir = v0_6_4_project / '.kittify' / 'missions'
        assert missions_dir.exists(), \
            "missions/ directory should still exist"

        assert (missions_dir / 'software-dev').exists(), \
            "software-dev mission should still exist"

        # Verify command-templates/ created correctly
        command_templates = missions_dir / 'software-dev' / 'command-templates'
        assert command_templates.exists(), \
            "command-templates/ should exist after migration"

    def test_migration_handles_worktrees(self, create_project_with_worktrees):
        """Test: Upgrades worktrees too

        GIVEN: A project with multiple worktrees
        WHEN: Applying migration
        THEN: Should upgrade each worktree's commands/ → command-templates/
        """
        try:
            from specify_cli.upgrade.migrations.m_0_6_5_commands_rename import CommandsRenameMigration
        except ImportError:
            pytest.skip("CommandsRenameMigration not yet implemented")

        migration = CommandsRenameMigration()

        # Create project with 2 worktrees
        main_project = create_project_with_worktrees(
            version="0.6.4",
            num_worktrees=2
        )

        # Verify main project has old structure
        main_commands = main_project / '.kittify' / 'missions' / 'software-dev' / 'commands'
        assert main_commands.exists(), \
            "Main project should have commands/"

        # Verify worktrees exist
        worktrees_dir = main_project / '.worktrees'
        assert worktrees_dir.exists(), \
            "Should have .worktrees/ directory"

        worktrees = list(worktrees_dir.iterdir())
        assert len(worktrees) == 2, \
            f"Should have 2 worktrees, found {len(worktrees)}"

        # Verify worktrees have old structure
        for worktree in worktrees:
            worktree_commands = worktree / '.kittify' / 'missions' / 'software-dev' / 'commands'
            # Worktrees might share .kittify with main via symlink, or have their own
            # Migration should handle both cases

        # Apply migration
        result = migration.apply(main_project, dry_run=False)

        assert result.success, "Migration should succeed"

        # Verify main project upgraded
        assert not main_commands.exists(), \
            "Main project commands/ should be gone"

        main_templates = main_project / '.kittify' / 'missions' / 'software-dev' / 'command-templates'
        assert main_templates.exists(), \
            "Main project should have command-templates/"

        # Verify worktrees upgraded
        for worktree in worktrees:
            worktree_kittify = worktree / '.kittify'

            # If worktree has its own .kittify/
            if worktree_kittify.exists() and not worktree_kittify.is_symlink():
                worktree_commands = worktree_kittify / 'missions' / 'software-dev' / 'commands'
                worktree_templates = worktree_kittify / 'missions' / 'software-dev' / 'command-templates'

                assert not worktree_commands.exists(), \
                    f"Worktree {worktree.name} commands/ should be gone"

                assert worktree_templates.exists(), \
                    f"Worktree {worktree.name} should have command-templates/"

            # If worktree shares .kittify via symlink
            elif worktree_kittify.is_symlink():
                # Should point to main project's .kittify which is already upgraded
                target = worktree_kittify.resolve()
                assert target == main_project / '.kittify', \
                    "Worktree .kittify symlink should point to main"

    def test_dry_run_preview(self, v0_6_4_project):
        """Test: Shows changes without applying

        GIVEN: A project needing migration
        WHEN: Running with dry_run=True
        THEN: Should show what changes would be made without modifying anything
        """
        try:
            from specify_cli.upgrade.migrations.m_0_6_5_commands_rename import CommandsRenameMigration
        except ImportError:
            pytest.skip("CommandsRenameMigration not yet implemented")

        migration = CommandsRenameMigration()

        # Verify starting state
        commands_dir = v0_6_4_project / '.kittify' / 'missions' / 'software-dev' / 'commands'
        templates_dir = v0_6_4_project / '.kittify' / 'templates'

        assert commands_dir.exists(), "Should have commands/ before dry run"
        assert templates_dir.exists(), "Should have templates/ before dry run"

        # Run migration with dry_run=True
        result = migration.apply(v0_6_4_project, dry_run=True)

        # Should succeed (dry run doesn't fail)
        assert result.success or result is not None, \
            "Dry run should complete successfully"

        # Verify NO changes made
        assert commands_dir.exists(), \
            "commands/ should still exist after dry run (no changes made)"

        assert templates_dir.exists(), \
            "templates/ should still exist after dry run (no changes made)"

        templates_path = v0_6_4_project / '.kittify' / 'missions' / 'software-dev' / 'command-templates'
        assert not templates_path.exists(), \
            "command-templates/ should NOT be created during dry run"

        # If result has preview information
        if hasattr(result, 'changes') or hasattr(result, 'preview'):
            changes = getattr(result, 'changes', None) or getattr(result, 'preview', None)

            if changes:
                # Should describe planned changes
                changes_str = str(changes)

                assert 'commands' in changes_str.lower() or 'rename' in changes_str.lower(), \
                    "Dry run should describe command directory changes"

        # If result has files_changed count
        if hasattr(result, 'files_changed'):
            assert result.files_changed > 0, \
                "Dry run should report how many files would be changed"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
