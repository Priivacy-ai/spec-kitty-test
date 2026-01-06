"""
Validate package bundling includes correct templates.

THIS IS THE CRITICAL TEST THAT WAS MISSING!

This test validates the actual package that gets shipped to PyPI users.
It would have caught Issues #62, #63, #64 before any release.

Test Coverage (Per Remediation Plan Phase 4):
1. test_sdist_bundles_kittify_templates() - Verify source distribution
2. test_no_bash_script_references_in_bundled_templates() - Verify content
3. test_wheel_bundles_templates_correctly() - Verify wheel packaging

Related:
- Issues: #62, #63, #64
- Remediation Plan: Phase 4 - Add Package Bundling Validation Test
- Finding: 2026-01-06_01_wrong_template_bundling_issues_62_63_64.md
"""

from pathlib import Path
import subprocess
import tempfile
import tarfile
import zipfile

import pytest


class TestSourceDistributionBundling:
    """Validate sdist (source distribution) bundles correct templates."""

    @pytest.fixture
    def spec_kitty_repo_root(self):
        """Get spec-kitty repository root."""
        # This should point to actual spec-kitty repo
        env_path = Path(__file__).parent.parent.parent / "spec-kitty"
        if not env_path.exists():
            pytest.skip("spec-kitty repository not found")
        return env_path

    def test_sdist_bundles_kittify_templates(self, spec_kitty_repo_root):
        """
        CRITICAL: Verify source distribution includes .kittify/templates/ not /templates/.

        This is the ROOT CAUSE test - validates pyproject.toml line 72 is correct.
        """
        # Build sdist
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                ["python", "-m", "build", "--sdist", "--outdir", tmpdir],
                cwd=spec_kitty_repo_root,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode != 0:
                pytest.skip(f"Build failed (may need dependencies): {result.stderr}")

            # Find the tarball
            dist_dir = Path(tmpdir)
            tarballs = list(dist_dir.glob("spec-kitty-cli-*.tar.gz"))

            if not tarballs:
                pytest.fail(
                    f"No sdist tarball found in {dist_dir}\n"
                    f"Build output: {result.stdout}\n"
                    f"Build errors: {result.stderr}"
                )

            latest = max(tarballs, key=lambda p: p.stat().st_mtime)

            # Extract and check contents
            with tarfile.open(latest, "r:gz") as tar:
                members = tar.getnames()

                # Should have .kittify/templates/
                kittify_templates = [m for m in members if ".kittify/templates/" in m]

                assert len(kittify_templates) > 0, (
                    "CRITICAL BUG: .kittify/templates/ not found in sdist!\n\n"
                    f"Checked {len(members)} files in {latest.name}\n"
                    "This means pyproject.toml line 80 is still wrong.\n\n"
                    "Should include: .kittify/templates/**/*"
                )

                # Should NOT have old /templates/ directory
                old_templates = [
                    m for m in members
                    if "/templates/" in m and ".kittify" not in m
                ]

                if old_templates:
                    pytest.fail(
                        f"CRITICAL BUG: Old /templates/ found in sdist!\n\n"
                        f"Found {len(old_templates)} files from outdated directory:\n" +
                        "\n".join([f"  - {t}" for t in old_templates[:10]]) +
                        ("\n  ..." if len(old_templates) > 10 else "") +
                        "\n\nThis means pyproject.toml line 80 still references /templates/\n"
                        "Remove old templates line from [tool.setuptools.sdist] includes"
                    )

                # Should have command templates
                cmd_templates = [
                    m for m in members
                    if "command-templates" in m and m.endswith(".md")
                ]

                assert len(cmd_templates) >= 13, (
                    f"Missing command templates in sdist!\n"
                    f"Expected: >=13 templates\n"
                    f"Found: {len(cmd_templates)}\n\n"
                    "Template files found:\n" +
                    "\n".join([f"  - {t}" for t in cmd_templates])
                )

                # Should have git hooks (Issue #64 - outdated dir had only 1, correct has 3)
                git_hooks = [m for m in members if "git-hooks/pre-commit" in m]

                assert len(git_hooks) >= 2, (
                    f"Missing git hooks in sdist!\n"
                    f"Expected: >=2 hooks (pre-commit, pre-commit-agent-check, pre-commit-encoding-check)\n"
                    f"Found: {len(git_hooks)}\n\n"
                    "This was one of the divergences - outdated /templates/ only had 1 hook"
                )

    def test_pyproject_includes_correct_files(self, spec_kitty_repo_root):
        """
        Validate pyproject.toml [tool.setuptools.sdist] includes section.

        Should include .kittify/templates, not templates.
        """
        pyproject = spec_kitty_repo_root / "pyproject.toml"

        if not pyproject.exists():
            pytest.skip("pyproject.toml not found")

        content = pyproject.read_text(encoding="utf-8")

        # Check sdist includes section
        if "[tool.setuptools.sdist]" in content:
            # Extract includes section
            sdist_section = content.split("[tool.setuptools.sdist]")[1]
            sdist_section = sdist_section.split("[")[0]  # Until next section

            # Should have .kittify/templates
            assert ".kittify/templates" in sdist_section, (
                "pyproject.toml [tool.setuptools.sdist] should include .kittify/templates/**/*"
            )

            # Should NOT have old templates reference
            if '"templates/**/*"' in sdist_section or "'templates/**/*'" in sdist_section:
                pytest.fail(
                    "CRITICAL: pyproject.toml [tool.setuptools.sdist] still includes old templates/!\n"
                    "Change line ~80 from:\n"
                    '  "templates/**/*",\n'
                    "To:\n"
                    '  ".kittify/templates/**/*",'
                )


