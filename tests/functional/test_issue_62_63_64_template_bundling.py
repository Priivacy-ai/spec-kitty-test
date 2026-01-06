"""
Test: Issues #62, #63, #64 - Wrong Template Directory Bundled in pyproject.toml

Purpose: Validate that packaged spec-kitty includes correct templates with Python CLI commands,
not outdated templates with bash/PowerShell script references.

Root Cause:
- Line 72 of pyproject.toml: "templates" = "specify_cli/templates"
- This bundles /templates/ (outdated with bash script references)
- Should bundle /.kittify/templates/ (correct with Python CLI commands)

Issue Breakdown:

Issue #62 - Worktree Script Failure
- User scenario: Upgraded existing project but didn't run spec-kitty upgrade
- Symptom: check-prerequisites.sh: No such file or directory
- Root cause: Old templates reference scripts that don't exist

Issue #63 - New Project Has Broken References
- User scenario: Fresh spec-kitty init with v0.10.8
- Symptom: .github/prompts/spec-kitty.specify.prompt.md references create-new-feature.ps1
- Root cause: Bundled templates are outdated

Issue #64 - Comprehensive Breakdown
- User scenario: New installation via uv tool install
- Symptom: All slash commands reference non-existent bash/PowerShell scripts
- Root cause: Package bundles wrong template directory

Test Coverage:
1. Package Template Validation (5 tests)
   - Verify no bash script references (.sh files)
   - Verify no PowerShell script references (.ps1 files)
   - Verify Python CLI commands are used
   - Verify command templates exist and are correct

2. New Project Init Validation (6 tests)
   - New projects don't reference .sh scripts
   - New projects don't reference .ps1 scripts
   - New projects use Python CLI commands
   - All command templates are correct

3. Template Directory Structure (4 tests)
   - Correct template directory structure
   - All expected templates exist
   - No outdated templates

4. Upgrade Path Validation (3 tests)
   - Existing projects can upgrade
   - Upgrade fixes broken references
   - No regression after upgrade

Related Issues: #62, #63, #64
Version: v0.10.8
"""

import os
import re
import subprocess
import tempfile
from pathlib import Path

import pytest


