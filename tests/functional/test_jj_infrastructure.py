"""
Test infrastructure verification for jj (jujutsu) VCS integration tests.

These tests verify that WP01 fixtures and markers are working correctly.
"""
import os
import pytest


class TestJJMarkerRegistration:
    """Verify @pytest.mark.jj marker is properly registered (T001)."""

    @pytest.mark.jj
    def test_jj_marker_can_be_applied(self, jj_available):
        """Verify jj marker can be applied without warnings.

        If this test runs without "unknown marker" warnings, the marker is registered.
        The test itself will be skipped if jj is not available (proving auto-skip works).
        """
        # If we get here, both marker registration and auto-skip are working
        assert jj_available is True


class TestJJAvailableFixture:
    """Verify jj_available fixture works correctly (T002)."""

    def test_jj_available_returns_bool(self, jj_available):
        """jj_available fixture should return True or False."""
        assert isinstance(jj_available, bool)

    def test_jj_version_returns_string_or_none(self, jj_version):
        """jj_version fixture should return version string or None."""
        assert jj_version is None or isinstance(jj_version, str)


class TestJJAutoSkip:
    """Verify auto-skip behavior for @pytest.mark.jj tests (T003)."""

    @pytest.mark.jj
    def test_marked_with_jj(self, jj_available):
        """This test should auto-skip if jj not installed."""
        # If we get here, jj is available (otherwise test would be skipped)
        assert jj_available is True


class TestDistributionMarker:
    """Verify @pytest.mark.distribution marker works (T004)."""

    @pytest.mark.distribution
    def test_distribution_marker_registered(self):
        """Verify distribution marker can be applied without warnings."""
        pass


class TestSpecKittyProjectFixture:
    """Verify spec_kitty_project fixture works (T005)."""

    def test_creates_directory(self, spec_kitty_project):
        """spec_kitty_project fixture should create a valid directory."""
        assert spec_kitty_project.exists()
        assert spec_kitty_project.is_dir()

    def test_git_initialized(self, spec_kitty_project):
        """spec_kitty_project should have git initialized."""
        git_dir = spec_kitty_project / ".git"
        assert git_dir.exists() or git_dir.is_dir()

    def test_spec_kitty_initialized(self, spec_kitty_project):
        """spec_kitty_project should have spec-kitty initialized."""
        # Check for .kittify directory (spec-kitty project marker)
        kittify_dir = spec_kitty_project / ".kittify"
        assert kittify_dir.exists(), f"Expected .kittify directory in {spec_kitty_project}"


class TestNoTemplateBypassFixture:
    """Verify no_template_bypass fixture works (T006)."""

    def test_removes_template_root(self, no_template_bypass):
        """no_template_bypass should remove SPEC_KITTY_TEMPLATE_ROOT."""
        assert "SPEC_KITTY_TEMPLATE_ROOT" not in os.environ

    def test_removes_spec_kitty_repo(self, no_template_bypass):
        """no_template_bypass should remove SPEC_KITTY_REPO."""
        assert "SPEC_KITTY_REPO" not in os.environ


class TestVersionGating:
    """Verify requires_spec_kitty_version utilities work (T054)."""

    def test_spec_kitty_version_fixture(self, spec_kitty_version):
        """spec_kitty_version fixture should return a tuple."""
        assert isinstance(spec_kitty_version, tuple)
        assert len(spec_kitty_version) == 3
        assert all(isinstance(v, int) for v in spec_kitty_version)

    def test_requires_v011_on_011_plus(self, requires_v011):
        """If we're on v0.11.0+, requires_v011 should not skip."""
        # If we get here, the version is sufficient
        pass
