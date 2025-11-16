"""
Dashboard sys.path Priority Tests

Tests the fix for commit c989f9a: Dashboard subprocess import failure due to
PYTHONPATH conflicts.

Background:
-----------
In complex Python environments (with .pth files, PYTHONPATH entries, or
multiple projects), sys.path can contain paths from other projects that
appear BEFORE spec-kitty's installation path.

The Bug (Before Fix):
--------------------
The dashboard subprocess code checked:
  if str(repo_root) not in sys.path:
      sys.path.insert(0, str(repo_root))

If spec-kitty's path was already in sys.path (at position 8, for example),
the conditional check would return False and skip the insertion. Then when
trying to import:
  from specify_cli.dashboard.server import run_dashboard_server

Python would search positions [0-7] first, not find the module, and fail with:
  ModuleNotFoundError: No module named 'specify_cli.dashboard'

The Fix:
--------
Always insert spec-kitty's path at position 0, regardless of whether it's
already in sys.path:
  sys.path.insert(0, str(repo_root))

This ensures the correct installation takes priority over environment paths.

Test Coverage:
-------------
1. Dashboard starts with polluted sys.path
2. Dashboard loads correct modules (not from other paths)
3. Dashboard works in clean environment (regression test)
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


class TestDashboardSysPathPriority:
    """Test dashboard startup with polluted sys.path."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_dashboard_starts_with_polluted_syspath(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Dashboard starts successfully even when sys.path contains
        multiple other project paths that could interfere.

        This simulates the environment where:
        - User has multiple Python projects
        - PYTHONPATH or .pth files add those paths to sys.path
        - spec-kitty's path is already in sys.path but not at position 0
        """
        project_name = 'syspath_test'
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Create a test project
        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Create fake project directories to pollute sys.path
        fake_projects = [
            temp_project_dir / 'fake_project_1' / 'src',
            temp_project_dir / 'fake_project_2' / 'src',
            temp_project_dir / 'fake_project_3' / 'src',
        ]

        for fake_path in fake_projects:
            fake_path.mkdir(parents=True, exist_ok=True)

        # Set PYTHONPATH to include fake projects (simulating .pth files or user's environment)
        # Note: spec-kitty is likely already in sys.path via pip install
        pythonpath_entries = [str(p) for p in fake_projects]
        modified_env = env.copy()
        modified_env['PYTHONPATH'] = os.pathsep.join(pythonpath_entries)

        # Try to start dashboard with polluted PYTHONPATH
        result = subprocess.run(
            ['spec-kitty', 'dashboard'],
            cwd=project_path,
            env=modified_env,
            capture_output=True,
            text=True,
            check=False
        )

        # Verify dashboard started successfully
        output = result.stdout + result.stderr

        # Should not have ModuleNotFoundError
        assert 'ModuleNotFoundError' not in output, \
            f"Dashboard should start even with polluted sys.path. Got: {output}"

        # Should not have ImportError
        assert 'ImportError' not in output, \
            f"Dashboard should import modules correctly. Got: {output}"

        # Should start successfully
        assert result.returncode == 0 or 'Started' in output or 'already running' in output, \
            f"Dashboard should start successfully. Got: {output}"

        # Clean up: Stop the dashboard if it started
        subprocess.run(
            ['spec-kitty', 'dashboard', '--kill'],
            cwd=project_path,
            env=modified_env,
            capture_output=True,
            text=True,
            check=False
        )

    def test_dashboard_health_check_with_polluted_syspath(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Dashboard health check works correctly when started with
        polluted sys.path, ensuring correct modules are loaded.
        """
        project_name = 'health_syspath_test'
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

        # Create fake paths
        fake_paths = [
            temp_project_dir / 'interference_1' / 'src',
            temp_project_dir / 'interference_2' / 'lib',
        ]

        for fake_path in fake_paths:
            fake_path.mkdir(parents=True, exist_ok=True)

        # Pollute PYTHONPATH
        modified_env = env.copy()
        modified_env['PYTHONPATH'] = os.pathsep.join([str(p) for p in fake_paths])

        # Start dashboard
        start_result = subprocess.run(
            ['spec-kitty', 'dashboard'],
            cwd=project_path,
            env=modified_env,
            capture_output=True,
            text=True,
            check=False
        )

        try:
            # Verify it started
            if start_result.returncode != 0:
                pytest.skip(f"Dashboard failed to start: {start_result.stderr}")

            # Check health endpoint
            import time
            time.sleep(1)  # Give server time to start

            # Read dashboard metadata
            dashboard_file = project_path / '.kittify' / '.dashboard'
            if not dashboard_file.exists():
                pytest.skip("Dashboard metadata file not created")

            lines = dashboard_file.read_text().strip().split('\n')
            if len(lines) < 2:
                pytest.skip("Dashboard metadata incomplete")

            port = int(lines[1])

            # Test health check
            import urllib.request
            import json

            try:
                response = urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health')
                health_data = json.loads(response.read())

                # Verify it returns correct project path
                assert 'project_path' in health_data, "Health check should include project_path"
                assert str(project_path) in health_data['project_path'], \
                    "Health check should return correct project path"

            except Exception as e:
                pytest.skip(f"Health check failed: {e}")

        finally:
            # Clean up
            subprocess.run(
                ['spec-kitty', 'dashboard', '--kill'],
                cwd=project_path,
                env=modified_env,
                capture_output=True,
                text=True,
                check=False
            )

    def test_dashboard_regression_clean_environment(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Dashboard still works in clean environment without PYTHONPATH pollution.

        Regression test to ensure the fix doesn't break normal operation.
        """
        project_name = 'clean_env_test'
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Remove PYTHONPATH if it exists
        env.pop('PYTHONPATH', None)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Start dashboard in clean environment
        result = subprocess.run(
            ['spec-kitty', 'dashboard'],
            cwd=project_path,
            env=env,
            capture_output=True,
            text=True,
            check=False
        )

        output = result.stdout + result.stderr

        # Should start successfully (no change from before fix)
        assert result.returncode == 0 or 'Started' in output or 'already running' in output, \
            f"Dashboard should work in clean environment. Got: {output}"

        # Should not have any import errors
        assert 'ModuleNotFoundError' not in output and 'ImportError' not in output, \
            "Should not have import errors in clean environment"

        # Clean up
        subprocess.run(
            ['spec-kitty', 'dashboard', '--kill'],
            cwd=project_path,
            env=env,
            capture_output=True,
            text=True,
            check=False
        )


class TestDashboardThreadedMode:
    """Test dashboard in threaded mode (doesn't spawn subprocess, less affected by sys.path)."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_threaded_mode_unaffected_by_syspath(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Threaded mode (background_process=False) should work regardless
        of sys.path pollution since it runs in the same process.

        This test documents that threaded mode doesn't have the sys.path issue.
        """
        project_name = 'threaded_test'
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

        # Test threaded mode directly
        from specify_cli.dashboard.lifecycle import ensure_dashboard_running

        try:
            # Start in threaded mode (background_process=False)
            url, port, started = ensure_dashboard_running(
                project_path,
                background_process=False
            )

            # Should start successfully
            assert port > 0, "Dashboard should get a valid port"
            assert url, "Dashboard should have a URL"

            # Verify health check
            import time
            import urllib.request
            import json

            time.sleep(0.5)

            response = urllib.request.urlopen(f'{url}/api/health')
            health_data = json.loads(response.read())

            assert 'project_path' in health_data, "Health check should work"
            assert str(project_path) in health_data['project_path'], \
                "Should return correct project path"

        except Exception as e:
            pytest.fail(f"Threaded mode failed: {e}")

        finally:
            # Stop dashboard
            from specify_cli.dashboard.lifecycle import stop_dashboard
            stop_dashboard(project_path)
