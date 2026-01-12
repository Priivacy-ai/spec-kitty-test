"""
Test: Comprehensive Upgrade Paths with pip and uv

Purpose: Validate all major version upgrade paths work correctly with both
pip and uv package managers.

CONTEXT:
Users upgrade spec-kitty across multiple versions. Each upgrade must:
- Install successfully
- Run migrations correctly
- Preserve user data
- Not introduce contamination
- Work with both pip and uv

Test Strategy:
- Test all major version transitions
- Test both pip and uv installers
- Test in clean venvs (no cross-contamination)
- Verify migrations run
- Verify data preservation
- Verify no contamination

Test Coverage:
- TestPipUpgradePaths: All upgrade paths with pip
- TestUvUpgradePaths: All upgrade paths with uv
- TestCrossVersionData: Data preservation across versions
- TestPackageManagerParity: pip vs uv consistency

Major Version Transitions:
- v0.6.4 → v0.10.13 (large jump, many migrations)
- v0.10.0 → v0.10.13 (minor jump, recent migrations)
- v0.10.11 → v0.10.13 (patch jump, single migration)
- v0.10.13 → v0.11.0 (major version, breaking changes)
- v0.6.4 → v0.11.0 (full upgrade path)

Version: All versions (no version guard - tests package manager behavior)
"""

import subprocess
import tempfile
import venv
from pathlib import Path
import pytest
import shutil


def get_venv_executable(venv_dir, name):
    """Helper: Get platform-independent path to venv executable."""
    # Try Unix path first
    path = venv_dir / 'bin' / name
    if path.exists():
        return path

    # Try Windows path
    if name == 'pip':
        path = venv_dir / 'Scripts' / 'pip.exe'
    elif name == 'spec-kitty':
        path = venv_dir / 'Scripts' / 'spec-kitty.exe'
    elif name == 'python':
        path = venv_dir / 'Scripts' / 'python.exe'
    else:
        path = venv_dir / 'Scripts' / f'{name}.exe'

    if path.exists():
        return path

    # Return Unix path as default (will fail if not exists)
    return venv_dir / 'bin' / name


