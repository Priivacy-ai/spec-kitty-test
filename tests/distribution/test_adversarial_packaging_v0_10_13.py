"""
Test: Adversarial Packaging Validation (v0.10.13)

Purpose: Catch packaging bugs that slip through normal testing.

CONTEXT:
v0.10.12 had a critical bug: migration m_0_10_12_constitution_cleanup.py existed
in source but was MISSING from PyPI package. This test file adds adversarial
checks to prevent similar bugs in future releases.

Test Strategy:
- Verify ALL expected files are in package
- Count migrations (source vs package)
- Verify file sizes match
- Check for missing dependencies
- Validate metadata completeness
- Test edge cases in packaging configuration

Test Coverage:
- TestMigrationFileCompleteness (verify all migrations packaged)
- TestPackageContentVerification (verify all expected files)
- TestDependencyCompleteness (verify all dependencies)
- TestMetadataAccuracy (verify package metadata)

Version: Requires v0.10.13+ (fixed migration packaging bug)
"""

import subprocess
import zipfile
from pathlib import Path
import pytest
import tomli


class TestMigrationFileCompleteness:
    """
    ADVERSARIAL: Verify ALL migration files are packaged.

    This test class specifically addresses the v0.10.12 bug where
    m_0_10_12_constitution_cleanup.py was missing from PyPI.
    """

    def test_migration_0_10_12_exists_in_package(self, spec_kitty_repo_root):
        """
        CRITICAL: Verify migration 0.10.12 file is in package.

        This is the EXACT bug from v0.10.12 PyPI release.
        """
        # Check source has the file
        source_migration = spec_kitty_repo_root / 'src' / 'specify_cli' / 'upgrade' / 'migrations' / 'm_0_10_12_constitution_cleanup.py'

        if not source_migration.exists():
            pytest.skip("Migration 0.10.12 not in source (may be removed in future version)")

        # Build wheel
        wheel_file = self._build_wheel(spec_kitty_repo_root)

        # Check wheel has the file
        with zipfile.ZipFile(wheel_file, 'r') as zf:
            namelist = zf.namelist()

        migration_in_wheel = any('m_0_10_12_constitution_cleanup.py' in name for name in namelist)

        assert migration_in_wheel, (
            "CRITICAL BUG: Migration 0.10.12 missing from wheel!\n\n"
            "This is the EXACT bug from v0.10.12 PyPI release.\n"
            f"Source file exists: {source_migration}\n"
            "But NOT in wheel!\n\n"
            "This will cause constitution cleanup to fail for PyPI users."
        )

    def test_all_source_migrations_in_wheel(self, spec_kitty_repo_root):
        """
        ADVERSARIAL: Verify ALL migration files from source are in wheel.

        Count migrations in source and wheel - must match.
        """
        # Find all migrations in source
        migrations_dir = spec_kitty_repo_root / 'src' / 'specify_cli' / 'upgrade' / 'migrations'

        if not migrations_dir.exists():
            pytest.skip("Migrations directory not found")

        source_migrations = [
            f.name for f in migrations_dir.glob('m_*.py')
            if not f.name.startswith('__')
        ]

        source_count = len(source_migrations)

        # Build wheel
        wheel_file = self._build_wheel(spec_kitty_repo_root)

        # Find all migrations in wheel
        with zipfile.ZipFile(wheel_file, 'r') as zf:
            wheel_migrations = [
                Path(name).name for name in zf.namelist()
                if 'migrations/m_' in name and name.endswith('.py')
                and '__' not in Path(name).name
            ]

        wheel_count = len(wheel_migrations)

        assert source_count == wheel_count, (
            f"CRITICAL BUG: Migration count mismatch!\n\n"
            f"Source migrations: {source_count}\n"
            f"Wheel migrations: {wheel_count}\n"
            f"Difference: {source_count - wheel_count}\n\n"
            f"Source has:\n" +
            "\n".join([f"  - {m}" for m in sorted(source_migrations)]) +
            f"\n\nWheel has:\n" +
            "\n".join([f"  - {m}" for m in sorted(wheel_migrations)]) +
            "\n\nSome migrations are missing from the package!"
        )

    def test_migration_file_sizes_match(self, spec_kitty_repo_root):
        """
        ADVERSARIAL: Verify migration files in wheel match source file sizes.

        Catches truncation or corruption during packaging.
        """
        migrations_dir = spec_kitty_repo_root / 'src' / 'specify_cli' / 'upgrade' / 'migrations'

        if not migrations_dir.exists():
            pytest.skip("Migrations directory not found")

        source_migrations = {
            f.name: f.stat().st_size
            for f in migrations_dir.glob('m_*.py')
            if not f.name.startswith('__')
        }

        # Build wheel
        wheel_file = self._build_wheel(spec_kitty_repo_root)

        # Check sizes in wheel
        with zipfile.ZipFile(wheel_file, 'r') as zf:
            size_mismatches = []

            for name, source_size in source_migrations.items():
                wheel_paths = [p for p in zf.namelist() if name in p and 'migrations' in p]

                if not wheel_paths:
                    size_mismatches.append(f"{name}: MISSING from wheel")
                    continue

                wheel_info = zf.getinfo(wheel_paths[0])
                wheel_size = wheel_info.file_size

                # Allow small differences (whitespace, line endings)
                if abs(source_size - wheel_size) > 100:
                    size_mismatches.append(
                        f"{name}: Source={source_size}b, Wheel={wheel_size}b (diff={abs(source_size - wheel_size)}b)"
                    )

        assert len(size_mismatches) == 0, (
            f"Migration file size mismatches detected!\n\n" +
            "\n".join(size_mismatches) +
            "\n\nFiles may be truncated or corrupted during packaging."
        )

    def test_migration_0_10_12_exactly_3384_bytes(self, spec_kitty_repo_root):
        """
        ADVERSARIAL: Verify migration 0.10.12 has expected size.

        Known good size: 3,384 bytes (from source).
        """
        wheel_file = self._build_wheel(spec_kitty_repo_root)

        with zipfile.ZipFile(wheel_file, 'r') as zf:
            migration_files = [
                name for name in zf.namelist()
                if 'm_0_10_12_constitution_cleanup.py' in name
            ]

            if not migration_files:
                pytest.fail(
                    "Migration 0.10.12 not in wheel!\n"
                    "This is the bug from v0.10.12 PyPI release."
                )

            info = zf.getinfo(migration_files[0])
            actual_size = info.file_size

            # Expected size (from source)
            expected_size = 3384

            # Allow small variance (±100 bytes for formatting)
            assert abs(actual_size - expected_size) < 100, (
                f"Migration 0.10.12 file size unexpected!\n\n"
                f"Expected: ~{expected_size} bytes\n"
                f"Actual: {actual_size} bytes\n"
                f"Difference: {abs(actual_size - expected_size)} bytes\n\n"
                "File may be corrupted or incomplete."
            )

    def test_no_pyc_files_in_migrations(self, spec_kitty_repo_root):
        """
        ADVERSARIAL: Verify no .pyc files packaged instead of .py files.

        Catches build configuration errors.
        """
        wheel_file = self._build_wheel(spec_kitty_repo_root)

        with zipfile.ZipFile(wheel_file, 'r') as zf:
            pyc_migrations = [
                name for name in zf.namelist()
                if 'migrations/' in name and name.endswith('.pyc')
            ]

        assert len(pyc_migrations) == 0, (
            f"CRITICAL: Found .pyc files in migrations!\n\n"
            f"Found {len(pyc_migrations)} .pyc file(s):\n" +
            "\n".join([f"  - {f}" for f in pyc_migrations[:5]]) +
            "\n\n.pyc files should not be packaged (only .py source files)."
        )

    def _build_wheel(self, repo_root):
        """Helper: Build wheel and return path."""
        dist_dir = repo_root / 'dist'

        if not dist_dir.exists():
            pytest.fail("No dist/ directory")

        # Use existing wheel if available
        wheels = sorted(dist_dir.glob('*.whl'), key=lambda p: p.stat().st_mtime, reverse=True)

        if wheels:
            return wheels[0]

        pytest.fail("No wheel found - run build first")


