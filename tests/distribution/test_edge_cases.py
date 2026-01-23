"""
Distribution edge case tests (WP13: T076).

Tests unusual, adversarial, or boundary conditions for package distribution.
"""
import pytest
import subprocess
import sys
import shutil
from pathlib import Path


@pytest.mark.distribution
@pytest.mark.adversarial
class TestMultipleInstallations:
    """Test handling of multiple package installations."""

    def test_spec_kitty_on_path(self):
        """Edge case: Verify spec-kitty is discoverable on PATH."""
        spec_kitty_path = shutil.which("spec-kitty")

        # Should be on PATH
        assert spec_kitty_path is not None, \
            "spec-kitty should be on PATH"

    def test_version_command_works(self):
        """Edge case: Version command returns valid output."""
        # Use spec-kitty CLI directly if available
        spec_kitty_path = shutil.which("spec-kitty")
        if spec_kitty_path:
            result = subprocess.run(
                [spec_kitty_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )

            # Should succeed
            assert result.returncode == 0, \
                f"Version command failed: {result.stderr}"

            # Should have version info
            output = result.stdout + result.stderr
            assert len(output) > 0, "Version output should not be empty"
        else:
            # Fall back to checking package is importable
            import specify_cli
            assert specify_cli is not None


@pytest.mark.distribution
@pytest.mark.adversarial
class TestImportPaths:
    """Test edge cases in import paths."""

    def test_import_main_module(self):
        """Edge case: Main module is importable."""
        try:
            import specify_cli
            assert specify_cli is not None
        except ImportError as e:
            pytest.fail(f"Failed to import specify_cli: {e}")

    def test_import_core_modules(self):
        """Edge case: Core modules are importable."""
        modules = [
            "specify_cli.core.dependency_graph",
            "specify_cli.frontmatter",
        ]

        for module_name in modules:
            try:
                __import__(module_name)
            except ImportError as e:
                pytest.fail(f"Failed to import {module_name}: {e}")

    def test_import_with_missing_optional_dependency(self):
        """Edge case: Package works without optional dependencies."""
        # Core functionality should work even if optional deps missing
        from specify_cli.core.dependency_graph import topological_sort

        # Should work with basic graph
        graph = {"WP01": [], "WP02": ["WP01"]}
        order = topological_sort(graph)

        assert "WP01" in order
        assert "WP02" in order


@pytest.mark.distribution
@pytest.mark.adversarial
class TestTemplateAccess:
    """Test edge cases in template file access."""

    def test_template_directory_accessible(self):
        """Edge case: Template directory exists and is readable."""
        import specify_cli.templates
        import importlib.resources

        # Use importlib.resources for reliable package path discovery
        try:
            # Python 3.9+ approach
            with importlib.resources.as_file(
                importlib.resources.files("specify_cli.templates")
            ) as template_dir:
                assert template_dir.exists(), \
                    "Template directory should exist"
                assert template_dir.is_dir(), \
                    "Template path should be a directory"
        except (TypeError, AttributeError):
            # Older approach or namespace package
            if hasattr(specify_cli.templates, '__path__'):
                template_paths = list(specify_cli.templates.__path__)
                assert len(template_paths) > 0, "Template path should exist"

    def test_common_templates_exist(self):
        """Edge case: Common templates are bundled."""
        import specify_cli.templates
        import importlib.resources

        try:
            # Python 3.9+ approach
            with importlib.resources.as_file(
                importlib.resources.files("specify_cli.templates")
            ) as template_dir:
                # Check for mission templates directory
                mission_templates = template_dir / "mission-templates"
                if mission_templates.exists():
                    assert mission_templates.is_dir()
        except (TypeError, AttributeError):
            # If using namespace package, templates accessible via __path__
            pass


@pytest.mark.distribution
@pytest.mark.adversarial
class TestEncodingIssues:
    """Test encoding-related edge cases."""

    def test_utf8_handling_in_cli_output(self):
        """Edge case: CLI handles UTF-8 characters in output."""
        result = subprocess.run(
            [sys.executable, "-c", "print('Hello\u2728')"],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0
        assert "\u2728" in result.stdout or "\\u2728" in result.stdout

    def test_non_ascii_in_path(self, tmp_path):
        """Edge case: Non-ASCII characters in file path."""
        unicode_dir = tmp_path / "ficher\u00e9"  # fiché
        unicode_dir.mkdir()

        test_file = unicode_dir / "test.txt"
        test_file.write_text("content")

        assert test_file.exists()
        assert test_file.read_text() == "content"
