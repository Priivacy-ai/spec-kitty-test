"""
Test: Version Detection and Upgrade Reliability (Distribution Tests)

Purpose: Verify version_utils.py provides reliable version detection across all
installation modes, preventing the "0.5.0-dev" fallback bug in upgrades.

HISTORICAL CONTEXT:
Prior to version_utils.py, spec-kitty used a hardcoded "0.5.0-dev" fallback when
importlib.metadata failed (common in editable installs). This caused:
- spec-kitty upgrade writing "0.5.0-dev" to metadata.yaml
- Accidental downgrades from 0.13.x to 0.5.0-dev
- Broken version comparison logic

The version_utils.py fix implements a three-tier fallback:
1. importlib.metadata (best practice for pip installs)
2. pyproject.toml parsing (fallback for editable installs)
3. "0.0.0-dev" (last resort, makes failures obvious)

THIS TEST FILE DOES NOT USE SPEC_KITTY_TEMPLATE_ROOT BYPASS.
We test what users actually experience.

Test Coverage:
- TestPyPIInstallVersion: Version detection from PyPI packages
- TestEditableInstallVersion: Version detection from pip install -e
- TestLocalWheelVersion: Version detection from built wheels
- TestUpgradeVersionUpdate: Upgrade command writes correct version
- TestVersionCommandOutput: CLI --version shows correct version

Implementation: Commit 865229a in spec-kitty repo (2026-01-26)
Target Version: 0.13.2+ (when version_utils.py ships to PyPI)
"""

import subprocess
import sys
import tempfile
import venv
import zipfile
from datetime import datetime
from pathlib import Path

import pytest
import yaml


