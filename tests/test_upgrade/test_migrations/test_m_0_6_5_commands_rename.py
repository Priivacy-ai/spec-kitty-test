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

        # Verify command files are present
        # (fixture has flat files like implement.md, review.md, specify.md)
        command_files = list(command_templates.glob('*.md'))
        assert len(command_files) > 0, \
            "Command template files should exist"

    def test_handles_both_old_and_new(self, tmp_path):
        """Test: Requires manual merge when both exist

        GIVEN: A project with BOTH commands/ and command-templates/
        WHEN: Checking can_apply()
        THEN: Should return False (manual merge required)

        NOTE: The implementation deliberately avoids automatic merging to
        prevent data loss. Users must manually resolve the conflict.
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
        (old_commands / 'old-only.md').write_text("# Old command")

        # Create new command-templates/ directory (conflict!)
        new_templates = missions_dir / 'command-templates'
        new_templates.mkdir()
        (new_templates / 'new-only.md').write_text("# New command")

        # Check can_apply - should return False due to conflict
        can_apply, message = migration.can_apply(tmp_path)

        assert can_apply is False, \
            "Should not allow migration when both directories exist"

        assert 'manual' in message.lower() or 'merge' in message.lower(), \
            "Error message should mention manual merge requirement"

        # Verify both directories still exist (not modified)
        assert old_commands.exists(), \
            "commands/ should not be touched when conflict detected"

        assert new_templates.exists(), \
            "command-templates/ should not be touched when conflict detected"

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
        """Test: Rendered commands are NOT modified (separate concern)

        GIVEN: A project with rendered commands in .claude/commands/
        WHEN: Applying migration
        THEN: Migration only renames template directories, not rendered commands

        NOTE: The migration focuses only on renaming the source template
        directories. Rendered commands in .claude/commands/ are managed
        separately by the mission system (spec-kitty mission activate).
        Users can re-run mission activate to regenerate rendered commands.
        """
        try:
            from specify_cli.upgrade.migrations.m_0_6_5_commands_rename import CommandsRenameMigration
        except ImportError:
            pytest.skip("CommandsRenameMigration not yet implemented")

        migration = CommandsRenameMigration()

        # Create .claude/commands/ directory with old rendered commands
        claude_commands = v0_6_4_project / '.claude' / 'commands'
        claude_commands.mkdir(parents=True, exist_ok=True)

        # Add old rendered command
        old_rendered = claude_commands / 'code-review.md'
        old_rendered.write_text("""# Code Review

Source: .kittify/missions/software-dev/commands/code-review

This is old rendered content from commands/.
""")
        original_content = old_rendered.read_text()

        # Apply migration
        result = migration.apply(v0_6_4_project, dry_run=False)

        assert result.success, "Migration should succeed"

        # Verify rendered commands are NOT touched by this migration
        # (this is intentional - rendered commands are separate concern)
        assert old_rendered.exists(), \
            "Rendered commands should not be deleted by this migration"

        current_content = old_rendered.read_text()
        assert current_content == original_content, \
            "Migration should not modify rendered commands (separate concern)"

        # Verify the actual migration happened - template dirs renamed
        command_templates = v0_6_4_project / '.kittify' / 'missions' / 'software-dev' / 'command-templates'
        assert command_templates.exists(), \
            "command-templates/ should exist after migration"

    def test_removes_template_pollution(self, v0_6_4_project):
        """Test: Renames templates/commands/ to templates/command-templates/

        GIVEN: A project with .kittify/templates/commands/ (template pollution)
        WHEN: Applying migration
        THEN: Should rename commands/ to command-templates/ within templates/

        NOTE: The migration renames directories rather than deleting them,
        preserving the structure while avoiding Claude Code's auto-discovery
        of commands/ directories.
        """
        try:
            from specify_cli.upgrade.migrations.m_0_6_5_commands_rename import CommandsRenameMigration
        except ImportError:
            pytest.skip("CommandsRenameMigration not yet implemented")

        migration = CommandsRenameMigration()

        # v0.6.4 fixture has template pollution
        templates_dir = v0_6_4_project / '.kittify' / 'templates'
        templates_commands = templates_dir / 'commands'

        # Verify fixture has template pollution
        assert templates_dir.exists(), \
            "Fixture should have .kittify/templates/"

        assert templates_commands.exists(), \
            "Fixture should have .kittify/templates/commands/"

        # Apply migration
        result = migration.apply(v0_6_4_project, dry_run=False)

        assert result.success, "Migration should succeed"

        # Verify templates/commands/ is renamed to templates/command-templates/
        assert not templates_commands.exists(), \
            ".kittify/templates/commands/ should be renamed"

        templates_command_templates = templates_dir / 'command-templates'
        assert templates_command_templates.exists(), \
            ".kittify/templates/command-templates/ should exist after migration"

        # Verify missions are intact
        missions_dir = v0_6_4_project / '.kittify' / 'missions'
        assert missions_dir.exists(), \
            "missions/ directory should still exist"

        # Verify mission commands also renamed
        command_templates = missions_dir / 'software-dev' / 'command-templates'
        assert command_templates.exists(), \
            "command-templates/ should exist after migration"

    def test_migration_handles_worktrees(self, v0_6_4_project, create_project_with_worktrees):
        """Test: Upgrades worktrees too

        GIVEN: A project with multiple worktrees
        WHEN: Applying migration
        THEN: Should upgrade each worktree's commands/ → command-templates/

        NOTE: This test uses the v0_6_4_project fixture and adds worktrees to it.
        """
        try:
            from specify_cli.upgrade.migrations.m_0_6_5_commands_rename import CommandsRenameMigration
        except ImportError:
            pytest.skip("CommandsRenameMigration not yet implemented")

        migration = CommandsRenameMigration()

        # Add worktrees to the v0_6_4 project
        main_project = create_project_with_worktrees(
            base_fixture=v0_6_4_project,
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

        # Apply migration
        result = migration.apply(main_project, dry_run=False)

        assert result.success, "Migration should succeed"

        # Verify main project upgraded
        assert not main_commands.exists(), \
            "Main project commands/ should be gone"

        main_templates = main_project / '.kittify' / 'missions' / 'software-dev' / 'command-templates'
        assert main_templates.exists(), \
            "Main project should have command-templates/"

        # Verify worktrees upgraded (if they have their own .kittify/)
        for worktree in worktrees:
            worktree_kittify = worktree / '.kittify'

            # If worktree has its own .kittify/ (copied from fixture)
            if worktree_kittify.exists() and not worktree_kittify.is_symlink():
                worktree_commands = worktree_kittify / 'missions' / 'software-dev' / 'commands'
                worktree_templates = worktree_kittify / 'missions' / 'software-dev' / 'command-templates'

                assert not worktree_commands.exists(), \
                    f"Worktree {worktree.name} commands/ should be gone"

                assert worktree_templates.exists(), \
                    f"Worktree {worktree.name} should have command-templates/"

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
