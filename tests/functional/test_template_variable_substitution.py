"""
Template Variable Substitution Tests

Tests that command templates have all variables properly substituted
before being shown to agents. Unsubstituted placeholders like {SCRIPT}
or $ARGUMENTS cause agents to halt execution.

The Bug:
-------
Command templates contain placeholders that should be filled during rendering:
- {SCRIPT} - Path to helper script
- $ARGUMENTS - User input passed to command
- {FEATURE_DIR} - Feature directory path
- etc.

If these aren't substituted, agents see literal "{SCRIPT}" in the prompt
and cannot proceed.

Example from user report:
```
2. Run `{SCRIPT}` from repo root and parse FEATURE_DIR and AVAILABLE_DOCS list.
```

Agent response: "The command placeholder {SCRIPT} wasn't provided, so I don't
have the FEATURE_DIR/AVAILABLE_DOCS data."

Test Coverage:
-------------
1. Variable Detection (3 tests)
   - Find all template variables in command files
   - Detect unsubstituted placeholders
   - Report which commands have issues

2. Common Variables (4 tests)
   - $ARGUMENTS substitution
   - {SCRIPT} substitution
   - {FEATURE_DIR} substitution
   - {PROJECT_ROOT} substitution

3. Command-Specific Variables (3 tests)
   - implement.md has all variables filled
   - review.md has all variables filled
   - specify.md has all variables filled

4. Agent-Specific Rendering (3 tests)
   - Claude commands rendered correctly
   - Codex commands rendered correctly
   - Variables match agent's syntax requirements
"""

import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import List, Tuple

import pytest


@pytest.fixture
def spec_kitty_repo_root():
    """Get spec-kitty repository root."""
    env_path = os.environ.get('SPEC_KITTY_REPO')
    if env_path:
        return Path(env_path)

    default_path = Path(__file__).parent.parent.parent.parent / 'spec-kitty'
    if default_path.exists():
        return default_path

    raise ValueError("spec-kitty repository not found")


def find_template_variables(content: str) -> List[Tuple[str, str]]:
    """
    Find template variables in content.

    Returns list of (variable, pattern) tuples.
    """
    variables = []

    # Pattern 1: {VARIABLE_NAME}
    for match in re.finditer(r'\{([A-Z_]+)\}', content):
        variables.append((match.group(1), 'braces'))

    # Pattern 2: $VARIABLE_NAME (word boundary)
    for match in re.finditer(r'\$([A-Z_][A-Z0-9_]*)\b', content):
        # Skip shell variables like $$ or $? or $PWD
        var_name = match.group(1)
        if var_name not in ['SHELL', 'HOME', 'USER', 'PATH', 'PWD', 'OLDPWD']:
            variables.append((var_name, 'dollar'))

    # Pattern 3: {{variable}} (Jinja-style)
    for match in re.finditer(r'\{\{([a-z_]+)\}\}', content):
        variables.append((match.group(1), 'jinja'))

    return variables


