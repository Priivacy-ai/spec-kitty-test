"""
Test ProjectMetadata Class

Tests the core metadata system that tracks:
- Project version
- Initialization and upgrade timestamps
- Platform information
- Applied migrations with results

Test Coverage:
1. Metadata I/O (4 tests)
   - Create new metadata
   - Save and load round-trip
   - Handle missing metadata
   - Handle malformed metadata

2. Migration Tracking (4 tests)
   - Check if migration applied
   - Record successful migration
   - Record failed migration
   - Maintain migration chronology

Dependencies: This tests the FOUNDATION of the upgrade system.
All other upgrade tests depend on metadata working correctly.
"""

import platform
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest


# Note: These tests will work once the metadata module is implemented
# For now, they serve as specifications for what the API should be


class TestMetadataIO:
    """Test creating, saving, and loading metadata files."""

    def test_create_new_metadata(self, tmp_path):
        """Test: Create metadata with version, timestamps, platform info

        GIVEN: A fresh project with no metadata
        WHEN: Creating new ProjectMetadata instance
        THEN: It should capture all required fields correctly
        """
        try:
            from specify_cli.upgrade.metadata import ProjectMetadata
        except ImportError:
            pytest.skip("ProjectMetadata not yet implemented")

        # Create new metadata
        metadata = ProjectMetadata(
            version="0.6.7",
            initialized_at=datetime.now(),
            python_version=platform.python_version(),
            platform=sys.platform,
            platform_version=platform.platform()
        )

        # Verify all fields set correctly
        assert metadata.version == "0.6.7", \
            "Version should match what was set"

        assert isinstance(metadata.initialized_at, datetime), \
            "initialized_at should be datetime object"

        assert metadata.last_upgraded_at is None, \
            "last_upgraded_at should be None for new metadata"

        assert metadata.python_version == platform.python_version(), \
            "Python version should match system Python"

        assert metadata.platform == sys.platform, \
            f"Platform should be {sys.platform}"

        assert metadata.applied_migrations == [], \
            "New metadata should have empty migrations list"

    def test_save_and_load_metadata(self, tmp_path):
        """Test: Round-trip save/load from .kittify/metadata.yaml

        GIVEN: A ProjectMetadata instance with data
        WHEN: Saving to disk and loading back
        THEN: All data should be preserved exactly
        """
        try:
            from specify_cli.upgrade.metadata import ProjectMetadata
        except ImportError:
            pytest.skip("ProjectMetadata not yet implemented")

        kittify_dir = tmp_path / '.kittify'
        kittify_dir.mkdir()

        # Create metadata with test data
        original = ProjectMetadata(
            version="0.6.7",
            initialized_at=datetime(2025, 1, 1, 10, 30, 0),
            last_upgraded_at=datetime(2025, 1, 15, 14, 0, 0),
            python_version="3.11.5",
            platform="darwin",
            platform_version="Darwin 24.5.0"
        )

        # Add some migration records
        original.record_migration("0.6.5_commands_rename", "success")
        original.record_migration("0.4.8_gitignore_agents", "success")

        # Save to disk
        original.save(kittify_dir)

        # Verify file was created
        metadata_file = kittify_dir / 'metadata.yaml'
        assert metadata_file.exists(), \
            "metadata.yaml should be created"

        # Load back from disk
        loaded = ProjectMetadata.load(kittify_dir)

        # Verify all fields match
        assert loaded is not None, \
            "Load should succeed and return ProjectMetadata instance"

        assert loaded.version == original.version, \
            "Version should match"

        assert loaded.initialized_at == original.initialized_at, \
            "Initialization timestamp should match"

        assert loaded.last_upgraded_at == original.last_upgraded_at, \
            "Last upgraded timestamp should match"

        assert loaded.python_version == original.python_version, \
            "Python version should match"

        assert loaded.platform == original.platform, \
            "Platform should match"

        assert loaded.platform_version == original.platform_version, \
            "Platform version should match"

        assert len(loaded.applied_migrations) == 2, \
            "Should have 2 recorded migrations"

        # Check migration records preserved
        assert loaded.has_migration("0.6.5_commands_rename"), \
            "Should have commands_rename migration"

        assert loaded.has_migration("0.4.8_gitignore_agents"), \
            "Should have gitignore_agents migration"

    def test_load_missing_metadata(self, tmp_path):
        """Test: Returns None when file doesn't exist

        GIVEN: A directory with no metadata.yaml
        WHEN: Attempting to load metadata
        THEN: Should return None (not raise exception)
        """
        try:
            from specify_cli.upgrade.metadata import ProjectMetadata
        except ImportError:
            pytest.skip("ProjectMetadata not yet implemented")

        kittify_dir = tmp_path / '.kittify'
        kittify_dir.mkdir()

        # Try to load non-existent metadata
        metadata = ProjectMetadata.load(kittify_dir)

        assert metadata is None, \
            "Loading missing metadata should return None, not raise exception"

        # Verify no file was created
        metadata_file = kittify_dir / 'metadata.yaml'
        assert not metadata_file.exists(), \
            "Load should not create file if it doesn't exist"

    def test_load_malformed_metadata(self, tmp_path, corrupt_metadata):
        """Test: Handles corrupted YAML gracefully

        GIVEN: A corrupted metadata.yaml file
        WHEN: Attempting to load
        THEN: Should return None or raise clear error (not crash)
        """
        try:
            from specify_cli.upgrade.metadata import ProjectMetadata
        except ImportError:
            pytest.skip("ProjectMetadata not yet implemented")

        kittify_dir = tmp_path / '.kittify'
        kittify_dir.mkdir()

        # Create corrupted metadata file
        corrupt_metadata(tmp_path, 'invalid_yaml')

        # Attempt to load corrupted metadata
        # Implementation should handle this gracefully
        try:
            metadata = ProjectMetadata.load(kittify_dir)

            # If it returns something, it should be None (couldn't parse)
            assert metadata is None, \
                "Loading corrupted metadata should return None"

        except Exception as e:
            # If it raises, should be a clear, specific error
            assert 'yaml' in str(e).lower() or 'parse' in str(e).lower(), \
                f"Error should mention YAML or parsing issue. Got: {e}"


