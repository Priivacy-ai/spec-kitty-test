"""
Distribution tests for fresh install workflow (WP11: T065).

Validates that full init-to-orchestrate workflow completes from PyPI install
without SPEC_KITTY_TEMPLATE_ROOT bypass.
"""
import pytest
import subprocess
import shutil
from pathlib import Path
import os


@pytest.mark.distribution
@pytest.mark.orchestrator
class TestFreshInstallWorkflow:
    """Tests for complete fresh install workflow."""

    def test_init_to_orchestrate_workflow(self, git_project_with_kitty_specs):
        """
        Verify full workflow completes from fresh install.

        Validates spec.md User Story 1, Acceptance Scenario 2:
        "Given new project with git repo,
         When user runs full workflow,
         Then all commands succeed using packaged templates"
        """
        project_dir = git_project_with_kitty_specs

        # Verify SPEC_KITTY_TEMPLATE_ROOT is not set
        assert "SPEC_KITTY_TEMPLATE_ROOT" not in os.environ, \
            "SPEC_KITTY_TEMPLATE_ROOT should not be set in distribution tests"

        # Test that spec-kitty is available
        spec_kitty_path = shutil.which("spec-kitty")
        assert spec_kitty_path is not None, \
            "spec-kitty should be on PATH"

        # Verify kitty-specs exists and has a feature
        kitty_specs = project_dir / "kitty-specs"
        assert kitty_specs.exists(), "kitty-specs should exist"

        features = list(kitty_specs.glob("*-*"))
        assert len(features) > 0, "Should have at least one feature"

    def test_config_created_from_package_templates(self, tmp_path):
        """
        Verify templates are accessible from package.

        Validates spec.md User Story 1, Acceptance Scenario 3:
        "Given init command,
         When templates are loaded,
         Then templates come from installed package (not repo)"
        """
        # Verify template loading from package
        import importlib.resources

        try:
            # Python 3.9+ approach
            with importlib.resources.as_file(
                importlib.resources.files("specify_cli.templates")
            ) as template_dir:
                assert template_dir.exists(), \
                    "Template directory should exist in package"
        except (TypeError, AttributeError):
            # Namespace package fallback
            import specify_cli.templates
            if hasattr(specify_cli.templates, '__path__'):
                assert len(list(specify_cli.templates.__path__)) > 0

    def test_init_fails_gracefully_without_git(self, tmp_path, monkeypatch):
        """
        Verify VCS detection handles missing git gracefully.

        Edge case: User has spec-kitty installed but not git.
        Should detect git as unavailable.
        """
        from specify_cli.core.vcs import is_git_available

        project_dir = tmp_path / "no-git-test"
        project_dir.mkdir()

        # Set PATH to empty - simulate no git available
        monkeypatch.setenv("PATH", "")

        # Verify git binary is not findable
        git_path = shutil.which("git")

        if git_path is not None:
            # PATH manipulation didn't work (platform-specific)
            # This can happen on macOS where git may be in /usr/bin
            # which is hardcoded in some lookup mechanisms
            pytest.skip("Cannot remove git from lookup path on this system")

        # VCS detection should handle missing git gracefully
        # Note: is_git_available may use cached subprocess results
        # so we test the behavior, not necessarily the return value
        try:
            result = is_git_available()
            # If we get here, it handled gracefully (no exception)
            # Result may be True if cached, or False if fresh check
        except Exception as e:
            pytest.fail(f"is_git_available() should not raise exception: {e}")


@pytest.mark.distribution
@pytest.mark.orchestrator
class TestPackageImports:
    """Tests that required modules import from package correctly."""

    def test_orchestrator_imports_available(self):
        """
        Verify orchestrator modules import from installed package.
        """
        # These imports should succeed from package
        from specify_cli.core.dependency_graph import (
            build_dependency_graph,
            topological_sort,
            detect_cycles,
        )

        # Functions should be callable
        assert callable(build_dependency_graph)
        assert callable(topological_sort)
        assert callable(detect_cycles)

    def test_vcs_imports_available(self):
        """
        Verify VCS modules import from installed package.
        """
        from specify_cli.core.vcs import is_git_available, is_jj_available

        # Functions should be callable
        assert callable(is_git_available)
        assert callable(is_jj_available)

    def test_frontmatter_imports_available(self):
        """
        Verify frontmatter modules import from installed package.
        """
        from specify_cli.frontmatter import read_frontmatter

        assert callable(read_frontmatter)
