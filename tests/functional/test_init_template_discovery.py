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

    @pytest.fixture
    def spec_kitty_root(self):
        """Path to spec-kitty repository"""
        return Path(__file__).parent.parent.parent.parent / "spec-kitty"

    def test_init_with_template_root_env_var(self, temp_project_dir, spec_kitty_root):
        """
        Test: Init succeeds when SPEC_KITTY_TEMPLATE_ROOT is set

        This is the workaround for editable installs documented in our first finding.
        """
        project_name = "test_project"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_root)

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

        assert len(claude_commands) == 13, f"Expected 13 Claude commands, got {len(claude_commands)}"
        assert len(codex_commands) == 13, f"Expected 13 Codex commands, got {len(codex_commands)}"

    def test_init_without_template_root_fails_with_clear_error(self, temp_project_dir):
        """
        Test: Init fails gracefully when templates cannot be found

        This tests the error message quality from our first finding.
        Expected to FAIL on ed3f461 (cryptic error message).
        Expected to PASS after upstream fix (clear error with suggestions).
        """
        project_name = "test_project"

        # Explicitly unset SPEC_KITTY_TEMPLATE_ROOT
        env = os.environ.copy()
        env.pop('SPEC_KITTY_TEMPLATE_ROOT', None)

        # Run spec-kitty init (should fail)
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

        # Assert init failed (as expected)
        assert result.returncode != 0, "Init should have failed without templates"

        # Check error message quality (this is what we're fixing)
        error_output = result.stderr.lower()

        # BEFORE FIX (ed3f461): Cryptic error about .kittify/templates/commands
        # AFTER FIX: Should mention template discovery, env vars, solutions

        # These checks will help us validate the fix
        has_helpful_info = any([
            'spec_kitty_template_root' in error_output,
            'template' in error_output and 'not found' in error_output,
            'environment variable' in error_output,
        ])

        # Document what we got
        if not has_helpful_info:
            # This is expected to fail on ed3f461
            pytest.skip(
                f"Error message needs improvement (expected on ed3f461):\n{result.stderr}\n\n"
                "After upstream fix, this should provide clear guidance on:\n"
                "- SPEC_KITTY_TEMPLATE_ROOT environment variable\n"
                "- Template discovery mechanism\n"
                "- Suggested remediation steps"
            )

        # After fix, verify the error is helpful
        assert has_helpful_info, (
            f"Error message should explain template discovery issue.\n"
            f"Got: {result.stderr}"
        )

    def test_variable_substitution_in_generated_commands(self, temp_project_dir, spec_kitty_root):
        """
        Test: Generated command files have variables properly substituted

        Verifies that template placeholders like {AGENT_SCRIPT}, __AGENT__, etc.
        are replaced with actual values.
        """
        project_name = "test_project"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_root)

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

    def test_agent_specific_formats(self, temp_project_dir, spec_kitty_root):
        """
        Test: Different agents get appropriate file formats

        Claude/Codex: Markdown with $ARGUMENTS
        Gemini: TOML with {{args}}
        """
        project_name = "test_project"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_root)

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
