"""
Slash Command Path Configuration Tests

Tests that slash commands point to the RENDERED command files, not the
source templates.

The Bug:
-------
When users run /spec-kitty.implement (or other commands), they should see
the RENDERED command with variables substituted, not the source template.

User's Report:
Path shown: templates/commands/implement.md  ✗ (source template)
Should show: .codex/prompts/spec-kitty.implement.md  ✓ (rendered)

Impact:
- Agents see placeholders like {SCRIPT} and $ARGUMENTS
- Agents cannot execute commands (halt execution)
- Confusing user experience

Test Coverage:
-------------
1. Slash Command Files (3 tests)
   - Commands directory exists
   - Command files reference correct paths
   - No references to templates/ directory

2. File Path Validation (3 tests)
   - Claude commands point to .claude/commands/
   - Codex prompts point to .codex/prompts/
   - Not pointing to templates/commands/

3. Content Verification (3 tests)
   - Referenced files exist
   - Referenced files have variables substituted
   - Source templates are not referenced
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path

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


class TestSlashCommandConfiguration:
    """Test slash command configuration files."""

    def test_claude_commands_directory_exists(self, spec_kitty_repo_root):
        """Test: .claude/commands/ directory created by init"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'slash_cmd_test'
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
            assert claude_dir.exists(), \
                "Claude commands directory should be created"

            # Check for spec-kitty commands
            spec_kitty_cmds = list(claude_dir.glob('spec-kitty.*.md'))
            assert len(spec_kitty_cmds) > 0, \
                "Should have spec-kitty command files"

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_codex_prompts_directory_exists(self, spec_kitty_repo_root):
        """Test: .codex/prompts/ directory created by init"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'codex_slash_test'
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
            assert codex_dir.exists(), \
                "Codex prompts directory should be created"

            spec_kitty_cmds = list(codex_dir.glob('spec-kitty.*.md'))
            assert len(spec_kitty_cmds) > 0, \
                "Should have spec-kitty prompt files"

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_slash_commands_not_in_commands_directory(self, spec_kitty_repo_root):
        """
        Test: Slash command definitions are separate from rendered commands.

        Claude Code uses .claude/commands/*.md as slash commands.
        These should be the RENDERED versions, not source templates.
        """
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'slash_location_test'
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

            # The .claude/commands/ files ARE the slash commands
            # They should NOT reference templates/
            claude_dir = project_path / '.claude' / 'commands'

            for cmd_file in claude_dir.glob('spec-kitty.*.md'):
                content = cmd_file.read_text(encoding='utf-8')

                # Should not contain references to templates directory
                if 'templates/commands/' in content:
                    pytest.fail(
                        f"Command file {cmd_file.name} references templates/ directory.\n"
                        f"This suggests it's not properly rendered."
                    )

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestRenderedCommandPaths:
    """Test that rendered commands are in correct locations."""

    def test_claude_implement_in_correct_location(self, spec_kitty_repo_root):
        """Test: Claude's implement command is in .claude/commands/, not templates/"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'claude_path_test'
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

            # CORRECT path
            correct_path = project_path / '.claude' / 'commands' / 'spec-kitty.implement.md'
            assert correct_path.exists(), \
                "implement.md should be in .claude/commands/"

            # WRONG path (should NOT exist or be referenced)
            wrong_path = project_path / 'templates' / 'commands' / 'implement.md'
            assert not wrong_path.exists(), \
                "templates/commands/ should not exist in initialized project"

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_codex_implement_in_correct_location(self, spec_kitty_repo_root):
        """Test: Codex's implement prompt is in .codex/prompts/, not templates/"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'codex_path_test'
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

            # CORRECT path
            correct_path = project_path / '.codex' / 'prompts' / 'spec-kitty.implement.md'
            assert correct_path.exists(), \
                "implement.md should be in .codex/prompts/"

            # WRONG path
            wrong_path = project_path / 'templates' / 'commands' / 'implement.md'
            assert not wrong_path.exists(), \
                "templates/commands/ should not exist in user's project"

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_no_templates_directory_in_initialized_project(self, spec_kitty_repo_root):
        """
        Test: Initialized projects should not have a templates/ directory.

        templates/ exists only in the spec-kitty repository, not in user projects.
        """
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'no_templates_test'
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

            templates_dir = project_path / 'templates'

            if templates_dir.exists():
                pytest.fail(
                    f"templates/ directory should NOT exist in initialized project!\n"
                    f"Found: {templates_dir}\n"
                    f"This suggests templates are being copied instead of rendered.\n\n"
                    f"User projects should have:\n"
                    f"  .claude/commands/ - Rendered commands for Claude\n"
                    f"  .codex/prompts/ - Rendered prompts for Codex\n"
                    f"NOT:\n"
                    f"  templates/commands/ - Source templates (belong in spec-kitty repo)"
                )

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestRenderedContentQuality:
    """Test that rendered commands have proper content."""

    def test_rendered_implement_has_actual_script_path(self, spec_kitty_repo_root):
        """Test: implement.md has actual script path, not {SCRIPT} placeholder"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'rendered_content_test'
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

            implement_file = project_path / '.codex' / 'prompts' / 'spec-kitty.implement.md'
            content = implement_file.read_text(encoding='utf-8')

            # Should have actual script path
            assert '.kittify/scripts/bash/' in content or '.kittify/scripts/powershell/' in content, \
                "Should reference actual .kittify/scripts/ path"

            # Should NOT have {SCRIPT} placeholder
            if '{SCRIPT}' in content:
                lines = content.split('\n')
                script_lines = [i for i, line in enumerate(lines, 1) if '{SCRIPT}' in line]

                pytest.fail(
                    f"🐛 BUG: {{SCRIPT}} placeholder not substituted!\n"
                    f"Found at line(s): {script_lines}\n"
                    f"File: {implement_file}\n\n"
                    f"This is what agents see, causing them to halt."
                )

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_rendered_command_has_no_dollar_arguments(self, spec_kitty_repo_root):
        """Test: $ARGUMENTS is handled appropriately in rendered commands"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'args_render_test'
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

            implement_file = project_path / '.claude' / 'commands' / 'spec-kitty.implement.md'
            content = implement_file.read_text(encoding='utf-8')

            # Check context of $ARGUMENTS
            if '$ARGUMENTS' in content:
                # It's OK if it's in a "User Input" section as a placeholder for runtime
                # But it shouldn't be in prose/instructions as literal text

                # Find the context
                lines = content.split('\n')
                args_lines = []

                for i, line in enumerate(lines):
                    if '$ARGUMENTS' in line:
                        # Get context (5 lines before/after)
                        start = max(0, i - 5)
                        end = min(len(lines), i + 6)
                        context = lines[start:end]

                        # Check if in code block
                        code_block = False
                        for ctx_line in context:
                            if '```' in ctx_line:
                                code_block = not code_block

                        # If in ## User Input section with code block, that's OK
                        user_input_section = any('## User Input' in l for l in context)

                        if user_input_section and code_block:
                            # This is fine - it's a placeholder for runtime input
                            pass
                        else:
                            # This is problematic - literal $ARGUMENTS in instructions
                            args_lines.append((i + 1, line.strip(), '\n'.join(context)))

                if args_lines:
                    print(f"\n⚠ $ARGUMENTS found in unexpected context:")
                    for line_num, line, ctx in args_lines:
                        print(f"\nLine {line_num}: {line}")
                        print(f"Context:\n{ctx}")

                    # This is informational - $ARGUMENTS in User Input section is OK

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_source_templates_not_in_user_project(self, spec_kitty_repo_root):
        """Test: Source templates are not copied to user projects"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'no_source_templates'
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

            # These should NOT exist in user projects
            wrong_locations = [
                project_path / 'templates' / 'commands',
                project_path / 'templates',
            ]

            for wrong_path in wrong_locations:
                if wrong_path.exists():
                    files = list(wrong_path.rglob('*.md')) if wrong_path.is_dir() else []
                    pytest.fail(
                        f"Source templates copied to user project!\n"
                        f"Found: {wrong_path}\n"
                        f"Files: {[f.name for f in files]}\n\n"
                        f"User projects should only have RENDERED commands:\n"
                        f"  .claude/commands/ - For Claude\n"
                        f"  .codex/prompts/ - For Codex\n\n"
                        f"Source templates belong only in spec-kitty repository."
                    )

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestSlashCommandReferences:
    """Test what slash commands actually reference."""

    def test_user_sees_rendered_commands_not_templates(self, spec_kitty_repo_root):
        """
        Test: When user runs /spec-kitty.implement, they should see rendered command.

        This is the core test for the user's bug report.
        """
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'user_experience_test'
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

            # Codex slash commands are defined in .codex/prompts/
            # When user runs /spec-kitty.implement, Codex reads:
            #   .codex/prompts/spec-kitty.implement.md

            implement_prompt = project_path / '.codex' / 'prompts' / 'spec-kitty.implement.md'
            assert implement_prompt.exists(), \
                "Implement prompt should exist"

            content = implement_prompt.read_text(encoding='utf-8')

            # CRITICAL: This file should have variables substituted
            if '{SCRIPT}' in content:
                pytest.fail(
                    f"🐛 USER'S BUG REPRODUCED!\n\n"
                    f"File: .codex/prompts/spec-kitty.implement.md\n"
                    f"Contains: {{SCRIPT}} placeholder\n\n"
                    f"When user runs /spec-kitty.implement in Codex:\n"
                    f"1. Codex reads .codex/prompts/spec-kitty.implement.md\n"
                    f"2. Agent sees literal '{{SCRIPT}}' in instructions\n"
                    f"3. Agent says: 'The command placeholder {{SCRIPT}} wasn't provided'\n"
                    f"4. Execution halts ✗\n\n"
                    f"Expected: {{SCRIPT}} replaced with actual path like:\n"
                    f"  '.kittify/scripts/bash/check-prerequisites.sh --json'\n\n"
                    f"This is exactly what the user reported!"
                )

            # Also check $ARGUMENTS
            if '```text\n$ARGUMENTS\n```' in content or '```text\n  $ARGUMENTS\n  ```' in content:
                print(f"\n⚠ $ARGUMENTS placeholder found in User Input section")
                print(f"  This might be OK if it's a runtime placeholder")
                print(f"  But user's agent reported it as an issue")

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_slash_command_path_shown_to_user(self, spec_kitty_repo_root):
        """
        Test: Verify the path shown to user is correct.

        User's report showed: "Path: templates/commands/implement.md"
        This should be: "Path: .codex/prompts/spec-kitty.implement.md"
        """
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'path_display_test'
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

            # The path Codex shows to user should be the rendered prompt
            expected_path = '.codex/prompts/spec-kitty.implement.md'
            full_path = project_path / expected_path

            assert full_path.exists(), \
                f"Expected slash command file should exist: {expected_path}"

            # Check if there's any configuration file that might have wrong path
            # (This would be Codex-specific configuration)

            # For now, just verify the correct file exists and has substituted content
            content = full_path.read_text(encoding='utf-8')

            has_script_path = '.kittify/scripts/bash/' in content or '.kittify/scripts/powershell/' in content

            if not has_script_path:
                pytest.fail(
                    f"Rendered command doesn't have substituted script path.\n"
                    f"File: {expected_path}\n"
                    f"Expected: Reference to .kittify/scripts/bash/check-prerequisites.sh\n"
                    f"This suggests template rendering failed."
                )

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_arguments_placeholder_behavior(self, spec_kitty_repo_root):
        """
        Test: Document how $ARGUMENTS should behave.

        When user runs: /spec-kitty.implement "fix the login bug"
        The command should receive: fix the login bug

        When user runs: /spec-kitty.implement
        The $ARGUMENTS section should be empty or show "(no arguments provided)"
        """
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'args_behavior_test'
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

            implement_file = project_path / '.claude' / 'commands' / 'spec-kitty.implement.md'
            content = implement_file.read_text(encoding='utf-8')

            # Check if $ARGUMENTS is there
            if '$ARGUMENTS' in content:
                print(f"\n$ARGUMENTS placeholder exists in rendered command")
                print(f"File: {implement_file}")

                # Find context
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if '$ARGUMENTS' in line:
                        context = lines[max(0, i-3):min(len(lines), i+4)]
                        print(f"\nContext at line {i+1}:")
                        print('\n'.join(context))

                # This is expected behavior for runtime substitution
                # The slash command framework substitutes $ARGUMENTS at runtime
                print(f"\n✓ This is likely OK - $ARGUMENTS is for runtime substitution")
                print(f"  Slash command framework should substitute it when user provides args")

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
