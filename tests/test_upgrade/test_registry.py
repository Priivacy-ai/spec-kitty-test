"""
Test Migration Registry

Tests the registry system that discovers, validates, and manages
all migration classes.

The MigrationRegistry:
- Discovers all migration classes (via decorator or auto-discovery)
- Validates migration metadata (ID, version, description)
- Returns migrations in chronological order
- Filters migrations by version range
- Prevents duplicate migration IDs
- Ensures migrations meet interface requirements

Test Coverage:
1. Registration (2 tests)
   - Register migration via decorator
   - Get all registered migrations

2. Filtering (1 test)
   - Get applicable migrations for version range

3. Ordering (1 test)
   - Migrations returned in chronological order

4. Validation (2 tests)
   - Duplicate ID error
   - Missing target version validation
"""

from pathlib import Path

import pytest


class TestMigrationRegistry:
    """Test the migration registry and discovery system."""

    def test_register_migration(self):
        """Test: Decorator registers migration class

        GIVEN: A migration class with @register decorator
        WHEN: Module is imported
        THEN: Migration should be registered in registry
        """
        try:
            from specify_cli.upgrade.migrations.base import BaseMigration
            from specify_cli.upgrade.registry import MigrationRegistry, register
        except ImportError:
            pytest.skip("MigrationRegistry not yet implemented")

        # Save original registry for restoration
        original_migrations = None
        if hasattr(MigrationRegistry, '_migrations'):
            original_migrations = MigrationRegistry._migrations.copy()
            MigrationRegistry._migrations = {}

        try:
            # Create and register a test migration
            @register
            class TestRegistrationMigration(BaseMigration):
                migration_id = "test_registration"
                description = "Test migration for registration"
                target_version = "0.6.7"

                def detect(self, project_path: Path) -> bool:
                    return False

                def can_apply(self, project_path: Path) -> tuple:
                    return (True, "")

                def apply(self, project_path: Path, dry_run: bool = False):
                    pass

            # Verify migration is registered
            all_migrations = MigrationRegistry.get_all()

            migration_ids = [m.migration_id for m in all_migrations]

            assert "test_registration" in migration_ids, \
                "Registered migration should appear in registry"

            # Verify we can retrieve it
            test_migration = next(
                (m for m in all_migrations if m.migration_id == "test_registration"),
                None
            )

            assert test_migration is not None, \
                "Should be able to retrieve registered migration"

            assert test_migration.description == "Test migration for registration", \
                "Migration metadata should be preserved"

            assert test_migration.target_version == "0.6.7", \
                "Target version should be preserved"

        finally:
            # Restore original registry
            if original_migrations is not None:
                MigrationRegistry._migrations = original_migrations

    def test_get_all_migrations(self):
        """Test: Returns all registered migrations

        GIVEN: Multiple migrations registered
        WHEN: Calling get_all()
        THEN: Should return all migrations
        """
        try:
            from specify_cli.upgrade.registry import MigrationRegistry
        except ImportError:
            pytest.skip("MigrationRegistry not yet implemented")

        # Get all migrations (includes all real migrations from the codebase)
        all_migrations = MigrationRegistry.get_all()

        assert len(all_migrations) >= 4, \
            f"Should have at least 4 migrations (0.2.0, 0.4.8, 0.5.0, 0.6.5), found {len(all_migrations)}"

        # Verify all migrations have required fields
        for migration in all_migrations:
            assert hasattr(migration, 'migration_id'), \
                f"Migration {migration} should have migration_id"

            assert hasattr(migration, 'description'), \
                f"Migration {migration.migration_id} should have description"

            assert hasattr(migration, 'target_version'), \
                f"Migration {migration.migration_id} should have target_version"

            # Verify migration_id is unique
            matching_migrations = [
                m for m in all_migrations
                if m.migration_id == migration.migration_id
            ]

            assert len(matching_migrations) == 1, \
                f"Migration ID '{migration.migration_id}' should be unique"

        # Verify specific expected migrations exist
        expected_migrations = [
            "0.2.0_specify_to_kittify",
            "0.4.8_gitignore_agents",
            "0.5.0_encoding_hooks",
            "0.6.5_commands_rename"
        ]

        migration_ids = [m.migration_id for m in all_migrations]

        for expected_id in expected_migrations:
            assert expected_id in migration_ids, \
                f"Expected migration '{expected_id}' should be registered"

    def test_get_applicable_migrations(self):
        """Test: Filters by version range

        GIVEN: A project at specific version
        WHEN: Getting applicable migrations
        THEN: Should return only migrations needed to reach target
        """
        try:
            from specify_cli.upgrade.registry import MigrationRegistry
        except ImportError:
            pytest.skip("MigrationRegistry not yet implemented")

        # Test: v0.4.7 → current
        # Should need: 0.4.8 (gitignore), 0.5.0 (hooks), 0.6.5 (commands)
        applicable_047 = MigrationRegistry.get_applicable(
            from_version="0.4.7",
            to_version="0.6.7"  # or None for "latest"
        )

        migration_ids_047 = [m.migration_id for m in applicable_047]

        # Should include migrations after 0.4.7
        assert "0.4.8_gitignore_agents" in migration_ids_047, \
            "v0.4.7 → v0.6.7 should include gitignore migration"

        assert "0.5.0_encoding_hooks" in migration_ids_047, \
            "v0.4.7 → v0.6.7 should include hooks migration"

        assert "0.6.5_commands_rename" in migration_ids_047, \
            "v0.4.7 → v0.6.7 should include commands rename"

        # Should NOT include migrations before current version
        assert "0.2.0_specify_to_kittify" not in migration_ids_047, \
            "v0.4.7 → v0.6.7 should NOT include 0.2.0 migration (already on .kittify/)"

        # Test: v0.6.4 → current
        # Should only need: 0.6.5 (commands rename)
        applicable_064 = MigrationRegistry.get_applicable(
            from_version="0.6.4",
            to_version="0.6.7"
        )

        migration_ids_064 = [m.migration_id for m in applicable_064]

        assert "0.6.5_commands_rename" in migration_ids_064, \
            "v0.6.4 → v0.6.7 should include commands rename"

        # Should NOT include earlier migrations
        assert "0.4.8_gitignore_agents" not in migration_ids_064, \
            "v0.6.4 already has gitignore agents"

        assert "0.5.0_encoding_hooks" not in migration_ids_064, \
            "v0.6.4 already has encoding hooks"

        # Verify count is reasonable
        assert len(applicable_064) <= 2, \
            f"v0.6.4 → v0.6.7 should need at most 2 migrations, found {len(applicable_064)}"

        # Test: v0.1.x → current (needs all migrations)
        applicable_01x = MigrationRegistry.get_applicable(
            from_version="0.1.5",
            to_version="0.6.7"
        )

        migration_ids_01x = [m.migration_id for m in applicable_01x]

        # Should include ALL migrations
        assert "0.2.0_specify_to_kittify" in migration_ids_01x, \
            "v0.1.x → v0.6.7 should include specify_to_kittify"

        assert "0.4.8_gitignore_agents" in migration_ids_01x, \
            "v0.1.x → v0.6.7 should include gitignore"

        assert "0.5.0_encoding_hooks" in migration_ids_01x, \
            "v0.1.x → v0.6.7 should include hooks"

        assert "0.6.5_commands_rename" in migration_ids_01x, \
            "v0.1.x → v0.6.7 should include commands rename"

        assert len(applicable_01x) >= 4, \
            f"v0.1.x → v0.6.7 should need at least 4 migrations, found {len(applicable_01x)}"

    def test_migration_ordering(self):
        """Test: Migrations returned in chronological order

        GIVEN: Multiple migrations in registry
        WHEN: Getting all or applicable migrations
        THEN: Should be ordered by target_version (chronologically)
        """
        try:
            from specify_cli.upgrade.registry import MigrationRegistry
        except ImportError:
            pytest.skip("MigrationRegistry not yet implemented")

        # Get all migrations
        all_migrations = MigrationRegistry.get_all()

        # Extract version numbers from migration IDs or target_version
        # Migrations should be named like: "0.2.0_specify_to_kittify"

        # Verify they're in order
        previous_version = "0.0.0"

        for migration in all_migrations:
            current_version = migration.target_version

            # Parse versions for comparison
            # Format: "0.2.0" → (0, 2, 0)
            prev_parts = tuple(map(int, previous_version.split('.')))
            curr_parts = tuple(map(int, current_version.split('.')))

            assert curr_parts >= prev_parts, \
                f"Migrations should be ordered: {previous_version} should come before {current_version}"

            previous_version = current_version

        # Verify specific ordering of known migrations
        migration_ids = [m.migration_id for m in all_migrations]

        # Find indices
        idx_020 = next(
            (i for i, mid in enumerate(migration_ids) if "0.2.0" in mid),
            -1
        )
        idx_048 = next(
            (i for i, mid in enumerate(migration_ids) if "0.4.8" in mid),
            -1
        )
        idx_050 = next(
            (i for i, mid in enumerate(migration_ids) if "0.5.0" in mid),
            -1
        )
        idx_065 = next(
            (i for i, mid in enumerate(migration_ids) if "0.6.5" in mid),
            -1
        )

        # Verify ordering
        if idx_020 >= 0 and idx_048 >= 0:
            assert idx_020 < idx_048, \
                "0.2.0 migration should come before 0.4.8"

        if idx_048 >= 0 and idx_050 >= 0:
            assert idx_048 < idx_050, \
                "0.4.8 migration should come before 0.5.0"

        if idx_050 >= 0 and idx_065 >= 0:
            assert idx_050 < idx_065, \
                "0.5.0 migration should come before 0.6.5"

    def test_duplicate_id_error(self):
        """Test: Raises error for duplicate migration IDs

        GIVEN: Attempting to register migration with duplicate ID
        WHEN: Registration occurs
        THEN: Should raise error preventing duplicate
        """
        try:
            from specify_cli.upgrade.migrations.base import BaseMigration
            from specify_cli.upgrade.registry import MigrationRegistry, register
        except ImportError:
            pytest.skip("MigrationRegistry not yet implemented")

        # First registration should succeed
        @register
        class FirstMigration(BaseMigration):
            migration_id = "duplicate_test_id"
            description = "First migration with this ID"
            target_version = "0.6.7"

            def detect(self, project_path: Path) -> bool:
                return False

            def can_apply(self, project_path: Path) -> tuple:
                return (True, "")

            def apply(self, project_path: Path, dry_run: bool = False):
                pass

        # Second registration with SAME ID should fail
        with pytest.raises((ValueError, RuntimeError, KeyError)):
            @register
            class SecondMigration(BaseMigration):
                migration_id = "duplicate_test_id"  # DUPLICATE!
                description = "Second migration with same ID (should fail)"
                target_version = "0.6.8"

                def detect(self, project_path: Path) -> bool:
                    return False

                def can_apply(self, project_path: Path) -> tuple:
                    return (True, "")

                def apply(self, project_path: Path, dry_run: bool = False):
                    pass

    def test_missing_target_version(self):
        """Test: Validates migration metadata

        GIVEN: Migration class missing required fields
        WHEN: Attempting to register
        THEN: Should raise validation error
        """
        try:
            from specify_cli.upgrade.migrations.base import BaseMigration
            from specify_cli.upgrade.registry import MigrationRegistry, register
        except ImportError:
            pytest.skip("MigrationRegistry not yet implemented")

        # Migration missing target_version
        with pytest.raises((ValueError, AttributeError, TypeError)):
            @register
            class InvalidMigration(BaseMigration):
                migration_id = "invalid_no_version"
                description = "Missing target_version"
                # target_version is MISSING!

                def detect(self, project_path: Path) -> bool:
                    return False

                def can_apply(self, project_path: Path) -> tuple:
                    return (True, "")

                def apply(self, project_path: Path, dry_run: bool = False):
                    pass

            # If decorator doesn't catch it, instantiation should
            migration = InvalidMigration()

        # Migration missing migration_id
        with pytest.raises((ValueError, AttributeError, TypeError)):
            @register
            class InvalidMigration2(BaseMigration):
                # migration_id is MISSING!
                description = "Missing migration_id"
                target_version = "0.6.7"

                def detect(self, project_path: Path) -> bool:
                    return False

                def can_apply(self, project_path: Path) -> tuple:
                    return (True, "")

                def apply(self, project_path: Path, dry_run: bool = False):
                    pass

            migration = InvalidMigration2()

        # Migration missing description (might be warning, not error)
        with pytest.raises((ValueError, AttributeError, TypeError)):
            @register
            class InvalidMigration3(BaseMigration):
                migration_id = "invalid_no_description"
                # description is MISSING!
                target_version = "0.6.7"

                def detect(self, project_path: Path) -> bool:
                    return False

                def can_apply(self, project_path: Path) -> tuple:
                    return (True, "")

                def apply(self, project_path: Path, dry_run: bool = False):
                    pass

            migration = InvalidMigration3()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
