"""Fixtures for distribution testing of templates and migrations.

This module provides fixtures for building wheels, creating clean virtualenvs,
and testing the PyPI user experience without SPEC_KITTY_TEMPLATE_ROOT bypass.
"""

import pytest
import subprocess
import shutil
from pathlib import Path
import zipfile
import venv
import re


@pytest.fixture(scope="session")
def spec_kitty_source():
    """Path to spec-kitty source repository for building wheel.

    Returns:
        Path: Path to spec-kitty repository
    """
    # Look for spec-kitty in standard locations
    candidates = [
        Path("/Users/robert/Code/spec-kitty"),
        Path(__file__).parent.parent.parent.parent.parent / "spec-kitty",
    ]

    for candidate in candidates:
        if candidate.exists() and (candidate / "src" / "specify_cli").exists():
            return candidate

    pytest.skip("spec-kitty source repository not found")


@pytest.fixture(scope="session")
def build_wheel(spec_kitty_source, tmp_path_factory):
    """Build spec-kitty wheel for distribution testing.

    This fixture builds the wheel once per test session for performance.
    The wheel is built from the spec-kitty source repository.

    Args:
        spec_kitty_source: Path to spec-kitty repo
        tmp_path_factory: Pytest factory for creating temp directories

    Returns:
        Path: Path to built wheel file

    Raises:
        pytest.Failed: If wheel build fails
    """
    dist_dir = spec_kitty_source / "dist"

    # Clean old builds
    if dist_dir.exists():
        shutil.rmtree(dist_dir)

    # Build wheel
    import sys
    result = subprocess.run(
        [sys.executable, "-m", "build", "--wheel"],
        cwd=spec_kitty_source,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        pytest.fail(f"Wheel build failed: {result.stderr}")

    # Find built wheel
    wheels = list(dist_dir.glob("spec_kitty_cli-*.whl"))
    if not wheels:
        pytest.fail("No wheel file found after build")

    return wheels[0]


@pytest.fixture
def clean_venv(tmp_path):
    """Create clean virtualenv for installation testing.

    Creates a fresh virtualenv for each test to ensure isolation.
    No spec-kitty or dependencies pre-installed.

    Args:
        tmp_path: Pytest temporary directory

    Returns:
        Path: Path to venv directory
    """
    venv_path = tmp_path / "test_venv"
    venv.create(venv_path, with_pip=True)
    return venv_path


@pytest.fixture
def installed_spec_kitty(build_wheel, clean_venv):
    """Install spec-kitty wheel in clean venv.

    This fixture installs the built wheel in a clean virtualenv,
    replicating the exact experience of a PyPI user installing
    spec-kitty for the first time.

    Args:
        build_wheel: Path to built wheel
        clean_venv: Path to clean virtualenv

    Returns:
        tuple: (venv_path, wheel_path, site_packages_path)

    Raises:
        pytest.Failed: If installation fails
    """
    pip = clean_venv / "bin" / "pip"

    # Install wheel
    result = subprocess.run(
        [str(pip), "install", str(build_wheel)],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        pytest.fail(f"Installation failed: {result.stderr}")

    # Find site-packages
    python = clean_venv / "bin" / "python"
    result = subprocess.run(
        [str(python), "-c",
         "import site; print(site.getsitepackages()[0])"],
        capture_output=True,
        text=True
    )
    site_packages = Path(result.stdout.strip())

    return clean_venv, build_wheel, site_packages


class DistributionPackage:
    """Helper for inspecting and validating built wheels.

    This class provides utilities for examining wheel contents,
    validating template bundling, and checking migration registry.
    """

    def __init__(self, wheel_path: Path):
        """Initialize with path to wheel file.

        Args:
            wheel_path: Path to .whl file
        """
        self.wheel_path = wheel_path
        self.version = self._extract_version()
        self.template_manifest = self._build_template_manifest()
        self.migration_list = self._build_migration_list()

    def _extract_version(self) -> str:
        """Extract version from wheel filename.

        Returns:
            str: Version string (e.g., "0.11.2")
        """
        # spec_kitty_cli-0.11.2-py3-none-any.whl -> 0.11.2
        name = self.wheel_path.name
        parts = name.split("-")
        return parts[1] if len(parts) > 1 else "unknown"

    def _build_template_manifest(self) -> list[str]:
        """List all template files in wheel.

        Returns:
            list: List of template file paths in wheel
        """
        with zipfile.ZipFile(self.wheel_path) as zf:
            return [
                name for name in zf.namelist()
                if "specify_cli/missions/" in name and name.endswith(".md")
            ]

    def _build_migration_list(self) -> list[str]:
        """Extract migration names from wheel.

        Parses migrations/__init__.py to find all registered migrations.

        Returns:
            list: List of migration identifiers (e.g., ["0.10.9_repair_templates"])
        """
        with zipfile.ZipFile(self.wheel_path) as zf:
            try:
                # Check multiple possible paths for migrations
                possible_paths = [
                    "specify_cli/upgrade/migrations/__init__.py",
                    "specify_cli/migrations/__init__.py"
                ]

                init_content = None
                for path in possible_paths:
                    try:
                        init_content = zf.read(path).decode()
                        break
                    except KeyError:
                        continue

                if not init_content:
                    return []

                # Parse for migration import statements like "from . import m_0_10_9_repair_templates"
                # Extract the module names and convert to migration_id format (replace first _ with .)
                import_pattern = r"from\s+\.\s+import\s+(m_\d+_\d+_\d+[\w_]*)"
                matches = re.findall(import_pattern, init_content)

                # Convert from m_0_10_9_repair_templates to 0.10.9_repair_templates
                migrations = []
                for match in matches:
                    # Remove 'm_' prefix and replace first two underscores with dots
                    parts = match[2:].split('_')  # Remove 'm_' prefix
                    if len(parts) >= 3:
                        # Convert 0_10_9_repair_templates to 0.10.9_repair_templates
                        migration_id = f"{parts[0]}.{parts[1]}.{parts[2]}"
                        if len(parts) > 3:
                            migration_id += "_" + "_".join(parts[3:])
                        migrations.append(migration_id)

                return list(set(migrations))
            except Exception:
                return []

    def validate_templates(self, required_templates: list[str]) -> list[str]:
        """Check for missing required templates.

        Args:
            required_templates: List of template paths to check

        Returns:
            list: List of missing templates (empty if all present)
        """
        missing = []
        for req in required_templates:
            if not any(req in path for path in self.template_manifest):
                missing.append(req)
        return missing

    def validate_migrations(self, expected_migrations: list[str]) -> list[str]:
        """Check for missing expected migrations.

        Args:
            expected_migrations: List of migration prefixes to check

        Returns:
            list: List of missing migrations (empty if all present)
        """
        missing = []
        for exp in expected_migrations:
            if not any(exp in mig for mig in self.migration_list):
                missing.append(exp)
        return missing

    def get_all_files(self) -> list[str]:
        """Get complete list of files in wheel.

        Returns:
            list: All file paths in wheel
        """
        with zipfile.ZipFile(self.wheel_path) as zf:
            return zf.namelist()


@pytest.fixture
def distribution_package(build_wheel):
    """Provide DistributionPackage helper for wheel inspection.

    Args:
        build_wheel: Path to built wheel

    Returns:
        DistributionPackage: Helper instance for wheel inspection
    """
    return DistributionPackage(build_wheel)
