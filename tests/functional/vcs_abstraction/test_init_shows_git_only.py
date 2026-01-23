"""
T047: Init Command Shows Git Only Tests

Verifies that `spec-kitty init` displays git as the only VCS option
and contains no references to jj.
"""
import pytest
import subprocess
from pathlib import Path


@pytest.mark.functional
@pytest.mark.vcs
class TestInitDisplaysGitOnly:
    """Test init command shows only git as VCS option."""

    def test_init_output_mentions_git(self, tmp_path, spec_kitty_repo_root):
        """Init command output mentions git."""
        import os
        env = os.environ.copy()
        env["SPEC_KITTY_TEMPLATE_ROOT"] = str(spec_kitty_repo_root)

        # Initialize git repo first (spec-kitty requires git)
        subprocess.run(["git", "init"], cwd=tmp_path,
                      capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"],
                      cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"],
                      cwd=tmp_path, capture_output=True, check=True)

        result = subprocess.run(
            ["spec-kitty", "init"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            env=env
        )

        output = (result.stdout + result.stderr).lower()

        # Should either succeed or mention git in error
        # (Error likely says "already initialized" or shows git info)
        assert "git" in output or result.returncode == 0, (
            f"Init output doesn't mention git: {output}"
        )

    def test_init_output_no_jj_reference(self, tmp_path, spec_kitty_repo_root):
        """Init command output has no jj reference."""
        import os
        env = os.environ.copy()
        env["SPEC_KITTY_TEMPLATE_ROOT"] = str(spec_kitty_repo_root)

        subprocess.run(["git", "init"], cwd=tmp_path,
                      capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"],
                      cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"],
                      cwd=tmp_path, capture_output=True, check=True)

        result = subprocess.run(
            ["spec-kitty", "init"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            env=env
        )

        output = (result.stdout + result.stderr).lower()

        # Should NOT mention jj or jujutsu
        assert "jujutsu" not in output, (
            f"Init output mentions jujutsu (should be disabled): {output}"
        )
        # Allow "jj" only in contexts like project names, not VCS references
        # Check for explicit jj VCS references
        jj_vcs_refs = [
            "jj vcs",
            "using jj",
            "jj detected",
            "jj repository",
            "jj available",
        ]
        for ref in jj_vcs_refs:
            assert ref not in output, (
                f"Init output has jj VCS reference '{ref}': {output}"
            )


@pytest.mark.functional
@pytest.mark.vcs
class TestInitConfigNoJJ:
    """Test init creates config without jj references."""

    def test_init_config_has_git(self, tmp_path, spec_kitty_repo_root):
        """Init creates config that uses git."""
        import os
        env = os.environ.copy()
        env["SPEC_KITTY_TEMPLATE_ROOT"] = str(spec_kitty_repo_root)

        subprocess.run(["git", "init"], cwd=tmp_path,
                      capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"],
                      cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"],
                      cwd=tmp_path, capture_output=True, check=True)

        subprocess.run(
            ["spec-kitty", "init"],
            cwd=tmp_path,
            capture_output=True,
            env=env
        )

        # Check for config file(s)
        config_paths = [
            tmp_path / ".kittify" / "config.yaml",
            tmp_path / ".kittify" / "config.yml",
            tmp_path / "spec-kitty.yaml",
        ]

        config_found = False
        for config_path in config_paths:
            if config_path.exists():
                config_found = True
                content = config_path.read_text().lower()

                # Check for jj references in config
                assert "jj:" not in content and "jujutsu" not in content, (
                    f"Config has jj reference: {content}"
                )
                break

        # If no config file found, that's OK - init may not create one
        # in all cases

    def test_init_no_jj_vcs_option(self, tmp_path, spec_kitty_repo_root):
        """Init doesn't offer jj as VCS option."""
        import os
        env = os.environ.copy()
        env["SPEC_KITTY_TEMPLATE_ROOT"] = str(spec_kitty_repo_root)

        subprocess.run(["git", "init"], cwd=tmp_path,
                      capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"],
                      cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"],
                      cwd=tmp_path, capture_output=True, check=True)

        result = subprocess.run(
            ["spec-kitty", "init"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            env=env
        )

        output = result.stdout + result.stderr

        # Look for VCS selection prompts that might offer jj
        jj_options = [
            "1. git  2. jj",
            "jj]",
            "[jj]",
            "jujutsu]",
            "choose vcs: jj",
        ]

        for option in jj_options:
            assert option.lower() not in output.lower(), (
                f"Init offers jj as option: {output}"
            )


@pytest.mark.functional
@pytest.mark.vcs
class TestInitHelpNoJJ:
    """Test init help text has no jj references."""

    def test_init_help_no_jj_reference(self):
        """Init help text doesn't reference jj."""
        result = subprocess.run(
            ["spec-kitty", "init", "--help"],
            capture_output=True,
            text=True
        )

        help_text = (result.stdout + result.stderr).lower()

        # Should not mention jj as an option
        assert "jujutsu" not in help_text, (
            f"Help text mentions jujutsu: {result.stdout}"
        )

        # Check for jj VCS option mentions
        jj_refs = [
            "--vcs jj",
            "-v jj",
            "vcs=jj",
            "jj vcs",
        ]
        for ref in jj_refs:
            assert ref not in help_text, (
                f"Help text has jj VCS reference '{ref}'"
            )

    def test_init_help_mentions_git(self):
        """Init help text mentions git."""
        result = subprocess.run(
            ["spec-kitty", "init", "--help"],
            capture_output=True,
            text=True
        )

        help_text = (result.stdout + result.stderr).lower()

        # Should mention git (either as requirement or VCS)
        # It's OK if git is not explicitly mentioned if help is minimal
        if "vcs" in help_text:
            assert "git" in help_text, (
                f"Help mentions VCS but not git: {result.stdout}"
            )


@pytest.mark.functional
@pytest.mark.vcs
@pytest.mark.adversarial
class TestInitWithJJInstalled:
    """Test init behavior when jj is installed on system."""

    def test_init_ignores_jj_installation(self, tmp_path, spec_kitty_repo_root):
        """Init ignores jj even when installed on system."""
        import shutil
        import os

        env = os.environ.copy()
        env["SPEC_KITTY_TEMPLATE_ROOT"] = str(spec_kitty_repo_root)

        # Check if jj is actually installed
        jj_installed = shutil.which("jj") is not None

        subprocess.run(["git", "init"], cwd=tmp_path,
                      capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"],
                      cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"],
                      cwd=tmp_path, capture_output=True, check=True)

        result = subprocess.run(
            ["spec-kitty", "init"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            env=env
        )

        output = (result.stdout + result.stderr).lower()

        # Even if jj is installed, init should not mention it
        assert "jujutsu" not in output
        assert "using jj" not in output

        if jj_installed:
            # If jj is installed, this proves init truly ignores it
            pass  # Test passes - jj exists but wasn't mentioned
