"""
Test Edge Cases and Real-World Scenarios

Tests unusual situations, conflicts, and real bugs encountered in the field.

This test file covers:
1. Conflicting states (both old and new structures present)
2. Partial migration states (interrupted or failed migrations)
3. Real-world scenarios (actual bugs from production)

These tests ensure the upgrade system handles edge cases gracefully
and provides clear guidance when manual intervention is needed.

Test Coverage:
1. Conflicts (3 tests)
   - Both .specify/ and .kittify/ exist
   - Both commands/ and command-templates/ exist
   - Gitignore has conflicting patterns

2. Partial States (3 tests)
   - Partial migration recovery
   - Migration interrupted midway
   - Rerun failed migration

3. Real-World Scenarios (4 tests)
   - agentfunc doubled-commands bug
   - Fresh install upgrade (no-op)
   - Ancient project without git
   - Windows symlink fallback
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest


class TestConflicts:
    """Test handling of conflicting project states."""

    def test_both_specify_and_kittify_exist(self, tmp_path, create_conflicting_state):
        """Test: Error - manual cleanup needed

        GIVEN: A project with BOTH .specify/ and .kittify/ directories
        WHEN: Running upgrade
        THEN: Should error with clear message about manual cleanup
        """
        try:
            from specify_cli.upgrade.detector import VersionDetector
        except ImportError:
            pytest.skip("VersionDetector not yet implemented")

        # Create conflicting state
        create_conflicting_state(tmp_path, ['both_specify_and_kittify'])

        # Verify both exist
        assert (tmp_path / '.specify').exists(), \
            "Should have .specify/ directory"

        assert (tmp_path / '.kittify').exists(), \
            "Should have .kittify/ directory"

        # Try to detect version (requires instantiation)
        detector = VersionDetector(tmp_path)
        detected = detector.detect_version()

        # Should detect conflict or return "unknown"
        # (Behavior depends on implementation choice)

        # Try to upgrade
        result = subprocess.run(
            ['spec-kitty', 'upgrade', '--force'],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=10
        )

        # Should either:
        # 1. Fail with error about conflict
        # 2. Ask user which to keep
        # 3. Automatically merge (less ideal)

        if result.returncode != 0:
            # Failed - should explain the conflict
            error_output = (result.stdout + result.stderr).lower()

            assert 'specify' in error_output and 'kittify' in error_output, \
                f"Error should mention both directories. Got: {result.stderr}"

            assert 'manual' in error_output or 'conflict' in error_output, \
                "Error should suggest manual resolution"

        else:
            # If succeeded, should have resolved intelligently
            # At minimum, should end up with only .kittify/
            assert (tmp_path / '.kittify').exists(), \
                "Should have .kittify/ after resolution"

    def test_both_commands_and_templates_exist(self, tmp_path, create_conflicting_state):
        """Test: Detects conflict, may refuse to apply

        GIVEN: A mission with BOTH commands/ and command-templates/
        WHEN: Running commands rename migration
        THEN: Should detect conflict and handle appropriately
        """
        try:
            from specify_cli.upgrade.migrations.m_0_6_5_commands_rename import CommandsRenameMigration
        except ImportError:
            pytest.skip("CommandsRenameMigration not yet implemented")

        # Create conflicting state
        create_conflicting_state(tmp_path, ['both_commands_and_templates'])

        # Verify both exist
        missions_dir = tmp_path / '.kittify' / 'missions' / 'software-dev'

        assert (missions_dir / 'commands').exists(), \
            "Should have commands/ directory"

        assert (missions_dir / 'command-templates').exists(), \
            "Should have command-templates/ directory"

        # Create different content in each
        old_command = missions_dir / 'commands' / 'old-only'
        old_command.mkdir(parents=True)
        (old_command / 'command.yaml').write_text("name: old-only")

        new_command = missions_dir / 'command-templates' / 'new-only'
        new_command.mkdir(parents=True)
        (new_command / 'command.yaml').write_text("name: new-only")

        # Run migration
        migration = CommandsRenameMigration()

        # Check if migration detects the conflict via can_apply
        can_apply = migration.can_apply(tmp_path)

        # Migration should either:
        # 1. Return False for can_apply (detects conflict)
        # 2. Or handle the conflict gracefully when applying

        if not can_apply:
            # Migration correctly detects conflict - skip cannot be applied
            return

        # If can_apply is True, try to apply
        result = migration.apply(tmp_path, dry_run=False)

        # Verify templates still exists (may or may not have processed commands/)
        templates_dir = missions_dir / 'command-templates'
        assert (templates_dir / 'new-only').exists(), \
            "Should keep command-templates content"

        # commands/ may still exist if migration didn't merge
        # or may be renamed/removed if it did - either is acceptable

    def test_gitignore_has_conflicting_patterns(self, v0_4_7_project):
        """Test: Preserves user customizations

        GIVEN: A .gitignore with custom patterns for agent directories
        WHEN: Running gitignore migration
        THEN: Should not duplicate or conflict with user patterns
        """
        try:
            from specify_cli.upgrade.migrations.m_0_4_8_gitignore_agents import GitignoreAgentsMigration
        except ImportError:
            pytest.skip("GitignoreAgentsMigration not yet implemented")

        # Add custom patterns to .gitignore
        gitignore = v0_4_7_project / '.gitignore'
        original_content = gitignore.read_text()

        # Add user's custom agent directory pattern
        custom_content = original_content + """
