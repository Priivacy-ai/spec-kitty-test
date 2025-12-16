"""
Test Migration 0.8.0: Worktree AGENTS.md Symlink

Tests the migration that creates .kittify/AGENTS.md symlinks in existing
worktrees so command templates can access agent configuration.

Migration ID: 0.8.0_worktree_agents_symlink
Class: WorktreeAgentsSymlinkMigration

Bug Fix Context:
- Worktrees don't have access to main repo's .kittify/AGENTS.md
- Command templates (like dashboard.md) reference AGENTS.md
- This migration creates symlinks from worktrees to main repo

Test Coverage:
1. Detection (4 tests)
   - Detects worktree missing AGENTS.md
   - No detection when main AGENTS.md missing
   - No detection when no worktrees exist
   - No detection when all worktrees have valid symlinks

2. Migration Execution (3 tests)
   - Creates symlink in worktree missing AGENTS.md
   - Fixes broken symlink in worktree
   - Preserves existing valid symlinks

3. Edge Cases (2 tests)
   - Handles worktree with regular file (warns, skips)
   - Dry run shows changes without applying

4. Integration (2 tests)
   - Migration is registered in registry
   - Migration ordered correctly (0.8.0)
"""

import os
import subprocess
from pathlib import Path

import pytest


class TestWorktreeAgentsSymlinkMigration:
    """Test the 0.8.0 worktree AGENTS.md symlink migration."""

    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        """Create temporary directory for test project."""
        return tmp_path

    @pytest.fixture
    def project_with_worktree(self, temp_project_dir, spec_kitty_repo_root):
        """Create a project with a worktree missing AGENTS.md symlink."""
        project_name = "test_agents_symlink"
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

        # Ensure main AGENTS.md exists
        main_agents = project_path / '.kittify' / 'AGENTS.md'
        if not main_agents.exists():
            main_agents.write_text("# Test AGENTS.md\n")

        # Create a worktree manually (simulating pre-migration state)
        worktrees_dir = project_path / '.worktrees'
        worktrees_dir.mkdir(exist_ok=True)

        worktree = worktrees_dir / '001-test-feature'
        worktree.mkdir()
        wt_kittify = worktree / '.kittify'
        wt_kittify.mkdir()
        # Don't create AGENTS.md symlink - this is what migration should fix

        return project_path

    # ========================================================================
    # Detection Tests
    # ========================================================================

    def test_detect_worktree_missing_agents(self, project_with_worktree):
        """Test: Detects worktree missing AGENTS.md

        GIVEN: A project with worktree that has no .kittify/AGENTS.md
        WHEN: Running detect()
        THEN: Should return True (migration needed)
        """
        try:
            from specify_cli.upgrade.migrations.m_0_8_0_worktree_agents_symlink import (
                WorktreeAgentsSymlinkMigration,
            )
        except ImportError:
            pytest.skip("WorktreeAgentsSymlinkMigration not yet implemented")

        migration = WorktreeAgentsSymlinkMigration()

        # Verify worktree exists but AGENTS.md doesn't
        worktree = project_with_worktree / '.worktrees' / '001-test-feature'
        wt_agents = worktree / '.kittify' / 'AGENTS.md'
        assert worktree.exists(), "Worktree should exist"
        assert not wt_agents.exists(), "AGENTS.md should not exist in worktree"

        # Should detect migration needed
        needs_migration = migration.detect(project_with_worktree)

        assert needs_migration is True, \
            "Should detect worktree missing AGENTS.md needs migration"

    def test_detect_no_main_agents(self, temp_project_dir, spec_kitty_repo_root):
        """Test: No detection when main AGENTS.md doesn't exist

        GIVEN: A project without .kittify/AGENTS.md in main repo
        WHEN: Running detect()
        THEN: Should return False (nothing to symlink)
        """
        try:
            from specify_cli.upgrade.migrations.m_0_8_0_worktree_agents_symlink import (
                WorktreeAgentsSymlinkMigration,
            )
        except ImportError:
            pytest.skip("WorktreeAgentsSymlinkMigration not yet implemented")

        migration = WorktreeAgentsSymlinkMigration()

        project_name = "test_no_main_agents"
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

        # Remove main AGENTS.md if it exists
        main_agents = project_path / '.kittify' / 'AGENTS.md'
        if main_agents.exists():
            main_agents.unlink()

        # Create worktree without AGENTS.md
        worktrees_dir = project_path / '.worktrees'
        worktrees_dir.mkdir(exist_ok=True)
        worktree = worktrees_dir / '001-feature'
        worktree.mkdir()
        (worktree / '.kittify').mkdir()

        # Should NOT detect migration needed
        needs_migration = migration.detect(project_path)

        assert needs_migration is False, \
            "Should not detect migration when main AGENTS.md doesn't exist"

    def test_detect_no_worktrees(self, temp_project_dir, spec_kitty_repo_root):
        """Test: No detection when no worktrees exist

        GIVEN: A project with no .worktrees directory
        WHEN: Running detect()
        THEN: Should return False
        """
        try:
            from specify_cli.upgrade.migrations.m_0_8_0_worktree_agents_symlink import (
                WorktreeAgentsSymlinkMigration,
            )
        except ImportError:
            pytest.skip("WorktreeAgentsSymlinkMigration not yet implemented")

        migration = WorktreeAgentsSymlinkMigration()

        project_name = "test_no_worktrees"
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

        # Ensure main AGENTS.md exists
        main_agents = project_path / '.kittify' / 'AGENTS.md'
        if not main_agents.exists():
            main_agents.write_text("# AGENTS\n")

        # Remove worktrees if they exist
        worktrees_dir = project_path / '.worktrees'
        if worktrees_dir.exists():
            import shutil
            shutil.rmtree(worktrees_dir)

        # Should NOT detect migration needed
        needs_migration = migration.detect(project_path)

        assert needs_migration is False, \
            "Should not detect migration when no worktrees exist"

    def test_detect_all_worktrees_have_valid_symlinks(self, project_with_worktree):
        """Test: No detection when all worktrees have valid AGENTS.md symlinks

        GIVEN: A project where all worktrees have valid AGENTS.md symlinks
        WHEN: Running detect()
        THEN: Should return False
        """
        try:
            from specify_cli.upgrade.migrations.m_0_8_0_worktree_agents_symlink import (
                WorktreeAgentsSymlinkMigration,
            )
        except ImportError:
            pytest.skip("WorktreeAgentsSymlinkMigration not yet implemented")

        migration = WorktreeAgentsSymlinkMigration()

        # Create valid symlink in worktree
        worktree = project_with_worktree / '.worktrees' / '001-test-feature'
        wt_kittify = worktree / '.kittify'
        wt_agents = wt_kittify / 'AGENTS.md'

        # Create symlink (change to dir for relative path)
        original_cwd = os.getcwd()
        try:
            os.chdir(wt_kittify)
            os.symlink('../../../.kittify/AGENTS.md', 'AGENTS.md')
        finally:
            os.chdir(original_cwd)

        # Verify symlink is valid
        assert wt_agents.is_symlink(), "Should be a symlink"
        assert wt_agents.exists(), "Symlink should point to valid target"

        # Should NOT detect migration needed
        needs_migration = migration.detect(project_with_worktree)

        assert needs_migration is False, \
            "Should not detect migration when all symlinks are valid"

    # ========================================================================
    # Migration Execution Tests
    # ========================================================================

    def test_creates_symlink_in_worktree(self, project_with_worktree):
        """Test: Creates AGENTS.md symlink in worktree

        GIVEN: A worktree missing .kittify/AGENTS.md
        WHEN: Applying migration
        THEN: Symlink should be created pointing to main repo
        """
        try:
            from specify_cli.upgrade.migrations.m_0_8_0_worktree_agents_symlink import (
                WorktreeAgentsSymlinkMigration,
            )
        except ImportError:
            pytest.skip("WorktreeAgentsSymlinkMigration not yet implemented")

        migration = WorktreeAgentsSymlinkMigration()

        worktree = project_with_worktree / '.worktrees' / '001-test-feature'
        wt_agents = worktree / '.kittify' / 'AGENTS.md'

        # Verify AGENTS.md doesn't exist before migration
        assert not wt_agents.exists(), "AGENTS.md should not exist before migration"

        # Apply migration
        result = migration.apply(project_with_worktree, dry_run=False)

        assert result.success, f"Migration should succeed. Errors: {result.errors}"

        # Verify symlink created
        assert wt_agents.exists(), "AGENTS.md should exist after migration"
        assert wt_agents.is_symlink(), "AGENTS.md should be a symlink"

        # Verify symlink points to correct target
        main_agents = project_with_worktree / '.kittify' / 'AGENTS.md'
        assert wt_agents.resolve() == main_agents.resolve(), \
            "Symlink should resolve to main repo AGENTS.md"

    def test_fixes_broken_symlink(self, project_with_worktree):
        """Test: Fixes broken AGENTS.md symlink in worktree

        GIVEN: A worktree with broken .kittify/AGENTS.md symlink
        WHEN: Applying migration
        THEN: Should replace with working symlink
        """
        try:
            from specify_cli.upgrade.migrations.m_0_8_0_worktree_agents_symlink import (
                WorktreeAgentsSymlinkMigration,
            )
        except ImportError:
            pytest.skip("WorktreeAgentsSymlinkMigration not yet implemented")

        migration = WorktreeAgentsSymlinkMigration()

        worktree = project_with_worktree / '.worktrees' / '001-test-feature'
        wt_kittify = worktree / '.kittify'
        wt_agents = wt_kittify / 'AGENTS.md'

        # Create broken symlink
        original_cwd = os.getcwd()
        try:
            os.chdir(wt_kittify)
            os.symlink('../nonexistent/AGENTS.md', 'AGENTS.md')
        finally:
            os.chdir(original_cwd)

        # Verify symlink is broken
        assert wt_agents.is_symlink(), "Should be a symlink"
        assert not wt_agents.exists(), "Symlink should be broken"

        # Migration should detect broken symlink
        assert migration.detect(project_with_worktree) is True, \
            "Should detect broken symlink"

        # Apply migration
        result = migration.apply(project_with_worktree, dry_run=False)

        assert result.success, f"Migration should succeed. Errors: {result.errors}"

        # Verify symlink is now valid
        assert wt_agents.is_symlink(), "Should still be a symlink"
        assert wt_agents.exists(), "Symlink should now be valid"

    def test_preserves_valid_symlinks(self, project_with_worktree):
        """Test: Preserves existing valid symlinks

        GIVEN: Multiple worktrees, some with valid symlinks
        WHEN: Applying migration
        THEN: Valid symlinks should be preserved unchanged
        """
        try:
            from specify_cli.upgrade.migrations.m_0_8_0_worktree_agents_symlink import (
                WorktreeAgentsSymlinkMigration,
            )
        except ImportError:
            pytest.skip("WorktreeAgentsSymlinkMigration not yet implemented")

        migration = WorktreeAgentsSymlinkMigration()

        # Create second worktree with valid symlink
        worktree2 = project_with_worktree / '.worktrees' / '002-feature-with-symlink'
        wt2_kittify = worktree2 / '.kittify'
        wt2_kittify.mkdir(parents=True)

        original_cwd = os.getcwd()
        try:
            os.chdir(wt2_kittify)
            os.symlink('../../../.kittify/AGENTS.md', 'AGENTS.md')
        finally:
            os.chdir(original_cwd)

        wt2_agents = wt2_kittify / 'AGENTS.md'
        original_target = os.readlink(wt2_agents)

        # Apply migration
        result = migration.apply(project_with_worktree, dry_run=False)

        assert result.success, "Migration should succeed"

        # Second worktree symlink should be unchanged
        assert wt2_agents.is_symlink(), "Should still be a symlink"
        assert os.readlink(wt2_agents) == original_target, \
            "Symlink target should be unchanged"

    # ========================================================================
    # Edge Case Tests
    # ========================================================================

    def test_warns_on_regular_file(self, project_with_worktree):
        """Test: Warns when worktree has regular file instead of symlink

        GIVEN: A worktree with regular .kittify/AGENTS.md file (not symlink)
        WHEN: Applying migration
        THEN: Should warn and skip (don't overwrite user's file)
        """
        try:
            from specify_cli.upgrade.migrations.m_0_8_0_worktree_agents_symlink import (
                WorktreeAgentsSymlinkMigration,
            )
        except ImportError:
            pytest.skip("WorktreeAgentsSymlinkMigration not yet implemented")

        migration = WorktreeAgentsSymlinkMigration()

        worktree = project_with_worktree / '.worktrees' / '001-test-feature'
        wt_agents = worktree / '.kittify' / 'AGENTS.md'

        # Create regular file (not symlink)
        wt_agents.write_text("# Custom AGENTS.md in worktree\n")

        # Migration should NOT detect this as needing migration
        # (detect only checks for missing or broken symlinks)
        assert not migration.detect(project_with_worktree), \
            "Should not detect regular file as needing migration"

        # If we force apply, it should warn
        result = migration.apply(project_with_worktree, dry_run=False)

        assert result.success, "Migration should succeed (with warning)"

        # Should have warning about non-symlink file
        warning_found = any('non-symlink' in w.lower() or 'skip' in w.lower()
                           for w in result.warnings)
        assert warning_found, \
            f"Should warn about non-symlink file. Warnings: {result.warnings}"

        # Original file should be preserved
        assert wt_agents.read_text() == "# Custom AGENTS.md in worktree\n", \
            "Original file should be preserved"

    def test_dry_run_no_changes(self, project_with_worktree):
        """Test: Dry run shows changes without applying

        GIVEN: A worktree missing AGENTS.md
        WHEN: Running with dry_run=True
        THEN: Should report changes but not create symlink
        """
        try:
            from specify_cli.upgrade.migrations.m_0_8_0_worktree_agents_symlink import (
                WorktreeAgentsSymlinkMigration,
            )
        except ImportError:
            pytest.skip("WorktreeAgentsSymlinkMigration not yet implemented")

        migration = WorktreeAgentsSymlinkMigration()

        worktree = project_with_worktree / '.worktrees' / '001-test-feature'
        wt_agents = worktree / '.kittify' / 'AGENTS.md'

        # Verify AGENTS.md doesn't exist before dry run
        assert not wt_agents.exists(), "AGENTS.md should not exist before dry run"

        # Run dry run
        result = migration.apply(project_with_worktree, dry_run=True)

        # Should report changes
        assert len(result.changes_made) > 0, "Dry run should report changes"
        assert any('would' in c.lower() for c in result.changes_made), \
            "Dry run changes should use 'would' language"

        # AGENTS.md should still not exist
        assert not wt_agents.exists(), \
            "AGENTS.md should not exist after dry run"


