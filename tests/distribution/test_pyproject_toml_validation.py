"""
Test: Validate pyproject.toml Package Configuration

Purpose: Ensure pyproject.toml correctly specifies what gets bundled in the package.

THE BUG THAT WAS MISSED:
Line 72 of pyproject.toml had:
  "templates" = "specify_cli/templates"

Should have been:
  ".kittify/templates" = "specify_cli/templates"

This test would have caught it BEFORE any release.

Test Coverage:
1. Package-data configuration points to correct directory
2. Bundled directory exists and contains templates
3. Bundled directory has correct content (Python CLI, not bash/PS1)
4. Template directory consistency across sources

Related Issues: #62, #63, #64
Related Finding: 2026-01-06_01_wrong_template_bundling_issues_62_63_64.md
"""

import re
import tomli
from pathlib import Path

import pytest


class TestPyprojectTomlPackageData:
    """Validate [tool.setuptools.package-data] section."""

    def test_pyproject_toml_exists(self, spec_kitty_repo_root):
        """Basic: pyproject.toml must exist"""
        pyproject_file = spec_kitty_repo_root / 'pyproject.toml'
        assert pyproject_file.exists(), "pyproject.toml must exist in repository root"

    def test_package_data_points_to_kittify_templates(self, spec_kitty_repo_root):
        """
        CRITICAL: Package-data must bundle .kittify/templates/, not templates/

        This is the ROOT CAUSE of Issues #62, #63, #64.
        """
        pyproject_file = spec_kitty_repo_root / 'pyproject.toml'
        content = pyproject_file.read_text(encoding='utf-8')

        # Parse TOML
        with open(pyproject_file, 'rb') as f:
            pyproject = tomli.load(f)

        # Get package-data section
        try:
            package_data = pyproject['tool']['setuptools']['package-data']
        except KeyError:
            pytest.fail(
                "pyproject.toml must have [tool.setuptools.package-data] section\n"
                "This section specifies what files get bundled in the package"
            )

        # Check if it points to correct directory
        # Should have entry for .kittify/templates or specify_cli with .kittify/templates
        bundled_templates = None

        # Check all package-data entries
        for package, patterns in package_data.items():
            if isinstance(patterns, list):
                for pattern in patterns:
                    if '.kittify/templates' in pattern or 'kittify/templates' in pattern:
                        bundled_templates = pattern
                        break
            elif isinstance(patterns, str):
                if '.kittify/templates' in patterns or 'kittify/templates' in patterns:
                    bundled_templates = patterns

        # Also check string representation for simple cases
        package_data_str = str(package_data)

        # CRITICAL CHECK: Should have .kittify/templates
        assert '.kittify/templates' in package_data_str or 'kittify/templates' in package_data_str, (
            "CRITICAL BUG: pyproject.toml does not bundle .kittify/templates/!\n\n"
            f"Current package-data:\n{package_data}\n\n"
            "Must include entry for .kittify/templates/ directory.\n"
            "This is the bug from Issues #62, #63, #64!"
        )

        # ANTI-PATTERN CHECK: Should NOT have 'templates' without '.kittify' prefix
        # Look for pattern like: "templates" = "specify_cli/templates"
        wrong_pattern = re.search(r'"templates"\s*=\s*"specify_cli/templates"', content)

        assert not wrong_pattern, (
            f"CRITICAL BUG: pyproject.toml has WRONG template bundling!\n\n"
            f"Found at line ~{content[:wrong_pattern.start()].count(chr(10)) + 1}:\n"
            f'  "templates" = "specify_cli/templates"\n\n'
            "Should be:\n"
            '  ".kittify/templates" = "specify_cli/templates"\n\n'
            "This bundles /templates/ (outdated) instead of /.kittify/templates/ (correct)"
        )

    def test_bundled_template_directory_exists(self, spec_kitty_repo_root):
        """
        CRITICAL: The directory specified in package-data must actually exist
        """
        # Should exist: .kittify/templates/
        kittify_templates = spec_kitty_repo_root / '.kittify' / 'templates'

        assert kittify_templates.exists(), (
            f".kittify/templates/ directory must exist\n"
            f"Expected: {kittify_templates}\n"
            "This is the directory that should be bundled in the package"
        )

        assert kittify_templates.is_dir(), (
            f".kittify/templates/ must be a directory, not a file or symlink\n"
            f"Path: {kittify_templates}"
        )

    def test_bundled_directory_has_command_templates(self, spec_kitty_repo_root):
        """
        VALIDATION: Bundled directory must contain command templates
        """
        kittify_templates = spec_kitty_repo_root / '.kittify' / 'templates'
        command_templates_dir = kittify_templates / 'command-templates'

        assert command_templates_dir.exists(), (
            f"Command templates directory must exist in bundled location\n"
            f"Expected: {command_templates_dir}"
        )

        # Must have template files
        templates = list(command_templates_dir.glob('*.md'))

        assert len(templates) >= 10, (
            f"Should have at least 10 command templates in bundled directory\n"
            f"Found: {len(templates)} templates in {command_templates_dir}"
        )

    def test_wrong_templates_directory_should_not_exist_or_be_removed(self, spec_kitty_repo_root):
        """
        CLEANUP CHECK: Old /templates/ directory should not exist

        After fixing the bug, /templates/ should be:
        - Removed entirely (recommended), OR
        - Synced with .kittify/templates/ (if kept for compatibility)
        """
        templates_dir = spec_kitty_repo_root / 'templates'

        if not templates_dir.exists():
            # Good! Old directory was removed
            pytest.skip("templates/ directory removed - this is the correct fix")
            return

        # If it exists, warn that it should probably be removed
        print("\nWARNING: /templates/ directory still exists")
        print("Recommendation: Remove this directory or keep it synced with /.kittify/templates/")
        print(f"Path: {templates_dir}")


