"""
Test: User Experience Simulation - Testing Without Development Overrides

Purpose: Test spec-kitty exactly as PyPI users experience it, without any development
environment variables or shortcuts.

THE CRITICAL MISSING TEST:
Every existing test used SPEC_KITTY_TEMPLATE_ROOT to bypass the package's bundled
templates. This test explicitly REMOVES that variable to simulate real user experience.

Test Coverage:
1. Init without SPEC_KITTY_TEMPLATE_ROOT (real user experience)
2. Commands work without development overrides
3. Templates have correct content (no script references)
4. User workflow end-to-end

Related Issues: #62, #63, #64
Related Finding: 2026-01-06_02_test_suite_systemic_failure_analysis.md
"""

import os
import re
import subprocess
import tempfile
from pathlib import Path

import pytest


class TestPyPIUserExperience:
    """Test user experience without development environment overrides."""

    @pytest.fixture
    def clean_environment(self):
        """
        Clean environment without development overrides

        This is THE KEY DIFFERENCE from existing tests.
        """
        env = os.environ.copy()

        # CRITICAL: Remove development overrides
        env.pop('SPEC_KITTY_TEMPLATE_ROOT', None)
        env.pop('SPEC_KITTY_REPO', None)

        # Remove any other spec-kitty development variables
        to_remove = [k for k in env.keys() if k.startswith('SPEC_KITTY_') and k not in ['SPEC_KITTY_API_KEY']]
        for key in to_remove:
            if key != 'SPEC_KITTY_API_KEY':  # Keep API key if set
                env.pop(key, None)

        return env

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_init_succeeds_without_template_root_override(
        self,
        temp_project_dir,
        clean_environment
    ):
        """
        CRITICAL: spec-kitty init must work without SPEC_KITTY_TEMPLATE_ROOT

        This is how PyPI users experience it. All existing tests set this variable,
        which hid the bug.
        """
        project_name = 'pypi_user_test'

        result = subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=clean_environment,  # No SPEC_KITTY_TEMPLATE_ROOT!
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30
        )

        assert result.returncode == 0, (
            f"Init should succeed without SPEC_KITTY_TEMPLATE_ROOT\n"
            f"This simulates PyPI user experience\n\n"
            f"Error: {result.stderr}\n"
            f"Output: {result.stdout}"
        )

        project_path = temp_project_dir / project_name
        assert project_path.exists(), "Project directory should be created"

    def test_command_templates_exist_without_overrides(
        self,
        temp_project_dir,
        clean_environment
    ):
        """
        VALIDATION: Command templates must be created even without env var overrides
        """
        project_name = 'template_check'
        project_path = temp_project_dir / project_name

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=clean_environment,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        # Check for command templates (claude uses .claude/commands/)
        claude_commands = project_path / '.claude' / 'commands'
        assert claude_commands.exists(), f"Command directory should exist: {claude_commands}"

        # Should have spec-kitty command files (format: spec-kitty.*.md)
        command_files = list(claude_commands.glob('spec-kitty.*.md'))

        assert len(command_files) >= 10, (
            f"Should have at least 10 command templates\n"
            f"Found: {len(command_files)} in {claude_commands}\n\n"
            f"This test runs WITHOUT SPEC_KITTY_TEMPLATE_ROOT,\n"
            f"so it uses templates from the installed package."
        )

    def test_command_templates_have_correct_content_without_overrides(
        self,
        temp_project_dir,
        clean_environment
    ):
        """
        CRITICAL VALIDATION: Templates must use Python CLI, not bash/PowerShell

        This is THE TEST that would have caught Issues #62, #63, #64.

        It runs WITHOUT SPEC_KITTY_TEMPLATE_ROOT, so it gets templates from
        the actual installed package (not local development repository).
        """
        project_name = 'content_validation'
        project_path = temp_project_dir / project_name

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=clean_environment,  # THE KEY: No development overrides
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        # Scan all command templates
        command_dir = project_path / '.claude' / 'commands'
        templates_with_scripts = []
        templates_with_cli = []

        for template in command_dir.glob('spec-kitty.*.md'):
            content = template.read_text(encoding='utf-8')

            # Check for script references (BUG)
            sh_refs = re.findall(r'[\w\-\.]+\.sh', content)
            ps1_refs = re.findall(r'[\w\-\.]+\.ps1', content)

            if sh_refs or ps1_refs:
                templates_with_scripts.append({
                    'file': template.name,
                    'sh': sh_refs,
                    'ps1': ps1_refs
                })

            # Check for Python CLI usage (CORRECT)
            if re.search(r'spec-kitty\s+(?:agent|task|worktree|dashboard)', content):
                templates_with_cli.append(template.name)

        # CRITICAL ASSERTION: No script references
        if templates_with_scripts:
            error_msg = (
                "🐛 BUG CONFIRMED: Command templates contain script references!\n\n"
                "This test runs WITHOUT SPEC_KITTY_TEMPLATE_ROOT,\n"
                "so it uses templates from the INSTALLED PACKAGE.\n\n"
                f"Found {len(templates_with_scripts)} template(s) with script references:\n"
            )
            for t in templates_with_scripts:
                error_msg += f"\n  {t['file']}:\n"
                if t['sh']:
                    error_msg += f"    Bash: {', '.join(set(t['sh']))}\n"
                if t['ps1']:
                    error_msg += f"    PowerShell: {', '.join(set(t['ps1']))}\n"

            error_msg += (
                "\nThis means the PACKAGE is broken (pyproject.toml bundles wrong templates).\n"
                "This is exactly Issues #62, #63, #64!"
            )

            pytest.fail(error_msg)

        # Should have Python CLI commands (6+ templates typically use spec-kitty agent/task commands)
        assert len(templates_with_cli) >= 6, (
            f"Most templates should use Python CLI commands\n"
            f"Found: {len(templates_with_cli)} templates with spec-kitty commands"
        )

    def test_worktree_command_has_no_script_references_without_overrides(
        self,
        temp_project_dir,
        clean_environment
    ):
        """
        Issue #62: Worktree commands must not reference check-prerequisites.sh

        This test would have caught Issue #62 before users discovered it.
        """
        project_name = 'worktree_test'
        project_path = temp_project_dir / project_name

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=clean_environment,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        # Find worktree-related commands
        command_dir = project_path / '.claude' / 'commands'
        worktree_commands = []

        for template in command_dir.glob('spec-kitty.*.md'):
            # implement.md handles worktree creation in workspace-per-WP model
            if 'feature' in template.name.lower() or 'worktree' in template.name.lower() or 'implement' in template.name.lower():
                worktree_commands.append(template)

        assert len(worktree_commands) > 0, "Should have worktree/feature/implement commands"

        # Check each for the specific Issue #62 problem
        for cmd_file in worktree_commands:
            content = cmd_file.read_text(encoding='utf-8')

            # Issue #62 specific check
            if 'check-prerequisites.sh' in content:
                pytest.fail(
                    f"🐛 ISSUE #62 CONFIRMED: {cmd_file.name} references check-prerequisites.sh\n\n"
                    f"This is the exact bug users reported.\n"
                    f"This script doesn't exist in Python CLI version."
                )

            # General check
            if re.search(r'[\w\-\.]+\.sh', content):
                pytest.fail(
                    f"🐛 BUG: {cmd_file.name} references bash scripts\n"
                    f"Worktree commands should use Python CLI"
                )

    def test_specify_command_has_no_ps1_references_without_overrides(
        self,
        temp_project_dir,
        clean_environment
    ):
        """
        Issue #63: spec-kitty.specify.md must not reference .ps1 scripts

        This is the exact file mentioned in Issue #63.
        """
        project_name = 'specify_test'
        project_path = temp_project_dir / project_name

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=clean_environment,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        # Find spec-kitty.specify.md
        specify_file = project_path / '.claude' / 'commands' / 'spec-kitty.specify.md'

        if not specify_file.exists():
            # Try alternate locations
            specify_files = list(project_path.rglob('spec-kitty.specify.md'))
            if not specify_files:
                pytest.skip("spec-kitty.specify.md not found")
            specify_file = specify_files[0]

        content = specify_file.read_text(encoding='utf-8')

        # Issue #63 specific check
        ps1_refs = re.findall(r'[\w\-\.]+\.ps1', content)

        if ps1_refs:
            pytest.fail(
                f"🐛 ISSUE #63 CONFIRMED: spec-kitty.specify.md references .ps1 scripts\n\n"
                f"Found: {', '.join(set(ps1_refs))}\n\n"
                f"This is the exact bug from Issue #63.\n"
                f"These PowerShell scripts don't exist."
            )

    def test_all_agents_get_correct_templates_without_overrides(
        self,
        temp_project_dir,
        clean_environment
    ):
        """
        Issue #64: ALL 12 AI agents should get correct templates

        Test multiple agents to ensure the bug doesn't affect any of them.
        """
        agents_to_test = ['claude', 'copilot', 'gemini']
        agents_with_script_refs = []

        for agent in agents_to_test:
            project_name = f'test_{agent}'
            project_path = temp_project_dir / project_name

            result = subprocess.run(
                ['spec-kitty', 'init', project_name, f'--ai={agent}', '--ignore-agent-tools'],
                cwd=temp_project_dir,
                env=clean_environment,
                input='y\n',
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                continue  # Skip if init failed for this agent

            # Find command templates for this agent
            command_files = list(project_path.rglob('spec-kitty.*.md')) + \
                           list(project_path.rglob('spec-kitty.*.md')) + \
                           list(project_path.rglob('spec-kitty.*.toml'))

            for cmd_file in command_files:
                try:
                    content = cmd_file.read_text(encoding='utf-8')
                except:
                    continue  # Skip binary or problematic files

                # Check for script references
                if re.search(r'[\w\-\.]+\.(sh|ps1)', content):
                    agents_with_script_refs.append({
                        'agent': agent,
                        'file': cmd_file.relative_to(project_path)
                    })

        if agents_with_script_refs:
            error_msg = (
                f"🐛 ISSUE #64 CONFIRMED: Multiple agents affected by script references\n\n"
                f"Found script references in {len(agents_with_script_refs)} file(s):\n"
            )
            for ref in agents_with_script_refs:
                error_msg += f"  {ref['agent']}: {ref['file']}\n"

            error_msg += "\nALL agents should use Python CLI commands, not scripts!"

            pytest.fail(error_msg)


class TestDevelopmentVsProductionParity:
    """Ensure development and production environments behave the same."""

    @pytest.fixture
    def dev_environment(self, spec_kitty_repo_root):
        """Development environment (with SPEC_KITTY_TEMPLATE_ROOT)"""
        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)
        return env

    @pytest.fixture
    def prod_environment(self):
        """Production environment (without overrides)"""
        env = os.environ.copy()
        env.pop('SPEC_KITTY_TEMPLATE_ROOT', None)
        env.pop('SPEC_KITTY_REPO', None)
        return env

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.mark.parametrize('environment_name', ['dev_environment', 'prod_environment'])
    def test_init_succeeds_in_both_environments(
        self,
        environment_name,
        temp_project_dir,
        request
    ):
        """
        PARITY: Init should succeed in both development and production environments

        This test runs the SAME test with BOTH environments to ensure parity.
        """
        env = request.getfixturevalue(environment_name)
        project_name = f'test_{environment_name}'

        result = subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30
        )

        assert result.returncode == 0, (
            f"Init should succeed in {environment_name}\n"
            f"Error: {result.stderr}"
        )

    @pytest.mark.parametrize('environment_name', ['dev_environment', 'prod_environment'])
    def test_templates_have_cli_commands_in_both_environments(
        self,
        environment_name,
        temp_project_dir,
        request
    ):
        """
        PARITY: Templates should use Python CLI in BOTH environments

        This ensures development and production give users the same experience.
        """
        env = request.getfixturevalue(environment_name)
        project_name = f'test_{environment_name}'
        project_path = temp_project_dir / project_name

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

        # Scan templates
        command_dir = project_path / '.claude' / 'commands'
        templates_with_cli = 0

        for template in command_dir.glob('spec-kitty.*.md'):
            content = template.read_text(encoding='utf-8')
            if re.search(r'spec-kitty\s+(?:agent|task|worktree)', content):
                templates_with_cli += 1

        assert templates_with_cli >= 6, (
            f"Templates should use Python CLI in {environment_name}\n"
            f"Found: {templates_with_cli} templates with CLI commands"
        )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