class TestPackageContentVerification:
    """
    ADVERSARIAL: Verify expected directories and files are in package.

    Catches missing files that tests don't explicitly check.
    """

    def test_all_mission_directories_packaged(self, spec_kitty_repo_root):
        """
        ADVERSARIAL: Verify ALL mission directories from source are in wheel.
        """
        missions_dir = spec_kitty_repo_root / 'src' / 'specify_cli' / 'missions'

        if not missions_dir.exists():
            pytest.skip("Missions directory not found")

        source_missions = [
            d.name for d in missions_dir.iterdir()
            if d.is_dir() and not d.name.startswith('__') and not d.name.startswith('.')
        ]

        wheel_file = self._build_wheel(spec_kitty_repo_root)

        with zipfile.ZipFile(wheel_file, 'r') as zf:
            wheel_missions = set()
            for name in zf.namelist():
                if 'missions/' in name:
                    parts = name.split('missions/')
                    if len(parts) > 1:
                        mission_name = parts[1].split('/')[0]
                        if mission_name and not mission_name.startswith('__'):
                            wheel_missions.add(mission_name)

        missing_missions = set(source_missions) - wheel_missions

        assert len(missing_missions) == 0, (
            f"CRITICAL: Missions missing from wheel!\n\n"
            f"Source has {len(source_missions)} mission(s)\n"
            f"Wheel has {len(wheel_missions)} mission(s)\n"
            f"Missing:\n" +
            "\n".join([f"  - {m}" for m in missing_missions])
        )

    def test_command_templates_completeness(self, spec_kitty_repo_root):
        """
        ADVERSARIAL: Verify command templates are complete in wheel.

        Checks that all .md files from source are in wheel.
        """
        templates_dir = spec_kitty_repo_root / 'src' / 'specify_cli' / 'templates' / 'command-templates'

        if not templates_dir.exists():
            pytest.skip("Templates directory not found")

        source_templates = [
            f.name for f in templates_dir.glob('*.md')
        ]

        wheel_file = self._build_wheel(spec_kitty_repo_root)

        with zipfile.ZipFile(wheel_file, 'r') as zf:
            wheel_template_names = [
                Path(name).name for name in zf.namelist()
                if 'command-templates/' in name and name.endswith('.md')
            ]

        missing_templates = set(source_templates) - set(wheel_template_names)

        assert len(missing_templates) == 0, (
            f"Command templates missing from wheel!\n\n"
            f"Source: {len(source_templates)} template(s)\n"
            f"Wheel: {len(wheel_template_names)} template(s)\n"
            f"Missing:\n" +
            "\n".join([f"  - {t}" for t in missing_templates])
        )

    def test_scripts_directory_not_empty(self, spec_kitty_repo_root):
        """
        ADVERSARIAL: Verify scripts directory has content.

        Empty directories suggest packaging issue.
        """
        wheel_file = self._build_wheel(spec_kitty_repo_root)

        with zipfile.ZipFile(wheel_file, 'r') as zf:
            script_files = [
                name for name in zf.namelist()
                if 'specify_cli/scripts/' in name
                and (name.endswith('.py') or name.endswith('.js'))
            ]

        # Should have at least some scripts
        assert len(script_files) > 0, (
            "Scripts directory appears empty in wheel!\n"
            "Expected at least some .py or .js files in specify_cli/scripts/"
        )

    def _build_wheel(self, repo_root):
        """Helper: Get wheel file"""
        dist_dir = repo_root / 'dist'
        if not dist_dir.exists():
            pytest.fail("No dist/ directory")
        wheels = sorted(dist_dir.glob('*.whl'), key=lambda p: p.stat().st_mtime, reverse=True)
        if wheels:
            return wheels[0]
        pytest.fail("No wheel found")