class TestBundledTemplateContent:
    """Validate content of templates that will be bundled in package."""

    def test_bundled_templates_use_python_cli_not_scripts(self, spec_kitty_repo_root):
        """
        CRITICAL: Bundled templates must use Python CLI commands, not bash/PowerShell

        This is what users get when they install from PyPI.
        """
        kittify_templates = spec_kitty_repo_root / '.kittify' / 'templates' / 'command-templates'

        if not kittify_templates.exists():
            pytest.fail(
                f"Cannot validate bundled templates - directory doesn't exist:\n"
                f"{kittify_templates}"
            )

        templates_with_cli = []
        templates_with_scripts = []

        for template in kittify_templates.glob('*.md'):
            content = template.read_text(encoding='utf-8')

            # Check for Python CLI usage
            if re.search(r'spec-kitty\s+(?:agent|task|worktree|dashboard)', content):
                templates_with_cli.append(template.name)

            # Check for script references (anti-pattern)
            if re.search(r'[\w\-\.]+\.(sh|ps1)', content):
                templates_with_scripts.append({
                    'file': template.name,
                    'content_preview': content[:200]
                })

        # Should have Python CLI commands
        assert len(templates_with_cli) > 0, (
            f"Bundled templates should use Python CLI commands\n"
            f"Checked: {kittify_templates}\n"
            f"Found 0 templates with 'spec-kitty agent/task' commands"
        )

        # Should NOT have script references
        if templates_with_scripts:
            pytest.fail(
                f"CRITICAL: Bundled templates contain script references!\n\n"
                f"Found {len(templates_with_scripts)} template(s) with .sh/.ps1 references:\n" +
                "\n".join([
                    f"  - {t['file']}: {t['content_preview'][:100]}..."
                    for t in templates_with_scripts
                ]) +
                "\n\nBundled templates must use Python CLI commands, not scripts!"
            )

    def test_no_bash_script_references_in_bundled_templates(self, spec_kitty_repo_root):
        """
        Issue #62, #64: Bundled templates must NOT reference .sh files
        """
        kittify_templates = spec_kitty_repo_root / '.kittify' / 'templates' / 'command-templates'

        bash_refs = []

        for template in kittify_templates.glob('*.md'):
            content = template.read_text(encoding='utf-8')
            sh_matches = re.findall(r'[\w\-\.]+\.sh', content)

            if sh_matches:
                bash_refs.append({
                    'file': template.name,
                    'references': sh_matches
                })

        if bash_refs:
            error_msg = "Bundled templates contain bash script references:\n"
            for ref in bash_refs:
                error_msg += f"  {ref['file']}: {', '.join(set(ref['references']))}\n"
            error_msg += "\nUsers will get these templates and commands will fail!"

            pytest.fail(error_msg)

    def test_no_powershell_script_references_in_bundled_templates(self, spec_kitty_repo_root):
        """
        Issue #63: Bundled templates must NOT reference .ps1 files
        """
        kittify_templates = spec_kitty_repo_root / '.kittify' / 'templates' / 'command-templates'

        ps1_refs = []

        for template in kittify_templates.glob('*.md'):
            content = template.read_text(encoding='utf-8')
            ps1_matches = re.findall(r'[\w\-\.]+\.ps1', content)

            if ps1_matches:
                ps1_refs.append({
                    'file': template.name,
                    'references': ps1_matches
                })

        if ps1_refs:
            error_msg = "Bundled templates contain PowerShell script references:\n"
            for ref in ps1_refs:
                error_msg += f"  {ref['file']}: {', '.join(set(ref['references']))}\n"
            error_msg += "\nThis is Issue #63 - users get broken templates!"

            pytest.fail(error_msg)


class TestTemplateDirectoryConsistency:
    """Ensure no divergence between template sources."""

    def test_no_template_directory_divergence(self, spec_kitty_repo_root):
        """
        Issue #64: Three divergent template sources

        If /templates/ exists, it must be identical to /.kittify/templates/
        Otherwise, remove it entirely.
        """
        templates_dir = spec_kitty_repo_root / 'templates' / 'command-templates'
        kittify_dir = spec_kitty_repo_root / '.kittify' / 'templates' / 'command-templates'

        if not templates_dir.exists():
            pytest.skip("/templates/ removed - no divergence possible")
            return

        # Both exist - they must be identical
        templates_files = {}
        kittify_files = {}

        for f in templates_dir.glob('*.md'):
            templates_files[f.name] = f.read_text(encoding='utf-8')

        for f in kittify_dir.glob('*.md'):
            kittify_files[f.name] = f.read_text(encoding='utf-8')

        # Check for missing files
        only_in_templates = set(templates_files.keys()) - set(kittify_files.keys())
        only_in_kittify = set(kittify_files.keys()) - set(templates_files.keys())

        if only_in_templates:
            pytest.fail(
                f"Files in /templates/ but not in /.kittify/templates/:\n" +
                "\n".join([f"  - {f}" for f in only_in_templates])
            )

        if only_in_kittify:
            pytest.fail(
                f"Files in /.kittify/templates/ but not in /templates/:\n" +
                "\n".join([f"  - {f}" for f in only_in_kittify])
            )

        # Check for content differences
        diverged_files = []
        for filename in templates_files.keys():
            if filename in kittify_files:
                if templates_files[filename] != kittify_files[filename]:
                    diverged_files.append(filename)

        if diverged_files:
            pytest.fail(
                f"Template directories have diverged!\n"
                f"{len(diverged_files)} file(s) differ between /templates/ and /.kittify/templates/:\n" +
                "\n".join([f"  - {f}" for f in diverged_files]) +
                "\n\nEither sync them or remove /templates/ entirely"
            )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