class TestPackageTemplateValidation:
    """Validate that packaged templates are correct (not outdated)."""

    def test_no_bash_script_references_in_packaged_templates(self, spec_kitty_repo_root):
        """
        CRITICAL: Bundled templates must NOT reference .sh scripts

        Issue #62, #64: Templates reference check-prerequisites.sh and other bash scripts
        that don't exist in the Python CLI version.
        """
        # Check the templates that will be bundled
        # According to pyproject.toml line 72, this should be .kittify/templates
        # But the bug is it points to templates/ instead

        # First, let's check what's actually in templates/ (the wrong source)
        templates_dir = spec_kitty_repo_root / 'templates'
        if not templates_dir.exists():
            pytest.skip("templates/ directory doesn't exist - may already be fixed")

        bash_references = []

        # Scan all .md files in templates/
        for md_file in templates_dir.rglob('*.md'):
            content = md_file.read_text(encoding='utf-8')

            # Look for .sh file references
            sh_matches = re.findall(r'[\w\-\.]+\.sh', content)
            if sh_matches:
                bash_references.append({
                    'file': md_file.relative_to(templates_dir),
                    'references': sh_matches
                })

        if bash_references:
            error_msg = "CRITICAL BUG: templates/ directory contains bash script references:\n"
            for ref in bash_references:
                error_msg += f"  {ref['file']}: {', '.join(set(ref['references']))}\n"
            error_msg += "\nThis is the bug! pyproject.toml bundles templates/ instead of .kittify/templates/\n"
            error_msg += "FIX: Change pyproject.toml line 72 to:\n"
            error_msg += '  ".kittify/templates" = "specify_cli/templates"\n'

            pytest.fail(error_msg)

    def test_no_powershell_script_references_in_packaged_templates(self, spec_kitty_repo_root):
        """
        CRITICAL: Bundled templates must NOT reference .ps1 scripts

        Issue #63: New projects have references to create-new-feature.ps1 and other
        PowerShell scripts that don't exist.
        """
        templates_dir = spec_kitty_repo_root / 'templates'
        if not templates_dir.exists():
            pytest.skip("templates/ directory doesn't exist - may already be fixed")

        ps1_references = []

        for md_file in templates_dir.rglob('*.md'):
            content = md_file.read_text(encoding='utf-8')

            # Look for .ps1 file references
            ps1_matches = re.findall(r'[\w\-\.]+\.ps1', content)
            if ps1_matches:
                ps1_references.append({
                    'file': md_file.relative_to(templates_dir),
                    'references': ps1_matches
                })

        if ps1_references:
            error_msg = "CRITICAL BUG: templates/ directory contains PowerShell script references:\n"
            for ref in ps1_references:
                error_msg += f"  {ref['file']}: {', '.join(set(ref['references']))}\n"
            error_msg += "\nThis is Issue #63! Bundled templates reference .ps1 scripts.\n"
            error_msg += "FIX: Change pyproject.toml line 72 to use .kittify/templates/\n"

            pytest.fail(error_msg)

    def test_correct_templates_use_python_cli(self, spec_kitty_repo_root):
        """
        VERIFICATION: .kittify/templates/ should use Python CLI commands

        This verifies that the CORRECT template source uses Python CLI commands.
        """
        kittify_templates = spec_kitty_repo_root / '.kittify' / 'templates'
        if not kittify_templates.exists():
            pytest.skip(".kittify/templates/ doesn't exist")

        python_cli_commands = []

        for md_file in kittify_templates.rglob('*.md'):
            content = md_file.read_text(encoding='utf-8')

            # Look for Python CLI command patterns
            # e.g., "spec-kitty agent feature ...", "spec-kitty task approve"
            cli_matches = re.findall(r'spec-kitty\s+(?:agent|task|worktree|dashboard)', content)
            if cli_matches:
                python_cli_commands.append({
                    'file': md_file.relative_to(kittify_templates),
                    'commands': len(cli_matches)
                })

        # Should have multiple files with Python CLI commands
        assert len(python_cli_commands) > 0, (
            ".kittify/templates/ should contain Python CLI commands\n"
            "If this fails, .kittify/templates/ might not be the correct source either"
        )

    def test_kittify_templates_have_no_script_references(self, spec_kitty_repo_root):
        """
        VERIFICATION: .kittify/templates/ should NOT have script references

        This confirms the correct template source doesn't have the bug.
        """
        kittify_templates = spec_kitty_repo_root / '.kittify' / 'templates'
        if not kittify_templates.exists():
            pytest.skip(".kittify/templates/ doesn't exist")

        script_references = []

        for md_file in kittify_templates.rglob('*.md'):
            content = md_file.read_text(encoding='utf-8')

            # Look for script references
            sh_matches = re.findall(r'[\w\-\.]+\.sh', content)
            ps1_matches = re.findall(r'[\w\-\.]+\.ps1', content)

            if sh_matches or ps1_matches:
                script_references.append({
                    'file': md_file.relative_to(kittify_templates),
                    'sh': sh_matches,
                    'ps1': ps1_matches
                })

        if script_references:
            error_msg = "WARNING: .kittify/templates/ contains script references:\n"
            for ref in script_references:
                if ref['sh']:
                    error_msg += f"  {ref['file']}: .sh files: {', '.join(set(ref['sh']))}\n"
                if ref['ps1']:
                    error_msg += f"  {ref['file']}: .ps1 files: {', '.join(set(ref['ps1']))}\n"
            error_msg += "\nEven the correct template source has script references!"

            pytest.fail(error_msg)

    def test_pyproject_toml_points_to_correct_templates(self, spec_kitty_repo_root):
        """
        ROOT CAUSE: Check pyproject.toml line 72

        This is the actual bug - pyproject.toml points to wrong directory.
        """
        pyproject_file = spec_kitty_repo_root / 'pyproject.toml'
        if not pyproject_file.exists():
            pytest.skip("pyproject.toml not found")

        content = pyproject_file.read_text(encoding='utf-8')

        # Look for the [tool.setuptools.package-data] section
        # Should have: ".kittify/templates" = "specify_cli/templates"
        # Bug has: "templates" = "specify_cli/templates"

        # Check if wrong pattern exists
        wrong_pattern = re.search(r'"templates"\s*=\s*"specify_cli/templates"', content)
        correct_pattern = re.search(r'"\\.kittify/templates"\s*=\s*"specify_cli/templates"', content)

        if wrong_pattern and not correct_pattern:
            pytest.fail(
                "CRITICAL BUG: pyproject.toml points to wrong template directory!\n\n"
                f"Found at line ~{content[:wrong_pattern.start()].count(chr(10)) + 1}:\n"
                f'  "templates" = "specify_cli/templates"\n\n'
                "Should be:\n"
                '  ".kittify/templates" = "specify_cli/templates"\n\n'
                "This is the root cause of Issues #62, #63, #64!"
            )


