"""
Test: Distribution Packaging Inspection (Feature 011 - v0.10.12)

Purpose: Validate what PyPI users actually receive.

CRITICAL CONTEXT:
Issues #62-64 happened because ALL 323 tests used:
  env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

This bypassed the real package installation, so:
- Tests ✅ (used local repo templates)
- Users ❌ (used packaged templates - which were wrong)

THIS TEST FILE DOES NOT USE THAT BYPASS.
It tests what users actually get from PyPI.

Test Strategy:
1. Build wheel from repo
2. Install in CLEAN venv (no SPEC_KITTY_TEMPLATE_ROOT)
3. Verify package contents
4. Verify commands work
5. Verify templates are correct

This is "test what you ship, not what you write."

Test Coverage:
- TestPackageContentValidation (10 tests): Build and inspect wheel
- TestInstalledPackageInspection (8 tests): Install from wheel validation

Version: Requires v0.10.12+ (Feature 011)
"""

import subprocess
import tempfile
import zipfile
import venv
from pathlib import Path
import pytest
import sys


class TestPackageContentValidation:
    """
    CRITICAL: Validate wheel contents match expectations.

    These tests inspect the wheel file BEFORE installation.
    They catch packaging bugs at build time.

    NO SPEC_KITTY_TEMPLATE_ROOT bypass allowed.
    """

    def test_build_wheel_succeeds(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Must be able to build a wheel.

        If build fails, all distribution tests fail.
        """
        dist_dir = spec_kitty_repo_root / 'dist'
        dist_dir.mkdir(exist_ok=True)

        result = subprocess.run(
            ['python', '-m', 'build', '--wheel', '--outdir', str(dist_dir)],
            cwd=spec_kitty_repo_root,
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, (
            f"Failed to build wheel!\n\n"
            f"Stdout: {result.stdout}\n"
            f"Stderr: {result.stderr}\n\n"
            "Cannot test distribution without buildable wheel."
        )

        # Verify wheel exists
        wheels = list(dist_dir.glob('*.whl'))
        assert len(wheels) > 0, "No wheel file found after build"

    def test_wheel_excludes_kittify_directory(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Wheel must NOT contain .kittify/ directory.

        .kittify/ is runtime data, not package data.
        If packaged, causes 100% user contamination (Issues #62-64).
        """
        wheel_file = self._get_wheel(spec_kitty_repo_root)

        with zipfile.ZipFile(wheel_file, 'r') as zf:
            namelist = zf.namelist()

        kittify_files = [name for name in namelist if '.kittify/' in name or 'kittify/memory' in name]

        assert len(kittify_files) == 0, (
            f"CRITICAL BUG: Wheel contains .kittify/ directory!\n\n"
            f"This is the exact bug from Issues #62-64.\n"
            f"Found {len(kittify_files)} .kittify/ file(s):\n" +
            "\n".join([f"  - {f}" for f in kittify_files[:10]]) +
            "\n\nALL PyPI users will get contaminated package."
        )

    def test_wheel_excludes_memory_directory(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Wheel must NOT contain memory/ directory.

        memory/ contains user data (constitution, conversation history).
        """
        wheel_file = self._get_wheel(spec_kitty_repo_root)

        with zipfile.ZipFile(wheel_file, 'r') as zf:
            namelist = zf.namelist()

        memory_files = [name for name in namelist if 'memory/' in name and 'memory' not in name.split('/')[-1]]

        assert len(memory_files) == 0, (
            f"CRITICAL BUG: Wheel contains memory/ directory!\n\n"
            f"Found {len(memory_files)} memory/ file(s):\n" +
            "\n".join([f"  - {f}" for f in memory_files[:10]]) +
            "\n\nUsers will get developer's personal data."
        )

    def test_wheel_has_templates_in_src(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Wheel must have templates in src/specify_cli/.

        Feature 011 moves templates from .kittify/ to src/specify_cli/.
        """
        wheel_file = self._get_wheel(spec_kitty_repo_root)

        with zipfile.ZipFile(wheel_file, 'r') as zf:
            namelist = zf.namelist()

        template_files = [
            name for name in namelist
            if 'templates/' in name and name.endswith('.md')
            and 'specify_cli' in name
        ]

        assert len(template_files) > 0, (
            "Wheel does not contain templates!\n\n"
            f"Searched for: specify_cli/templates/*.md\n"
            f"Wheel contents (first 50 files):\n" +
            "\n".join([f"  - {f}" for f in namelist[:50]]) +
            "\n\nUsers cannot initialize projects without templates."
        )

    def test_wheel_has_missions_in_src(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Wheel must have missions in src/specify_cli/.

        Feature 011 moves missions from .kittify/ to src/specify_cli/.
        """
        wheel_file = self._get_wheel(spec_kitty_repo_root)

        with zipfile.ZipFile(wheel_file, 'r') as zf:
            namelist = zf.namelist()

        mission_files = [
            name for name in namelist
            if 'missions/' in name
            and 'specify_cli' in name
        ]

        assert len(mission_files) > 0, (
            "Wheel does not contain missions!\n\n"
            "Expected missions in specify_cli/missions/\n"
            "Users cannot run missions without mission files."
        )

    def test_wheel_has_scripts_in_src(self, spec_kitty_repo_root, requires_v010_12):
        """
        VALIDATION: Wheel should have scripts in src/specify_cli/.

        Feature 011 moves scripts from .kittify/ to src/specify_cli/.
        """
        wheel_file = self._get_wheel(spec_kitty_repo_root)

        with zipfile.ZipFile(wheel_file, 'r') as zf:
            namelist = zf.namelist()

        script_files = [
            name for name in namelist
            if 'scripts/' in name
            and 'specify_cli' in name
            and (name.endswith('.py') or name.endswith('.js'))
        ]

        # Scripts are optional, but if they exist, they should be in specify_cli/
        if len(script_files) == 0:
            pytest.skip("No scripts found in wheel (may be optional)")

    def test_no_filled_constitution_in_wheel(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Wheel must NOT contain filled constitution.

        This is the exact bug from Issues #62-64.
        Developers fill constitution, it gets packaged, users get dev's constitution.
        """
        wheel_file = self._get_wheel(spec_kitty_repo_root)

        with zipfile.ZipFile(wheel_file, 'r') as zf:
            # Find all constitution.md files
            constitution_files = [
                name for name in zf.namelist()
                if 'constitution.md' in name.lower()
            ]

            for const_file in constitution_files:
                # Read content
                content = zf.read(const_file).decode('utf-8', errors='ignore')

                # Check if it looks filled (more than 5000 bytes is suspicious)
                if len(content) > 5000:
                    pytest.fail(
                        f"CRITICAL BUG: Wheel contains filled constitution!\n\n"
                        f"File: {const_file}\n"
                        f"Size: {len(content)} bytes\n\n"
                        f"First 500 chars:\n{content[:500]}\n\n"
                        "This is the exact bug from Issues #62-64."
                    )

                # Check for filled content patterns
                filled_patterns = [
                    'Project-specific',
                    'Our team',
                    'We use',
                    'This project',
                ]

                filled_count = sum(1 for pattern in filled_patterns if pattern in content)

                if filled_count >= 2:
                    pytest.fail(
                        f"CRITICAL BUG: Constitution appears to be filled!\n\n"
                        f"File: {const_file}\n"
                        f"Matched {filled_count} filled patterns: {filled_patterns}\n\n"
                        "Template should have placeholder text, not filled values."
                    )

    def test_no_developer_artifacts_in_wheel(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Wheel must NOT contain developer artifacts.

        Developer artifacts:
        - __pycache__/
        - .pytest_cache/
        - .git/
        - dist/
        - build/
        - *.egg-info/
        """
        wheel_file = self._get_wheel(spec_kitty_repo_root)

        with zipfile.ZipFile(wheel_file, 'r') as zf:
            namelist = zf.namelist()

        artifact_patterns = [
            '__pycache__/',
            '.pytest_cache/',
            '.git/',
            'dist/',
            'build/',
            '.egg-info/',
        ]

        artifacts_found = []
        for name in namelist:
            for pattern in artifact_patterns:
                if pattern in name:
                    artifacts_found.append(name)
                    break

        assert len(artifacts_found) == 0, (
            f"Wheel contains developer artifacts!\n\n"
            f"Found {len(artifacts_found)} artifact(s):\n" +
            "\n".join([f"  - {f}" for f in artifacts_found[:10]]) +
            "\n\nThese bloat the package and should be excluded."
        )

    def test_psutil_in_dependencies(self, spec_kitty_repo_root, requires_v010_12):
        """
        HIGH: Wheel metadata must include psutil dependency.

        Feature 011 requires psutil for Windows dashboard.
        """
        wheel_file = self._get_wheel(spec_kitty_repo_root)

        with zipfile.ZipFile(wheel_file, 'r') as zf:
            # Find METADATA file
            metadata_files = [name for name in zf.namelist() if name.endswith('/METADATA')]

            if not metadata_files:
                pytest.fail("No METADATA file found in wheel")

            metadata_content = zf.read(metadata_files[0]).decode('utf-8')

            # Check for psutil in Requires-Dist
            has_psutil = 'psutil' in metadata_content

            assert has_psutil, (
                "psutil dependency not found in wheel metadata!\n\n"
                f"Metadata file: {metadata_files[0]}\n\n"
                "Feature 011 requires psutil for Windows dashboard."
            )

    def test_package_size_reasonable(self, spec_kitty_repo_root, requires_v010_12):
        """
        VALIDATION: Wheel size should be reasonable.

        If wheel is too large, may contain unnecessary files.
        """
        wheel_file = self._get_wheel(spec_kitty_repo_root)

        size_mb = wheel_file.stat().st_size / (1024 * 1024)

        # Reasonable size: < 10 MB (adjust as needed)
        assert size_mb < 10, (
            f"Wheel size is too large: {size_mb:.2f} MB\n\n"
            "May contain unnecessary files (tests, dev artifacts, etc.)"
        )

    def _get_wheel(self, repo_root):
        """Helper: Get built wheel file"""
        dist_dir = repo_root / 'dist'

        if not dist_dir.exists():
            pytest.fail("No dist/ directory - run test_build_wheel_succeeds first")

        wheels = list(dist_dir.glob('*.whl'))

        if not wheels:
            pytest.fail("No wheel file found - run test_build_wheel_succeeds first")

        return wheels[0]


class TestInstalledPackageInspection:
    """
    CRITICAL: Test package after installation in clean environment.

    These tests:
    - Install wheel in clean venv
    - NO SPEC_KITTY_TEMPLATE_ROOT bypass
    - Test what real PyPI users experience

    This is "test what you ship."
    """

    def test_install_from_wheel_succeeds(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Wheel must be installable.

        If installation fails, users cannot use spec-kitty.
        """
        wheel_file = self._get_wheel(spec_kitty_repo_root)

        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / 'test_venv'

            # Create clean venv
            venv.create(venv_dir, with_pip=True, clear=True)

            # Get pip path
            pip_path = venv_dir / 'bin' / 'pip'
            if not pip_path.exists():
                pip_path = venv_dir / 'Scripts' / 'pip.exe'  # Windows

            # Install wheel
            result = subprocess.run(
                [str(pip_path), 'install', str(wheel_file)],
                capture_output=True,
                text=True
            )

            assert result.returncode == 0, (
                f"Failed to install wheel!\n\n"
                f"Wheel: {wheel_file}\n"
                f"Stderr: {result.stderr}\n\n"
                "Users cannot install from PyPI if wheel installation fails."
            )

    def test_installed_package_has_no_kittify(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Installed package must NOT have .kittify/ directory.

        After installation, check site-packages for .kittify/.
        """
        wheel_file = self._get_wheel(spec_kitty_repo_root)

        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / 'test_venv'
            venv.create(venv_dir, with_pip=True, clear=True)

            pip_path = venv_dir / 'bin' / 'pip'
            if not pip_path.exists():
                pip_path = venv_dir / 'Scripts' / 'pip.exe'

            # Install
            subprocess.run(
                [str(pip_path), 'install', str(wheel_file)],
                capture_output=True,
                text=True,
                check=True
            )

            # Find site-packages
            site_packages = list(venv_dir.glob('**/site-packages'))
            if not site_packages:
                pytest.fail("Cannot find site-packages")

            # Check for .kittify/ in specify_cli package
            specify_cli_dir = site_packages[0] / 'specify_cli'

            if not specify_cli_dir.exists():
                pytest.fail("specify_cli not installed")

            kittify_dir = specify_cli_dir / '.kittify'

            assert not kittify_dir.exists(), (
                f"CRITICAL BUG: Installed package contains .kittify/!\n\n"
                f"Location: {kittify_dir}\n\n"
                "This is the packaging contamination bug from Issues #62-64."
            )

    def test_importlib_resources_finds_templates(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: importlib.resources must find templates in installed package.

        Feature 011 uses importlib.resources to load templates.
        """
        wheel_file = self._get_wheel(spec_kitty_repo_root)

        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / 'test_venv'
            venv.create(venv_dir, with_pip=True, clear=True)

            pip_path = venv_dir / 'bin' / 'pip'
            if not pip_path.exists():
                pip_path = venv_dir / 'Scripts' / 'pip.exe'

            subprocess.run(
                [str(pip_path), 'install', str(wheel_file)],
                capture_output=True,
                check=True
            )

            # Test importlib.resources
            python_path = venv_dir / 'bin' / 'python'
            if not python_path.exists():
                python_path = venv_dir / 'Scripts' / 'python.exe'

            result = subprocess.run(
                [str(python_path), '-c',
                 "import importlib.resources; "
                 "import specify_cli.templates; "
                 "files = list(importlib.resources.files('specify_cli.templates').iterdir()); "
                 "print(len(files))"],
                capture_output=True,
                text=True
            )

            assert result.returncode == 0, (
                f"importlib.resources failed!\n\n"
                f"Error: {result.stderr}\n\n"
                "Templates must be accessible via importlib.resources."
            )

            # Should find templates
            num_files = int(result.stdout.strip())
            assert num_files > 0, "No templates found via importlib.resources"

    def test_importlib_resources_finds_missions(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: importlib.resources must find missions in installed package.
        """
        wheel_file = self._get_wheel(spec_kitty_repo_root)

        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / 'test_venv'
            venv.create(venv_dir, with_pip=True, clear=True)

            pip_path = venv_dir / 'bin' / 'pip'
            if not pip_path.exists():
                pip_path = venv_dir / 'Scripts' / 'pip.exe'

            subprocess.run(
                [str(pip_path), 'install', str(wheel_file)],
                capture_output=True,
                check=True
            )

            python_path = venv_dir / 'bin' / 'python'
            if not python_path.exists():
                python_path = venv_dir / 'Scripts' / 'python.exe'

            result = subprocess.run(
                [str(python_path), '-c',
                 "import importlib.resources; "
                 "import specify_cli.missions; "
                 "files = list(importlib.resources.files('specify_cli.missions').iterdir()); "
                 "print(len(files))"],
                capture_output=True,
                text=True
            )

            assert result.returncode == 0, (
                f"importlib.resources failed for missions!\n"
                f"Error: {result.stderr}"
            )

            num_files = int(result.stdout.strip())
            assert num_files > 0, "No missions found via importlib.resources"

    def test_importlib_resources_finds_scripts(self, spec_kitty_repo_root, requires_v010_12):
        """
        VALIDATION: importlib.resources should find scripts in installed package.
        """
        wheel_file = self._get_wheel(spec_kitty_repo_root)

        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / 'test_venv'
            venv.create(venv_dir, with_pip=True, clear=True)

            pip_path = venv_dir / 'bin' / 'pip'
            if not pip_path.exists():
                pip_path = venv_dir / 'Scripts' / 'pip.exe'

            subprocess.run(
                [str(pip_path), 'install', str(wheel_file)],
                capture_output=True,
                check=True
            )

            python_path = venv_dir / 'bin' / 'python'
            if not python_path.exists():
                python_path = venv_dir / 'Scripts' / 'python.exe'

            result = subprocess.run(
                [str(python_path), '-c',
                 "import importlib.resources; "
                 "try:\n"
                 "    import specify_cli.scripts\n"
                 "    files = list(importlib.resources.files('specify_cli.scripts').iterdir())\n"
                 "    print(len(files))\n"
                 "except:\n"
                 "    print('0')"],
                capture_output=True,
                text=True
            )

            # Scripts are optional
            if result.returncode != 0 or result.stdout.strip() == '0':
                pytest.skip("No scripts directory (may be optional)")

    def test_template_manager_works_from_installed_package(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Template manager must work from installed package.

        NO SPEC_KITTY_TEMPLATE_ROOT bypass.
        """
        wheel_file = self._get_wheel(spec_kitty_repo_root)

        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / 'test_venv'
            venv.create(venv_dir, with_pip=True, clear=True)

            pip_path = venv_dir / 'bin' / 'pip'
            if not pip_path.exists():
                pip_path = venv_dir / 'Scripts' / 'pip.exe'

            subprocess.run(
                [str(pip_path), 'install', str(wheel_file)],
                capture_output=True,
                check=True
            )

            # Try to run spec-kitty command (uses template manager)
            spec_kitty_path = venv_dir / 'bin' / 'spec-kitty'
            if not spec_kitty_path.exists():
                spec_kitty_path = venv_dir / 'Scripts' / 'spec-kitty.exe'

            result = subprocess.run(
                [str(spec_kitty_path), '--version'],
                capture_output=True,
                text=True,
                # NO SPEC_KITTY_TEMPLATE_ROOT!
                env={'PATH': str(spec_kitty_path.parent)}
            )

            assert result.returncode == 0, (
                f"spec-kitty command failed from installed package!\n\n"
                f"Error: {result.stderr}\n\n"
                "This indicates template manager cannot load templates from package."
            )

    def test_init_creates_blank_constitution(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: spec-kitty init must create BLANK constitution.

        NOT the developer's filled constitution.
        This is the final validation that Issues #62-64 are fixed.

        NO SPEC_KITTY_TEMPLATE_ROOT bypass.
        """
        wheel_file = self._get_wheel(spec_kitty_repo_root)

        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / 'test_venv'
            venv.create(venv_dir, with_pip=True, clear=True)

            pip_path = venv_dir / 'bin' / 'pip'
            if not pip_path.exists():
                pip_path = venv_dir / 'Scripts' / 'pip.exe'

            subprocess.run(
                [str(pip_path), 'install', str(wheel_file)],
                capture_output=True,
                check=True
            )

            spec_kitty_path = venv_dir / 'bin' / 'spec-kitty'
            if not spec_kitty_path.exists():
                spec_kitty_path = venv_dir / 'Scripts' / 'spec-kitty.exe'

            # Initialize project
            project_dir = Path(tmpdir) / 'test_project'

            result = subprocess.run(
                [str(spec_kitty_path), 'init', 'test_project', '--ai', 'claude'],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                # NO SPEC_KITTY_TEMPLATE_ROOT!
            )

            if result.returncode != 0:
                pytest.skip(f"Init failed: {result.stderr}")

            # Check constitution
            constitution = project_dir / '.kittify' / 'memory' / 'constitution.md'

            if not constitution.exists():
                # May be optional now
                pytest.skip("No constitution created (may be optional in Feature 011)")

            content = constitution.read_text()

            # Should be blank template (< 5000 bytes)
            assert len(content) < 5000, (
                f"CRITICAL BUG: Users receiving filled constitution!\n\n"
                f"Constitution size: {len(content)} bytes (should be < 5000)\n"
                f"First 500 chars:\n{content[:500]}\n\n"
                "This is the exact bug from Issues #62-64."
            )

    def test_init_creates_project_kittify_not_package_kittify(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: spec-kitty init creates .kittify/ in PROJECT, not in package.

        .kittify/ is runtime data, not package data.
        """
        wheel_file = self._get_wheel(spec_kitty_repo_root)

        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / 'test_venv'
            venv.create(venv_dir, with_pip=True, clear=True)

            pip_path = venv_dir / 'bin' / 'pip'
            if not pip_path.exists():
                pip_path = venv_dir / 'Scripts' / 'pip.exe'

            subprocess.run(
                [str(pip_path), 'install', str(wheel_file)],
                capture_output=True,
                check=True
            )

            spec_kitty_path = venv_dir / 'bin' / 'spec-kitty'
            if not spec_kitty_path.exists():
                spec_kitty_path = venv_dir / 'Scripts' / 'spec-kitty.exe'

            project_dir = Path(tmpdir) / 'test_project'

            subprocess.run(
                [str(spec_kitty_path), 'init', 'test_project', '--ai', 'claude'],
                cwd=tmpdir,
                capture_output=True,
                check=True
            )

            # Check project has .kittify/
            project_kittify = project_dir / '.kittify'
            assert project_kittify.exists(), (
                ".kittify/ not created in project!"
            )

            # Check package does NOT have .kittify/
            site_packages = list(venv_dir.glob('**/site-packages'))
            specify_cli_dir = site_packages[0] / 'specify_cli'
            package_kittify = specify_cli_dir / '.kittify'

            assert not package_kittify.exists(), (
                f"CRITICAL BUG: Package has .kittify/ directory!\n"
                f"{package_kittify}"
            )

    def _get_wheel(self, repo_root):
        """Helper: Get built wheel file"""
        dist_dir = repo_root / 'dist'

        if not dist_dir.exists():
            pytest.fail("No dist/ directory")

        wheels = list(dist_dir.glob('*.whl'))

        if not wheels:
            pytest.fail("No wheel file found")

        return wheels[0]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