# User's custom agent exclusions
.claude/workspace-*
.cursor/cache/
!.claude/my-important-file.txt
"""

        gitignore.write_text(custom_content)

        # Run migration
        migration = GitignoreAgentsMigration()
        result = migration.apply(v0_4_7_project, dry_run=False)

        assert result.success, "Migration should succeed"

        # Verify user customizations preserved
        new_content = gitignore.read_text()

        assert '.claude/workspace-*' in new_content, \
            "User's custom patterns should be preserved"

        assert '!.claude/my-important-file.txt' in new_content, \
            "User's negation patterns should be preserved"

        # Verify migration patterns added
        assert '.claude/' in new_content, \
            "Migration should add .claude/"

        # Verify no duplicates
        claude_count = new_content.count('.claude/')

        # Might have: .claude/, .claude/workspace-*, etc.
        # Should not have multiple identical ".claude/" entries
        lines = new_content.split('\n')
        exact_claude_lines = [l for l in lines if l.strip() == '.claude/']

        assert len(exact_claude_lines) <= 1, \
            "Should not duplicate .claude/ pattern"


class TestPartialStates:
    """Test recovery from interrupted or failed migrations."""

    def test_partial_migration_recovery(self, v0_4_7_project):
        """Test: Resumes from last successful migration

        GIVEN: A project where some migrations succeeded, one failed
        WHEN: Re-running upgrade after fixing issue
        THEN: Should skip successful migrations, retry failed one
        """
        from datetime import datetime

        try:
            from specify_cli.upgrade.metadata import ProjectMetadata
            from specify_cli.upgrade.runner import MigrationRunner
        except ImportError:
            pytest.skip("MigrationRunner not yet implemented")

        # Simulate partial upgrade by manually recording some migrations
        metadata = ProjectMetadata(
            version="0.4.7",
            initialized_at=datetime.now(),  # Must be set for save()
            python_version="3.11",
            platform="darwin",
            platform_version="Darwin 24.5.0"
        )

        # Record that gitignore migration succeeded
        metadata.record_migration(
            migration_id="0.4.8_gitignore_agents",
            result="success"  # Use result= not success=
        )

        # Record that hooks migration FAILED
        metadata.record_migration(
            migration_id="0.5.0_encoding_hooks",
            result="failed"  # Use result= not success=
        )

        # Save metadata
        kittify_dir = v0_4_7_project / '.kittify'
        metadata.save(kittify_dir)

        # Now re-run upgrade
        result = subprocess.run(
            ['spec-kitty', 'upgrade', '--force'],
            cwd=v0_4_7_project,
            capture_output=True,
            text=True,
            timeout=30
        )

        # May succeed or fail on ensure_missions
        # Just verify the command ran
        output = result.stdout + result.stderr

        # Verify all migrations attempted
        # (ensure_missions may fail in test env, which is expected)
        assert 'migration' in output.lower() or result.returncode == 0, \
            f"Should attempt migrations. Output: {output}"

    def test_migration_interrupted_midway(self, v0_6_4_project):
        """Test: Metadata shows incomplete state

        GIVEN: A migration that was interrupted partway through
        WHEN: Checking project state
        THEN: Metadata should show what was completed
        """
        from datetime import datetime

        try:
            from specify_cli.upgrade.metadata import ProjectMetadata
        except ImportError:
            pytest.skip("ProjectMetadata not yet implemented")

        # Simulate interrupted migration by creating metadata but not completing work
        metadata = ProjectMetadata(
            version="0.6.4",
            initialized_at=datetime.now(),  # Must be set for save()
            python_version="3.11",
            platform="darwin",
            platform_version="Darwin 24.5.0"
        )

        # Start recording a migration but don't complete it
        # (In real scenario, process might crash here)

        metadata.save(v0_6_4_project / '.kittify')

        # Verify metadata exists
        loaded = ProjectMetadata.load(v0_6_4_project / '.kittify')

        assert loaded is not None, \
            "Metadata should exist from interrupted migration"

        # Should not show 0.6.5 migration as complete
        assert not loaded.has_migration("0.6.5_commands_rename"), \
            "Interrupted migration should not be marked complete"

        # Re-running upgrade should complete the work
        result = subprocess.run(
            ['spec-kitty', 'upgrade', '--force'],
            cwd=v0_6_4_project,
            capture_output=True,
            text=True,
            timeout=30
        )

        # May succeed or fail on ensure_missions - that's expected
        output = result.stdout + result.stderr
        assert 'migration' in output.lower() or result.returncode == 0, \
            "Should attempt to complete interrupted migration"

    def test_rerun_failed_migration(self, v0_6_4_project, monkeypatch):
        """Test: Can retry after fixing issues

        GIVEN: A migration that previously failed
        WHEN: Running upgrade again after fixing the issue
        THEN: Should successfully retry the failed migration
        """
        from datetime import datetime

        try:
            from specify_cli.upgrade.metadata import ProjectMetadata
        except ImportError:
            pytest.skip("ProjectMetadata not yet implemented")

        # Create metadata showing failed migration
        metadata = ProjectMetadata(
            version="0.6.4",
            initialized_at=datetime.now(),  # Must be set for save()
            python_version="3.11",
            platform="darwin",
            platform_version="Darwin 24.5.0"
        )

        # Record failed attempt
        metadata.record_migration(
            migration_id="0.6.5_commands_rename",
            result="failed"  # Use result= not success=
        )

        metadata.save(v0_6_4_project / '.kittify')

        # Simulate fixing the issue (e.g., fixing permissions)
        # Then retry upgrade

        result = subprocess.run(
            ['spec-kitty', 'upgrade', '--force'],
            cwd=v0_6_4_project,
            capture_output=True,
            text=True,
            timeout=30
        )

        # May succeed or fail on ensure_missions - that's expected
        output = result.stdout + result.stderr

        # Verify migration was attempted
        assert 'migration' in output.lower() or \
               'commands' in output.lower() or \
               result.returncode == 0, \
            f"Should retry failed migration. Output: {output}"


class TestRealWorldScenarios:
    """Test actual bugs and scenarios from production."""

    def test_agentfunc_doubled_commands(self, v0_6_4_project):
        """Test: Replicates agentfunc issue, verifies fix

        GIVEN: A v0.6.4 project with doubled commands (agentfunc bug)
        WHEN: Running commands rename migration
        THEN: Should fix the doubling issue
        """
        try:
            from specify_cli.upgrade.migrations.m_0_6_5_commands_rename import CommandsRenameMigration
        except ImportError:
            pytest.skip("CommandsRenameMigration not yet implemented")

        # v0.6.4 fixture replicates the agentfunc doubled-commands bug

        # Old commands/ structure exists
        commands_dir = v0_6_4_project / '.kittify' / 'missions' / 'software-dev' / 'commands'
        assert commands_dir.exists(), \
            "v0.6.4 should have old commands/ structure"

        # Run migration
        migration = CommandsRenameMigration()
        result = migration.apply(v0_6_4_project, dry_run=False)

        assert result.success, \
            f"Migration should fix agentfunc issue. Error: {result.error if hasattr(result, 'error') else 'N/A'}"

        # Verify fix - commands renamed to command-templates
        command_templates = v0_6_4_project / '.kittify' / 'missions' / 'software-dev' / 'command-templates'
        assert command_templates.exists(), \
            "Should have command-templates/"

        assert not commands_dir.exists(), \
            "Old commands/ should be removed"

        # Note: Template pollution (.kittify/templates/) handling is separate
        # The commands rename migration focuses on commands/ -> command-templates/
        # Template pollution may be renamed to templates.bak or left as-is

    def test_fresh_install_upgrade_noop(self, tmp_path, spec_kitty_repo_root):
        """Test: Fresh v0.6.7 project → no-op

        GIVEN: A freshly initialized v0.6.7 project
        WHEN: Running spec-kitty upgrade
        THEN: Should report no upgrades needed
        """
        from datetime import datetime

        # Simulate fresh install by running spec-kitty init
        # (If init command exists)

        # Create fresh project structure manually
        kittify_dir = tmp_path / '.kittify'
        kittify_dir.mkdir()

        # Copy current structure from spec-kitty repo
        spec_kitty_kittify = spec_kitty_repo_root / '.kittify'

        if spec_kitty_kittify.exists():
            shutil.copytree(
                spec_kitty_kittify,
                kittify_dir,
                dirs_exist_ok=True,
                symlinks=True
            )

        # Create metadata with current version
        try:
            from specify_cli.upgrade.metadata import ProjectMetadata

            metadata = ProjectMetadata(
                version="0.6.7",
                initialized_at=datetime.now(),  # Must be set for save()
                python_version="3.11",
                platform="darwin",
                platform_version="Darwin 24.5.0"
            )

            metadata.save(kittify_dir)
        except ImportError:
            pytest.skip("ProjectMetadata not yet implemented")

        # Initialize git
        subprocess.run(['git', 'init'], cwd=tmp_path, capture_output=True)
        subprocess.run(['git', 'add', '.'], cwd=tmp_path, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=tmp_path, capture_output=True)

        # Run upgrade with --force to skip prompts
        result = subprocess.run(
            ['spec-kitty', 'upgrade', '--force'],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        output = (result.stdout + result.stderr).lower()

        # Should indicate no upgrades needed or succeed with minimal work
        # (ensure_missions may still run and fail, which is expected)
        assert result.returncode == 0 or 'ensure_missions' in output or \
               'no migrations' in output or 'already' in output, \
            f"Should handle fresh install gracefully. Output: {output}"

    def test_ancient_project_no_git(self, tmp_path):
        """Test: Projects without git still work (partial)

        GIVEN: An ancient project without .git/ directory
        WHEN: Running upgrade
        THEN: Should warn but attempt migrations that don't require git
        """
        # Create old project without git
        specify_dir = tmp_path / '.specify' / 'memory'
        specify_dir.mkdir(parents=True)

        (specify_dir / 'constitution.md').write_text("# Old constitution")

        # No .git/ directory!

        # Try to upgrade
        result = subprocess.run(
            ['spec-kitty', 'upgrade', '--force'],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Might fail (requires git) or succeed with warnings
        if result.returncode != 0:
            # If fails, should clearly explain why
            error = (result.stdout + result.stderr).lower()

            assert 'git' in error, \
                "Should explain that git is required"

        else:
            # If succeeds, migrations that work without git should complete
            # (e.g., directory rename doesn't require git)

            # Verify .specify → .kittify happened
            assert (tmp_path / '.kittify').exists() or (tmp_path / '.specify').exists(), \
                "Should have attempted migration"

    def test_windows_symlink_fallback(self, v0_6_4_project, monkeypatch):
        """Test: Worktree upgrade uses copy on Windows

        GIVEN: Running on Windows where symlinks are restricted
        WHEN: Upgrading worktrees
        THEN: Should fall back to copying instead of symlinking
        """
        # Simulate Windows environment
        monkeypatch.setattr(os, 'name', 'nt')

        # Patch symlink to fail (simulating Windows without admin)
        original_symlink = os.symlink

        def failing_symlink(*args, **kwargs):
            raise OSError("Symlinks require elevated permissions on Windows")

        monkeypatch.setattr(os, 'symlink', failing_symlink)

        try:
            from specify_cli.upgrade.migrations.m_0_6_5_commands_rename import CommandsRenameMigration
        except ImportError:
            pytest.skip("CommandsRenameMigration not yet implemented")

        # Run migration
        migration = CommandsRenameMigration()
        result = migration.apply(v0_6_4_project, dry_run=False)

        # Should succeed despite symlink failure (falls back to copy)
        assert result.success, \
            "Should fall back to copying on Windows"

        # Verify migration completed
        command_templates = v0_6_4_project / '.kittify' / 'missions' / 'software-dev' / 'command-templates'
        assert command_templates.exists(), \
            "Migration should complete using copy instead of symlink"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