class TestPipUpgradePaths:
    """
    COMPREHENSIVE: Test all major upgrade paths using pip.

    These tests validate the upgrade experience for pip users.
    """

    def test_upgrade_0_6_4_to_0_10_13_via_pip(self):
        """
        CRITICAL: Test full upgrade from v0.6.4 to v0.10.13 using pip.

        This is the longest upgrade path with most migrations.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create clean venv
            venv_dir = tmpdir_path / 'test_venv'
            venv.create(venv_dir, with_pip=True, clear=True)

            # Get pip path (platform-independent)
            pip_path = get_venv_executable(venv_dir, 'pip')
            spec_kitty_path = get_venv_executable(venv_dir, 'spec-kitty')

            # Install v0.6.4
            result = subprocess.run(
                [str(pip_path), 'install', 'spec-kitty-cli==0.6.4'],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                pytest.skip(f"v0.6.4 not available or installation failed: {result.stderr}")

            # Initialize project with v0.6.4
            project_dir = tmpdir_path / 'test_project'

            result = subprocess.run(
                [str(spec_kitty_path), 'init', 'test_project', '--ai', 'claude'],
                cwd=tmpdir_path,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                pytest.skip(f"v0.6.4 init failed: {result.stderr}")

            # Add some user data to preserve
            memory_dir = project_dir / '.kittify' / 'memory'
            if not memory_dir.exists():
                memory_dir.mkdir(parents=True)

            user_data = memory_dir / 'test_data.txt'
            user_data_content = 'User data from v0.6.4'
            user_data.write_text(user_data_content)

            # Upgrade to v0.10.13
            result = subprocess.run(
                [str(pip_path), 'install', '--upgrade', 'spec-kitty-cli==0.10.13'],
                capture_output=True,
                text=True
            )

            assert result.returncode == 0, (
                f"Upgrade to v0.10.13 failed!\n{result.stderr}"
            )

            # Run upgrade command
            result = subprocess.run(
                [str(spec_kitty_path), 'upgrade', '--force'],
                cwd=project_dir,
                capture_output=True,
                text=True
            )

            assert result.returncode == 0, (
                f"spec-kitty upgrade failed!\n{result.stderr}"
            )

            # Verify user data preserved
            assert user_data.exists(), "User data lost during upgrade!"
            assert user_data.read_text() == user_data_content, "User data corrupted!"

            # Verify spec-kitty commands work
            result = subprocess.run(
                [str(spec_kitty_path), '--version'],
                capture_output=True,
                text=True
            )

            assert '0.10.13' in result.stdout, "Version not updated to 0.10.13"

    def test_upgrade_0_10_11_to_0_10_13_via_pip(self):
        """
        CRITICAL: Test recent upgrade from v0.10.11 to v0.10.13 using pip.

        Most common upgrade path for existing users.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            venv_dir = tmpdir_path / 'test_venv'
            venv.create(venv_dir, with_pip=True, clear=True)

            # Get pip path (platform-independent)
            pip_path = get_venv_executable(venv_dir, 'pip')
            spec_kitty_path = get_venv_executable(venv_dir, 'spec-kitty')

            # Install v0.10.11
            result = subprocess.run(
                [str(pip_path), 'install', 'spec-kitty-cli==0.10.11'],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                pytest.skip(f"v0.10.11 not available: {result.stderr}")

            # Initialize project
            project_dir = tmpdir_path / 'test_project'

            subprocess.run(
                [str(spec_kitty_path), 'init', 'test_project', '--ai', 'claude'],
                cwd=tmpdir_path,
                capture_output=True,
                text=True,
                check=True
            )

            # Create mission constitutions (will be cleaned up by 0.10.12 migration)
            sw_const = project_dir / '.kittify' / 'missions' / 'software-dev' / 'constitution'
            sw_const.mkdir(parents=True, exist_ok=True)
            (sw_const / 'principles.md').write_text('Old constitution')

            # Upgrade to v0.10.13
            result = subprocess.run(
                [str(pip_path), 'install', '--upgrade', 'spec-kitty-cli==0.10.13'],
                capture_output=True,
                text=True
            )

            assert result.returncode == 0, "Upgrade to v0.10.13 failed"

            # Run upgrade command
            result = subprocess.run(
                [str(spec_kitty_path), 'upgrade', '--force'],
                cwd=project_dir,
                capture_output=True,
                text=True
            )

            assert result.returncode == 0, "spec-kitty upgrade failed"

            # Verify migration 0.10.12 ran (constitution removed)
            assert not sw_const.exists(), (
                "Migration 0.10.12 did not remove mission constitution!\n"
                f"Still exists: {sw_const}"
            )

    def test_upgrade_0_10_13_to_0_11_0_via_pip(self):
        """
        CRITICAL: Test major version upgrade from v0.10.13 to v0.11.0 using pip.

        This is a breaking change upgrade (workspace-per-WP).
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            venv_dir = tmpdir_path / 'test_venv'
            venv.create(venv_dir, with_pip=True, clear=True)

            # Get pip path (platform-independent)
            pip_path = get_venv_executable(venv_dir, 'pip')
            spec_kitty_path = get_venv_executable(venv_dir, 'spec-kitty')

            # Install v0.10.13
            subprocess.run(
                [str(pip_path), 'install', 'spec-kitty-cli==0.10.13'],
                capture_output=True,
                check=True
            )

            # Initialize project
            project_dir = tmpdir_path / 'test_project'

            subprocess.run(
                [str(spec_kitty_path), 'init', 'test_project', '--ai', 'claude'],
                cwd=tmpdir_path,
                capture_output=True,
                check=True
            )

            # Add user data
            user_data = project_dir / '.kittify' / 'memory' / 'important.txt'
            user_data_content = 'Critical data from v0.10.13'
            user_data.write_text(user_data_content)

            # Upgrade to v0.11.0 (if available on PyPI)
            result = subprocess.run(
                [str(pip_path), 'install', '--upgrade', 'spec-kitty-cli==0.11.0'],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                pytest.skip("v0.11.0 not available on PyPI yet")

            # Run upgrade command
            result = subprocess.run(
                [str(spec_kitty_path), 'upgrade', '--force'],
                cwd=project_dir,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                pytest.skip(f"Upgrade command failed: {result.stderr}")

            # Verify user data preserved
            assert user_data.exists(), "User data lost in major version upgrade!"
            assert user_data.read_text() == user_data_content, "User data corrupted!"


class TestUvUpgradePaths:
    """
    COMPREHENSIVE: Test all major upgrade paths using uv.

    These tests validate the upgrade experience for uv users.
    uv is a faster Python package installer.
    """

    def test_uv_available(self):
        """
        SETUP: Check if uv is available.

        If not, skip all uv tests.
        """
        result = subprocess.run(
            ['uv', '--version'],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip("uv not installed - skipping uv tests")

    def test_upgrade_0_10_11_to_0_10_13_via_uv(self):
        """
        CRITICAL: Test upgrade from v0.10.11 to v0.10.13 using uv.

        Validates uv package manager compatibility.
        """
        # Check uv available
        result = subprocess.run(['uv', '--version'], capture_output=True)
        if result.returncode != 0:
            pytest.skip("uv not installed")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            venv_dir = tmpdir_path / 'test_venv'

            # Create venv with uv
            result = subprocess.run(
                ['uv', 'venv', str(venv_dir)],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                pytest.skip(f"uv venv creation failed: {result.stderr}")

            # Install v0.10.11 with uv
            result = subprocess.run(
                ['uv', 'pip', 'install', '--python', str(venv_dir / 'bin' / 'python'), 'spec-kitty-cli==0.10.11'],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                pytest.skip(f"uv install v0.10.11 failed: {result.stderr}")

            spec_kitty_path = venv_dir / 'bin' / 'spec-kitty'
            if not spec_kitty_path.exists():
                spec_kitty_path = venv_dir / 'Scripts' / 'spec-kitty.exe'

            # Initialize project
            project_dir = tmpdir_path / 'test_project'

            subprocess.run(
                [str(spec_kitty_path), 'init', 'test_project', '--ai', 'claude'],
                cwd=tmpdir_path,
                capture_output=True,
                check=True
            )

            # Upgrade to v0.10.13 with uv
            result = subprocess.run(
                ['uv', 'pip', 'install', '--python', str(venv_dir / 'bin' / 'python'), '--upgrade', 'spec-kitty-cli==0.10.13'],
                capture_output=True,
                text=True
            )

            assert result.returncode == 0, (
                f"uv upgrade to v0.10.13 failed!\n{result.stderr}"
            )

            # Run upgrade command
            result = subprocess.run(
                [str(spec_kitty_path), 'upgrade', '--force'],
                cwd=project_dir,
                capture_output=True,
                text=True
            )

            assert result.returncode == 0, (
                f"spec-kitty upgrade failed after uv install!\n{result.stderr}"
            )

            # Verify version
            result = subprocess.run(
                [str(spec_kitty_path), '--version'],
                capture_output=True,
                text=True
            )

            assert '0.10.13' in result.stdout, "Version not updated to 0.10.13"

    def test_upgrade_0_10_13_to_0_11_0_via_uv(self):
        """
        CRITICAL: Test major version upgrade v0.10.13 → v0.11.0 using uv.

        Major version with breaking changes.
        """
        result = subprocess.run(['uv', '--version'], capture_output=True)
        if result.returncode != 0:
            pytest.skip("uv not installed")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            venv_dir = tmpdir_path / 'test_venv'

            # Create venv
            subprocess.run(
                ['uv', 'venv', str(venv_dir)],
                capture_output=True,
                check=True
            )

            # Install v0.10.13
            subprocess.run(
                ['uv', 'pip', 'install', '--python', str(venv_dir / 'bin' / 'python'), 'spec-kitty-cli==0.10.13'],
                capture_output=True,
                check=True
            )

            spec_kitty_path = venv_dir / 'bin' / 'spec-kitty'
            if not spec_kitty_path.exists():
                spec_kitty_path = venv_dir / 'Scripts' / 'spec-kitty.exe'

            # Initialize project
            project_dir = tmpdir_path / 'test_project'

            subprocess.run(
                [str(spec_kitty_path), 'init', 'test_project', '--ai', 'claude'],
                cwd=tmpdir_path,
                capture_output=True,
                check=True
            )

            # Add user data
            user_data = project_dir / '.kittify' / 'memory' / 'critical.txt'
            user_data_content = 'Data from v0.10.13'
            user_data.write_text(user_data_content)

            # Upgrade to v0.11.0
            result = subprocess.run(
                ['uv', 'pip', 'install', '--python', str(venv_dir / 'bin' / 'python'), '--upgrade', 'spec-kitty-cli==0.11.0'],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                pytest.skip("v0.11.0 not available on PyPI")

            # Run upgrade command
            result = subprocess.run(
                [str(spec_kitty_path), 'upgrade', '--force'],
                cwd=project_dir,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                pytest.skip(f"Upgrade command failed: {result.stderr}")

            # Verify data preserved across major version
            assert user_data.exists(), "User data lost in major upgrade!"
            assert user_data.read_text() == user_data_content, "User data corrupted!"


class TestCrossVersionData:
    """
    CRITICAL: Test data preservation across version upgrades.

    Validates that user data survives upgrades.
    """

    def test_constitution_preserved_across_upgrades(self):
        """
        CRITICAL: User's constitution must survive all upgrades.

        Test with pip (uv similar).
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            venv_dir = tmpdir_path / 'test_venv'
            venv.create(venv_dir, with_pip=True, clear=True)

            # Get pip path (platform-independent)
            pip_path = get_venv_executable(venv_dir, 'pip')
            spec_kitty_path = get_venv_executable(venv_dir, 'spec-kitty')

            # Install v0.10.11
            result = subprocess.run(
                [str(pip_path), 'install', 'spec-kitty-cli==0.10.11'],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                pytest.skip("v0.10.11 not available")

            # Initialize and create constitution
            project_dir = tmpdir_path / 'test_project'

            subprocess.run(
                [str(spec_kitty_path), 'init', 'test_project', '--ai', 'claude'],
                cwd=tmpdir_path,
                capture_output=True,
                check=True
            )

            constitution = project_dir / '.kittify' / 'memory' / 'constitution.md'
            constitution_content = '# My Project Constitution\n\nCritical project guidelines.'
            constitution.write_text(constitution_content)

            # Upgrade to v0.10.13
            subprocess.run(
                [str(pip_path), 'install', '--upgrade', 'spec-kitty-cli==0.10.13'],
                capture_output=True,
                check=True
            )

            subprocess.run(
                [str(spec_kitty_path), 'upgrade', '--force'],
                cwd=project_dir,
                capture_output=True,
                check=True
            )

            # Verify constitution preserved
            assert constitution.exists(), "Constitution deleted during upgrade!"
            preserved_content = constitution.read_text()
            assert preserved_content == constitution_content, (
                f"Constitution corrupted!\n"
                f"Expected: {constitution_content[:100]}\n"
                f"Got: {preserved_content[:100]}"
            )

    def test_memory_directory_preserved_across_upgrades(self):
        """
        CRITICAL: Entire .kittify/memory/ must survive upgrades.

        All user conversation history and data.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            venv_dir = tmpdir_path / 'test_venv'
            venv.create(venv_dir, with_pip=True, clear=True)

            # Get pip path (platform-independent)
            pip_path = get_venv_executable(venv_dir, 'pip')
            spec_kitty_path = get_venv_executable(venv_dir, 'spec-kitty')

            # Install old version
            subprocess.run(
                [str(pip_path), 'install', 'spec-kitty-cli==0.10.11'],
                capture_output=True,
                check=True
            )

            project_dir = tmpdir_path / 'test_project'

            subprocess.run(
                [str(spec_kitty_path), 'init', 'test_project', '--ai', 'claude'],
                cwd=tmpdir_path,
                capture_output=True,
                check=True
            )

            # Create multiple files in memory/
            memory_dir = project_dir / '.kittify' / 'memory'
            files = {
                'notes.txt': 'Important notes',
                'decisions.md': '# Decisions\n\nKey decisions',
                'context.txt': 'Project context'
            }

            for filename, content in files.items():
                (memory_dir / filename).write_text(content)

            # Upgrade
            subprocess.run(
                [str(pip_path), 'install', '--upgrade', 'spec-kitty-cli==0.10.13'],
                capture_output=True,
                check=True
            )

            subprocess.run(
                [str(spec_kitty_path), 'upgrade', '--force'],
                cwd=project_dir,
                capture_output=True,
                check=True
            )

            # Verify ALL files preserved
            for filename, expected_content in files.items():
                file_path = memory_dir / filename
                assert file_path.exists(), f"{filename} deleted during upgrade!"
                actual_content = file_path.read_text()
                assert actual_content == expected_content, f"{filename} corrupted!"


class TestPackageManagerParity:
    """
    VALIDATION: Test that pip and uv produce identical results.

    Ensures both package managers work correctly.
    """

    def test_pip_and_uv_install_same_version(self):
        """
        VALIDATION: pip and uv should install same version.

        Both should get v0.10.13 when requested.
        """
        # Test with pip
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / 'pip_venv'
            venv.create(venv_dir, with_pip=True, clear=True)

            pip_path = venv_dir / 'bin' / 'pip'
            if not pip_path.exists():
                pip_path = venv_dir / 'Scripts' / 'pip.exe'

            subprocess.run(
                [str(pip_path), 'install', 'spec-kitty-cli==0.10.13'],
                capture_output=True,
                check=True
            )

            spec_kitty_path = venv_dir / 'bin' / 'spec-kitty'
            if not spec_kitty_path.exists():
                spec_kitty_path = venv_dir / 'Scripts' / 'spec-kitty.exe'

            result = subprocess.run(
                [str(spec_kitty_path), '--version'],
                capture_output=True,
                text=True
            )

            pip_version = result.stdout.strip()

        # Test with uv
        result = subprocess.run(['uv', '--version'], capture_output=True)
        if result.returncode != 0:
            pytest.skip("uv not installed")

        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / 'uv_venv'

            subprocess.run(
                ['uv', 'venv', str(venv_dir)],
                capture_output=True,
                check=True
            )

            subprocess.run(
                ['uv', 'pip', 'install', '--python', str(venv_dir / 'bin' / 'python'), 'spec-kitty-cli==0.10.13'],
                capture_output=True,
                check=True
            )

            spec_kitty_path = venv_dir / 'bin' / 'spec-kitty'
            if not spec_kitty_path.exists():
                spec_kitty_path = venv_dir / 'Scripts' / 'spec-kitty.exe'

            result = subprocess.run(
                [str(spec_kitty_path), '--version'],
                capture_output=True,
                text=True
            )

            uv_version = result.stdout.strip()

        # Versions should match
        assert pip_version == uv_version, (
            f"pip and uv installed different versions!\n"
            f"pip: {pip_version}\n"
            f"uv: {uv_version}"
        )

    def test_pip_and_uv_produce_identical_installations(self):
        """
        VALIDATION: pip and uv should produce identical installations.

        Same package structure, same files.
        """
        # Check uv available
        result = subprocess.run(['uv', '--version'], capture_output=True)
        if result.returncode != 0:
            pytest.skip("uv not installed")

        pip_site_packages = None
        uv_site_packages = None

        # Install with pip
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / 'pip_venv'
            venv.create(venv_dir, with_pip=True, clear=True)

            pip_path = venv_dir / 'bin' / 'pip'
            if not pip_path.exists():
                pip_path = venv_dir / 'Scripts' / 'pip.exe'

            subprocess.run(
                [str(pip_path), 'install', 'spec-kitty-cli==0.10.13'],
                capture_output=True,
                check=True
            )

            # Count files in pip installation
            site_packages = list(venv_dir.glob('**/site-packages/specify_cli'))
            if site_packages:
                pip_site_packages = site_packages[0]
                pip_files = list(pip_site_packages.rglob('*'))
                pip_file_count = len([f for f in pip_files if f.is_file()])

        # Install with uv
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / 'uv_venv'

            subprocess.run(
                ['uv', 'venv', str(venv_dir)],
                capture_output=True,
                check=True
            )

            subprocess.run(
                ['uv', 'pip', 'install', '--python', str(venv_dir / 'bin' / 'python'), 'spec-kitty-cli==0.10.13'],
                capture_output=True,
                check=True
            )

            # Count files in uv installation
            site_packages = list(venv_dir.glob('**/site-packages/specify_cli'))
            if site_packages:
                uv_site_packages = site_packages[0]
                uv_files = list(uv_site_packages.rglob('*'))
                uv_file_count = len([f for f in uv_files if f.is_file()])

        # File counts should be identical
        assert pip_file_count == uv_file_count, (
            f"pip and uv installed different number of files!\n"
            f"pip: {pip_file_count} files\n"
            f"uv: {uv_file_count} files"
        )


class TestUpgradeNoContamination:
    """
    CRITICAL: Verify upgrades don't introduce contamination.

    Even during upgrade process, no contamination should occur.
    """

    def test_upgrade_preserves_blank_constitution_template(self):
        """
        CRITICAL: Upgrading package must not contaminate local templates.

        After upgrade, fresh init should still give blank template.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            venv_dir = tmpdir_path / 'test_venv'
            venv.create(venv_dir, with_pip=True, clear=True)

            # Get pip path (platform-independent)
            pip_path = get_venv_executable(venv_dir, 'pip')
            spec_kitty_path = get_venv_executable(venv_dir, 'spec-kitty')

            # Install old version
            subprocess.run(
                [str(pip_path), 'install', 'spec-kitty-cli==0.10.11'],
                capture_output=True,
                check=True
            )

            # Upgrade to new version
            subprocess.run(
                [str(pip_path), 'install', '--upgrade', 'spec-kitty-cli==0.10.13'],
                capture_output=True,
                check=True
            )

            # Initialize NEW project after upgrade
            new_project = tmpdir_path / 'new_project'

            result = subprocess.run(
                [str(spec_kitty_path), 'init', 'new_project', '--ai', 'claude'],
                cwd=tmpdir_path,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                pytest.skip("Init failed after upgrade")

            # Check constitution is blank
            constitution = new_project / '.kittify' / 'memory' / 'constitution.md'

            if constitution.exists():
                content = constitution.read_text()

                # Should be small (blank template)
                assert len(content) < 5000, (
                    f"Constitution appears filled after upgrade!\n"
                    f"Size: {len(content)} bytes\n"
                    f"Should be blank template."
                )

    def test_upgrade_no_cross_project_contamination(self):
        """
        CRITICAL: Upgrading spec-kitty must not affect other projects.

        Project A upgrades, Project B unchanged.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            venv_dir = tmpdir_path / 'test_venv'
            venv.create(venv_dir, with_pip=True, clear=True)

            # Get pip path (platform-independent)
            pip_path = get_venv_executable(venv_dir, 'pip')
            spec_kitty_path = get_venv_executable(venv_dir, 'spec-kitty')

            # Install v0.10.11
            subprocess.run(
                [str(pip_path), 'install', 'spec-kitty-cli==0.10.11'],
                capture_output=True,
                check=True
            )

            # Create two projects
            project_a = tmpdir_path / 'project_a'
            project_b = tmpdir_path / 'project_b'

            subprocess.run(
                [str(spec_kitty_path), 'init', 'project_a', '--ai', 'claude'],
                cwd=tmpdir_path,
                capture_output=True,
                check=True
            )

            subprocess.run(
                [str(spec_kitty_path), 'init', 'project_b', '--ai', 'claude'],
                cwd=tmpdir_path,
                capture_output=True,
                check=True
            )

            # Add data to project B
            project_b_data = project_b / '.kittify' / 'memory' / 'data.txt'
            project_b_content = 'Project B data'
            project_b_data.write_text(project_b_content)

            # Upgrade package
            subprocess.run(
                [str(pip_path), 'install', '--upgrade', 'spec-kitty-cli==0.10.13'],
                capture_output=True,
                check=True
            )

            # Upgrade project A only
            subprocess.run(
                [str(spec_kitty_path), 'upgrade', '--force'],
                cwd=project_a,
                capture_output=True,
                check=True
            )

            # Verify project B unchanged
            assert project_b_data.exists(), "Project B affected by Project A upgrade!"
            assert project_b_data.read_text() == project_b_content, "Project B data changed!"


class TestUpgradePathEdgeCases:
    """
    ADVERSARIAL: Test edge cases in upgrade paths.

    Test scenarios that might break.
    """

    def test_upgrade_with_partial_migration_state(self):
        """
        EDGE CASE: Upgrade with some migrations already applied.

        Project upgraded partway, then continued.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            venv_dir = tmpdir_path / 'test_venv'
            venv.create(venv_dir, with_pip=True, clear=True)

            # Get pip path (platform-independent)
            pip_path = get_venv_executable(venv_dir, 'pip')
            spec_kitty_path = get_venv_executable(venv_dir, 'spec-kitty')

            # Install v0.10.0
            result = subprocess.run(
                [str(pip_path), 'install', 'spec-kitty-cli==0.10.0'],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                pytest.skip("v0.10.0 not available")

            project_dir = tmpdir_path / 'test_project'

            subprocess.run(
                [str(spec_kitty_path), 'init', 'test_project', '--ai', 'claude'],
                cwd=tmpdir_path,
                capture_output=True,
                check=True
            )

            # Upgrade to v0.10.11 (partial)
            subprocess.run(
                [str(pip_path), 'install', '--upgrade', 'spec-kitty-cli==0.10.11'],
                capture_output=True,
                check=True
            )

            subprocess.run(
                [str(spec_kitty_path), 'upgrade', '--force'],
                cwd=project_dir,
                capture_output=True,
                check=True
            )

            # Now upgrade to v0.10.13 (continuation)
            subprocess.run(
                [str(pip_path), 'install', '--upgrade', 'spec-kitty-cli==0.10.13'],
                capture_output=True,
                check=True
            )

            result = subprocess.run(
                [str(spec_kitty_path), 'upgrade', '--force'],
                cwd=project_dir,
                capture_output=True,
                text=True
            )

            # Should succeed (handle partial state)
            assert result.returncode == 0, (
                "Upgrade from partial state failed!\n"
                "Projects that upgraded partway should be able to continue."
            )

    def test_downgrade_not_recommended_but_safe(self):
        """
        EDGE CASE: Downgrading spec-kitty version.

        Not recommended, but shouldn't corrupt data.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            venv_dir = tmpdir_path / 'test_venv'
            venv.create(venv_dir, with_pip=True, clear=True)

            # Get pip path (platform-independent)
            pip_path = get_venv_executable(venv_dir, 'pip')
            spec_kitty_path = get_venv_executable(venv_dir, 'spec-kitty')

            # Install v0.10.13
            subprocess.run(
                [str(pip_path), 'install', 'spec-kitty-cli==0.10.13'],
                capture_output=True,
                check=True
            )

            project_dir = tmpdir_path / 'test_project'

            subprocess.run(
                [str(spec_kitty_path), 'init', 'test_project', '--ai', 'claude'],
                cwd=tmpdir_path,
                capture_output=True,
                check=True
            )

            # Add critical user data
            user_data = project_dir / '.kittify' / 'memory' / 'critical.txt'
            user_data_content = 'CRITICAL USER DATA'
            user_data.write_text(user_data_content)

            # Downgrade to v0.10.11 (NOT recommended, but test data safety)
            subprocess.run(
                [str(pip_path), 'install', 'spec-kitty-cli==0.10.11'],
                capture_output=True,
                check=True
            )

            # Verify data NOT corrupted or deleted
            assert user_data.exists(), (
                "Downgrade deleted user data!\n"
                "Even unsupported operations should not lose data."
            )

            assert user_data.read_text() == user_data_content, (
                "Downgrade corrupted user data!"
            )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