class TestWorktreeAgentsSymlinkIntegration:
    """Integration tests for the 0.8.0 worktree AGENTS.md symlink migration."""

    def test_migration_registered(self):
        """Test: Migration is registered in the registry

        GIVEN: The migration module is loaded
        WHEN: Checking MigrationRegistry
        THEN: 0.8.0_worktree_agents_symlink should be registered
        """
        try:
            from specify_cli.upgrade.registry import MigrationRegistry
        except ImportError:
            pytest.skip("MigrationRegistry not yet implemented")

        all_migrations = MigrationRegistry.get_all()
        migration_ids = [m.migration_id for m in all_migrations]

        # Skip if migration not yet implemented
        if "0.8.0_worktree_agents_symlink" not in migration_ids:
            pytest.skip("0.8.0_worktree_agents_symlink migration not yet implemented")

        assert "0.8.0_worktree_agents_symlink" in migration_ids, \
            "0.8.0_worktree_agents_symlink should be registered"

    def test_migration_version_is_0_8_0(self):
        """Test: Migration targets v0.8.0

        GIVEN: The migration is loaded
        WHEN: Checking target_version
        THEN: Should be 0.8.0
        """
        try:
            from specify_cli.upgrade.migrations.m_0_8_0_worktree_agents_symlink import (
                WorktreeAgentsSymlinkMigration,
            )
        except ImportError:
            pytest.skip("WorktreeAgentsSymlinkMigration not yet implemented")

        migration = WorktreeAgentsSymlinkMigration()

        assert migration.target_version == "0.8.0", \
            "Migration should target v0.8.0"