class TestMigrationTracking:
    """Test recording and querying migration application history."""

    def test_has_migration(self, tmp_path):
        """Test: Check if migration was applied

        GIVEN: Metadata with some migrations recorded
        WHEN: Checking for specific migration IDs
        THEN: Should correctly report which migrations are applied
        """
        try:
            from specify_cli.upgrade.metadata import ProjectMetadata
        except ImportError:
            pytest.skip("ProjectMetadata not yet implemented")

        metadata = ProjectMetadata(
            version="0.6.7",
            initialized_at=datetime.now(),
            python_version="3.11",
            platform="darwin",
            platform_version="Darwin 24.5.0"
        )

        # Initially no migrations
        assert not metadata.has_migration("0.6.5_commands_rename"), \
            "Should not have migration before it's recorded"

        # Record a migration
        metadata.record_migration("0.6.5_commands_rename", "success")

        # Now should have it
        assert metadata.has_migration("0.6.5_commands_rename"), \
            "Should have migration after recording"

        # Should not have other migrations
        assert not metadata.has_migration("0.4.8_gitignore_agents"), \
            "Should not have migrations that weren't recorded"

    def test_record_migration(self, tmp_path):
        """Test: Record successful migration

        GIVEN: Metadata instance
        WHEN: Recording a successful migration
        THEN: Migration should be added to applied_migrations list
        """
        try:
            from specify_cli.upgrade.metadata import ProjectMetadata
        except ImportError:
            pytest.skip("ProjectMetadata not yet implemented")

        metadata = ProjectMetadata(
            version="0.6.7",
            initialized_at=datetime.now(),
            python_version="3.11",
            platform="darwin",
            platform_version="Darwin 24.5.0"
        )

        # Record migration
        migration_id = "0.6.5_commands_rename"
        before_time = datetime.now()

        metadata.record_migration(migration_id, "success")

        after_time = datetime.now()

        # Verify migration recorded
        assert len(metadata.applied_migrations) == 1, \
            "Should have 1 migration recorded"

        migration_record = metadata.applied_migrations[0]

        assert migration_record['id'] == migration_id, \
            "Migration ID should match"

        assert migration_record['result'] == 'success', \
            "Result should be 'success'"

        # Verify timestamp is reasonable (between before and after)
        applied_at = migration_record['applied_at']
        assert isinstance(applied_at, datetime), \
            "applied_at should be datetime"

        assert before_time <= applied_at <= after_time + timedelta(seconds=1), \
            "Timestamp should be within expected range"

    def test_record_failed_migration(self, tmp_path):
        """Test: Track failed migration attempts

        GIVEN: Metadata instance
        WHEN: Recording a failed migration
        THEN: Migration should be recorded with 'failed' result
        """
        try:
            from specify_cli.upgrade.metadata import ProjectMetadata
        except ImportError:
            pytest.skip("ProjectMetadata not yet implemented")

        metadata = ProjectMetadata(
            version="0.6.7",
            initialized_at=datetime.now(),
            python_version="3.11",
            platform="darwin",
            platform_version="Darwin 24.5.0"
        )

        # Record failed migration
        migration_id = "0.6.5_commands_rename"
        metadata.record_migration(migration_id, "failed")

        # Verify recorded as failed
        assert len(metadata.applied_migrations) == 1, \
            "Failed migration should still be recorded"

        migration_record = metadata.applied_migrations[0]

        assert migration_record['id'] == migration_id, \
            "Migration ID should match"

        assert migration_record['result'] == 'failed', \
            "Result should be 'failed'"

        # Failed migration should still be in history
        # (but has_migration might return False for failed ones,
        # depending on implementation choice)

    def test_migration_chronology(self, tmp_path):
        """Test: Migrations recorded in order

        GIVEN: Metadata instance
        WHEN: Recording multiple migrations
        THEN: They should be in chronological order in the list
        """
        try:
            from specify_cli.upgrade.metadata import ProjectMetadata
        except ImportError:
            pytest.skip("ProjectMetadata not yet implemented")

        metadata = ProjectMetadata(
            version="0.6.7",
            initialized_at=datetime.now(),
            python_version="3.11",
            platform="darwin",
            platform_version="Darwin 24.5.0"
        )

        # Record migrations in order (simulating upgrade process)
        migrations = [
            "0.2.0_specify_to_kittify",
            "0.4.8_gitignore_agents",
            "0.5.0_encoding_hooks",
            "0.6.5_commands_rename"
        ]

        for migration_id in migrations:
            metadata.record_migration(migration_id, "success")
            # Small delay to ensure different timestamps
            import time
            time.sleep(0.01)

        # Verify all recorded
        assert len(metadata.applied_migrations) == 4, \
            "Should have all 4 migrations recorded"

        # Verify chronological order
        recorded_ids = [m['id'] for m in metadata.applied_migrations]
        assert recorded_ids == migrations, \
            "Migrations should be in chronological order"

        # Verify timestamps are also increasing
        timestamps = [m['applied_at'] for m in metadata.applied_migrations]
        for i in range(len(timestamps) - 1):
            assert timestamps[i] < timestamps[i + 1], \
                f"Timestamp {i} should be less than timestamp {i+1}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
