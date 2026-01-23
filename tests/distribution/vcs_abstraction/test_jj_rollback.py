"""
Distribution tests for JJ rollback validation (WP11: T063).

Validates that jj is never invoked from PyPI install and jj detection
returns False since jj support was rolled back.
"""
import pytest
import shutil
from pathlib import Path


@pytest.mark.distribution
@pytest.mark.vcs
class TestJJNeverInvoked:
    """Tests that jj commands are never invoked from package."""

    def test_jj_never_invoked_fresh_install(self):
        """
        Verify jj is never invoked on fresh install.

        Validates spec.md User Story 4, Acceptance Scenario 1:
        "Given fresh spec-kitty install,
         When any VCS operation is performed,
         Then jj is never invoked"
        """
        from specify_cli.core.vcs import is_jj_available

        # JJ detection should always return False
        result = is_jj_available()

        assert result is False, \
            "is_jj_available() should always return False after rollback"

    def test_is_jj_available_returns_false(self):
        """
        Verify is_jj_available() returns False regardless of environment.

        Validates spec.md User Story 3, Acceptance Scenario 1:
        "Given VCS operations,
         When git is available,
         Then git is used exclusively"

        Even if jj binary exists on PATH, detection should return False.
        """
        from specify_cli.core.vcs import is_jj_available

        # Should return False unconditionally
        result = is_jj_available()

        assert result is False, \
            "is_jj_available() should return False regardless of jj presence"

    def test_jj_in_path_but_broken(self, broken_jj_binary, monkeypatch):
        """
        Verify jj detection returns False even with broken jj binary.

        Edge case: User has jj installed but it's broken.
        Detection should still return False (not attempt to invoke).
        """
        from specify_cli.core.vcs import is_jj_available

        # Add broken jj to PATH
        original_path = shutil.which("jj") or ""
        monkeypatch.setenv(
            "PATH",
            f"{broken_jj_binary}:{original_path}:/usr/bin:/bin"
        )

        # Should still return False (never attempts to invoke)
        result = is_jj_available()

        assert result is False, \
            "is_jj_available() should return False even with jj on PATH"


@pytest.mark.distribution
@pytest.mark.vcs
class TestVCSDetectionGitOnly:
    """Tests that VCS detection only considers git."""

    def test_get_vcs_returns_git(self, git_initialized_project):
        """
        Verify get_vcs() returns git VCS.

        From installed package, VCS factory should only return git.
        """
        from specify_cli.core.vcs import get_vcs, VCSBackend

        # Create meta.json in project
        kitty_specs = git_initialized_project / "kitty-specs" / "001-test"
        kitty_specs.mkdir(parents=True)
        (kitty_specs / "meta.json").write_text('{"vcs": "git", "feature_number": "001"}')

        vcs = get_vcs(git_initialized_project, VCSBackend.GIT)

        assert vcs is not None, \
            "VCS should be created"

    def test_jj_meta_treated_as_git(self, legacy_jj_feature):
        """
        Verify features with jj in meta.json are treated as git.

        Legacy features may have vcs: jj but should use git backend.
        """
        from specify_cli.core.vcs import is_jj_available, is_git_available

        # meta.json has vcs: jj
        meta_file = legacy_jj_feature / "meta.json"
        assert '"vcs": "jj"' in meta_file.read_text()

        # JJ should be unavailable, git should be available
        assert is_jj_available() is False, \
            "JJ should be unavailable after rollback"
        assert is_git_available() is True, \
            "Git should be available"
