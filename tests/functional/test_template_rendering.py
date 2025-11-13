"""
Category 3: Template Rendering Tests

Tests advanced variable substitution, format conversion, and path rewriting.

Test Coverage:
1. Variable Substitution (5 tests)
   - $ARGUMENTS variable present in commands
   - {SCRIPT} variable substituted correctly per script type
   - {AGENT_SCRIPT} variable handling
   - __AGENT__ internal variable not exposed
   - Mission-specific variables

2. Format Conversion (3 tests)
   - Markdown to TOML conversion for gemini/qwen
   - .prompt.md format for copilot
   - Frontmatter preservation

3. Path Rewriting (2 tests)
   - Relative paths converted to .kittify/ references
   - Agent script paths substituted correctly
"""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest


class TestVariableSubstitution:
    """Test variable substitution in rendered templates."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_arguments_variable_in_all_commands(self, temp_project_dir, spec_kitty_repo_root):
        """Test: All rendered commands contain $ARGUMENTS or equivalent variable (except commands that don't need input)"""
        project_name = "test_args_var"
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
            check=True
        )

        commands_dir = project_path / '.claude' / 'commands'
        assert commands_dir.exists(), "Commands directory should exist"

        command_files = list(commands_dir.glob('spec-kitty.*.md'))
        assert len(command_files) > 0, "Should have command files"

        # Commands that don't need user input (no $ARGUMENTS)
        no_args_commands = {'dashboard', 'merge', 'research'}

        for command_file in command_files:
            content = command_file.read_text()
            command_name = command_file.stem.replace('spec-kitty.', '')

            if command_name not in no_args_commands:
                assert '$ARGUMENTS' in content, \
                    f"{command_file.name} should contain $ARGUMENTS variable"

    def test_script_variable_substitution_sh(self, temp_project_dir, spec_kitty_repo_root):
        """Test: {SCRIPT} variable correctly substituted for sh script type"""
        project_name = "test_script_sh"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        result = subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--script=sh', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Check specify command which has script frontmatter
        specify_cmd = project_path / '.claude' / 'commands' / 'spec-kitty.specify.md'
        assert specify_cmd.exists(), "specify command should exist"

        content = specify_cmd.read_text()

        # Should contain the sh script path
        assert '.kittify/scripts/bash/' in content, \
            "Should contain bash script path for sh script type"
        assert '.sh' in content, \
            "Should reference .sh script file"

        # Should NOT contain unreplaced {SCRIPT} placeholder
        assert '{SCRIPT}' not in content, \
            "Should not contain unreplaced {SCRIPT} placeholder"

    def test_script_variable_substitution_ps(self, temp_project_dir, spec_kitty_repo_root):
        """Test: {SCRIPT} variable correctly substituted for ps script type"""
        project_name = "test_script_ps"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        result = subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--script=ps', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Check specify command which has script frontmatter
        specify_cmd = project_path / '.claude' / 'commands' / 'spec-kitty.specify.md'
        assert specify_cmd.exists(), "specify command should exist"

        content = specify_cmd.read_text()

        # Should contain the PowerShell script path
        assert '.kittify/scripts/powershell/' in content, \
            "Should contain powershell script path for ps script type"
        assert '.ps1' in content, \
            "Should reference .ps1 script file"

        # Should NOT contain unreplaced {SCRIPT} placeholder
        assert '{SCRIPT}' not in content, \
            "Should not contain unreplaced {SCRIPT} placeholder"

    def test_agent_script_variable_handling(self, temp_project_dir, spec_kitty_repo_root):
        """Test: {AGENT_SCRIPT} variable properly handled (present or removed)"""
        project_name = "test_agent_script"
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
            check=True
        )

        commands_dir = project_path / '.claude' / 'commands'
        command_files = list(commands_dir.glob('spec-kitty.*.md'))

        for command_file in command_files:
            content = command_file.read_text()

            # Should NOT contain unreplaced {AGENT_SCRIPT} placeholder
            assert '{AGENT_SCRIPT}' not in content, \
                f"{command_file.name} should not contain unreplaced {{AGENT_SCRIPT}} placeholder"

    def test_no_internal_agent_variable_exposed(self, temp_project_dir, spec_kitty_repo_root):
        """Test: __AGENT__ internal variable not exposed in rendered commands"""
        project_name = "test_no_internal"
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
            check=True
        )

        commands_dir = project_path / '.claude' / 'commands'
        command_files = list(commands_dir.glob('spec-kitty.*.md'))

        for command_file in command_files:
            content = command_file.read_text()

            # Should NOT contain __AGENT__ placeholder
            assert '__AGENT__' not in content, \
                f"{command_file.name} should not expose __AGENT__ internal variable"


