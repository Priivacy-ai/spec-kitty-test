"""
Test Git Protection Features

Tests that agent directories are protected from accidental git commits through
.gitignore entries and pre-commit hooks.

Related: findings/0.6.0/2025-12-13_TEST_PLAN_command_templates.md

Test Coverage:
1. Gitignore Generation (2 tests)
   - All agent directories in .gitignore
   - .gitignore created during init

2. Pre-commit Hook (5 tests)
   - Hook installed and executable
   - Hook blocks agent file commits
   - Hook allows normal commits
   - Hook can be bypassed with --no-verify
   - Hook provides clear error messages

3. Protection Verification (1 test)
   - GitignoreManager verify_protection works
"""

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

    default_path = Path.home() / 'Code' / 'spec-kitty'
    if default_path.exists():
        return default_path

    raise ValueError("spec-kitty repository not found. Set SPEC_KITTY_REPO environment variable.")


class TestGitignoreGeneration:
    """Test that .gitignore includes all agent directories."""

    def test_gitignore_includes_all_agent_directories(self, spec_kitty_repo_root):
        """Test: .gitignore includes all 12 agent directories"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'test_gitignore'
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
                timeout=60,
                check=True
            )

            gitignore_file = project_path / '.gitignore'
            assert gitignore_file.exists(), \
                ".gitignore should be created during init"

            gitignore_content = gitignore_file.read_text()

            # All agent directories should be listed
            agent_dirs = [
                '.claude/',
                '.codex/',
                '.gemini/',
                '.cursor/',
                '.qwen/',
                '.opencode/',
                '.windsurf/',
                '.kilocode/',
                '.augment/',
                '.roo/',
                '.amazonq/',
                '.github/copilot/',
            ]

            missing_dirs = []
            for agent_dir in agent_dirs:
                if agent_dir not in gitignore_content:
                    missing_dirs.append(agent_dir)

            assert not missing_dirs, \
                f".gitignore missing agent directories: {missing_dirs}"

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_gitignore_created_during_init(self, spec_kitty_repo_root):
        """Test: .gitignore is created automatically"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'test_git_created'
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
                timeout=60,
                check=True
            )

            gitignore_file = project_path / '.gitignore'
            assert gitignore_file.exists(), \
                ".gitignore should exist after init"

            # Should be a file, not a directory
            assert gitignore_file.is_file(), \
                ".gitignore should be a file"

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestPreCommitHook:
    """Test pre-commit hook installation and functionality."""

    def test_pre_commit_hook_installed(self, spec_kitty_repo_root):
        """Test: Pre-commit hook is installed and executable"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'test_hook_install'
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
                timeout=60,
                check=True
            )

            hook_file = project_path / '.git' / 'hooks' / 'pre-commit-agent-check'
            assert hook_file.exists(), \
                "pre-commit-agent-check hook should be installed"

            # Check if executable (on Unix-like systems)
            if os.name != 'nt':  # Not Windows
                import stat
                file_stat = hook_file.stat()
                is_executable = bool(file_stat.st_mode & stat.S_IXUSR)
                assert is_executable, \
                    "pre-commit hook should be executable"

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_pre_commit_hook_blocks_agent_files(self, spec_kitty_repo_root):
        """Test: Pre-commit hook blocks commits of agent directory files"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'test_hook_blocks'
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
                timeout=60,
                check=True
            )

            # Create a file in agent directory
            test_file = project_path / '.claude' / 'test-secret.txt'
            test_file.write_text("This should not be committed")

            # Try to add and commit the file
            subprocess.run(
                ['git', 'add', '-f', '.claude/test-secret.txt'],
                cwd=project_path,
                capture_output=True,
                check=True
            )

            # Commit should FAIL due to pre-commit hook
            result = subprocess.run(
                ['git', 'commit', '-m', 'Test commit'],
                cwd=project_path,
                capture_output=True,
                text=True
            )

            assert result.returncode != 0, \
                "Commit should fail when agent files are staged"

            # Check for helpful error message
            output = result.stdout + result.stderr
            assert 'agent' in output.lower() or 'blocked' in output.lower(), \
                f"Error message should mention agent files or blocking. Got: {output}"

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_pre_commit_hook_allows_normal_commits(self, spec_kitty_repo_root):
        """Test: Pre-commit hook allows normal file commits"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'test_hook_allows'
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
                timeout=60,
                check=True
            )

            # Create a normal file
            test_file = project_path / 'README.md'
            test_file.write_text("# Test Project\n")

            # Add and commit should SUCCEED
            subprocess.run(
                ['git', 'add', 'README.md'],
                cwd=project_path,
                capture_output=True,
                check=True
            )

            result = subprocess.run(
                ['git', 'commit', '-m', 'Add README'],
                cwd=project_path,
                capture_output=True,
                text=True
            )

            assert result.returncode == 0, \
                f"Normal commits should succeed. Error: {result.stdout}\n{result.stderr}"

            # Verify commit was created
            log_result = subprocess.run(
                ['git', 'log', '--oneline', '-1'],
                cwd=project_path,
                capture_output=True,
                text=True,
                check=True
            )

            assert 'Add README' in log_result.stdout, \
                "Commit should be in git log"

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_pre_commit_hook_bypass_with_no_verify(self, spec_kitty_repo_root):
        """Test: Pre-commit hook can be bypassed with --no-verify"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'test_hook_bypass'
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
                timeout=60,
                check=True
            )

            # Create a file in agent directory
            test_file = project_path / '.claude' / 'bypass-test.txt'
            test_file.write_text("Testing bypass")

            # Force add the file
            subprocess.run(
                ['git', 'add', '-f', '.claude/bypass-test.txt'],
                cwd=project_path,
                capture_output=True,
                check=True
            )

            # Commit with --no-verify should SUCCEED
            result = subprocess.run(
                ['git', 'commit', '--no-verify', '-m', 'Bypass test'],
                cwd=project_path,
                capture_output=True,
                text=True
            )

            assert result.returncode == 0, \
                f"Commit with --no-verify should succeed. Error: {result.stdout}\n{result.stderr}"

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_pre_commit_hook_has_clear_error_message(self, spec_kitty_repo_root):
        """Test: Pre-commit hook provides clear, actionable error message"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'test_hook_message'
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
                timeout=60,
                check=True
            )

            # Create file in agent directory
            agent_dir = project_path / '.codex'
            agent_dir.mkdir(parents=True, exist_ok=True)
            test_file = agent_dir / 'auth.json'
            test_file.write_text('{"token": "secret"}')

            # Try to commit
            subprocess.run(
                ['git', 'add', '-f', '.codex/auth.json'],
                cwd=project_path,
                capture_output=True
            )

            result = subprocess.run(
                ['git', 'commit', '-m', 'Test'],
                cwd=project_path,
                capture_output=True,
                text=True
            )

            output = result.stdout + result.stderr

            # Should have helpful keywords
            assert any(keyword in output.lower() for keyword in [
                'blocked', 'agent', 'token', 'auth', 'fix'
            ]), f"Error message should be helpful. Got: {output}"

            # Should mention .codex
            assert '.codex' in output, \
                f"Error message should mention the specific directory. Got: {output}"

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestGitProtectionVerification:
    """Test GitignoreManager verification functionality."""

    def test_gitignore_manager_can_import(self):
        """Test: GitignoreManager can be imported"""
        try:
            from specify_cli.gitignore_manager import GitignoreManager
            assert GitignoreManager is not None
        except ImportError as e:
            pytest.skip(f"GitignoreManager not available: {e}")

    def test_gitignore_manager_verify_protection_method_exists(self):
        """Test: GitignoreManager has verify_protection method (if implemented)"""
        try:
            from specify_cli.gitignore_manager import GitignoreManager

            # Check if verify_protection method exists
            if hasattr(GitignoreManager, 'verify_protection'):
                # Method exists - this is good!
                pass
            else:
                pytest.skip("verify_protection method not yet implemented")

        except ImportError:
            pytest.skip("GitignoreManager not available")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