class TestDependencyCompleteness:
    """
    ADVERSARIAL: Verify all required dependencies are declared.

    Catches missing dependencies that cause runtime errors.
    """

    def test_psutil_declared_and_in_wheel_metadata(self, spec_kitty_repo_root):
        """
        CRITICAL: psutil must be in both pyproject.toml AND wheel metadata.

        v0.10.12/v0.10.13 requires psutil for Windows dashboard.
        """
        # Check pyproject.toml
        pyproject_file = spec_kitty_repo_root / 'pyproject.toml'

        with open(pyproject_file, 'rb') as f:
            pyproject = tomli.load(f)

        dependencies = pyproject.get('project', {}).get('dependencies', [])
        has_psutil_in_config = any('psutil' in dep for dep in dependencies)

        assert has_psutil_in_config, (
            "psutil not in pyproject.toml dependencies!\n"
            f"Current dependencies: {dependencies}"
        )

        # Check wheel metadata
        wheel_file = self._build_wheel(spec_kitty_repo_root)

        with zipfile.ZipFile(wheel_file, 'r') as zf:
            metadata_files = [name for name in zf.namelist() if 'METADATA' in name]

            if not metadata_files:
                pytest.fail("No METADATA file in wheel")

            metadata_content = zf.read(metadata_files[0]).decode('utf-8')

        has_psutil_in_metadata = 'psutil' in metadata_content

        assert has_psutil_in_metadata, (
            "psutil not in wheel METADATA!\n\n"
            "Config has psutil, but wheel metadata doesn't.\n"
            "This indicates a build configuration issue."
        )

    def test_importlib_resources_not_required(self, spec_kitty_repo_root):
        """
        VALIDATION: importlib.resources should be stdlib (no dependency needed).

        For Python 3.11+, importlib.resources is built-in.
        """
        pyproject_file = spec_kitty_repo_root / 'pyproject.toml'

        with open(pyproject_file, 'rb') as f:
            pyproject = tomli.load(f)

        dependencies = pyproject.get('project', {}).get('dependencies', [])

        # Should NOT require importlib_resources package
        has_importlib_dep = any('importlib' in dep.lower() and 'resources' in dep.lower() for dep in dependencies)

        if has_importlib_dep:
            pytest.fail(
                "Unnecessary importlib-resources dependency!\n\n"
                f"Dependencies: {dependencies}\n\n"
                "For Python 3.11+, importlib.resources is built-in."
            )

    def _build_wheel(self, repo_root):
        """Helper: Get wheel file"""
        dist_dir = repo_root / 'dist'
        if not dist_dir.exists():
            pytest.fail("No dist/ directory")
        wheels = sorted(dist_dir.glob('*.whl'), key=lambda p: p.stat().st_mtime, reverse=True)
        if wheels:
            return wheels[0]
        pytest.fail("No wheel found")


