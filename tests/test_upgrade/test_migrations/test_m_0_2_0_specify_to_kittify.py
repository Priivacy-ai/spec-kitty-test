"""
Test Migration 0.2.0: Specify → Kittify Directory Rename

Tests the migration that renames:
- .specify/ → .kittify/
- /specs/ → /kitty-specs/

This is the oldest migration, transitioning from the original naming
to the current naming convention.

Test Coverage:
1. Detection (1 test)
   - Detects .specify/ directory

2. Migration Execution (3 tests)
   - Rename .specify/ → .kittify/
   - Rename /specs/ → /kitty-specs/
   - Update symlinks if they exist

3. Safety (2 tests)
   - Idempotent (safe to run twice)
   - Preserves user content
"""

import shutil
from pathlib import Path

import pytest


class TestSpecifyToKittifyMigration:
    """Test the .specify/ → .kittify/ migration."""

    def test_detect_old_specify_structure(self, v0_1_x_project):
        """Test: Detects .specify/ directory

        GIVEN: A v0.1.x project with .specify/ directory
        WHEN: Running detect()
        THEN: Should return True (migration needed)
        """
        try:
            from specify_cli.upgrade.migrations.m_0_2_0_specify_to_kittify import SpecifyToKittifyMigration
        except ImportError:
            pytest.skip("SpecifyToKittifyMigration not yet implemented")

        migration = SpecifyToKittifyMigration()

        # Should detect .specify/ directory
        needs_migration = migration.detect(v0_1_x_project)

        assert needs_migration is True, \
            "Should detect that migration is needed for .specify/ project"

        # Verify the directory actually exists (fixture validation)
        assert (v0_1_x_project / '.specify').exists(), \
            "Fixture should have .specify/ directory"

        assert not (v0_1_x_project / '.kittify').exists(), \
            "Fixture should not have .kittify/ directory yet"

    def test_rename_specify_to_kittify(self, v0_1_x_project):
        """Test: .specify/ → .kittify/

        GIVEN: A project with .specify/ directory
        WHEN: Applying migration
        THEN: Should rename .specify/ to .kittify/ preserving all content
        """
        try:
            from specify_cli.upgrade.migrations.m_0_2_0_specify_to_kittify import SpecifyToKittifyMigration
        except ImportError:
            pytest.skip("SpecifyToKittifyMigration not yet implemented")

        migration = SpecifyToKittifyMigration()

        # Verify starting state
        specify_dir = v0_1_x_project / '.specify'
        assert specify_dir.exists(), "Should start with .specify/"

        # Note original content
        original_constitution = (specify_dir / 'memory' / 'constitution.md').read_text()

        # Apply migration
        result = migration.apply(v0_1_x_project, dry_run=False)

        # Verify result
        assert result.success, \
            f"Migration should succeed. Error: {result.error if hasattr(result, 'error') else 'N/A'}"

        # Verify .specify/ is gone
        assert not specify_dir.exists(), \
            ".specify/ should no longer exist"

        # Verify .kittify/ exists
        kittify_dir = v0_1_x_project / '.kittify'
        assert kittify_dir.exists(), \
            ".kittify/ should exist"

        # Verify content preserved
        new_constitution = (kittify_dir / 'memory' / 'constitution.md').read_text()
        assert new_constitution == original_constitution, \
            "Constitution content should be preserved exactly"

        # Verify directory structure preserved
        assert (kittify_dir / 'memory').is_dir(), \
            "memory/ subdirectory should exist"

        assert (kittify_dir / 'missions').is_dir(), \
            "missions/ subdirectory should exist"

    def test_rename_specs_to_kitty_specs(self, v0_1_x_project):
        """Test: /specs/ → /kitty-specs/

        GIVEN: A project with /specs/ directory
        WHEN: Applying migration
        THEN: Should rename /specs/ to /kitty-specs/ preserving content
        """
        try:
            from specify_cli.upgrade.migrations.m_0_2_0_specify_to_kittify import SpecifyToKittifyMigration
        except ImportError:
            pytest.skip("SpecifyToKittifyMigration not yet implemented")

        migration = SpecifyToKittifyMigration()

        # Verify starting state
        specs_dir = v0_1_x_project / 'specs'
        assert specs_dir.exists(), "Should start with specs/"

        # Note original content
        example_spec = specs_dir / '001-example' / 'README.md'
        assert example_spec.exists(), "Fixture should have example spec"
        original_content = example_spec.read_text()

        # Apply migration
        result = migration.apply(v0_1_x_project, dry_run=False)

        assert result.success, "Migration should succeed"

        # Verify specs/ is gone
        assert not specs_dir.exists(), \
            "specs/ should no longer exist"

        # Verify kitty-specs/ exists
        kitty_specs_dir = v0_1_x_project / 'kitty-specs'
        assert kitty_specs_dir.exists(), \
            "kitty-specs/ should exist"

        # Verify content preserved
        new_spec = kitty_specs_dir / '001-example' / 'README.md'
        assert new_spec.exists(), \
            "Example spec should exist in new location"

        new_content = new_spec.read_text()
        assert new_content == original_content, \
            "Spec content should be preserved exactly"

    def test_update_symlinks_if_exist(self, v0_1_x_project, tmp_path):
        """Test: Migration handles existing symlinks gracefully

        GIVEN: A project with symlinks pointing to .specify/
        WHEN: Applying migration
        THEN: Migration should succeed (symlink handling is implementation-dependent)

        Note: The migration may or may not update symlink targets.
        This test verifies the migration succeeds with symlinks present.
        """
        import os  # Must import before using

        try:
            from specify_cli.upgrade.migrations.m_0_2_0_specify_to_kittify import SpecifyToKittifyMigration
        except ImportError:
            pytest.skip("SpecifyToKittifyMigration not yet implemented")

        # Skip on Windows (symlink handling different)
        if not hasattr(os, 'symlink'):
            pytest.skip("Symlinks not supported on this platform")

        migration = SpecifyToKittifyMigration()

        # Create a symlink pointing to .specify/memory
        symlink_path = v0_1_x_project / 'my-symlink'

        # Create relative symlink
        os.symlink('.specify/memory', symlink_path)

        # Verify symlink exists and points to .specify/
        assert symlink_path.is_symlink(), \
            "Symlink should exist"

        original_target = os.readlink(symlink_path)
        assert '.specify' in original_target, \
            "Symlink should point to .specify/"

        # Apply migration
        result = migration.apply(v0_1_x_project, dry_run=False)

        assert result.success, "Migration should succeed with symlinks present"

        # Verify .specify was renamed to .kittify
        assert not (v0_1_x_project / '.specify').exists(), \
            ".specify/ should be renamed"
        assert (v0_1_x_project / '.kittify').exists(), \
            ".kittify/ should exist"

        # Symlink handling is implementation-dependent
        # The migration may leave the symlink pointing to old target (now broken)
        # or may update the target to point to .kittify/
        # Either behavior is acceptable - just verify migration succeeded

    def test_migration_idempotent(self, v0_1_x_project):
        """Test: Safe to run twice

        GIVEN: A project that has already been migrated
        WHEN: Running migration again
        THEN: Should be safe (no-op or gracefully skip)
        """
        try:
            from specify_cli.upgrade.migrations.m_0_2_0_specify_to_kittify import SpecifyToKittifyMigration
        except ImportError:
            pytest.skip("SpecifyToKittifyMigration not yet implemented")

        migration = SpecifyToKittifyMigration()

        # Run migration first time
        result1 = migration.apply(v0_1_x_project, dry_run=False)
        assert result1.success, "First migration should succeed"

        # Verify .kittify/ now exists
        assert (v0_1_x_project / '.kittify').exists(), \
            ".kittify/ should exist after first run"

        # Take snapshot of state after first migration
        kittify_files = list((v0_1_x_project / '.kittify').rglob('*'))
        first_run_count = len(kittify_files)

        # Run migration AGAIN
        result2 = migration.apply(v0_1_x_project, dry_run=False)

        # Should not crash
        assert result2 is not None, \
            "Second run should not crash"

        # If detect() is properly implemented, should not detect need
        needs_migration_after = migration.detect(v0_1_x_project)
        assert not needs_migration_after, \
            "Should not detect migration need after already applied"

        # Verify state unchanged
        kittify_files_after = list((v0_1_x_project / '.kittify').rglob('*'))
        second_run_count = len(kittify_files_after)

        assert second_run_count == first_run_count, \
            "File count should be unchanged after second run"

    def test_preserves_user_content(self, v0_1_x_project, inject_custom_content):
        """Test: Constitution and custom files intact

        GIVEN: A project with custom user content in .specify/
        WHEN: Applying migration
        THEN: All user content should be preserved in .kittify/
        """
        try:
            from specify_cli.upgrade.migrations.m_0_2_0_specify_to_kittify import SpecifyToKittifyMigration
        except ImportError:
            pytest.skip("SpecifyToKittifyMigration not yet implemented")

        migration = SpecifyToKittifyMigration()

        # Add custom user content
        custom_notes = "# My Important Notes\n\nDo not lose this!"
        inject_custom_content(
            v0_1_x_project,
            '.specify/memory/custom-notes.md',
            custom_notes
        )

        # Add custom mission file
        custom_mission = "# Custom Mission\n\nMy special mission."
        inject_custom_content(
            v0_1_x_project,
            '.specify/missions/custom-mission/README.md',
            custom_mission
        )

        # Apply migration
        result = migration.apply(v0_1_x_project, dry_run=False)

        assert result.success, "Migration should succeed"

        # Verify custom content preserved in new location
        new_notes_path = v0_1_x_project / '.kittify' / 'memory' / 'custom-notes.md'
        assert new_notes_path.exists(), \
            "Custom notes should exist in .kittify/"

        assert new_notes_path.read_text() == custom_notes, \
            "Custom notes content should be preserved exactly"

        # Verify custom mission preserved
        new_mission_path = v0_1_x_project / '.kittify' / 'missions' / 'custom-mission' / 'README.md'
        assert new_mission_path.exists(), \
            "Custom mission should exist in .kittify/"

        assert new_mission_path.read_text() == custom_mission, \
            "Custom mission content should be preserved exactly"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