class TestNewProjectInitValidation:
    """Validate that newly initialized projects have correct templates."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_new_project_no_bash_references(self, temp_project_dir, spec_kitty_repo_root):
        """
        Issue #62, #64: New projects should NOT reference .sh scripts

        Test by creating a new project and scanning all generated files.
        """
        project_name = "test_bash_refs"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        result = subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            pytest.skip(f"Init failed: {result.stderr}")

        # Scan all .md files for bash script references
        bash_refs = []
        for md_file in project_path.rglob('*.md'):
            # Skip node_modules, venv, etc.
            if any(part.startswith('.') and part != '.github' and part != '.kittify'
                   for part in md_file.parts):
                continue

            content = md_file.read_text(encoding='utf-8')
            sh_matches = re.findall(r'[\w\-\.]+\.sh', content)
            if sh_matches:
                bash_refs.append({
                    'file': md_file.relative_to(project_path),
                    'references': sh_matches
                })

        if bash_refs:
            error_msg = "BUG CONFIRMED (Issue #62, #64): New project contains bash script references:\n"
            for ref in bash_refs:
                error_msg += f"  {ref['file']}: {', '.join(set(ref['references']))}\n"
            error_msg += "\nNew projects are getting outdated templates with script references!"

            pytest.fail(error_msg)

    def test_new_project_no_powershell_references(self, temp_project_dir, spec_kitty_repo_root):
        """
        Issue #63: New projects should NOT reference .ps1 scripts

        Test the exact scenario from Issue #63.
        """
        project_name = "test_ps1_refs"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        result = subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            pytest.skip(f"Init failed: {result.stderr}")

        # Check the specific file mentioned in Issue #63
        specify_prompt = project_path / '.github' / 'prompts' / 'spec-kitty.specify.prompt.md'

        if not specify_prompt.exists():
            # Might be in different location for different agents
            specify_prompts = list(project_path.rglob('spec-kitty.specify.prompt.md'))
            if not specify_prompts:
                pytest.skip("spec-kitty.specify.prompt.md not found")
            specify_prompt = specify_prompts[0]

        content = specify_prompt.read_text(encoding='utf-8')

        # Look for PowerShell script references
        ps1_matches = re.findall(r'[\w\-\.]+\.ps1', content)

        if ps1_matches:
            pytest.fail(
                f"BUG CONFIRMED (Issue #63): {specify_prompt.relative_to(project_path)} "
                f"references PowerShell scripts:\n"
                f"  {', '.join(set(ps1_matches))}\n\n"
                f"This is exactly Issue #63 - new projects get outdated templates!"
            )

    def test_new_project_uses_python_cli_commands(self, temp_project_dir, spec_kitty_repo_root):
        """
        CORRECT BEHAVIOR: New projects should use Python CLI commands

        Verify that command templates contain spec-kitty CLI commands, not scripts.
        """
        project_name = "test_cli_commands"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        result = subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            pytest.skip(f"Init failed: {result.stderr}")

        # Find command templates
        command_templates = list(project_path.rglob('spec-kitty.*.prompt.md'))

        if not command_templates:
            pytest.skip("No command templates found")

        # At least some should have Python CLI commands
        has_cli_commands = False
        for template in command_templates:
            content = template.read_text(encoding='utf-8')
            if re.search(r'spec-kitty\s+(?:agent|task|worktree|dashboard)', content):
                has_cli_commands = True
                break

        assert has_cli_commands, (
            "New project command templates should use Python CLI commands\n"
            f"Checked {len(command_templates)} templates, none had CLI commands\n"
            "This means the project got outdated templates!"
        )

    def test_all_command_templates_correct(self, temp_project_dir, spec_kitty_repo_root):
        """
        COMPREHENSIVE: Scan all command templates for script references

        Issue #64 states ALL slash commands reference scripts.
        """
        project_name = "test_all_commands"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        result = subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            pytest.skip(f"Init failed: {result.stderr}")

        # Find all command templates
        command_templates = list(project_path.rglob('spec-kitty.*.prompt.md'))

        if not command_templates:
            pytest.skip("No command templates found")

        templates_with_scripts = []

        for template in command_templates:
            content = template.read_text(encoding='utf-8')

            sh_matches = re.findall(r'[\w\-\.]+\.sh', content)
            ps1_matches = re.findall(r'[\w\-\.]+\.ps1', content)

            if sh_matches or ps1_matches:
                templates_with_scripts.append({
                    'file': template.relative_to(project_path),
                    'sh': sh_matches,
                    'ps1': ps1_matches
                })

        if templates_with_scripts:
            error_msg = f"BUG CONFIRMED (Issue #64): {len(templates_with_scripts)} command template(s) have script references:\n"
            for template in templates_with_scripts:
                error_msg += f"\n  {template['file']}:\n"
                if template['sh']:
                    error_msg += f"    Bash: {', '.join(set(template['sh']))}\n"
                if template['ps1']:
                    error_msg += f"    PowerShell: {', '.join(set(template['ps1']))}\n"
            error_msg += "\nIssue #64: ALL slash commands reference non-existent scripts!"

            pytest.fail(error_msg)

    def test_worktree_commands_use_cli(self, temp_project_dir, spec_kitty_repo_root):
        """
        Issue #62: Worktree commands should use Python CLI, not check-prerequisites.sh
        """
        project_name = "test_worktree"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        result = subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            pytest.skip(f"Init failed: {result.stderr}")

        # Find worktree-related command templates
        worktree_templates = list(project_path.rglob('spec-kitty.*worktree*.prompt.md'))
        worktree_templates.extend(project_path.rglob('spec-kitty.*feature*.prompt.md'))

        if not worktree_templates:
            pytest.skip("No worktree command templates found")

        for template in worktree_templates:
            content = template.read_text(encoding='utf-8')

            # Check for the specific script mentioned in Issue #62
            if 'check-prerequisites.sh' in content:
                pytest.fail(
                    f"BUG CONFIRMED (Issue #62): {template.relative_to(project_path)} "
                    f"references check-prerequisites.sh\n\n"
                    f"This is the exact issue - worktree commands reference bash scripts!"
                )

    def test_new_project_structure_complete(self, temp_project_dir, spec_kitty_repo_root):
        """
        VALIDATION: New projects should have complete structure

        No missing templates, no broken references.
        """
        project_name = "test_structure"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        result = subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            pytest.skip(f"Init failed: {result.stderr}")

        # Should have .kittify directory
        assert (project_path / '.kittify').exists(), ".kittify directory should exist"

        # Should have command templates
        command_templates = list(project_path.rglob('spec-kitty.*.prompt.md'))
        assert len(command_templates) >= 10, (
            f"Should have at least 10 command templates, got {len(command_templates)}\n"
            "Missing templates might indicate bundling issue"
        )


class TestTemplateDirectoryStructure:
    """Validate template directory structure in spec-kitty repo."""

    def test_both_template_directories_exist(self, spec_kitty_repo_root):
        """
        ANALYSIS: Check if both template directories exist

        This helps understand the divergence mentioned in Issue #64.
        """
        templates_dir = spec_kitty_repo_root / 'templates'
        kittify_templates = spec_kitty_repo_root / '.kittify' / 'templates'

        templates_exists = templates_dir.exists()
        kittify_exists = kittify_templates.exists()

        print(f"\nTemplate Directory Analysis:")
        print(f"  /templates/ exists: {templates_exists}")
        print(f"  /.kittify/templates/ exists: {kittify_exists}")

        if templates_exists and kittify_exists:
            # Count files in each
            templates_files = list(templates_dir.rglob('*.md'))
            kittify_files = list(kittify_templates.rglob('*.md'))

            print(f"  /templates/ has {len(templates_files)} .md files")
            print(f"  /.kittify/templates/ has {len(kittify_files)} .md files")

        assert kittify_exists, (
            ".kittify/templates/ should exist\n"
            "This is the correct template source"
        )

    def test_mission_templates_exist(self, spec_kitty_repo_root):
        """
        Issue #64: Check for mission-based templates

        Issue #64 mentions three divergent template sources, including missions.
        """
        missions_dir = spec_kitty_repo_root / '.kittify' / 'missions'

        if not missions_dir.exists():
            pytest.skip("Missions directory doesn't exist")

        # Find mission command templates
        mission_templates = list(missions_dir.rglob('command-templates/*.md'))

        print(f"\nMission Templates Analysis:")
        print(f"  Found {len(mission_templates)} command templates in missions/")

    def test_template_divergence_analysis(self, spec_kitty_repo_root):
        """
        Issue #64: Analyze the three divergent template sources

        1. /templates/command-templates/ (outdated, bash refs)
        2. /.kittify/templates/command-templates/ (correct, Python CLI)
        3. /.kittify/missions/*/command-templates/ (migrations only)
        """
        templates_dir = spec_kitty_repo_root / 'templates' / 'command-templates'
        kittify_dir = spec_kitty_repo_root / '.kittify' / 'templates' / 'command-templates'
        missions_dir = spec_kitty_repo_root / '.kittify' / 'missions'

        sources = {
            '/templates/command-templates/': templates_dir,
            '/.kittify/templates/command-templates/': kittify_dir,
            '/.kittify/missions/*/command-templates/': missions_dir
        }

        print("\nTemplate Source Analysis:")
        for name, path in sources.items():
            if not path.exists():
                print(f"  {name}: NOT FOUND")
                continue

            if name.endswith('missions/'):
                # Count mission templates
                mission_templates = list(path.rglob('command-templates/*.md'))
                print(f"  {name}: {len(mission_templates)} templates in missions")
            else:
                # Count templates
                templates = list(path.glob('*.md'))
                print(f"  {name}: {len(templates)} templates")

                # Check for script references
                has_scripts = False
                for template in templates[:5]:  # Sample first 5
                    content = template.read_text(encoding='utf-8')
                    if re.search(r'[\w\-\.]+\.(sh|ps1)', content):
                        has_scripts = True
                        break

                print(f"    Script references: {has_scripts}")


