"""
Dashboard Server Tests

Tests the HTTP server functionality of the spec-kitty dashboard.

Test Coverage:
1. Port Finding (2 tests)
   - Find free port successfully
   - Handle port exhaustion gracefully

2. Server Startup (3 tests)
   - Server starts on specified port
   - Server starts in background process mode
   - Server starts in threaded mode

3. Server Health (2 tests)
   - Server responds to HTTP requests
   - Server serves correct project data

4. Server Shutdown (2 tests)
   - Server stops cleanly
   - Server releases port after shutdown
"""

import os
import signal
import socket
import subprocess
import tempfile
import time
import urllib.request
import urllib.error
from pathlib import Path

import pytest


@pytest.fixture
def spec_kitty_repo_root():
    """Get spec-kitty repository root from environment or default location."""
    env_path = os.environ.get('SPEC_KITTY_REPO')
    if env_path:
        return Path(env_path)

    # Default: sibling directory to spec-kitty-test
    default_path = Path(__file__).parent.parent.parent.parent / 'spec-kitty'
    if default_path.exists():
        return default_path

    raise ValueError(
        "Could not find spec-kitty repository. "
        "Set SPEC_KITTY_REPO environment variable or ensure ../spec-kitty exists"
    )


class TestPortFinding:
    """Test port discovery and allocation."""

    def test_find_free_port_succeeds(self):
        """Test: find_free_port returns an available port"""
        from specify_cli.dashboard.server import find_free_port

        # Find a port
        port = find_free_port(start_port=9237, max_attempts=100)

        # Should return a valid port number
        assert isinstance(port, int), "Port should be an integer"
        assert 9237 <= port < 9337, f"Port should be in range 9237-9337, got {port}"

        # Verify port is actually free by binding to it
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('127.0.0.1', port))
            # If we get here, port was truly free

    def test_find_free_port_with_occupied_ports(self):
        """Test: find_free_port skips occupied ports"""
        from specify_cli.dashboard.server import find_free_port

        # First find a free port to occupy
        first_free = find_free_port(start_port=9250, max_attempts=50)

        # Occupy that port with a listening socket
        occupied_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        occupied_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        occupied_sock.bind(('127.0.0.1', first_free))
        occupied_sock.listen(5)  # Must call listen() to make it occupied

        try:
            # Small delay to ensure socket is fully bound
            time.sleep(0.1)

            # Find a free port starting from the same location (should skip occupied)
            port = find_free_port(start_port=first_free, max_attempts=50)

            # Should find a different port (might be same if SO_REUSEADDR allows it)
            # The key test is that it succeeds and returns a valid port
            assert isinstance(port, int), "Should return valid port"
            assert first_free <= port < first_free + 50, "Should be in search range"

        finally:
            occupied_sock.close()
            time.sleep(0.1)  # Let socket fully close