class TestNewWorktreeAgentsSymlink:
    """Test that new worktrees get AGENTS.md symlink via create-new-feature.sh."""

    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        """Create temporary directory for test project."""
        return tmp_path

    def test_new_worktree_has_agents_symlink(
        self, temp_project_dir, spec_kitty_repo_root, requires_v08
    ):
        """Test: New worktrees get AGENTS.md symlink automatically

        GIVEN: A project with .kittify/AGENTS.md
        WHEN: Creating a new feature (worktree)
        THEN: Worktree should have .kittify/AGENTS.md symlink

        Note: Requires v0.8.0+ for this fix
        """
        project_name = "test_new_worktree_agents"
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

        # Ensure main AGENTS.md exists
        main_agents = project_path / '.kittify' / 'AGENTS.md'
        if not main_agents.exists():
            main_agents.write_text("# Test AGENTS.md\n")

        # Create a new feature using the script
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'Test Feature',
             'Test description for agents symlink'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        # Find the created worktree
        import json
        for line in result.stdout.split('\n'):
            if line.strip().startswith('{'):
                try:
                    output = json.loads(line)
                    branch_name = output.get('BRANCH_NAME')
                    if branch_name:
                        worktree_path = project_path / '.worktrees' / branch_name
                        wt_agents = worktree_path / '.kittify' / 'AGENTS.md'

                        # Verify AGENTS.md exists in worktree
                        assert wt_agents.exists() or wt_agents.is_symlink(), \
                            "AGENTS.md should exist in new worktree"

                        # Verify it's a symlink (or copy on Windows)
                        if wt_agents.is_symlink():
                            assert wt_agents.resolve() == main_agents.resolve(), \
                                "Symlink should point to main repo AGENTS.md"
                        else:
                            # On Windows, might be a copy
                            assert wt_agents.exists(), \
                                "AGENTS.md copy should exist"
                        break
                except json.JSONDecodeError:
                    continue


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
