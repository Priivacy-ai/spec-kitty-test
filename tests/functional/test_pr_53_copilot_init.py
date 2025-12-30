"""
Test: PR #53 - Fix Copilot initialization bug

Purpose: Validate that spec-kitty init --ai copilot works correctly without NameError.

Bug History:
- Before fix: NameError: name 'commands_dir' is not defined
- Root cause: Line 41 of asset_generator.py used wrong variable name
- Fix: Changed commands_dir → command_templates_dir (commit 23a56ff)

Test Coverage:
1. Copilot Init Success (3 tests)
   - Init with --ai copilot succeeds
   - VSCode settings are copied correctly
   - No NameError is raised

2. VSCode Settings Validation (2 tests)
   - Settings.json exists in .vscode/
   - Settings.json has valid content

3. Other Agents Still Work (2 tests)
   - Claude init still works
   - Gemini init still works

Related Issues: #61, #50
Commit: 23a56ff8163f1becf7e05ac244fb24d60ebdecfd
"""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest


class TestCopilotInitFix:
    """Test that Copilot initialization works correctly."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_copilot_init_succeeds(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: spec-kitty init --ai copilot succeeds without NameError

        This was the critical bug - it would crash with:
        NameError: name 'commands_dir' is not defined

        Now it should succeed.
        """
        project_name = "copilot_test"

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        result = subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=copilot', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should succeed (no NameError)
        assert result.returncode == 0, (
            f"Copilot init should succeed. "
            f"Error: {result.stderr}\n"
            f"Output: {result.stdout}"
        )

        # Should not mention 'commands_dir' error
        assert 'commands_dir' not in result.stderr.lower(), (
            "Should not have commands_dir NameError"
        )
        assert 'NameError' not in result.stderr, (
            "Should not have any NameError"
        )

        project_path = temp_project_dir / project_name
        assert project_path.exists(), "Project directory should be created"

    def test_vscode_settings_created(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: VSCode settings.json is created for Copilot

        The bug was in the Copilot-specific code that copies vscode-settings.json.
        Verify this functionality works.
        """
        project_name = "copilot_vscode"
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
            timeout=30,
            check=True
        )

        # VSCode settings should exist
        vscode_settings = project_path / '.vscode' / 'settings.json'
        assert vscode_settings.exists(), (
            f"VSCode settings.json should be created for Copilot. "
            f"Checked: {vscode_settings}"
        )

    def test_vscode_settings_valid_json(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: VSCode settings.json has valid JSON content

        Verify the copied file is actually valid.
        """
        import json

        project_name = "copilot_valid"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=copilot', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        vscode_settings = project_path / '.vscode' / 'settings.json'

        # Should parse as valid JSON
        try:
            content = vscode_settings.read_text(encoding='utf-8')
            settings_data = json.loads(content)
            assert isinstance(settings_data, dict), "Settings should be a JSON object"
        except json.JSONDecodeError as e:
            pytest.fail(f"VSCode settings.json should be valid JSON. Error: {e}")

    def test_copilot_directory_structure(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Copilot gets proper directory structure (.github/copilot/)

        Verify the full initialization succeeds and creates expected structure.
        """
        project_name = "copilot_structure"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=copilot', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        # Copilot uses .github/copilot/ directory
        copilot_dir = project_path / '.github' / 'copilot'
        assert copilot_dir.exists(), (
            f"Copilot directory should exist at {copilot_dir}"
        )

        # Should have command templates
        commands = list(copilot_dir.glob('spec-kitty.*.md'))
        assert len(commands) >= 11, (
            f"Should have >=11 command templates, got {len(commands)}"
        )

    def test_no_regression_claude_init(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Claude init still works (no regression)

        Verify the fix didn't break other agents.
        """
        project_name = "claude_check"

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

        assert result.returncode == 0, (
            f"Claude init should still work. Error: {result.stderr}"
        )

    def test_no_regression_gemini_init(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Gemini init still works (no regression)

        Verify the fix didn't break other agents.
        """
        project_name = "gemini_check"

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        result = subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=gemini', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30
        )

        assert result.returncode == 0, (
            f"Gemini init should still work. Error: {result.stderr}"
        )

    def test_error_message_quality(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: If init fails for other reasons, error is clear (not NameError)

        Verify that when things fail, we get useful errors not Python stack traces.
        """
        project_name = "error_test"

        env = os.environ.copy()
        # Deliberately use invalid template root to trigger error
        env['SPEC_KITTY_TEMPLATE_ROOT'] = '/nonexistent/path'

        result = subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=copilot', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should fail (bad template path)
        assert result.returncode != 0, "Should fail with invalid template path"

        # But error should NOT be a NameError about commands_dir
        assert 'NameError' not in result.stderr, (
            "Error should not be a NameError (that was the bug)"
        )
        assert 'commands_dir' not in result.stderr, (
            "Error should not mention commands_dir variable"
        )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
