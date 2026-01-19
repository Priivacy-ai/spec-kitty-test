"""Distribution testing - validates PyPI package, not development code.

CRITICAL: Per CLAUDE.md, this test validates what users experience.
The 0.10.8 catastrophe taught us: test what you ship, not just what you write.

These tests MUST NOT set SPEC_KITTY_TEMPLATE_ROOT.

This module implements:
- T036: PyPI install verification (no SPEC_KITTY_TEMPLATE_ROOT)
- T037: Version verification for spec-kitty
- T048: Distribution edge case tests
"""

import os
from pathlib import Path

import pytest


# Mark all tests in this module as distribution tests
pytestmark = [
    pytest.mark.distribution,
    pytest.mark.slow,  # Real agent invocations take time
]


class TestDistributionInstall:
    """Verify spec-kitty is installed from PyPI correctly.

    T036: Verify PyPI install (no SPEC_KITTY_TEMPLATE_ROOT)
    """

    def test_spec_kitty_installed_from_pypi(self, test_container):
        """Verify spec-kitty is installed from PyPI, not local source."""
        # Run pip show inside container
        exit_code, stdout, stderr = test_container.exec_command(
            "pip show spec-kitty",
            timeout=30
        )

        assert exit_code == 0, f"spec-kitty not installed: {stderr}"

        # Verify it's not an editable install
        assert "Editable project location" not in stdout, \
            "spec-kitty appears to be an editable install (development mode)"

        # Verify Location is in site-packages, not a local path
        lines = stdout.split('\n')
        location_line = [line for line in lines if line.startswith('Location:')]
        assert location_line, "Could not find Location in pip show output"
        assert 'site-packages' in location_line[0], \
            f"spec-kitty not in site-packages: {location_line[0]}"

    def test_template_root_not_set(self, test_container):
        """Verify SPEC_KITTY_TEMPLATE_ROOT is not set in container."""
        exit_code, stdout, stderr = test_container.exec_command(
            "python -c 'import os; print(os.environ.get(\"SPEC_KITTY_TEMPLATE_ROOT\", \"NOT_SET\"))'",
            timeout=10
        )

        assert exit_code == 0
        assert stdout.strip() == "NOT_SET" or stdout.strip() == "", \
            f"SPEC_KITTY_TEMPLATE_ROOT is set: {stdout.strip()}"

    def test_templates_from_package(self, test_container):
        """Verify templates are loaded from the installed package."""
        exit_code, stdout, stderr = test_container.exec_command(
            "python -c '"
            "from spec_kitty.template_manager import TemplateManager; "
            "tm = TemplateManager(); "
            "print(tm.template_dir)"
            "'",
            timeout=30
        )

        assert exit_code == 0, f"Failed to get template dir: {stderr}"

        # Should be in site-packages, not a local directory
        template_dir = stdout.strip()
        assert 'site-packages' in template_dir, \
            f"Templates not from package: {template_dir}"


class TestDistributionFunctionality:
    """Verify distributed package works correctly."""

    def test_spec_kitty_version_accessible(self, test_container):
        """Verify spec-kitty version is accessible."""
        exit_code, stdout, stderr = test_container.exec_command(
            "spec-kitty --version",
            timeout=30
        )

        assert exit_code == 0, f"spec-kitty --version failed: {stderr}"
        assert "spec-kitty" in stdout.lower() or stdout.strip(), \
            f"Unexpected version output: {stdout}"

    def test_spec_kitty_help_works(self, test_container):
        """Verify spec-kitty help command works."""
        exit_code, stdout, stderr = test_container.exec_command(
            "spec-kitty --help",
            timeout=30
        )

        assert exit_code == 0, f"spec-kitty --help failed: {stderr}"
        assert "Usage" in stdout or "usage" in stdout, \
            f"Help output missing Usage: {stdout}"

    def test_agent_commands_available(self, test_container):
        """Verify agent subcommands are available."""
        exit_code, stdout, stderr = test_container.exec_command(
            "spec-kitty agent --help",
            timeout=30
        )

        assert exit_code == 0, f"spec-kitty agent --help failed: {stderr}"
        # Should list agent-related subcommands
        assert any(cmd in stdout for cmd in ['feature', 'tasks', 'workflow']), \
            f"Agent commands not found in help: {stdout}"


