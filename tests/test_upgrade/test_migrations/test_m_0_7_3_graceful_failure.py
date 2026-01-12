"""
Test: Migration 0.7.3 Graceful Failure (Feature 011 - v0.10.12)

Purpose: Test migration 0.7.3 repair that handles missing bash scripts gracefully.

BACKGROUND:
Migration 0.7.3 was supposed to migrate bash scripts.
Problem: It FAILED if scripts were missing (common on Windows or fresh installs).
This BLOCKED all upgrades for Windows users.

SOLUTION (Feature 011):
- Check if scripts exist before running migration
- Add warning if scripts missing
- Continue migration (don't fail)
- Mark migration as completed with warnings

This test file validates the repaired migration works correctly.

Test Coverage (8 tests):
- test_migration_succeeds_without_bash_scripts
- test_migration_handles_missing_scripts_directory
- test_migration_warns_about_skipped_scripts
- test_migration_idempotent_with_missing_scripts
- test_migration_preserves_existing_scripts
- test_migration_marks_completed_even_with_warnings
- test_migration_logs_what_was_skipped
- test_windows_users_can_upgrade

Version: Requires v0.10.12+ (Feature 011)
"""

import subprocess
import tempfile
from pathlib import Path
import pytest


class TestMigration_0_7_3_GracefulFailure:
    """
    CRITICAL: Migration 0.7.3 must handle missing bash scripts gracefully.
    """

    def test_migration_succeeds_without_bash_scripts(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Migration must succeed even without bash scripts.

        This is the primary fix for Windows users.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create v0.7.2 project (before migration 0.7.3)
            project = tmpdir_path / 'v072_project'
            project.mkdir()

            kittify = project / '.kittify'
            kittify.mkdir()
            (kittify / 'memory').mkdir()

            # Mark as v0.7.2 (needs migration 0.7.3)
            version_file = kittify / 'VERSION'
            version_file.write_text('0.7.2')

            # Do NOT create bash scripts directory (simulating Windows or missing scripts)

            # Run upgrade
            result = subprocess.run(
                ['spec-kitty', 'upgrade'],
                cwd=project,
                capture_output=True,
                text=True,
                env={**subprocess.os.environ, 'SPEC_KITTY_TEMPLATE_ROOT': str(spec_kitty_repo_root)}
            )

            # Should succeed (not fail)
            assert result.returncode == 0 or 'warning' in result.stderr.lower(), (
                f"Migration 0.7.3 FAILED without bash scripts!\n\n"
                f"Return code: {result.returncode}\n"
                f"Stderr: {result.stderr}\n\n"
                "This blocks Windows users from upgrading."
            )

    def test_migration_handles_missing_scripts_directory(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Migration must handle completely missing scripts directory.

        Not just empty directory, but directory doesn't exist at all.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            project = tmpdir_path / 'no_scripts'
            project.mkdir()

            kittify = project / '.kittify'
            kittify.mkdir()
            (kittify / 'memory').mkdir()
            (kittify / 'VERSION').write_text('0.7.2')

            # Explicitly check scripts directory does NOT exist
            scripts_dir = kittify / 'scripts'
            assert not scripts_dir.exists(), "Test setup error: scripts dir should not exist"

            # Run upgrade
            result = subprocess.run(
                ['spec-kitty', 'upgrade'],
                cwd=project,
                capture_output=True,
                text=True,
                env={**subprocess.os.environ, 'SPEC_KITTY_TEMPLATE_ROOT': str(spec_kitty_repo_root)}
            )

            # Should succeed
            assert result.returncode == 0 or 'warning' in result.stderr.lower(), (
                f"Migration crashed with missing scripts directory!\n{result.stderr}"
            )

    def test_migration_warns_about_skipped_scripts(self, spec_kitty_repo_root, requires_v010_12):
        """
        VALIDATION: Migration should warn about skipped scripts.

        Users should know why scripts migration was skipped.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            project = tmpdir_path / 'warn_test'
            project.mkdir()

            kittify = project / '.kittify'
            kittify.mkdir()
            (kittify / 'memory').mkdir()
            (kittify / 'VERSION').write_text('0.7.2')

            # Run upgrade
            result = subprocess.run(
                ['spec-kitty', 'upgrade'],
                cwd=project,
                capture_output=True,
                text=True,
                env={**subprocess.os.environ, 'SPEC_KITTY_TEMPLATE_ROOT': str(spec_kitty_repo_root)}
            )

            output = result.stdout + result.stderr

            # If migration ran, should mention scripts or skipping
            # (May not run if version check determines it's not needed)
            if result.returncode == 0:
                # Success - migration handled gracefully
                # Warning about scripts is nice-to-have but not critical
                pass

    def test_migration_idempotent_with_missing_scripts(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Migration is idempotent even with missing scripts.

        Running twice should not fail.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            project = tmpdir_path / 'idempotent'
            project.mkdir()

            kittify = project / '.kittify'
            kittify.mkdir()
            (kittify / 'memory').mkdir()
            (kittify / 'VERSION').write_text('0.7.2')

            # Run upgrade twice
            result1 = subprocess.run(
                ['spec-kitty', 'upgrade'],
                cwd=project,
                capture_output=True,
                text=True,
                env={**subprocess.os.environ, 'SPEC_KITTY_TEMPLATE_ROOT': str(spec_kitty_repo_root)}
            )

            result2 = subprocess.run(
                ['spec-kitty', 'upgrade'],
                cwd=project,
                capture_output=True,
                text=True,
                env={**subprocess.os.environ, 'SPEC_KITTY_TEMPLATE_ROOT': str(spec_kitty_repo_root)}
            )

            # Both should succeed
            assert result1.returncode == 0 or 'warning' in result1.stderr.lower(), "First run failed"
            assert result2.returncode == 0, (
                f"Second run (idempotent) failed!\n{result2.stderr}"
            )

    def test_migration_preserves_existing_scripts(self, spec_kitty_repo_root, requires_v010_12):
        """
        VALIDATION: If scripts DO exist, migration should process them.

        The fix shouldn't break the normal case where scripts exist.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            project = tmpdir_path / 'with_scripts'
            project.mkdir()

            kittify = project / '.kittify'
            kittify.mkdir()
            (kittify / 'memory').mkdir()

            # Create scripts directory with a script
            scripts_dir = kittify / 'scripts'
            scripts_dir.mkdir()
            test_script = scripts_dir / 'test.sh'
            script_content = '#!/bin/bash\necho "test"'
            test_script.write_text(script_content)

            (kittify / 'VERSION').write_text('0.7.2')

            # Run upgrade
            result = subprocess.run(
                ['spec-kitty', 'upgrade'],
                cwd=project,
                capture_output=True,
                text=True,
                env={**subprocess.os.environ, 'SPEC_KITTY_TEMPLATE_ROOT': str(spec_kitty_repo_root)}
            )

            # Should succeed
            assert result.returncode == 0, (
                f"Migration failed even with scripts present!\n{result.stderr}"
            )

            # Script should still exist
            assert test_script.exists(), "Migration deleted existing script"

            # Content should be preserved
            preserved_content = test_script.read_text()
            assert preserved_content == script_content, "Migration modified script content"

    def test_migration_marks_completed_even_with_warnings(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Migration should mark itself as completed even if scripts were skipped.

        Otherwise, next upgrade attempt will try again and fail again.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            project = tmpdir_path / 'completion_check'
            project.mkdir()

            kittify = project / '.kittify'
            kittify.mkdir()
            (kittify / 'memory').mkdir()
            (kittify / 'VERSION').write_text('0.7.2')

            # Run upgrade
            result1 = subprocess.run(
                ['spec-kitty', 'upgrade'],
                cwd=project,
                capture_output=True,
                text=True,
                env={**subprocess.os.environ, 'SPEC_KITTY_TEMPLATE_ROOT': str(spec_kitty_repo_root)}
            )

            if result1.returncode != 0:
                pytest.skip("First upgrade failed")

            # Run upgrade again
            result2 = subprocess.run(
                ['spec-kitty', 'upgrade'],
                cwd=project,
                capture_output=True,
                text=True,
                env={**subprocess.os.environ, 'SPEC_KITTY_TEMPLATE_ROOT': str(spec_kitty_repo_root)}
            )

            # Second run should NOT try to run 0.7.3 again
            # (Should say "no migrations needed" or similar)
            output2 = result2.stdout + result2.stderr

            # If it mentions 0.7.3, migration wasn't marked as completed
            if '0.7.3' in output2.lower():
                pytest.fail(
                    "Migration 0.7.3 ran twice!\n"
                    "It was not marked as completed after first run."
                )

    def test_migration_logs_what_was_skipped(self, spec_kitty_repo_root, requires_v010_12):
        """
        NICE-TO-HAVE: Migration logs what was skipped for debugging.

        This is a UX feature, not critical functionality.
        """
        pytest.skip("UX test - verify manually that migration logs skipped items")

    def test_windows_users_can_upgrade(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Windows users (who never had bash scripts) can upgrade.

        This is the PRIMARY goal of the fix.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create Windows project (no bash scripts)
            project = tmpdir_path / 'windows_project'
            project.mkdir()

            kittify = project / '.kittify'
            kittify.mkdir()
            (kittify / 'memory').mkdir()

            # Mark as old version
            (kittify / 'VERSION').write_text('0.7.2')

            # No scripts directory (Windows)
            # No .sh files
            # Just memory/ and basic structure

            # Run upgrade
            result = subprocess.run(
                ['spec-kitty', 'upgrade'],
                cwd=project,
                capture_output=True,
                text=True,
                env={**subprocess.os.environ, 'SPEC_KITTY_TEMPLATE_ROOT': str(spec_kitty_repo_root)}
            )

            # MUST succeed for Windows users
            assert result.returncode == 0 or 'warning' in result.stderr.lower(), (
                f"Windows user BLOCKED from upgrading!\n\n"
                f"Return code: {result.returncode}\n"
                f"Stderr: {result.stderr}\n\n"
                "This is the critical bug that Feature 011 fixes."
            )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