class TestFormatConversion:
    """Test format conversion for different agent types."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_markdown_to_toml_conversion_gemini(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Markdown commands converted to TOML format for gemini"""
        project_name = "test_toml_gemini"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        result = subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=gemini', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        commands_dir = project_path / '.gemini' / 'commands'
        assert commands_dir.exists(), "Commands directory should exist"

        # Get all .toml files
        toml_files = list(commands_dir.glob('*.toml'))
        assert len(toml_files) > 0, "Should have TOML command files for gemini"

        # Check a sample command file
        sample_file = toml_files[0]
        content = sample_file.read_text()

        # Should have TOML structure
        assert 'description = ' in content, "Should have description field"
        assert 'prompt = """' in content, "Should have prompt field with triple quotes"

        # Should use {{args}} instead of $ARGUMENTS
        assert '{{args}}' in content, "Should use {{args}} variable for gemini"
        assert '$ARGUMENTS' not in content, "Should NOT contain $ARGUMENTS in TOML format"

    def test_markdown_to_toml_conversion_qwen(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Markdown commands converted to TOML format for qwen"""
        project_name = "test_toml_qwen"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        result = subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=qwen', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        commands_dir = project_path / '.qwen' / 'commands'
        assert commands_dir.exists(), "Commands directory should exist"

        # Get all .toml files
        toml_files = list(commands_dir.glob('*.toml'))
        assert len(toml_files) > 0, "Should have TOML command files for qwen"

        # Check a sample command file
        sample_file = toml_files[0]
        content = sample_file.read_text()

        # Should have TOML structure
        assert 'description = ' in content, "Should have description field"
        assert 'prompt = """' in content, "Should have prompt field"

        # Should use {{args}} instead of $ARGUMENTS
        assert '{{args}}' in content, "Should use {{args}} variable for qwen"
        assert '$ARGUMENTS' not in content, "Should NOT contain $ARGUMENTS in TOML format"

    def test_prompt_md_format_for_copilot(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Commands use .prompt.md extension for copilot"""
        project_name = "test_copilot_format"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        result = subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=copilot', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Copilot uses .github/prompts/ directory
        prompts_dir = project_path / '.github' / 'prompts'
        assert prompts_dir.exists(), "Prompts directory should exist for copilot"

        # Check that .prompt.md files exist
        prompt_files = list(prompts_dir.glob('*.prompt.md'))
        assert len(prompt_files) > 0, "Should have .prompt.md files for copilot"

        # Verify format - should be markdown with frontmatter
        sample_file = prompt_files[0]
        content = sample_file.read_text()

        # Should preserve markdown format
        assert content.startswith('---\n') or '$ARGUMENTS' in content, \
            "Should be markdown format (with frontmatter or content)"


class TestPathRewriting:
    """Test path rewriting in rendered templates."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_relative_paths_converted_to_kittify_references(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Relative paths in templates converted to .kittify/ references"""
        project_name = "test_path_rewrite"
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
            check=True
        )

        commands_dir = project_path / '.claude' / 'commands'
        command_files = list(commands_dir.glob('spec-kitty.*.md'))

        for command_file in command_files:
            content = command_file.read_text()

            # Check for patterns that should be rewritten
            # Templates reference scripts/, templates/, memory/ which should be .kittify/...
            if 'scripts/' in content:
                assert '.kittify/scripts/' in content, \
                    f"{command_file.name} should reference .kittify/scripts/ not bare scripts/"

            if 'templates/' in content:
                assert '.kittify/templates/' in content, \
                    f"{command_file.name} should reference .kittify/templates/ not bare templates/"

            if 'memory/' in content:
                assert '.kittify/memory/' in content, \
                    f"{command_file.name} should reference .kittify/memory/ not bare memory/"

    def test_agent_script_paths_correct(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Agent script paths correctly reference .kittify/scripts/"""
        project_name = "test_script_paths"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        result = subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--script=sh', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Check specify command which references scripts
        specify_cmd = project_path / '.claude' / 'commands' / 'spec-kitty.specify.md'
        if specify_cmd.exists():
            content = specify_cmd.read_text()

            # Should reference .kittify/scripts/bash/ for sh type
            if 'scripts/' in content:
                assert '.kittify/scripts/' in content, \
                    "Scripts should be referenced under .kittify/scripts/"
                assert 'bash/' in content or 'powershell/' in content, \
                    "Should reference specific script type directory"