def has_version_utils_in_pypi():
    """Check if version_utils.py is available in the PyPI package.

    This is a runtime check - returns False until version_utils.py ships to PyPI.
    Once it ships, these tests will automatically start running.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        venv_dir = Path(tmpdir) / 'check_venv'
        try:
            venv.create(venv_dir, with_pip=True, clear=True)
            pip_path = venv_dir / 'bin' / 'pip'
            if not pip_path.exists():
                pip_path = venv_dir / 'Scripts' / 'pip.exe'

            # Install latest from PyPI
            result = subprocess.run(
                [str(pip_path), 'install', 'spec-kitty-cli'],
                capture_output=True,
                timeout=60
            )
            if result.returncode != 0:
                return False

            # Check for version_utils
            python_path = venv_dir / 'bin' / 'python'
            if not python_path.exists():
                python_path = venv_dir / 'Scripts' / 'python.exe'

            result = subprocess.run(
                [str(python_path), '-c', 'import specify_cli.version_utils'],
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False


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


def get_installed_version(venv_dir):
    """Get spec-kitty version from venv using importlib.metadata."""
    python_path = get_venv_executable(venv_dir, 'python')

    result = subprocess.run(
        [
            str(python_path), '-c',
            'from importlib.metadata import version; print(version("spec-kitty-cli"))'
        ],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return None

    return result.stdout.strip()


def get_module_version(venv_dir):
    """Get spec-kitty version from venv using module import."""
    python_path = get_venv_executable(venv_dir, 'python')

    result = subprocess.run(
        [
            str(python_path), '-c',
            'import specify_cli; print(specify_cli.__version__)'
        ],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return None

    return result.stdout.strip()


class TestPyPIInstallVersion:
    """
    CRITICAL: Test version detection from PyPI-installed packages.

    This is the most common installation mode. Version detection must work
    flawlessly here.

    These tests automatically start running once version_utils.py ships to PyPI.
    """

    @pytest.mark.skipif(
        not has_version_utils_in_pypi(),
        reason="Waiting for version_utils.py to be released to PyPI (will auto-enable when available)"
    )
    def test_pypi_install_has_version_utils_module(self):
        """
        PREREQUISITE: Verify version_utils.py is included in PyPI package.

        Without this, the fix doesn't ship to users.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / 'test_venv'
            venv.create(venv_dir, with_pip=True, clear=True)

            pip_path = get_venv_executable(venv_dir, 'pip')
            python_path = get_venv_executable(venv_dir, 'python')

            # Install latest spec-kitty from PyPI
            result = subprocess.run(
                [str(pip_path), 'install', 'spec-kitty-cli'],
                capture_output=True,
                text=True
            )

            assert result.returncode == 0, f"PyPI install failed: {result.stderr}"

            # Check version_utils.py exists
            result = subprocess.run(
                [
                    str(python_path), '-c',
                    'import specify_cli.version_utils; print("OK")'
                ],
                capture_output=True,
                text=True
            )

            assert result.returncode == 0, (
                "CRITICAL: version_utils.py not in PyPI package!\n"
                f"Import error: {result.stderr}\n"
                "The fix has not shipped to users."
            )

    @pytest.mark.skipif(
        not has_version_utils_in_pypi(),
        reason="Waiting for version_utils.py to be released to PyPI (will auto-enable when available)"
    )
    def test_pypi_version_not_fallback(self):
        """
        CRITICAL: PyPI install must not use fallback versions.

        Should use importlib.metadata, not pyproject.toml or "0.0.0-dev".
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / 'test_venv'
            venv.create(venv_dir, with_pip=True, clear=True)

            pip_path = get_venv_executable(venv_dir, 'pip')

            # Install latest
            subprocess.run(
                [str(pip_path), 'install', 'spec-kitty-cli'],
                capture_output=True,
                check=True
            )

            module_version = get_module_version(venv_dir)
            metadata_version = get_installed_version(venv_dir)

            # Should NOT be fallback values
            assert module_version != "0.5.0-dev", (
                "REGRESSION: Using old hardcoded fallback!"
            )
            assert module_version != "0.0.0-dev", (
                "Using last-resort fallback in normal PyPI install!"
            )

            # Should match metadata
            assert module_version == metadata_version, (
                f"Version mismatch: module={module_version}, metadata={metadata_version}\n"
                "Should use importlib.metadata, not fallback"
            )

    @pytest.mark.skipif(
        not has_version_utils_in_pypi(),
        reason="Waiting for version_utils.py to be released to PyPI (will auto-enable when available)"
    )
    def test_pypi_upgrade_writes_correct_version(self):
        """
        CRITICAL: spec-kitty upgrade must write actual version, not fallback.

        This is THE BUG that version_utils.py fixes.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            venv_dir = tmpdir_path / 'test_venv'
            venv.create(venv_dir, with_pip=True, clear=True)

            pip_path = get_venv_executable(venv_dir, 'pip')
            spec_kitty_path = get_venv_executable(venv_dir, 'spec-kitty')

            # Install latest
            subprocess.run(
                [str(pip_path), 'install', 'spec-kitty-cli'],
                capture_output=True,
                check=True
            )

            # Get actual version
            actual_version = get_installed_version(venv_dir)

            # Initialize project
            project_dir = tmpdir_path / 'test_project'
            subprocess.run(
                [str(spec_kitty_path), 'init', 'test_project', '--ai', 'claude'],
                cwd=tmpdir_path,
                capture_output=True,
                text=True,
                check=True
            )

            # Run upgrade
            result = subprocess.run(
                [str(spec_kitty_path), 'upgrade'],
                cwd=project_dir,
                capture_output=True,
                text=True
            )

            # Should succeed
            assert result.returncode == 0, f"Upgrade failed: {result.stderr}"

            # Check metadata.yaml
            metadata_file = project_dir / '.kittify' / 'metadata.yaml'
            assert metadata_file.exists(), "metadata.yaml not found"

            with open(metadata_file) as f:
                metadata = yaml.safe_load(f)

            written_version = metadata['spec_kitty']['version']

            # CRITICAL: Should write ACTUAL version
            assert written_version == actual_version, (
                f"BUG: Upgrade wrote wrong version!\n"
                f"Expected: {actual_version}\n"
                f"Got: {written_version}\n"
                "This is the bug version_utils.py should fix."
            )

            # Should NOT be fallback values
            assert written_version != "0.5.0-dev", (
                "CRITICAL: Upgrade wrote old fallback version!"
            )
            assert written_version != "0.0.0-dev", (
                "CRITICAL: Upgrade wrote new fallback version!"
            )


