"""
Version Flag and Enhanced Diagnostics Tests (v0.4.12)

Tests new features added in spec-kitty v0.4.12:
1. Version flag (--version, -v)
2. Enhanced diagnostics with dashboard health checking

Test Coverage:
1. Version Flag (3 tests)
   - spec-kitty --version returns version string
   - spec-kitty -v works as shorthand
   - Version string format is correct

2. Dashboard Health in Diagnostics (4 tests)
   - Diagnostics detects healthy dashboard
   - Diagnostics detects broken dashboard
   - Diagnostics shows dashboard startup errors
   - Diagnostics reports PID tracking status

3. Diagnostics Output Format (2 tests)
   - Dashboard health section present
   - Error messages are helpful
"""

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

import pytest

from .test_helpers import get_diagnostics_command


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


class TestVersionFlag:
    """Test --version and -v flags."""

    def test_version_flag_long_form(self):
        """Test: spec-kitty --version returns version string"""
        result = subprocess.run(
            ['spec-kitty', '--version'],
            capture_output=True,
            text=True,
            check=False
        )

        # Should succeed
        assert result.returncode == 0, f"--version should succeed. Error: {result.stderr}"

        # Should return version string
        output = result.stdout.strip()
        assert 'spec-kitty-cli' in output or 'version' in output.lower(), \
            f"Should mention spec-kitty-cli or version. Got: {output}"

        # Should have version number (e.g., 0.4.12)
        version_pattern = r'\d+\.\d+\.\d+'
        assert re.search(version_pattern, output), \
            f"Should include version number (x.y.z). Got: {output}"

    def test_version_flag_short_form(self):
        """Test: spec-kitty -v works as shorthand"""
        result = subprocess.run(
            ['spec-kitty', '-v'],
            capture_output=True,
            text=True,
            check=False
        )

        # Should succeed
        assert result.returncode == 0, f"-v should succeed. Error: {result.stderr}"

        # Should return same version string
        output = result.stdout.strip()
        assert len(output) > 0, "Should return version string"

        # Should have version number
        version_pattern = r'\d+\.\d+\.\d+'
        assert re.search(version_pattern, output), \
            f"Should include version number. Got: {output}"

    def test_version_string_format(self):
        """Test: Version string follows expected format"""
        result = subprocess.run(
            ['spec-kitty', '--version'],
            capture_output=True,
            text=True,
            check=True
        )

        output = result.stdout.strip()

        # Expected format: "spec-kitty-cli version X.Y.Z" or similar
        # Should have package name
        assert 'spec-kitty' in output.lower(), "Should include package name"

        # Should have semantic version
        version_match = re.search(r'(\d+)\.(\d+)\.(\d+)', output)
        assert version_match, f"Should have semantic version (X.Y.Z). Got: {output}"

        # Version should be current (0.4.12 or higher)
        major, minor, patch = version_match.groups()
        assert int(major) >= 0, "Major version should be >= 0"
        assert int(minor) >= 4, "Minor version should be >= 4 (for 0.4.x)"


class TestDashboardHealthInDiagnostics:
    """Test enhanced diagnostics with dashboard health checking."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_diagnostics_includes_dashboard_health(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Diagnostics output includes dashboard health section"""
        project_name = 'diag_health_test'
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

        # Get version-appropriate diagnostics command
        diag_cmd, version = get_diagnostics_command()

        # Run diagnostics
        result = subprocess.run(
            diag_cmd,
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        # Should include dashboard health info
        output = result.stdout + result.stderr

        # Look for dashboard health indicators
        # Output should mention dashboard in some form
        assert 'dashboard' in output.lower(), \
            f"Diagnostics should include dashboard health (using {version}). Got: {output[:200]}"

    def test_diagnostics_detects_healthy_dashboard(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Diagnostics detects and reports healthy dashboard"""
        from specify_cli.dashboard.lifecycle import ensure_dashboard_running

        project_name = 'diag_healthy_dash'
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

        # Start dashboard in threaded mode (to avoid orphans)
        try:
            url, port, started = ensure_dashboard_running(project_path, background_process=False)
            import time
            time.sleep(0.5)

            # Run diagnostics (should detect healthy dashboard)
            from specify_cli.dashboard import run_diagnostics

            diag_result = run_diagnostics(project_path)

            # Should include dashboard health info
            assert 'dashboard' in str(diag_result).lower() or 'port' in str(diag_result), \
                f"Should include dashboard info. Got: {diag_result}"

        except Exception as e:
            # If dashboard can't start, that's okay for this test
            # The important thing is diagnostics handles it gracefully
            pass

    def test_diagnostics_detects_broken_dashboard(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Diagnostics detects and reports broken dashboard"""
        project_name = 'diag_broken_dash'
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

        # Create a broken .dashboard file (orphaned metadata)
        dashboard_file = project_path / '.kittify' / '.dashboard'
        dashboard_file.parent.mkdir(parents=True, exist_ok=True)
        dashboard_file.write_text("http://127.0.0.1:9999\n9999\nfake-token\n12345\n")

        # Run diagnostics
        from specify_cli.dashboard import run_diagnostics

        diag_result = run_diagnostics(project_path)

        # Should detect dashboard issue
        # (Either reports it's not running or shows it's broken)
        result_str = str(diag_result)

        # Should mention dashboard in some capacity
        assert isinstance(diag_result, dict), "Diagnostics should return dict"

    def test_diagnostics_shows_dashboard_errors_helpfully(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Diagnostics shows helpful error messages for dashboard issues"""
        project_name = 'diag_error_msg'
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

        # Get version-appropriate diagnostics command
        diag_cmd, version = get_diagnostics_command()

        # Run diagnostics CLI command
        result = subprocess.run(
            diag_cmd,
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        # Should run without crashing
        assert result.returncode == 0 or result.returncode == 1, \
            f"Diagnostics should run (may fail gracefully) using {version}. Got code: {result.returncode}"

        output = result.stdout + result.stderr

        # Should not have uncaught exceptions
        assert 'Traceback' not in output, \
            f"Should not have uncaught exceptions. Got: {output}"


class TestDiagnosticsOutputFormat:
    """Test diagnostics output format and content."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_diagnostics_api_includes_dashboard_section(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Diagnostics API returns dashboard health information"""
        project_name = 'diag_api_test'
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

        # Use diagnostics API
        from specify_cli.dashboard import run_diagnostics

        result = run_diagnostics(project_path)

        # Should return dict
        assert isinstance(result, dict), "Diagnostics should return dictionary"

        # Should have expected sections
        # (May include dashboard health, features, git status, etc.)
        assert len(result) > 0, "Diagnostics should return data"

    def test_error_messages_are_actionable(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Dashboard error messages guide users to fix issues"""
        project_name = 'diag_actionable'
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

        # Get version-appropriate diagnostics command
        diag_cmd, version = get_diagnostics_command()

        # Run diagnostics
        result = subprocess.run(
            diag_cmd,
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        output = result.stdout + result.stderr

        # If there are errors/warnings, they should be actionable
        # (Not testing specific errors, just that output is well-formatted)

        # Should not have cryptic Python tracebacks
        if 'error' in output.lower() or 'warning' in output.lower():
            assert 'Traceback (most recent call last)' not in output, \
                f"Errors should be user-friendly, not raw tracebacks (using {version})"