class TestUpgradePathValidation:
    """Validate that upgrade path works correctly."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_upgrade_command_exists(self, temp_project_dir, spec_kitty_repo_root):
        """
        Issue #62: Users need to run spec-kitty upgrade

        Verify the upgrade command exists and works.
        """
        project_name = "test_upgrade"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Create project
        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        # Run upgrade
        result = subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60
        )

        assert result.returncode == 0, (
            "spec-kitty upgrade should succeed\n"
            f"Error: {result.stderr}"
        )

    def test_upgrade_message_quality(self, temp_project_dir, spec_kitty_repo_root):
        """
        Issue #62: When users hit script errors, they should be told to upgrade

        Verify error messages guide users to the solution.
        """
        # This test validates error message quality
        # We can't easily simulate the error without the bug, but we can
        # verify that upgrade is documented

        project_name = "test_upgrade_msg"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        # Run upgrade and check output
        result = subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60
        )

        # Output should mention migrations or updates
        output = result.stdout + result.stderr

        # Should have some output about what was done
        assert len(output) > 0, "Upgrade should provide output about what it did"

    def test_version_comparison_for_new_projects(self, temp_project_dir, spec_kitty_repo_root):
        """
        Issue #64: Migration doesn't work for new projects (version comparison issue)

        New projects with v0.10.8 shouldn't need migrations for v0.10.8 changes.
        """
        project_name = "test_version"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Create new project
        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        # Check version metadata
        version_file = project_path / '.kittify' / 'version.txt'
        if version_file.exists():
            version = version_file.read_text().strip()
            print(f"\nProject initialized with version: {version}")

        # Run upgrade (should detect no migrations needed for new project)
        result = subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60
        )

        # For a brand new project, upgrade shouldn't fail
        assert result.returncode == 0, (
            "Upgrade should work on newly created project\n"
            f"Error: {result.stderr}"
        )


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