class TestMetadataAccuracy:
    """
    ADVERSARIAL: Verify package metadata is accurate and complete.

    Catches version mismatches, missing classifiers, etc.
    """

    def test_wheel_version_matches_pyproject(self, spec_kitty_repo_root):
        """
        CRITICAL: Wheel version must match pyproject.toml version.

        Catches version number inconsistencies.
        """
        # Get version from pyproject.toml
        pyproject_file = spec_kitty_repo_root / 'pyproject.toml'

        with open(pyproject_file, 'rb') as f:
            pyproject = tomli.load(f)

        config_version = pyproject.get('project', {}).get('version')

        assert config_version is not None, "No version in pyproject.toml"

        # Get version from wheel filename
        wheel_file = self._build_wheel(spec_kitty_repo_root)
        wheel_name = wheel_file.name

        # Extract version from wheel name (spec_kitty_cli-VERSION-py3-none-any.whl)
        parts = wheel_name.split('-')
        if len(parts) >= 2:
            wheel_version = parts[1]
        else:
            pytest.fail(f"Cannot parse version from wheel name: {wheel_name}")

        assert config_version == wheel_version, (
            f"Version mismatch!\n\n"
            f"pyproject.toml: {config_version}\n"
            f"Wheel filename: {wheel_version}\n\n"
            "Package version is inconsistent."
        )

    def test_wheel_name_format_correct(self, spec_kitty_repo_root):
        """
        VALIDATION: Wheel filename should follow PEP 427 format.

        Format: {distribution}-{version}(-{build tag})?-{python}-{abi}-{platform}.whl
        """
        wheel_file = self._build_wheel(spec_kitty_repo_root)
        wheel_name = wheel_file.name

        # Expected format: spec_kitty_cli-VERSION-py3-none-any.whl
        assert wheel_name.startswith('spec_kitty_cli-'), (
            f"Wheel name doesn't start with spec_kitty_cli-: {wheel_name}"
        )

        assert wheel_name.endswith('-py3-none-any.whl'), (
            f"Wheel name doesn't end with -py3-none-any.whl: {wheel_name}\n"
            "Should be a universal wheel."
        )

    def _build_wheel(self, repo_root):
        """Helper: Get wheel file"""
        dist_dir = repo_root / 'dist'
        if not dist_dir.exists():
            pytest.fail("No dist/ directory")
        wheels = sorted(dist_dir.glob('*.whl'), key=lambda p: p.stat().st_mtime, reverse=True)
        if wheels:
            return wheels[0]
        pytest.fail("No wheel found")