class TestBundledTemplateContent:
    """Validate content of templates that will be bundled."""

    @pytest.fixture
    def spec_kitty_repo_root(self):
        """Get spec-kitty repository root."""
        env_path = Path(__file__).parent.parent.parent / "spec-kitty"
        if not env_path.exists():
            pytest.skip("spec-kitty repository not found")
        return env_path

    def test_no_bash_script_references_in_bundled_templates(self, spec_kitty_repo_root):
        """
        CRITICAL: Ensure bundled templates don't reference deleted bash scripts.

        This test scans .kittify/templates/ (what SHOULD be bundled) for script refs.
        """
        templates_dir = spec_kitty_repo_root / ".kittify" / "templates" / "command-templates"

        if not templates_dir.exists():
            pytest.fail(
                f"Template directory not found: {templates_dir}\n"
                "This is the directory that should be bundled per pyproject.toml line 72"
            )

        bash_references = []
        ps1_references = []

        for template in templates_dir.glob("*.md"):
            content = template.read_text(encoding="utf-8")

            # Check for bash script references
            if "scripts/bash/" in content or ".kittify/scripts/bash/" in content:
                # Extract actual references
                import re
                bash_refs = re.findall(r'[\w\-/\.]+scripts/bash/[\w\-/\.]+', content)
                if bash_refs:
                    bash_references.append({
                        'file': template.name,
                        'refs': bash_refs
                    })

            # Check for PowerShell script references
            if "scripts/powershell/" in content or ".kittify/scripts/powershell/" in content:
                import re
                ps1_refs = re.findall(r'[\w\-/\.]+scripts/powershell/[\w\-/\.]+', content)
                if ps1_refs:
                    ps1_references.append({
                        'file': template.name,
                        'refs': ps1_refs
                    })

        errors = []

        if bash_references:
            error_msg = (
                f"CRITICAL: Bash script references found in {len(bash_references)} template(s):\n"
            )
            for ref in bash_references:
                error_msg += f"\n  {ref['file']}:\n"
                for r in ref['refs']:
                    error_msg += f"    - {r}\n"
            error_msg += (
                "\nThese scripts were removed in v0.10.0!\n"
                "Templates must use Python CLI commands like 'spec-kitty agent create-feature'"
            )
            errors.append(error_msg)

        if ps1_references:
            error_msg = (
                f"CRITICAL: PowerShell script references found in {len(ps1_references)} template(s):\n"
            )
            for ref in ps1_references:
                error_msg += f"\n  {ref['file']}:\n"
                for r in ref['refs']:
                    error_msg += f"    - {r}\n"
            error_msg += (
                "\nThese scripts were removed in v0.10.0!\n"
                "Templates must use Python CLI commands"
            )
            errors.append(error_msg)

        if errors:
            pytest.fail("\n\n".join(errors))