class TestVariableDetection:
    """Test detection of template variables in command files."""

    def test_find_variables_in_implement_template(self, spec_kitty_repo_root):
        """Test: Detect variables in implement.md template"""
        # Check both template locations
        template_paths = [
            spec_kitty_repo_root / 'templates' / 'commands' / 'implement.md',
            spec_kitty_repo_root / '.kittify' / 'templates' / 'commands' / 'implement.md',
        ]

        for template_path in template_paths:
            if not template_path.exists():
                continue

            content = template_path.read_text(encoding='utf-8')
            variables = find_template_variables(content)

            print(f"\nVariables in {template_path.name}:")
            for var_name, pattern_type in variables:
                print(f"  {pattern_type}: {var_name}")

            # Should find $ARGUMENTS and {SCRIPT}
            var_names = [v[0] for v in variables]

            assert 'ARGUMENTS' in var_names, \
                f"Template should have $ARGUMENTS variable. Found: {var_names}"

            if 'SCRIPT' in var_names:
                print(f"  Found {{SCRIPT}} placeholder - should be substituted!")

    def test_detect_unsubstituted_placeholders_in_rendered_commands(self, spec_kitty_repo_root):
        """
        Test: Rendered commands in initialized project should have no placeholders.

        This is the critical test - checks AFTER template rendering.
        """
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'var_test'
            project_path = Path(temp_dir) / project_name

            env = os.environ.copy()
            env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

            # Create project
            subprocess.run(
                ['spec-kitty', 'init', project_name, '--ai=codex', '--ignore-agent-tools'],
                cwd=temp_dir,
                env=env,
                input='y\n',
                capture_output=True,
                text=True,
                check=True
            )

            # Check rendered command files
            codex_commands = project_path / '.codex' / 'prompts'
            if not codex_commands.exists():
                pytest.skip("Codex commands not generated")

            implement_cmd = codex_commands / 'spec-kitty.implement.md'
            if not implement_cmd.exists():
                pytest.skip("implement.md not found in rendered commands")

            content = implement_cmd.read_text(encoding='utf-8')

            # Look for unsubstituted placeholders
            unsubstituted = find_template_variables(content)

            # Filter out legitimate variables (like shell commands)
            problematic = []
            for var_name, pattern_type in unsubstituted:
                # {SCRIPT} should be substituted to an actual path
                if var_name == 'SCRIPT' and pattern_type == 'braces':
                    problematic.append(f'{{{var_name}}}')

                # $ARGUMENTS should be substituted or removed if no args
                if var_name == 'ARGUMENTS' and pattern_type == 'dollar':
                    # Check context - is it in a code block or literal text?
                    # In the user's example, it appears as literal "$ARGUMENTS"
                    problematic.append(f'${var_name}')

            if problematic:
                pytest.fail(
                    f"🐛 BUG: Unsubstituted template variables found!\n\n"
                    f"File: {implement_cmd}\n"
                    f"Unsubstituted: {', '.join(problematic)}\n\n"
                    f"These placeholders should be replaced during template rendering.\n"
                    f"Agents cannot execute commands with literal '{{SCRIPT}}' or '$ARGUMENTS'.\n\n"
                    f"This is the bug the user reported!"
                )

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_all_commands_have_no_placeholders(self, spec_kitty_repo_root):
        """Test: All rendered command files have variables substituted"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'all_vars_test'
            project_path = Path(temp_dir) / project_name

            env = os.environ.copy()
            env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

            # Create project with multiple agents
            subprocess.run(
                ['spec-kitty', 'init', project_name, '--ai=claude,codex', '--ignore-agent-tools'],
                cwd=temp_dir,
                env=env,
                input='y\n',
                capture_output=True,
                text=True,
                check=True
            )

            # Check all command files
            issues = []

            for agent_dir in ['.claude/commands', '.codex/prompts']:
                commands_path = project_path / agent_dir
                if not commands_path.exists():
                    continue

                for cmd_file in commands_path.glob('spec-kitty.*.md'):
                    content = cmd_file.read_text(encoding='utf-8')
                    variables = find_template_variables(content)

                    # Look for likely placeholders
                    for var_name, pattern_type in variables:
                        # These should definitely be substituted
                        if var_name in ['SCRIPT', 'FEATURE_DIR', 'PROJECT_ROOT']:
                            issues.append(f"{cmd_file.name}: {{{var_name}}}")

            if issues:
                pytest.fail(
                    f"Template placeholders not substituted in {len(issues)} locations:\n" +
                    "\n".join(f"  - {issue}" for issue in issues)
                )

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestCommonVariableSubstitution:
    """Test common template variables are properly substituted."""

    def test_arguments_variable_handling(self, spec_kitty_repo_root):
        """Test: $ARGUMENTS is either substituted with actual args or removed"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'args_test'
            project_path = Path(temp_dir) / project_name

            env = os.environ.copy()
            env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

            subprocess.run(
                ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
                cwd=temp_dir,
                env=env,
                input='y\n',
                capture_output=True,
                text=True,
                check=True
            )

            # Check implement command
            implement_cmd = project_path / '.claude' / 'commands' / 'spec-kitty.implement.md'
            if not implement_cmd.exists():
                pytest.skip("implement.md not found")

            content = implement_cmd.read_text(encoding='utf-8')

            # Check for literal $ARGUMENTS in user-facing text
            # It's OK in code blocks like ```bash, but not in prose
            lines = content.split('\n')
            problematic_lines = []

            in_code_block = False
            for i, line in enumerate(lines, 1):
                if line.strip().startswith('```'):
                    in_code_block = not in_code_block
                    continue

                if not in_code_block and '$ARGUMENTS' in line:
                    # Check if it's in a context that should be substituted
                    if '## User Input' in line or 'text\n  $ARGUMENTS' in '\n'.join(lines[max(0,i-3):i+2]):
                        problematic_lines.append((i, line.strip()))

            if problematic_lines:
                print(f"\n⚠ Found $ARGUMENTS in rendered template:")
                for line_num, line in problematic_lines:
                    print(f"  Line {line_num}: {line}")

                pytest.fail(
                    f"$ARGUMENTS placeholder found in rendered template.\n"
                    f"This should be substituted with user input or removed if empty.\n"
                    f"Found at line(s): {[ln for ln, _ in problematic_lines]}"
                )

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_script_variable_substitution(self, spec_kitty_repo_root):
        """Test: {SCRIPT} is substituted with actual script path"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'script_test'
            project_path = Path(temp_dir) / project_name

            env = os.environ.copy()
            env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

            subprocess.run(
                ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
                cwd=temp_dir,
                env=env,
                input='y\n',
                capture_output=True,
                text=True,
                check=True
            )

            implement_cmd = project_path / '.claude' / 'commands' / 'spec-kitty.implement.md'
            if not implement_cmd.exists():
                pytest.skip("implement.md not found")

            content = implement_cmd.read_text(encoding='utf-8')

            # Check for literal {SCRIPT}
            if '{SCRIPT}' in content:
                # Find the line
                lines = content.split('\n')
                script_lines = [i for i, line in enumerate(lines, 1) if '{SCRIPT}' in line]

                pytest.fail(
                    f"🐛 BUG: {{SCRIPT}} placeholder not substituted!\n\n"
                    f"Found at line(s): {script_lines}\n"
                    f"Context:\n" +
                    "\n".join(f"  {i}: {lines[i-1]}" for i in script_lines) +
                    f"\n\nExpected: Actual script path like '.kittify/scripts/bash/get-feature-context.sh'\n"
                    f"Actual: Literal '{{SCRIPT}}' placeholder\n\n"
                    f"This is exactly what the user reported!"
                )

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_feature_dir_variable_substitution(self, spec_kitty_repo_root):
        """Test: {FEATURE_DIR} is substituted with actual path"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'feature_dir_test'
            project_path = Path(temp_dir) / project_name

            env = os.environ.copy()
            env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

            subprocess.run(
                ['spec-kitty', 'init', project_name, '--ai=codex', '--ignore-agent-tools'],
                cwd=temp_dir,
                env=env,
                input='y\n',
                capture_output=True,
                text=True,
                check=True
            )

            # Check codex prompts
            codex_prompts = project_path / '.codex' / 'prompts'
            if not codex_prompts.exists():
                pytest.skip("Codex prompts not generated")

            # Check all command files
            for cmd_file in codex_prompts.glob('spec-kitty.*.md'):
                content = cmd_file.read_text(encoding='utf-8')

                if '{FEATURE_DIR}' in content:
                    pytest.fail(
                        f"{{FEATURE_DIR}} placeholder in {cmd_file.name}.\n"
                        f"Should be substituted during rendering."
                    )

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_project_root_variable_substitution(self, spec_kitty_repo_root):
        """Test: {PROJECT_ROOT} is substituted with actual path"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'project_root_test'
            project_path = Path(temp_dir) / project_name

            env = os.environ.copy()
            env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

            subprocess.run(
                ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
                cwd=temp_dir,
                env=env,
                input='y\n',
                capture_output=True,
                text=True,
                check=True
            )

            claude_commands = project_path / '.claude' / 'commands'

            for cmd_file in claude_commands.glob('spec-kitty.*.md'):
                content = cmd_file.read_text(encoding='utf-8')

                if '{PROJECT_ROOT}' in content:
                    pytest.fail(
                        f"{{PROJECT_ROOT}} placeholder in {cmd_file.name}.\n"
                        f"Should be substituted with actual project path."
                    )

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestCommandSpecificVariables:
    """Test command-specific templates are fully rendered."""

    def test_implement_command_fully_rendered(self, spec_kitty_repo_root):
        """
        Test: implement.md has all variables substituted.

        This is THE test for the user-reported bug.
        """
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'implement_render_test'
            project_path = Path(temp_dir) / project_name

            env = os.environ.copy()
            env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

            subprocess.run(
                ['spec-kitty', 'init', project_name, '--ai=codex', '--ignore-agent-tools'],
                cwd=temp_dir,
                env=env,
                input='y\n',
                capture_output=True,
                text=True,
                check=True
            )

            implement_cmd = project_path / '.codex' / 'prompts' / 'spec-kitty.implement.md'
            if not implement_cmd.exists():
                pytest.skip("implement.md not found")

            content = implement_cmd.read_text(encoding='utf-8')

            # Find ALL placeholders
            variables = find_template_variables(content)

            # Check for the specific ones mentioned in user's report
            problematic = []

            for var_name, pattern_type in variables:
                # {SCRIPT} should be replaced with actual script path
                if var_name == 'SCRIPT' and pattern_type == 'braces':
                    problematic.append('{SCRIPT}')

                # $ARGUMENTS should be replaced or have user's input
                if var_name == 'ARGUMENTS' and pattern_type == 'dollar':
                    # Check if it's in the literal "## User Input" section
                    if '## User Input' in content and '$ARGUMENTS' in content.split('## User Input')[1].split('```')[1]:
                        problematic.append('$ARGUMENTS')

            if problematic:
                # Extract relevant lines
                lines = content.split('\n')
                context = []

                for i, line in enumerate(lines, 1):
                    if any(p in line for p in problematic):
                        context.append(f"Line {i}: {line.strip()}")

                pytest.fail(
                    f"🐛 USER-REPORTED BUG CONFIRMED!\n\n"
                    f"Unsubstituted placeholders in implement.md:\n" +
                    "\n".join(f"  - {p}" for p in problematic) +
                    f"\n\nContext:\n" +
                    "\n".join(f"  {c}" for c in context) +
                    f"\n\nExpected: Variables replaced with actual values\n"
                    f"Actual: Literal placeholders in rendered file\n\n"
                    f"Agent Response: '{{{problematic[0]}}} placeholder wasn't provided'\n"
                    f"This matches the user's report exactly!"
                )

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_review_command_fully_rendered(self, spec_kitty_repo_root):
        """Test: review.md has all variables substituted"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'review_render_test'
            project_path = Path(temp_dir) / project_name

            env = os.environ.copy()
            env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

            subprocess.run(
                ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
                cwd=temp_dir,
                env=env,
                input='y\n',
                capture_output=True,
                text=True,
                check=True
            )

            review_cmd = project_path / '.claude' / 'commands' / 'spec-kitty.review.md'
            if not review_cmd.exists():
                pytest.skip("review.md not found")

            content = review_cmd.read_text(encoding='utf-8')
            variables = find_template_variables(content)

            # Check for unsubstituted placeholders
            var_names = [v[0] for v in variables if v[1] == 'braces']

            problematic = [v for v in var_names if v in ['SCRIPT', 'FEATURE_DIR', 'PROJECT_ROOT']]

            if problematic:
                pytest.fail(
                    f"Unsubstituted placeholders in review.md: {problematic}"
                )

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_specify_command_fully_rendered(self, spec_kitty_repo_root):
        """Test: specify.md has all variables substituted"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'specify_render_test'
            project_path = Path(temp_dir) / project_name

            env = os.environ.copy()
            env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

            subprocess.run(
                ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
                cwd=temp_dir,
                env=env,
                input='y\n',
                capture_output=True,
                text=True,
                check=True
            )

            specify_cmd = project_path / '.claude' / 'commands' / 'spec-kitty.specify.md'
            if not specify_cmd.exists():
                pytest.skip("specify.md not found")

            content = specify_cmd.read_text(encoding='utf-8')
            variables = find_template_variables(content)

            var_names = [v[0] for v in variables if v[1] == 'braces']
            problematic = [v for v in var_names if v in ['SCRIPT', 'FEATURE_DIR']]

            if problematic:
                pytest.fail(
                    f"Unsubstituted placeholders in specify.md: {problematic}"
                )

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestAgentSpecificRendering:
    """Test agent-specific template rendering."""

    def test_claude_commands_rendered(self, spec_kitty_repo_root):
        """Test: Claude commands have variables properly substituted"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'claude_test'
            project_path = Path(temp_dir) / project_name

            env = os.environ.copy()
            env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

            subprocess.run(
                ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
                cwd=temp_dir,
                env=env,
                input='y\n',
                capture_output=True,
                text=True,
                check=True
            )

            claude_dir = project_path / '.claude' / 'commands'
            issues = []

            for cmd_file in claude_dir.glob('spec-kitty.*.md'):
                content = cmd_file.read_text(encoding='utf-8')
                variables = find_template_variables(content)

                for var_name, pattern_type in variables:
                    if pattern_type == 'braces' and var_name in ['SCRIPT', 'FEATURE_DIR', 'PROJECT_ROOT']:
                        issues.append(f"{cmd_file.name}: {{{var_name}}}")

            if issues:
                pytest.fail(f"Claude commands have unsubstituted placeholders:\n" + "\n".join(f"  - {i}" for i in issues))

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_codex_prompts_rendered(self, spec_kitty_repo_root):
        """
        Test: Codex prompts have variables properly substituted.

        User reported issue with Codex, so this is critical.
        """
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'codex_test'
            project_path = Path(temp_dir) / project_name

            env = os.environ.copy()
            env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

            subprocess.run(
                ['spec-kitty', 'init', project_name, '--ai=codex', '--ignore-agent-tools'],
                cwd=temp_dir,
                env=env,
                input='y\n',
                capture_output=True,
                text=True,
                check=True
            )

            codex_dir = project_path / '.codex' / 'prompts'
            if not codex_dir.exists():
                pytest.skip("Codex prompts not generated")

            issues = []

            for cmd_file in codex_dir.glob('spec-kitty.*.md'):
                content = cmd_file.read_text(encoding='utf-8')
                variables = find_template_variables(content)

                for var_name, pattern_type in variables:
                    if pattern_type == 'braces' and var_name in ['SCRIPT', 'FEATURE_DIR', 'PROJECT_ROOT']:
                        issues.append(f"{cmd_file.name}: {{{var_name}}}")
                    if pattern_type == 'dollar' and var_name == 'ARGUMENTS':
                        # Check if in user input section
                        if '## User Input' in content and '$ARGUMENTS' in content.split('## User Input')[1].split('\n\n')[0]:
                            issues.append(f"{cmd_file.name}: $ARGUMENTS")

            if issues:
                pytest.fail(
                    f"🐛 BUG: Codex prompts have unsubstituted placeholders!\n\n" +
                    "\n".join(f"  - {i}" for i in issues) +
                    f"\n\nThis matches the user's bug report."
                )

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_variables_agent_syntax_appropriate(self, spec_kitty_repo_root):
        """Test: Substituted paths use appropriate syntax for each agent"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'syntax_test'
            project_path = Path(temp_dir) / project_name

            env = os.environ.copy()
            env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

            subprocess.run(
                ['spec-kitty', 'init', project_name, '--ai=claude,codex', '--ignore-agent-tools'],
                cwd=temp_dir,
                env=env,
                input='y\n',
                capture_output=True,
                text=True,
                check=True
            )

            # Both agents should get properly formatted paths
            # (e.g., Unix paths on Unix, proper escaping, etc.)

            for agent, cmd_dir in [('claude', '.claude/commands'), ('codex', '.codex/prompts')]:
                commands_path = project_path / cmd_dir
                if not commands_path.exists():
                    continue

                # Just verify no syntax errors in paths
                for cmd_file in commands_path.glob('spec-kitty.*.md'):
                    content = cmd_file.read_text(encoding='utf-8')

                    # Should not have malformed paths like "{/some/path}" or "$/path"
                    if re.search(r'\{/|\$/|>\{|>\$', content):
                        pytest.fail(
                            f"Malformed path syntax in {cmd_file.name} for {agent}"
                        )

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
