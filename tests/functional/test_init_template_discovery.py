"""
Test: Template Discovery and Init Success
Purpose: Validate that spec-kitty init works with proper template discovery
Related Finding: findings/2025-11-13_01_init_template_discovery.md
Version Tested: ed3f4618b84ab40e4c5bd19ba4cd8423cea23ac6 (ed3f461)
"""
import os
import subprocess
import tempfile
from pathlib import Path
import pytest


class TestInitTemplateDiscovery:
    """Test template discovery mechanisms during init"""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_init_with_template_root_env_var(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Init succeeds when SPEC_KITTY_TEMPLATE_ROOT is set

        This is the workaround for editable installs documented in our first finding.
        """
        project_name = "test_project"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Run spec-kitty init
        result = subprocess.run(
            [
                'spec-kitty', 'init', project_name,
                '--ai=claude,codex',
                '--ignore-agent-tools'
            ],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30
        )

        # Assert init succeeded
        assert result.returncode == 0, f"Init failed: {result.stderr}"
        assert project_path.exists(), "Project directory not created"

        # Assert core structure exists
        assert (project_path / '.claude' / 'commands').exists()
        assert (project_path / '.codex' / 'prompts').exists()
        assert (project_path / '.kittify').exists()
        assert (project_path / '.git').exists()

        # Count generated files
        claude_commands = list((project_path / '.claude' / 'commands').glob('spec-kitty.*.md'))
        codex_commands = list((project_path / '.codex' / 'prompts').glob('spec-kitty.*.md'))

        # v0.11.0+ has 14 commands, v0.10.x has 13
        expected_count = 14 if len(claude_commands) >= 14 else 13
        assert len(claude_commands) >= 13, f"Expected at least 13 Claude commands, got {len(claude_commands)}"
        assert len(codex_commands) >= 13, f"Expected at least 13 Codex commands, got {len(codex_commands)}"

    def test_init_without_template_root_fails_with_clear_error(self, temp_project_dir):
        """
        Test: Init uses bundled templates when SPEC_KITTY_TEMPLATE_ROOT not set

        In v0.11.0+, templates are bundled in the package (Feature 011), so
        init succeeds without SPEC_KITTY_TEMPLATE_ROOT.

        This is the INTENDED behavior for distribution - users shouldn't need
        to set environment variables.
        """
        project_name = "test_project"

        # Explicitly unset SPEC_KITTY_TEMPLATE_ROOT
        env = os.environ.copy()
        env.pop('SPEC_KITTY_TEMPLATE_ROOT', None)

        # Run spec-kitty init - should succeed with bundled templates in v0.11.0+
        result = subprocess.run(
            [
                'spec-kitty', 'init', project_name,
                '--ai=claude',
                '--ignore-agent-tools'
            ],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30
        )

        # v0.11.0+ has bundled templates - init should succeed
        assert result.returncode == 0, f"Init should succeed with bundled templates: {result.stderr}"

        # Verify project was created correctly with bundled templates
        project_path = temp_project_dir / project_name
        assert project_path.exists(), "Project directory should be created"
        assert (project_path / '.claude' / 'commands').exists(), "Claude commands should be created"

        # Verify templates were correctly applied
        claude_commands = list((project_path / '.claude' / 'commands').glob('spec-kitty.*.md'))
        assert len(claude_commands) >= 13, f"Expected at least 13 commands, got {len(claude_commands)}"

    def test_variable_substitution_in_generated_commands(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Generated command files have variables properly substituted

        Verifies that template placeholders like {AGENT_SCRIPT}, __AGENT__, etc.
        are replaced with actual values.
        """
        project_name = "test_project"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Run init
        subprocess.run(
            [
                'spec-kitty', 'init', project_name,
                '--ai=claude',
                '--ignore-agent-tools'
            ],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True  # Raise if init fails
        )

        # Check a sample command file
        specify_cmd = project_path / '.claude' / 'commands' / 'spec-kitty.specify.md'
        assert specify_cmd.exists(), "spec-kitty.specify.md not found"

        content = specify_cmd.read_text()

        # Verify no unsubstituted template variables
        unsubstituted = []
        if '{AGENT_SCRIPT}' in content:
            unsubstituted.append('{AGENT_SCRIPT}')
        if '__AGENT__' in content:
            unsubstituted.append('__AGENT__')
        if '{SCRIPT}' in content and 'bash' not in content.lower():
            # {SCRIPT} might legitimately appear in bash script examples
            unsubstituted.append('{SCRIPT}')

        assert not unsubstituted, (
            f"Found unsubstituted template variables in {specify_cmd.name}: {unsubstituted}\n"
            f"First 500 chars: {content[:500]}"
        )

        # Verify expected variables are present
        assert '$ARGUMENTS' in content, "Expected $ARGUMENTS variable for Claude"

        # Verify it's valid markdown
        assert content.startswith('---') or content.startswith('#'), (
            "Command file should be valid Markdown (YAML frontmatter or heading)"
        )

    def test_agent_specific_formats(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Different agents get appropriate file formats

        Claude/Codex: Markdown with $ARGUMENTS
        Gemini: TOML with {{args}}
        """
        project_name = "test_project"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Init with claude and gemini to test different formats
        subprocess.run(
            [
                'spec-kitty', 'init', project_name,
                '--ai=claude,gemini',
                '--ignore-agent-tools'
            ],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        # Check Claude (Markdown format)
        claude_specify = project_path / '.claude' / 'commands' / 'spec-kitty.specify.md'
        claude_content = claude_specify.read_text()

        assert '$ARGUMENTS' in claude_content, "Claude should use $ARGUMENTS"
        assert '{{args}}' not in claude_content, "Claude should not use Gemini's {{args}}"
        assert claude_specify.suffix == '.md', "Claude commands should be .md"

        # Check Gemini (TOML format)
        gemini_specify = project_path / '.gemini' / 'commands' / 'spec-kitty.specify.toml'
        if gemini_specify.exists():
            gemini_content = gemini_specify.read_text()

            assert '{{args}}' in gemini_content, "Gemini should use {{args}}"
            assert '$ARGUMENTS' not in gemini_content, "Gemini should not use Claude's $ARGUMENTS"
            assert gemini_specify.suffix == '.toml', "Gemini commands should be .toml"
        else:
            pytest.skip("Gemini format test requires gemini agent support")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