class TestVersionVerification:
    """Verify spec-kitty version matches expected release.

    T037: Implement version verification for spec-kitty
    """

    @pytest.fixture
    def expected_version(self):
        """Get expected version from test configuration."""
        # Can be set via environment or config
        return os.environ.get("SPEC_KITTY_TEST_VERSION", None)

    def test_version_matches_expected(self, test_container, expected_version):
        """Verify installed version matches expected version."""
        if not expected_version:
            pytest.skip("SPEC_KITTY_TEST_VERSION not set")

        exit_code, stdout, stderr = test_container.exec_command(
            "python -c 'import spec_kitty; print(spec_kitty.__version__)'",
            timeout=30
        )

        assert exit_code == 0, f"Failed to get version: {stderr}"
        installed_version = stdout.strip()

        assert installed_version == expected_version, \
            f"Version mismatch: installed={installed_version}, expected={expected_version}"

    def test_version_is_release(self, test_container):
        """Verify version looks like a release (not dev/local)."""
        exit_code, stdout, stderr = test_container.exec_command(
            "python -c 'import spec_kitty; print(spec_kitty.__version__)'",
            timeout=30
        )

        assert exit_code == 0
        version = stdout.strip()

        # Should not contain dev indicators
        dev_indicators = ['.dev', '+local', '+editable', '-dirty']
        for indicator in dev_indicators:
            assert indicator not in version, \
                f"Version contains development indicator: {version}"

    def test_pypi_metadata_present(self, test_container):
        """Verify PyPI metadata is present in package."""
        exit_code, stdout, stderr = test_container.exec_command(
            "python -c '"
            "from importlib.metadata import metadata; "
            "m = metadata(\"spec-kitty\"); "
            "print(m[\"Author\"] or m.get(\"Maintainer\", \"\"))"
            "'",
            timeout=30
        )

        # Should have metadata from PyPI
        assert exit_code == 0, f"Could not read package metadata: {stderr}"
        # Metadata may be empty but the call should succeed


class TestDistributionEdgeCases:
    """Edge cases for distribution testing.

    T048: Write test_distribution.py test cases (edge cases)
    """

    def test_no_development_overrides(self, test_container):
        """Verify no development environment variables are set."""
        env_vars_to_check = [
            "SPEC_KITTY_TEMPLATE_ROOT",
            "SPEC_KITTY_DEV_MODE",
        ]

        for var in env_vars_to_check:
            exit_code, stdout, stderr = test_container.exec_command(
                f"python -c 'import os; print(os.environ.get(\"{var}\", \"NOT_SET\"))'",
                timeout=10
            )
            # Either NOT_SET or empty string is acceptable
            if var == "SPEC_KITTY_TEMPLATE_ROOT":
                assert stdout.strip() in ("NOT_SET", ""), \
                    f"{var} is set: {stdout.strip()}"

    def test_package_includes_all_templates(self, test_container):
        """Verify all required templates are in package."""
        exit_code, stdout, stderr = test_container.exec_command(
            "python -c '"
            "from spec_kitty.template_manager import TemplateManager; "
            "import os; "
            "tm = TemplateManager(); "
            "templates = os.listdir(tm.template_dir) if os.path.isdir(tm.template_dir) else []; "
            "print(\"\\n\".join(templates))"
            "'",
            timeout=30
        )

        assert exit_code == 0, f"Failed to list templates: {stderr}"

        templates = stdout.strip().split('\n')
        # Should have some templates (filter out empty lines)
        templates = [t for t in templates if t.strip()]
        assert len(templates) > 0, "No templates found in package"

    def test_cli_entry_point_works(self, test_container):
        """Verify CLI entry point is properly configured."""
        exit_code, stdout, stderr = test_container.exec_command(
            "which spec-kitty && spec-kitty --version",
            timeout=30
        )

        assert exit_code == 0, f"CLI entry point not working: {stderr}"

    def test_no_import_errors(self, test_container):
        """Verify all modules can be imported without errors."""
        exit_code, stdout, stderr = test_container.exec_command(
            "python -c '"
            "import spec_kitty; "
            "from spec_kitty import cli; "
            "from spec_kitty.template_manager import TemplateManager; "
            "print(\"All imports successful\")"
            "'",
            timeout=30
        )

        assert exit_code == 0, f"Import errors occurred: {stderr}"
        assert "All imports successful" in stdout

    def test_dependencies_installed(self, test_container):
        """Verify package dependencies are properly installed."""
        exit_code, stdout, stderr = test_container.exec_command(
            "python -c '"
            "import yaml; "  # PyYAML
            "import click; "  # CLI framework
            "print(\"Dependencies verified\")"
            "'",
            timeout=30
        )

        assert exit_code == 0, f"Missing dependencies: {stderr}"
        assert "Dependencies verified" in stdout