class TestEditableInstallVersion:
    """
    CRITICAL: Test version detection from editable installs (pip install -e).

    This is where the original bug occurred. importlib.metadata often fails in
    editable installs, triggering the fallback chain.

    version_utils.py should fall back to pyproject.toml (not "0.5.0-dev").
    """

    def test_editable_install_has_version_utils(self, spec_kitty_repo_root):
        """
        PREREQUISITE: Verify version_utils.py exists in local repo.
        """
        version_utils_path = spec_kitty_repo_root / 'src' / 'specify_cli' / 'version_utils.py'

        assert version_utils_path.exists(), (
            f"version_utils.py not found at {version_utils_path}\n"
            "The fix has not been implemented yet."
        )

        content = version_utils_path.read_text()

        # Should have three-tier fallback
        assert 'importlib.metadata' in content, "Should try importlib.metadata first"
        assert 'pyproject.toml' in content, "Should have pyproject.toml fallback"
        assert '0.0.0-dev' in content, "Should have last-resort fallback"

    def test_editable_version_not_old_fallback(self, spec_kitty_repo_root):
        """
        CRITICAL: Editable install must not use "0.5.0-dev" fallback.

        Should use pyproject.toml fallback, not hardcoded "0.5.0-dev".
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / 'test_venv'
            venv.create(venv_dir, with_pip=True, clear=True)

            pip_path = get_venv_executable(venv_dir, 'pip')

            # Install in editable mode
            result = subprocess.run(
                [str(pip_path), 'install', '-e', str(spec_kitty_repo_root)],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                pytest.skip(f"Editable install failed: {result.stderr}")

            module_version = get_module_version(venv_dir)

            # CRITICAL: Should NOT use old fallback
            assert module_version != "0.5.0-dev", (
                "REGRESSION: Still using old hardcoded fallback!\n"
                "version_utils.py should fall back to pyproject.toml"
            )

            # Should be valid semver
            import re
            assert re.match(r'^\d+\.\d+\.\d+', module_version), (
                f"Invalid version format: {module_version}"
            )

    def test_editable_upgrade_writes_correct_version(self, spec_kitty_repo_root):
        """
        CRITICAL: Editable install upgrade must write pyproject.toml version.

        This is the EXACT scenario that caused the bug.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            venv_dir = tmpdir_path / 'test_venv'
            venv.create(venv_dir, with_pip=True, clear=True)

            pip_path = get_venv_executable(venv_dir, 'pip')
            spec_kitty_path = get_venv_executable(venv_dir, 'spec-kitty')

            # Install in editable mode
            result = subprocess.run(
                [str(pip_path), 'install', '-e', str(spec_kitty_repo_root)],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                pytest.skip(f"Editable install failed: {result.stderr}")

            # Get expected version from pyproject.toml
            pyproject_path = spec_kitty_repo_root / 'pyproject.toml'
            pyproject_content = pyproject_path.read_text()

            import re
            version_match = re.search(r'version\s*=\s*"(\d+\.\d+\.\d+)"', pyproject_content)
            assert version_match, "Could not find version in pyproject.toml"

            expected_version = version_match.group(1)

            # Initialize project
            project_dir = tmpdir_path / 'test_project'
            result = subprocess.run(
                [str(spec_kitty_path), 'init', 'test_project', '--ai', 'claude'],
                cwd=tmpdir_path,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                pytest.skip(f"Init failed: {result.stderr}")

            # Run upgrade
            result = subprocess.run(
                [str(spec_kitty_path), 'upgrade'],
                cwd=project_dir,
                capture_output=True,
                text=True
            )

            assert result.returncode == 0, f"Upgrade failed: {result.stderr}"

            # Check metadata.yaml
            metadata_file = project_dir / '.kittify' / 'metadata.yaml'
            with open(metadata_file) as f:
                metadata = yaml.safe_load(f)

            written_version = metadata['spec_kitty']['version']

            # CRITICAL: Should write pyproject.toml version
            assert written_version == expected_version, (
                f"BUG: Editable install upgrade wrote wrong version!\n"
                f"Expected (from pyproject.toml): {expected_version}\n"
                f"Got: {written_version}\n"
                "This is the exact bug version_utils.py should fix."
            )

            # Should NOT be fallback
            assert written_version != "0.5.0-dev", "Used old fallback!"
            assert written_version != "0.0.0-dev", "Used new fallback!"


class TestLocalWheelVersion:
    """
    CRITICAL: Test version detection from locally built wheels.

    Developers build wheels from local repo. Version detection must work
    correctly in built packages.
    """

    def test_local_wheel_includes_version_utils(self, spec_kitty_repo_root):
        """
        CRITICAL: Verify version_utils.py is included in built wheel.

        If pyproject.toml doesn't include it, the fix won't ship.
        """
        # Build wheel
        dist_dir = spec_kitty_repo_root / 'dist'
        dist_dir.mkdir(exist_ok=True)

        result = subprocess.run(
            [sys.executable, '-m', 'build', '--wheel', '--outdir', str(dist_dir)],
            cwd=spec_kitty_repo_root,
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, f"Wheel build failed: {result.stderr}"

        # Find wheel
        wheels = list(dist_dir.glob('*.whl'))
        assert len(wheels) > 0, "No wheel created"

        wheel_file = wheels[0]

        # Check contents
        with zipfile.ZipFile(wheel_file, 'r') as zf:
            namelist = zf.namelist()

            # Look for version_utils.py
            version_utils_files = [
                name for name in namelist
                if 'version_utils.py' in name
            ]

            assert len(version_utils_files) > 0, (
                "CRITICAL: version_utils.py not in wheel!\n"
                f"Wheel contents:\n" + "\n".join(sorted(namelist)[:30]) + "\n...\n"
                "The fix will not ship to users.\n"
                "Check pyproject.toml package configuration."
            )

    def test_local_wheel_version_detection_works(self, spec_kitty_repo_root):
        """
        CRITICAL: Version detection must work from locally built wheel.
        """
        # Build wheel
        dist_dir = spec_kitty_repo_root / 'dist'
        dist_dir.mkdir(exist_ok=True)

        subprocess.run(
            [sys.executable, '-m', 'build', '--wheel', '--outdir', str(dist_dir)],
            cwd=spec_kitty_repo_root,
            capture_output=True,
            check=True
        )

        wheel_file = list(dist_dir.glob('*.whl'))[0]

        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / 'test_venv'
            venv.create(venv_dir, with_pip=True, clear=True)

            pip_path = get_venv_executable(venv_dir, 'pip')

            # Install wheel
            subprocess.run(
                [str(pip_path), 'install', str(wheel_file)],
                capture_output=True,
                check=True
            )

            module_version = get_module_version(venv_dir)
            metadata_version = get_installed_version(venv_dir)

            # Should have version
            assert module_version is not None, "Could not get module version"
            assert metadata_version is not None, "Could not get metadata version"

            # Should match
            assert module_version == metadata_version, (
                f"Version mismatch: module={module_version}, metadata={metadata_version}"
            )

            # Should not be fallback
            assert module_version != "0.5.0-dev", "Using old fallback"
            assert module_version != "0.0.0-dev", "Using new fallback"


class TestVersionCommandOutput:
    """
    Test spec-kitty --version command shows correct version in all modes.
    """

    def test_version_command_shows_correct_version_editable(self, spec_kitty_repo_root):
        """
        Test: spec-kitty --version shows pyproject.toml version in editable install.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / 'test_venv'
            venv.create(venv_dir, with_pip=True, clear=True)

            pip_path = get_venv_executable(venv_dir, 'pip')
            spec_kitty_path = get_venv_executable(venv_dir, 'spec-kitty')

            # Editable install
            result = subprocess.run(
                [str(pip_path), 'install', '-e', str(spec_kitty_repo_root)],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                pytest.skip(f"Editable install failed: {result.stderr}")

            # Get expected version
            pyproject_path = spec_kitty_repo_root / 'pyproject.toml'
            pyproject_content = pyproject_path.read_text()

            import re
            version_match = re.search(r'version\s*=\s*"(\d+\.\d+\.\d+)"', pyproject_content)
            expected_version = version_match.group(1)

            # Run --version
            result = subprocess.run(
                [str(spec_kitty_path), '--version'],
                capture_output=True,
                text=True
            )

            assert result.returncode == 0, f"--version failed: {result.stderr}"

            output = result.stdout + result.stderr

            # Should show correct version
            assert expected_version in output, (
                f"--version should show {expected_version}\n"
                f"Got: {output}"
            )

            # Should not show fallback
            assert "0.5.0-dev" not in output, "Showing old fallback version"
            assert "0.0.0-dev" not in output, "Showing new fallback version"

    @pytest.mark.skipif(
        not has_version_utils_in_pypi(),
        reason="Waiting for version_utils.py to be released to PyPI (will auto-enable when available)"
    )
    def test_version_command_shows_correct_version_pypi(self):
        """
        Test: spec-kitty --version shows correct version from PyPI install.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / 'test_venv'
            venv.create(venv_dir, with_pip=True, clear=True)

            pip_path = get_venv_executable(venv_dir, 'pip')
            spec_kitty_path = get_venv_executable(venv_dir, 'spec-kitty')

            # PyPI install
            subprocess.run(
                [str(pip_path), 'install', 'spec-kitty-cli'],
                capture_output=True,
                check=True
            )

            # Get expected version
            expected_version = get_installed_version(venv_dir)

            # Run --version
            result = subprocess.run(
                [str(spec_kitty_path), '--version'],
                capture_output=True,
                text=True,
                check=True
            )

            output = result.stdout + result.stderr

            # Should show correct version
            assert expected_version in output, (
                f"--version should show {expected_version}\n"
                f"Got: {output}"
            )