class TestWheelBundling:
    """Validate wheel bundles templates correctly for importlib.resources."""

    @pytest.fixture
    def spec_kitty_repo_root(self):
        """Get spec-kitty repository root."""
        env_path = Path(__file__).parent.parent.parent / "spec-kitty"
        if not env_path.exists():
            pytest.skip("spec-kitty repository not found")
        return env_path

    @pytest.mark.slow
    def test_wheel_bundles_templates_correctly(self, spec_kitty_repo_root):
        """
        Verify wheel includes templates at correct path for importlib.resources.

        This is a SLOW test - creates venv, builds wheel, installs, validates.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Build wheel
            result = subprocess.run(
                ["python", "-m", "build", "--wheel", "--outdir", str(tmpdir)],
                cwd=spec_kitty_repo_root,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode != 0:
                pytest.skip(f"Wheel build failed: {result.stderr}")

            # Find wheel
            wheels = list(tmpdir.glob("spec_kitty_cli-*.whl"))
            if not wheels:
                pytest.fail("No wheel found after build")

            wheel_path = wheels[0]

            # Inspect wheel contents
            with zipfile.ZipFile(wheel_path, 'r') as whl:
                names = whl.namelist()

                # Should have templates under specify_cli/
                template_files = [n for n in names if "templates/" in n and ".md" in n]

                assert len(template_files) >= 13, (
                    f"Wheel should contain >=13 template files\n"
                    f"Found: {len(template_files)}\n\n"
                    "Wheel contents (template-related):\n" +
                    "\n".join([f"  - {t}" for t in template_files[:20]])
                )

                # Should have command-templates
                cmd_templates = [n for n in names if "command-templates/" in n]

                assert len(cmd_templates) > 0, (
                    "Wheel should contain command-templates/ directory"
                )

                # Should have git-hooks
                git_hooks = [n for n in names if "git-hooks/" in n]

                assert len(git_hooks) >= 3, (
                    f"Wheel should contain >=3 git hooks\n"
                    f"Found: {len(git_hooks)}"
                )

    @pytest.mark.slow
    @pytest.mark.integration
    def test_wheel_install_and_importlib_access(self, spec_kitty_repo_root):
        """
        Full integration: Build wheel, install in venv, verify importlib.resources access.

        This is the most comprehensive test - actually installs and validates.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Build wheel
            build_result = subprocess.run(
                ["python", "-m", "build", "--wheel", "--outdir", str(tmpdir)],
                cwd=spec_kitty_repo_root,
                capture_output=True,
                text=True,
                timeout=120
            )

            if build_result.returncode != 0:
                pytest.skip(f"Build failed: {build_result.stderr}")

            wheel_path = list(tmpdir.glob("spec_kitty_cli-*.whl"))[0]

            # Create venv
            venv_dir = tmpdir / "venv"
            subprocess.run(
                ["python", "-m", "venv", str(venv_dir)],
                check=True,
                timeout=60
            )

            # Install wheel
            pip = venv_dir / "bin" / "pip"
            install_result = subprocess.run(
                [str(pip), "install", str(wheel_path)],
                capture_output=True,
                text=True,
                timeout=60
            )

            if install_result.returncode != 0:
                pytest.skip(f"Install failed: {install_result.stderr}")

            # Verify importlib.resources access
            python = venv_dir / "bin" / "python"

            # Test 1: Can access templates via importlib
            result = subprocess.run(
                [
                    str(python), "-c",
                    "from importlib.resources import files; "
                    "t = files('specify_cli').joinpath('templates'); "
                    "print(list(t.iterdir()))"
                ],
                capture_output=True,
                text=True,
                timeout=10
            )

            assert result.returncode == 0, (
                f"Failed to access templates via importlib.resources\n"
                f"Error: {result.stderr}"
            )

            output = result.stdout.lower()

            assert "command-templates" in output, (
                "command-templates not accessible via importlib.resources\n"
                f"Available: {result.stdout}"
            )

            assert "git-hooks" in output, (
                "git-hooks not accessible via importlib.resources\n"
                f"Available: {result.stdout}"
            )

            # Test 2: Can list command templates
            result = subprocess.run(
                [
                    str(python), "-c",
                    "from importlib.resources import files; "
                    "templates = files('specify_cli').joinpath('templates/command-templates'); "
                    "print([f.name for f in templates.iterdir() if f.name.endswith('.md')])"
                ],
                capture_output=True,
                text=True,
                timeout=10
            )

            assert result.returncode == 0
            template_list = result.stdout

            # Should have multiple templates
            assert ".md" in template_list, (
                "No .md template files found\n"
                f"Found: {template_list}"
            )


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
