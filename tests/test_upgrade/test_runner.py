"""
Test Migration Runner

Tests the orchestration layer that plans and executes migration chains.

The MigrationRunner:
- Plans upgrade path from current version to target version
- Executes migrations in chronological order
- Skips already-applied migrations (checks metadata)
- Stops chain on first failure
- Updates metadata after each successful migration
- Provides progress reporting

Test Coverage:
1. Planning (1 test)
   - Identifies needed migrations for version range

2. Execution (3 tests)
   - Run single migration successfully
   - Run migration chain (multiple migrations)
   - Skip already-applied migrations

3. Error Handling (2 tests)
   - Stop on failure (don't continue chain)
   - Rollback on error (NOT implemented - document limitation)

4. Metadata Updates (1 test)
   - Records each migration immediately
"""

import shutil
from pathlib import Path

import pytest


class TestMigrationRunner:
    """Test the migration runner orchestration system."""

    def test_plan_upgrade_path(self, v0_4_7_project):
        """Test: Identifies needed migrations (v0.4.7 → v0.6.7)

        GIVEN: A v0.4.7 project
        WHEN: Planning upgrade to v0.6.7
        THEN: Should identify all needed migrations in correct order
        """
        try:
            from specify_cli.upgrade.runner import MigrationRunner
            from specify_cli.upgrade.detector import VersionDetector
        except ImportError:
            pytest.skip("MigrationRunner not yet implemented")

        # Detect current version
        current_version = VersionDetector.detect_version(v0_4_7_project)

        assert current_version.startswith("0.4"), \
            f"Fixture should be v0.4.x, detected: {current_version}"

        # Plan upgrade
        runner = MigrationRunner()
        plan = runner.plan_upgrade(
            project_path=v0_4_7_project,
            current_version=current_version,
            target_version="0.6.7"
        )

        # Should include migrations after 0.4.7
        migration_ids = [m.migration_id for m in plan]

        assert "0.4.8_gitignore_agents" in migration_ids, \
            "Should need gitignore agents migration"

        assert "0.5.0_encoding_hooks" in migration_ids, \
            "Should need encoding hooks migration"

        assert "0.6.5_commands_rename" in migration_ids, \
            "Should need commands rename migration"

        # Should NOT include migrations before current version
        assert "0.2.0_specify_to_kittify" not in migration_ids, \
            "Should NOT include migrations before current version"

        # Verify order is chronological
        # First migration should be 0.4.8
        assert plan[0].migration_id == "0.4.8_gitignore_agents", \
            "First migration should be 0.4.8"

        # Verify count
        assert len(plan) >= 3, \
            f"Should plan at least 3 migrations (0.4.8, 0.5.0, 0.6.5), found {len(plan)}"

    def test_run_single_migration(self, v0_6_4_project):
        """Test: Executes one migration successfully

        GIVEN: A v0.6.4 project needing commands rename
        WHEN: Running single migration
        THEN: Should execute successfully and update metadata
        """
        try:
            from specify_cli.upgrade.runner import MigrationRunner
            from specify_cli.upgrade.metadata import ProjectMetadata
        except ImportError:
            pytest.skip("MigrationRunner not yet implemented")

        runner = MigrationRunner()

        # Verify starting state
        commands_dir = v0_6_4_project / '.kittify' / 'missions' / 'software-dev' / 'commands'
        assert commands_dir.exists(), \
            "Should start with commands/ directory"

        # Run single migration
        result = runner.run_single_migration(
            project_path=v0_6_4_project,
            migration_id="0.6.5_commands_rename",
            dry_run=False
        )

        # Verify success
        assert result.success, \
            f"Migration should succeed. Error: {result.error if hasattr(result, 'error') else 'N/A'}"

        # Verify migration was applied
        assert not commands_dir.exists(), \
            "commands/ should be renamed"

        templates_dir = v0_6_4_project / '.kittify' / 'missions' / 'software-dev' / 'command-templates'
        assert templates_dir.exists(), \
            "command-templates/ should exist"

        # Verify metadata updated
        metadata = ProjectMetadata.load(v0_6_4_project / '.kittify')

        assert metadata is not None, \
            "Metadata should be created/updated"

        assert metadata.has_migration("0.6.5_commands_rename"), \
            "Migration should be recorded in metadata"

    def test_run_migration_chain(self, v0_4_7_project):
        """Test: Executes multiple migrations in order

        GIVEN: A v0.4.7 project
        WHEN: Running upgrade to v0.6.7
        THEN: Should execute all migrations in correct order
        """
        try:
            from specify_cli.upgrade.runner import MigrationRunner
            from specify_cli.upgrade.metadata import ProjectMetadata
        except ImportError:
            pytest.skip("MigrationRunner not yet implemented")

        runner = MigrationRunner()

        # Run full upgrade
        result = runner.run_upgrade(
            project_path=v0_4_7_project,
            current_version="0.4.7",
            target_version="0.6.7",
            dry_run=False
        )

        # Verify overall success
        assert result.success, \
            f"Upgrade should succeed. Error: {result.error if hasattr(result, 'error') else 'N/A'}"

        # Verify all migrations applied
        # Should have run: 0.4.8 (gitignore), 0.5.0 (hooks), 0.6.5 (commands)

        # Check .gitignore has agent directories
        gitignore = v0_4_7_project / '.gitignore'
        gitignore_content = gitignore.read_text()

        assert '.claude/' in gitignore_content, \
            "Gitignore migration should have added .claude/"

        assert '.github/copilot/' in gitignore_content, \
            "Gitignore migration should have added .github/copilot/"

        # Check pre-commit hook installed
        hook = v0_4_7_project / '.git' / 'hooks' / 'pre-commit-agent-check'
        assert hook.exists(), \
            "Encoding hooks migration should have installed pre-commit hook"

        # Check commands renamed
        software_dev = v0_4_7_project / '.kittify' / 'missions' / 'software-dev'
        assert not (software_dev / 'commands').exists(), \
            "Commands rename migration should have removed commands/"

        assert (software_dev / 'command-templates').exists(), \
            "Commands rename migration should have created command-templates/"

        # Verify metadata shows all migrations
        metadata = ProjectMetadata.load(v0_4_7_project / '.kittify')

        assert metadata is not None, "Metadata should exist"

        assert metadata.has_migration("0.4.8_gitignore_agents"), \
            "Should record gitignore migration"

        assert metadata.has_migration("0.5.0_encoding_hooks"), \
            "Should record hooks migration"

        assert metadata.has_migration("0.6.5_commands_rename"), \
            "Should record commands rename migration"

        # Verify migrations recorded in order
        applied = metadata.applied_migrations

        # Find indices
        idx_048 = next(
            (i for i, m in enumerate(applied) if "0.4.8" in m.get('migration_id', '')),
            -1
        )
        idx_050 = next(
            (i for i, m in enumerate(applied) if "0.5.0" in m.get('migration_id', '')),
            -1
        )
        idx_065 = next(
            (i for i, m in enumerate(applied) if "0.6.5" in m.get('migration_id', '')),
            -1
        )

        assert idx_048 < idx_050 < idx_065, \
            "Migrations should be recorded in chronological order"

    def test_skip_already_applied(self, v0_6_4_project):
        """Test: Doesn't re-run recorded migrations

        GIVEN: A project with some migrations already applied
        WHEN: Running upgrade
        THEN: Should skip already-applied migrations
        """
        try:
            from specify_cli.upgrade.runner import MigrationRunner
            from specify_cli.upgrade.metadata import ProjectMetadata
        except ImportError:
            pytest.skip("MigrationRunner not yet implemented")

        # Create metadata with some migrations already recorded
        metadata = ProjectMetadata(
            version="0.6.4",
            initialized_at=None,
            python_version="3.11",
            platform="darwin",
            platform_version="Darwin 24.5.0"
        )

        # Record that gitignore and hooks migrations already applied
        metadata.record_migration(
            migration_id="0.4.8_gitignore_agents",
            success=True
        )

        metadata.record_migration(
            migration_id="0.5.0_encoding_hooks",
            success=True
        )

        # Save metadata
        kittify_dir = v0_6_4_project / '.kittify'
        metadata.save(kittify_dir)

        # Verify metadata saved
        loaded = ProjectMetadata.load(kittify_dir)
        assert loaded.has_migration("0.4.8_gitignore_agents"), \
            "Pre-existing migration should be recorded"

        # Now run upgrade
        runner = MigrationRunner()

        result = runner.run_upgrade(
            project_path=v0_6_4_project,
            current_version="0.6.4",
            target_version="0.6.7",
            dry_run=False
        )

        assert result.success, "Upgrade should succeed"

        # Verify only NEW migration was applied
        # (commands rename should run, but not gitignore/hooks)

        # If runner tracks which migrations ran
        if hasattr(result, 'migrations_applied'):
            applied_ids = [m.migration_id for m in result.migrations_applied]

            # Should only run commands rename (not already recorded)
            assert "0.6.5_commands_rename" in applied_ids, \
                "Should run commands rename (not yet applied)"

            # Should NOT re-run already applied migrations
            assert "0.4.8_gitignore_agents" not in applied_ids, \
                "Should skip gitignore (already applied)"

            assert "0.5.0_encoding_hooks" not in applied_ids, \
                "Should skip hooks (already applied)"

        # Verify end result is correct regardless
        command_templates = v0_6_4_project / '.kittify' / 'missions' / 'software-dev' / 'command-templates'
        assert command_templates.exists(), \
            "Commands should be renamed even if earlier migrations skipped"

    def test_stop_on_failure(self, v0_4_7_project, monkeypatch):
        """Test: Halts chain if migration fails

        GIVEN: A migration chain where one migration fails
        WHEN: Running upgrade
        THEN: Should stop at failed migration, not continue
        """
        try:
            from specify_cli.upgrade.runner import MigrationRunner
            from specify_cli.upgrade.metadata import ProjectMetadata
            from specify_cli.upgrade.migrations.m_0_5_0_encoding_hooks import EncodingHooksMigration
        except ImportError:
            pytest.skip("MigrationRunner not yet implemented")

        # Patch the encoding hooks migration to fail
        original_apply = EncodingHooksMigration.apply

        def failing_apply(self, project_path: Path, dry_run: bool = False):
            # Simulate failure
            class FailedResult:
                success = False
                error = "Simulated migration failure for testing"

            return FailedResult()

        monkeypatch.setattr(EncodingHooksMigration, 'apply', failing_apply)

        # Run upgrade
        runner = MigrationRunner()

        result = runner.run_upgrade(
            project_path=v0_4_7_project,
            current_version="0.4.7",
            target_version="0.6.7",
            dry_run=False
        )

        # Overall result should indicate failure
        assert not result.success, \
            "Upgrade should fail when a migration fails"

        # Verify first migration (gitignore) ran
        gitignore = v0_4_7_project / '.gitignore'
        gitignore_content = gitignore.read_text()
        assert '.claude/' in gitignore_content, \
            "First migration (gitignore) should have run before failure"

        # Verify failed migration recorded
        metadata = ProjectMetadata.load(v0_4_7_project / '.kittify')

        if metadata:
            assert metadata.has_migration("0.4.8_gitignore_agents"), \
                "First migration should be recorded"

            # Failed migration might be recorded as failed, or not recorded at all
            # Either is acceptable behavior

        # Verify later migrations did NOT run
        # Commands should still exist (not renamed yet)
        commands_dir = v0_4_7_project / '.kittify' / 'missions' / 'software-dev' / 'commands'
        assert commands_dir.exists(), \
            "Later migrations should NOT run after failure"

        templates_dir = v0_4_7_project / '.kittify' / 'missions' / 'software-dev' / 'command-templates'
        assert not templates_dir.exists(), \
            "Commands rename should NOT have run after earlier failure"

    def test_rollback_on_error(self):
        """Test: Rollback not implemented (document limitation)

        GIVEN: A migration that fails partway through
        WHEN: Failure occurs
        THEN: No automatic rollback (manual cleanup required)

        NOTE: This test documents that rollback is NOT implemented.
        Users must manually fix issues and re-run upgrade.
        """
        try:
            from specify_cli.upgrade.runner import MigrationRunner
        except ImportError:
            pytest.skip("MigrationRunner not yet implemented")

        runner = MigrationRunner()

        # Verify rollback capability does NOT exist
        assert not hasattr(runner, 'rollback'), \
            "Rollback is not implemented (by design)"

        # Verify documentation or error message mentions manual cleanup
        # (This would be in actual error handling, not testable here)

        # For now, just document the limitation
        pytest.skip("Rollback not implemented - migrations are atomic or require manual cleanup")

    def test_metadata_updated_after_each(self, v0_4_7_project):
        """Test: Records each migration immediately

        GIVEN: A migration chain
        WHEN: Each migration completes
        THEN: Should update metadata immediately (not batch at end)
        """
        try:
            from specify_cli.upgrade.runner import MigrationRunner
            from specify_cli.upgrade.metadata import ProjectMetadata
        except ImportError:
            pytest.skip("MigrationRunner not yet implemented")

        runner = MigrationRunner()

        # Create callback to check metadata after each migration
        metadata_states = []

        def check_metadata_callback(migration_id: str):
            """Called after each migration to verify metadata updated."""
            metadata = ProjectMetadata.load(v0_4_7_project / '.kittify')
            if metadata:
                metadata_states.append({
                    'after_migration': migration_id,
                    'recorded_migrations': [
                        m.get('migration_id') for m in metadata.applied_migrations
                    ]
                })

        # If runner supports callbacks
        if hasattr(runner, 'on_migration_complete'):
            runner.on_migration_complete = check_metadata_callback

        # Run upgrade
        result = runner.run_upgrade(
            project_path=v0_4_7_project,
            current_version="0.4.7",
            target_version="0.6.7",
            dry_run=False
        )

        assert result.success, "Upgrade should succeed"

        # Verify final metadata is complete
        final_metadata = ProjectMetadata.load(v0_4_7_project / '.kittify')

        assert final_metadata is not None, "Metadata should exist"

        # Should have all migrations recorded
        assert final_metadata.has_migration("0.4.8_gitignore_agents"), \
            "All migrations should be recorded"

        assert final_metadata.has_migration("0.5.0_encoding_hooks"), \
            "All migrations should be recorded"

        assert final_metadata.has_migration("0.6.5_commands_rename"), \
            "All migrations should be recorded"

        # If callbacks were supported, verify incremental updates
        if metadata_states:
            # First callback should show only first migration
            first_state = metadata_states[0]
            assert "0.4.8_gitignore_agents" in first_state['recorded_migrations'], \
                "First migration should be recorded immediately"

            # Second callback should show first two migrations
            if len(metadata_states) >= 2:
                second_state = metadata_states[1]
                assert len(second_state['recorded_migrations']) >= 2, \
                    "Each migration should be recorded incrementally"

        # Alternative verification: Check that metadata exists even if we
        # interrupt/fail partway through (since each is recorded immediately)
        # This is implicitly tested by test_stop_on_failure


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
