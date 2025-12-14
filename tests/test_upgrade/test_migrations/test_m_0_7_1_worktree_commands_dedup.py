"""
Test Migration 0.7.x: Worktree Commands Deduplication

Note: This migration was originally intended for 0.7.1 but was released as 0.7.2
due to a version bump after fixing the initial implementation.

Tests the migration that fixes the double slash command problem caused by
Claude Code's parent directory traversal finding .claude/commands/ in both
worktrees AND the main repo when worktrees are nested inside the main repo.

Background:
-----------
When you run Claude Code from inside a worktree at:
    /project/.worktrees/feature-branch/

Claude Code traverses up the directory tree looking for .claude/commands/.
If the worktree has its own .claude/commands/ AND the main repo at
/project/ also has .claude/commands/, Claude Code finds BOTH sets of
commands, causing duplicates (e.g., 26 commands instead of 13).

The Fix:
--------
Remove .claude/commands/ from worktrees. Since worktrees are physically
nested inside the main repo, Claude Code will traverse up and find the
main repo's .claude/commands/ automatically. The worktrees don't need
their own copies.

After migration:
    /project/.claude/commands/           <- KEPT (main repo)
    /project/.worktrees/
        feature-001/.claude/             <- commands/ REMOVED
        feature-002/.claude/             <- commands/ REMOVED

Test Coverage:
1. Detection (3 tests)
   - Detects worktrees with .claude/commands/
   - No detection when no worktrees exist
   - No detection when worktrees don't have .claude/commands/

2. Can Apply Validation (2 tests)
   - Requires main repo to have .claude/commands/
   - Fails gracefully if main repo missing commands

3. Migration Execution (4 tests)
   - Removes .claude/commands/ from all worktrees
   - Preserves main repo .claude/commands/
   - Handles multiple worktrees
   - Dry run shows changes without applying

4. Edge Cases (3 tests)
   - Worktree has .claude/ but no commands/ (no-op)
   - Mixed worktrees (some with, some without commands/)
   - Worktree has symlinked .claude/commands/ (skip or handle)
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest


class TestWorktreeCommandsDedupMigration:
    """Test the worktree commands deduplication migration (0.7.1)."""

    # ========================================================================
    # Detection Tests
    # ========================================================================

    def test_detect_worktrees_with_commands(self, v0_6_6_project, create_project_with_worktrees):
        """Test: Detects worktrees that have their own .claude/commands/

        GIVEN: A project with worktrees where worktrees have .claude/commands/
        WHEN: Running detect()
        THEN: Should return True (migration needed)
        """
        try:
            from specify_cli.upgrade.migrations.m_0_7_2_worktree_commands_dedup import (
                WorktreeCommandsDedupMigration,
            )
        except ImportError:
            pytest.skip("WorktreeCommandsDedupMigration not yet implemented")

        migration = WorktreeCommandsDedupMigration()

        # Create project with worktrees
        project = create_project_with_worktrees(
            base_fixture=v0_6_6_project,
            num_worktrees=2
        )

        # Ensure main repo has .claude/commands/
        main_commands = project / '.claude' / 'commands'
        main_commands.mkdir(parents=True, exist_ok=True)
        (main_commands / 'test-command.md').write_text('# Test Command\n')

        # Add .claude/commands/ to worktrees (simulating the problem)
        worktrees_dir = project / '.worktrees'
        for worktree in worktrees_dir.iterdir():
            if worktree.is_dir():
                wt_commands = worktree / '.claude' / 'commands'
                wt_commands.mkdir(parents=True, exist_ok=True)
                (wt_commands / 'test-command.md').write_text('# Test Command\n')

        # Should detect migration needed
        needs_migration = migration.detect(project)

        assert needs_migration is True, \
            "Should detect worktrees with .claude/commands/"

    def test_detect_no_worktrees(self, v0_6_6_project):
        """Test: No detection when project has no worktrees

        GIVEN: A project without any worktrees
        WHEN: Running detect()
        THEN: Should return False (nothing to migrate)
        """
        try:
            from specify_cli.upgrade.migrations.m_0_7_2_worktree_commands_dedup import (
                WorktreeCommandsDedupMigration,
            )
        except ImportError:
            pytest.skip("WorktreeCommandsDedupMigration not yet implemented")

        migration = WorktreeCommandsDedupMigration()

        # Ensure main repo has .claude/commands/ (but no worktrees)
        main_commands = v0_6_6_project / '.claude' / 'commands'
        main_commands.mkdir(parents=True, exist_ok=True)
        (main_commands / 'test-command.md').write_text('# Test Command\n')

        # Verify no .worktrees directory
        worktrees_dir = v0_6_6_project / '.worktrees'
        assert not worktrees_dir.exists(), \
            "Fixture should not have .worktrees/"

        # Should NOT detect migration needed
        needs_migration = migration.detect(v0_6_6_project)

        assert needs_migration is False, \
            "Should not detect migration when no worktrees exist"

    def test_detect_worktrees_without_commands(self, v0_6_6_project, create_project_with_worktrees):
        """Test: No detection when worktrees don't have .claude/commands/

        GIVEN: A project with worktrees that don't have .claude/commands/
        WHEN: Running detect()
        THEN: Should return False (worktrees already clean)
        """
        try:
            from specify_cli.upgrade.migrations.m_0_7_2_worktree_commands_dedup import (
                WorktreeCommandsDedupMigration,
            )
        except ImportError:
            pytest.skip("WorktreeCommandsDedupMigration not yet implemented")

        migration = WorktreeCommandsDedupMigration()

        # Create project with worktrees
        project = create_project_with_worktrees(
            base_fixture=v0_6_6_project,
            num_worktrees=2
        )

        # Ensure main repo has .claude/commands/
        main_commands = project / '.claude' / 'commands'
        main_commands.mkdir(parents=True, exist_ok=True)
        (main_commands / 'test-command.md').write_text('# Test Command\n')

        # Worktrees exist but do NOT have .claude/commands/
        # (create_project_with_worktrees copies .kittify/, not .claude/)

        # Remove any .claude/commands/ that might exist in worktrees
        worktrees_dir = project / '.worktrees'
        for worktree in worktrees_dir.iterdir():
            if worktree.is_dir():
                wt_commands = worktree / '.claude' / 'commands'
                if wt_commands.exists():
                    shutil.rmtree(wt_commands)

        # Should NOT detect migration needed
        needs_migration = migration.detect(project)

        assert needs_migration is False, \
            "Should not detect migration when worktrees don't have .claude/commands/"

    # ========================================================================
    # Can Apply Validation Tests
    # ========================================================================

    def test_can_apply_requires_main_commands(self, v0_6_6_project, create_project_with_worktrees):
        """Test: Requires main repo to have .claude/commands/ before removing from worktrees

        GIVEN: A project where main repo does NOT have .claude/commands/
        WHEN: Checking can_apply()
        THEN: Should return False (can't remove from worktrees if main doesn't have it)
        """
        try:
            from specify_cli.upgrade.migrations.m_0_7_2_worktree_commands_dedup import (
                WorktreeCommandsDedupMigration,
            )
        except ImportError:
            pytest.skip("WorktreeCommandsDedupMigration not yet implemented")

        migration = WorktreeCommandsDedupMigration()

        # Create project with worktrees
        project = create_project_with_worktrees(
            base_fixture=v0_6_6_project,
            num_worktrees=2
        )

        # Ensure main repo does NOT have .claude/commands/
        main_commands = project / '.claude' / 'commands'
        if main_commands.exists():
            shutil.rmtree(main_commands)

        # Add .claude/commands/ to worktrees
        worktrees_dir = project / '.worktrees'
        for worktree in worktrees_dir.iterdir():
            if worktree.is_dir():
                wt_commands = worktree / '.claude' / 'commands'
                wt_commands.mkdir(parents=True, exist_ok=True)
                (wt_commands / 'test-command.md').write_text('# Test Command\n')

        # Check can_apply
        can_apply, message = migration.can_apply(project)

        assert can_apply is False, \
            "Should not allow migration when main repo lacks .claude/commands/"

        assert 'main' in message.lower() or 'exist' in message.lower(), \
            f"Error message should explain main repo requirement: {message}"

    def test_can_apply_with_main_commands(self, v0_6_6_project, create_project_with_worktrees):
        """Test: Allows migration when main repo has .claude/commands/

        GIVEN: A project where main repo has .claude/commands/
        WHEN: Checking can_apply()
        THEN: Should return True
        """
        try:
            from specify_cli.upgrade.migrations.m_0_7_2_worktree_commands_dedup import (
                WorktreeCommandsDedupMigration,
            )
        except ImportError:
            pytest.skip("WorktreeCommandsDedupMigration not yet implemented")

        migration = WorktreeCommandsDedupMigration()

        # Create project with worktrees
        project = create_project_with_worktrees(
            base_fixture=v0_6_6_project,
            num_worktrees=2
        )

        # Ensure main repo HAS .claude/commands/
        main_commands = project / '.claude' / 'commands'
        main_commands.mkdir(parents=True, exist_ok=True)
        (main_commands / 'test-command.md').write_text('# Test Command\n')

        # Add .claude/commands/ to worktrees
        worktrees_dir = project / '.worktrees'
        for worktree in worktrees_dir.iterdir():
            if worktree.is_dir():
                wt_commands = worktree / '.claude' / 'commands'
                wt_commands.mkdir(parents=True, exist_ok=True)
                (wt_commands / 'test-command.md').write_text('# Test Command\n')

        # Check can_apply
        can_apply, message = migration.can_apply(project)

        assert can_apply is True, \
            f"Should allow migration when main repo has .claude/commands/: {message}"

    # ========================================================================
    # Migration Execution Tests
    # ========================================================================

    def test_removes_commands_from_worktrees(self, v0_6_6_project, create_project_with_worktrees):
        """Test: Removes .claude/commands/ from all worktrees

        GIVEN: A project with worktrees that have .claude/commands/
        WHEN: Applying migration
        THEN: Should remove .claude/commands/ from all worktrees
        """
        try:
            from specify_cli.upgrade.migrations.m_0_7_2_worktree_commands_dedup import (
                WorktreeCommandsDedupMigration,
            )
        except ImportError:
            pytest.skip("WorktreeCommandsDedupMigration not yet implemented")

        migration = WorktreeCommandsDedupMigration()

        # Create project with worktrees
        project = create_project_with_worktrees(
            base_fixture=v0_6_6_project,
            num_worktrees=2
        )

        # Ensure main repo has .claude/commands/
        main_commands = project / '.claude' / 'commands'
        main_commands.mkdir(parents=True, exist_ok=True)
        (main_commands / 'test-command.md').write_text('# Test Command\n')

        # Add .claude/commands/ to worktrees
        worktrees_dir = project / '.worktrees'
        worktree_commands_paths = []
        for worktree in worktrees_dir.iterdir():
            if worktree.is_dir():
                wt_commands = worktree / '.claude' / 'commands'
                wt_commands.mkdir(parents=True, exist_ok=True)
                (wt_commands / 'test-command.md').write_text('# Worktree Command\n')
                worktree_commands_paths.append(wt_commands)

        # Verify worktree commands exist before migration
        for wt_commands in worktree_commands_paths:
            assert wt_commands.exists(), \
                f"Worktree {wt_commands} should exist before migration"

        # Apply migration
        result = migration.apply(project, dry_run=False)

        assert result.success, \
            f"Migration should succeed. Errors: {result.errors if hasattr(result, 'errors') else 'N/A'}"

        # Verify worktree commands are removed
        for wt_commands in worktree_commands_paths:
            assert not wt_commands.exists(), \
                f"Worktree {wt_commands} should be removed after migration"

    def test_preserves_main_repo_commands(self, v0_6_6_project, create_project_with_worktrees):
        """Test: Main repo .claude/commands/ is preserved

        GIVEN: A project with main repo and worktrees both having .claude/commands/
        WHEN: Applying migration
        THEN: Main repo .claude/commands/ should NOT be touched
        """
        try:
            from specify_cli.upgrade.migrations.m_0_7_2_worktree_commands_dedup import (
                WorktreeCommandsDedupMigration,
            )
        except ImportError:
            pytest.skip("WorktreeCommandsDedupMigration not yet implemented")

        migration = WorktreeCommandsDedupMigration()

        # Create project with worktrees
        project = create_project_with_worktrees(
            base_fixture=v0_6_6_project,
            num_worktrees=2
        )

        # Create main repo .claude/commands/ with specific content
        main_commands = project / '.claude' / 'commands'
        main_commands.mkdir(parents=True, exist_ok=True)
        main_command_file = main_commands / 'main-only-command.md'
        main_command_file.write_text('# Main Repo Command\nThis is the canonical command.\n')
        original_content = main_command_file.read_text()

        # Add .claude/commands/ to worktrees
        worktrees_dir = project / '.worktrees'
        for worktree in worktrees_dir.iterdir():
            if worktree.is_dir():
                wt_commands = worktree / '.claude' / 'commands'
                wt_commands.mkdir(parents=True, exist_ok=True)
                (wt_commands / 'worktree-command.md').write_text('# Worktree Copy\n')

        # Apply migration
        result = migration.apply(project, dry_run=False)

        assert result.success, "Migration should succeed"

        # Verify main repo commands still exist
        assert main_commands.exists(), \
            "Main repo .claude/commands/ should still exist"

        assert main_command_file.exists(), \
            "Main repo command file should still exist"

        # Verify content is unchanged
        current_content = main_command_file.read_text()
        assert current_content == original_content, \
            "Main repo command content should be unchanged"

    def test_handles_multiple_worktrees(self, v0_6_6_project, create_project_with_worktrees):
        """Test: Handles projects with many worktrees

        GIVEN: A project with multiple worktrees (5+)
        WHEN: Applying migration
        THEN: Should remove .claude/commands/ from ALL worktrees
        """
        try:
            from specify_cli.upgrade.migrations.m_0_7_2_worktree_commands_dedup import (
                WorktreeCommandsDedupMigration,
            )
        except ImportError:
            pytest.skip("WorktreeCommandsDedupMigration not yet implemented")

        migration = WorktreeCommandsDedupMigration()

        # Create project with 5 worktrees
        project = create_project_with_worktrees(
            base_fixture=v0_6_6_project,
            num_worktrees=5
        )

        # Ensure main repo has .claude/commands/
        main_commands = project / '.claude' / 'commands'
        main_commands.mkdir(parents=True, exist_ok=True)
        (main_commands / 'test-command.md').write_text('# Test Command\n')

        # Add .claude/commands/ to ALL worktrees
        worktrees_dir = project / '.worktrees'
        worktree_count = 0
        for worktree in worktrees_dir.iterdir():
            if worktree.is_dir():
                wt_commands = worktree / '.claude' / 'commands'
                wt_commands.mkdir(parents=True, exist_ok=True)
                (wt_commands / 'command.md').write_text('# Command\n')
                worktree_count += 1

        assert worktree_count == 5, \
            f"Should have 5 worktrees, found {worktree_count}"

        # Apply migration
        result = migration.apply(project, dry_run=False)

        assert result.success, "Migration should succeed"

        # Verify ALL worktree commands are removed
        remaining_commands = 0
        for worktree in worktrees_dir.iterdir():
            if worktree.is_dir():
                wt_commands = worktree / '.claude' / 'commands'
                if wt_commands.exists():
                    remaining_commands += 1

        assert remaining_commands == 0, \
            f"All worktree commands should be removed, {remaining_commands} remaining"

        # Verify changes are reported
        if hasattr(result, 'changes'):
            # Should have 5 removal messages (one per worktree)
            assert len(result.changes) >= 5, \
                f"Should report changes for all 5 worktrees, got {len(result.changes)}"

    def test_dry_run_no_changes(self, v0_6_6_project, create_project_with_worktrees):
        """Test: Dry run shows changes without applying

        GIVEN: A project needing migration
        WHEN: Running with dry_run=True
        THEN: Should show what changes would be made without modifying anything
        """
        try:
            from specify_cli.upgrade.migrations.m_0_7_2_worktree_commands_dedup import (
                WorktreeCommandsDedupMigration,
            )
        except ImportError:
            pytest.skip("WorktreeCommandsDedupMigration not yet implemented")

        migration = WorktreeCommandsDedupMigration()

        # Create project with worktrees
        project = create_project_with_worktrees(
            base_fixture=v0_6_6_project,
            num_worktrees=2
        )

        # Ensure main repo has .claude/commands/
        main_commands = project / '.claude' / 'commands'
        main_commands.mkdir(parents=True, exist_ok=True)
        (main_commands / 'test-command.md').write_text('# Test Command\n')

        # Add .claude/commands/ to worktrees
        worktrees_dir = project / '.worktrees'
        worktree_commands_paths = []
        for worktree in worktrees_dir.iterdir():
            if worktree.is_dir():
                wt_commands = worktree / '.claude' / 'commands'
                wt_commands.mkdir(parents=True, exist_ok=True)
                (wt_commands / 'command.md').write_text('# Command\n')
                worktree_commands_paths.append(wt_commands)

        # Run dry run
        result = migration.apply(project, dry_run=True)

        # Should complete without error
        assert result is not None, "Dry run should return a result"

        # Verify NO changes were made
        for wt_commands in worktree_commands_paths:
            assert wt_commands.exists(), \
                f"Worktree {wt_commands} should still exist after dry run"

        # If result has changes, they should describe what WOULD happen
        if hasattr(result, 'changes') and result.changes:
            for change in result.changes:
                assert 'would' in change.lower(), \
                    f"Dry run changes should use 'would' language: {change}"

    # ========================================================================
    # Edge Case Tests
    # ========================================================================

    def test_worktree_has_claude_but_no_commands(self, v0_6_6_project, create_project_with_worktrees):
        """Test: Worktree with .claude/ but no commands/ is handled gracefully

        GIVEN: A worktree with .claude/ directory but no commands/ subdirectory
        WHEN: Applying migration
        THEN: Should complete successfully (no-op for that worktree)
        """
        try:
            from specify_cli.upgrade.migrations.m_0_7_2_worktree_commands_dedup import (
                WorktreeCommandsDedupMigration,
            )
        except ImportError:
            pytest.skip("WorktreeCommandsDedupMigration not yet implemented")

        migration = WorktreeCommandsDedupMigration()

        # Create project with worktrees
        project = create_project_with_worktrees(
            base_fixture=v0_6_6_project,
            num_worktrees=2
        )

        # Ensure main repo has .claude/commands/
        main_commands = project / '.claude' / 'commands'
        main_commands.mkdir(parents=True, exist_ok=True)
        (main_commands / 'test-command.md').write_text('# Test Command\n')

        # One worktree has .claude/ but NOT commands/
        worktrees_dir = project / '.worktrees'
        worktrees = list(worktrees_dir.iterdir())

        # First worktree: .claude/ exists but no commands/
        wt1_claude = worktrees[0] / '.claude'
        wt1_claude.mkdir(parents=True, exist_ok=True)
        (wt1_claude / 'settings.json').write_text('{}')  # Some other file
        # NO commands/ directory

        # Second worktree: has .claude/commands/
        wt2_commands = worktrees[1] / '.claude' / 'commands'
        wt2_commands.mkdir(parents=True, exist_ok=True)
        (wt2_commands / 'command.md').write_text('# Command\n')

        # Apply migration
        result = migration.apply(project, dry_run=False)

        assert result.success, "Migration should succeed"

        # First worktree's .claude/ should still exist (we don't delete the whole .claude/)
        assert wt1_claude.exists(), \
            "Worktree .claude/ should not be deleted (only commands/)"

        # Second worktree's commands/ should be removed
        assert not wt2_commands.exists(), \
            "Worktree commands/ should be removed"

    def test_mixed_worktrees(self, v0_6_6_project, create_project_with_worktrees):
        """Test: Handles mix of worktrees with and without .claude/commands/

        GIVEN: Multiple worktrees where only some have .claude/commands/
        WHEN: Applying migration
        THEN: Should only remove from worktrees that have it
        """
        try:
            from specify_cli.upgrade.migrations.m_0_7_2_worktree_commands_dedup import (
                WorktreeCommandsDedupMigration,
            )
        except ImportError:
            pytest.skip("WorktreeCommandsDedupMigration not yet implemented")

        migration = WorktreeCommandsDedupMigration()

        # Create project with 4 worktrees
        project = create_project_with_worktrees(
            base_fixture=v0_6_6_project,
            num_worktrees=4
        )

        # Ensure main repo has .claude/commands/
        main_commands = project / '.claude' / 'commands'
        main_commands.mkdir(parents=True, exist_ok=True)
        (main_commands / 'test-command.md').write_text('# Test Command\n')

        # Only add .claude/commands/ to 2 of 4 worktrees
        worktrees_dir = project / '.worktrees'
        worktrees = list(worktrees_dir.iterdir())

        # Worktrees 0 and 2 have commands
        wt0_commands = worktrees[0] / '.claude' / 'commands'
        wt0_commands.mkdir(parents=True, exist_ok=True)
        (wt0_commands / 'command.md').write_text('# Command\n')

        wt2_commands = worktrees[2] / '.claude' / 'commands'
        wt2_commands.mkdir(parents=True, exist_ok=True)
        (wt2_commands / 'command.md').write_text('# Command\n')

        # Worktrees 1 and 3 do NOT have commands (nothing to remove)

        # Apply migration
        result = migration.apply(project, dry_run=False)

        assert result.success, "Migration should succeed"

        # Verify commands removed from worktrees 0 and 2
        assert not wt0_commands.exists(), \
            "Worktree 0 commands/ should be removed"

        assert not wt2_commands.exists(), \
            "Worktree 2 commands/ should be removed"

        # If result has changes, should only report 2 removals
        if hasattr(result, 'changes') and result.changes:
            removal_changes = [c for c in result.changes if 'remove' in c.lower()]
            assert len(removal_changes) == 2, \
                f"Should report 2 removals, got {len(removal_changes)}"

    def test_worktree_symlinked_commands(self, v0_6_6_project, create_project_with_worktrees):
        """Test: Handles worktree with symlinked .claude/commands/

        GIVEN: A worktree where .claude/commands/ is a symlink
        WHEN: Applying migration
        THEN: Should handle gracefully (remove symlink or skip with warning)

        NOTE: Symlinked commands might point to main repo or elsewhere.
        The migration should either:
        1. Remove the symlink (safe - it's just a link)
        2. Skip with a warning (conservative approach)
        """
        try:
            from specify_cli.upgrade.migrations.m_0_7_2_worktree_commands_dedup import (
                WorktreeCommandsDedupMigration,
            )
        except ImportError:
            pytest.skip("WorktreeCommandsDedupMigration not yet implemented")

        migration = WorktreeCommandsDedupMigration()

        # Create project with worktrees
        project = create_project_with_worktrees(
            base_fixture=v0_6_6_project,
            num_worktrees=2
        )

        # Ensure main repo has .claude/commands/
        main_commands = project / '.claude' / 'commands'
        main_commands.mkdir(parents=True, exist_ok=True)
        (main_commands / 'test-command.md').write_text('# Test Command\n')

        # First worktree: symlinked commands (points to main)
        worktrees_dir = project / '.worktrees'
        worktrees = list(worktrees_dir.iterdir())

        wt1_claude = worktrees[0] / '.claude'
        wt1_claude.mkdir(parents=True, exist_ok=True)
        wt1_commands = wt1_claude / 'commands'

        # Create symlink to main repo commands
        # Use relative path for portability
        rel_path = os.path.relpath(main_commands, wt1_claude)
        os.symlink(rel_path, wt1_commands)

        assert wt1_commands.is_symlink(), \
            "Worktree commands should be a symlink"

        # Second worktree: regular directory
        wt2_commands = worktrees[1] / '.claude' / 'commands'
        wt2_commands.mkdir(parents=True, exist_ok=True)
        (wt2_commands / 'command.md').write_text('# Command\n')

        # Apply migration
        result = migration.apply(project, dry_run=False)

        # Migration should complete (success or with warnings)
        assert result is not None, "Migration should return a result"

        # Main repo commands should be untouched
        assert main_commands.exists(), \
            "Main repo commands should still exist"

        # Regular worktree commands should be removed
        assert not wt2_commands.exists(), \
            "Regular worktree commands should be removed"

        # Symlinked commands should either be:
        # 1. Removed (the symlink itself, not the target)
        # 2. Still exist but logged as warning
        if wt1_commands.exists():
            # If still exists, check it was warned about
            if hasattr(result, 'warnings') and result.warnings:
                symlink_warnings = [w for w in result.warnings if 'symlink' in w.lower()]
                assert len(symlink_warnings) > 0, \
                    "Should warn about symlinked commands if not removed"
        else:
            # Symlink was removed - verify target (main commands) still exists
            assert main_commands.exists(), \
                "Removing symlink should not affect target"


class TestWorktreeCommandsDedupIntegration:
    """Integration tests for the 0.7.1 migration with full upgrade flow."""

    def test_migration_registered(self):
        """Test: Migration is registered in the registry

        GIVEN: The migration module is loaded
        WHEN: Checking MigrationRegistry
        THEN: 0.7.1_worktree_commands_dedup should be registered
        """
        try:
            from specify_cli.upgrade.registry import MigrationRegistry
        except ImportError:
            pytest.skip("MigrationRegistry not yet implemented")

        all_migrations = MigrationRegistry.get_all()
        migration_ids = [m.migration_id for m in all_migrations]

        assert "0.7.2_worktree_commands_dedup" in migration_ids, \
            "0.7.2_worktree_commands_dedup should be registered"

    def test_migration_ordered_after_0_6_7(self):
        """Test: Migration comes after 0.6.7

        GIVEN: The migration registry
        WHEN: Getting all migrations
        THEN: 0.7.2 should come after 0.6.7 (ensure_missions)
        """
        try:
            from specify_cli.upgrade.registry import MigrationRegistry
        except ImportError:
            pytest.skip("MigrationRegistry not yet implemented")

        all_migrations = MigrationRegistry.get_all()
        migration_ids = [m.migration_id for m in all_migrations]

        # Find indices
        idx_067 = next(
            (i for i, mid in enumerate(migration_ids) if "0.6.7" in mid),
            -1
        )
        idx_072 = next(
            (i for i, mid in enumerate(migration_ids) if "0.7.2" in mid),
            -1
        )

        if idx_067 >= 0 and idx_072 >= 0:
            assert idx_067 < idx_072, \
                "0.6.7 migration should come before 0.7.2"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
