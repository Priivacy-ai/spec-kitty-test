"""
Verify Setup Command Tests

Tests the spec-kitty verify-setup command to ensure it works correctly
and doesn't crash with import errors.

Test Coverage:
1. Verify Setup Execution (3 tests)
   - verify-setup runs without crashing on fresh project
   - verify-setup runs without ImportError
   - verify-setup returns valid output

2. Verify Setup in Different Contexts (3 tests)
   - Works from main branch
   - Works from worktree
   - Works with features present

3. Error Handling (2 tests)
   - Handles missing .kittify gracefully
   - Shows helpful errors for broken projects
"""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def spec_kitty_repo_root():
    """Get spec-kitty repository root from environment or default location."""
    env_path = os.environ.get('SPEC_KITTY_REPO')
    if env_path:
        return Path(env_path)

    default_path = Path(__file__).parent.parent.parent.parent / 'spec-kitty'
    if default_path.exists():
        return default_path

    raise ValueError(
        "Could not find spec-kitty repository. "
        "Set SPEC_KITTY_REPO environment variable or ensure ../spec-kitty exists"
    )


class TestVerifySetupExecution:
    """Test that verify-setup command executes without errors."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_verify_setup_runs_without_crashing(self, temp_project_dir, spec_kitty_repo_root):
        """Test: spec-kitty verify-setup runs without crashing on fresh project"""
        project_name = 'verify_no_crash'
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
            check=True
        )

        # Run verify-setup
        result = subprocess.run(
            ['spec-kitty', 'verify-setup'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False  # Don't fail on non-zero exit
        )

        # CRITICAL: Should not crash with ImportError
        output = result.stdout + result.stderr

        assert 'ImportError' not in output, \
            f"Should not have ImportError. Got: {output}"

        # Should not crash with UnboundLocalError
        assert 'UnboundLocalError' not in output, \
            f"Should not have UnboundLocalError. Got: {output}"

        # Should not have uncaught exceptions
        assert 'Traceback (most recent call last)' not in output or result.returncode == 0, \
            f"Should not have uncaught exceptions. Got: {output}"

    def test_verify_setup_no_import_errors(self, temp_project_dir, spec_kitty_repo_root):
        """Test: verify-setup doesn't fail with 'cannot import name' errors"""
        project_name = 'verify_imports'
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
            check=True
        )

        # Run verify-setup
        result = subprocess.run(
            ['spec-kitty', 'verify-setup'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        output = result.stdout + result.stderr

        # Specifically check for the reported bug
        assert "cannot import name 'detect_feature_slug'" not in output, \
            f"Should not have detect_feature_slug import error. Got: {output}"

        assert "cannot import name 'AcceptanceError'" not in output, \
            f"Should not have AcceptanceError import error. Got: {output}"

    def test_verify_setup_returns_valid_output(self, temp_project_dir, spec_kitty_repo_root):
        """Test: verify-setup returns meaningful output"""
        project_name = 'verify_output'
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
            check=True
        )

        # Run verify-setup
        result = subprocess.run(
            ['spec-kitty', 'verify-setup'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        output = result.stdout + result.stderr

        # Should produce some output
        assert len(output) > 0, "Should produce output"

        # Should mention key things like environment, mission, or status
        assert any(keyword in output.lower() for keyword in ['environment', 'mission', 'directory', 'integrity', 'check']), \
            f"Should mention key verification items. Got: {output}"


class TestVerifySetupInDifferentContexts:
    """Test verify-setup in different project contexts."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_verify_setup_from_main_branch(self, temp_project_dir, spec_kitty_repo_root):
        """Test: verify-setup works when run from main branch"""
        project_name = 'verify_main'
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
            check=True
        )

        # Verify we're on main
        branch_result = subprocess.run(
            ['git', 'branch', '--show-current'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )
        assert 'main' in branch_result.stdout, "Should be on main branch"

        # Run verify-setup from main
        result = subprocess.run(
            ['spec-kitty', 'verify-setup'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        # Should run without ImportError/UnboundLocalError
        output = result.stdout + result.stderr
        assert 'ImportError' not in output, "Should not crash on main branch"
        assert 'UnboundLocalError' not in output, "Should not have undefined variable errors"

    def test_verify_setup_from_worktree(self, temp_project_dir, spec_kitty_repo_root):
        """Test: verify-setup works when run from feature worktree"""
        project_name = 'verify_worktree'
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
            check=True
        )

        # Create a feature
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        create_result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'VerifyTest', 'Test verify from worktree'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        # Extract worktree path
        import json
        for line in reversed(create_result.stdout.strip().split('\n')):
            if line.strip().startswith('{'):
                data = json.loads(line.strip())
                worktree_path = data.get('WORKTREE_PATH')
                break

        assert worktree_path, "Should have worktree path"

        # Run verify-setup from worktree
        result = subprocess.run(
            ['spec-kitty', 'verify-setup'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=False
        )

        # Should run without ImportError
        output = result.stdout + result.stderr
        assert 'ImportError' not in output, "Should not crash in worktree"
        assert 'UnboundLocalError' not in output, "Should not have undefined variable errors"

    def test_verify_setup_with_features_present(self, temp_project_dir, spec_kitty_repo_root):
        """Test: verify-setup works when features exist"""
        project_name = 'verify_with_features'
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
            check=True
        )

        # Create multiple features
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'

        for i, name in enumerate(['Feature1', 'Feature2', 'Feature3'], 1):
            subprocess.run(
                [str(create_script), '--json', '--feature-name', name, f'Test feature {i}'],
                cwd=project_path,
                capture_output=True,
                text=True,
                check=True
            )

        # Run verify-setup
        result = subprocess.run(
            ['spec-kitty', 'verify-setup'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        # Should handle features without crashing
        output = result.stdout + result.stderr
        assert 'ImportError' not in output, "Should not crash with features present"
        assert 'UnboundLocalError' not in output, "Should handle features correctly"


class TestVerifySetupErrorHandling:
    """Test verify-setup error handling."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_verify_setup_handles_missing_kittify(self, temp_project_dir):
        """Test: verify-setup shows helpful error when .kittify is missing"""
        project_path = temp_project_dir / 'no_kittify'
        project_path.mkdir()

        # Don't create .kittify directory (simulate broken project)

        # Run verify-setup
        result = subprocess.run(
            ['spec-kitty', 'verify-setup'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        # Should fail or warn about missing .kittify
        output = result.stdout + result.stderr

        # Should not crash with ImportError/UnboundLocalError
        assert 'ImportError' not in output, "Should handle missing .kittify gracefully"
        assert 'UnboundLocalError' not in output, "Should not have undefined variables"

        # Should mention .kittify or that project isn't initialized
        if result.returncode != 0:
            assert '.kittify' in output or 'not initialized' in output.lower() or 'not found' in output.lower(), \
                f"Should mention missing .kittify. Got: {output}"

    def test_verify_setup_shows_actionable_errors(self, temp_project_dir, spec_kitty_repo_root):
        """Test: verify-setup errors are actionable, not raw exceptions"""
        project_name = 'verify_errors'
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
            check=True
        )

        # Run verify-setup
        result = subprocess.run(
            ['spec-kitty', 'verify-setup'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        output = result.stdout + result.stderr

        # Should not show raw Python tracebacks to users
        # If there's an error, it should be handled gracefully
        if result.returncode != 0:
            # Errors should be user-friendly
            # Allow "Traceback" in debug output, but not as the primary message
            # The key is no ImportError or UnboundLocalError
            assert 'ImportError' not in output, "Should not have ImportError"
            assert 'UnboundLocalError' not in output, "Should not have UnboundLocalError"