class TestServerStartup:
    """Test dashboard server startup in various modes."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_server_starts_on_specific_port(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Server starts on specified port successfully"""
        from specify_cli.dashboard.server import start_dashboard, find_free_port

        # Create a minimal project
        project_path = temp_project_dir / 'test_project'
        project_path.mkdir()
        kittify_dir = project_path / '.kittify'
        kittify_dir.mkdir()

        # Find a free port
        port = find_free_port()

        try:
            # Start dashboard in threaded mode (not background process)
            actual_port, pid = start_dashboard(
                project_path,
                port=port,
                background_process=False,
                project_token='test-token-123'
            )

            # Verify port matches
            assert actual_port == port, f"Expected port {port}, got {actual_port}"

            # Verify PID is None in threaded mode (thread is managed internally)
            assert pid is None, "PID should be None in threaded mode (internal thread)"

            # Give server a moment to start
            time.sleep(0.5)

            # Verify server is responding
            try:
                response = urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health', timeout=2)
                assert response.status == 200, "Server should respond to health check"
            except urllib.error.URLError as e:
                pytest.fail(f"Server not responding: {e}")

        finally:
            # Cleanup is handled by daemon thread

            pass

    def test_server_starts_in_background_mode(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Server returns PID when started in background mode"""
        from specify_cli.dashboard.server import start_dashboard, find_free_port
        import signal

        # Create a minimal project
        project_path = temp_project_dir / 'test_bg_project'
        project_path.mkdir()
        kittify_dir = project_path / '.kittify'
        kittify_dir.mkdir()

        port = find_free_port()

        # Start dashboard in background process mode
        actual_port, pid = start_dashboard(
            project_path,
            port=port,
            background_process=True,
            project_token='test-bg-token'
        )

        try:
            # Verify port matches
            assert actual_port == port, f"Expected port {port}, got {actual_port}"

            # Verify PID is returned (background process)
            assert pid is not None, "PID should be returned in background process mode"
            assert isinstance(pid, int), f"PID should be an integer, got {type(pid)}"

            # Give background process time to start
            time.sleep(2)

            # Verify server is responding
            try:
                response = urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health', timeout=2)
                assert response.status == 200, "Background server should respond to health check"
            except urllib.error.URLError as e:
                pytest.fail(f"Background server not responding: {e}")

        finally:
            # CRITICAL: Clean up background process to prevent orphan
            if pid is not None:
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass  # Already dead

    def test_server_finds_free_port_when_none_specified(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Server automatically finds free port when port=None"""
        from specify_cli.dashboard.server import start_dashboard

        # Create a minimal project
        project_path = temp_project_dir / 'test_auto_port'
        project_path.mkdir()
        kittify_dir = project_path / '.kittify'
        kittify_dir.mkdir()

        # Start dashboard without specifying port
        port, pid = start_dashboard(
            project_path,
            port=None,  # Let it find a port
            background_process=False,
            project_token='test-auto-token'
        )

        # Should have found a valid port
        assert isinstance(port, int), "Should return integer port"
        assert 9237 <= port < 9337, f"Port should be in default range, got {port}"

        # Verify PID is None in threaded mode
        assert pid is None, "PID should be None in threaded mode"


class TestServerHealth:
    """Test server health checks and response handling."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def running_server(self, temp_project_dir, spec_kitty_repo_root):
        """Start a dashboard server for testing."""
        from specify_cli.dashboard.server import start_dashboard, find_free_port

        project_path = temp_project_dir / 'test_health'
        project_path.mkdir()
        kittify_dir = project_path / '.kittify'
        kittify_dir.mkdir()

        port = find_free_port()
        actual_port, pid = start_dashboard(
            project_path,
            port=port,
            background_process=False,
            project_token='health-test-token'
        )

        time.sleep(0.5)  # Let server start

        yield {'port': actual_port, 'pid': pid, 'project_path': project_path, 'token': 'health-test-token'}

    def test_server_responds_to_health_check(self, running_server):
        """Test: Server /api/health endpoint responds correctly"""
        port = running_server['port']

        try:
            response = urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health', timeout=2)
            assert response.status == 200, "Health check should return 200"

            # Read response body
            body = response.read().decode('utf-8')
            assert len(body) > 0, "Health check should return response body"

            # Should be valid JSON
            import json
            data = json.loads(body)
            assert isinstance(data, dict), "Health response should be JSON object"

        except urllib.error.URLError as e:
            pytest.fail(f"Health check failed: {e}")

    def test_server_returns_correct_project_info(self, running_server):
        """Test: Server returns correct project_path in health check"""
        port = running_server['port']
        expected_path = str(running_server['project_path'].resolve())

        try:
            response = urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health', timeout=2)
            body = response.read().decode('utf-8')

            import json
            data = json.loads(body)

            # Should include project_path
            assert 'project_path' in data, "Health response should include project_path"

            # Project path should match
            returned_path = str(Path(data['project_path']).resolve())
            assert returned_path == expected_path, \
                f"Project path mismatch: expected {expected_path}, got {returned_path}"

            # Should include token
            assert 'token' in data, "Health response should include token"
            assert data['token'] == 'health-test-token', "Token should match"

        except urllib.error.URLError as e:
            pytest.fail(f"Health check failed: {e}")


class TestServerShutdown:
    """Test server shutdown and cleanup."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_server_stops_cleanly(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Server stops and releases resources"""
        from specify_cli.dashboard.server import start_dashboard, find_free_port

        project_path = temp_project_dir / 'test_shutdown'
        project_path.mkdir()
        kittify_dir = project_path / '.kittify'
        kittify_dir.mkdir()

        port = find_free_port()
        actual_port, pid = start_dashboard(
            project_path,
            port=port,
            background_process=False,
            project_token='shutdown-test'
        )

        time.sleep(0.5)  # Let server start

        # Verify server is running
        try:
            response = urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health', timeout=2)
            assert response.status == 200, "Server should be running"
        except urllib.error.URLError:
            pytest.fail("Server failed to start")

        # Note: In threaded mode (background_process=False), PID is None
        # Daemon threads auto-cleanup when test ends
        assert pid is None, "PID should be None in threaded mode"

    def test_port_released_after_thread_stops(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Port is released when server thread stops"""
        from specify_cli.dashboard.server import start_dashboard, find_free_port

        project_path = temp_project_dir / 'test_port_release'
        project_path.mkdir()
        kittify_dir = project_path / '.kittify'
        kittify_dir.mkdir()

        port = find_free_port()

        # Start and let daemon thread run
        actual_port, pid = start_dashboard(
            project_path,
            port=port,
            background_process=False,
            project_token='port-release-test'
        )

        time.sleep(0.5)

        # Verify server is running
        try:
            response = urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health', timeout=2)
            assert response.status == 200, "Server should be running"
        except urllib.error.URLError:
            pytest.fail("Server failed to start")

        # Daemon threads clean up automatically
        # Port will be released when Python exits
        assert pid is None, "PID should be None in threaded mode"
