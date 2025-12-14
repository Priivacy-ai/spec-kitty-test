"""
Test BaseMigration Abstract Class

Tests the foundation class that all migrations inherit from.

Test Coverage:
1. Migration Interface (3 tests)
   - Required fields (ID, description, target_version)
   - detect() method required
   - apply() method required

The BaseMigration class defines the contract that all migration
implementations must follow.
"""

from pathlib import Path

import pytest


class TestBaseMigration:
    """Test the BaseMigration abstract class interface."""

    def test_migration_has_required_fields(self):
        """Test: ID, description, target_version required

        GIVEN: The BaseMigration class definition
        WHEN: Creating a migration subclass
        THEN: Must define migration_id, description, target_version
        """
        try:
            from specify_cli.upgrade.migrations.base import BaseMigration
        except ImportError:
            pytest.skip("BaseMigration not yet implemented")

        # Verify class has required attributes documented
        # (Actual enforcement happens when subclass is instantiated)

        # Try to create invalid migration (missing fields)
        with pytest.raises((AttributeError, ValueError, TypeError)):
            class InvalidMigration(BaseMigration):
                # Missing required fields!
                pass

            instance = InvalidMigration()

        # Create valid migration with all fields
        class ValidMigration(BaseMigration):
            migration_id = "test_migration"
            description = "Test migration for validation"
            target_version = "0.6.7"

            def detect(self, project_path: Path) -> bool:
                return False

            def can_apply(self, project_path: Path) -> tuple:
                return (True, "")

            def apply(self, project_path: Path, dry_run: bool = False):
                pass

        # Should instantiate successfully
        migration = ValidMigration()

        assert migration.migration_id == "test_migration", \
            "Should have migration_id"

        assert migration.description == "Test migration for validation", \
            "Should have description"

        assert migration.target_version == "0.6.7", \
            "Should have target_version"

    def test_detect_method_required(self):
        """Test: detect() abstract method enforced

        GIVEN: BaseMigration class
        WHEN: Creating subclass without detect() method
        THEN: Should raise error or fail type checking
        """
        try:
            from specify_cli.upgrade.migrations.base import BaseMigration
        except ImportError:
            pytest.skip("BaseMigration not yet implemented")

        # Try to create migration without detect() method
        with pytest.raises((TypeError, NotImplementedError)):
            class NoDetectMigration(BaseMigration):
                migration_id = "no_detect"
                description = "Missing detect method"
                target_version = "0.6.7"

                # detect() method is MISSING!

                def can_apply(self, project_path: Path) -> tuple:
                    return (True, "")

                def apply(self, project_path: Path, dry_run: bool = False):
                    pass

            # Instantiating or calling should fail
            migration = NoDetectMigration()
            migration.detect(Path("/tmp"))

    def test_apply_method_required(self):
        """Test: apply() abstract method enforced

        GIVEN: BaseMigration class
        WHEN: Creating subclass without apply() method
        THEN: Should raise error or fail type checking
        """
        try:
            from specify_cli.upgrade.migrations.base import BaseMigration
        except ImportError:
            pytest.skip("BaseMigration not yet implemented")

        # Try to create migration without apply() method
        with pytest.raises((TypeError, NotImplementedError)):
            class NoApplyMigration(BaseMigration):
                migration_id = "no_apply"
                description = "Missing apply method"
                target_version = "0.6.7"

                def detect(self, project_path: Path) -> bool:
                    return True

                def can_apply(self, project_path: Path) -> tuple:
                    return (True, "")

                # apply() method is MISSING!

            # Instantiating or calling should fail
            migration = NoApplyMigration()
            migration.apply(Path("/tmp"))


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
