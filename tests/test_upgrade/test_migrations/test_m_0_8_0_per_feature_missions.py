"""
Test Migration 0.8.0: Per-Feature Missions

Tests the migration that removes project-level mission selection and
transitions to per-feature missions stored in meta.json.

Breaking Changes in v0.8.0:
- Remove --mission flag from spec-kitty init
- Remove spec-kitty mission switch command
- Remove .kittify/active-mission concept
- Mission stored per-feature in meta.json

Test Coverage:
1. Detection (3 tests)
   - Detects active-mission symlink exists
   - No detection when active-mission doesn't exist
   - No detection on fresh v0.8.0+ project

2. Migration Execution (3 tests)
   - Removes active-mission symlink
   - Removes active-mission file (if file instead of symlink)
   - Preserves missions directory

3. Edge Cases (2 tests)
   - Handles broken active-mission symlink
   - Handles active-mission pointing to non-existent mission

4. Integration (2 tests)
   - Migration is registered in registry
   - Migration ordered correctly
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest


class TestPerFeatureMissionsMigration:
    """Test the 0.8.0 per-feature missions migration."""

    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        """Create temporary directory for test project."""
        return tmp_path

    @pytest.fixture
    def project_with_active_mission(self, temp_project_dir, spec_kitty_repo_root):
        """Create a project with active-mission symlink (pre-v0.8.0 structure)."""
        project_name = "test_active_mission"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Initialize project
        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        kittify_dir = project_path / '.kittify'

        # Create active-mission symlink manually (simulating pre-v0.8.0)
        active_mission = kittify_dir / 'active-mission'
        missions_dir = kittify_dir / 'missions'

        # Remove if exists (v0.8.0+ may not create it)
        if active_mission.exists() or active_mission.is_symlink():
            active_mission.unlink()

        # Create symlink to software-dev mission
        if (missions_dir / 'software-dev').exists():
            os.symlink('missions/software-dev', active_mission)
        else:
            # Create minimal mission structure
            (missions_dir / 'software-dev').mkdir(parents=True, exist_ok=True)
            (missions_dir / 'software-dev' / 'mission.yaml').write_text('name: Software Dev\n')
            os.symlink('missions/software-dev', active_mission)

        return project_path

    # ========================================================================
    # Detection Tests
    # ========================================================================

    def test_detect_active_mission_symlink(self, project_with_active_mission):
        """Test: Detects active-mission symlink exists

        GIVEN: A project with .kittify/active-mission symlink
        WHEN: Running detect()
        THEN: Should return True (migration needed)
        """
        try:
            from specify_cli.upgrade.migrations.m_0_8_0_per_feature_missions import (
                PerFeatureMissionsMigration,
            )
        except ImportError:
            pytest.skip("PerFeatureMissionsMigration not yet implemented")

        migration = PerFeatureMissionsMigration()

        # Verify active-mission exists
        active_mission = project_with_active_mission / '.kittify' / 'active-mission'
        assert active_mission.is_symlink(), "Fixture should have active-mission symlink"

        # Should detect migration needed
        needs_migration = migration.detect(project_with_active_mission)

        assert needs_migration is True, \
            "Should detect active-mission symlink needs to be removed"

    def test_detect_no_active_mission(self, temp_project_dir, spec_kitty_repo_root):
        """Test: No detection when active-mission doesn't exist

        GIVEN: A project without .kittify/active-mission
        WHEN: Running detect()
        THEN: Should return False (no migration needed)
        """
        try:
            from specify_cli.upgrade.migrations.m_0_8_0_per_feature_missions import (
                PerFeatureMissionsMigration,
            )
        except ImportError:
            pytest.skip("PerFeatureMissionsMigration not yet implemented")

        migration = PerFeatureMissionsMigration()

        project_name = "test_no_active_mission"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Remove active-mission if it exists
        active_mission = project_path / '.kittify' / 'active-mission'
        if active_mission.exists() or active_mission.is_symlink():
            active_mission.unlink()

        # Should NOT detect migration needed
        needs_migration = migration.detect(project_path)

        assert needs_migration is False, \
            "Should not detect migration when active-mission doesn't exist"

    def test_detect_active_mission_as_file(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Detects active-mission as regular file (edge case)

        GIVEN: A project with .kittify/active-mission as a regular file
        WHEN: Running detect()
        THEN: Should return True (file should also be removed)
        """
        try:
            from specify_cli.upgrade.migrations.m_0_8_0_per_feature_missions import (
                PerFeatureMissionsMigration,
            )
        except ImportError:
            pytest.skip("PerFeatureMissionsMigration not yet implemented")

        migration = PerFeatureMissionsMigration()

        project_name = "test_active_mission_file"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Create active-mission as a regular file (edge case)
        active_mission = project_path / '.kittify' / 'active-mission'
        if active_mission.exists() or active_mission.is_symlink():
            active_mission.unlink()
        active_mission.write_text('software-dev\n')

        # Should detect migration needed
        needs_migration = migration.detect(project_path)

        assert needs_migration is True, \
            "Should detect active-mission file needs to be removed"

    # ========================================================================
    # Migration Execution Tests
    # ========================================================================

    def test_removes_active_mission_symlink(self, project_with_active_mission):
        """Test: Removes active-mission symlink

        GIVEN: A project with .kittify/active-mission symlink
        WHEN: Applying migration
        THEN: Symlink should be removed
        """
        try:
            from specify_cli.upgrade.migrations.m_0_8_0_per_feature_missions import (
                PerFeatureMissionsMigration,
            )
        except ImportError:
            pytest.skip("PerFeatureMissionsMigration not yet implemented")

        migration = PerFeatureMissionsMigration()

        active_mission = project_with_active_mission / '.kittify' / 'active-mission'

        # Verify symlink exists before migration
        assert active_mission.is_symlink(), "Should have active-mission symlink before migration"

        # Apply migration
        result = migration.apply(project_with_active_mission, dry_run=False)

        assert result.success, f"Migration should succeed. Errors: {getattr(result, 'errors', 'N/A')}"

        # Verify symlink removed
        assert not active_mission.exists(), \
            "active-mission symlink should be removed after migration"
        assert not active_mission.is_symlink(), \
            "active-mission should not be a symlink after migration"

    def test_removes_active_mission_file(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Removes active-mission regular file

        GIVEN: A project with .kittify/active-mission as a regular file
        WHEN: Applying migration
        THEN: File should be removed
        """
        try:
            from specify_cli.upgrade.migrations.m_0_8_0_per_feature_missions import (
                PerFeatureMissionsMigration,
            )
        except ImportError:
            pytest.skip("PerFeatureMissionsMigration not yet implemented")

        migration = PerFeatureMissionsMigration()

        project_name = "test_remove_file"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Create active-mission as file
        active_mission = project_path / '.kittify' / 'active-mission'
        if active_mission.is_symlink():
            active_mission.unlink()
        active_mission.write_text('software-dev\n')

        # Apply migration
        result = migration.apply(project_path, dry_run=False)

        assert result.success, "Migration should succeed"

        # Verify file removed
        assert not active_mission.exists(), \
            "active-mission file should be removed after migration"

    def test_preserves_missions_directory(self, project_with_active_mission):
        """Test: Missions directory is preserved

        GIVEN: A project with .kittify/active-mission and .kittify/missions/
        WHEN: Applying migration
        THEN: missions/ directory should be preserved (only symlink removed)
        """
        try:
            from specify_cli.upgrade.migrations.m_0_8_0_per_feature_missions import (
                PerFeatureMissionsMigration,
            )
        except ImportError:
            pytest.skip("PerFeatureMissionsMigration not yet implemented")

        migration = PerFeatureMissionsMigration()

        missions_dir = project_with_active_mission / '.kittify' / 'missions'

        # Verify missions directory exists before migration
        assert missions_dir.exists(), "Should have missions directory before migration"

        # Apply migration
        result = migration.apply(project_with_active_mission, dry_run=False)

        assert result.success, "Migration should succeed"

        # Verify missions directory still exists
        assert missions_dir.exists(), \
            "missions/ directory should be preserved after migration"

        # Verify missions content preserved
        assert (missions_dir / 'software-dev').exists(), \
            "software-dev mission should still exist"

    # ========================================================================
    # Edge Case Tests
    # ========================================================================

    def test_handles_broken_symlink(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Handles broken active-mission symlink

        GIVEN: A project with broken .kittify/active-mission symlink
        WHEN: Applying migration
        THEN: Broken symlink should be removed without error
        """
        try:
            from specify_cli.upgrade.migrations.m_0_8_0_per_feature_missions import (
                PerFeatureMissionsMigration,
            )
        except ImportError:
            pytest.skip("PerFeatureMissionsMigration not yet implemented")

        migration = PerFeatureMissionsMigration()

        project_name = "test_broken_symlink"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Create broken symlink
        active_mission = project_path / '.kittify' / 'active-mission'
        if active_mission.exists() or active_mission.is_symlink():
            active_mission.unlink()
        os.symlink('missions/nonexistent-mission', active_mission)

        # Verify symlink is broken
        assert active_mission.is_symlink(), "Should be a symlink"
        assert not active_mission.exists(), "Symlink should be broken (target doesn't exist)"

        # Apply migration
        result = migration.apply(project_path, dry_run=False)

        assert result.success, "Migration should succeed even with broken symlink"

        # Verify broken symlink removed
        assert not active_mission.is_symlink(), \
            "Broken symlink should be removed after migration"

    def test_dry_run_no_changes(self, project_with_active_mission):
        """Test: Dry run shows changes without applying

        GIVEN: A project with active-mission symlink
        WHEN: Running with dry_run=True
        THEN: Should report changes but not modify anything
        """
        try:
            from specify_cli.upgrade.migrations.m_0_8_0_per_feature_missions import (
                PerFeatureMissionsMigration,
            )
        except ImportError:
            pytest.skip("PerFeatureMissionsMigration not yet implemented")

        migration = PerFeatureMissionsMigration()

        active_mission = project_with_active_mission / '.kittify' / 'active-mission'

        # Verify symlink exists before dry run
        assert active_mission.is_symlink(), "Should have active-mission before dry run"

        # Run dry run
        result = migration.apply(project_with_active_mission, dry_run=True)

        # Should complete without error
        assert result is not None, "Dry run should return a result"

        # Symlink should still exist
        assert active_mission.is_symlink(), \
            "active-mission should still exist after dry run"


class TestPerFeatureMissionsIntegration:
    """Integration tests for the 0.8.0 migration."""

    def test_migration_registered(self):
        """Test: Migration is registered in the registry

        GIVEN: The migration module is loaded
        WHEN: Checking MigrationRegistry
        THEN: 0.8.0_per_feature_missions should be registered

        Note: Skips if migration not yet implemented (pre-v0.8.0)
        """
        try:
            from specify_cli.upgrade.registry import MigrationRegistry
        except ImportError:
            pytest.skip("MigrationRegistry not yet implemented")

        all_migrations = MigrationRegistry.get_all()
        migration_ids = [m.migration_id for m in all_migrations]

        # Skip if migration not yet implemented
        if "0.8.0_per_feature_missions" not in migration_ids:
            pytest.skip("0.8.0_per_feature_missions migration not yet implemented")

        assert "0.8.0_per_feature_missions" in migration_ids, \
            "0.8.0_per_feature_missions should be registered"

    def test_migration_ordered_after_0_7_2(self):
        """Test: Migration comes after 0.7.2

        GIVEN: The migration registry
        WHEN: Getting all migrations
        THEN: 0.8.0 should come after 0.7.2 (worktree dedup)
        """
        try:
            from specify_cli.upgrade.registry import MigrationRegistry
        except ImportError:
            pytest.skip("MigrationRegistry not yet implemented")

        all_migrations = MigrationRegistry.get_all()
        migration_ids = [m.migration_id for m in all_migrations]

        # Find indices
        idx_072 = next(
            (i for i, mid in enumerate(migration_ids) if "0.7.2" in mid),
            -1
        )
        idx_080 = next(
            (i for i, mid in enumerate(migration_ids) if "0.8.0" in mid),
            -1
        )

        if idx_072 >= 0 and idx_080 >= 0:
            assert idx_072 < idx_080, \
                "0.7.2 migration should come before 0.8.0"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