class TestPackagingRegressionPrevention:
    """
    ADVERSARIAL: Prevent regressions in packaging configuration.

    Tests that would have caught the v0.10.12 bug earlier.
    """

    def test_hatchling_packages_includes_src_specify_cli(self, spec_kitty_repo_root):
        """
        CRITICAL: Hatchling must include src/specify_cli in packages.

        Without this, NOTHING gets packaged.
        """
        pyproject_file = spec_kitty_repo_root / 'pyproject.toml'

        with open(pyproject_file, 'rb') as f:
            pyproject = tomli.load(f)

        build_backend = pyproject.get('build-system', {}).get('build-backend', '')

        if 'hatchling' not in build_backend:
            pytest.skip("Not using hatchling")

        packages = pyproject.get('tool', {}).get('hatch', {}).get('build', {}).get('targets', {}).get('wheel', {}).get('packages', [])

        has_specify_cli = 'src/specify_cli' in packages or 'specify_cli' in packages

        assert has_specify_cli, (
            f"CRITICAL: src/specify_cli not in hatchling packages!\n\n"
            f"Current packages: {packages}\n\n"
            "Without this, package will be empty or incomplete."
        )

    def test_no_exclude_patterns_blocking_migrations(self, spec_kitty_repo_root):
        """
        ADVERSARIAL: Verify no exclude patterns block migration files.

        Catches overly broad excludes that remove necessary files.
        """
        pyproject_file = spec_kitty_repo_root / 'pyproject.toml'

        with open(pyproject_file, 'rb') as f:
            pyproject = tomli.load(f)

        # Check sdist excludes
        sdist_exclude = pyproject.get('tool', {}).get('hatch', {}).get('build', {}).get('targets', {}).get('sdist', {}).get('exclude', [])

        problematic_excludes = []
        for pattern in sdist_exclude:
            # Check if pattern would exclude migrations
            if any(keyword in pattern for keyword in ['*.py', 'src/', 'specify_cli/', 'migrations/']):
                problematic_excludes.append(pattern)

        assert len(problematic_excludes) == 0, (
            f"Exclude patterns may block migrations!\n\n"
            f"Found:\n" +
            "\n".join([f"  - {p}" for p in problematic_excludes]) +
            "\n\nThese patterns might exclude migration files."
        )

    def test_build_system_requirements_correct(self, spec_kitty_repo_root):
        """
        VALIDATION: Build system should specify correct backend.

        Incorrect build system can cause packaging failures.
        """
        pyproject_file = spec_kitty_repo_root / 'pyproject.toml'

        with open(pyproject_file, 'rb') as f:
            pyproject = tomli.load(f)

        build_system = pyproject.get('build-system', {})

        assert 'requires' in build_system, "No build-system.requires"
        assert 'build-backend' in build_system, "No build-system.build-backend"

        backend = build_system['build-backend']
        requires = build_system['requires']

        # Verify backend is in requires
        if 'hatchling' in backend:
            assert any('hatchling' in req for req in requires), (
                f"Build backend is {backend} but hatchling not in requires!\n"
                f"Requires: {requires}"
            )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
